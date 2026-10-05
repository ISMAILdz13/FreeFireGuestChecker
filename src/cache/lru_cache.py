"""
LRU Cache Implementation for Free Fire Guest Account Checker
Least Recently Used cache with O(1) operations
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar, Union

from src.utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


@dataclass
class CacheStats:
    """Cache statistics"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    max_size: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate hit rate"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "size": self.size,
            "max_size": self.max_size,
            "hit_rate": self.hit_rate
        }


class LRUCache(Generic[T]):
    """Thread-safe LRU cache implementation"""

    def __init__(self, max_size: int = 1000):
        if max_size <= 0:
            raise ValueError("Cache size must be positive")
        
        self._max_size = max_size
        self._cache: OrderedDict[str, T] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = CacheStats(max_size=max_size)

    def get(self, key: str) -> Optional[T]:
        """Get an item from the cache"""
        with self._lock:
            if key not in self._cache:
                self._stats.misses += 1
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._stats.hits += 1
            return self._cache[key]

    def put(self, key: str, value: T) -> None:
        """Put an item in the cache"""
        with self._lock:
            if key in self._cache:
                # Update existing
                self._cache.move_to_end(key)
                self._cache[key] = value
            else:
                # Add new
                self._cache[key] = value
                self._cache.move_to_end(key)
                
                # Evict if over capacity
                if len(self._cache) > self._max_size:
                    self._evict()
            
            self._stats.size = len(self._cache)

    def _evict(self) -> None:
        """Evict the least recently used item"""
        with self._lock:
            if len(self._cache) > self._max_size:
                self._cache.popitem(last=False)
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
            self._stats.size = 0
            self._stats.evictions = 0
            self._stats.hits = 0
            self._stats.misses = 0

    def contains(self, key: str) -> bool:
        """Check if key exists in cache"""
        with self._lock:
            return key in self._cache

    def size(self) -> int:
        """Get current cache size"""
        with self._lock:
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
            return list(self._cache.keys())

    def values(self) -> List[T]:
        """Get all values in cache"""
        with self._lock:
            return list(self._cache.values())

    def items(self) -> List[tuple]:
        """Get all key-value pairs in cache"""
        with self._lock:
            return list(self._cache.items())

    def get_stats(self) -> CacheStats:
        """Get cache statistics"""
        with self._lock:
            self._stats.size = len(self._cache)
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                size=self._stats.size,
                max_size=self._max_size
            )

    def get_oldest(self) -> Optional[tuple]:
        """Get the oldest (least recently used) item"""
        with self._lock:
            if not self._cache:
                return None
            # First item is oldest
            oldest_key = next(iter(self._cache))
            return (oldest_key, self._cache[oldest_key])

    def get_newest(self) -> Optional[tuple]:
        """Get the newest (most recently used) item"""
        with self._lock:
            if not self._cache:
                return None
            # Last item is newest
            newest_key = next(reversed(self._cache))
            return (newest_key, self._cache[newest_key])

    def resize(self, new_size: int) -> None:
        """Resize the cache"""
        with self._lock:
            if new_size <= 0:
                self.clear()
                return
            
            self._max_size = new_size
            self._stats.max_size = new_size
            
            # Evict if necessary
            while len(self._cache) > self._max_size:
                self._evict()

    def get_with_default(self, key: str, default: T) -> T:
        """Get an item with a default value if not found"""
        value = self.get(key)
        return value if value is not None else default

    def get_or_compute(self, key: str, compute_func: Callable[[], T]) -> T:
        """Get an item or compute it if not in cache"""
        value = self.get(key)
        if value is not None:
            return value
        
        # Compute and cache
        value = compute_func()
        self.put(key, value)
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


def create_lru_cache(max_size: int = 1000) -> LRUCache:
    """Create an LRU cache"""
    return LRUCache(max_size)
