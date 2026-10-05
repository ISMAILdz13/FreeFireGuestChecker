"""
TTL Cache Implementation for Free Fire Guest Account Checker
Time-to-Live cache with automatic expiration
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from heapq import heappop, heappush
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar, Union

from src.cache.lru_cache import CacheStats
from src.utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """Cache entry with TTL"""
    value: T
    expires_at: float
    created_at: float = field(default_factory=time.time)
    
    def is_expired(self) -> bool:
        """Check if entry has expired"""
        return time.time() > self.expires_at


class TTLCache(Generic[T]):
    """Thread-safe TTL cache implementation"""

    def __init__(self, max_size: int = 1000, default_ttl: float = 300.0):
        if max_size <= 0:
            raise ValueError("Cache size must be positive")
        if default_ttl <= 0:
            raise ValueError("TTL must be positive")
        
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry[T]] = {}
        self._expiration_queue: List[tuple] = []  # (expires_at, key)
        self._lock = threading.RLock()
        self._stats = CacheStats(max_size=max_size)

    def get(self, key: str) -> Optional[T]:
        """Get an item from the cache"""
        with self._lock:
            self._cleanup_expired()
            
            if key not in self._cache:
                self._stats.misses += 1
                return None
            
            entry = self._cache[key]
            if entry.is_expired():
                del self._cache[key]
                self._stats.misses += 1
                self._stats.evictions += 1
                self._stats.size = len(self._cache)
                return None
            
            self._stats.hits += 1
            return entry.value

    def put(self, key: str, value: T, ttl: Optional[float] = None) -> None:
        """Put an item in the cache"""
        with self._lock:
            self._cleanup_expired()
            
            effective_ttl = ttl if ttl is not None else self._default_ttl
            expires_at = time.time() + effective_ttl
            
            entry = CacheEntry(
                value=value,
                expires_at=expires_at,
                created_at=time.time()
            )
            
            # Update or add
            self._cache[key] = entry
            
            # Add to expiration queue
            heappush(self._expiration_queue, (expires_at, key))
            
            # Evict if over capacity
            if len(self._cache) > self._max_size:
                self._evict()
            
            self._stats.size = len(self._cache)

    def _cleanup_expired(self) -> None:
        """Remove expired entries from cache"""
        with self._lock:
            now = time.time()
            
            # Remove from expiration queue
            while self._expiration_queue and self._expiration_queue[0][0] <= now:
                _, key = heappop(self._expiration_queue)
                if key in self._cache and self._cache[key].is_expired():
                    del self._cache[key]
                    self._stats.evictions += 1
            
            self._stats.size = len(self._cache)

    def _evict(self) -> None:
        """Evict the least recently used non-expired item"""
        with self._lock:
            # First, try to find expired items to remove
            self._cleanup_expired()
            
            # If still over capacity, remove oldest non-expired
            if len(self._cache) > self._max_size:
                # Find oldest non-expired
                oldest_key = None
                oldest_time = float('inf')
                
                for key, entry in self._cache.items():
                    if not entry.is_expired() and entry.created_at < oldest_time:
                        oldest_key = key
                        oldest_time = entry.created_at
                
                if oldest_key:
                    del self._cache[oldest_key]
                    self._stats.evictions += 1
                    self._stats.size = len(self._cache)

    def delete(self, key: str) -> bool:
        """Delete an item from the cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats.size = len(self._cache)
                return True
            return False

    def clear(self) -> None:
        """Clear all items from the cache"""
        with self._lock:
            self._cache.clear()
            self._expiration_queue.clear()
            self._stats.size = 0
            self._stats.evictions = 0
            self._stats.hits = 0
            self._stats.misses = 0

    def contains(self, key: str) -> bool:
        """Check if key exists in cache and is not expired"""
        with self._lock:
            self._cleanup_expired()
            return key in self._cache and not self._cache[key].is_expired()

    def size(self) -> int:
        """Get current cache size"""
        with self._lock:
            self._cleanup_expired()
            return len(self._cache)

    def is_empty(self) -> bool:
        """Check if cache is empty"""
        return self.size() == 0

    def is_full(self) -> bool:
        """Check if cache is full"""
        return self.size() >= self._max_size

    def keys(self) -> List[str]:
        """Get all keys in cache"""
        with self._lock:
            self._cleanup_expired()
            return list(self._cache.keys())

    def values(self) -> List[T]:
        """Get all values in cache"""
        with self._lock:
            self._cleanup_expired()
            return [entry.value for entry in self._cache.values()]

    def items(self) -> List[tuple]:
        """Get all key-value pairs in cache"""
        with self._lock:
            self._cleanup_expired()
            return [(key, entry.value) for key, entry in self._cache.items()]

    def get_ttl(self, key: str) -> Optional[float]:
        """Get TTL for a key"""
        with self._lock:
            if key not in self._cache:
                return None
            entry = self._cache[key]
            if entry.is_expired():
                return 0.0
            return entry.expires_at - time.time()

    def set_ttl(self, key: str, ttl: float) -> bool:
        """Set TTL for a key"""
        with self._lock:
            if key not in self._cache:
                return False
            
            entry = self._cache[key]
            entry.expires_at = time.time() + ttl
            
            # Re-add to expiration queue with new time
            heappush(self._expiration_queue, (entry.expires_at, key))
            return True

    def touch(self, key: str, ttl: Optional[float] = None) -> bool:
        """Update expiration time for a key"""
        with self._lock:
            if key not in self._cache:
                return False
            
            entry = self._cache[key]
            effective_ttl = ttl if ttl is not None else self._default_ttl
            entry.expires_at = time.time() + effective_ttl
            entry.created_at = time.time()
            
            # Re-add to expiration queue
            heappush(self._expiration_queue, (entry.expires_at, key))
            return True

    def get_stats(self) -> CacheStats:
        """Get cache statistics"""
        with self._lock:
            self._cleanup_expired()
            self._stats.size = len(self._cache)
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                size=self._stats.size,
                max_size=self._max_size
            )

    def resize(self, new_size: int) -> None:
        """Resize the cache"""
        with self._lock:
            if new_size <= 0:
                self.clear()
                return
            
            self._max_size = new_size
            self._stats.max_size = new_size
            
            # Cleanup and evict if necessary
            self._cleanup_expired()
            while len(self._cache) > self._max_size:
                self._evict()

    def set_default_ttl(self, ttl: float) -> None:
        """Set default TTL"""
        if ttl <= 0:
            raise ValueError("TTL must be positive")
        self._default_ttl = ttl

    def get_with_default(self, key: str, default: T) -> T:
        """Get an item with a default value if not found"""
        value = self.get(key)
        return value if value is not None else default

    def get_or_compute(self, key: str, compute_func: Callable[[], T], 
                       ttl: Optional[float] = None) -> T:
        """Get an item or compute it if not in cache"""
        value = self.get(key)
        if value is not None:
            return value
        
        # Compute and cache
        value = compute_func()
        self.put(key, value, ttl)
        return value

    def __contains__(self, key: str) -> bool:
        return self.contains(key)

    def __getitem__(self, key: str) -> T:
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key: str, value: T) -> None:
        self.put(key, value)

    def __delitem__(self, key: str) -> None:
        if not self.delete(key):
            raise KeyError(key)

    def __len__(self) -> int:
        return self.size()

    def __iter__(self):
        return iter(self.keys())


def create_ttl_cache(max_size: int = 1000, default_ttl: float = 300.0) -> TTLCache:
    """Create a TTL cache"""
    return TTLCache(max_size, default_ttl)
