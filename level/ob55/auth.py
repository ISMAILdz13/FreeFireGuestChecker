"""
OB55 Authenticator for Free Fire
Handles authentication with OB55 protocol
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

import aiohttp
import requests

from src.utils.logging import get_logger
from src.utils.helpers import generate_id, get_timestamp
from src.utils.validators import validate_account_id
from src.level.auth import Authenticator, AuthResult
from config.settings import Settings, get_settings

logger = get_logger(__name__)


@dataclass
class OB55AuthConfig:
    """OB55 authentication configuration"""
    api_url: str = "https://api-ob55.ff.garena.com"
    login_url: str = "https://login-ob55.ff.garena.com"
    auth_url: str = "https://auth-ob55.ff.garena.com"
    
    # Headers
    user_agent: str = "FreeFire/2.0 (Android; 11; Mobile)"
    accept: str = "application/json"
    content_type: str = "application/json"
    
    # Device info
    device_id: str = field(default_factory=lambda: generate_id("device"))
    device_model: str = "Android 11"
    device_brand: str = "Google"
    device_manufacturer: str = "Google"
    
    # App info
    app_version: str = "2.0.0"
    app_id: str = "com.dts.freefireth"
    package_name: str = "com.dts.freefireth"
    
    # Timeouts
    connect_timeout: float = 10.0
    read_timeout: float = 30.0


class OB55Authenticator(Authenticator):
    """OB55 protocol authenticator"""

    def __init__(self, 
                 http_client: Optional[aiohttp.ClientSession] = None,
                 settings: Optional[Settings] = None,
                 config: Optional[OB55AuthConfig] = None):
        super().__init__(http_client, settings)
        self.config = config or OB55AuthConfig()
        self._session: Optional[requests.Session] = None

    def _get_session(self) -> requests.Session:
        """Get or create a requests session"""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                "User-Agent": self.config.user_agent,
                "Accept": self.config.accept,
                "Content-Type": self.config.content_type
            })
        return self._session

    def _get_headers(self) -> Dict[str, str]:
        """Get default headers for OB55"""
        return {
            "User-Agent": self.config.user_agent,
            "Accept": self.config.accept,
            "Content-Type": self.config.content_type,
            "X-Device-ID": self.config.device_id,
            "X-App-Version": self.config.app_version,
            "X-Device-Model": self.config.device_model,
            "X-Device-Brand": self.config.device_brand
        }

    def authenticate_sync(self) -> AuthResult:
        """Authenticate synchronously with OB55"""
        try:
            # Step 1: Get device info
            device_info = self._get_device_info()
            
            # Step 2: Get login data
            login_data = self._get_login_data(device_info)
            
            if login_data.get("success", False):
                return AuthResult(
                    success=True,
                    data=login_data,
                    token=login_data.get("token"),
                    expiry=login_data.get("expiry", time.time() + 3600)
                )
            else:
                return AuthResult(
                    success=False,
                    error=login_data.get("error", "Unknown error")
                )
        except Exception as e:
            logger.error(f"OB55 authentication failed: {e}")
            return AuthResult(
                success=False,
                error=str(e)
            )

    async def authenticate(self) -> AuthResult:
        """Authenticate asynchronously with OB55"""
        try:
            # Step 1: Get device info
            device_info = await self._get_device_info_async()
            
            # Step 2: Get login data
            login_data = await self._get_login_data_async(device_info)
            
            if login_data.get("success", False):
                return AuthResult(
                    success=True,
                    data=login_data,
                    token=login_data.get("token"),
                    expiry=login_data.get("expiry", time.time() + 3600)
                )
            else:
                return AuthResult(
                    success=False,
                    error=login_data.get("error", "Unknown error")
                )
        except Exception as e:
            logger.error(f"OB55 authentication failed: {e}")
            return AuthResult(
                success=False,
                error=str(e)
            )

    def _get_device_info(self) -> Dict[str, Any]:
        """Get device information"""
        return {
            "device_id": self.config.device_id,
            "device_model": self.config.device_model,
            "device_brand": self.config.device_brand,
            "device_manufacturer": self.config.device_manufacturer,
            "app_version": self.config.app_version,
            "app_id": self.config.app_id,
            "package_name": self.config.package_name,
            "platform": "Android",
            "os_version": "11",
            "sdk_version": "30"
        }

    async def _get_device_info_async(self) -> Dict[str, Any]:
        """Get device information asynchronously"""
        return self._get_device_info()

    def _get_login_data(self, device_info: Dict[str, Any]) -> Dict[str, Any]:
        """Get login data from OB55 server"""
        session = self._get_session()
        
        try:
            # Prepare request
            url = f"{self.config.auth_url}/v1/auth/device"
            
            # Create payload
            payload = {
                "device_id": device_info["device_id"],
                "device_model": device_info["device_model"],
                "device_brand": device_info["device_brand"],
                "app_version": device_info["app_version"],
                "platform": device_info["platform"],
                "timestamp": int(time.time() * 1000)
            }
            
            # Add signature
            payload["signature"] = self._generate_signature(payload)
            
            # Make request
            response = session.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=(self.config.connect_timeout, self.config.read_timeout)
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get login data: {e}")
            return {"success": False, "error": str(e)}

    async def _get_login_data_async(self, device_info: Dict[str, Any]) -> Dict[str, Any]:
        """Get login data asynchronously"""
        try:
            url = f"{self.config.auth_url}/v1/auth/device"
            
            payload = {
                "device_id": device_info["device_id"],
                "device_model": device_info["device_model"],
                "device_brand": device_info["device_brand"],
                "app_version": device_info["app_version"],
                "platform": device_info["platform"],
                "timestamp": int(time.time() * 1000)
            }
            
            payload["signature"] = self._generate_signature(payload)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(
                        total=self.config.read_timeout,
                        connect=self.config.connect_timeout
                    )
                ) as response:
                    response.raise_for_status()
                    return await response.json()
                    
        except aiohttp.ClientError as e:
            logger.error(f"Failed to get login data async: {e}")
            return {"success": False, "error": str(e)}

    def _generate_signature(self, payload: Dict[str, Any]) -> str:
        """Generate signature for OB55 requests"""
        # Sort keys and create query string
        sorted_keys = sorted(payload.keys())
        query_string = "&".join(f"{k}={payload[k]}" for k in sorted_keys)
        
        # Use a simple hash for demonstration
        # In production, use proper signing with secret key
        return hashlib.sha256(query_string.encode()).hexdigest()

    def validate_response(self, response: Dict[str, Any]) -> bool:
        """Validate OB55 response"""
        required_fields = ["success", "token", "expiry"]
        return all(field in response for field in required_fields)

    def refresh_token(self, token: str) -> AuthResult:
        """Refresh authentication token"""
        try:
            # Prepare request
            url = f"{self.config.auth_url}/v1/auth/refresh"
            
            payload = {
                "token": token,
                "device_id": self.config.device_id,
                "timestamp": int(time.time() * 1000)
            }
            
            payload["signature"] = self._generate_signature(payload)
            
            session = self._get_session()
            response = session.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=(self.config.connect_timeout, self.config.read_timeout)
            )
            
            response.raise_for_status()
            data = response.json()
            
            if data.get("success", False):
                return AuthResult(
                    success=True,
                    data=data,
                    token=data.get("token"),
                    expiry=data.get("expiry", time.time() + 3600)
                )
            else:
                return AuthResult(
                    success=False,
                    error=data.get("error", "Unknown error")
                )
                
        except Exception as e:
            logger.error(f"Failed to refresh token: {e}")
            return AuthResult(
                success=False,
                error=str(e)
            )

    async def refresh_token_async(self, token: str) -> AuthResult:
        """Refresh authentication token asynchronously"""
        try:
            url = f"{self.config.auth_url}/v1/auth/refresh"
            
            payload = {
                "token": token,
                "device_id": self.config.device_id,
                "timestamp": int(time.time() * 1000)
            }
            
            payload["signature"] = self._generate_signature(payload)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(
                        total=self.config.read_timeout,
                        connect=self.config.connect_timeout
                    )
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    if data.get("success", False):
                        return AuthResult(
                            success=True,
                            data=data,
                            token=data.get("token"),
                            expiry=data.get("expiry", time.time() + 3600)
                        )
                    else:
                        return AuthResult(
                            success=False,
                            error=data.get("error", "Unknown error")
                        )
                        
        except Exception as e:
            logger.error(f"Failed to refresh token async: {e}")
            return AuthResult(
                success=False,
                error=str(e)
            )
