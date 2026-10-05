"""
File Session Store for Free Fire Guest Account Checker
Stores sessions in files
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from src.sessions.session import Session, SessionData
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class FileSessionStoreConfig:
    """File session store configuration"""
    directory: str = "sessions"
    file_extension: str = ".session"
    pretty_json: bool = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FileSessionStoreConfig:
        """Create from dictionary"""
        return cls(
            directory=data.get("directory", "sessions"),
            file_extension=data.get("file_extension", ".session"),
            pretty_json=data.get("pretty_json", False)
        )


class FileSessionStore:
    """File-based session store"""

    def __init__(self, config: Optional[FileSessionStoreConfig] = None):
        self.config = config or FileSessionStoreConfig()
        self._lock = threading.RLock()
        
        # Create directory if it doesn't exist
        Path(self.config.directory).mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, session_id: str) -> str:
        """Get file path for a session"""
        return os.path.join(self.config.directory, f"{session_id}{self.config.file_extension}")

    def save(self, session: Session) -> bool:
        """Save a session to file"""
        with self._lock:
            try:
                file_path = self._get_file_path(session.session_id)
                
                with open(file_path, 'w') as f:
                    json.dump(
                        session.to_dict(),
                        f,
                        indent=2 if self.config.pretty_json else None
                    )
                
                logger.debug(f"Saved session {session.session_id} to file")
                return True
            except Exception as e:
                logger.error(f"Failed to save session {session.session_id}: {e}")
                return False

    def get(self, session_id: str) -> Optional[Session]:
        """Get a session from file"""
        with self._lock:
            try:
                file_path = self._get_file_path(session_id)
                
                if not os.path.exists(file_path):
                    return None
                
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                session = Session.from_dict(data)
                
                # Check if session is still valid
                if session.is_expired():
                    self.delete(session_id)
                    return None
                
                logger.debug(f"Loaded session {session_id} from file")
                return session
            except Exception as e:
                logger.error(f"Failed to load session {session_id}: {e}")
                return None

    def get_by_user(self, user_id: str) -> List[Session]:
        """Get all sessions for a user"""
        with self._lock:
            sessions = []
            
            for file_name in os.listdir(self.config.directory):
                if file_name.endswith(self.config.file_extension):
                    session_id = file_name[:-len(self.config.file_extension)]
                    session = self.get(session_id)
                    
                    if session and session.get_user_id() == user_id:
                        sessions.append(session)
            
            return sessions

    def delete(self, session_id: str) -> bool:
        """Delete a session file"""
        with self._lock:
            try:
                file_path = self._get_file_path(session_id)
                
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Deleted session {session_id} file")
                    return True
                return False
            except Exception as e:
                logger.error(f"Failed to delete session {session_id}: {e}")
                return False

    def clear(self) -> int:
        """Clear all session files"""
        with self._lock:
            count = 0
            
            for file_name in os.listdir(self.config.directory):
                if file_name.endswith(self.config.file_extension):
                    try:
                        file_path = os.path.join(self.config.directory, file_name)
                        os.remove(file_path)
                        count += 1
                    except Exception as e:
                        logger.error(f"Failed to delete session file {file_name}: {e}")
            
            logger.info(f"Cleared {count} session files")
            return count

    def cleanup_expired(self) -> int:
        """Cleanup expired session files"""
        with self._lock:
            count = 0
            now = time.time()
            
            for file_name in os.listdir(self.config.directory):
                if file_name.endswith(self.config.file_extension):
                    session_id = file_name[:-len(self.config.file_extension)]
                    session = self.get(session_id)
                    
                    if session and session.is_expired():
                        self.delete(session_id)
                        count += 1
            
            logger.debug(f"Cleaned up {count} expired session files")
            return count

    def list_all(self) -> List[Session]:
        """List all sessions"""
        with self._lock:
            sessions = []
            
            for file_name in os.listdir(self.config.directory):
                if file_name.endswith(self.config.file_extension):
                    session_id = file_name[:-len(self.config.file_extension)]
                    session = self.get(session_id)
                    
                    if session:
                        sessions.append(session)
            
            return sessions

    def exists(self, session_id: str) -> bool:
        """Check if session file exists"""
        file_path = self._get_file_path(session_id)
        return os.path.exists(file_path)

    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics"""
        with self._lock:
            file_count = sum(
                1 for f in os.listdir(self.config.directory)
                if f.endswith(self.config.file_extension)
            )
            
            return {
                "type": "file",
                "directory": self.config.directory,
                "file_count": file_count,
                "file_extension": self.config.file_extension
            }
