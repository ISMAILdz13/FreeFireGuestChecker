"""
Password Hasher for Free Fire Guest Account Checker
Handles secure password hashing and verification
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import string
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from passlib.context import CryptContext
from passlib.hash import bcrypt, pbkdf2_sha256, argon2
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class HashConfig:
    """Password hashing configuration"""
    algorithm: str = "bcrypt"
    rounds: int = 12
    salt_size: int = 16
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> HashConfig:
        """Create from dictionary"""
        return cls(
            algorithm=data.get("algorithm", "bcrypt"),
            rounds=data.get("rounds", 12),
            salt_size=data.get("salt_size", 16)
        )


class PasswordHasher:
    """Secure password hasher"""

    def __init__(self, config: Optional[HashConfig] = None):
        self.config = config or HashConfig()
        self._context = self._create_context()

    def _create_context(self) -> CryptContext:
        """Create password hashing context"""
        if self.config.algorithm == "bcrypt":
            return CryptContext(
                schemes=["bcrypt"],
                deprecated=["md5_crypt", "sha1_crypt", "sha256_crypt", "sha512_crypt"]
            )
        elif self.config.algorithm == "pbkdf2_sha256":
            return CryptContext(
                schemes=["pbkdf2_sha256"],
                pbkdf2_sha256__default_rounds=self.config.rounds,
                pbkdf2_sha256__salt_size=self.config.salt_size
            )
        elif self.config.algorithm == "argon2":
            return CryptContext(
                schemes=["argon2"],
                argon2__rounds=self.config.rounds,
                argon2__salt_size=self.config.salt_size
            )
        else:
            # Default to bcrypt
            return CryptContext(
                schemes=["bcrypt"],
                deprecated=["md5_crypt", "sha1_crypt", "sha256_crypt", "sha512_crypt"]
            )

    def hash(self, password: str) -> str:
        """Hash a password"""
        if not password:
            raise ValueError("Password cannot be empty")

        hashed = self._context.hash(password)
        logger.debug(f"Hashed password with {self.config.algorithm}")
        return hashed

    def verify(self, password: str, hashed: str) -> bool:
        """Verify a password against a hash"""
        if not password or not hashed:
            return False

        try:
            result = self._context.verify(password, hashed)
            if result:
                logger.debug("Password verification successful")
            else:
                logger.warning("Password verification failed")
            return result
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False

    def needs_rehash(self, hashed: str) -> bool:
        """Check if a hash needs to be rehashed"""
        return self._context.needs_update(hashed)

    def rehash(self, password: str, old_hash: str) -> str:
        """Rehash a password if needed"""
        if self.needs_rehash(old_hash):
            return self.hash(password)
        return old_hash

    def generate_salt(self) -> str:
        """Generate a random salt"""
        return secrets.token_hex(self.config.salt_size)

    def generate_pepper(self) -> str:
        """Generate a random pepper (application-wide salt)"""
        return secrets.token_hex(32)

    def hash_with_pepper(self, password: str, pepper: str) -> str:
        """Hash a password with a pepper"""
        if not pepper:
            return self.hash(password)
        
        # Combine password with pepper
        combined = f"{password}{pepper}"
        return self.hash(combined)

    def verify_with_pepper(self, password: str, hashed: str, pepper: str) -> bool:
        """Verify a password against a hash with pepper"""
        if not pepper:
            return self.verify(password, hashed)
        
        combined = f"{password}{pepper}"
        return self.verify(combined, hashed)

    def generate_secure_password(self, length: int = 16) -> str:
        """Generate a secure random password"""
        if length < 8:
            length = 8
        
        characters = string.ascii_letters + string.digits + string.punctuation
        password = ''.join(secrets.choice(characters) for _ in range(length))
        
        # Ensure at least one character from each category
        if not any(c.islower() for c in password):
            password = password[:-1] + secrets.choice(string.ascii_lowercase)
        if not any(c.isupper() for c in password):
            password = password[:-1] + secrets.choice(string.ascii_uppercase)
        if not any(c.isdigit() for c in password):
            password = password[:-1] + secrets.choice(string.digits)
        if not any(c in string.punctuation for c in password):
            password = password[:-1] + secrets.choice(string.punctuation)
        
        return password

    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """Validate password strength"""
        score = 0
        suggestions = []
        
        # Length check
        if len(password) >= 12:
            score += 2
        elif len(password) >= 8:
            score += 1
        else:
            suggestions.append("Use at least 8 characters (12+ recommended)")
        
        # Character variety
        if any(c.islower() for c in password):
            score += 1
        else:
            suggestions.append("Include lowercase letters")
        
        if any(c.isupper() for c in password):
            score += 1
        else:
            suggestions.append("Include uppercase letters")
        
        if any(c.isdigit() for c in password):
            score += 1
        else:
            suggestions.append("Include numbers")
        
        if any(c in string.punctuation for c in password):
            score += 1
        else:
            suggestions.append("Include special characters")
        
        # Entropy check
        import math
        char_set_size = 0
        if any(c.islower() for c in password):
            char_set_size += 26
        if any(c.isupper() for c in password):
            char_set_size += 26
        if any(c.isdigit() for c in password):
            char_set_size += 10
        if any(c in string.punctuation for c in password):
            char_set_size += 32
        
        entropy = len(password) * math.log2(char_set_size) if char_set_size > 0 else 0
        
        if entropy < 28:
            suggestions.append("Increase password complexity")
        elif entropy < 60:
            score += 1
        else:
            score += 2
        
        # Strength level
        if score >= 8:
            strength = "strong"
        elif score >= 6:
            strength = "good"
        elif score >= 4:
            strength = "fair"
        else:
            strength = "weak"
        
        return {
            "score": score,
            "strength": strength,
            "suggestions": suggestions,
            "entropy": entropy,
            "length": len(password),
            "has_lower": any(c.islower() for c in password),
            "has_upper": any(c.isupper() for c in password),
            "has_digit": any(c.isdigit() for c in password),
            "has_special": any(c in string.punctuation for c in password)
        }


# Global PasswordHasher instance
_password_hasher: Optional[PasswordHasher] = None


def get_password_hasher() -> PasswordHasher:
    """Get the global password hasher"""
    global _password_hasher
    if _password_hasher is None:
        _password_hasher = PasswordHasher()
    return _password_hasher


def hash_password(password: str) -> str:
    """Hash a password"""
    return get_password_hasher().hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password"""
    return get_password_hasher().verify(password, hashed)
