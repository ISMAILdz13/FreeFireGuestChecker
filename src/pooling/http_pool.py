"""
HTTP Connection Pool for Free Fire Guest Account Checker
Manages a pool of HTTP connections for better performance
"""

from __future__ import annotations

import asyncio
import ssl
import threading
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from queue import Queue
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import aiohttp
import httpx
import requests

from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class HTTPPoolConfig:
    """HTTP connection pool configuration"""
    max_connections: int = 100
    max_keepalive_connections: int = 20
    keepalive_timeout: float = 60.0
    connect_timeout: float = 10.0
    read_timeout: float = 30.0
    write_timeout: float = 30.0
    pool_timeout: float = 30.0
    retry_total: int = 3
    retry_backoff_factor: float = 0.5
    
    # SSL/TLS configuration
    ssl_verify: bool = True
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None
    
    # Proxy configuration
    proxy_url: Optional[str] = None
    proxy_auth: Optional[Tuple[str, str]] = None
    
    # Headers
    default_headers: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> HTTPPoolConfig:
        """Create from dictionary"""
        return cls(
            max_connections=data.get("max_connections", 100),
            max_keepalive_connections=data.get("max_keepalive_connections", 20),
            keepalive_timeout=data.get("keepalive_timeout", 60.0),
            connect_timeout=data.get("connect_timeout", 10.0),
            read_timeout=data.get("read_timeout", 30.0),
            write_timeout=data.get("write_timeout", 30.0),
            pool_timeout=data.get("pool_timeout", 30.0),
            retry_total=data.get("retry_total", 3),
            retry_backoff_factor=data.get("retry_backoff_factor", 0.5),
            ssl_verify=data.get("ssl_verify", True),
            ssl_cert=data.get("ssl_cert"),
            ssl_key=data.get("ssl_key"),
            proxy_url=data.get("proxy_url"),
            proxy_auth=data.get("proxy_auth"),
            default_headers=data.get("default_headers", {})
        )


class HTTPConnectionPool:
    """HTTP connection pool for synchronous requests"""

    def __init__(self, config: Optional[HTTPPoolConfig] = None):
        self.config = config or HTTPPoolConfig()
        self._pool: Queue = Queue(maxsize=self.config.max_connections)
        self._active_connections: Set = set()
        self._lock = threading.Lock()
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "active_connections": 0,
            "queued_requests": 0
        }
        
        # Initialize pool with connections
        for _ in range(min(self.config.max_keepalive_connections, self.config.max_connections)):
            self._create_connection()

    def _create_connection(self) -> requests.Session:
        """Create a new HTTP session"""
        session = requests.Session()
        
        # Configure timeouts
        session.connect_timeout = self.config.connect_timeout
        session.read_timeout = self.config.read_timeout
        
        # Configure pool
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=self.config.max_connections,
            pool_maxsize=self.config.max_connections,
            max_retries=self._create_retry_config()
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Configure SSL
        if not self.config.ssl_verify:
            session.verify = False
        elif self.config.ssl_cert and self.config.ssl_key:
            session.cert = (self.config.ssl_cert, self.config.ssl_key)
        
        # Configure proxy
        if self.config.proxy_url:
            session.proxies = {
                "http": self.config.proxy_url,
                "https": self.config.proxy_url
            }
            if self.config.proxy_auth:
                session.auth = self.config.proxy_auth
        
        # Set default headers
        session.headers.update(self.config.default_headers)
        
        return session

    def _create_retry_config(self) -> requests.packages.urllib3.util.Retry:
        """Create retry configuration"""
        from requests.packages.urllib3.util.retry import Retry
        
        return Retry(
            total=self.config.retry_total,
            backoff_factor=self.config.retry_backoff_factor,
            status_forcelist=[408, 429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"]
        )

    def get_connection(self) -> requests.Session:
        """Get a connection from the pool"""
        with self._lock:
            self._stats["queued_requests"] += 1
        
        try:
            # Try to get from queue
            connection = self._pool.get(timeout=self.config.pool_timeout)
            
            with self._lock:
                self._active_connections.add(connection)
                self._stats["queued_requests"] -= 1
                self._stats["active_connections"] = len(self._active_connections)
            
            return connection
        except Exception:
            # Create new connection if queue is empty
            connection = self._create_connection()
            with self._lock:
                self._active_connections.add(connection)
                self._stats["active_connections"] = len(self._active_connections)
            return connection

    def release_connection(self, connection: requests.Session) -> None:
        """Release a connection back to the pool"""
        with self._lock:
            if connection in self._active_connections:
                self._active_connections.remove(connection)
                self._stats["active_connections"] = len(self._active_connections)
                
                # Put back in queue if pool is not full
                if self._pool.qsize() < self.config.max_keepalive_connections:
                    self._pool.put(connection)
                else:
                    # Close connection if pool is full
                    connection.close()

    @contextmanager
    def connection(self) -> requests.Session:
        """Context manager for connection"""
        conn = self.get_connection()
        try:
            yield conn
        finally:
            self.release_connection(conn)

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make an HTTP request"""
        with self.connection() as conn:
            self._stats["total_requests"] += 1
            
            try:
                response = conn.request(method, url, **kwargs)
                self._stats["successful_requests"] += 1
                return response
            except Exception as e:
                self._stats["failed_requests"] += 1
                logger.error(f"HTTP request failed: {e}")
                raise

    def get(self, url: str, **kwargs) -> requests.Response:
        """Make a GET request"""
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        """Make a POST request"""
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs) -> requests.Response:
        """Make a PUT request"""
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs) -> requests.Response:
        """Make a DELETE request"""
        return self.request("DELETE", url, **kwargs)

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        with self._lock:
            return {
                **self._stats,
                "max_connections": self.config.max_connections,
                "max_keepalive": self.config.max_keepalive_connections,
                "queue_size": self._pool.qsize()
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


class AsyncHTTPConnectionPool:
    """Async HTTP connection pool for aiohttp"""

    def __init__(self, config: Optional[HTTPPoolConfig] = None):
        self.config = config or HTTPPoolConfig()
        self._session: Optional[aiohttp.ClientSession] = None
        self._lock = asyncio.Lock()
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "active_connections": 0
        }

    async def _create_session(self) -> aiohttp.ClientSession:
        """Create a new async HTTP session"""
        # Configure SSL context if needed
        ssl_context = None
        if not self.config.ssl_verify:
            ssl_context = False
        elif self.config.ssl_cert and self.config.ssl_key:
            ssl_context = ssl.create_default_context(
                ssl.Purpose.SERVER_AUTH,
                cafile=self.config.ssl_cert,
                capath=None,
                cadata=None
            )
        
        # Configure connector
        connector = aiohttp.TCPConnector(
            limit=self.config.max_connections,
            limit_per_host=0,
            ssl=ssl_context,
            keepalive_timeout=self.config.keepalive_timeout
        )
        
        # Configure timeout
        timeout = aiohttp.ClientTimeout(
            total=self.config.pool_timeout,
            connect=self.config.connect_timeout,
            sock_connect=self.config.connect_timeout,
            sock_read=self.config.read_timeout
        )
        
        # Create session
        session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.config.default_headers,
            auto_decompress=True
        )
        
        return session

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create session"""
        if self._session is None or self._session.closed:
            async with self._lock:
                if self._session is None or self._session.closed:
                    self._session = await self._create_session()
        return self._session

    async def request(self, method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make an async HTTP request"""
        session = await self.get_session()
        self._stats["total_requests"] += 1
        
        try:
            response = await session.request(method, url, **kwargs)
            self._stats["successful_requests"] += 1
            return response
        except Exception as e:
            self._stats["failed_requests"] += 1
            logger.error(f"Async HTTP request failed: {e}")
            raise

    async def get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make an async GET request"""
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make an async POST request"""
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make an async PUT request"""
        return await self.request("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make an async DELETE request"""
        return await self.request("DELETE", url, **kwargs)

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        return {
            **self._stats,
            "max_connections": self.config.max_connections,
            "is_closed": self._session.closed if self._session else True
        }

    async def close(self) -> None:
        """Close the session"""
        if self._session and not self._session.closed:
            await self._session.close()

    @asynccontextmanager
    async def session(self) -> aiohttp.ClientSession:
        """Async context manager for session"""
        session = await self.get_session()
        try:
            yield session
        finally:
            pass  # Session is managed by the pool


class HttpxConnectionPool:
    """HTTP connection pool using httpx"""

    def __init__(self, config: Optional[HTTPPoolConfig] = None):
        self.config = config or HTTPPoolConfig()
        self._client: Optional[httpx.Client] = None
        self._lock = threading.Lock()
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0
        }

    def _create_client(self) -> httpx.Client:
        """Create a new httpx client"""
        # Configure limits
        limits = httpx.Limits(
            max_keepalive_connections=self.config.max_keepalive_connections,
            max_connections=self.config.max_connections,
            keepalive_expiry=self.config.keepalive_timeout
        )
        
        # Configure timeout
        timeout = httpx.Timeout(
            self.config.pool_timeout,
            connect=self.config.connect_timeout,
            read=self.config.read_timeout,
            write=self.config.write_timeout
        )
        
        # Configure SSL
        verify = self.config.ssl_verify
        cert = None
        if self.config.ssl_cert and self.config.ssl_key:
            cert = (self.config.ssl_cert, self.config.ssl_key)
        
        # Configure proxy
        proxies = None
        if self.config.proxy_url:
            proxies = {
                "http://": self.config.proxy_url,
                "https://": self.config.proxy_url
            }
        
        # Create client
        client = httpx.Client(
            limits=limits,
            timeout=timeout,
            verify=verify,
            cert=cert,
            proxies=proxies,
            headers=self.config.default_headers
        )
        
        return client

    def get_client(self) -> httpx.Client:
        """Get or create client"""
        if self._client is None:
            with self._lock:
                if self._client is None:
                    self._client = self._create_client()
        return self._client

    def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make an HTTP request"""
        client = self.get_client()
        self._stats["total_requests"] += 1
        
        try:
            response = client.request(method, url, **kwargs)
            self._stats["successful_requests"] += 1
            return response
        except Exception as e:
            self._stats["failed_requests"] += 1
            logger.error(f"Httpx request failed: {e}")
            raise

    def get(self, url: str, **kwargs) -> httpx.Response:
        """Make a GET request"""
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> httpx.Response:
        """Make a POST request"""
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs) -> httpx.Response:
        """Make a PUT request"""
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs) -> httpx.Response:
        """Make a DELETE request"""
        return self.request("DELETE", url, **kwargs)

    @contextmanager
    def client(self) -> httpx.Client:
        """Context manager for client"""
        client = self.get_client()
        try:
            yield client
        finally:
            pass  # Client is managed by the pool

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        return {
            **self._stats,
            "max_connections": self.config.max_connections,
            "active_connections": len(self._client._connection_pool._connections) if self._client else 0
        }

    def close(self) -> None:
        """Close the client"""
        if self._client:
            self._client.close()
            self._client = None


def create_http_pool(config: Optional[HTTPPoolConfig] = None) -> HTTPConnectionPool:
    """Create an HTTP connection pool"""
    return HTTPConnectionPool(config)


def create_async_http_pool(config: Optional[HTTPPoolConfig] = None) -> AsyncHTTPConnectionPool:
    """Create an async HTTP connection pool"""
    return AsyncHTTPConnectionPool(config)


def create_httpx_pool(config: Optional[HTTPPoolConfig] = None) -> HttpxConnectionPool:
    """Create an httpx connection pool"""
    return HttpxConnectionPool(config)
