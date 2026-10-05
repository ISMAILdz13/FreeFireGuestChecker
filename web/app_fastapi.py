"""
FastAPI Application for Free Fire Guest Account Checker
Provides async REST API with WebSocket support
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import sys
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Set, Tuple, Union

import aiohttp
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Import local modules
from config.settings import Settings, get_settings
from config.runtime import RuntimeState, get_runtime_state
from src.database.database import Database, get_database, init_database
from src.utils.logging import get_logger, setup_logging
from src.utils.helpers import generate_id, format_timestamp, get_timestamp
from src.utils.validators import validate_account_id, validate_proxy_config, validate_rate_limit
from src.level.auth import Authenticator, AuthResult
from src.level.guest_info import GuestInfoFetcher, GuestInfo

logger = get_logger(__name__)


@dataclass
class WebSocketConnection:
    """Represents an active WebSocket connection"""
    websocket: WebSocket
    client_id: str
    connected_at: float
    last_ping: float = field(default_factory=time.time)
    account_ids: Set[str] = field(default_factory=set)


@dataclass
class AppState:
    """Application state for FastAPI"""
    settings: Settings
    database: Database
    runtime: RuntimeState
    authenticator: Optional[Authenticator] = None
    guest_fetcher: Optional[GuestInfoFetcher] = None
    http_client: Optional[aiohttp.ClientSession] = None
    websocket_connections: Dict[str, WebSocketConnection] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)
    request_count: int = 0
    error_count: int = 0


# Global app state
_app_state: Optional[AppState] = None


def get_app_state() -> AppState:
    """Get the global application state"""
    if _app_state is None:
        raise RuntimeError("App state not initialized")
    return _app_state


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager"""
    global _app_state

    logger.info("Starting FastAPI application...")

    # Initialize settings
    settings = get_settings()
    setup_logging(level=settings.log_level, json_format=False)

    # Initialize database
    db_path = settings.database_path or "data/accounts.db"
    database = await init_database(db_path)

    # Initialize runtime state
    runtime = RuntimeState()

    # Create HTTP client
    http_client = aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=60),
        headers={"User-Agent": "FreeFireGuestChecker/2.0"}
    )

    # Create authenticator
    authenticator = Authenticator(
        http_client=http_client,
        settings=settings
    )

    # Create guest fetcher
    guest_fetcher = GuestInfoFetcher(
        http_client=http_client,
        authenticator=authenticator
    )

    # Initialize app state
    _app_state = AppState(
        settings=settings,
        database=database,
        runtime=runtime,
        authenticator=authenticator,
        guest_fetcher=guest_fetcher,
        http_client=http_client
    )

    logger.info("Application started successfully")

    yield

    # Cleanup
    logger.info("Shutting down FastAPI application...")

    if _app_state and _app_state.http_client:
        await _app_state.http_client.close()

    if _app_state and _app_state.database:
        await _app_state.database.close()

    _app_state = None
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Free Fire Guest Account Checker API",
    description="Async API for checking Free Fire guest accounts",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")


# =============================================================================
# Health and Monitoring Endpoints
# =============================================================================

@app.get("/api/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    state = get_app_state()
    db_health = await state.database.health_check()
    
    return {
        "status": "healthy",
        "timestamp": get_timestamp(),
        "uptime": time.time() - state.started_at,
        "database": db_health,
        "request_count": state.request_count,
        "error_count": state.error_count,
        "active_connections": len(state.websocket_connections)
    }


@app.get("/api/metrics")
async def metrics() -> str:
    """Prometheus metrics endpoint"""
    state = get_app_state()
    
    metrics = [
        f"# HELP freefire_guest_checker_uptime_seconds Application uptime in seconds",
        f"# TYPE freefire_guest_checker_uptime_seconds gauge",
        f"freefire_guest_checker_uptime_seconds {time.time() - state.started_at}",
        "",
        f"# HELP freefire_guest_checker_requests_total Total number of requests",
        f"# TYPE freefire_guest_checker_requests_total counter",
        f"freefire_guest_checker_requests_total {state.request_count}",
        "",
        f"# HELP freefire_guest_checker_errors_total Total number of errors",
        f"# TYPE freefire_guest_checker_errors_total counter",
        f"freefire_guest_checker_errors_total {state.error_count}",
        "",
        f"# HELP freefire_guest_checker_active_connections Active WebSocket connections",
        f"# TYPE freefire_guest_checker_active_connections gauge",
        f"freefire_guest_checker_active_connections {len(state.websocket_connections)}",
        "",
        f"# HELP freefire_guest_checker_database_size_bytes Database size in bytes",
        f"# TYPE freefire_guest_checker_database_size_bytes gauge",
    ]
    
    db_path = Path(state.settings.database_path or "data/accounts.db")
    if db_path.exists():
        metrics.append(f"freefire_guest_checker_database_size_bytes {db_path.stat().st_size}")
    
    return "\n".join(metrics)


@app.get("/api/status")
async def status() -> Dict[str, Any]:
    """Get application status"""
    state = get_app_state()
    
    stats = await state.database.get_statistics()
    
    return {
        "app": {
            "name": "FreeFireGuestChecker",
            "version": "2.0.0",
            "uptime": time.time() - state.started_at,
            "started_at": format_timestamp(state.started_at),
        },
        "database": {
            "path": state.settings.database_path,
            "accounts_count": stats.get("total_accounts", 0),
            "checked_count": stats.get("checked_count", 0),
            "banned_count": stats.get("banned_count", 0),
        },
        "connections": {
            "active": len(state.websocket_connections),
            "max": state.settings.max_connections,
        },
        "rate_limits": {
            "requests": state.runtime.rate_limits.get("requests", {}),
            "auth": state.runtime.rate_limits.get("auth", {}),
        }
    }


# =============================================================================
# Account Endpoints
# =============================================================================

@app.post("/api/accounts/check")
async def check_account(account_id: str, region: str = "global") -> Dict[str, Any]:
    """Check a single guest account"""
    state = get_app_state()
    state.request_count += 1

    # Validate input
    if not validate_account_id(account_id):
        state.error_count += 1
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid account ID: {account_id}"
        )

    try:
        # Check if already in database
        existing = await state.database.get_account(account_id)
        if existing:
            return {
                "account_id": account_id,
                "status": existing.status.value,
                "data": existing.to_dict(),
                "cached": True,
                "checked_at": format_timestamp(existing.updated_at)
            }

        # Authenticate
        auth_result = await state.authenticator.authenticate()
        if not auth_result.success:
            state.error_count += 1
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Authentication failed: {auth_result.error}"
            )

        # Fetch guest info
        guest_info = await state.guest_fetcher.fetch_guest_info(
            account_id=account_id,
            auth_data=auth_result.data
        )

        if not guest_info:
            state.error_count += 1
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account not found: {account_id}"
            )

        # Save to database
        await state.database.save_account(
            account_id=account_id,
            data=guest_info.to_dict(),
            region=region,
            source="api"
        )

        return {
            "account_id": account_id,
            "status": "success",
            "data": guest_info.to_dict(),
            "cached": False,
            "checked_at": format_timestamp(time.time())
        }

    except Exception as e:
        state.error_count += 1
        logger.error(f"Error checking account {account_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/api/accounts/check-batch")
async def check_batch(accounts: List[str], region: str = "global", max_concurrent: int = 5) -> Dict[str, Any]:
    """Check multiple accounts concurrently"""
    state = get_app_state()
    state.request_count += 1

    if len(accounts) > 1000:
        state.error_count += 1
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 1000 accounts per batch"
        )

    if max_concurrent > 20:
        max_concurrent = 20

    results = []
    errors = []
    semaphore = asyncio.Semaphore(max_concurrent)

    async def check_single(account_id: str) -> Tuple[str, Any]:
        async with semaphore:
            try:
                result = await check_account(account_id, region)
                return account_id, result
            except Exception as e:
                return account_id, {"error": str(e), "status": "failed"}

    # Run concurrent checks
    tasks = [check_single(acc) for acc in accounts]
    batch_results = await asyncio.gather(*tasks, return_exceptions=True)

    for account_id, result in batch_results:
        if isinstance(result, Exception):
            errors.append({"account_id": account_id, "error": str(result)})
        elif isinstance(result, dict) and result.get("error"):
            errors.append(result)
        else:
            results.append(result)

    return {
        "total": len(accounts),
        "success": len(results),
        "errors": len(errors),
        "results": results,
        "errors": errors,
        "completed_at": format_timestamp(time.time())
    }


@app.get("/api/accounts/{account_id}")
async def get_account(account_id: str) -> Dict[str, Any]:
    """Get account information from database"""
    state = get_app_state()
    state.request_count += 1

    account = await state.database.get_account(account_id)
    if not account:
        state.error_count += 1
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account not found: {account_id}"
        )

    return account.to_dict()


@app.get("/api/accounts")
async def list_accounts(
    page: int = 1,
    per_page: int = 50,
    status: Optional[str] = None,
    region: Optional[str] = None,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """List accounts with pagination and filtering"""
    state = get_app_state()
    state.request_count += 1

    offset = (page - 1) * per_page
    
    accounts, total = await state.database.list_accounts(
        offset=offset,
        limit=per_page,
        status=status,
        region=region,
        search=search
    )

    return {
        "accounts": [acc.to_dict() for acc in accounts],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page
        }
    }


@app.post("/api/accounts")
async def create_account(account: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update an account"""
    state = get_app_state()
    state.request_count += 1

    account_id = account.get("account_id")
    if not account_id or not validate_account_id(account_id):
        state.error_count += 1
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or missing account_id"
        )

    await state.database.save_account(
        account_id=account_id,
        data=account.get("data", {}),
        region=account.get("region", "global"),
        source=account.get("source", "api")
    )

    return {"status": "success", "account_id": account_id}


@app.delete("/api/accounts/{account_id}")
async def delete_account(account_id: str) -> Dict[str, Any]:
    """Delete an account"""
    state = get_app_state()
    state.request_count += 1

    await state.database.delete_account(account_id)
    return {"status": "deleted", "account_id": account_id}


# =============================================================================
# WebSocket Endpoints
# =============================================================================

@app.websocket("/ws/check")
async def websocket_check(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time account checking"""
    state = get_app_state()
    client_id = generate_id("ws")
    
    await websocket.accept()
    
    # Add connection to state
    connection = WebSocketConnection(
        websocket=websocket,
        client_id=client_id,
        connected_at=time.time()
    )
    state.websocket_connections[client_id] = connection
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON",
                    "client_id": client_id
                }))
                continue
            
            message_type = message.get("type")
            
            if message_type == "ping":
                connection.last_ping = time.time()
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "timestamp": get_timestamp(),
                    "client_id": client_id
                }))
            
            elif message_type == "check":
                account_id = message.get("account_id")
                if not account_id:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Missing account_id",
                        "client_id": client_id
                    }))
                    continue
                
                # Add to connection's account set
                connection.account_ids.add(account_id)
                
                # Check account
                try:
                    result = await check_account(account_id)
                    await websocket.send_text(json.dumps({
                        "type": "result",
                        "account_id": account_id,
                        "data": result,
                        "client_id": client_id
                    }))
                except Exception as e:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "account_id": account_id,
                        "message": str(e),
                        "client_id": client_id
                    }))
            
            elif message_type == "batch_check":
                accounts = message.get("accounts", [])
                if not accounts:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Missing accounts",
                        "client_id": client_id
                    }))
                    continue
                
                # Process batch
                batch_result = await check_batch(accounts)
                await websocket.send_text(json.dumps({
                    "type": "batch_result",
                    "data": batch_result,
                    "client_id": client_id
                }))
            
            elif message_type == "subscribe":
                account_id = message.get("account_id")
                if account_id:
                    connection.account_ids.add(account_id)
                    await websocket.send_text(json.dumps({
                        "type": "subscribed",
                        "account_id": account_id,
                        "client_id": client_id
                    }))
            
            elif message_type == "unsubscribe":
                account_id = message.get("account_id")
                if account_id:
                    connection.account_ids.discard(account_id)
                    await websocket.send_text(json.dumps({
                        "type": "unsubscribed",
                        "account_id": account_id,
                        "client_id": client_id
                    }))
            
            else:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}",
                    "client_id": client_id
                }))
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": str(e),
                "client_id": client_id
            }))
        except:
            pass
    finally:
        # Remove connection
        if client_id in state.websocket_connections:
            del state.websocket_connections[client_id]
        logger.info(f"WebSocket connection closed: {client_id}")


# =============================================================================
# Authentication and Configuration
# =============================================================================

@app.post("/api/auth/token")
async def get_auth_token() -> Dict[str, Any]:
    """Get authentication token (simplified for demo)"""
    state = get_app_state()
    state.request_count += 1

    try:
        auth_result = await state.authenticator.authenticate()
        if auth_result.success:
            return {
                "status": "success",
                "authenticated": True,
                "expires_in": 3600
            }
        else:
            state.error_count += 1
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=auth_result.error or "Authentication failed"
            )
    except Exception as e:
        state.error_count += 1
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/api/config")
async def get_config() -> Dict[str, Any]:
    """Get current configuration"""
    state = get_app_state()
    state.request_count += 1

    return {
        "app": {
            "name": "FreeFireGuestChecker",
            "version": "2.0.0",
            "debug": state.settings.debug
        },
        "database": {
            "path": state.settings.database_path,
            "pool_size": state.settings.database_pool_size
        },
        "rate_limits": {
            "requests": state.settings.rate_limit_requests,
            "auth": state.settings.rate_limit_auth,
            "backoff": state.settings.rate_limit_backoff
        },
        "proxy": {
            "enabled": state.settings.proxy_enabled,
            "type": state.settings.proxy_type,
            "host": state.settings.proxy_host,
            "port": state.settings.proxy_port
        },
        "logging": {
            "level": state.settings.log_level,
            "json_format": state.settings.log_json_format
        }
    }


# =============================================================================
# Utility Endpoints
# =============================================================================

@app.post("/api/utils/validate-account")
async def validate_account_endpoint(account_id: str) -> Dict[str, Any]:
    """Validate an account ID"""
    state = get_app_state()
    state.request_count += 1

    is_valid = validate_account_id(account_id)
    
    return {
        "account_id": account_id,
        "valid": is_valid,
        "reason": "Invalid format" if not is_valid else None
    }


@app.post("/api/utils/generate-accounts")
async def generate_accounts(count: int = 10, region: str = "global") -> Dict[str, Any]:
    """Generate random account IDs"""
    from scripts.generate_accounts import generate_random_accounts
    
    state = get_app_state()
    state.request_count += 1

    if count > 1000:
        count = 1000

    accounts = generate_random_accounts(count, region)
    
    return {
        "count": len(accounts),
        "region": region,
        "accounts": accounts
    }


@app.get("/api/stats")
async def get_stats() -> Dict[str, Any]:
    """Get comprehensive statistics"""
    state = get_app_state()
    state.request_count += 1

    stats = await state.database.get_statistics()
    
    return {
        "database": stats,
        "runtime": {
            "request_count": state.request_count,
            "error_count": state.error_count,
            "uptime": time.time() - state.started_at,
            "active_connections": len(state.websocket_connections)
        },
        "rate_limits": state.runtime.rate_limits
    }


# =============================================================================
# HTML Pages
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def index_page():
    """Serve index page"""
    state = get_app_state()
    state.request_count += 1

    stats = await state.database.get_statistics()
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": {"path": "/", "method": "GET"},
            "stats": stats,
            "app_name": "FreeFire Guest Checker",
            "version": "2.0.0"
        }
    )


@app.get("/check", response_class=HTMLResponse)
async def check_page():
    """Serve check page"""
    state = get_app_state()
    state.request_count += 1

    return templates.TemplateResponse(
        "check.html",
        {
            "request": {"path": "/check", "method": "GET"},
            "app_name": "FreeFire Guest Checker"
        }
    )


@app.get("/accounts", response_class=HTMLResponse)
async def accounts_page():
    """Serve accounts page"""
    state = get_app_state()
    state.request_count += 1

    accounts, total = await state.database.list_accounts(limit=50)
    
    return templates.TemplateResponse(
        "accounts.html",
        {
            "request": {"path": "/accounts", "method": "GET"},
            "accounts": [acc.to_dict() for acc in accounts],
            "total": total,
            "app_name": "FreeFire Guest Checker"
        }
    )


# =============================================================================
# Error Handlers
# =============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions"""
    state = get_app_state()
    state.error_count += 1

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "code": exc.status_code,
                "type": "http_error"
            },
            "timestamp": get_timestamp()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception) -> JSONResponse:
    """Handle general exceptions"""
    state = get_app_state()
    state.error_count += 1

    logger.error(f"Unhandled exception: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "message": "Internal server error",
                "code": 500,
                "type": "server_error",
                "details": str(exc) if state.settings.debug else None
            },
            "timestamp": get_timestamp()
        }
    )


# =============================================================================
# Main Entry Point
# =============================================================================

def run_fastapi(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run the FastAPI application"""
    import uvicorn
    
    logger.info(f"Starting FastAPI server on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=False,
        workers=4,
        log_level="info"
    )


if __name__ == "__main__":
    run_fastapi()
