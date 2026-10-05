"""
Validators Module
Provides validation functions for various data types.
"""

import re
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass

from .helpers import validate_uid, validate_password

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """Represents a validation error."""
    field: str
    message: str
    value: Any = None
    
    def __str__(self) -> str:
        return f"{self.field}: {self.message}" if self.value is None else f"{self.field}: {self.message} (got: {self.value})"


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    errors: List[ValidationError] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    def add_error(self, field: str, message: str, value: Any = None) -> None:
        """Add a validation error."""
        self.errors.append(ValidationError(field, message, value))
        self.is_valid = False
    
    def __str__(self) -> str:
        if self.is_valid:
            return "Validation passed"
        return "Validation failed: " + ", ".join(str(e) for e in self.errors)


def validate_account_data(
    account: Dict[str, Any],
    require_password: bool = True,
    require_uid: bool = True,
) -> ValidationResult:
    """
    Validate guest account data.
    
    Args:
        account: Account dictionary to validate
        require_password: Whether password is required
        require_uid: Whether UID is required
        
    Returns:
        ValidationResult with errors if any
    """
    result = ValidationResult(is_valid=True)
    
    if require_uid:
        uid = account.get("uid", account.get("id", ""))
        if not uid:
            result.add_error("uid", "UID is required")
        elif not validate_uid(str(uid)):
            result.add_error("uid", "Invalid UID format. Must be 8-12 digits", uid)
    
    if require_password:
        password = account.get("password", "")
        if not password:
            result.add_error("password", "Password is required")
        elif not validate_password(str(password)):
            result.add_error("password", "Invalid password format", password)
    
    # Validate nickname if present
    nickname = account.get("nickname", account.get("name", ""))
    if nickname:
        if len(nickname) > 32:
            result.add_error("nickname", "Nickname too long (max 32 characters)", nickname)
        if not re.match(r'^[\w\s\-\.]+$', nickname):
            result.add_error("nickname", "Invalid characters in nickname", nickname)
    
    # Validate region if present
    region = account.get("region", "")
    if region:
        valid_regions = ["GLOBAL", "INDIA", "INDONESIA", "BRAZIL", "LATAM", "MENA", "SEA", "US", "EU"]
        if region.upper() not in valid_regions:
            result.add_error("region", f"Invalid region. Must be one of: {', '.join(valid_regions)}", region)
    
    return result


def validate_batch_size(batch_size: int) -> ValidationResult:
    """
    Validate batch size for processing.
    
    Args:
        batch_size: Batch size to validate
        
    Returns:
        ValidationResult with errors if any
    """
    result = ValidationResult(is_valid=True)
    
    if not isinstance(batch_size, int):
        result.add_error("batch_size", "Batch size must be an integer", batch_size)
    elif batch_size < 1:
        result.add_error("batch_size", "Batch size must be at least 1", batch_size)
    elif batch_size > 10000:
        result.add_error("batch_size", "Batch size too large (max 10000)", batch_size)
    
    return result


def validate_concurrency(concurrency: int) -> ValidationResult:
    """
    Validate concurrency setting.
    
    Args:
        concurrency: Concurrency level to validate
        
    Returns:
        ValidationResult with errors if any
    """
    result = ValidationResult(is_valid=True)
    
    if not isinstance(concurrency, int):
        result.add_error("concurrency", "Concurrency must be an integer", concurrency)
    elif concurrency < 1:
        result.add_error("concurrency", "Concurrency must be at least 1", concurrency)
    elif concurrency > 50:
        result.add_error("concurrency", "Concurrency too high (max 50)", concurrency)
    
    return result


def validate_proxy_config(proxy_config: Dict[str, Any]) -> ValidationResult:
    """
    Validate proxy configuration.
    
    Args:
        proxy_config: Proxy configuration dictionary
        
    Returns:
        ValidationResult with errors if any
    """
    result = ValidationResult(is_valid=True)
    
    if not proxy_config:
        return result
    
    enabled = proxy_config.get("enabled", False)
    if not enabled:
        return result
    
    # Check required fields
    if not proxy_config.get("host"):
        result.add_error("proxy.host", "Proxy host is required")
    
    proxy_type = proxy_config.get("proxy_type", "http").lower()
    valid_types = ["http", "https", "socks4", "socks5", "none"]
    if proxy_type not in valid_types:
        result.add_error("proxy.proxy_type", f"Invalid proxy type. Must be one of: {', '.join(valid_types)}", proxy_type)
    
    port = proxy_config.get("port", 0)
    if port and (port < 1 or port > 65535):
        result.add_error("proxy.port", "Proxy port must be between 1 and 65535", port)
    
    # Validate proxy URL format if provided directly
    proxy_url = proxy_config.get("proxy_url", "")
    if proxy_url:
        # Simple URL validation
        if not re.match(r'^(http|https|socks4|socks5)://[^:\s]+(:\d+)?$', proxy_url):
            result.add_error("proxy.proxy_url", "Invalid proxy URL format", proxy_url)
    
    return result


def validate_endpoint_url(url: str, require_https: bool = False) -> ValidationResult:
    """
    Validate an endpoint URL.
    
    Args:
        url: URL to validate
        require_https: Whether HTTPS is required
        
    Returns:
        ValidationResult with errors if any
    """
    result = ValidationResult(is_valid=True)
    
    if not url:
        result.add_error("url", "URL is required")
        return result
    
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        
        if not parsed.scheme:
            result.add_error("url", "URL must include scheme (http/https)", url)
        elif require_https and parsed.scheme.lower() != "https":
            result.add_error("url", "HTTPS is required", url)
        
        if not parsed.netloc:
            result.add_error("url", "URL must include hostname", url)
        
        if parsed.port and (parsed.port < 1 or parsed.port > 65535):
            result.add_error("url", "Invalid port number", url)
            
    except Exception as e:
        result.add_error("url", f"Invalid URL: {e}", url)
    
    return result


def validate_oauth_config(oauth_config: Dict[str, Any]) -> ValidationResult:
    """
    Validate OAuth configuration.
    
    Args:
        oauth_config: OAuth configuration dictionary
        
    Returns:
        ValidationResult with errors if any
    """
    result = ValidationResult(is_valid=True)
    
    if not oauth_config:
        result.add_error("oauth", "OAuth configuration is required")
        return result
    
    if not oauth_config.get("client_id"):
        result.add_error("oauth.client_id", "Client ID is required")
    
    if not oauth_config.get("client_secret"):
        result.add_error("oauth.client_secret", "Client secret is required")
    
    endpoints = oauth_config.get("oauth_endpoints", [])
    if not endpoints:
        result.add_error("oauth.oauth_endpoints", "At least one OAuth endpoint is required")
    else:
        for i, endpoint in enumerate(endpoints):
            endpoint_result = validate_endpoint_url(endpoint, require_https=True)
            if not endpoint_result.is_valid:
                for error in endpoint_result.errors:
                    result.add_error(f"oauth.oauth_endpoints[{i}]", error.message, error.value)
    
    return result


def validate_account_list(accounts: List[Dict[str, Any]]) -> ValidationResult:
    """
    Validate a list of accounts.
    
    Args:
        accounts: List of account dictionaries
        
    Returns:
        ValidationResult with errors if any
    """
    result = ValidationResult(is_valid=True)
    
    if not accounts:
        result.add_error("accounts", "At least one account is required")
        return result
    
    if not isinstance(accounts, list):
        result.add_error("accounts", "Accounts must be a list", accounts)
        return result
    
    if len(accounts) > 100000:
        result.add_error("accounts", "Too many accounts (max 100000)", len(accounts))
        return result
    
    # Validate each account
    for i, account in enumerate(accounts):
        if not isinstance(account, dict):
            result.add_error(f"accounts[{i}]", "Account must be a dictionary", account)
            continue
        
        account_result = validate_account_data(account)
        if not account_result.is_valid:
            for error in account_result.errors:
                result.add_error(f"accounts[{i}].{error.field}", error.message, error.value)
    
    return result


def validate_rate_limit_config(config: Dict[str, Any]) -> ValidationResult:
    """
    Validate rate limit configuration.
    
    Args:
        config: Rate limit configuration dictionary
        
    Returns:
        ValidationResult with errors if any
    """
    result = ValidationResult(is_valid=True)
    
    if not config:
        return result
    
    max_requests = config.get("max_requests_per_minute")
    if max_requests is not None:
        if not isinstance(max_requests, int) or max_requests < 1:
            result.add_error("rate_limit.max_requests_per_minute", 
                            "Must be a positive integer", max_requests)
    
    max_concurrent = config.get("max_concurrent_requests")
    if max_concurrent is not None:
        if not isinstance(max_concurrent, int) or max_concurrent < 1:
            result.add_error("rate_limit.max_concurrent_requests", 
                            "Must be a positive integer", max_concurrent)
    
    timeout = config.get("request_timeout")
    if timeout is not None:
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            result.add_error("rate_limit.request_timeout", 
                            "Must be a positive number", timeout)
    
    retry_attempts = config.get("retry_attempts")
    if retry_attempts is not None:
        if not isinstance(retry_attempts, int) or retry_attempts < 0:
            result.add_error("rate_limit.retry_attempts", 
                            "Must be a non-negative integer", retry_attempts)
    
    return result


def validate_checker_config(config: Dict[str, Any]) -> ValidationResult:
    """
    Validate checker configuration.
    
    Args:
        config: Checker configuration dictionary
        
    Returns:
        ValidationResult with errors if any
    """
    result = ValidationResult(is_valid=True)
    
    if not config:
        return result
    
    concurrency = config.get("concurrent_workers")
    if concurrency is not None:
        concurrency_result = validate_concurrency(concurrency)
        if not concurrency_result.is_valid:
            for error in concurrency_result.errors:
                result.add_error(f"checker.{error.field}", error.message, error.value)
    
    batch_size = config.get("batch_size")
    if batch_size is not None:
        batch_result = validate_batch_size(batch_size)
        if not batch_result.is_valid:
            for error in batch_result.errors:
                result.add_error(f"checker.{error.field}", error.message, error.value)
    
    return result


def validate_web_config(config: Dict[str, Any]) -> ValidationResult:
    """
    Validate web server configuration.
    
    Args:
        config: Web configuration dictionary
        
    Returns:
        ValidationResult with errors if any
    """
    result = ValidationResult(is_valid=True)
    
    if not config:
        return result
    
    if config.get("enabled", False):
        port = config.get("port", 8080)
        if not isinstance(port, int) or port < 1 or port > 65535:
            result.add_error("web.port", "Port must be between 1 and 65535", port)
        
        host = config.get("host", "0.0.0.0")
        if host and not re.match(r'^[\w\.\:]+$', host):
            result.add_error("web.host", "Invalid host format", host)
    
    return result


def validate_all_config(config: Dict[str, Any]) -> ValidationResult:
    """
    Validate the entire configuration.
    
    Args:
        config: Complete configuration dictionary
        
    Returns:
        ValidationResult with all errors found
    """
    result = ValidationResult(is_valid=True)
    
    # Validate proxy config
    proxy_config = config.get("proxy", {})
    proxy_result = validate_proxy_config(proxy_config)
    if not proxy_result.is_valid:
        for error in proxy_result.errors:
            result.add_error(error.field, error.message, error.value)
    
    # Validate OAuth config
    auth_config = config.get("auth", {})
    oauth_result = validate_oauth_config(auth_config)
    if not oauth_result.is_valid:
        for error in oauth_result.errors:
            result.add_error(error.field, error.message, error.value)
    
    # Validate rate limit config
    rate_config = config.get("rate_limit", {})
    rate_result = validate_rate_limit_config(rate_config)
    if not rate_result.is_valid:
        for error in rate_result.errors:
            result.add_error(error.field, error.message, error.value)
    
    # Validate checker config
    checker_config = config.get("checker", {})
    checker_result = validate_checker_config(checker_config)
    if not checker_result.is_valid:
        for error in checker_result.errors:
            result.add_error(error.field, error.message, error.value)
    
    # Validate web config
    web_config = config.get("web", {})
    web_result = validate_web_config(web_config)
    if not web_result.is_valid:
        for error in web_result.errors:
            result.add_error(error.field, error.message, error.value)
    
    return result


def validate_and_raise(
    data: Any,
    validator: callable,
    context: str = "Validation",
) -> Any:
    """
    Validate data and raise exception if invalid.
    
    Args:
        data: Data to validate
        validator: Validation function to use
        context: Context for error messages
        
    Returns:
        The validated data
        
    Raises:
        ValueError: If validation fails
    """
    result = validator(data)
    if not result.is_valid:
        error_messages = [str(e) for e in result.errors]
        raise ValueError(f"{context} failed: " + "; ".join(error_messages))
    return data
