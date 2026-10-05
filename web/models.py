"""
Web Models
Defines models used in the web interface.
"""

from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class APIResponse:
    """Standard API response format."""
    
    success: bool = True
    data: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    error: Optional[str] = None
    status: int = 200
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "timestamp": self.timestamp,
        }
        
        if self.error:
            result["error"] = self.error
        
        return result


@dataclass
class Pagination:
    """Pagination information."""
    page: int = 1
    per_page: int = 20
    total: int = 0
    total_pages: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "page": self.page,
            "per_page": self.per_page,
            "total": self.total,
            "total_pages": self.total_pages,
        }


@dataclass
class AccountFilter:
    """Filter criteria for account queries."""
    status: Optional[str] = None
    region: Optional[str] = None
    search: Optional[str] = None
    page: int = 1
    per_page: int = 20
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "region": self.region,
            "search": self.search,
            "page": self.page,
            "per_page": self.per_page,
        }


@dataclass
class Stats:
    """Statistics about accounts."""
    total: int = 0
    by_status: Dict[str, int] = field(default_factory=dict)
    by_region: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "by_status": self.by_status,
            "by_region": self.by_region,
        }
