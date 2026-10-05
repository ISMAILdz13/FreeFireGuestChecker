"""
Security Configuration for Free Fire Guest Account Checker
Centralized security settings and configuration
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from src.utils.logging import get_logger
from config.settings import Settings, get_settings

logger = get_logger(__name__)


@dataclass
class SecurityConfig:
    """Security configuration"""
    # JWT Configuration
    jwt_secret_key: str = field(default_factory=lambda: secrets.token_hex(32))
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7
    jwt_issuer: str = "FreeFireGuestChecker"
    jwt_audience: str = "api"
    
    # Password Configuration
    password_algorithm: str = "bcrypt"
    password_rounds: int = 12
    password_min_length: int = 8
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digit: bool = True
    password_require_special: bool = True
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window_seconds: float = 60.0
    rate_limit_burst_requests: int = 10
    rate_limit_burst_seconds: float = 1.0
    
    # CORS Configuration
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = field(default_factory=lambda: ["*"])
    cors_allow_headers: List[str] = field(default_factory=lambda: ["*"])
    
    # CSRF Configuration
    csrf_enabled: bool = True
    csrf_secret_key: str = field(default_factory=lambda: secrets.token_hex(32))
    csrf_cookie_name: str = "csrf_token"
    csrf_header_name: str = "X-CSRF-Token"
    
    # Session Configuration
    session_secret_key: str = field(default_factory=lambda: secrets.token_hex(32))
    session_cookie_name: str = "session"
    session_cookie_secure: bool = True
    session_cookie_httponly: bool = True
    session_cookie_samesite: str = "lax"
    session_timeout_seconds: int = 3600
    
    # API Key Configuration
    api_key_required: bool = False
    api_keys: Set[str] = field(default_factory=set)
    
    # SSL/TLS Configuration
    ssl_enabled: bool = False
    ssl_cert_file: Optional[str] = None
    ssl_key_file: Optional[str] = None
    
    # Security Headers
    security_headers_enabled: bool = True
    content_security_policy: str = "default-src 'self' 'unsafe-inline' 'unsafe-eval'; img-src 'self' data:;"
    strict_transport_security: str = "max-age=31536000; includeSubDomains"
    x_frame_options: str = "SAMEORIGIN"
    x_content_type_options: str = "nosniff"
    x_xss_protection: str = "1; mode=block"
    
    # Logging Configuration
    log_security_events: bool = True
    log_failed_attempts: bool = True
    
    @classmethod
    def from_settings(cls, settings: Settings) -> SecurityConfig:
        """Create from settings"""
        return cls(
            # JWT Configuration
            jwt_secret_key=settings.jwt_secret_key or secrets.token_hex(32),
            jwt_algorithm=settings.jwt_algorithm or "HS256",
            jwt_access_token_expire_minutes=settings.jwt_access_token_expire_minutes or 60,
            jwt_refresh_token_expire_days=settings.jwt_refresh_token_expire_days or 7,
            jwt_issuer=settings.jwt_issuer or "FreeFireGuestChecker",
            jwt_audience=settings.jwt_audience or "api",
            
            # Password Configuration
            password_algorithm=settings.password_algorithm or "bcrypt",
            password_rounds=settings.password_rounds or 12,
            password_min_length=settings.password_min_length or 8,
            password_require_uppercase=settings.password_require_uppercase if settings.password_require_uppercase is not None else True,
            password_require_lowercase=settings.password_require_lowercase if settings.password_require_lowercase is not None else True,
            password_require_digit=settings.password_require_digit if settings.password_require_digit is not None else True,
            password_require_special=settings.password_require_special if settings.password_require_special is not None else True,
            
            # Rate Limiting
            rate_limit_enabled=settings.rate_limit_enabled if settings.rate_limit_enabled is not None else True,
            rate_limit_requests=settings.rate_limit_requests or 100,
            rate_limit_window_seconds=settings.rate_limit_window_seconds or 60.0,
            rate_limit_burst_requests=settings.rate_limit_burst_requests or 10,
            rate_limit_burst_seconds=settings.rate_limit_burst_seconds or 1.0,
            
            # CORS Configuration
            cors_origins=settings.cors_origins or ["*"],
            cors_allow_credentials=settings.cors_allow_credentials if settings.cors_allow_credentials is not None else True,
            cors_allow_methods=settings.cors_allow_methods or ["*"],
            cors_allow_headers=settings.cors_allow_headers or ["*"],
            
            # CSRF Configuration
            csrf_enabled=settings.csrf_enabled if settings.csrf_enabled is not None else True,
            csrf_secret_key=settings.csrf_secret_key or secrets.token_hex(32),
            csrf_cookie_name=settings.csrf_cookie_name or "csrf_token",
            csrf_header_name=settings.csrf_header_name or "X-CSRF-Token",
            
            # Session Configuration
            session_secret_key=settings.session_secret_key or secrets.token_hex(32),
            session_cookie_name=settings.session_cookie_name or "session",
            session_cookie_secure=settings.session_cookie_secure if settings.session_cookie_secure is not None else True,
            session_cookie_httponly=settings.session_cookie_httponly if settings.session_cookie_httponly is not None else True,
            session_cookie_samesite=settings.session_cookie_samesite or "lax",
            session_timeout_seconds=settings.session_timeout_seconds or 3600,
            
            # SSL/TLS Configuration
            ssl_enabled=settings.ssl_enabled if settings.ssl_enabled is not None else False,
            ssl_cert_file=settings.ssl_cert_file,
            ssl_key_file=settings.ssl_key_file,
            
            # Logging Configuration
            log_security_events=settings.log_security_events if settings.log_security_events is not None else True,
            log_failed_attempts=settings.log_failed_attempts if settings.log_failed_attempts is not None else True
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding sensitive data)"""
        return {
            "jwt_algorithm": self.jwt_algorithm,
            "jwt_access_token_expire_minutes": self.jwt_access_token_expire_minutes,
            "jwt_refresh_token_expire_days": self.jwt_refresh_token_expire_days,
            "jwt_issuer": self.jwt_issuer,
            "jwt_audience": self.jwt_audience,
            
            "password_algorithm": self.password_algorithm,
            "password_rounds": self.password_rounds,
            "password_min_length": self.password_min_length,
            "password_require_uppercase": self.password_require_uppercase,
            "password_require_lowercase": self.password_require_lowercase,
            "password_require_digit": self.password_require_digit,
            "password_require_special": self.password_require_special,
            
            "rate_limit_enabled": self.rate_limit_enabled,
            "rate_limit_requests": self.rate_limit_requests,
            "rate_limit_window_seconds": self.rate_limit_window_seconds,
            "rate_limit_burst_requests": self.rate_limit_burst_requests,
            "rate_limit_burst_seconds": self.rate_limit_burst_seconds,
            
            "cors_origins": self.cors_origins,
            "cors_allow_credentials": self.cors_allow_credentials,
            "cors_allow_methods": self.cors_allow_methods,
            "cors_allow_headers": self.cors_allow_headers,
            
            "csrf_enabled": self.csrf_enabled,
            "csrf_cookie_name": self.csrf_cookie_name,
            "csrf_header_name": self.csrf_header_name,
            
            "session_cookie_name": self.session_cookie_name,
            "session_cookie_secure": self.session_cookie_secure,
            "session_cookie_httponly": self.session_cookie_httponly,
            "session_cookie_samesite": self.session_cookie_samesite,
            "session_timeout_seconds": self.session_timeout_seconds,
            
            "ssl_enabled": self.ssl_enabled,
            "ssl_cert_file": self.ssl_cert_file,
            "ssl_key_file": self.ssl_key_file,
            
            "security_headers_enabled": self.security_headers_enabled,
            "content_security_policy": self.content_security_policy,
            "strict_transport_security": self.strict_transport_security,
            "x_frame_options": self.x_frame_options,
            "x_content_type_options": self.x_content_type_options,
            "x_xss_protection": self.x_xss_protection,
            
            "log_security_events": self.log_security_events,
            "log_failed_attempts": self.log_failed_attempts
        }
    
    def add_api_key(self, key: str) -> None:
        """Add an API key"""
        self.api_keys.add(key)
        self.api_key_required = True
        logger.info(f"Added API key: {key[:8]}...")
    
    def remove_api_key(self, key: str) -> bool:
        """Remove an API key"""
        if key in self.api_keys:
            self.api_keys.remove(key)
            logger.info(f"Removed API key: {key[:8]}...")
            return True
        return False
    
    def validate_api_key(self, key: str) -> bool:
        """Validate an API key"""
        if not self.api_key_required:
            return True
        return key in self.api_keys
    
    def generate_api_key(self, prefix: str = "sk") -> str:
        """Generate a new API key"""
        key = f"{prefix}_{secrets.token_hex(32)}"
        self.add_api_key(key)
        return key


# Global SecurityConfig instance
_security_config: Optional[SecurityConfig] = None


def get_security_config() -> SecurityConfig:
    """Get the global security configuration"""
    global _security_config
    if _security_config is None:
        _security_config = SecurityConfig.from_settings(get_settings())
    return _security_config


def reload_security_config() -> SecurityConfig:
    """Reload the security configuration from settings"""
    global _security_config
    _security_config = SecurityConfig.from_settings(get_settings())
    return _security_config
