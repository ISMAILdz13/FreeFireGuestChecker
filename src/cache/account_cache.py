"""
Account Cache for Free Fire Guest Account Checker
Specialized cache for storing account information
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from src.cache.ttl_cache import TTLCache
from src.cache.lru_cache import LRUCache
from src.cache.redis_cache import RedisCache, RedisConfig
from src.utils.logging import get_logger
from src.utils.helpers import get_timestamp

logger = get_logger(__name__)


@dataclass
class CachedAccount:
    """Cached account information"""
    account_id: str
    data: Dict[str, Any]
    status: str
    region: str
    source: str
    cached_at: float
    expires_at: float
    checked_count: int = 0
    last_checked: float = field(default_factory=time.time)
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return time.time() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "account_id": self.account_id,
            "data": self.data,
            "status": self.status,
            "region": self.region,
            "source": self.source,
            "cached_at": self.cached_at,
            "expires_at": self.expires_at,
            "checked_count": self.checked_count,
            "last_checked": self.last_checked
        }


class AccountCache:
    """Specialized cache for account information"""

    def __init__(self, 
                 cache_type: str = "memory",
                 max_size: int = 10000,
                 default_ttl: float = 300.0,
                 redis_config: Optional[RedisConfig] = None):
        self.cache_type = cache_type
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.redis_config = redis_config
        
        # Initialize the appropriate cache
        if cache_type == "redis" and redis_config:
            self._cache = RedisCache(redis_config, prefix="accounts:", default_ttl=default_ttl)
        else:
            # Use TTL cache for memory-based caching
            self._cache = TTLCache(max_size=max_size, default_ttl=default_ttl)
        
        # Additional index for fast lookups
        self._status_index: Dict[str, Set[str]] = {}
        self._region_index: Dict[str, Set[str]] = {}
        self._source_index: Dict[str, Set[str]] = {}
        self._lock = threading.RLock()
        
        # Statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "cached_accounts": 0
        }

    def get(self, account_id: str) -> Optional[CachedAccount]:
        """Get an account from cache"""
        with self._lock:
            cached = self._cache.get(account_id)
            
            if cached is None:
                self._stats["misses"] += 1
                return None
            
            self._stats["hits"] += 1
            
            # Update last checked
            if isinstance(cached, CachedAccount):
                cached.last_checked = time.time()
                cached.checked_count += 1
            
            return cached

    def put(self, account_id: str, data: Dict[str, Any], 
            status: str = "unknown", region: str = "global", 
            source: str = "cache", ttl: Optional[float] = None) -> None:
        """Put an account in cache"""
        with self._lock:
            expires_at = time.time() + (ttl if ttl is not None else self.default_ttl)
            
            cached = CachedAccount(
                account_id=account_id,
                data=data,
                status=status,
                region=region,
                source=source,
                cached_at=time.time(),
                expires_at=expires_at
            )
            
            self._cache.put(account_id, cached, ttl)
            
            # Update indexes
            if status not in self._status_index:
                self._status_index[status] = set()
            self._status_index[status].add(account_id)
            
            if region not in self._region_index:
                self._region_index[region] = set()
            self._region_index[region].add(account_id)
            
            if source not in self._source_index:
                self._source_index[source] = set()
            self._source_index[source].add(account_id)
            
            self._stats["cached_accounts"] = len(self._cache)

    def delete(self, account_id: str) -> bool:
        """Delete an account from cache"""
        with self._lock:
            # Remove from indexes
            cached = self._cache.get(account_id)
            if cached:
                if cached.status in self._status_index:
                    self._status_index[cached.status].discard(account_id)
                if cached.region in self._region_index:
                    self._region_index[cached.region].discard(account_id)
                if cached.source in self._source_index:
                    self._source_index[cached.source].discard(account_id)
            
            result = self._cache.delete(account_id)
            if result:
                self._stats["cached_accounts"] = len(self._cache)
            return result
        return False

    def clear(self) -> None:
        """Clear all accounts from cache"""
        with self._lock:
            self._cache.clear()
            self._status_index.clear()
            self._region_index.clear()
            self._source_index.clear()
            self._stats = {
                "hits": 0,
                "misses": 0,
                "evictions": 0,
                "cached_accounts": 0
            }

    def contains(self, account_id: str) -> bool:
        """Check if account is in cache"""
        return self._cache.contains(account_id)

    def get_by_status(self, status: str) -> List[CachedAccount]:
        """Get all accounts with a specific status"""
        with self._lock:
            account_ids = self._status_index.get(status, set())
            return [self.get(acc_id) for acc_id in account_ids if self.get(acc_id) is not None]

    def get_by_region(self, region: str) -> List[CachedAccount]:
        """Get all accounts from a specific region"""
        with self._lock:
            account_ids = self._region_index.get(region, set())
            return [self.get(acc_id) for acc_id in account_ids if self.get(acc_id) is not None]

    def get_by_source(self, source: str) -> List[CachedAccount]:
        """Get all accounts from a specific source"""
        with self._lock:
            account_ids = self._source_index.get(source, set())
            return [self.get(acc_id) for acc_id in account_ids if self.get(acc_id) is not None]

    def get_all(self) -> List[CachedAccount]:
        """Get all cached accounts"""
        with self._lock:
            return [self.get(key) for key in self._cache.keys() if self.get(key) is not None]

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            cache_stats = self._cache.get_stats() if hasattr(self._cache, 'get_stats') else {}
            return {
                **self._stats,
                **cache_stats,
                "status_index": {k: len(v) for k, v in self._status_index.items()},
                "region_index": {k: len(v) for k, v in self._region_index.items()},
                "source_index": {k: len(v) for k, v in self._source_index.items()}
            }

    def invalidate_expired(self) -> int:
        """Remove all expired accounts from cache"""
        with self._lock:
            expired_count = 0
            
            for key in list(self._cache.keys()):
                cached = self._cache.get(key)
                if cached and cached.is_expired():
                    self.delete(key)
                    expired_count += 1
            
            return expired_count

    def invalidate_by_status(self, status: str) -> int:
        """Invalidate all accounts with a specific status"""
        with self._lock:
            count = 0
            account_ids = list(self._status_index.get(status, set()))
            
            for acc_id in account_ids:
                if self.delete(acc_id):
                    count += 1
            
            return count

    def invalidate_by_region(self, region: str) -> int:
        """Invalidate all accounts from a specific region"""
        with self._lock:
            count = 0
            account_ids = list(self._region_index.get(region, set()))
            
            for acc_id in account_ids:
                if self.delete(acc_id):
                    count += 1
            
            return count

    def invalidate_by_source(self, source: str) -> int:
        """Invalidate all accounts from a specific source"""
        with self._lock:
            count = 0
            account_ids = list(self._source_index.get(source, set()))
            
            for acc_id in account_ids:
                if self.delete(acc_id):
                    count += 1
            
            return count

    def size(self) -> int:
        """Get current cache size"""
        return self._cache.size()

    def is_empty(self) -> bool:
        """Check if cache is empty"""
        return self.size() == 0

    def warm_cache(self, accounts: List[Dict[str, Any]]) -> int:
        """Warm the cache with a list of accounts"""
        with self._lock:
            count = 0
            for account in accounts:
                account_id = account.get("account_id")
                if account_id:
                    self.put(
                        account_id=account_id,
                        data=account.get("data", {}),
                        status=account.get("status", "unknown"),
                        region=account.get("region", "global"),
                        source=account.get("source", "warm_cache")
                    )
                    count += 1
            return count

    def get_most_checked(self, limit: int = 10) -> List[CachedAccount]:
        """Get most frequently checked accounts"""
        with self._lock:
            all_accounts = self.get_all()
            sorted_accounts = sorted(all_accounts, key=lambda x: x.checked_count, reverse=True)
            return sorted_accounts[:limit]

    def get_recently_checked(self, limit: int = 10) -> List[CachedAccount]:
        """Get recently checked accounts"""
        with self._lock:
            all_accounts = self.get_all()
            sorted_accounts = sorted(all_accounts, key=lambda x: x.last_checked, reverse=True)
            return sorted_accounts[:limit]


# Import threading for lock
import threading
