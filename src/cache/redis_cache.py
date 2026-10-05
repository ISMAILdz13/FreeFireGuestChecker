"""
Redis Cache Implementation for Free Fire Guest Account Checker
Redis-based distributed cache
"""

from __future__ import annotations

import json
import pickle
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar, Union

import redis
from redis import Redis

from src.cache.lru_cache import CacheStats
from src.utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


@dataclass
class RedisConfig:
    """Redis configuration"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    socket_keepalive: bool = True
    max_connections: int = 50
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RedisConfig:
        """Create from dictionary"""
        return cls(
            host=data.get("host", "localhost"),
            port=data.get("port", 6379),
            db=data.get("db", 0),
            password=data.get("password"),
            socket_timeout=data.get("socket_timeout", 5.0),
            socket_connect_timeout=data.get("socket_connect_timeout", 5.0),
            socket_keepalive=data.get("socket_keepalive", True),
            max_connections=data.get("max_connections", 50)
        )


class RedisCache(Generic[T]):
    """Redis-based cache implementation"""

    def __init__(self, config: Optional[RedisConfig] = None, 
                 prefix: str = "ffgc:", default_ttl: float = 300.0):
        self.config = config or RedisConfig()
        self.prefix = prefix
        self.default_ttl = default_ttl
        
        # Create Redis connection pool
        self._pool = redis.ConnectionPool(
            host=self.config.host,
            port=self.config.port,
            db=self.config.db,
            password=self.config.password,
            socket_timeout=self.config.socket_timeout,
            socket_connect_timeout=self.config.socket_connect_timeout,
            socket_keepalive=self.config.socket_keepalive,
            max_connections=self.config.max_connections,
            decode_responses=True
        )
        
        self._redis = Redis(connection_pool=self._pool)
        self._lock = threading.RLock()
        self._stats = CacheStats(max_size=10000)  # Redis doesn't have max size

    def _make_key(self, key: str) -> str:
        """Make a Redis key with prefix"""
        return f"{self.prefix}{key}"

    def _serialize(self, value: T) -> str:
        """Serialize a value for Redis"""
        try:
            if isinstance(value, (str, int, float, bool)):
                return str(value)
            return json.dumps(value)
        except (TypeError, ValueError):
            # Use pickle for complex objects
            return base64.b64encode(pickle.dumps(value)).decode('utf-8')

    def _deserialize(self, value: str, default: Optional[T] = None) -> Optional[T]:
        """Deserialize a value from Redis"""
        if value is None:
            return default
        
        try:
            # Try JSON first
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            try:
                # Try base64 pickle
                return pickle.loads(base64.b64decode(value.encode('utf-8')))
            except Exception:
                return value if default is None else default

    def get(self, key: str) -> Optional[T]:
        """Get an item from the cache"""
        with self._lock:
            redis_key = self._make_key(key)
            value = self._redis.get(redis_key)
            
            if value is None:
                self._stats.misses += 1
                return None
            
            self._stats.hits += 1
            return self._deserialize(value)

    def put(self, key: str, value: T, ttl: Optional[float] = None) -> None:
        """Put an item in the cache"""
        with self._lock:
            redis_key = self._make_key(key)
            effective_ttl = int(ttl) if ttl is not None else int(self.default_ttl)
            
            serialized = self._serialize(value)
            self._redis.setex(redis_key, effective_ttl, serialized)
            
            self._stats.size = self._redis.dbsize()

    def delete(self, key: str) -> bool:
        """Delete an item from the cache"""
        with self._lock:
            redis_key = self._make_key(key)
            result = self._redis.delete(redis_key)
            self._stats.size = self._redis.dbsize()
            return result > 0

    def clear(self) -> None:
        """Clear all items with this prefix"""
        with self._lock:
            # Find all keys with prefix
            pattern = f"{self.prefix}*"
            keys = self._redis.keys(pattern)
            
            if keys:
                self._redis.delete(*keys)
            
            self._stats.size = 0
            self._stats.evictions = 0
            self._stats.hits = 0
            self._stats.misses = 0

    def contains(self, key: str) -> bool:
        """Check if key exists in cache"""
        with self._lock:
            redis_key = self._make_key(key)
            return self._redis.exists(redis_key) > 0

    def size(self) -> int:
        """Get current cache size"""
        with self._lock:
            return self._redis.dbsize()

    def is_empty(self) -> bool:
        """Check if cache is empty"""
        return self.size() == 0

    def keys(self, pattern: str = "*") -> List[str]:
        """Get all keys matching pattern"""
        with self._lock:
            full_pattern = f"{self.prefix}{pattern}"
            redis_keys = self._redis.keys(full_pattern)
            return [key[len(self.prefix):] for key in redis_keys]

    def values(self) -> List[T]:
        """Get all values in cache"""
        with self._lock:
            keys = self.keys()
            return [self.get(key) for key in keys if self.get(key) is not None]

    def items(self) -> List[tuple]:
        """Get all key-value pairs in cache"""
        with self._lock:
            keys = self.keys()
            return [(key, self.get(key)) for key in keys if self.get(key) is not None]

    def get_ttl(self, key: str) -> Optional[float]:
        """Get TTL for a key"""
        with self._lock:
            redis_key = self._make_key(key)
            ttl = self._redis.ttl(redis_key)
            return float(ttl) if ttl > 0 else None

    def set_ttl(self, key: str, ttl: float) -> bool:
        """Set TTL for a key"""
        with self._lock:
            redis_key = self._make_key(key)
            return self._redis.expire(redis_key, int(ttl)) > 0

    def touch(self, key: str, ttl: Optional[float] = None) -> bool:
        """Update expiration time for a key"""
        with self._lock:
            redis_key = self._make_key(key)
            effective_ttl = int(ttl) if ttl is not None else int(self.default_ttl)
            return self._redis.expire(redis_key, effective_ttl) > 0

    def increment(self, key: str, amount: int = 1) -> int:
        """Increment a numeric value"""
        with self._lock:
            redis_key = self._make_key(key)
            return self._redis.incrby(redis_key, amount)

    def decrement(self, key: str, amount: int = 1) -> int:
        """Decrement a numeric value"""
        with self._lock:
            redis_key = self._make_key(key)
            return self._redis.decrby(redis_key, amount)

    def get_stats(self) -> CacheStats:
        """Get cache statistics"""
        with self._lock:
            info = self._redis.info()
            self._stats.size = info.get("db0", {}).get("keys", 0)
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=info.get("stats", {}).get("evicted_keys", 0),
                size=self._stats.size,
                max_size=10000  # Redis doesn't have max size
            )

    def ping(self) -> bool:
        """Check Redis connection"""
        try:
            return self._redis.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False

    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        try:
            return self._redis.connection_pool.get_connection().ping()
        except Exception:
            return False

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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self) -> None:
        """Close Redis connection"""
        self._redis.close()
        self._pool.close()


def create_redis_cache(config: Optional[RedisConfig] = None, 
                      prefix: str = "ffgc:", default_ttl: float = 300.0) -> RedisCache:
    """Create a Redis cache"""
    return RedisCache(config, prefix, default_ttl)


# Import base64 for serialization
import base64
