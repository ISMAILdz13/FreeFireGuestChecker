"""
Database Models
Defines data models for account storage.
"""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class AccountStatus(Enum):
    """Status of a guest account."""
    UNKNOWN = "UNKNOWN"
    ALIVE = "ALIVE"
    DEAD = "DEAD"
    BANNED = "BANNED"
    SERVER_DOWN = "SERVER_DOWN"
    BLACKLISTED = "BLACKLISTED"
    PENDING = "PENDING"


class AccountSource(Enum):
    """Source of account data."""
    MANUAL = "MANUAL"
    GENERATED = "GENERATED"
    IMPORTED_JSON = "IMPORTED_JSON"
    IMPORTED_DB = "IMPORTED_DB"
    IMPORTED_CSV = "IMPORTED_CSV"


@dataclass
class CheckResult:
    """Result of checking an account."""
    checked_at: datetime = field(default_factory=datetime.now)
    status: AccountStatus = AccountStatus.UNKNOWN
    oauth_status: str = "UNKNOWN"
    ban_reason: str = ""
    nickname: str = ""
    level: int = 0
    exp: int = 0
    likes: int = 0
    rank: int = 0
    region: str = "Unknown"
    clan_name: str = ""
    clan_level: int = 0
    release_version: str = ""
    credit_score: int = 0
    last_login: str = ""
    account_created: str = ""
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "checked_at": self.checked_at.isoformat() if self.checked_at else None,
            "status": self.status.value,
            "oauth_status": self.oauth_status,
            "ban_reason": self.ban_reason,
            "nickname": self.nickname,
            "level": self.level,
            "exp": self.exp,
            "likes": self.likes,
            "rank": self.rank,
            "region": self.region,
            "clan_name": self.clan_name,
            "clan_level": self.clan_level,
            "release_version": self.release_version,
            "credit_score": self.credit_score,
            "last_login": self.last_login,
            "account_created": self.account_created,
            "error": self.error,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CheckResult':
        """Create from dictionary."""
        return cls(
            checked_at=datetime.fromisoformat(data.get("checked_at", "")) if data.get("checked_at") else datetime.now(),
            status=AccountStatus(data.get("status", "UNKNOWN")),
            oauth_status=data.get("oauth_status", "UNKNOWN"),
            ban_reason=data.get("ban_reason", ""),
            nickname=data.get("nickname", ""),
            level=data.get("level", 0),
            exp=data.get("exp", 0),
            likes=data.get("likes", 0),
            rank=data.get("rank", 0),
            region=data.get("region", "Unknown"),
            clan_name=data.get("clan_name", ""),
            clan_level=data.get("clan_level", 0),
            release_version=data.get("release_version", ""),
            credit_score=data.get("credit_score", 0),
            last_login=data.get("last_login", ""),
            account_created=data.get("account_created", ""),
            error=data.get("error"),
        )


@dataclass
class Account:
    """Represents a Free Fire guest account."""
    uid: str
    password: str
    name: str = ""
    source: AccountSource = AccountSource.MANUAL
    region: str = "GLOBAL"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_checked: Optional[datetime] = None
    status: AccountStatus = AccountStatus.UNKNOWN
    check_count: int = 0
    last_check_result: Optional[CheckResult] = None
    notes: str = ""
    tags: List[str] = field(default_factory=list)
    custom_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        # Ensure tags is a list
        if not isinstance(self.tags, list):
            self.tags = []
        if not isinstance(self.custom_data, dict):
            self.custom_data = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "uid": self.uid,
            "password": "***",  # Mask password
            "name": self.name,
            "source": self.source.value,
            "region": self.region,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_checked": self.last_checked.isoformat() if self.last_checked else None,
            "status": self.status.value,
            "check_count": self.check_count,
            "notes": self.notes,
            "tags": self.tags,
            "custom_data": self.custom_data,
        }
        
        # Include last check result if available
        if self.last_check_result:
            result["last_check_result"] = self.last_check_result.to_dict()
        
        return result
    
    def to_dict_with_password(self) -> Dict[str, Any]:
        """Convert to dictionary including password (use with caution)."""
        result = self.to_dict()
        result["password"] = self.password
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Account':
        """Create from dictionary."""
        last_checked = None
        if data.get("last_checked"):
            try:
                last_checked = datetime.fromisoformat(data["last_checked"])
            except (ValueError, TypeError):
                pass
        
        last_check_result = None
        if data.get("last_check_result"):
            last_check_result = CheckResult.from_dict(data["last_check_result"])
        
        return cls(
            uid=data.get("uid", ""),
            password=data.get("password", ""),
            name=data.get("name", ""),
            source=AccountSource(data.get("source", "MANUAL")),
            region=data.get("region", "GLOBAL"),
            created_at=datetime.fromisoformat(data.get("created_at", "")) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data.get("updated_at", "")) if data.get("updated_at") else datetime.now(),
            last_checked=last_checked,
            status=AccountStatus(data.get("status", "UNKNOWN")),
            check_count=data.get("check_count", 0),
            last_check_result=last_check_result,
            notes=data.get("notes", ""),
            tags=data.get("tags", []),
            custom_data=data.get("custom_data", {}),
        )
    
    def update_from_check(self, check_result: CheckResult) -> None:
        """Update account from check result."""
        self.last_checked = datetime.now()
        self.last_check_result = check_result
        self.status = check_result.status
        self.check_count += 1
        self.updated_at = datetime.now()
        
        # Update basic info from check result
        if check_result.nickname:
            self.name = check_result.nickname
        if check_result.region:
            self.region = check_result.region
    
    def is_valid(self) -> bool:
        """Check if account has valid data."""
        return bool(self.uid and self.password)
    
    def matches(self, uid: str, password: str) -> bool:
        """Check if account matches given credentials."""
        return self.uid == uid and self.password == password


@dataclass
class AccountFilter:
    """Filter criteria for account queries."""
    status: Optional[AccountStatus] = None
    region: Optional[str] = None
    source: Optional[AccountSource] = None
    tags: Optional[List[str]] = None
    min_check_count: Optional[int] = None
    max_check_count: Optional[int] = None
    has_been_checked: Optional[bool] = None
    last_checked_after: Optional[datetime] = None
    last_checked_before: Optional[datetime] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    search: Optional[str] = None
    limit: Optional[int] = None
    offset: Optional[int] = None
    order_by: Optional[str] = None
    order_desc: bool = False
