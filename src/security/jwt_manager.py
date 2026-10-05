"""
JWT Manager for Free Fire Guest Account Checker
Handles JWT token generation, verification, and management
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import jwt
from jwt import PyJWKClient, PyJWT
from python_jose import jws
from python_jose.cryptodome import aes, rsa

from src.utils.logging import get_logger
from src.utils.helpers import get_timestamp
from config.settings import Settings, get_settings

logger = get_logger(__name__)


@dataclass
class TokenPayload:
    """JWT token payload"""
    sub: str  # Subject (user ID)
    iat: float = field(default_factory=time.time)  # Issued at
    exp: float = 0.0  # Expiration
    nbf: float = 0.0  # Not before
    jti: str = field(default_factory=lambda: secrets.token_hex(16))  # JWT ID
    iss: str = "FreeFireGuestChecker"  # Issuer
    aud: str = "api"  # Audience
    
    # Custom claims
    username: Optional[str] = None
    email: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    session_id: Optional[str] = None
    
    def __post_init__(self):
        if self.exp == 0.0:
            self.exp = self.iat + 3600  # Default 1 hour expiration
        if self.nbf == 0.0:
            self.nbf = self.iat
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "sub": self.sub,
            "iat": self.iat,
            "exp": self.exp,
            "nbf": self.nbf,
            "jti": self.jti,
            "iss": self.iss,
            "aud": self.aud,
            "username": self.username,
            "email": self.email,
            "roles": self.roles,
            "permissions": self.permissions,
            "session_id": self.session_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TokenPayload:
        """Create from dictionary"""
        return cls(
            sub=data.get("sub", ""),
            iat=data.get("iat", time.time()),
            exp=data.get("exp", 0.0),
            nbf=data.get("nbf", 0.0),
            jti=data.get("jti", secrets.token_hex(16)),
            iss=data.get("iss", "FreeFireGuestChecker"),
            aud=data.get("aud", "api"),
            username=data.get("username"),
            email=data.get("email"),
            roles=data.get("roles", []),
            permissions=data.get("permissions", []),
            session_id=data.get("session_id")
        )


@dataclass
class JWTConfig:
    """JWT configuration"""
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    issuer: str = "FreeFireGuestChecker"
    audience: str = "api"
    
    @classmethod
    def from_settings(cls, settings: Settings) -> JWTConfig:
        """Create from settings"""
        secret_key = settings.jwt_secret_key or secrets.token_hex(32)
        return cls(
            secret_key=secret_key,
            algorithm=settings.jwt_algorithm or "HS256",
            access_token_expire_minutes=settings.jwt_access_token_expire_minutes or 60,
            refresh_token_expire_days=settings.jwt_refresh_token_expire_days or 7,
            issuer=settings.jwt_issuer or "FreeFireGuestChecker",
            audience=settings.jwt_audience or "api"
        )


class JWTManager:
    """JWT token manager"""

    def __init__(self, config: Optional[JWTConfig] = None):
        self.config = config or JWTConfig(
            secret_key=secrets.token_hex(32)
        )
        self._jwt: PyJWT = PyJWT()
        self._revoked_tokens: set = set()
        self._active_sessions: Dict[str, Dict[str, Any]] = {}

    def create_access_token(
        self,
        subject: str,
        username: Optional[str] = None,
        email: Optional[str] = None,
        roles: Optional[List[str]] = None,
        permissions: Optional[List[str]] = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create an access token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=self.config.access_token_expire_minutes
            )

        to_encode = TokenPayload(
            sub=subject,
            iat=datetime.utcnow().timestamp(),
            exp=expire.timestamp(),
            username=username,
            email=email,
            roles=roles or [],
            permissions=permissions or []
        ).to_dict()

        encoded_jwt = self._jwt.encode(
            to_encode,
            self.config.secret_key,
            algorithm=self.config.algorithm
        )

        logger.debug(f"Created access token for {subject}")
        return encoded_jwt

    def create_refresh_token(
        self,
        subject: str,
        session_id: Optional[str] = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a refresh token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                days=self.config.refresh_token_expire_days
            )

        jti = secrets.token_hex(16)
        session_id = session_id or secrets.token_hex(16)

        to_encode = TokenPayload(
            sub=subject,
            iat=datetime.utcnow().timestamp(),
            exp=expire.timestamp(),
            jti=jti,
            session_id=session_id
        ).to_dict()

        encoded_jwt = self._jwt.encode(
            to_encode,
            self.config.secret_key,
            algorithm=self.config.algorithm
        )

        # Store active session
        self._active_sessions[session_id] = {
            "subject": subject,
            "token": encoded_jwt,
            "created_at": datetime.utcnow().timestamp(),
            "expires_at": expire.timestamp()
        }

        logger.debug(f"Created refresh token for {subject} with session {session_id}")
        return encoded_jwt

    def verify_token(
        self,
        token: str,
        verify_exp: bool = True,
        verify_iat: bool = True,
        verify_nbf: bool = True
    ) -> Optional[TokenPayload]:
        """Verify a JWT token"""
        try:
            # Check if token is revoked
            payload_dict = self._jwt.decode(
                token,
                self.config.secret_key,
                algorithms=[self.config.algorithm],
                options={
                    "verify_exp": verify_exp,
                    "verify_iat": verify_iat,
                    "verify_nbf": verify_nbf,
                    "verify_aud": False,
                    "verify_iss": False
                }
            )

            # Check if token is revoked
            jti = payload_dict.get("jti")
            if jti and jti in self._revoked_tokens:
                logger.warning(f"Token {jti} is revoked")
                return None

            return TokenPayload.from_dict(payload_dict)

        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Error verifying token: {e}")
            return None

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode a JWT token without verification"""
        try:
            return self._jwt.decode(
                token,
                options={"verify_signature": False}
            )
        except Exception as e:
            logger.error(f"Error decoding token: {e}")
            return None

    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Refresh an access token using a refresh token"""
        payload = self.verify_token(refresh_token, verify_exp=False)
        
        if not payload:
            logger.warning("Invalid refresh token")
            return None

        # Check if session is still active
        session_id = payload.session_id
        if session_id and session_id not in self._active_sessions:
            logger.warning(f"Session {session_id} is not active")
            return None

        # Create new access token
        new_token = self.create_access_token(
            subject=payload.sub,
            username=payload.username,
            email=payload.email,
            roles=payload.roles,
            permissions=payload.permissions
        )

        logger.info(f"Refreshed access token for {payload.sub}")
        return new_token

    def revoke_token(self, token: str) -> bool:
        """Revoke a token"""
        payload = self.decode_token(token)
        if not payload:
            return False

        jti = payload.get("jti")
        if jti:
            self._revoked_tokens.add(jti)
            
            # Also revoke session if it's a refresh token
            session_id = payload.get("session_id")
            if session_id and session_id in self._active_sessions:
                del self._active_sessions[session_id]
            
            logger.info(f"Revoked token {jti}")
            return True
        
        return False

    def revoke_session(self, session_id: str) -> bool:
        """Revoke all tokens for a session"""
        if session_id in self._active_sessions:
            session = self._active_sessions[session_id]
            token = session.get("token")
            
            if token:
                payload = self.decode_token(token)
                if payload:
                    jti = payload.get("jti")
                    if jti:
                        self._revoked_tokens.add(jti)
            
            del self._active_sessions[session_id]
            logger.info(f"Revoked session {session_id}")
            return True
        
        return False

    def revoke_all_tokens(self, subject: str) -> int:
        """Revoke all tokens for a user"""
        count = 0
        
        # Find and revoke all sessions for this user
        sessions_to_remove = []
        for session_id, session in self._active_sessions.items():
            if session.get("subject") == subject:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            self.revoke_session(session_id)
            count += 1
        
        logger.info(f"Revoked {count} tokens for user {subject}")
        return count

    def list_active_sessions(self, subject: Optional[str] = None) -> List[Dict[str, Any]]:
        """List active sessions"""
        if subject:
            return [
                session for session in self._active_sessions.values()
                if session.get("subject") == subject
            ]
        return list(self._active_sessions.values())

    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions"""
        now = datetime.utcnow().timestamp()
        expired_sessions = []
        
        for session_id, session in self._active_sessions.items():
            if session.get("expires_at", 0) < now:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self._active_sessions[session_id]
        
        logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
        return len(expired_sessions)

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information"""
        return self._active_sessions.get(session_id)


# Global JWT Manager instance
_jwt_manager: Optional[JWTManager] = None


def get_jwt_manager() -> JWTManager:
    """Get the global JWT manager"""
    global _jwt_manager
    if _jwt_manager is None:
        _jwt_manager = JWTManager()
    return _jwt_manager


def generate_jwt_token(
    subject: str,
    username: Optional[str] = None,
    email: Optional[str] = None,
    roles: Optional[List[str]] = None,
    permissions: Optional[List[str]] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Generate a JWT token"""
    return get_jwt_manager().create_access_token(
        subject=subject,
        username=username,
        email=email,
        roles=roles,
        permissions=permissions,
        expires_delta=expires_delta
    )


def verify_jwt_token(
    token: str,
    verify_exp: bool = True,
    verify_iat: bool = True,
    verify_nbf: bool = True
) -> Optional[TokenPayload]:
    """Verify a JWT token"""
    return get_jwt_manager().verify_token(
        token=token,
        verify_exp=verify_exp,
        verify_iat=verify_iat,
        verify_nbf=verify_nbf
    )
