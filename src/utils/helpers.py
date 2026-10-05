"""
Helper Functions Module
Provides utility functions for common tasks.
"""

import os
import re
import time
import asyncio
import random
import hashlib
import string
import logging
from typing import Any, Callable, Coroutine, List, Optional, Tuple, TypeVar
from datetime import datetime, timedelta
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


#  Time formatting 

def format_seconds(seconds: float) -> str:
    """Format seconds into human-readable string."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def format_timestamp(timestamp: Optional[float] = None, 
                     fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format a timestamp into a readable string."""
    if timestamp is None:
        timestamp = time.time()
    return datetime.fromtimestamp(timestamp).strftime(fmt)


def format_bytes(size: int) -> str:
    """Format bytes into human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"


#  ID Generation 

def generate_uid(length: int = 10) -> str:
    """Generate a random numeric UID."""
    return ''.join(random.choices(string.digits, k=length))


def generate_guest_uid() -> str:
    """Generate a Free Fire guest UID (10-12 digits)."""
    # Free Fire UIDs are typically 10-12 digits
    length = random.choice([10, 11, 12])
    return generate_uid(length)


def validate_uid(uid: str) -> bool:
    """Validate a Free Fire UID."""
    # UID should be numeric and 8-12 digits
    return bool(re.match(r'^\d{8,12}$', uid))


def validate_password(password: str) -> bool:
    """Validate a guest account password."""
    # Password should be at least 8 characters, alphanumeric with possible hyphens
    return bool(re.match(r'^[A-Za-z0-9\-]{8,}$', password))


def sanitize_nickname(nickname: str, max_length: int = 32) -> str:
    """Sanitize a nickname for safe display and storage."""
    # Remove control characters and limit length
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', nickname)
    return sanitized[:max_length]


#  Async utilities 

async def retry_async(
    func: Callable[..., Coroutine[Any, Any, T]],
    *args: Any,
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
    **kwargs: Any,
) -> Optional[T]:
    """
    Retry an async function with exponential backoff.
    
    Args:
        func: Async function to retry
        *args: Positional arguments for the function
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for exponential backoff
        on_retry: Callback called on each retry attempt
        **kwargs: Keyword arguments for the function
        
    Returns:
        Result of the function, or None if all retries fail
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            
            if attempt < max_retries:
                wait_time = delay * (backoff ** attempt)
                logger.debug(f"Retry {attempt + 1}/{max_retries} after {wait_time:.2f}s: {e}")
                
                if on_retry:
                    try:
                        on_retry(e, attempt)
                    except Exception as retry_error:
                        logger.warning(f"Error in retry callback: {retry_error}")
                
                await asyncio.sleep(wait_time)
            else:
                logger.warning(f"All {max_retries} retries exhausted: {e}")
    
    return None


async def run_with_timeout(
    func: Callable[..., Coroutine[Any, Any, T]],
    timeout: float,
    *args: Any,
    **kwargs: Any,
) -> Tuple[Optional[T], bool]:
    """
    Run an async function with a timeout.
    
    Args:
        func: Async function to run
        timeout: Timeout in seconds
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Tuple of (result, timed_out)
    """
    try:
        result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
        return result, False
    except asyncio.TimeoutError:
        return None, True
    except Exception as e:
        return None, False


async def gather_with_concurrency(
    tasks: List[Coroutine[Any, Any, T]],
    max_concurrent: int = 10,
) -> List[Optional[T]]:
    """
    Run multiple async tasks with limited concurrency.
    
    Args:
        tasks: List of async tasks to run
        max_concurrent: Maximum number of concurrent tasks
        
    Returns:
        List of results in the same order as input tasks
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def limited_task(task: Coroutine[Any, Any, T]) -> Optional[T]:
        async with semaphore:
            try:
                return await task
            except Exception as e:
                logger.debug(f"Task failed: {e}")
                return None
    
    # Create limited tasks
    limited_tasks = [limited_task(task) for task in tasks]
    
    # Run and return results
    results = await asyncio.gather(*limited_tasks, return_exceptions=False)
    return results


#  List utilities 

def chunk_list(data: List[T], chunk_size: int) -> List[List[T]]:
    """Split a list into chunks of specified size."""
    return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]


def batch_generator(data: List[T], batch_size: int):
    """Generator that yields batches of data."""
    for i in range(0, len(data), batch_size):
        yield data[i:i + batch_size]


def filter_none(values: List[Optional[T]]) -> List[T]:
    """Filter out None values from a list."""
    return [v for v in values if v is not None]


def flatten_list(nested: List[List[T]]) -> List[T]:
    """Flatten a nested list."""
    return [item for sublist in nested for item in sublist]


#  String utilities 

def truncate(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to max length with optional suffix."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def slugify(text: str, lowercase: bool = True) -> str:
    """Convert text to URL-friendly slug."""
    # Replace special characters with underscores
    slug = re.sub(r'[^\w\s-]', '_', text)
    # Replace spaces with underscores
    slug = re.sub(r'[\s]+', '_', slug)
    # Remove leading/trailing underscores
    slug = slug.strip('_')
    if lowercase:
        slug = slug.lower()
    return slug


def mask_sensitive(value: str, show_last: int = 4) -> str:
    """Mask sensitive data, showing only last N characters."""
    if not value or len(value) <= show_last:
        return value
    return "*" * (len(value) - show_last) + value[-show_last:]


#  Hash utilities 

def md5_hash(data: str) -> str:
    """Calculate MD5 hash of string."""
    return hashlib.md5(data.encode()).hexdigest()


def sha256_hash(data: str) -> str:
    """Calculate SHA256 hash of string."""
    return hashlib.sha256(data.encode()).hexdigest()


def generate_session_id() -> str:
    """Generate a unique session ID."""
    import uuid
    return str(uuid.uuid4())


#  File utilities 

def ensure_directory(path: str) -> None:
    """Ensure a directory exists."""
    os.makedirs(path, exist_ok=True)


def get_file_size(path: str) -> int:
    """Get file size in bytes."""
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def read_file_lines(path: str, max_lines: int = None) -> List[str]:
    """Read lines from a file."""
    lines = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                lines.append(line.rstrip('\n\r'))
                if max_lines and len(lines) >= max_lines:
                    break
    except Exception as e:
        logger.warning(f"Failed to read file {path}: {e}")
    return lines


def write_file(path: str, content: str, append: bool = False) -> bool:
    """Write content to a file."""
    try:
        mode = 'a' if append else 'w'
        with open(path, mode, encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"Failed to write file {path}: {e}")
        return False


#  Timing utilities 

class Timer:
    """Simple timer for measuring execution time."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        
    def start(self):
        """Start the timer."""
        self.start_time = time.time()
        self.end_time = None
        
    def stop(self):
        """Stop the timer."""
        self.end_time = time.time()
        
    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time is None:
            return 0.0
        end = self.end_time or time.time()
        return end - self.start_time
    
    def __enter__(self):
        self.start()
        return self
        
    def __exit__(self, *args):
        self.stop()


class ContextTimer:
    """Context manager for timing code blocks."""
    
    def __init__(self, name: str = "Operation", logger: Optional[logging.Logger] = None):
        self.name = name
        self.logger = logger or logging.getLogger(__name__)
        self.start_time = None
        self.end_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        self.logger.debug(f"Starting: {self.name}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        elapsed = self.end_time - self.start_time
        
        if exc_type:
            self.logger.error(f"Failed: {self.name} in {elapsed:.3f}s - {exc_val}")
        else:
            self.logger.debug(f"Completed: {self.name} in {elapsed:.3f}s")


#  Decorators 

def timed(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to time function execution."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            logger.debug(f"Function {func.__name__} executed in {elapsed:.3f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"Function {func.__name__} failed after {elapsed:.3f}s: {e}")
            raise
    return wrapper


def async_timed(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
    """Decorator to time async function execution."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = await func(*args, **kwargs)
            elapsed = time.time() - start
            logger.debug(f"Async function {func.__name__} executed in {elapsed:.3f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"Async function {func.__name__} failed after {elapsed:.3f}s: {e}")
            raise
    return wrapper
