"""
Redis Connection Pool for Free Fire Guest Account Checker
Manages a pool of Redis connections
"""

from __future__ import annotations

import asyncio
import threading
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from queue import Queue
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import redis
from redis import Redis, ConnectionPool
import aioredis

from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RedisPoolConfig:
    """Redis connection pool configuration"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    
    # Pool configuration
    max_connections: int = 50
    max_idle_time: int = 300  # 5 minutes
    connection_lifetime: int = 3600  # 1 hour
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    socket_keepalive: bool = True
    socket_keepalive_options: Optional[Dict[str, Any]] = None
    
    # SSL configuration
    ssl: bool = False
    ssl_cert_reqs: Optional[str] = None
    ssl_ca_certs: Optional[str] = None
    ssl_certfile: Optional[str] = None
    ssl_keyfile: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RedisPoolConfig:
        """Create from dictionary"""
        return cls(
            host=data.get("host", "localhost"),
            port=data.get("port", 6379),
            db=data.get("db", 0),
            password=data.get("password"),
            max_connections=data.get("max_connections", 50),
            max_idle_time=data.get("max_idle_time", 300),
            connection_lifetime=data.get("connection_lifetime", 3600),
            socket_timeout=data.get("socket_timeout", 5.0),
            socket_connect_timeout=data.get("socket_connect_timeout", 5.0),
            socket_keepalive=data.get("socket_keepalive", True),
            socket_keepalive_options=data.get("socket_keepalive_options"),
            ssl=data.get("ssl", False),
            ssl_cert_reqs=data.get("ssl_cert_reqs"),
            ssl_ca_certs=data.get("ssl_ca_certs"),
            ssl_certfile=data.get("ssl_certfile"),
            ssl_keyfile=data.get("ssl_keyfile")
        )


class RedisConnectionPool:
    """Redis connection pool for synchronous operations"""

    def __init__(self, config: Optional[RedisPoolConfig] = None):
        self.config = config or RedisPoolConfig()
        self._pool: Queue = Queue(maxsize=self.config.max_connections)
        self._active_connections: Set = set()
        self._lock = threading.RLock()
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "active_connections": 0,
            "queued_connections": 0
        }
        
        # Create connection pool
        self._connection_pool = self._create_connection_pool()
        
        # Initialize pool with connections
        for _ in range(min(self.config.max_connections, 10)):
            self._create_connection()

    def _create_connection_pool(self) -> ConnectionPool:
        """Create a Redis connection pool"""
        return ConnectionPool(
            host=self.config.host,
            port=self.config.port,
            db=self.config.db,
            password=self.config.password,
            max_connections=self.config.max_connections,
            max_idle_time=self.config.max_idle_time,
            connection_lifetime=self.config.connection_lifetime,
            socket_timeout=self.config.socket_timeout,
            socket_connect_timeout=self.config.socket_connect_timeout,
            socket_keepalive=self.config.socket_keepalive,
            socket_keepalive_options=self.config.socket_keepalive_options,
            ssl=self.config.ssl,
            ssl_cert_reqs=self.config.ssl_cert_reqs,
            ssl_ca_certs=self.config.ssl_ca_certs,
            ssl_certfile=self.config.ssl_certfile,
            ssl_keyfile=self.config.ssl_keyfile,
            decode_responses=True
        )

    def _create_connection(self) -> Redis:
        """Create a new Redis connection"""
        return Redis(connection_pool=self._connection_pool)

    def get_connection(self) -> Redis:
        """Get a connection from the pool"""
        with self._lock:
            self._stats["queued_connections"] += 1
        
        try:
            # Try to get from queue
            connection = self._pool.get(timeout=5.0)
            
            with self._lock:
                # Test connection
                try:
                    connection.ping()
                except Exception:
                    # Connection is bad, close it and create new
                    connection.connection_pool.release(connection.connection)
                    connection = self._create_connection()
                
                self._active_connections.add(connection)
                self._stats["queued_connections"] -= 1
                self._stats["active_connections"] = len(self._active_connections)
            
            return connection
        except Exception:
            # Create new connection
            connection = self._create_connection()
            with self._lock:
                self._active_connections.add(connection)
                self._stats["active_connections"] = len(self._active_connections)
            return connection

    def release_connection(self, connection: Redis) -> None:
        """Release a connection back to the pool"""
        with self._lock:
            if connection in self._active_connections:
                self._active_connections.remove(connection)
                self._stats["active_connections"] = len(self._active_connections)
                
                # Put back in queue if pool is not full
                if self._pool.qsize() < self.config.max_connections:
                    self._pool.put(connection)
                else:
                    # Close connection
                    connection.close()

    @contextmanager
    def connection(self) -> Redis:
        """Context manager for connection"""
        conn = self.get_connection()
        try:
            yield conn
        except Exception as e:
            self._stats["failed_requests"] += 1
            logger.error(f"Redis error: {e}")
            raise
        finally:
            self.release_connection(conn)

    def execute_command(self, *args, **kwargs) -> Any:
        """Execute a Redis command"""
        with self.connection() as conn:
            self._stats["total_requests"] += 1
            
            try:
                result = conn.execute_command(*args, **kwargs)
                self._stats["successful_requests"] += 1
                return result
            except Exception as e:
                self._stats["failed_requests"] += 1
                logger.error(f"Redis command failed: {e}")
                raise

    def get(self, key: str) -> Any:
        """Get a value from Redis"""
        return self.execute_command("GET", key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in Redis"""
        if ttl:
            return bool(self.execute_command("SETEX", key, ttl, value))
        return bool(self.execute_command("SET", key, value))

    def delete(self, key: str) -> bool:
        """Delete a key from Redis"""
        return bool(self.execute_command("DEL", key))

    def exists(self, key: str) -> bool:
        """Check if key exists"""
        return bool(self.execute_command("EXISTS", key))

    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern"""
        return self.execute_command("KEYS", pattern)

    def ping(self) -> bool:
        """Ping Redis"""
        return bool(self.execute_command("PING"))

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        with self._lock:
            info = self.execute_command("INFO")
            return {
                **self._stats,
                "max_connections": self.config.max_connections,
                "queue_size": self._pool.qsize(),
                "redis_info": info
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
            
            # Close connection pool
            self._connection_pool.close()


class AsyncRedisConnectionPool:
    """Async Redis connection pool for aioredis"""

    def __init__(self, config: Optional[RedisPoolConfig] = None):
        self.config = config or RedisPoolConfig()
        self._pool: asyncio.Queue = asyncio.Queue(maxsize=self.config.max_connections)
        self._active_connections: Set = set()
        self._lock = asyncio.Lock()
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "active_connections": 0,
            "queued_connections": 0
        }
        self._redis: Optional[aioredis.Redis] = None
        
        # Initialize pool
        asyncio.create_task(self._initialize_pool())

    async def _initialize_pool(self) -> None:
        """Initialize pool with connections"""
        for _ in range(min(self.config.max_connections, 10)):
            await self._create_connection()

    async def _create_connection(self) -> aioredis.Redis:
        """Create a new async Redis connection"""
        return await aioredis.create_redis_pool(
            (self.config.host, self.config.port),
            db=self.config.db,
            password=self.config.password,
            minsize=1,
            maxsize=self.config.max_connections,
            socket_timeout=self.config.socket_timeout,
            socket_connect_timeout=self.config.socket_connect_timeout,
            ssl=self.config.ssl,
            encoding="utf-8"
        )

    async def get_connection(self) -> aioredis.Redis:
        """Get a connection from the pool"""
        async with self._lock:
            self._stats["queued_connections"] += 1
        
        try:
            # Try to get from queue
            connection = await asyncio.wait_for(
                self._pool.get(),
                timeout=5.0
            )
            
            async with self._lock:
                # Test connection
                try:
                    await connection.ping()
                except Exception:
                    # Connection is bad, close it and create new
                    await connection.close()
                    connection = await self._create_connection()
                
                self._active_connections.add(connection)
                self._stats["queued_connections"] -= 1
                self._stats["active_connections"] = len(self._active_connections)
            
            return connection
        except asyncio.TimeoutError:
            # Create new connection
            connection = await self._create_connection()
            async with self._lock:
                self._active_connections.add(connection)
                self._stats["active_connections"] = len(self._active_connections)
            return connection

    async def release_connection(self, connection: aioredis.Redis) -> None:
        """Release a connection back to the pool"""
        async with self._lock:
            if connection in self._active_connections:
                self._active_connections.remove(connection)
                self._stats["active_connections"] = len(self._active_connections)
                
                # Put back in queue if pool is not full
                if self._pool.qsize() < self.config.max_connections:
                    await self._pool.put(connection)
                else:
                    # Close connection
                    await connection.close()

    @asynccontextmanager
    async def connection(self) -> aioredis.Redis:
        """Async context manager for connection"""
        conn = await self.get_connection()
        try:
            yield conn
        except Exception as e:
            self._stats["failed_requests"] += 1
            logger.error(f"Async Redis error: {e}")
            raise
        finally:
            await self.release_connection(conn)

    async def execute_command(self, *args, **kwargs) -> Any:
        """Execute a Redis command"""
        async with self.connection() as conn:
            self._stats["total_requests"] += 1
            
            try:
                result = await conn.execute(*args, **kwargs)
                self._stats["successful_requests"] += 1
                return result
            except Exception as e:
                self._stats["failed_requests"] += 1
                logger.error(f"Async Redis command failed: {e}")
                raise

    async def get(self, key: str) -> Any:
        """Get a value from Redis"""
        return await self.execute_command("GET", key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in Redis"""
        if ttl:
            return bool(await self.execute_command("SETEX", key, ttl, value))
        return bool(await self.execute_command("SET", key, value))

    async def delete(self, key: str) -> bool:
        """Delete a key from Redis"""
        return bool(await self.execute_command("DEL", key))

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        return bool(await self.execute_command("EXISTS", key))

    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern"""
        return await self.execute_command("KEYS", pattern)

    async def ping(self) -> bool:
        """Ping Redis"""
        return bool(await self.execute_command("PING"))

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        return {
            **self._stats,
            "max_connections": self.config.max_connections,
            "queue_size": self._pool.qsize()
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


def create_redis_pool(config: Optional[RedisPoolConfig] = None) -> RedisConnectionPool:
    """Create a Redis connection pool"""
    return RedisConnectionPool(config)


def create_async_redis_pool(config: Optional[RedisPoolConfig] = None) -> AsyncRedisConnectionPool:
    """Create an async Redis connection pool"""
    return AsyncRedisConnectionPool(config)
