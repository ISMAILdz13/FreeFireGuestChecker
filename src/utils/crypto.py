"""
Cryptography Utilities Module
Handles AES encryption/decryption and key generation for Free Fire API.
"""

import os
import base64
import logging
from typing import Tuple, Optional
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes

logger = logging.getLogger(__name__)


# Default AES key and IV for Free Fire API
# These are extracted from the original implementation
DEFAULT_API_KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
DEFAULT_API_IV = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

# AES key and IV for UID encryption
DEFAULT_UID_KEY = b"Yg&tc%DEuh6%Zc^8"
DEFAULT_UID_IV = b"6oyZDr22E3ychjM%"


class CryptoError(Exception):
    """Custom exception for cryptography errors."""
    pass


def generate_aes_key(key_size: int = 16) -> bytes:
    """
    Generate a random AES key.
    
    Args:
        key_size: Key size in bytes (16, 24, or 32 for AES-128, AES-192, AES-256)
        
    Returns:
        Random AES key
    """
    if key_size not in (16, 24, 32):
        raise ValueError("Key size must be 16, 24, or 32 bytes")
    return get_random_bytes(key_size)


def generate_aes_iv() -> bytes:
    """
    Generate a random AES initialization vector.
    
    Returns:
        Random 16-byte IV
    """
    return get_random_bytes(16)


def encrypt_aes_cbc(
    plaintext: bytes,
    key: bytes,
    iv: bytes,
    padding: bool = True,
) -> bytes:
    """
    Encrypt data using AES-CBC mode.
    
    Args:
        plaintext: Data to encrypt
        key: AES key (16, 24, or 32 bytes)
        iv: Initialization vector (16 bytes)
        padding: Whether to apply PKCS7 padding
        
    Returns:
        Encrypted data
        
    Raises:
        CryptoError: If encryption fails
    """
    try:
        cipher = AES.new(key, AES.MODE_CBC, iv)
        if padding:
            padded = pad(plaintext, AES.block_size)
        else:
            padded = plaintext
        return cipher.encrypt(padded)
    except Exception as e:
        logger.error(f"AES-CBC encryption failed: {e}")
        raise CryptoError(f"Encryption failed: {e}")


def decrypt_aes_cbc(
    ciphertext: bytes,
    key: bytes,
    iv: bytes,
    padding: bool = True,
) -> bytes:
    """
    Decrypt data using AES-CBC mode.
    
    Args:
        ciphertext: Data to decrypt
        key: AES key (16, 24, or 32 bytes)
        iv: Initialization vector (16 bytes)
        padding: Whether to remove PKCS7 padding
        
    Returns:
        Decrypted data
        
    Raises:
        CryptoError: If decryption fails
    """
    try:
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(ciphertext)
        if padding:
            return unpad(decrypted, AES.block_size)
        return decrypted
    except Exception as e:
        logger.error(f"AES-CBC decryption failed: {e}")
        raise CryptoError(f"Decryption failed: {e}")


def encrypt_api(hex_data: str, key: bytes = DEFAULT_API_KEY, iv: bytes = DEFAULT_API_IV) -> str:
    """
    Encrypt hex payload for Free Fire API requests.
    
    Args:
        hex_data: Hex string to encrypt
        key: AES key (default: Free Fire API key)
        iv: Initialization vector (default: Free Fire API IV)
        
    Returns:
        Hex string of encrypted data
    """
    try:
        plain = bytes.fromhex(hex_data)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        encrypted = cipher.encrypt(pad(plain, AES.block_size))
        return encrypted.hex()
    except Exception as e:
        logger.error(f"API encryption failed: {e}")
        raise CryptoError(f"API encryption failed: {e}")


def decrypt_api(
    encrypted_hex: str,
    key: bytes = DEFAULT_API_KEY,
    iv: bytes = DEFAULT_API_IV,
) -> str:
    """
    Decrypt Free Fire API response.
    
    Args:
        encrypted_hex: Hex string of encrypted data
        key: AES key (default: Free Fire API key)
        iv: Initialization vector (default: Free Fire API IV)
        
    Returns:
        Hex string of decrypted data
    """
    try:
        ciphertext = bytes.fromhex(encrypted_hex)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
        return decrypted.hex()
    except Exception as e:
        logger.error(f"API decryption failed: {e}")
        raise CryptoError(f"API decryption failed: {e}")


def encrypt_uid(uid: str, key: bytes = DEFAULT_UID_KEY, iv: bytes = DEFAULT_UID_IV) -> bytes:
    """
    Encrypt UID for GetPlayerPersonalShow request.
    
    This uses the same AES-CBC encryption as the original implementation.
    
    Args:
        uid: UID to encrypt
        key: AES key (default: UID encryption key)
        iv: Initialization vector (default: UID encryption IV)
        
    Returns:
        Encrypted bytes
    """
    try:
        import sys
        import os
        
        # Add parent directory to path for protobuf imports
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        sys.path.insert(0, project_root)
        
        from src.level.dev_generator_pb2 import dev_generator
        
        # Create protobuf with UID
        msg = dev_generator()
        msg.saturn_ = int(uid)
        msg.garena = 1
        raw = msg.SerializeToString()
        
        # Encrypt with AES-CBC
        cipher = AES.new(key, AES.MODE_CBC, iv)
        encrypted = cipher.encrypt(pad(raw, AES.block_size))
        return encrypted
        
    except ImportError as e:
        logger.error(f"Failed to import protobuf: {e}")
        raise CryptoError(f"Protobuf import failed: {e}")
    except Exception as e:
        logger.error(f"UID encryption failed: {e}")
        raise CryptoError(f"UID encryption failed: {e}")


def create_encrypted_payload(
    data: bytes,
    key: bytes = DEFAULT_API_KEY,
    iv: bytes = DEFAULT_API_IV,
) -> bytes:
    """
    Create encrypted payload for API requests.
    
    Args:
        data: Raw data to encrypt
        key: AES key
        iv: Initialization vector
        
    Returns:
        Encrypted payload
    """
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(data, AES.block_size))


def decrypt_response(
    response: bytes,
    key: bytes = DEFAULT_API_KEY,
    iv: bytes = DEFAULT_API_IV,
) -> bytes:
    """
    Decrypt API response.
    
    Args:
        response: Encrypted response data
        key: AES key
        iv: Initialization vector
        
    Returns:
        Decrypted response data
    """
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(response), AES.block_size)


def generate_template_payload(
    uid: str,
    access_token: str,
    open_id: str,
    date: str,
    signature: str,
) -> bytes:
    """
    Generate a template payload with substituted values.
    
    This is used for MajorLogin and GetLoginData requests.
    
    Args:
        uid: User UID
        access_token: OAuth access token
        open_id: OAuth open ID
        date: Current date string
        signature: MD5 signature
        
    Returns:
        Protobuf-encoded payload
    """
    # This is a placeholder - the actual template is in auth.py
    # This function provides a cleaner interface
    from src.level.auth import TEMPLATE_HEX
    
    data = bytes.fromhex(TEMPLATE_HEX)
    data = data.replace(b'996a629dbcdb3964be6b6978f5d814db', open_id.encode())
    data = data.replace(b'ff90c07eb9815af30a43b4a9f6019516e0e4c703b44092516d0defa4cef51f2a', access_token.encode())
    data = data.replace(b'2025-07-30 11:02:51', date.encode())
    data = data.replace(b'7428b253defc164018c604a1ebbfebdf', signature.encode())
    
    return data


class CryptoManager:
    """
    Manager for cryptographic operations with configurable keys.
    """
    
    def __init__(self, 
                 api_key: bytes = DEFAULT_API_KEY,
                 api_iv: bytes = DEFAULT_API_IV,
                 uid_key: bytes = DEFAULT_UID_KEY,
                 uid_iv: bytes = DEFAULT_UID_IV):
        self.api_key = api_key
        self.api_iv = api_iv
        self.uid_key = uid_key
        self.uid_iv = uid_iv
        
    def encrypt_api_data(self, hex_data: str) -> str:
        """Encrypt API data with configured keys."""
        return encrypt_api(hex_data, self.api_key, self.api_iv)
    
    def decrypt_api_data(self, encrypted_hex: str) -> str:
        """Decrypt API data with configured keys."""
        return decrypt_api(encrypted_hex, self.api_key, self.api_iv)
    
    def encrypt_uid_data(self, uid: str) -> bytes:
        """Encrypt UID with configured keys."""
        return encrypt_uid(uid, self.uid_key, self.uid_iv)
    
    def generate_keys(self) -> Tuple[bytes, bytes]:
        """Generate new API key and IV."""
        return generate_aes_key(16), generate_aes_iv()
    
    def set_api_keys(self, key: bytes, iv: bytes) -> None:
        """Set new API encryption keys."""
        if len(key) not in (16, 24, 32):
            raise ValueError("Key must be 16, 24, or 32 bytes")
        if len(iv) != 16:
            raise ValueError("IV must be 16 bytes")
        self.api_key = key
        self.api_iv = iv
    
    def set_uid_keys(self, key: bytes, iv: bytes) -> None:
        """Set new UID encryption keys."""
        if len(key) not in (16, 24, 32):
            raise ValueError("Key must be 16, 24, or 32 bytes")
        if len(iv) != 16:
            raise ValueError("IV must be 16 bytes")
        self.uid_key = key
        self.uid_iv = iv


# Global crypto manager instance with default keys
crypto_manager = CryptoManager()
