"""
Network Utilities Module
Handles HTTP client creation, proxy management, and connectivity checks.
"""

import os
import re
import time
import asyncio
import logging
import socket
import httpx
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urlparse

from ..config import config_manager
from .helpers import retry_async

logger = logging.getLogger(__name__)


class NetworkError(Exception):
    """Custom exception for network errors."""
    pass


class ProxyError(Exception):
    """Custom exception for proxy errors."""
    pass


def get_proxy_url(proxy_config: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    Build proxy URL from configuration.
    
    Args:
        proxy_config: Proxy configuration dictionary
        
    Returns:
        Proxy URL string or None
    """
    if proxy_config is None:
        settings = config_manager.get()
        proxy_config = {
            "enabled": settings.proxy.enabled,
            "proxy_type": settings.proxy.proxy_type.value,
            "host": settings.proxy.host,
            "port": settings.proxy.port,
            "username": settings.proxy.username,
            "password": settings.proxy.password,
        }
    
    if not proxy_config.get("enabled") or not proxy_config.get("host"):
        return None
    
    proxy_type = proxy_config.get("proxy_type", "http")
    host = proxy_config.get("host")
    port = proxy_config.get("port", 0)
    username = proxy_config.get("username", "")
    password = proxy_config.get("password", "")
    
    # Build proxy URL
    if username and password:
        auth = f"{username}:{password}@"
    else:
        auth = ""
    
    if port:
        proxy_url = f"{proxy_type}://{auth}{host}:{port}"
    else:
        proxy_url = f"{proxy_type}://{auth}{host}"
    
    return proxy_url


def validate_proxy_config(proxy_config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate proxy configuration.
    
    Args:
        proxy_config: Proxy configuration dictionary
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not proxy_config.get("enabled"):
        return True, "Proxy disabled"
    
    if not proxy_config.get("host"):
        return False, "Proxy host is required"
    
    proxy_type = proxy_config.get("proxy_type", "http").lower()
    if proxy_type not in ("http", "https", "socks4", "socks5"):
        return False, f"Invalid proxy type: {proxy_type}"
    
    port = proxy_config.get("port", 0)
    if port and (port < 1 or port > 65535):
        return False, "Proxy port must be between 1 and 65535"
    
    return True, "Valid"


async def check_proxy_connectivity(proxy_url: str, timeout: float = 5.0) -> bool:
    """
    Check if a proxy is working.
    
    Args:
        proxy_url: Proxy URL to test
        timeout: Timeout in seconds
        
    Returns:
        True if proxy is working, False otherwise
    """
    try:
        # Parse proxy URL
        parsed = urlparse(proxy_url)
        proxy_type = parsed.scheme
        host = parsed.hostname
        port = parsed.port or (443 if proxy_type == "https" else 80)
        
        # Test with a simple HTTP request
        test_url = "https://httpbin.org/ip"
        
        proxy_dict = {
            "http://": proxy_url,
            "https://": proxy_url,
        }
        
        async with httpx.AsyncClient(
            proxy=proxy_url,
            timeout=timeout,
        ) as client:
            response = await client.get(test_url, timeout=timeout)
            if response.status_code == 200:
                logger.info(f"Proxy {proxy_url} is working")
                return True
            else:
                logger.warning(f"Proxy {proxy_url} returned status {response.status_code}")
                return False
                
    except httpx.ProxyError as e:
        logger.error(f"Proxy error: {e}")
        return False
    except httpx.ConnectTimeout:
        logger.error(f"Proxy connection timeout: {proxy_url}")
        return False
    except Exception as e:
        logger.error(f"Proxy check failed: {e}")
        return False


async def check_connectivity(url: str = "https://www.google.com", 
                           timeout: float = 5.0) -> Tuple[bool, float]:
    """
    Check internet connectivity.
    
    Args:
        url: URL to test connectivity
        timeout: Timeout in seconds
        
    Returns:
        Tuple of (is_connected, response_time)
    """
    start_time = time.time()
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, timeout=timeout)
            elapsed = time.time() - start_time
            
            if response.status_code < 400:
                logger.debug(f"Connectivity check passed ({elapsed:.2f}s)")
                return True, elapsed
            else:
                logger.warning(f"Connectivity check failed: status {response.status_code}")
                return False, elapsed
                
    except httpx.ConnectTimeout:
        logger.warning(f"Connectivity check timeout after {timeout}s")
        return False, timeout
    except Exception as e:
        logger.error(f"Connectivity check failed: {e}")
        return False, time.time() - start_time


async def validate_endpoint(url: str, timeout: float = 5.0) -> Tuple[bool, str]:
    """
    Validate if an endpoint is accessible.
    
    Args:
        url: Endpoint URL to validate
        timeout: Timeout in seconds
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, timeout=timeout)
            
            if response.status_code < 400:
                return True, "OK"
            else:
                return False, f"HTTP {response.status_code}"
                
    except httpx.ConnectTimeout:
        return False, "Connection timeout"
    except httpx.ReadTimeout:
        return False, "Read timeout"
    except httpx.ConnectError as e:
        return False, f"Connection error: {e}"
    except Exception as e:
        return False, str(e)


async def get_public_ip(proxy_url: Optional[str] = None) -> Optional[str]:
    """
    Get the public IP address.
    
    Args:
        proxy_url: Optional proxy URL to use
        
    Returns:
        Public IP address or None
    """
    ip_services = [
        "https://api.ipify.org",
        "https://icanhazip.com",
        "https://ifconfig.me/ip",
    ]
    
    for service in ip_services:
        try:
            proxy_dict = None
            if proxy_url:
                proxy_dict = proxy_url
            
            async with httpx.AsyncClient(
                proxy=proxy_dict,
                timeout=5.0,
            ) as client:
                response = await client.get(service, timeout=5.0)
                if response.status_code == 200:
                    ip = response.text.strip()
                    if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
                        return ip
        except Exception as e:
            logger.debug(f"Failed to get IP from {service}: {e}")
            continue
    
    return None


class ProxyRotator:
    """
    Manages proxy rotation for avoiding rate limits.
    """
    
    def __init__(self, proxy_list: List[str] = None):
        self.proxy_list = proxy_list or []
        self.current_index = 0
        self.failed_proxies: List[str] = []
        self._lock = asyncio.Lock()
        
    def add_proxy(self, proxy_url: str) -> None:
        """Add a proxy to the rotation list."""
        if proxy_url not in self.proxy_list:
            self.proxy_list.append(proxy_url)
            
    def remove_proxy(self, proxy_url: str) -> bool:
        """Remove a proxy from the rotation list."""
        if proxy_url in self.proxy_list:
            self.proxy_list.remove(proxy_url)
            return True
        return False
    
    async def get_next_proxy(self) -> Optional[str]:
        """
        Get the next proxy in rotation.
        
        Returns:
            Next proxy URL or None if no proxies available
        """
        async with self._lock:
            if not self.proxy_list:
                return None
            
            # Try to get a working proxy
            for _ in range(len(self.proxy_list)):
                proxy = self.proxy_list[self.current_index]
                self.current_index = (self.current_index + 1) % len(self.proxy_list)
                
                if proxy not in self.failed_proxies:
                    # Quick check if proxy is working
                    if await self._quick_check(proxy):
                        return proxy
                    else:
                        self.failed_proxies.append(proxy)
            
            # All proxies failed, reset and try again
            self.failed_proxies.clear()
            return self.proxy_list[0] if self.proxy_list else None
    
    async def _quick_check(self, proxy_url: str) -> bool:
        """Quick check if proxy is responsive."""
        try:
            async with httpx.AsyncClient(
                proxy=proxy_url,
                timeout=2.0,
            ) as client:
                response = await client.get("https://httpbin.org/ip", timeout=2.0)
                return response.status_code == 200
        except Exception:
            return False
    
    def mark_proxy_failed(self, proxy_url: str) -> None:
        """Mark a proxy as failed."""
        if proxy_url not in self.failed_proxies:
            self.failed_proxies.append(proxy_url)
    
    def reset_failed_proxies(self) -> None:
        """Reset the list of failed proxies."""
        self.failed_proxies.clear()
    
    def get_proxy_count(self) -> int:
        """Get the number of available proxies."""
        return len(self.proxy_list)


def create_http_client(
    proxy_url: Optional[str] = None,
    timeout: float = 30.0,
    verify_ssl: bool = False,
    follow_redirects: bool = True,
    headers: Optional[Dict[str, str]] = None,
    retry_enabled: bool = True,
) -> httpx.AsyncClient:
    """
    Create an HTTPX async client with common configuration.
    
    Args:
        proxy_url: Optional proxy URL
        timeout: Request timeout in seconds
        verify_ssl: Whether to verify SSL certificates
        follow_redirects: Whether to follow redirects
        headers: Custom headers to include
        retry_enabled: Whether to enable automatic retries
        
    Returns:
        Configured HTTPX async client
    """
    # Default headers
    default_headers = {
        "User-Agent": "GarenaMSDK/4.0.19P10(I2404 ;Android 15;en;US;)",
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "Keep-Alive",
    }
    
    if headers:
        default_headers.update(headers)
    
    # Build transport with proxy if provided
    transport_kwargs = {
        "verify": verify_ssl,
        "follow_redirects": follow_redirects,
    }
    
    if proxy_url:
        transport_kwargs["proxy"] = proxy_url
    
    # Create client
    client = httpx.AsyncClient(
        headers=default_headers,
        timeout=timeout,
        **transport_kwargs,
    )
    
    return client


class HTTPClientManager:
    """
    Manages HTTP clients with connection pooling and retry logic.
    """
    
    def __init__(self, 
                 max_clients: int = 10,
                 base_timeout: float = 30.0,
                 retry_attempts: int = 3):
        self.max_clients = max_clients
        self.base_timeout = base_timeout
        self.retry_attempts = retry_attempts
        self._clients: List[httpx.AsyncClient] = []
        self._proxy_rotator: Optional[ProxyRotator] = None
        
    def set_proxy_rotator(self, proxy_rotator: ProxyRotator) -> None:
        """Set a proxy rotator for this manager."""
        self._proxy_rotator = proxy_rotator
        
    async def get_client(self) -> httpx.AsyncClient:
        """
        Get an HTTP client from the pool.
        
        Returns:
            HTTPX async client
        """
        if self._clients:
            # Reuse existing client
            return self._clients[0]
        
        # Create new client
        proxy_url = None
        if self._proxy_rotator:
            proxy_url = await self._proxy_rotator.get_next_proxy()
        
        client = create_http_client(
            proxy_url=proxy_url,
            timeout=self.base_timeout,
            verify_ssl=False,
            follow_redirects=True,
        )
        self._clients.append(client)
        return client
    
    async def request(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> Optional[httpx.Response]:
        """
        Make an HTTP request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional arguments for HTTPX
            
        Returns:
            HTTPX response or None if all retries fail
        """
        client = await self.get_client()
        
        for attempt in range(self.retry_attempts):
            try:
                response = await client.request(method, url, **kwargs)
                
                # Check for rate limiting
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After", 5)
                    logger.warning(f"Rate limited. Retrying after {retry_after} seconds")
                    await asyncio.sleep(float(retry_after))
                    continue
                
                # Check for server errors that might be retried
                if response.status_code >= 500 and attempt < self.retry_attempts - 1:
                    delay = 2 ** attempt
                    logger.warning(f"Server error {response.status_code}. Retrying in {delay}s")
                    await asyncio.sleep(delay)
                    continue
                
                return response
                
            except httpx.ConnectError as e:
                logger.warning(f"Connection error on attempt {attempt + 1}: {e}")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.error(f"All {self.retry_attempts} connection attempts failed")
                    return None
                    
            except httpx.TimeoutException as e:
                logger.warning(f"Timeout on attempt {attempt + 1}: {e}")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.error(f"All {self.retry_attempts} timeout attempts failed")
                    return None
                    
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return None
        
        return None
    
    async def close_all(self) -> None:
        """Close all HTTP clients."""
        for client in self._clients:
            try:
                await client.aclose()
            except Exception as e:
                logger.error(f"Error closing client: {e}")
        self._clients.clear()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_all()


# Global HTTP client manager
http_client_manager = HTTPClientManager()
