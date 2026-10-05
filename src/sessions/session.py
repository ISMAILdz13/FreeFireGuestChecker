"""
Session for Free Fire Guest Account Checker
Represents a user session with authentication data
"""

from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Union

from src.utils.logging import get_logger
from src.utils.helpers import generate_id, get_timestamp

logger = get_logger(__name__)


@dataclass
class SessionData:
    """Session data container"""
    user_id: str
    username: Optional[str] = None
    email: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    
    # Authentication info
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expiry: float = 0.0
    
    # Session metadata
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_id: Optional[str] = None
    
    # Custom data
    custom_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "roles": self.roles,
            "permissions": self.permissions,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_expiry": self.token_expiry,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "device_id": self.device_id,
            "custom_data": self.custom_data
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SessionData:
        """Create from dictionary"""
        return cls(
            user_id=data.get("user_id", ""),
            username=data.get("username"),
            email=data.get("email"),
            roles=data.get("roles", []),
            permissions=data.get("permissions", []),
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            token_expiry=data.get("token_expiry", 0.0),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            device_id=data.get("device_id"),
            custom_data=data.get("custom_data", {})
        )


@dataclass
class Session:
    """User session representation"""
    session_id: str
    data: SessionData
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    expires_at: float = 0.0
    is_valid: bool = True
    
    def __post_init__(self):
        if self.expires_at == 0.0:
            # Default to 24 hours
            self.expires_at = self.created_at + 86400

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary"""
        return {
            "session_id": self.session_id,
            "data": self.data.to_dict(),
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "expires_at": self.expires_at,
            "is_valid": self.is_valid
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Session:
        """Create session from dictionary"""
        return cls(
            session_id=data.get("session_id", generate_id("session")),
            data=SessionData.from_dict(data.get("data", {})),
            created_at=data.get("created_at", time.time()),
            last_accessed=data.get("last_accessed", time.time()),
            expires_at=data.get("expires_at", time.time() + 86400),
            is_valid=data.get("is_valid", True)
        )
    
    @classmethod
    def create(cls, user_id: str, **kwargs) -> Session:
        """Create a new session"""
        session_data = SessionData(
            user_id=user_id,
            username=kwargs.get("username"),
            email=kwargs.get("email"),
            roles=kwargs.get("roles", []),
            permissions=kwargs.get("permissions", []),
            access_token=kwargs.get("access_token"),
            refresh_token=kwargs.get("refresh_token"),
            token_expiry=kwargs.get("token_expiry", 0.0),
            ip_address=kwargs.get("ip_address"),
            user_agent=kwargs.get("user_agent"),
            device_id=kwargs.get("device_id"),
            custom_data=kwargs.get("custom_data", {})
        )
        
        session_id = kwargs.get("session_id") or generate_id("session")
        expiry = kwargs.get("expires_in")
        
        session = cls(
            session_id=session_id,
            data=session_data,
            created_at=time.time(),
            last_accessed=time.time(),
            expires_at=time.time() + (expiry if expiry else 86400),
            is_valid=True
        )
        
        return session
    
    def touch(self) -> None:
        """Update last accessed time"""
        self.last_accessed = time.time()
    
    def extend(self, expiry: float) -> None:
        """Extend session expiration"""
        self.expires_at = time.time() + expiry
    
    def invalidate(self) -> None:
        """Invalidate session"""
        self.is_valid = False
        self.expires_at = time.time()
    
    def is_expired(self) -> bool:
        """Check if session has expired"""
        return time.time() > self.expires_at
    
    def get_remaining_time(self) -> float:
        """Get remaining time in seconds"""
        return max(0, self.expires_at - time.time())
    
    def has_permission(self, permission: str) -> bool:
        """Check if session has a specific permission"""
        return permission in self.data.permissions
    
    def has_role(self, role: str) -> bool:
        """Check if session has a specific role"""
        return role in self.data.roles
    
    def get_user_id(self) -> str:
        """Get the user ID"""
        return self.data.user_id
    
    def get_username(self) -> Optional[str]:
        """Get the username"""
        return self.data.username
    
    def get_access_token(self) -> Optional[str]:
        """Get the access token"""
        return self.data.access_token
    
    def get_refresh_token(self) -> Optional[str]:
        """Get the refresh token"""
        return self.data.refresh_token
    
    def set_access_token(self, token: str, expiry: float) -> None:
        """Set access token"""
        self.data.access_token = token
        self.data.token_expiry = expiry
    
    def set_refresh_token(self, token: str) -> None:
        """Set refresh token"""
        self.data.refresh_token = token
    
    def set_custom_data(self, key: str, value: Any) -> None:
        """Set custom session data"""
        self.data.custom_data[key] = value
    
    def get_custom_data(self, key: str, default: Any = None) -> Any:
        """Get custom session data"""
        return self.data.custom_data.get(key, default)
    
    def remove_custom_data(self, key: str) -> bool:
        """Remove custom session data"""
        if key in self.data.custom_data:
            del self.data.custom_data[key]
            return True
        return False
    
    def clear_custom_data(self) -> None:
        """Clear all custom session data"""
        self.data.custom_data.clear()
