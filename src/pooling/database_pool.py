"""
Database Connection Pool for Free Fire Guest Account Checker
Manages a pool of database connections
"""

from __future__ import annotations

import asyncio
import threading
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from queue import Queue
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import aiosqlite
import sqlite3

from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DatabasePoolConfig:
    """Database connection pool configuration"""
    database_path: str = "data/accounts.db"
    max_connections: int = 10
    max_overflow: int = 5
    timeout: float = 30.0
    pool_recycle: int = 3600  # Recycle connections after 1 hour
    pool_pre_ping: bool = True  # Test connections before use
    
    # SQLite specific
    isolation_level: Optional[str] = None
    check_same_thread: bool = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DatabasePoolConfig:
        """Create from dictionary"""
        return cls(
            database_path=data.get("database_path", "data/accounts.db"),
            max_connections=data.get("max_connections", 10),
            max_overflow=data.get("max_overflow", 5),
            timeout=data.get("timeout", 30.0),
            pool_recycle=data.get("pool_recycle", 3600),
            pool_pre_ping=data.get("pool_pre_ping", True),
            isolation_level=data.get("isolation_level"),
            check_same_thread=data.get("check_same_thread", False)
        )


class DatabaseConnectionPool:
    """Database connection pool for SQLite"""

    def __init__(self, config: Optional[DatabasePoolConfig] = None):
        self.config = config or DatabasePoolConfig()
        self._pool: Queue = Queue(maxsize=self.config.max_connections + self.config.max_overflow)
        self._active_connections: Set = set()
        self._lock = threading.Lock()
        self._stats = {
            "total_connections": 0,
            "active_connections": 0,
            "queued_connections": 0,
            "errors": 0
        }
        
        # Initialize pool with connections
        for _ in range(min(self.config.max_connections, 5)):
            self._create_connection()

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection"""
        try:
            conn = sqlite3.connect(
                self.config.database_path,
                isolation_level=self.config.isolation_level,
                check_same_thread=self.config.check_same_thread,
                timeout=self.config.timeout
            )
            
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Set journal mode
            conn.execute("PRAGMA journal_mode = WAL")
            
            # Set synchronous mode
            conn.execute("PRAGMA synchronous = NORMAL")
            
            # Set temp store
            conn.execute("PRAGMA temp_store = MEMORY")
            
            # Set cache size
            conn.execute("PRAGMA cache_size = -20000")  # 20MB cache
            
            return conn
        except Exception as e:
            logger.error(f"Failed to create database connection: {e}")
            raise

    def get_connection(self) -> sqlite3.Connection:
        """Get a connection from the pool"""
        with self._lock:
            self._stats["queued_connections"] += 1
        
        try:
            # Try to get from queue
            connection = self._pool.get(timeout=self.config.timeout)
            
            with self._lock:
                # Test connection if pre-ping is enabled
                if self.config.pool_pre_ping:
                    try:
                        connection.execute("SELECT 1")
                    except Exception:
                        # Connection is bad, close it and create new
                        connection.close()
                        connection = self._create_connection()
                
                self._active_connections.add(connection)
                self._stats["queued_connections"] -= 1
                self._stats["active_connections"] = len(self._active_connections)
            
            return connection
        except Exception:
            # Create new connection if queue is empty or timeout
            connection = self._create_connection()
            with self._lock:
                self._active_connections.add(connection)
                self._stats["active_connections"] = len(self._active_connections)
            return connection

    def release_connection(self, connection: sqlite3.Connection) -> None:
        """Release a connection back to the pool"""
        with self._lock:
            if connection in self._active_connections:
                self._active_connections.remove(connection)
                self._stats["active_connections"] = len(self._active_connections)
                
                # Put back in queue if pool is not full
                if self._pool.qsize() < self.config.max_connections:
                    self._pool.put(connection)
                else:
                    # Close connection if pool is full
                    connection.close()

    @contextmanager
    def connection(self) -> sqlite3.Connection:
        """Context manager for connection"""
        conn = self.get_connection()
        try:
            yield conn
        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Database error: {e}")
            raise
        finally:
            self.release_connection(conn)

    def execute(self, sql: str, params: Tuple = ()) -> sqlite3.Cursor:
        """Execute a SQL query"""
        with self.connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor

    def executemany(self, sql: str, params_list: List[Tuple]) -> sqlite3.Cursor:
        """Execute multiple SQL queries"""
        with self.connection() as conn:
            cursor = conn.executemany(sql, params_list)
            return cursor

    def fetchone(self, sql: str, params: Tuple = ()) -> Optional[Tuple]:
        """Fetch one row"""
        with self.connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.fetchone()

    def fetchall(self, sql: str, params: Tuple = ()) -> List[Tuple]:
        """Fetch all rows"""
        with self.connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.fetchall()

    def commit(self) -> None:
        """Commit all connections"""
        with self._lock:
            for conn in self._active_connections:
                try:
                    conn.commit()
                except Exception:
                    pass

    def rollback(self) -> None:
        """Rollback all connections"""
        with self._lock:
            for conn in self._active_connections:
                try:
                    conn.rollback()
                except Exception:
                    pass

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        with self._lock:
            return {
                **self._stats,
                "max_connections": self.config.max_connections,
                "max_overflow": self.config.max_overflow,
                "queue_size": self._pool.qsize(),
                "database_path": self.config.database_path
            }

    def close(self) -> None:
        """Close all connections"""
        with self._lock:
            # Close all active connections
            for conn in self._active_connections:
                try:
                    conn.close()
                except Exception:
                    pass
            
            self._active_connections.clear()
            
            # Clear queue
            while not self._pool.empty():
                try:
                    conn = self._pool.get_nowait()
                    conn.close()
                except Exception:
                    pass


class AsyncDatabaseConnectionPool:
    """Async database connection pool for aiosqlite"""

    def __init__(self, config: Optional[DatabasePoolConfig] = None):
        self.config = config or DatabasePoolConfig()
        self._pool: asyncio.Queue = asyncio.Queue(
            maxsize=self.config.max_connections + self.config.max_overflow
        )
        self._active_connections: Set = set()
        self._lock = asyncio.Lock()
        self._stats = {
            "total_connections": 0,
            "active_connections": 0,
            "queued_connections": 0,
            "errors": 0
        }
        
        # Initialize pool with connections
        asyncio.create_task(self._initialize_pool())

    async def _initialize_pool(self) -> None:
        """Initialize pool with connections"""
        for _ in range(min(self.config.max_connections, 5)):
            await self._create_connection()

    async def _create_connection(self) -> aiosqlite.Connection:
        """Create a new async database connection"""
        try:
            conn = await aiosqlite.connect(
                self.config.database_path,
                timeout=self.config.timeout
            )
            
            # Enable foreign keys
            await conn.execute("PRAGMA foreign_keys = ON")
            
            # Set journal mode
            await conn.execute("PRAGMA journal_mode = WAL")
            
            # Set synchronous mode
            await conn.execute("PRAGMA synchronous = NORMAL")
            
            # Set temp store
            await conn.execute("PRAGMA temp_store = MEMORY")
            
            # Set cache size
            await conn.execute("PRAGMA cache_size = -20000")
            
            return conn
        except Exception as e:
            logger.error(f"Failed to create async database connection: {e}")
            raise

    async def get_connection(self) -> aiosqlite.Connection:
        """Get a connection from the pool"""
        async with self._lock:
            self._stats["queued_connections"] += 1
        
        try:
            # Try to get from queue
            connection = await asyncio.wait_for(
                self._pool.get(),
                timeout=self.config.timeout
            )
            
            async with self._lock:
                # Test connection if pre-ping is enabled
                if self.config.pool_pre_ping:
                    try:
                        await connection.execute("SELECT 1")
                    except Exception:
                        # Connection is bad, close it and create new
                        await connection.close()
                        connection = await self._create_connection()
                
                self._active_connections.add(connection)
                self._stats["queued_connections"] -= 1
                self._stats["active_connections"] = len(self._active_connections)
            
            return connection
        except asyncio.TimeoutError:
            # Create new connection if queue is empty or timeout
            connection = await self._create_connection()
            async with self._lock:
                self._active_connections.add(connection)
                self._stats["active_connections"] = len(self._active_connections)
            return connection

    async def release_connection(self, connection: aiosqlite.Connection) -> None:
        """Release a connection back to the pool"""
        async with self._lock:
            if connection in self._active_connections:
                self._active_connections.remove(connection)
                self._stats["active_connections"] = len(self._active_connections)
                
                # Put back in queue if pool is not full
                if self._pool.qsize() < self.config.max_connections:
                    await self._pool.put(connection)
                else:
                    # Close connection if pool is full
                    await connection.close()

    @asynccontextmanager
    async def connection(self) -> aiosqlite.Connection:
        """Async context manager for connection"""
        conn = await self.get_connection()
        try:
            yield conn
        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Async database error: {e}")
            raise
        finally:
            await self.release_connection(conn)

    async def execute(self, sql: str, params: Tuple = ()) -> aiosqlite.Cursor:
        """Execute a SQL query"""
        async with self.connection() as conn:
            cursor = await conn.execute(sql, params)
            return cursor

    async def executemany(self, sql: str, params_list: List[Tuple]) -> aiosqlite.Cursor:
        """Execute multiple SQL queries"""
        async with self.connection() as conn:
            cursor = await conn.executemany(sql, params_list)
            return cursor

    async def fetchone(self, sql: str, params: Tuple = ()) -> Optional[Tuple]:
        """Fetch one row"""
        async with self.connection() as conn:
            cursor = await conn.execute(sql, params)
            return await cursor.fetchone()

    async def fetchall(self, sql: str, params: Tuple = ()) -> List[Tuple]:
        """Fetch all rows"""
        async with self.connection() as conn:
            cursor = await conn.execute(sql, params)
            return await cursor.fetchall()

    async def commit(self) -> None:
        """Commit all connections"""
        async with self._lock:
            for conn in self._active_connections:
                try:
                    await conn.commit()
                except Exception:
                    pass

    async def rollback(self) -> None:
        """Rollback all connections"""
        async with self._lock:
            for conn in self._active_connections:
                try:
                    await conn.rollback()
                except Exception:
                    pass

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        return {
            **self._stats,
            "max_connections": self.config.max_connections,
            "max_overflow": self.config.max_overflow,
            "queue_size": self._pool.qsize(),
            "database_path": self.config.database_path
        }

    async def close(self) -> None:
        """Close all connections"""
        async with self._lock:
            # Close all active connections
            for conn in self._active_connections:
                try:
                    await conn.close()
                except Exception:
                    pass
            
            self._active_connections.clear()
            
            # Clear queue
            while not self._pool.empty():
                try:
                    conn = self._pool.get_nowait()
                    await conn.close()
                except Exception:
                    pass


def create_database_pool(config: Optional[DatabasePoolConfig] = None) -> DatabaseConnectionPool:
    """Create a database connection pool"""
    return DatabaseConnectionPool(config)


def create_async_database_pool(config: Optional[DatabasePoolConfig] = None) -> AsyncDatabaseConnectionPool:
    """Create an async database connection pool"""
    return AsyncDatabaseConnectionPool(config)
