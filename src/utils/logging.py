"""
Enhanced Logging Module
Provides colored logging, file rotation, and structured logging.
"""

import os
import sys
import json
import logging
import logging.handlers
from datetime import datetime
from typing import Optional, Dict, Any
from colorama import Fore, Back, Style, init as colorama_init

# Initialize colorama for cross-platform colored output
colorama_init(strip=False, convert=True)


class ColorFormatter(logging.Formatter):
    """
    Custom formatter that adds colors to log levels.
    """
    
    # Color mapping for log levels
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Back.WHITE + Style.BRIGHT,
    }
    
    # Reset style
    RESET = Style.RESET_ALL
    
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None, 
                 use_colors: bool = True, include_module: bool = True):
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors
        self.include_module = include_module
        
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with colors."""
        # First, format the message without colors
        message = super().format(record)
        
        if not self.use_colors:
            return message
        
        # Get color for this level
        level_color = self.COLORS.get(record.levelname, Fore.WHITE)
        
        # Split the message and color the level
        if self.include_module:
            # Format: TIME - MODULE - LEVEL - MESSAGE
            parts = message.split(' - ', 3)
            if len(parts) >= 4:
                time_part, module_part, level_part, msg_part = parts
                colored_level = f"{level_color}{level_part}{self.RESET}"
                return f"{time_part} - {module_part} - {colored_level} - {msg_part}"
        else:
            # Format: TIME - LEVEL - MESSAGE
            parts = message.split(' - ', 2)
            if len(parts) >= 3:
                time_part, level_part, msg_part = parts
                colored_level = f"{level_color}{level_part}{self.RESET}"
                return f"{time_part} - {colored_level} - {msg_part}"
        
        return message
    
    def format_time(self, record: logging.LogRecord, datefmt: Optional[str] = None) -> str:
        """Format the time with color."""
        if datefmt:
            return datetime.fromtimestamp(record.created).strftime(datefmt)
        else:
            return super().formatTime(record, datefmt)


class JSONFormatter(logging.Formatter):
    """
    Formatter that outputs log records as JSON.
    """
    
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None,
                 include_extra: bool = True):
        super().__init__(fmt, datefmt)
        self.include_extra = include_extra
        
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'levelnum': record.levelno,
            'message': record.getMessage(),
            'module': record.module,
            'funcName': record.funcName,
            'lineno': record.lineno,
            'thread': record.threadName,
            'process': record.processName,
        }
        
        # Add extra fields
        if self.include_extra:
            for key, value in record.__dict__.items():
                if key not in log_data and not key.startswith('_'):
                    try:
                        json.dumps(value)  # Check if serializable
                        log_data[key] = value
                    except (TypeError, ValueError):
                        log_data[key] = str(value)
        
        # Handle exception info
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
            log_data['exc_text'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, default=str)


class FileFormatter(logging.Formatter):
    """
    Simple formatter for file output (no colors).
    """
    
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None):
        fmt = fmt or "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        datefmt = datefmt or "%Y-%m-%d %H:%M:%S"
        super().__init__(fmt, datefmt)


def setup_logging(
    config: Optional[Dict[str, Any]] = None,
    log_file: Optional[str] = None,
    level: Optional[int] = None,
    console: bool = True,
    file_output: bool = True,
    json_format: bool = False,
    use_colors: bool = True,
) -> logging.Logger:
    """
    Set up logging with the specified configuration.
    
    Args:
        config: Logging configuration dictionary
        log_file: Path to log file
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        console: Enable console output
        file_output: Enable file output
        json_format: Use JSON format for output
        use_colors: Use colored output for console
        
    Returns:
        Configured logger
    """
    
    # Default configuration
    if config is None:
        config = {}
    
    # Get settings from config or defaults
    log_level = level or getattr(logging, config.get('level', 'INFO'), logging.INFO)
    log_file_path = log_file or config.get('log_file', 'logs/app.log')
    max_bytes = config.get('max_file_size', 10 * 1024 * 1024)  # 10MB
    backup_count = config.get('backup_count', 5)
    fmt = config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    date_fmt = config.get('date_format', '%Y-%m-%d %H:%M:%S')
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Clear existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        
        if json_format:
            console_formatter = JSONFormatter(fmt, date_fmt)
        else:
            console_formatter = ColorFormatter(fmt, date_fmt, use_colors, True)
        
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if file_output:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Use rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8',
        )
        file_handler.setLevel(log_level)
        
        if json_format:
            file_formatter = JSONFormatter(fmt, date_fmt, False)
        else:
            file_formatter = FileFormatter(fmt, date_fmt)
        
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Set up root logger level
    logging.getLogger().setLevel(log_level)
    
    # Reduce noise from third-party libraries
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('protobuf').setLevel(logging.WARNING)
    
    return logger


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Get a logger with the specified name and level.
    
    Args:
        name: Logger name (usually __name__)
        level: Logging level (defaults to parent level)
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    if level is not None:
        logger.setLevel(level)
    return logger


def log_exception(logger: logging.Logger, message: str, exc: Exception, 
                  extra: Optional[Dict[str, Any]] = None) -> None:
    """
    Log an exception with additional context.
    
    Args:
        logger: Logger instance
        message: Error message
        exc: Exception instance
        extra: Additional context to include in log
    """
    extra_info = extra or {}
    extra_info['exception_type'] = type(exc).__name__
    extra_info['exception_str'] = str(exc)
    
    logger.error(message, extra=extra_info, exc_info=True)


def log_request(logger: logging.Logger, method: str, url: str, 
                status_code: int, duration: float, 
                extra: Optional[Dict[str, Any]] = None) -> None:
    """
    Log HTTP request details.
    
    Args:
        logger: Logger instance
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        status_code: Response status code
        duration: Request duration in seconds
        extra: Additional context
    """
    extra_info = extra or {}
    extra_info.update({
        'http_method': method,
        'url': url,
        'status_code': status_code,
        'duration_seconds': duration,
    })
    
    if status_code >= 400:
        logger.warning(f"Request failed: {method} {url} -> {status_code} ({duration:.2f}s)", 
                      extra=extra_info)
    else:
        logger.debug(f"Request: {method} {url} -> {status_code} ({duration:.2f}s)", 
                     extra=extra_info)


class ProgressLogger:
    """
    Logger for tracking progress of long-running operations.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None, 
                 total: int = 0, description: str = "Processing"):
        self.logger = logger or logging.getLogger(__name__)
        self.total = total
        self.current = 0
        self.description = description
        self.start_time = None
        self.last_update = 0
        
    def start(self, total: int = None, description: str = None):
        """Start tracking progress."""
        if total is not None:
            self.total = total
        if description is not None:
            self.description = description
        self.current = 0
        self.start_time = datetime.now()
        self.last_update = 0
        self.logger.info(f"Starting: {self.description} ({self.total} items)")
        
    def update(self, count: int = 1, message: str = None):
        """Update progress."""
        self.current += count
        current_time = datetime.now()
        
        # Log progress every 10% or every 100 items
        if self.total > 0:
            pct = (self.current / self.total) * 100
            if pct >= self.last_update + 10 or count >= 100:
                elapsed = (current_time - self.start_time).total_seconds()
                if elapsed > 0:
                    speed = self.current / elapsed
                    remaining = (self.total - self.current) / speed if speed > 0 else 0
                    self.logger.info(
                        f"Progress: {self.current}/{self.total} ({pct:.1f}%) "
                        f"- {speed:.2f} items/s - ETA: {remaining:.1f}s"
                    )
                else:
                    self.logger.info(f"Progress: {self.current}/{self.total} ({pct:.1f}%)")
                self.last_update = pct // 10 * 10
        
        if message:
            self.logger.debug(f"{self.description}: {message}")
            
    def finish(self, message: str = None):
        """Finish tracking progress."""
        current_time = datetime.now()
        elapsed = (current_time - self.start_time).total_seconds()
        
        if self.total > 0 and elapsed > 0:
            speed = self.current / elapsed
            self.logger.info(
                f"Completed: {self.description} - {self.current}/{self.total} "
                f"items in {elapsed:.2f}s ({speed:.2f} items/s)"
            )
        else:
            self.logger.info(f"Completed: {self.description} - {self.current} items")
        
        if message:
            self.logger.info(f"Result: {message}")
