"""
OB55 Guest Info Fetcher for Free Fire
Fetches guest account information using OB55 protocol
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

import aiohttp
import requests

from src.utils.logging import get_logger
from src.utils.helpers import generate_id, get_timestamp
from src.utils.validators import validate_account_id
from src.level.guest_info import GuestInfoFetcher, GuestInfo
from src.level.auth import AuthResult
from config.settings import Settings, get_settings

logger = get_logger(__name__)


@dataclass
class OB55GuestInfo:
    """OB55 guest account information"""
    account_id: str
    nickname: str
    level: int = 0
    diamonds: int = 0
    coins: int = 0
    region: str = "global"
    is_banned: bool = False
    ban_reason: Optional[str] = None
    ban_expiry: Optional[float] = None
    last_login: Optional[str] = None
    creation_date: Optional[str] = None
    is_guest: bool = True
    device_id: Optional[str] = None
    session_id: Optional[str] = None
    session_expiry: Optional[float] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "account_id": self.account_id,
            "nickname": self.nickname,
            "level": self.level,
            "diamonds": self.diamonds,
            "coins": self.coins,
            "region": self.region,
            "is_banned": self.is_banned,
            "ban_reason": self.ban_reason,
            "ban_expiry": self.ban_expiry,
            "last_login": self.last_login,
            "creation_date": self.creation_date,
            "is_guest": self.is_guest,
            "device_id": self.device_id,
            "session_id": self.session_id,
            "session_expiry": self.session_expiry,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent
        }


class OB55GuestInfoFetcher(GuestInfoFetcher):
    """OB55 protocol guest info fetcher"""

    def __init__(self, 
                 http_client: Optional[aiohttp.ClientSession] = None,
                 authenticator: Optional[Any] = None,
                 settings: Optional[Settings] = None):
        super().__init__(http_client, authenticator, settings)
        self.config = get_settings()
        self._session: Optional[requests.Session] = None

    def _get_session(self) -> requests.Session:
        """Get or create a requests session"""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                "User-Agent": "FreeFire/2.0 (Android; 11; Mobile)",
                "Accept": "application/json",
                "Content-Type": "application/json"
            })
        return self._session

    def _get_headers(self, auth_data: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """Get headers for OB55 requests"""
        headers = {
            "User-Agent": "FreeFire/2.0 (Android; 11; Mobile)",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        if auth_data and "token" in auth_data:
            headers["Authorization"] = f"Bearer {auth_data['token']}"
        
        return headers

    def fetch_guest_info_sync(self, account_id: str, 
                              auth_data: Optional[Dict[str, Any]] = None) -> Optional[GuestInfo]:
        """Fetch guest info synchronously"""
        if not validate_account_id(account_id):
            return None
        
        try:
            # Step 1: Get account data
            account_data = self._get_account_data(account_id, auth_data)
            
            if not account_data or not account_data.get("success", False):
                return None
            
            # Step 2: Parse response
            guest_info = self._parse_account_data(account_data, account_id)
            
            return guest_info
            
        except Exception as e:
            logger.error(f"Failed to fetch guest info for {account_id}: {e}")
            return None

    async def fetch_guest_info(self, account_id: str,
                                auth_data: Optional[Dict[str, Any]] = None) -> Optional[GuestInfo]:
        """Fetch guest info asynchronously"""
        if not validate_account_id(account_id):
            return None
        
        try:
            # Step 1: Get account data
            account_data = await self._get_account_data_async(account_id, auth_data)
            
            if not account_data or not account_data.get("success", False):
                return None
            
            # Step 2: Parse response
            guest_info = self._parse_account_data(account_data, account_id)
            
            return guest_info
            
        except Exception as e:
            logger.error(f"Failed to fetch guest info async for {account_id}: {e}")
            return None

    def _get_account_data(self, account_id: str, 
                          auth_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Get account data from OB55 server"""
        session = self._get_session()
        
        try:
            # Prepare request
            url = f"{self.config.api_url or 'https://api-ob55.ff.garena.com'}/v1/accounts/{account_id}"
            
            # Make request
            response = session.get(
                url,
                headers=self._get_headers(auth_data),
                timeout=(10.0, 30.0)
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get account data: {e}")
            return None

    async def _get_account_data_async(self, account_id: str,
                                      auth_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Get account data asynchronously"""
        try:
            url = f"{self.config.api_url or 'https://api-ob55.ff.garena.com'}/v1/accounts/{account_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=self._get_headers(auth_data),
                    timeout=aiohttp.ClientTimeout(total=30.0)
                ) as response:
                    response.raise_for_status()
                    return await response.json()
                    
        except aiohttp.ClientError as e:
            logger.error(f"Failed to get account data async: {e}")
            return None

    def _parse_account_data(self, data: Dict[str, Any], account_id: str) -> GuestInfo:
        """Parse account data into GuestInfo"""
        account_data = data.get("data", {}).get("account", {})
        
        return GuestInfo(
            account_id=account_id,
            nickname=account_data.get("nickname", "Unknown"),
            level=account_data.get("level", 0),
            diamonds=account_data.get("diamonds", 0),
            coins=account_data.get("coins", 0),
            region=account_data.get("region", "global"),
            is_banned=account_data.get("is_banned", False),
            ban_reason=account_data.get("ban_reason"),
            ban_expiry=account_data.get("ban_expiry"),
            last_login=account_data.get("last_login"),
            creation_date=account_data.get("creation_date"),
            is_guest=account_data.get("is_guest", True),
            device_id=account_data.get("device_id"),
            session_id=account_data.get("session_id"),
            session_expiry=account_data.get("session_expiry"),
            ip_address=account_data.get("ip_address"),
            user_agent=account_data.get("user_agent"),
            checked_at=get_timestamp()
        )

    def fetch_batch_sync(self, account_ids: List[str],
                         auth_data: Optional[Dict[str, Any]] = None) -> List[Optional[GuestInfo]]:
        """Fetch multiple guest infos synchronously"""
        results = []
        
        for account_id in account_ids:
            result = self.fetch_guest_info_sync(account_id, auth_data)
            results.append(result)
        
        return results

    async def fetch_batch(self, account_ids: List[str],
                         auth_data: Optional[Dict[str, Any]] = None) -> List[Optional[GuestInfo]]:
        """Fetch multiple guest infos asynchronously"""
        tasks = []
        
        for account_id in account_ids:
            task = self.fetch_guest_info(account_id, auth_data)
            tasks.append(task)
        
        return await asyncio.gather(*tasks)

    def validate_guest_account(self, account_id: str) -> bool:
        """Validate if an account is a guest account"""
        if not validate_account_id(account_id):
            return False
        
        # OB55 guest accounts typically have specific patterns
        # This is a placeholder - actual validation would require API call
        return True

    def get_guest_account_status(self, account_id: str) -> Dict[str, Any]:
        """Get detailed status of a guest account"""
        guest_info = self.fetch_guest_info_sync(account_id)
        
        if not guest_info:
            return {
                "account_id": account_id,
                "exists": False,
                "error": "Account not found"
            }
        
        return {
            "account_id": account_id,
            "exists": True,
            "nickname": guest_info.nickname,
            "level": guest_info.level,
            "diamonds": guest_info.diamonds,
            "coins": guest_info.coins,
            "is_banned": guest_info.is_banned,
            "ban_reason": guest_info.ban_reason,
            "ban_expiry": guest_info.ban_expiry,
            "last_login": guest_info.last_login,
            "creation_date": guest_info.creation_date,
            "is_guest": guest_info.is_guest,
            "checked_at": guest_info.checked_at
        }
