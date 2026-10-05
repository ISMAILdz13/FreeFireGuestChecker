"""
Settings Configuration Module
Manages application settings with environment variable support and validation.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Region(Enum):
    GLOBAL = "GLOBAL"
    INDIA = "INDIA"
    INDONESIA = "INDONESIA"
    BRAZIL = "BRAZIL"
    LATAM = "LATAM"
    MENA = "MENA"
    SEA = "SEA"
    CUSTOM = "CUSTOM"


class ProxyType(Enum):
    NONE = "none"
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


@dataclass
class DatabaseConfig:
    enabled: bool = True
    path: str = "data/guests.db"
    backup_path: str = "data/backups/guests_backup_{timestamp}.db"
    max_backups: int = 5
    auto_backup: bool = True
    vacuum_on_startup: bool = True


@dataclass
class ProxyConfig:
    enabled: bool = False
    proxy_type: ProxyType = ProxyType.NONE
    host: str = ""
    port: int = 0
    username: str = ""
    password: str = ""
    rotate_on_failure: bool = False
    rotation_list: List[str] = field(default_factory=list)
    rotation_interval: int = 0  # 0 = no rotation, >0 = seconds between rotation


@dataclass
class RateLimitConfig:
    enabled: bool = True
    max_requests_per_minute: int = 60
    max_concurrent_requests: int = 10
    request_timeout: float = 15.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    backoff_multiplier: float = 2.0
    cooldown_on_rate_limit: bool = True
    cooldown_seconds: int = 60


@dataclass
class AuthConfig:
    client_id: str = "100067"
    client_secret: str = "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3"
    oauth_endpoints: List[str] = field(default_factory=lambda: [
        "https://ffmconnect.live.gop.garenanow.com/api/v2/oauth/guest/token:grant",
        "https://100067.connect.garena.com/oauth/guest/token/grant",
    ])
    major_login_endpoints: List[str] = field(default_factory=lambda: [
        "https://loginbp.ggwhitehawk.com/MajorLogin",
        "https://loginbp.ggpolarbear.com/MajorLogin",
        "https://loginbp.ggblueshark.com/MajorLogin",
        "https://loginbp.common.ggbluefox.com/MajorLogin",
        "https://100067.connect.garena.com/MajorLogin",
    ])
    login_data_url: str = "https://clientbp.ggpolarbear.com/GetLoginData"
    player_info_url: str = "https://clientbp.ggpolarbear.com/GetPlayerPersonalShow"
    use_new_oauth: bool = True
    user_agent: str = "GarenaMSDK/4.0.19P10(I2404 ;Android 15;en;US;)"
    dalvik_ua: str = "Dalvik/2.1.0 (Linux; U; Android 15; I2404 Build/AP3A.240905.015.A2_V000L1)"


@dataclass
class CheckerConfig:
    concurrent_workers: int = 5
    batch_size: int = 100
    auto_save: bool = True
    save_interval: int = 10  # Save progress every N accounts
    validate_passwords: bool = True
    check_server_status: bool = True
    default_region: Region = Region.GLOBAL
    custom_region_endpoint: str = ""


@dataclass
class WebConfig:
    enabled: bool = False
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = False
    secret_key: str = "change-me-in-production"
    session_timeout: int = 3600
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    api_prefix: str = "/api/v1"


@dataclass
class LoggingConfig:
    level: LogLevel = LogLevel.INFO
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    log_file: str = "logs/app.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    console_output: bool = True
    file_output: bool = True


@dataclass
class Settings:
    """Main application settings container."""
    
    # Core settings
    app_name: str = "FreeFireGuestChecker"
    version: str = "2.0.0"
    environment: str = "development"
    
    # Configuration files
    config_dir: str = "config"
    config_file: str = "config/settings.json"
    secrets_file: str = "config/secrets.json"
    
    # Module configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    checker: CheckerConfig = field(default_factory=CheckerConfig)
    web: WebConfig = field(default_factory=WebConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return {
            "app_name": self.app_name,
            "version": self.version,
            "environment": self.environment,
            "config_dir": self.config_dir,
            "config_file": self.config_file,
            "secrets_file": self.secrets_file,
            "database": {
                "enabled": self.database.enabled,
                "path": self.database.path,
                "backup_path": self.database.backup_path,
                "max_backups": self.database.max_backups,
                "auto_backup": self.database.auto_backup,
                "vacuum_on_startup": self.database.vacuum_on_startup,
            },
            "proxy": {
                "enabled": self.proxy.enabled,
                "proxy_type": self.proxy.proxy_type.value,
                "host": self.proxy.host,
                "port": self.proxy.port,
                "username": self.proxy.username,
                "password": "***",  # Mask password
                "rotate_on_failure": self.proxy.rotate_on_failure,
                "rotation_list": self.proxy.rotation_list,
                "rotation_interval": self.proxy.rotation_interval,
            },
            "rate_limit": {
                "enabled": self.rate_limit.enabled,
                "max_requests_per_minute": self.rate_limit.max_requests_per_minute,
                "max_concurrent_requests": self.rate_limit.max_concurrent_requests,
                "request_timeout": self.rate_limit.request_timeout,
                "retry_attempts": self.rate_limit.retry_attempts,
                "retry_delay": self.rate_limit.retry_delay,
                "backoff_multiplier": self.rate_limit.backoff_multiplier,
                "cooldown_on_rate_limit": self.rate_limit.cooldown_on_rate_limit,
                "cooldown_seconds": self.rate_limit.cooldown_seconds,
            },
            "auth": {
                "client_id": self.auth.client_id,
                "client_secret": "***",  # Mask secret
                "oauth_endpoints": self.auth.oauth_endpoints,
                "major_login_endpoints": self.auth.major_login_endpoints,
                "login_data_url": self.auth.login_data_url,
                "player_info_url": self.auth.player_info_url,
                "use_new_oauth": self.auth.use_new_oauth,
            },
            "checker": {
                "concurrent_workers": self.checker.concurrent_workers,
                "batch_size": self.checker.batch_size,
                "auto_save": self.checker.auto_save,
                "save_interval": self.checker.save_interval,
                "validate_passwords": self.checker.validate_passwords,
                "check_server_status": self.checker.check_server_status,
                "default_region": self.checker.default_region.value,
                "custom_region_endpoint": self.checker.custom_region_endpoint,
            },
            "web": {
                "enabled": self.web.enabled,
                "host": self.web.host,
                "port": self.web.port,
                "debug": self.web.debug,
                "api_prefix": self.web.api_prefix,
            },
            "logging": {
                "level": self.logging.level.value,
                "format": self.logging.format,
                "date_format": self.logging.date_format,
                "log_file": self.logging.log_file,
                "max_file_size": self.logging.max_file_size,
                "backup_count": self.logging.backup_count,
                "console_output": self.logging.console_output,
                "file_output": self.logging.file_output,
            },
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Settings':
        """Create Settings from dictionary."""
        settings = cls()
        
        # Basic settings
        settings.app_name = data.get("app_name", "FreeFireGuestChecker")
        settings.version = data.get("version", "2.0.0")
        settings.environment = data.get("environment", "development")
        settings.config_dir = data.get("config_dir", "config")
        settings.config_file = data.get("config_file", "config/settings.json")
        settings.secrets_file = data.get("secrets_file", "config/secrets.json")
        
        # Database config
        db_data = data.get("database", {})
        settings.database = DatabaseConfig(
            enabled=db_data.get("enabled", True),
            path=db_data.get("path", "data/guests.db"),
            backup_path=db_data.get("backup_path", "data/backups/guests_backup_{timestamp}.db"),
            max_backups=db_data.get("max_backups", 5),
            auto_backup=db_data.get("auto_backup", True),
            vacuum_on_startup=db_data.get("vacuum_on_startup", True),
        )
        
        # Proxy config
        proxy_data = data.get("proxy", {})
        settings.proxy = ProxyConfig(
            enabled=proxy_data.get("enabled", False),
            proxy_type=ProxyType(proxy_data.get("proxy_type", "none")),
            host=proxy_data.get("host", ""),
            port=proxy_data.get("port", 0),
            username=proxy_data.get("username", ""),
            password=proxy_data.get("password", ""),
            rotate_on_failure=proxy_data.get("rotate_on_failure", False),
            rotation_list=proxy_data.get("rotation_list", []),
            rotation_interval=proxy_data.get("rotation_interval", 0),
        )
        
        # Rate limit config
        rate_data = data.get("rate_limit", {})
        settings.rate_limit = RateLimitConfig(
            enabled=rate_data.get("enabled", True),
            max_requests_per_minute=rate_data.get("max_requests_per_minute", 60),
            max_concurrent_requests=rate_data.get("max_concurrent_requests", 10),
            request_timeout=rate_data.get("request_timeout", 15.0),
            retry_attempts=rate_data.get("retry_attempts", 3),
            retry_delay=rate_data.get("retry_delay", 1.0),
            backoff_multiplier=rate_data.get("backoff_multiplier", 2.0),
            cooldown_on_rate_limit=rate_data.get("cooldown_on_rate_limit", True),
            cooldown_seconds=rate_data.get("cooldown_seconds", 60),
        )
        
        # Auth config
        auth_data = data.get("auth", {})
        settings.auth = AuthConfig(
            client_id=auth_data.get("client_id", "100067"),
            client_secret=auth_data.get("client_secret", "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3"),
            oauth_endpoints=auth_data.get("oauth_endpoints", [
                "https://ffmconnect.live.gop.garenanow.com/api/v2/oauth/guest/token:grant",
                "https://100067.connect.garena.com/oauth/guest/token/grant",
            ]),
            major_login_endpoints=auth_data.get("major_login_endpoints", [
                "https://loginbp.ggwhitehawk.com/MajorLogin",
                "https://loginbp.ggpolarbear.com/MajorLogin",
                "https://loginbp.ggblueshark.com/MajorLogin",
                "https://loginbp.common.ggbluefox.com/MajorLogin",
                "https://100067.connect.garena.com/MajorLogin",
            ]),
            login_data_url=auth_data.get("login_data_url", "https://clientbp.ggpolarbear.com/GetLoginData"),
            player_info_url=auth_data.get("player_info_url", "https://clientbp.ggpolarbear.com/GetPlayerPersonalShow"),
            use_new_oauth=auth_data.get("use_new_oauth", True),
            user_agent=auth_data.get("user_agent", "GarenaMSDK/4.0.19P10(I2404 ;Android 15;en;US;)"),
            dalvik_ua=auth_data.get("dalvik_ua", "Dalvik/2.1.0 (Linux; U; Android 15; I2404 Build/AP3A.240905.015.A2_V000L1)"),
        )
        
        # Checker config
        checker_data = data.get("checker", {})
        settings.checker = CheckerConfig(
            concurrent_workers=checker_data.get("concurrent_workers", 5),
            batch_size=checker_data.get("batch_size", 100),
            auto_save=checker_data.get("auto_save", True),
            save_interval=checker_data.get("save_interval", 10),
            validate_passwords=checker_data.get("validate_passwords", True),
            check_server_status=checker_data.get("check_server_status", True),
            default_region=Region(checker_data.get("default_region", "GLOBAL")),
            custom_region_endpoint=checker_data.get("custom_region_endpoint", ""),
        )
        
        # Web config
        web_data = data.get("web", {})
        settings.web = WebConfig(
            enabled=web_data.get("enabled", False),
            host=web_data.get("host", "0.0.0.0"),
            port=web_data.get("port", 8080),
            debug=web_data.get("debug", False),
            secret_key=web_data.get("secret_key", "change-me-in-production"),
            session_timeout=web_data.get("session_timeout", 3600),
            cors_origins=web_data.get("cors_origins", ["*"]),
            api_prefix=web_data.get("api_prefix", "/api/v1"),
        )
        
        # Logging config
        log_data = data.get("logging", {})
        settings.logging = LoggingConfig(
            level=LogLevel(log_data.get("level", "INFO")),
            format=log_data.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            date_format=log_data.get("date_format", "%Y-%m-%d %H:%M:%S"),
            log_file=log_data.get("log_file", "logs/app.log"),
            max_file_size=log_data.get("max_file_size", 10 * 1024 * 1024),
            backup_count=log_data.get("backup_count", 5),
            console_output=log_data.get("console_output", True),
            file_output=log_data.get("file_output", True),
        )
        
        return settings


class ConfigManager:
    """Manages loading, saving, and merging configuration from multiple sources."""
    
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = config_dir or "config"
        self.settings = Settings()
        self._loaded = False
        
    def _ensure_config_dir(self):
        """Ensure config directory exists."""
        Path(self.config_dir).mkdir(parents=True, exist_ok=True)
        
    def load_from_file(self, config_file: Optional[str] = None) -> bool:
        """Load configuration from JSON file."""
        config_file = config_file or os.path.join(self.config_dir, "settings.json")
        
        if not os.path.exists(config_file):
            logger.warning(f"Config file not found: {config_file}")
            return False
            
        try:
            with open(config_file, 'r') as f:
                data = json.load(f)
            
            self.settings = Settings.from_dict(data)
            self._loaded = True
            logger.info(f"Loaded configuration from {config_file}")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return False
    
    def load_from_env(self):
        """Load configuration from environment variables."""
        env_mapping = {
            "FFGC_ENVIRONMENT": ("environment", str),
            "FFGC_LOG_LEVEL": ("logging.level", lambda x: LogLevel(x.upper())),
            "FFGC_PROXY_ENABLED": ("proxy.enabled", lambda x: x.lower() in ("true", "1", "yes")),
            "FFGC_PROXY_TYPE": ("proxy.proxy_type", lambda x: ProxyType(x.lower())),
            "FFGC_PROXY_HOST": ("proxy.host", str),
            "FFGC_PROXY_PORT": ("proxy.port", int),
            "FFGC_PROXY_USER": ("proxy.username", str),
            "FFGC_PROXY_PASS": ("proxy.password", str),
            "FFGC_RATE_LIMIT_ENABLED": ("rate_limit.enabled", lambda x: x.lower() in ("true", "1", "yes")),
            "FFGC_MAX_REQUESTS": ("rate_limit.max_requests_per_minute", int),
            "FFGC_MAX_CONCURRENT": ("rate_limit.max_concurrent_requests", int),
            "FFGC_CONCURRENT_WORKERS": ("checker.concurrent_workers", int),
            "FFGC_WEB_ENABLED": ("web.enabled", lambda x: x.lower() in ("true", "1", "yes")),
            "FFGC_WEB_HOST": ("web.host", str),
            "FFGC_WEB_PORT": ("web.port", int),
            "FFGC_WEB_SECRET": ("web.secret_key", str),
        }
        
        for env_var, (path, converter) in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    self._set_nested(path, converter(value))
                    logger.debug(f"Set {path} from env {env_var}")
                except Exception as e:
                    logger.warning(f"Failed to set {path} from env {env_var}: {e}")
    
    def _set_nested(self, path: str, value: Any):
        """Set a nested attribute by path string."""
        parts = path.split('.')
        current = self.settings
        
        for part in parts[:-1]:
            if hasattr(current, part):
                current = getattr(current, part)
            else:
                raise AttributeError(f"No attribute {part}")
        
        setattr(current, parts[-1], value)
    
    def save_to_file(self, config_file: Optional[str] = None) -> bool:
        """Save current configuration to JSON file."""
        self._ensure_config_dir()
        config_file = config_file or os.path.join(self.config_dir, "settings.json")
        
        try:
            with open(config_file, 'w') as f:
                json.dump(self.settings.to_dict(), f, indent=2)
            
            logger.info(f"Saved configuration to {config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False
    
    def load(self, config_file: Optional[str] = None) -> Settings:
        """Load configuration from all sources."""
        self._ensure_config_dir()
        
        # Load from file
        self.load_from_file(config_file)
        
        # Override with environment variables
        self.load_from_env()
        
        self._loaded = True
        return self.settings
    
    def get(self) -> Settings:
        """Get current settings."""
        if not self._loaded:
            self.load()
        return self.settings
    
    def reload(self):
        """Reload configuration from all sources."""
        self._loaded = False
        return self.load()


# Global config manager instance
config_manager = ConfigManager()
