"""
Redis Session Store for Free Fire Guest Account Checker
Stores sessions in Redis
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Union

import redis

from src.sessions.session import Session, SessionData
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RedisSessionStoreConfig:
    """Redis session store configuration"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    prefix: str = "ffgc:session:"
    ttl: int = 86400  # 24 hours
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RedisSessionStoreConfig:
        """Create from dictionary"""
        return cls(
            host=data.get("host", "localhost"),
            port=data.get("port", 6379),
            db=data.get("db", 0),
            password=data.get("password"),
            prefix=data.get("prefix", "ffgc:session:"),
            ttl=data.get("ttl", 86400)
        )


class RedisSessionStore:
    """Redis-based session store"""

    def __init__(self, config: Optional[RedisSessionStoreConfig] = None):
        self.config = config or RedisSessionStoreConfig()
        self._lock = threading.RLock()
        
        # Create Redis connection
        self._redis = redis.Redis(
            host=self.config.host,
            port=self.config.port,
            db=self.config.db,
            password=self.config.password,
            decode_responses=True
        )
        
        # Test connection
        try:
            self._redis.ping()
            logger.info("Connected to Redis session store")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def _get_key(self, session_id: str) -> str:
        """Get Redis key for a session"""
        return f"{self.config.prefix}{session_id}"

    def _get_user_key(self, user_id: str) -> str:
        """Get Redis key for user sessions"""
        return f"{self.config.prefix}user:{user_id}"

    def _serialize(self, session: Session) -> str:
        """Serialize session to JSON"""
        return json.dumps(session.to_dict())

    def _deserialize(self, data: str) -> Optional[Session]:
        """Deserialize session from JSON"""
        try:
            return Session.from_dict(json.loads(data))
        except Exception as e:
            logger.error(f"Failed to deserialize session: {e}")
            return None

    def save(self, session: Session) -> bool:
        """Save a session to Redis"""
        with self._lock:
            try:
                key = self._get_key(session.session_id)
                data = self._serialize(session)
                
                # Save session with TTL
                self._redis.setex(key, self.config.ttl, data)
                
                # Add to user index
                user_key = self._get_user_key(session.get_user_id())
                self._redis.sadd(user_key, session.session_id)
                
                # Set TTL on user key
                self._redis.expire(user_key, self.config.ttl)
                
                logger.debug(f"Saved session {session.session_id} to Redis")
                return True
            except Exception as e:
                logger.error(f"Failed to save session {session.session_id} to Redis: {e}")
                return False

    def get(self, session_id: str) -> Optional[Session]:
        """Get a session from Redis"""
        with self._lock:
            try:
                key = self._get_key(session_id)
                data = self._redis.get(key)
                
                if not data:
                    return None
                
                session = self._deserialize(data)
                
                if session and session.is_expired():
                    self.delete(session_id)
                    return None
                
                logger.debug(f"Loaded session {session_id} from Redis")
                return session
            except Exception as e:
                logger.error(f"Failed to load session {session_id} from Redis: {e}")
                return None

    def get_by_user(self, user_id: str) -> List[Session]:
        """Get all sessions for a user"""
        with self._lock:
            sessions = []
            
            try:
                user_key = self._get_user_key(user_id)
                session_ids = self._redis.smembers(user_key)
                
                for session_id in session_ids:
                    session = self.get(session_id)
                    if session:
                        sessions.append(session)
            except Exception as e:
                logger.error(f"Failed to get sessions for user {user_id}: {e}")
            
            return sessions

    def delete(self, session_id: str) -> bool:
        """Delete a session from Redis"""
        with self._lock:
            try:
                key = self._get_key(session_id)
                
                # Get session to remove from user index
                session = self.get(session_id)
                if session:
                    user_key = self._get_user_key(session.get_user_id())
                    self._redis.srem(user_key, session_id)
                
                # Delete session
                result = bool(self._redis.delete(key))
                
                if result:
                    logger.debug(f"Deleted session {session_id} from Redis")
                
                return result
            except Exception as e:
                logger.error(f"Failed to delete session {session_id} from Redis: {e}")
                return False

    def clear(self) -> int:
        """Clear all sessions from Redis"""
        with self._lock:
            try:
                # Get all session keys
                pattern = f"{self.config.prefix}*"
                keys = self._redis.keys(pattern)
                
                if keys:
                    count = self._redis.delete(*keys)
                    logger.info(f"Cleared {count} sessions from Redis")
                    return count
                return 0
            except Exception as e:
                logger.error(f"Failed to clear sessions from Redis: {e}")
                return 0

    def cleanup_expired(self) -> int:
        """Cleanup expired sessions from Redis"""
        # Redis automatically expires keys, so we just need to clean up user indexes
        with self._lock:
            try:
                # Get all user keys
                pattern = f"{self.config.prefix}user:*"
                user_keys = self._redis.keys(pattern)
                
                count = 0
                for user_key in user_keys:
                    # Check if any session for this user still exists
                    session_ids = self._redis.smembers(user_key)
                    
                    # Remove user key if no sessions
                    if not session_ids:
                        self._redis.delete(user_key)
                        count += 1
                
                logger.debug(f"Cleaned up {count} user indexes from Redis")
                return count
            except Exception as e:
                logger.error(f"Failed to cleanup expired sessions from Redis: {e}")
                return 0

    def list_all(self) -> List[Session]:
        """List all sessions"""
        with self._lock:
            sessions = []
            
            try:
                pattern = f"{self.config.prefix}*"
                keys = self._redis.keys(pattern)
                
                for key in keys:
                    # Skip user index keys
                    if ":user:" in key:
                        continue
                    
                    session_id = key[len(self.config.prefix):]
                    session = self.get(session_id)
                    
                    if session:
                        sessions.append(session)
            except Exception as e:
                logger.error(f"Failed to list all sessions from Redis: {e}")
            
            return sessions

    def exists(self, session_id: str) -> bool:
        """Check if session exists in Redis"""
        key = self._get_key(session_id)
        return self._redis.exists(key) > 0

    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics"""
        try:
            info = self._redis.info()
            db_info = info.get("db0", {})
            
            return {
                "type": "redis",
                "host": self.config.host,
                "port": self.config.port,
                "db": self.config.db,
                "prefix": self.config.prefix,
                "ttl": self.config.ttl,
                "keys": db_info.get("keys", 0),
                "expired_keys": db_info.get("expired_keys", 0)
            }
        except Exception as e:
            logger.error(f"Failed to get Redis stats: {e}")
            return {
                "type": "redis",
                "error": str(e)
            }

    def ping(self) -> bool:
        """Check Redis connection"""
        try:
            return self._redis.ping()
        except Exception:
            return False

    def close(self) -> None:
        """Close Redis connection"""
        try:
            self._redis.close()
            logger.info("Redis session store connection closed")
        except Exception as e:
            logger.error(f"Failed to close Redis connection: {e}")
