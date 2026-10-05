"""
Account Checker Worker for Free Fire Guest Account Checker
Specialized worker for checking guest accounts
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from src.workers.queue import Task, TaskQueue, AsyncTaskQueue, TaskPriority
from src.workers.pool import WorkerPool, AsyncWorkerPool
from src.utils.logging import get_logger
from src.utils.helpers import generate_id, get_timestamp, format_timestamp
from src.utils.validators import validate_account_id
from src.level.auth import Authenticator, AuthResult
from src.level.guest_info import GuestInfoFetcher, GuestInfo
from src.database.database import Database, get_database
from config.settings import Settings, get_settings

logger = get_logger(__name__)


@dataclass
class CheckResult:
    """Result of an account check"""
    account_id: str
    success: bool
    status: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    cached: bool = False
    checked_at: float = field(default_factory=time.time)
    execution_time: float = 0.0
    retries: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "account_id": self.account_id,
            "success": self.success,
            "status": self.status,
            "data": self.data,
            "error": self.error,
            "cached": self.cached,
            "checked_at": format_timestamp(self.checked_at),
            "execution_time": self.execution_time,
            "retries": self.retries
        }


@dataclass
class BatchCheckResult:
    """Result of a batch check"""
    total: int
    success: int
    failed: int
    results: List[CheckResult]
    errors: List[Dict[str, Any]]
    started_at: float
    completed_at: float
    total_time: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total": self.total,
            "success": self.success,
            "failed": self.failed,
            "results": [r.to_dict() for r in self.results],
            "errors": self.errors,
            "started_at": format_timestamp(self.started_at),
            "completed_at": format_timestamp(self.completed_at),
            "total_time": self.total_time
        }


class AccountCheckerWorker:
    """Specialized worker for checking guest accounts"""

    def __init__(self, 
                 authenticator: Optional[Authenticator] = None,
                 guest_fetcher: Optional[GuestInfoFetcher] = None,
                 database: Optional[Database] = None,
                 settings: Optional[Settings] = None,
                 max_retries: int = 3,
                 rate_limit: float = 1.0):
        self.authenticator = authenticator
        self.guest_fetcher = guest_fetcher
        self.database = database or get_database()
        self.settings = settings or get_settings()
        self.max_retries = max_retries
        self.rate_limit = rate_limit
        
        # Initialize if not provided
        if not self.authenticator or not self.guest_fetcher:
            self._initialize_components()
        
        # Worker pool for concurrent checks
        self.pool = WorkerPool(
            num_workers=self.settings.max_workers or 4,
            queue_size=10000
        )
        
        # Rate limiting
        self._last_check_time: float = 0.0
        self._check_count: int = 0
        
        # Statistics
        self.stats = {
            "total_checks": 0,
            "successful_checks": 0,
            "failed_checks": 0,
            "cached_checks": 0,
            "total_time": 0.0,
            "avg_time": 0.0
        }

    def _initialize_components(self) -> None:
        """Initialize authenticator and guest fetcher"""
        import aiohttp
        
        http_client = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
            headers={"User-Agent": "FreeFireGuestChecker-Worker/2.0"}
        )
        
        self.authenticator = Authenticator(
            http_client=http_client,
            settings=self.settings
        )
        
        self.guest_fetcher = GuestInfoFetcher(
            http_client=http_client,
            authenticator=self.authenticator
        )

    def start(self) -> None:
        """Start the worker pool"""
        self.pool.start()
        logger.info("Account checker worker started")

    def stop(self) -> None:
        """Stop the worker pool"""
        self.pool.stop()
        logger.info("Account checker worker stopped")

    def check_account(self, account_id: str, region: str = "global") -> Optional[CheckResult]:
        """Check a single account"""
        if not validate_account_id(account_id):
            return CheckResult(
                account_id=account_id,
                success=False,
                status="invalid",
                error="Invalid account ID"
            )

        # Check rate limit
        current_time = time.time()
        if current_time - self._last_check_time < self.rate_limit:
            time.sleep(self.rate_limit - (current_time - self._last_check_time))
        
        self._last_check_time = time.time()
        self._check_count += 1

        # Check if already in database
        existing = self.database.get_account_sync(account_id) if hasattr(self.database, 'get_account_sync') else None
        if existing:
            self.stats["cached_checks"] += 1
            return CheckResult(
                account_id=account_id,
                success=True,
                status=existing.status.value if hasattr(existing, 'status') else "unknown",
                data=existing.to_dict() if hasattr(existing, 'to_dict') else {},
                cached=True
            )

        # Submit to worker pool
        start_time = time.time()
        
        def check_task():
            try:
                # Authenticate
                auth_result = self.authenticator.authenticate_sync() if hasattr(self.authenticator, 'authenticate_sync') else None
                if not auth_result or not auth_result.success:
                    return CheckResult(
                        account_id=account_id,
                        success=False,
                        status="auth_failed",
                        error=auth_result.error if auth_result else "Authentication failed"
                    )

                # Fetch guest info
                guest_info = self.guest_fetcher.fetch_guest_info_sync(
                    account_id=account_id,
                    auth_data=auth_result.data
                ) if hasattr(self.guest_fetcher, 'fetch_guest_info_sync') else None

                if not guest_info:
                    return CheckResult(
                        account_id=account_id,
                        success=False,
                        status="not_found",
                        error=f"Account not found: {account_id}"
                    )

                # Save to database
                self.database.save_account_sync(
                    account_id=account_id,
                    data=guest_info.to_dict() if hasattr(guest_info, 'to_dict') else {},
                    region=region,
                    source="worker"
                ) if hasattr(self.database, 'save_account_sync') else None

                return CheckResult(
                    account_id=account_id,
                    success=True,
                    status="success",
                    data=guest_info.to_dict() if hasattr(guest_info, 'to_dict') else {},
                    cached=False
                )

            except Exception as e:
                logger.error(f"Error checking account {account_id}: {e}")
                return CheckResult(
                    account_id=account_id,
                    success=False,
                    status="error",
                    error=str(e)
                )

        result = self.pool.submit(check_task).result
        
        if result:
            result.execution_time = time.time() - start_time
            self._update_stats(result)
        
        return result

    def check_account_async(self, account_id: str, region: str = "global") -> Optional[CheckResult]:
        """Check a single account asynchronously"""
        if not validate_account_id(account_id):
            return CheckResult(
                account_id=account_id,
                success=False,
                status="invalid",
                error="Invalid account ID"
            )

        # Check if already in database
        existing = self.database.get_account_sync(account_id) if hasattr(self.database, 'get_account_sync') else None
        if existing:
            self.stats["cached_checks"] += 1
            return CheckResult(
                account_id=account_id,
                success=True,
                status=existing.status.value if hasattr(existing, 'status') else "unknown",
                data=existing.to_dict() if hasattr(existing, 'to_dict') else {},
                cached=True
            )

        # Create async task
        async def check_task_async():
            try:
                # Authenticate
                auth_result = await self.authenticator.authenticate()
                if not auth_result.success:
                    return CheckResult(
                        account_id=account_id,
                        success=False,
                        status="auth_failed",
                        error=auth_result.error
                    )

                # Fetch guest info
                guest_info = await self.guest_fetcher.fetch_guest_info(
                    account_id=account_id,
                    auth_data=auth_result.data
                )

                if not guest_info:
                    return CheckResult(
                        account_id=account_id,
                        success=False,
                        status="not_found",
                        error=f"Account not found: {account_id}"
                    )

                # Save to database
                await self.database.save_account(
                    account_id=account_id,
                    data=guest_info.to_dict(),
                    region=region,
                    source="async_worker"
                )

                return CheckResult(
                    account_id=account_id,
                    success=True,
                    status="success",
                    data=guest_info.to_dict(),
                    cached=False
                )

            except Exception as e:
                logger.error(f"Error checking account {account_id}: {e}")
                return CheckResult(
                    account_id=account_id,
                    success=False,
                    status="error",
                    error=str(e)
                )

        # For now, run synchronously (would need async pool for true async)
        import asyncio
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(check_task_async())
        
        if result:
            result.execution_time = 0.0  # Would be set in async context
            self._update_stats(result)
        
        return result

    def check_batch(self, account_ids: List[str], region: str = "global", 
                   max_concurrent: int = 5) -> BatchCheckResult:
        """Check multiple accounts concurrently"""
        if len(account_ids) > 1000:
            raise ValueError("Maximum 1000 accounts per batch")

        if max_concurrent > 20:
            max_concurrent = 20

        start_time = time.time()
        results = []
        errors = []
        
        # Use thread pool for concurrent checks
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            futures = {
                executor.submit(self.check_account, account_id, region): account_id 
                for account_id in account_ids
            }
            
            for future in as_completed(futures):
                account_id = futures[future]
                try:
                    result = future.result()
                    if result:
                        if result.success:
                            results.append(result)
                        else:
                            errors.append({
                                "account_id": account_id,
                                "error": result.error or "Unknown error"
                            })
                except Exception as e:
                    errors.append({
                        "account_id": account_id,
                        "error": str(e)
                    })

        total_time = time.time() - start_time
        
        batch_result = BatchCheckResult(
            total=len(account_ids),
            success=len(results),
            failed=len(errors),
            results=results,
            errors=errors,
            started_at=start_time,
            completed_at=time.time(),
            total_time=total_time
        )
        
        logger.info(f"Batch check completed: {batch_result.success}/{batch_result.total} successful")
        return batch_result

    def check_batch_async(self, account_ids: List[str], region: str = "global",
                         max_concurrent: int = 5) -> Optional[BatchCheckResult]:
        """Check multiple accounts concurrently (async version)"""
        if len(account_ids) > 1000:
            raise ValueError("Maximum 1000 accounts per batch")

        if max_concurrent > 20:
            max_concurrent = 20

        start_time = time.time()
        results = []
        errors = []
        
        async def check_single(account_id: str) -> Optional[CheckResult]:
            try:
                return await self.check_account_async(account_id, region)
            except Exception as e:
                return CheckResult(
                    account_id=account_id,
                    success=False,
                    status="error",
                    error=str(e)
                )

        # For now, run synchronously (would need proper async pool)
        import asyncio
        loop = asyncio.get_event_loop()
        
        tasks = [check_single(acc) for acc in account_ids]
        batch_results = loop.run_until_complete(asyncio.gather(*tasks))
        
        for result in batch_results:
            if result:
                if result.success:
                    results.append(result)
                else:
                    errors.append({
                        "account_id": result.account_id,
                        "error": result.error or "Unknown error"
                    })

        total_time = time.time() - start_time
        
        batch_result = BatchCheckResult(
            total=len(account_ids),
            success=len(results),
            failed=len(errors),
            results=results,
            errors=errors,
            started_at=start_time,
            completed_at=time.time(),
            total_time=total_time
        )
        
        logger.info(f"Async batch check completed: {batch_result.success}/{batch_result.total} successful")
        return batch_result

    def _update_stats(self, result: CheckResult) -> None:
        """Update statistics based on check result"""
        self.stats["total_checks"] += 1
        
        if result.success:
            self.stats["successful_checks"] += 1
        else:
            self.stats["failed_checks"] += 1
        
        if result.cached:
            self.stats["cached_checks"] += 1
        
        self.stats["total_time"] += result.execution_time
        
        # Update average
        if self.stats["total_checks"] > 0:
            self.stats["avg_time"] = self.stats["total_time"] / self.stats["total_checks"]

    def get_stats(self) -> Dict[str, Any]:
        """Get checker statistics"""
        return {
            **self.stats,
            "pool_stats": self.pool.get_stats(),
            "rate_limit": self.rate_limit,
            "max_retries": self.max_retries
        }

    def clear_cache(self) -> None:
        """Clear cached results"""
        # Would clear any internal caches
        pass

    def is_running(self) -> bool:
        """Check if checker is running"""
        return self.pool.is_running()


class AsyncAccountCheckerWorker:
    """Async version of account checker worker"""

    def __init__(self,
                 authenticator: Optional[Authenticator] = None,
                 guest_fetcher: Optional[GuestInfoFetcher] = None,
                 database: Optional[Database] = None,
                 settings: Optional[Settings] = None,
                 max_retries: int = 3,
                 rate_limit: float = 1.0):
        self.authenticator = authenticator
        self.guest_fetcher = guest_fetcher
        self.database = database or get_database()
        self.settings = settings or get_settings()
        self.max_retries = max_retries
        self.rate_limit = rate_limit
        
        # Initialize if not provided
        if not self.authenticator or not self.guest_fetcher:
            self._initialize_components()
        
        # Async worker pool
        self.pool = AsyncWorkerPool(
            num_workers=self.settings.max_workers or 4,
            queue_size=10000
        )
        
        # Rate limiting
        self._last_check_time: float = 0.0
        self._check_count: int = 0
        
        # Statistics
        self.stats = {
            "total_checks": 0,
            "successful_checks": 0,
            "failed_checks": 0,
            "cached_checks": 0,
            "total_time": 0.0,
            "avg_time": 0.0
        }

    def _initialize_components(self) -> None:
        """Initialize authenticator and guest fetcher"""
        import aiohttp
        
        http_client = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
            headers={"User-Agent": "FreeFireGuestChecker-AsyncWorker/2.0"}
        )
        
        self.authenticator = Authenticator(
            http_client=http_client,
            settings=self.settings
        )
        
        self.guest_fetcher = GuestInfoFetcher(
            http_client=http_client,
            authenticator=self.authenticator
        )

    async def start(self) -> None:
        """Start the async worker pool"""
        await self.pool.start()
        logger.info("Async account checker worker started")

    async def stop(self) -> None:
        """Stop the async worker pool"""
        await self.pool.stop()
        logger.info("Async account checker worker stopped")

    async def check_account(self, account_id: str, region: str = "global") -> Optional[CheckResult]:
        """Check a single account asynchronously"""
        if not validate_account_id(account_id):
            return CheckResult(
                account_id=account_id,
                success=False,
                status="invalid",
                error="Invalid account ID"
            )

        # Check rate limit
        current_time = time.time()
        if current_time - self._last_check_time < self.rate_limit:
            await asyncio.sleep(self.rate_limit - (current_time - self._last_check_time))
        
        self._last_check_time = time.time()
        self._check_count += 1

        # Check if already in database
        existing = await self.database.get_account(account_id)
        if existing:
            self.stats["cached_checks"] += 1
            return CheckResult(
                account_id=account_id,
                success=True,
                status=existing.status.value,
                data=existing.to_dict(),
                cached=True
            )

        start_time = time.time()
        
        async def check_task():
            try:
                # Authenticate
                auth_result = await self.authenticator.authenticate()
                if not auth_result.success:
                    return CheckResult(
                        account_id=account_id,
                        success=False,
                        status="auth_failed",
                        error=auth_result.error
                    )

                # Fetch guest info
                guest_info = await self.guest_fetcher.fetch_guest_info(
                    account_id=account_id,
                    auth_data=auth_result.data
                )

                if not guest_info:
                    return CheckResult(
                        account_id=account_id,
                        success=False,
                        status="not_found",
                        error=f"Account not found: {account_id}"
                    )

                # Save to database
                await self.database.save_account(
                    account_id=account_id,
                    data=guest_info.to_dict(),
                    region=region,
                    source="async_worker"
                )

                return CheckResult(
                    account_id=account_id,
                    success=True,
                    status="success",
                    data=guest_info.to_dict(),
                    cached=False
                )

            except Exception as e:
                logger.error(f"Error checking account {account_id}: {e}")
                return CheckResult(
                    account_id=account_id,
                    success=False,
                    status="error",
                    error=str(e)
                )

        result = await self.pool.submit(check_task)
        
        if result:
            result.execution_time = time.time() - start_time
            self._update_stats(result)
        
        return result

    async def check_batch(self, account_ids: List[str], region: str = "global",
                         max_concurrent: int = 5) -> BatchCheckResult:
        """Check multiple accounts concurrently"""
        if len(account_ids) > 1000:
            raise ValueError("Maximum 1000 accounts per batch")

        if max_concurrent > 20:
            max_concurrent = 20

        start_time = time.time()
        results = []
        errors = []
        
        # Create semaphore for rate limiting
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def check_single(account_id: str) -> Optional[CheckResult]:
            async with semaphore:
                try:
                    return await self.check_account(account_id, region)
                except Exception as e:
                    return CheckResult(
                        account_id=account_id,
                        success=False,
                        status="error",
                        error=str(e)
                    )
        
        tasks = [check_single(acc) for acc in account_ids]
        batch_results = await asyncio.gather(*tasks)
        
        for result in batch_results:
            if result:
                if result.success:
                    results.append(result)
                else:
                    errors.append({
                        "account_id": result.account_id,
                        "error": result.error or "Unknown error"
                    })

        total_time = time.time() - start_time
        
        batch_result = BatchCheckResult(
            total=len(account_ids),
            success=len(results),
            failed=len(errors),
            results=results,
            errors=errors,
            started_at=start_time,
            completed_at=time.time(),
            total_time=total_time
        )
        
        logger.info(f"Async batch check completed: {batch_result.success}/{batch_result.total} successful")
        return batch_result

    def _update_stats(self, result: CheckResult) -> None:
        """Update statistics based on check result"""
        self.stats["total_checks"] += 1
        
        if result.success:
            self.stats["successful_checks"] += 1
        else:
            self.stats["failed_checks"] += 1
        
        if result.cached:
            self.stats["cached_checks"] += 1
        
        self.stats["total_time"] += result.execution_time
        
        # Update average
        if self.stats["total_checks"] > 0:
            self.stats["avg_time"] = self.stats["total_time"] / self.stats["total_checks"]

    def get_stats(self) -> Dict[str, Any]:
        """Get checker statistics"""
        return {
            **self.stats,
            "pool_stats": self.pool.get_stats(),
            "rate_limit": self.rate_limit,
            "max_retries": self.max_retries
        }

    def is_running(self) -> bool:
        """Check if checker is running"""
        return self.pool.is_running()
