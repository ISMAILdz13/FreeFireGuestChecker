"""
Runtime Configuration Module
Manages runtime state and dynamic configuration.
"""

import os
import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from threading import Lock
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class RateLimitState:
    """Tracks rate limiting state."""
    last_request_time: float = 0.0
    request_count: int = 0
    last_cooldown_time: float = 0.0
    in_cooldown: bool = False
    consecutive_failures: int = 0
    
    def check_rate_limit(self, max_requests: int, window_seconds: int) -> bool:
        """Check if rate limit has been exceeded."""
        current_time = time.time()
        
        # Check if we're in cooldown
        if self.in_cooldown:
            if current_time - self.last_cooldown_time < window_seconds:
                return False
            self.in_cooldown = False
            
        # Reset count if window has passed
        if current_time - self.last_request_time > window_seconds:
            self.request_count = 0
            self.last_request_time = current_time
            
        # Check if we've exceeded the limit
        if self.request_count >= max_requests:
            self.in_cooldown = True
            self.last_cooldown_time = current_time
            return False
            
        return True
    
    def record_request(self) -> None:
        """Record a request."""
        current_time = time.time()
        
        if current_time - self.last_request_time > 60:  # Reset after 1 minute of inactivity
            self.request_count = 0
            
        self.request_count += 1
        self.last_request_time = current_time
    
    def record_failure(self) -> None:
        """Record a failure."""
        self.consecutive_failures += 1
    
    def record_success(self) -> None:
        """Record a success."""
        self.consecutive_failures = 0


@dataclass
class ProgressState:
    """Tracks progress of account checking operations."""
    total_accounts: int = 0
    processed_accounts: int = 0
    successful_accounts: int = 0
    failed_accounts: int = 0
    current_batch: int = 0
    start_time: Optional[float] = None
    last_save_time: float = 0.0
    last_progress_update: float = 0.0
    
    def start(self, total: int) -> None:
        """Start tracking progress."""
        self.total_accounts = total
        self.processed_accounts = 0
        self.successful_accounts = 0
        self.failed_accounts = 0
        self.current_batch = 0
        self.start_time = time.time()
        self.last_save_time = self.start_time
        self.last_progress_update = self.start_time
    
    def update(self, success: bool = True) -> None:
        """Update progress after processing an account."""
        self.processed_accounts += 1
        if success:
            self.successful_accounts += 1
        else:
            self.failed_accounts += 1
        self.last_progress_update = time.time()
    
    def next_batch(self) -> None:
        """Move to next batch."""
        self.current_batch += 1
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current progress information."""
        current_time = time.time()
        elapsed = current_time - self.start_time if self.start_time else 0
        
        progress_pct = 0.0
        if self.total_accounts > 0:
            progress_pct = (self.processed_accounts / self.total_accounts) * 100
            
        speed = 0.0
        if elapsed > 0:
            speed = self.processed_accounts / elapsed
            
        remaining = 0.0
        if speed > 0 and self.processed_accounts < self.total_accounts:
            remaining = (self.total_accounts - self.processed_accounts) / speed
            
        return {
            "total": self.total_accounts,
            "processed": self.processed_accounts,
            "successful": self.successful_accounts,
            "failed": self.failed_accounts,
            "batch": self.current_batch,
            "progress_percent": progress_pct,
            "elapsed_seconds": elapsed,
            "accounts_per_second": speed,
            "estimated_seconds_remaining": remaining,
        }
    
    def should_save(self, interval: int = 10) -> bool:
        """Check if progress should be saved."""
        if self.processed_accounts % interval == 0:
            self.last_save_time = time.time()
            return True
        return False


@dataclass
class ServerStatus:
    """Tracks server status and availability."""
    oauth_available: bool = True
    major_login_available: bool = True
    player_info_available: bool = True
    last_check_time: float = 0.0
    last_success_time: Dict[str, float] = field(default_factory=dict)
    last_failure_time: Dict[str, float] = field(default_factory=dict)
    failure_count: Dict[str, int] = field(default_factory=dict)
    
    def update_status(self, service: str, success: bool) -> None:
        """Update status for a service."""
        current_time = time.time()
        self.last_check_time = current_time
        
        if success:
            self.last_success_time[service] = current_time
            self.failure_count[service] = 0
        else:
            self.last_failure_time[service] = current_time
            self.failure_count[service] = self.failure_count.get(service, 0) + 1
        
        # Update availability flags
        self.oauth_available = self.failure_count.get("oauth", 0) < 3
        self.major_login_available = self.failure_count.get("major_login", 0) < 3
        self.player_info_available = self.failure_count.get("player_info", 0) < 3
    
    def is_available(self, service: str) -> bool:
        """Check if a service is available."""
        if service == "oauth":
            return self.oauth_available
        elif service == "major_login":
            return self.major_login_available
        elif service == "player_info":
            return self.player_info_available
        return True
    
    def get_status_report(self) -> Dict[str, Any]:
        """Get a status report for all services."""
        return {
            "oauth": {
                "available": self.oauth_available,
                "last_success": self.last_success_time.get("oauth", 0),
                "last_failure": self.last_failure_time.get("oauth", 0),
                "failure_count": self.failure_count.get("oauth", 0),
            },
            "major_login": {
                "available": self.major_login_available,
                "last_success": self.last_success_time.get("major_login", 0),
                "last_failure": self.last_failure_time.get("major_login", 0),
                "failure_count": self.failure_count.get("major_login", 0),
            },
            "player_info": {
                "available": self.player_info_available,
                "last_success": self.last_success_time.get("player_info", 0),
                "last_failure": self.last_failure_time.get("player_info", 0),
                "failure_count": self.failure_count.get("player_info", 0),
            },
        }


class RuntimeConfig:
    """
    Manages runtime configuration and state.
    Thread-safe for concurrent access.
    """
    
    def __init__(self):
        self._lock = Lock()
        self._state: Dict[str, Any] = {}
        self.rate_limit = RateLimitState()
        self.progress = ProgressState()
        self.server_status = ServerStatus()
        self._start_time = datetime.now()
        
    def set(self, key: str, value: Any) -> None:
        """Set a runtime configuration value."""
        with self._lock:
            self._state[key] = value
            
    def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """Get a runtime configuration value."""
        with self._lock:
            return self._state.get(key, default)
    
    def remove(self, key: str) -> bool:
        """Remove a runtime configuration value."""
        with self._lock:
            if key in self._state:
                del self._state[key]
                return True
            return False
    
    def get_rate_limit_state(self) -> RateLimitState:
        """Get the rate limit state."""
        return self.rate_limit
    
    def get_progress_state(self) -> ProgressState:
        """Get the progress state."""
        return self.progress
    
    def get_server_status(self) -> ServerStatus:
        """Get the server status."""
        return self.server_status
    
    def get_uptime(self) -> float:
        """Get uptime in seconds."""
        return (datetime.now() - self._start_time).total_seconds()
    
    def reset(self) -> None:
        """Reset all runtime state."""
        with self._lock:
            self._state.clear()
            self.rate_limit = RateLimitState()
            self.progress = ProgressState()
            self.server_status = ServerStatus()
            self._start_time = datetime.now()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get runtime statistics."""
        return {
            "uptime_seconds": self.get_uptime(),
            "rate_limit": {
                "request_count": self.rate_limit.request_count,
                "in_cooldown": self.rate_limit.in_cooldown,
                "consecutive_failures": self.rate_limit.consecutive_failures,
            },
            "progress": self.progress.get_progress(),
            "server_status": self.server_status.get_status_report(),
            "custom_state": self._state.copy(),
        }


# Global runtime config instance
runtime_config = RuntimeConfig()
