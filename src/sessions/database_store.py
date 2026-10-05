"""
Database Session Store for Free Fire Guest Account Checker
Stores sessions in SQLite database
"""

from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from src.sessions.session import Session, SessionData
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DatabaseSessionStoreConfig:
    """Database session store configuration"""
    database_path: str = "data/sessions.db"
    table_name: str = "sessions"
    max_connections: int = 10
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DatabaseSessionStoreConfig:
        """Create from dictionary"""
        return cls(
            database_path=data.get("database_path", "data/sessions.db"),
            table_name=data.get("table_name", "sessions"),
            max_connections=data.get("max_connections", 10)
        )


class DatabaseSessionStore:
    """Database-based session store"""

    def __init__(self, config: Optional[DatabaseSessionStoreConfig] = None):
        self.config = config or DatabaseSessionStoreConfig()
        self._lock = threading.RLock()
        self._connection: Optional[sqlite3.Connection] = None
        
        # Initialize database
        self._initialize_database()

    def _initialize_database(self) -> None:
        """Initialize database tables"""
        with self._lock:
            try:
                # Ensure directory exists
                Path(self.config.database_path).parent.mkdir(parents=True, exist_ok=True)
                
                # Connect to database
                self._connection = sqlite3.connect(
                    self.config.database_path,
                    check_same_thread=False
                )
                
                # Enable foreign keys
                self._connection.execute("PRAGMA foreign_keys = ON")
                
                # Create sessions table
                self._connection.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.config.table_name} (
                        session_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        username TEXT,
                        email TEXT,
                        roles TEXT,
                        permissions TEXT,
                        access_token TEXT,
                        refresh_token TEXT,
                        token_expiry REAL,
                        ip_address TEXT,
                        user_agent TEXT,
                        device_id TEXT,
                        custom_data TEXT,
                        created_at REAL NOT NULL,
                        last_accessed REAL NOT NULL,
                        expires_at REAL NOT NULL,
                        is_valid INTEGER NOT NULL DEFAULT 1
                    )
                """)
                
                # Create user index
                self._connection.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.config.table_name}_user_id 
                    ON {self.config.table_name}(user_id)
                """)
                
                # Create expiry index
                self._connection.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.config.table_name}_expires_at 
                    ON {self.config.table_name}(expires_at)
                """)
                
                # Create is_valid index
                self._connection.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.config.table_name}_is_valid 
                    ON {self.config.table_name}(is_valid)
                """)
                
                self._connection.commit()
                logger.info(f"Initialized session database at {self.config.database_path}")
                
            except Exception as e:
                logger.error(f"Failed to initialize session database: {e}")
                raise

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        if self._connection is None:
            self._initialize_database()
        return self._connection

    def _serialize_data(self, data: Any) -> str:
        """Serialize data to JSON string"""
        if data is None:
            return ""
        if isinstance(data, (list, dict)):
            return json.dumps(data)
        return str(data)

    def _deserialize_data(self, data: str, default: Any = None) -> Any:
        """Deserialize data from JSON string"""
        if not data:
            return default
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return data

    def save(self, session: Session) -> bool:
        """Save a session to database"""
        with self._lock:
            try:
                conn = self._get_connection()
                
                # Convert session to database row
                row = {
                    "session_id": session.session_id,
                    "user_id": session.data.user_id,
                    "username": session.data.username,
                    "email": session.data.email,
                    "roles": self._serialize_data(session.data.roles),
                    "permissions": self._serialize_data(session.data.permissions),
                    "access_token": session.data.access_token,
                    "refresh_token": session.data.refresh_token,
                    "token_expiry": session.data.token_expiry,
                    "ip_address": session.data.ip_address,
                    "user_agent": session.data.user_agent,
                    "device_id": session.data.device_id,
                    "custom_data": self._serialize_data(session.data.custom_data),
                    "created_at": session.created_at,
                    "last_accessed": session.last_accessed,
                    "expires_at": session.expires_at,
                    "is_valid": 1 if session.is_valid else 0
                }
                
                # Upsert session
                conn.execute(f"""
                    INSERT OR REPLACE INTO {self.config.table_name} 
                    (session_id, user_id, username, email, roles, permissions, 
                     access_token, refresh_token, token_expiry, ip_address, 
                     user_agent, device_id, custom_data, created_at, last_accessed, 
                     expires_at, is_valid)
                    VALUES (:session_id, :user_id, :username, :email, :roles, :permissions,
                            :access_token, :refresh_token, :token_expiry, :ip_address,
                            :user_agent, :device_id, :custom_data, :created_at, :last_accessed,
                            :expires_at, :is_valid)
                """, row)
                
                conn.commit()
                logger.debug(f"Saved session {session.session_id} to database")
                return True
                
            except Exception as e:
                logger.error(f"Failed to save session {session.session_id} to database: {e}")
                return False

    def get(self, session_id: str) -> Optional[Session]:
        """Get a session from database"""
        with self._lock:
            try:
                conn = self._get_connection()
                
                cursor = conn.execute(f"""
                    SELECT * FROM {self.config.table_name} 
                    WHERE session_id = ?
                """, (session_id,))
                
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                # Convert row to session
                session_data = SessionData(
                    user_id=row[1],
                    username=row[2],
                    email=row[3],
                    roles=self._deserialize_data(row[4], []),
                    permissions=self._deserialize_data(row[5], []),
                    access_token=row[6],
                    refresh_token=row[7],
                    token_expiry=row[8],
                    ip_address=row[9],
                    user_agent=row[10],
                    device_id=row[11],
                    custom_data=self._deserialize_data(row[12], {})
                )
                
                session = Session(
                    session_id=row[0],
                    data=session_data,
                    created_at=row[13],
                    last_accessed=row[14],
                    expires_at=row[15],
                    is_valid=bool(row[16])
                )
                
                if session.is_expired():
                    self.delete(session_id)
                    return None
                
                logger.debug(f"Loaded session {session_id} from database")
                return session
                
            except Exception as e:
                logger.error(f"Failed to load session {session_id} from database: {e}")
                return None

    def get_by_user(self, user_id: str) -> List[Session]:
        """Get all sessions for a user"""
        with self._lock:
            sessions = []
            
            try:
                conn = self._get_connection()
                
                cursor = conn.execute(f"""
                    SELECT * FROM {self.config.table_name} 
                    WHERE user_id = ? AND is_valid = 1 AND expires_at > strftime('%s', 'now')
                """, (user_id,))
                
                for row in cursor:
                    session_data = SessionData(
                        user_id=row[1],
                        username=row[2],
                        email=row[3],
                        roles=self._deserialize_data(row[4], []),
                        permissions=self._deserialize_data(row[5], []),
                        access_token=row[6],
                        refresh_token=row[7],
                        token_expiry=row[8],
                        ip_address=row[9],
                        user_agent=row[10],
                        device_id=row[11],
                        custom_data=self._deserialize_data(row[12], {})
                    )
                    
                    session = Session(
                        session_id=row[0],
                        data=session_data,
                        created_at=row[13],
                        last_accessed=row[14],
                        expires_at=row[15],
                        is_valid=bool(row[16])
                    )
                    
                    sessions.append(session)
                
                logger.debug(f"Loaded {len(sessions)} sessions for user {user_id} from database")
                return sessions
                
            except Exception as e:
                logger.error(f"Failed to get sessions for user {user_id} from database: {e}")
                return []

    def delete(self, session_id: str) -> bool:
        """Delete a session from database"""
        with self._lock:
            try:
                conn = self._get_connection()
                
                cursor = conn.execute(f"""
                    DELETE FROM {self.config.table_name} 
                    WHERE session_id = ?
                """, (session_id,))
                
                result = cursor.rowcount > 0
                conn.commit()
                
                if result:
                    logger.debug(f"Deleted session {session_id} from database")
                
                return result
                
            except Exception as e:
                logger.error(f"Failed to delete session {session_id} from database: {e}")
                return False

    def clear(self) -> int:
        """Clear all sessions from database"""
        with self._lock:
            try:
                conn = self._get_connection()
                
                cursor = conn.execute(f"""
                    DELETE FROM {self.config.table_name}
                """)
                
                count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Cleared {count} sessions from database")
                return count
                
            except Exception as e:
                logger.error(f"Failed to clear sessions from database: {e}")
                return 0

    def cleanup_expired(self) -> int:
        """Cleanup expired sessions from database"""
        with self._lock:
            try:
                conn = self._get_connection()
                
                cursor = conn.execute(f"""
                    DELETE FROM {self.config.table_name} 
                    WHERE expires_at < strftime('%s', 'now')
                """)
                
                count = cursor.rowcount
                conn.commit()
                
                logger.debug(f"Cleaned up {count} expired sessions from database")
                return count
                
            except Exception as e:
                logger.error(f"Failed to cleanup expired sessions from database: {e}")
                return 0

    def list_all(self) -> List[Session]:
        """List all sessions"""
        with self._lock:
            sessions = []
            
            try:
                conn = self._get_connection()
                
                cursor = conn.execute(f"""
                    SELECT * FROM {self.config.table_name} 
                    WHERE is_valid = 1 AND expires_at > strftime('%s', 'now')
                """)
                
                for row in cursor:
                    session_data = SessionData(
                        user_id=row[1],
                        username=row[2],
                        email=row[3],
                        roles=self._deserialize_data(row[4], []),
                        permissions=self._deserialize_data(row[5], []),
                        access_token=row[6],
                        refresh_token=row[7],
                        token_expiry=row[8],
                        ip_address=row[9],
                        user_agent=row[10],
                        device_id=row[11],
                        custom_data=self._deserialize_data(row[12], {})
                    )
                    
                    session = Session(
                        session_id=row[0],
                        data=session_data,
                        created_at=row[13],
                        last_accessed=row[14],
                        expires_at=row[15],
                        is_valid=bool(row[16])
                    )
                    
                    sessions.append(session)
                
                logger.debug(f"Loaded {len(sessions)} sessions from database")
                return sessions
                
            except Exception as e:
                logger.error(f"Failed to list all sessions from database: {e}")
                return []

    def exists(self, session_id: str) -> bool:
        """Check if session exists in database"""
        with self._lock:
            try:
                conn = self._get_connection()
                
                cursor = conn.execute(f"""
                    SELECT 1 FROM {self.config.table_name} 
                    WHERE session_id = ?
                """, (session_id,))
                
                return cursor.fetchone() is not None
                
            except Exception as e:
                logger.error(f"Failed to check if session {session_id} exists: {e}")
                return False

    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics"""
        with self._lock:
            try:
                conn = self._get_connection()
                
                # Get total sessions
                cursor = conn.execute(f"""
                    SELECT COUNT(*) FROM {self.config.table_name}
                """)
                total = cursor.fetchone()[0]
                
                # Get active sessions
                cursor = conn.execute(f"""
                    SELECT COUNT(*) FROM {self.config.table_name} 
                    WHERE is_valid = 1 AND expires_at > strftime('%s', 'now')
                """)
                active = cursor.fetchone()[0]
                
                # Get database size
                cursor = conn.execute(f"""
                    SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()
                """)
                size = cursor.fetchone()
                
                return {
                    "type": "database",
                    "database_path": self.config.database_path,
                    "table_name": self.config.table_name,
                    "total_sessions": total,
                    "active_sessions": active,
                    "database_size": size[0] if size else 0
                }
                
            except Exception as e:
                logger.error(f"Failed to get database stats: {e}")
                return {
                    "type": "database",
                    "error": str(e)
                }

    def close(self) -> None:
        """Close database connection"""
        with self._lock:
            if self._connection:
                try:
                    self._connection.close()
                    self._connection = None
                    logger.info("Database session store connection closed")
                except Exception as e:
                    logger.error(f"Failed to close database connection: {e}")
