"""
Cache module for Free Fire Guest Account Checker
Contains caching implementations for performance optimization
"""

from __future__ import annotations

__all__ = [
    "Cache",
    "LRUCache",
    "TTLCache",
    "RedisCache",
    "AccountCache",
    "create_cache",
    "get_cache"
]

from .lru_cache import LRUCache, create_lru_cache
from .ttl_cache import TTLCache, create_ttl_cache
from .redis_cache import RedisCache, create_redis_cache
from .account_cache import AccountCache
