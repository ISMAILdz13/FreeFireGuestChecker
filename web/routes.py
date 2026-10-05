"""
Flask Routes
Defines all web routes for the application.
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from functools import wraps

from flask import (
    Blueprint,
    Flask,
    request,
    jsonify,
    render_template,
    redirect,
    url_for,
    session,
    current_app,
)

from config import config_manager, runtime_config
from config.settings import Settings

# Import database
from src.database import Database, Account, AccountStatus, AccountFilter

# Import utilities
from src.utils import get_logger

logger = get_logger(__name__)


# Create blueprints
main_routes = Blueprint("main", __name__)
api_routes = Blueprint("api", __name__, url_prefix="/api")


class APIResponse:
    """Standard API response format."""
    
    def __init__(
        self,
        success: bool = True,
        data: Optional[Dict[str, Any]] = None,
        message: str = "",
        error: Optional[str] = None,
        status: int = 200,
    ):
        self.success = success
        self.data = data or {}
        self.message = message
        self.error = error
        self.status = status
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "timestamp": self.timestamp,
        }
        
        if self.error:
            result["error"] = self.error
        
        return result
    
    def to_json(self, status: Optional[int] = None) -> Any:
        """Convert to Flask response."""
        from flask import jsonify
        resp_status = status or self.status
        return jsonify(self.to_dict()), resp_status


def require_api_key(func):
    """Decorator to require API key for endpoints."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        config = config_manager.get()
        
        # Check for API key in headers or query parameters
        api_key = request.headers.get("X-API-Key") or request.args.get("api_key")
        
        if not api_key:
            return APIResponse(
                success=False,
                error="API key required",
                status=401,
            ).to_json(401)
        
        # Validate API key (in production, this would check against a database)
        if config.environment == "production" and api_key != config.web.secret_key:
            return APIResponse(
                success=False,
                error="Invalid API key",
                status=403,
            ).to_json(403)
        
        return func(*args, **kwargs)
    
    return wrapper


#  Main Routes 

@main_routes.route("/")
def index():
    """Main dashboard page."""
    config = config_manager.get()
    
    # Get database stats if enabled
    db_stats = {}
    if config.database.enabled:
        try:
            db = Database(config.database.path)
            total_accounts = db.count_accounts()
            
            # Count by status
            for status in AccountStatus:
                filter = AccountFilter(status=status)
                count, _ = db.query_accounts(filter)
                db_stats[status.value.lower()] = len(count)
            
            db_stats["total"] = total_accounts
            
        except Exception as e:
            logger.error(f"Failed to get DB stats: {e}")
    
    return render_template(
        "index.html",
        db_stats=db_stats,
        config=config,
    )


@main_routes.route("/accounts")
def accounts_page():
    """Accounts list page."""
    config = config_manager.get()
    
    if not config.database.enabled:
        return redirect(url_for("main.index"))
    
    try:
        db = Database(config.database.path)
        
        # Get filter parameters from request
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        status = request.args.get("status")
        region = request.args.get("region")
        search = request.args.get("search")
        
        # Build filter
        filter = AccountFilter(
            status=AccountStatus(status) if status else None,
            region=region,
            search=search,
            limit=per_page,
            offset=(page - 1) * per_page,
        )
        
        accounts, total = db.query_accounts(filter)
        
        # Calculate pagination
        total_pages = (total + per_page - 1) // per_page
        
        return render_template(
            "accounts.html",
            accounts=accounts,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            status=status,
            region=region,
            search=search,
        )
        
    except Exception as e:
        logger.error(f"Failed to load accounts: {e}")
        return render_template("error.html", error=str(e)), 500


@main_routes.route("/accounts/<uid>")
def account_detail(uid: str):
    """Account detail page."""
    config = config_manager.get()
    
    if not config.database.enabled:
        return redirect(url_for("main.index"))
    
    try:
        db = Database(config.database.path)
        account = db.get_account(uid)
        
        if not account:
            return render_template("404.html"), 404
        
        # Get check history
        check_results = db.get_check_results(account.id, limit=10)
        
        return render_template(
            "account_detail.html",
            account=account,
            check_results=check_results,
        )
        
    except Exception as e:
        logger.error(f"Failed to load account {uid}: {e}")
        return render_template("error.html", error=str(e)), 500


@main_routes.route("/check")
def check_page():
    """Check accounts page."""
    config = config_manager.get()
    
    if not config.database.enabled:
        return redirect(url_for("main.index"))
    
    return render_template("check.html", config=config)


@main_routes.route("/settings")
def settings_page():
    """Settings page."""
    config = config_manager.get()
    return render_template("settings.html", config=config)


#  API Routes 

@api_routes.route("/status")
def api_status():
    """Get API status and health check."""
    config = config_manager.get()
    
    # Get runtime stats
    stats = runtime_config.get_stats()
    
    # Check database connectivity
    db_status = "disabled"
    if config.database.enabled:
        try:
            db = Database(config.database.path)
            count = db.count_accounts()
            db_status = {"status": "ok", "account_count": count}
        except Exception as e:
            db_status = {"status": "error", "error": str(e)}
    
    return APIResponse(
        success=True,
        data={
            "app_name": config.app_name,
            "version": config.version,
            "environment": config.environment,
            "uptime_seconds": stats["uptime_seconds"],
            "database": db_status,
        },
        message="API is running",
    ).to_json()


@api_routes.route("/accounts", methods=["GET"])
@require_api_key
def api_get_accounts():
    """Get list of accounts."""
    config = config_manager.get()
    
    if not config.database.enabled:
        return APIResponse(
            success=False,
            error="Database is disabled",
            status=400,
        ).to_json(400)
    
    try:
        db = Database(config.database.path)
        
        # Get filter parameters
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 50))
        status = request.args.get("status")
        region = request.args.get("region")
        search = request.args.get("search")
        
        # Build filter
        filter = AccountFilter(
            status=AccountStatus(status) if status else None,
            region=region,
            search=search,
            limit=per_page,
            offset=(page - 1) * per_page,
        )
        
        accounts, total = db.query_accounts(filter)
        
        # Convert to JSON-safe format
        accounts_data = []
        for account in accounts:
            acc_data = account.to_dict()
            # Remove password for security
            acc_data.pop("password", None)
            accounts_data.append(acc_data)
        
        return APIResponse(
            success=True,
            data={
                "accounts": accounts_data,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page,
            },
        ).to_json()
        
    except Exception as e:
        logger.error(f"API error: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            status=500,
        ).to_json(500)


@api_routes.route("/accounts/<uid>", methods=["GET"])
@require_api_key
def api_get_account(uid: str):
    """Get a single account by UID."""
    config = config_manager.get()
    
    if not config.database.enabled:
        return APIResponse(
            success=False,
            error="Database is disabled",
            status=400,
        ).to_json(400)
    
    try:
        db = Database(config.database.path)
        account = db.get_account(uid)
        
        if not account:
            return APIResponse(
                success=False,
                error=f"Account {uid} not found",
                status=404,
            ).to_json(404)
        
        account_data = account.to_dict()
        # Remove password for security
        account_data.pop("password", None)
        
        return APIResponse(
            success=True,
            data=account_data,
        ).to_json()
        
    except Exception as e:
        logger.error(f"API error: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            status=500,
        ).to_json(500)


@api_routes.route("/accounts", methods=["POST"])
@require_api_key
def api_create_account():
    """Create a new account."""
    config = config_manager.get()
    
    if not config.database.enabled:
        return APIResponse(
            success=False,
            error="Database is disabled",
            status=400,
        ).to_json(400)
    
    try:
        data = request.get_json()
        if not data:
            return APIResponse(
                success=False,
                error="Request body is required",
                status=400,
            ).to_json(400)
        
        # Validate required fields
        uid = data.get("uid")
        password = data.get("password")
        
        if not uid or not password:
            return APIResponse(
                success=False,
                error="uid and password are required",
                status=400,
            ).to_json(400)
        
        # Create account
        account = Account(
            uid=uid,
            password=password,
            name=data.get("name", ""),
            source=AccountSource.MANUAL,
            region=data.get("region", "GLOBAL"),
            notes=data.get("notes", ""),
            tags=data.get("tags", []),
        )
        
        db = Database(config.database.path)
        db.add_account(account)
        
        return APIResponse(
            success=True,
            data={"message": "Account created", "uid": uid},
            status=201,
        ).to_json(201)
        
    except Exception as e:
        logger.error(f"API error: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            status=500,
        ).to_json(500)


@api_routes.route("/accounts/<uid>", methods=["PUT"])
@require_api_key
def api_update_account(uid: str):
    """Update an account."""
    config = config_manager.get()
    
    if not config.database.enabled:
        return APIResponse(
            success=False,
            error="Database is disabled",
            status=400,
        ).to_json(400)
    
    try:
        data = request.get_json()
        if not data:
            return APIResponse(
                success=False,
                error="Request body is required",
                status=400,
            ).to_json(400)
        
        db = Database(config.database.path)
        account = db.get_account(uid)
        
        if not account:
            return APIResponse(
                success=False,
                error=f"Account {uid} not found",
                status=404,
            ).to_json(404)
        
        # Update fields
        if "name" in data:
            account.name = data["name"]
        if "region" in data:
            account.region = data["region"]
        if "notes" in data:
            account.notes = data["notes"]
        if "tags" in data:
            account.tags = data["tags"]
        if "status" in data:
            account.status = AccountStatus(data["status"])
        
        account.updated_at = datetime.now()
        db.update_account(account)
        
        return APIResponse(
            success=True,
            data={"message": "Account updated", "uid": uid},
        ).to_json()
        
    except Exception as e:
        logger.error(f"API error: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            status=500,
        ).to_json(500)


@api_routes.route("/accounts/<uid>", methods=["DELETE"])
@require_api_key
def api_delete_account(uid: str):
    """Delete an account."""
    config = config_manager.get()
    
    if not config.database.enabled:
        return APIResponse(
            success=False,
            error="Database is disabled",
            status=400,
        ).to_json(400)
    
    try:
        db = Database(config.database.path)
        
        if not db.delete_account(uid):
            return APIResponse(
                success=False,
                error=f"Account {uid} not found",
                status=404,
            ).to_json(404)
        
        return APIResponse(
            success=True,
            data={"message": "Account deleted", "uid": uid},
        ).to_json()
        
    except Exception as e:
        logger.error(f"API error: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            status=500,
        ).to_json(500)


@api_routes.route("/check", methods=["POST"])
@require_api_key
def api_check_accounts():
    """Check accounts via API."""
    import asyncio
    from guest_checker_v2 import AccountChecker, AccountData, CheckOptions, CheckResult
    
    config = config_manager.get()
    
    try:
        data = request.get_json()
        if not data:
            return APIResponse(
                success=False,
                error="Request body is required",
                status=400,
            ).to_json(400)
        
        # Get accounts to check
        account_uids = data.get("uids", [])
        
        if not account_uids:
            return APIResponse(
                success=False,
                error="At least one UID is required",
                status=400,
            ).to_json(400)
        
        # Load accounts from database
        db = Database(config.database.path)
        accounts = []
        
        for uid in account_uids:
            account = db.get_account(uid)
            if account:
                accounts.append(AccountData(
                    uid=account.uid,
                    password=account.password,
                    name=account.name,
                ))
        
        if not accounts:
            return APIResponse(
                success=False,
                error="No valid accounts found",
                status=404,
            ).to_json(404)
        
        # Create check options
        options = CheckOptions(
            concurrent=data.get("concurrent", config.checker.concurrent_workers),
            timeout=data.get("timeout", config.rate_limit.request_timeout),
            retries=data.get("retries", config.rate_limit.retry_attempts),
        )
        
        # Check accounts asynchronously
        import asyncio
        
        async def check_all():
            checker = AccountChecker(config, options)
            async with checker:
                results = []
                for account in accounts:
                    result = await checker.check_account(account)
                    results.append(result)
                return results
        
        results = asyncio.run(check_all())
        
        # Convert results to JSON-safe format
        results_data = [r.to_dict() for r in results]
        
        return APIResponse(
            success=True,
            data={
                "checked": len(results),
                "results": results_data,
            },
        ).to_json()
        
    except Exception as e:
        logger.error(f"API error: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            status=500,
        ).to_json(500)


@api_routes.route("/stats", methods=["GET"])
@require_api_key
def api_get_stats():
    """Get statistics about accounts."""
    config = config_manager.get()
    
    if not config.database.enabled:
        return APIResponse(
            success=False,
            error="Database is disabled",
            status=400,
        ).to_json(400)
    
    try:
        db = Database(config.database.path)
        
        # Get total count
        total = db.count_accounts()
        
        # Get counts by status
        status_counts = {}
        for status in AccountStatus:
            filter = AccountFilter(status=status)
            count, _ = db.query_accounts(filter)
            status_counts[status.value] = len(count)
        
        # Get counts by region
        region_counts = {}
        filter = AccountFilter()
        all_accounts, _ = db.query_accounts(filter)
        for account in all_accounts:
            region_counts[account.region] = region_counts.get(account.region, 0) + 1
        
        return APIResponse(
            success=True,
            data={
                "total": total,
                "by_status": status_counts,
                "by_region": region_counts,
            },
        ).to_json()
        
    except Exception as e:
        logger.error(f"API error: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            status=500,
        ).to_json(500)


@api_routes.route("/export", methods=["GET"])
@require_api_key
def api_export_accounts():
    """Export accounts in various formats."""
    config = config_manager.get()
    
    if not config.database.enabled:
        return APIResponse(
            success=False,
            error="Database is disabled",
            status=400,
        ).to_json(400)
    
    try:
        format = request.args.get("format", "json")
        
        db = Database(config.database.path)
        
        if format == "json":
            data = db.export_to_json()
            
            # Remove passwords for security
            for account in data:
                account.pop("password", None)
            
            return APIResponse(
                success=True,
                data=data,
            ).to_json()
            
        elif format == "csv":
            csv_data = db.export_to_csv()
            
            from flask import Response
            return Response(
                csv_data,
                mimetype="text/csv",
                headers={
                    "Content-Disposition": "attachment; filename=accounts.csv",
                    "Content-Type": "text/csv",
                },
            )
        
        else:
            return APIResponse(
                success=False,
                error=f"Unsupported format: {format}",
                status=400,
            ).to_json(400)
        
    except Exception as e:
        logger.error(f"API error: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            status=500,
        ).to_json(500)


@api_routes.route("/import", methods=["POST"])
@require_api_key
def api_import_accounts():
    """Import accounts from JSON or CSV."""
    config = config_manager.get()
    
    if not config.database.enabled:
        return APIResponse(
            success=False,
            error="Database is disabled",
            status=400,
        ).to_json(400)
    
    try:
        format = request.args.get("format", "json")
        
        if format == "json":
            data = request.get_json()
            if not data:
                return APIResponse(
                    success=False,
                    error="Request body is required",
                    status=400,
                ).to_json(400)
            
            db = Database(config.database.path)
            imported, duplicates = db.import_from_json(data)
            
            return APIResponse(
                success=True,
                data={
                    "imported": imported,
                    "duplicates": duplicates,
                },
            ).to_json()
            
        elif format == "csv":
            csv_data = request.data.decode("utf-8")
            
            db = Database(config.database.path)
            imported, duplicates = db.import_from_csv(csv_data)
            
            return APIResponse(
                success=True,
                data={
                    "imported": imported,
                    "duplicates": duplicates,
                },
            ).to_json()
        
        else:
            return APIResponse(
                success=False,
                error=f"Unsupported format: {format}",
                status=400,
            ).to_json(400)
        
    except Exception as e:
        logger.error(f"API error: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            status=500,
        ).to_json(500)
