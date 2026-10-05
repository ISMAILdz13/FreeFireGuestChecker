"""
Rate Limiter for Free Fire Guest Account Checker
Implements token bucket and sliding window rate limiting
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    max_requests: int = 100
    window_seconds: float = 60.0
    burst_requests: int = 10
    burst_seconds: float = 1.0
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RateLimitConfig:
        """Create from dictionary"""
        return cls(
            max_requests=data.get("max_requests", 100),
            window_seconds=data.get("window_seconds", 60.0),
            burst_requests=data.get("burst_requests", 10),
            burst_seconds=data.get("burst_seconds", 1.0)
        )


@dataclass
class RateLimitResult:
    """Result of a rate limit check"""
    allowed: bool
    remaining: int = 0
    reset_in: float = 0.0
    limit: int = 0
    retry_after: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "allowed": self.allowed,
            "remaining": self.remaining,
            "reset_in": self.reset_in,
            "limit": self.limit,
            "retry_after": self.retry_after
        }
    
    def to_headers(self) -> Dict[str, str]:
        """Convert to HTTP headers"""
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining),
            "X-RateLimit-Reset": str(int(self.reset_in))
        }
        
        if self.retry_after:
            headers["Retry-After"] = str(int(self.retry_after))
        
        return headers


class TokenBucket:
    """Token bucket rate limiter"""

    def __init__(self, max_tokens: int = 100, refill_rate: float = 1.0):
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate  # tokens per second
        self.tokens = max_tokens
        self.last_refill = time.time()
        self._lock = threading.Lock()

    def consume(self, tokens: int = 1) -> bool:
        """Consume tokens from the bucket"""
        with self._lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def available(self) -> int:
        """Get available tokens"""
        with self._lock:
            self._refill()
            return self.tokens

    def _refill(self) -> None:
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill
        
        if elapsed > 0:
            new_tokens = elapsed * self.refill_rate
            self.tokens = min(self.max_tokens, self.tokens + new_tokens)
            self.last_refill = now

    def wait(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """Wait until tokens are available"""
        start_time = time.time()
        
        while True:
            with self._lock:
                self._refill()
                
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
                
                if timeout and (time.time() - start_time) >= timeout:
                    return False
            
            # Calculate wait time
            needed = tokens - self.tokens
            wait_time = needed / self.refill_rate
            
            time.sleep(min(wait_time, 0.1))


class SlidingWindow:
    """Sliding window rate limiter"""

    def __init__(self, max_requests: int = 100, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.timestamps: deque = deque()
        self._lock = threading.Lock()

    def add_request(self) -> bool:
        """Add a request to the window"""
        with self._lock:
            now = time.time()
            
            # Remove old requests
            while self.timestamps and (now - self.timestamps[0]) > self.window_seconds:
                self.timestamps.popleft()
            
            # Check if we can add more
            if len(self.timestamps) < self.max_requests:
                self.timestamps.append(now)
                return True
            return False

    def get_count(self) -> int:
        """Get current request count in window"""
        with self._lock:
            now = time.time()
            
            # Remove old requests
            while self.timestamps and (now - self.timestamps[0]) > self.window_seconds:
                self.timestamps.popleft()
            
            return len(self.timestamps)

    def get_remaining(self) -> int:
        """Get remaining requests in window"""
        return max(0, self.max_requests - self.get_count())

    def get_reset_time(self) -> float:
        """Get time until window resets"""
        with self._lock:
            if not self.timestamps:
                return 0.0
            
            oldest = self.timestamps[0]
            now = time.time()
            elapsed = now - oldest
            
            if elapsed >= self.window_seconds:
                return 0.0
            return self.window_seconds - elapsed

    def wait(self, timeout: Optional[float] = None) -> bool:
        """Wait until a request can be made"""
        start_time = time.time()
        
        while True:
            with self._lock:
                now = time.time()
                
                # Remove old requests
                while self.timestamps and (now - self.timestamps[0]) > self.window_seconds:
                    self.timestamps.popleft()
                
                if len(self.timestamps) < self.max_requests:
                    self.timestamps.append(now)
                    return True
                
                if timeout and (time.time() - start_time) >= timeout:
                    return False
            
            # Calculate wait time
            oldest = self.timestamps[0] if self.timestamps else 0
            wait_time = (oldest + self.window_seconds) - time.time()
            
            time.sleep(min(wait_time, 0.1))


class RateLimiter:
    """Combined rate limiter with token bucket and sliding window"""

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.bucket = TokenBucket(
            max_tokens=self.config.max_requests,
            refill_rate=self.config.max_requests / self.config.window_seconds
        )
        self.window = SlidingWindow(
            max_requests=self.config.max_requests,
            window_seconds=self.config.window_seconds
        )
        self.burst_bucket = TokenBucket(
            max_tokens=self.config.burst_requests,
            refill_rate=self.config.burst_requests / self.config.burst_seconds
        )
        
        # Per-key rate limiting
        self._key_limits: Dict[str, RateLimiter] = {}
        self._key_lock = threading.Lock()

    def check(self, key: Optional[str] = None) -> RateLimitResult:
        """Check if request is allowed"""
        # Check global rate limit
        bucket_allowed = self.bucket.consume()
        window_allowed = self.window.add_request()
        burst_allowed = self.burst_bucket.consume()
        
        allowed = bucket_allowed and window_allowed and burst_allowed
        
        # Check per-key rate limit
        if key:
            key_limiter = self._get_key_limiter(key)
            key_result = key_limiter.check()
            allowed = allowed and key_result.allowed
        
        remaining = min(
            self.bucket.available(),
            self.window.get_remaining(),
            self.burst_bucket.available()
        )
        
        reset_in = max(
            self.window.get_reset_time(),
            self.burst_bucket.get_reset_time()
        )
        
        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_in=reset_in,
            limit=self.config.max_requests,
            retry_after=None if allowed else reset_in
        )

    def acquire(self, key: Optional[str] = None, timeout: Optional[float] = None) -> bool:
        """Acquire permission to make a request"""
        # Try to consume from all limiters
        bucket_ok = self.bucket.wait(timeout=timeout)
        if not bucket_ok:
            return False
        
        window_ok = self.window.wait(timeout=timeout)
        if not window_ok:
            # Return token to bucket if we got it
            self.bucket.tokens += 1
            return False
        
        burst_ok = self.burst_bucket.wait(timeout=timeout)
        if not burst_ok:
            # Return tokens
            self.bucket.tokens += 1
            # Can't easily return window request, so just fail
            return False
        
        # Check per-key limit
        if key:
            key_limiter = self._get_key_limiter(key)
            key_ok = key_limiter.acquire(timeout=timeout)
            if not key_ok:
                # Return all tokens
                self.bucket.tokens += 1
                return False
        
        return True

    def _get_key_limiter(self, key: str) -> RateLimiter:
        """Get or create a rate limiter for a specific key"""
        with self._key_lock:
            if key not in self._key_limits:
                # Use a separate config for per-key limits
                key_config = RateLimitConfig(
                    max_requests=10,
                    window_seconds=1.0,
                    burst_requests=5,
                    burst_seconds=0.1
                )
                self._key_limits[key] = RateLimiter(key_config)
            return self._key_limits[key]

    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        return {
            "bucket": {
                "available": self.bucket.available(),
                "max": self.bucket.max_tokens,
                "refill_rate": self.bucket.refill_rate
            },
            "window": {
                "count": self.window.get_count(),
                "max": self.window.max_requests,
                "reset_in": self.window.get_reset_time()
            },
            "burst": {
                "available": self.burst_bucket.available(),
                "max": self.burst_bucket.max_tokens
            },
            "key_limits": len(self._key_limits)
        }

    def reset(self) -> None:
        """Reset all rate limits"""
        self.bucket.tokens = self.bucket.max_tokens
        self.bucket.last_refill = time.time()
        self.window.timestamps.clear()
        self.burst_bucket.tokens = self.burst_bucket.max_tokens
        self.burst_bucket.last_refill = time.time()
        
        with self._key_lock:
            for limiter in self._key_limits.values():
                limiter.reset()
            self._key_limits.clear()


class AsyncRateLimiter:
    """Async rate limiter"""

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.bucket = TokenBucket(
            max_tokens=self.config.max_requests,
            refill_rate=self.config.max_requests / self.config.window_seconds
        )
        self.window = SlidingWindow(
            max_requests=self.config.max_requests,
            window_seconds=self.config.window_seconds
        )
        self._lock = asyncio.Lock()
        
        # Per-key rate limiting
        self._key_limits: Dict[str, AsyncRateLimiter] = {}

    async def check(self, key: Optional[str] = None) -> RateLimitResult:
        """Check if request is allowed"""
        async with self._lock:
            # Check global rate limit
            bucket_allowed = self.bucket.consume()
            window_allowed = self.window.add_request()
            
            allowed = bucket_allowed and window_allowed
            
            # Check per-key rate limit
            if key:
                key_limiter = await self._get_key_limiter(key)
                key_result = await key_limiter.check()
                allowed = allowed and key_result.allowed
            
            remaining = min(
                self.bucket.available(),
                self.window.get_remaining()
            )
            
            reset_in = self.window.get_reset_time()
            
            return RateLimitResult(
                allowed=allowed,
                remaining=remaining,
                reset_in=reset_in,
                limit=self.config.max_requests,
                retry_after=None if allowed else reset_in
            )

    async def acquire(self, key: Optional[str] = None, timeout: Optional[float] = None) -> bool:
        """Acquire permission to make a request"""
        start_time = time.time()
        
        while True:
            result = await self.check(key)
            
            if result.allowed:
                return True
            
            if timeout and (time.time() - start_time) >= timeout:
                return False
            
            if result.retry_after:
                await asyncio.sleep(min(result.retry_after, 0.1))
            else:
                await asyncio.sleep(0.1)

    async def _get_key_limiter(self, key: str) -> AsyncRateLimiter:
        """Get or create a rate limiter for a specific key"""
        if key not in self._key_limits:
            key_config = RateLimitConfig(
                max_requests=10,
                window_seconds=1.0
            )
            self._key_limits[key] = AsyncRateLimiter(key_config)
        return self._key_limits[key]

    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        return {
            "bucket": {
                "available": self.bucket.available(),
                "max": self.bucket.max_tokens,
                "refill_rate": self.bucket.refill_rate
            },
            "window": {
                "count": self.window.get_count(),
                "max": self.window.max_requests,
                "reset_in": self.window.get_reset_time()
            },
            "key_limits": len(self._key_limits)
        }


# Global RateLimiter instance
_rate_limiter: Optional[RateLimiter] = None


def create_rate_limiter(config: Optional[RateLimitConfig] = None) -> RateLimiter:
    """Create a rate limiter"""
    return RateLimiter(config)


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
