"""
Secrets Management Module
Handles sensitive data like API keys, passwords, and tokens.
"""

import os
import json
import base64
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class SecretsManager:
    """
    Manages sensitive configuration data with optional encryption.
    
    Supports:
    - Plain JSON storage
    - Encrypted storage using Fernet
    - Environment variable override
    - Secure memory handling
    """
    
    def __init__(self, secrets_dir: str = "config", encryption_key: Optional[str] = None):
        self.secrets_dir = secrets_dir
        self.encryption_key = encryption_key or os.getenv("FFGC_ENCRYPTION_KEY")
        self._secrets: Dict[str, Any] = {}
        self._loaded = False
        self._fernet = None
        
        if self.encryption_key:
            try:
                self._fernet = Fernet(self.encryption_key.encode())
            except Exception as e:
                logger.error(f"Invalid encryption key: {e}")
                self._fernet = None
                
    def _ensure_secrets_dir(self):
        """Ensure secrets directory exists."""
        Path(self.secrets_dir).mkdir(parents=True, exist_ok=True)
        
    def _get_secrets_file(self) -> str:
        """Get the secrets file path."""
        if self._fernet:
            return os.path.join(self.secrets_dir, "secrets.enc.json")
        return os.path.join(self.secrets_dir, "secrets.json")
    
    def _encrypt_data(self, data: Dict[str, Any]) -> str:
        """Encrypt data using Fernet."""
        if not self._fernet:
            raise RuntimeError("Encryption not available")
        
        json_data = json.dumps(data).encode()
        encrypted = self._fernet.encrypt(json_data)
        return base64.b64encode(encrypted).decode()
    
    def _decrypt_data(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt data using Fernet."""
        if not self._fernet:
            raise RuntimeError("Encryption not available")
        
        decoded = base64.b64decode(encrypted_data.encode())
        decrypted = self._fernet.decrypt(decoded)
        return json.loads(decrypted.decode())
    
    def load(self, secrets_file: Optional[str] = None) -> bool:
        """Load secrets from file."""
        self._ensure_secrets_dir()
        secrets_file = secrets_file or self._get_secrets_file()
        
        if not os.path.exists(secrets_file):
            logger.warning(f"Secrets file not found: {secrets_file}")
            self._secrets = {}
            self._loaded = True
            return False
            
        try:
            with open(secrets_file, 'r') as f:
                content = f.read().strip()
                
            if self._fernet:
                # Decrypt the content
                self._secrets = self._decrypt_data(content)
            else:
                # Parse as JSON
                self._secrets = json.loads(content)
            
            self._loaded = True
            logger.info(f"Loaded secrets from {secrets_file}")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in secrets file: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to load secrets: {e}")
            return False
    
    def save(self, secrets_file: Optional[str] = None) -> bool:
        """Save secrets to file."""
        self._ensure_secrets_dir()
        secrets_file = secrets_file or self._get_secrets_file()
        
        try:
            if self._fernet:
                content = self._encrypt_data(self._secrets)
            else:
                content = json.dumps(self._secrets, indent=2)
            
            # Write with restricted permissions
            old_umask = os.umask(0o077)
            try:
                with open(secrets_file, 'w') as f:
                    f.write(content)
            finally:
                os.umask(old_umask)
            
            logger.info(f"Saved secrets to {secrets_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save secrets: {e}")
            return False
    
    def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """Get a secret value by key."""
        if not self._loaded:
            self.load()
        
        # Check environment variable first
        env_key = f"FFGC_SECRET_{key.upper()}"
        env_value = os.getenv(env_key)
        if env_value is not None:
            return env_value
        
        return self._secrets.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a secret value."""
        self._secrets[key] = value
        
    def remove(self, key: str) -> bool:
        """Remove a secret value."""
        if key in self._secrets:
            del self._secrets[key]
            return True
        return False
    
    def has(self, key: str) -> bool:
        """Check if a secret exists."""
        if not self._loaded:
            self.load()
        
        env_key = f"FFGC_SECRET_{key.upper()}"
        if os.getenv(env_key) is not None:
            return True
            
        return key in self._secrets
    
    def list_keys(self) -> list:
        """List all secret keys."""
        if not self._loaded:
            self.load()
        return list(self._secrets.keys())
    
    def clear(self) -> None:
        """Clear all secrets from memory."""
        self._secrets.clear()
        self._loaded = False
    
    def generate_encryption_key(self) -> str:
        """Generate a new encryption key."""
        return Fernet.generate_key().decode()
    
    def mask_value(self, value: str, show_last: int = 4) -> str:
        """Mask a sensitive value for display."""
        if not value or len(value) <= show_last:
            return value
        return "*" * (len(value) - show_last) + value[-show_last:]


# Global secrets manager instance
secrets_manager = SecretsManager()
