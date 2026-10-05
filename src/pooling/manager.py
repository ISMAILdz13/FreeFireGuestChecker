"""
Connection Manager for Free Fire Guest Account Checker
Centralized manager for all connection pools
"""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from src.pooling.http_pool import HTTPConnectionPool, AsyncHTTPConnectionPool, HTTPPoolConfig
from src.pooling.database_pool import DatabaseConnectionPool, AsyncDatabaseConnectionPool, DatabasePoolConfig
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ConnectionManagerConfig:
    """Connection manager configuration"""
    http_config: HTTPPoolConfig = field(default_factory=HTTPPoolConfig)
    database_config: DatabasePoolConfig = field(default_factory=DatabasePoolConfig)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ConnectionManagerConfig:
        """Create from dictionary"""
        return cls(
            http_config=HTTPPoolConfig.from_dict(data.get("http", {})),
            database_config=DatabasePoolConfig.from_dict(data.get("database", {}))
        )


class ConnectionManager:
    """Centralized connection manager"""

    def __init__(self, config: Optional[ConnectionManagerConfig] = None):
        self.config = config or ConnectionManagerConfig()
        
        # Initialize pools
        self.http_pool = HTTPConnectionPool(self.config.http_config)
        self.async_http_pool = AsyncHTTPConnectionPool(self.config.http_config)
        self.database_pool = DatabaseConnectionPool(self.config.database_config)
        self.async_database_pool = AsyncDatabaseConnectionPool(self.config.database_config)
        
        # Statistics
        self._stats = {
            "total_requests": 0,
            "http_requests": 0,
            "database_requests": 0,
            "errors": 0
        }
        self._lock = threading.RLock()

    def get_http_pool(self) -> HTTPConnectionPool:
        """Get the HTTP connection pool"""
        return self.http_pool

    def get_async_http_pool(self) -> AsyncHTTPConnectionPool:
        """Get the async HTTP connection pool"""
        return self.async_http_pool

    def get_database_pool(self) -> DatabaseConnectionPool:
        """Get the database connection pool"""
        return self.database_pool

    def get_async_database_pool(self) -> AsyncDatabaseConnectionPool:
        """Get the async database connection pool"""
        return self.async_database_pool

    def http_request(self, method: str, url: str, **kwargs) -> Any:
        """Make an HTTP request"""
        with self._lock:
            self._stats["total_requests"] += 1
            self._stats["http_requests"] += 1
        
        return self.http_pool.request(method, url, **kwargs)

    def async_http_request(self, method: str, url: str, **kwargs) -> Any:
        """Make an async HTTP request"""
        self._stats["total_requests"] += 1
        self._stats["http_requests"] += 1
        
        return self.async_http_pool.request(method, url, **kwargs)

    def database_execute(self, sql: str, params: Tuple = ()) -> Any:
        """Execute a database query"""
        with self._lock:
            self._stats["total_requests"] += 1
            self._stats["database_requests"] += 1
        
        return self.database_pool.execute(sql, params)

    async def async_database_execute(self, sql: str, params: Tuple = ()) -> Any:
        """Execute an async database query"""
        self._stats["total_requests"] += 1
        self._stats["database_requests"] += 1
        
        return await self.async_database_pool.execute(sql, params)

    def get_stats(self) -> Dict[str, Any]:
        """Get connection manager statistics"""
        return {
            **self._stats,
            "http_pool": self.http_pool.get_stats(),
            "async_http_pool": self.async_http_pool.get_stats(),
            "database_pool": self.database_pool.get_stats(),
            "async_database_pool": self.async_database_pool.get_stats()
        }

    def close(self) -> None:
        """Close all connection pools"""
        logger.info("Closing connection manager...")
        
        try:
            self.http_pool.close()
            logger.info("HTTP pool closed")
        except Exception as e:
            logger.error(f"Error closing HTTP pool: {e}")
        
        try:
            asyncio.run_coroutine_threadsafe(self.async_http_pool.close(), asyncio.get_event_loop())
            logger.info("Async HTTP pool closed")
        except Exception as e:
            logger.error(f"Error closing async HTTP pool: {e}")
        
        try:
            self.database_pool.close()
            logger.info("Database pool closed")
        except Exception as e:
            logger.error(f"Error closing database pool: {e}")
        
        try:
            asyncio.run_coroutine_threadsafe(self.async_database_pool.close(), asyncio.get_event_loop())
            logger.info("Async database pool closed")
        except Exception as e:
            logger.error(f"Error closing async database pool: {e}")
        
        logger.info("Connection manager closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Global ConnectionManager instance
_connection_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager


def create_connection_manager(config: Optional[ConnectionManagerConfig] = None) -> ConnectionManager:
    """Create a connection manager"""
    return ConnectionManager(config)
