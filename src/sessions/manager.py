"""
Session Manager for Free Fire Guest Account Checker
Manages user sessions and authentication state
"""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from src.sessions.session import Session, SessionData
from src.utils.logging import get_logger
from src.utils.helpers import generate_id, get_timestamp

logger = get_logger(__name__)


@dataclass
class SessionConfig:
    """Session manager configuration"""
    session_timeout: float = 86400  # 24 hours
    max_sessions: int = 10000
    cleanup_interval: float = 3600  # 1 hour
    session_id_length: int = 32
    
    # Cookie settings
    cookie_name: str = "session_id"
    cookie_secure: bool = True
    cookie_httponly: bool = True
    cookie_samesite: str = "lax"
    cookie_domain: Optional[str] = None
    cookie_path: str = "/"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SessionConfig:
        """Create from dictionary"""
        return cls(
            session_timeout=data.get("session_timeout", 86400),
            max_sessions=data.get("max_sessions", 10000),
            cleanup_interval=data.get("cleanup_interval", 3600),
            session_id_length=data.get("session_id_length", 32),
            cookie_name=data.get("cookie_name", "session_id"),
            cookie_secure=data.get("cookie_secure", True),
            cookie_httponly=data.get("cookie_httponly", True),
            cookie_samesite=data.get("cookie_samesite", "lax"),
            cookie_domain=data.get("cookie_domain"),
            cookie_path=data.get("cookie_path", "/")
        )


class SessionManager:
    """Manages user sessions"""

    def __init__(self, config: Optional[SessionConfig] = None,
                 store: Optional[Any] = None):
        self.config = config or SessionConfig()
        self.store = store
        
        # In-memory session storage
        self._sessions: Dict[str, Session] = {}
        self._lock = threading.RLock()
        
        # Statistics
        self._stats = {
            "total_sessions": 0,
            "active_sessions": 0,
            "created_sessions": 0,
            "destroyed_sessions": 0,
            "expired_sessions": 0
        }
        
        # Cleanup thread
        self._cleanup_running = False
        self._cleanup_thread: Optional[threading.Thread] = None

    def start_cleanup(self) -> None:
        """Start session cleanup thread"""
        if self._cleanup_running:
            return
        
        self._cleanup_running = True
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True
        )
        self._cleanup_thread.start()
        logger.info("Session cleanup thread started")

    def stop_cleanup(self) -> None:
        """Stop session cleanup thread"""
        self._cleanup_running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=1.0)
        logger.info("Session cleanup thread stopped")

    def _cleanup_loop(self) -> None:
        """Cleanup loop for expired sessions"""
        while self._cleanup_running:
            try:
                # Cleanup expired sessions
                cleaned = self.cleanup_expired()
                if cleaned > 0:
                    logger.info(f"Cleaned up {cleaned} expired sessions")
                
                # Sleep for cleanup interval
                time.sleep(self.config.cleanup_interval)
            except Exception as e:
                logger.error(f"Session cleanup error: {e}")
                time.sleep(60)  # Wait before retrying

    def create_session(self, user_id: str, **kwargs) -> Session:
        """Create a new session"""
        with self._lock:
            # Check if user already has a session
            for session in self._sessions.values():
                if session.get_user_id() == user_id and session.is_valid:
                    # Optionally: invalidate old session
                    # session.invalidate()
                    pass
            
            # Create new session
            session = Session.create(user_id, **kwargs)
            
            # Store session
            self._sessions[session.session_id] = session
            self._stats["total_sessions"] += 1
            self._stats["active_sessions"] += 1
            self._stats["created_sessions"] += 1
            
            # Also store in external store if available
            if self.store:
                self.store.save(session)
            
            logger.debug(f"Created session {session.session_id} for user {user_id}")
            return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID"""
        with self._lock:
            # Try in-memory first
            session = self._sessions.get(session_id)
            
            if session and session.is_valid and not session.is_expired():
                session.touch()
                return session
            
            # Try external store
            if self.store:
                session = self.store.get(session_id)
                if session and session.is_valid and not session.is_expired():
                    session.touch()
                    # Cache in memory
                    self._sessions[session_id] = session
                    return session
            
            return None

    def get_session_by_user(self, user_id: str) -> Optional[Session]:
        """Get a session by user ID"""
        with self._lock:
            for session in self._sessions.values():
                if session.get_user_id() == user_id and session.is_valid and not session.is_expired():
                    session.touch()
                    return session
            
            # Try external store
            if self.store:
                sessions = self.store.get_by_user(user_id)
                for session in sessions:
                    if session.is_valid and not session.is_expired():
                        session.touch()
                        # Cache in memory
                        self._sessions[session.session_id] = session
                        return session
            
            return None

    def get_all_sessions(self) -> List[Session]:
        """Get all active sessions"""
        with self._lock:
            return list(self._sessions.values())

    def get_sessions_by_user(self, user_id: str) -> List[Session]:
        """Get all sessions for a user"""
        with self._lock:
            return [
                session for session in self._sessions.values()
                if session.get_user_id() == user_id
            ]

    def update_session(self, session_id: str, **kwargs) -> bool:
        """Update a session"""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session or not session.is_valid:
                return False
            
            # Update session
            for key, value in kwargs.items():
                if hasattr(session, key):
                    setattr(session, key, value)
                elif hasattr(session.data, key):
                    setattr(session.data, key, value)
                else:
                    session.set_custom_data(key, value)
            
            # Update in external store
            if self.store:
                self.store.save(session)
            
            logger.debug(f"Updated session {session_id}")
            return True

    def extend_session(self, session_id: str, expiry: float) -> bool:
        """Extend session expiration"""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session or not session.is_valid:
                return False
            
            session.extend(expiry)
            
            # Update in external store
            if self.store:
                self.store.save(session)
            
            logger.debug(f"Extended session {session_id}")
            return True

    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a session"""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            
            # Invalidate session
            session.invalidate()
            self._stats["active_sessions"] -= 1
            self._stats["destroyed_sessions"] += 1
            
            # Remove from external store
            if self.store:
                self.store.delete(session_id)
            
            logger.info(f"Invalidated session {session_id}")
            return True

    def invalidate_user_sessions(self, user_id: str) -> int:
        """Invalidate all sessions for a user"""
        with self._lock:
            count = 0
            sessions_to_remove = []
            
            for session_id, session in self._sessions.items():
                if session.get_user_id() == user_id:
                    session.invalidate()
                    sessions_to_remove.append(session_id)
                    count += 1
            
            for session_id in sessions_to_remove:
                del self._sessions[session_id]
                self._stats["active_sessions"] -= 1
                self._stats["destroyed_sessions"] += 1
                
                # Remove from external store
                if self.store:
                    self.store.delete(session_id)
            
            logger.info(f"Invalidated {count} sessions for user {user_id}")
            return count

    def invalidate_all_sessions(self) -> int:
        """Invalidate all sessions"""
        with self._lock:
            count = len(self._sessions)
            
            for session in self._sessions.values():
                session.invalidate()
            
            self._sessions.clear()
            self._stats["active_sessions"] = 0
            self._stats["total_sessions"] = 0
            
            # Clear external store
            if self.store:
                self.store.clear()
            
            logger.info(f"Invalidated all {count} sessions")
            return count

    def cleanup_expired(self) -> int:
        """Cleanup expired sessions"""
        with self._lock:
            expired = []
            now = time.time()
            
            for session_id, session in self._sessions.items():
                if session.is_expired():
                    expired.append(session_id)
            
            for session_id in expired:
                session = self._sessions[session_id]
                session.invalidate()
                del self._sessions[session_id]
                self._stats["active_sessions"] -= 1
                self._stats["destroyed_sessions"] += 1
                self._stats["expired_sessions"] += 1
                
                # Remove from external store
                if self.store:
                    self.store.delete(session_id)
            
            logger.debug(f"Cleaned up {len(expired)} expired sessions")
            return len(expired)

    def get_session_count(self) -> int:
        """Get total session count"""
        with self._lock:
            return len(self._sessions)

    def get_active_session_count(self) -> int:
        """Get active session count"""
        with self._lock:
            return sum(1 for s in self._sessions.values() if s.is_valid and not s.is_expired())

    def validate_session(self, session_id: str) -> bool:
        """Validate a session"""
        session = self.get_session(session_id)
        return session is not None and session.is_valid and not session.is_expired()

    def get_stats(self) -> Dict[str, Any]:
        """Get session manager statistics"""
        with self._lock:
            return {
                **self._stats,
                "session_timeout": self.config.session_timeout,
                "max_sessions": self.config.max_sessions
            }

    def close(self) -> None:
        """Close session manager"""
        self.stop_cleanup()
        self.invalidate_all_sessions()
        logger.info("Session manager closed")

    def __enter__(self):
        self.start_cleanup()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Global SessionManager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get the global session manager"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


def create_session_manager(config: Optional[SessionConfig] = None, 
                           store: Optional[Any] = None) -> SessionManager:
    """Create a session manager"""
    return SessionManager(config, store)
