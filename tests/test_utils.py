"""
Test Utilities
Tests for utility functions.
"""

import os
import sys
import time
import asyncio
import unittest
from datetime import datetime, timedelta
from io import StringIO

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.utils.helpers import (
    format_seconds,
    format_timestamp,
    format_bytes,
    generate_uid,
    validate_uid,
    validate_password,
    sanitize_nickname,
    retry_async,
    chunk_list,
    batch_generator,
    filter_none,
    flatten_list,
    truncate,
    slugify,
    mask_sensitive,
    md5_hash,
    sha256_hash,
    generate_session_id,
    ensure_directory,
    get_file_size,
    read_file_lines,
    write_file,
    Timer,
    ContextTimer,
    timed,
    async_timed,
)
from src.utils.crypto import (
    encrypt_aes_cbc,
    decrypt_aes_cbc,
    generate_aes_key,
    generate_aes_iv,
    CryptoError,
    DEFAULT_API_KEY,
    DEFAULT_API_IV,
)
from src.utils.logging import (
    ColorFormatter,
    JSONFormatter,
    FileFormatter,
    setup_logging,
    get_logger,
    log_exception,
    log_request,
    ProgressLogger,
)


class TestTimeFormatting(unittest.TestCase):
    """Test time formatting functions."""
    
    def test_format_seconds(self):
        """Test seconds formatting."""
        self.assertEqual(format_seconds(0.5), "500ms")
        self.assertEqual(format_seconds(1), "1.0s")
        self.assertEqual(format_seconds(30), "30.0s")
        self.assertEqual(format_seconds(90), "1m 30s")
        self.assertEqual(format_seconds(3661), "1h 1m")
    
    def test_format_timestamp(self):
        """Test timestamp formatting."""
        timestamp = 1700000000  # 2023-11-14 22:13:20 UTC
        result = format_timestamp(timestamp)
        self.assertIn("2023", result)
        
        # Custom format
        result = format_timestamp(timestamp, "%Y-%m-%d")
        self.assertEqual(result, "2023-11-14")
    
    def test_format_bytes(self):
        """Test bytes formatting."""
        self.assertEqual(format_bytes(0), "0.00 B")
        self.assertEqual(format_bytes(100), "100.00 B")
        self.assertEqual(format_bytes(1024), "1.00 KB")
        self.assertEqual(format_bytes(1024 * 1024), "1.00 MB")
        self.assertEqual(format_bytes(1024 * 1024 * 1024), "1.00 GB")


class TestIDGeneration(unittest.TestCase):
    """Test ID generation functions."""
    
    def test_generate_uid(self):
        """Test UID generation."""
        uid = generate_uid(10)
        self.assertEqual(len(uid), 10)
        self.assertTrue(uid.isdigit())
    
    def test_validate_uid(self):
        """Test UID validation."""
        self.assertTrue(validate_uid("1234567890"))
        self.assertTrue(validate_uid("12345678"))
        self.assertFalse(validate_uid("123"))
        self.assertFalse(validate_uid("abc"))
    
    def test_validate_password(self):
        """Test password validation."""
        self.assertTrue(validate_password("password123"))
        self.assertTrue(validate_password("PASS-WORD"))
        self.assertFalse(validate_password("short"))
        self.assertFalse(validate_password("pass word"))


class TestStringUtilities(unittest.TestCase):
    """Test string utility functions."""
    
    def test_sanitize_nickname(self):
        """Test nickname sanitization."""
        # Remove control characters
        self.assertEqual(sanitize_nickname("Test\x00Name"), "TestName")
        # Limit length
        long_name = "a" * 40
        self.assertEqual(len(sanitize_nickname(long_name)), 32)
    
    def test_truncate(self):
        """Test truncation."""
        self.assertEqual(truncate("short", 10), "short")
        self.assertEqual(truncate("this is a long string", 10), "this is...")
        self.assertEqual(truncate("this is a long string", 20, ""), "this is a long str")
    
    def test_slugify(self):
        """Test slugification."""
        self.assertEqual(slugify("Test String"), "test_string")
        self.assertEqual(slugify("Test-String_123"), "test-string_123")
        self.assertEqual(slugify("Test String", False), "Test_String")
    
    def test_mask_sensitive(self):
        """Test sensitive data masking."""
        self.assertEqual(mask_sensitive("password"), "pass****")
        self.assertEqual(mask_sensitive("1234"), "1234")
        self.assertEqual(mask_sensitive("secret1234", 2), "******1234")


class TestHashUtilities(unittest.TestCase):
    """Test hash utility functions."""
    
    def test_md5_hash(self):
        """Test MD5 hashing."""
        result = md5_hash("test")
        self.assertEqual(len(result), 32)  # MD5 produces 32 hex chars
    
    def test_sha256_hash(self):
        """Test SHA256 hashing."""
        result = sha256_hash("test")
        self.assertEqual(len(result), 64)  # SHA256 produces 64 hex chars
    
    def test_generate_session_id(self):
        """Test session ID generation."""
        session_id = generate_session_id()
        self.assertTrue(len(session_id) > 0)
        # Should be a UUID
        self.assertIn("-", session_id)


class TestListUtilities(unittest.TestCase):
    """Test list utility functions."""
    
    def test_chunk_list(self):
        """Test chunking list."""
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        chunks = chunk_list(data, 3)
        self.assertEqual(len(chunks), 4)
        self.assertEqual(chunks[0], [1, 2, 3])
        self.assertEqual(chunks[3], [10])
    
    def test_batch_generator(self):
        """Test batch generator."""
        data = [1, 2, 3, 4, 5]
        batches = list(batch_generator(data, 2))
        self.assertEqual(len(batches), 3)
        self.assertEqual(batches[0], [1, 2])
        self.assertEqual(batches[2], [5])
    
    def test_filter_none(self):
        """Test filtering None values."""
        data = [1, None, 2, None, 3]
        result = filter_none(data)
        self.assertEqual(result, [1, 2, 3])
    
    def test_flatten_list(self):
        """Test flattening nested list."""
        data = [[1, 2], [3, 4], [5]]
        result = flatten_list(data)
        self.assertEqual(result, [1, 2, 3, 4, 5])


class TestFileUtilities(unittest.TestCase):
    """Test file utility functions."""
    
    def setUp(self):
        """Set up temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_ensure_directory(self):
        """Test directory creation."""
        path = os.path.join(self.temp_dir, "test", "nested")
        ensure_directory(path)
        self.assertTrue(os.path.exists(path))
    
    def test_get_file_size(self):
        """Test file size retrieval."""
        path = os.path.join(self.temp_dir, "test.txt")
        with open(path, 'w') as f:
            f.write("test content")
        
        size = get_file_size(path)
        self.assertEqual(size, 12)
        
        # Non-existent file
        size = get_file_size("/nonexistent/file.txt")
        self.assertEqual(size, 0)
    
    def test_read_file_lines(self):
        """Test reading file lines."""
        path = os.path.join(self.temp_dir, "test.txt")
        with open(path, 'w') as f:
            f.write("line1\nline2\nline3\n")
        
        lines = read_file_lines(path)
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0], "line1")
        
        # With max lines
        lines = read_file_lines(path, max_lines=2)
        self.assertEqual(len(lines), 2)
    
    def test_write_file(self):
        """Test writing to file."""
        path = os.path.join(self.temp_dir, "test.txt")
        
        result = write_file(path, "test content")
        self.assertTrue(result)
        
        with open(path, 'r') as f:
            content = f.read()
        self.assertEqual(content, "test content")
        
        # Append mode
        result = write_file(path, "\nappended", append=True)
        self.assertTrue(result)
        
        with open(path, 'r') as f:
            content = f.read()
        self.assertEqual(content, "test content\nappended")


class TestTimingUtilities(unittest.TestCase):
    """Test timing utility classes."""
    
    def test_timer(self):
        """Test Timer class."""
        timer = Timer()
        timer.start()
        time.sleep(0.1)
        elapsed = timer.elapsed()
        self.assertGreater(elapsed, 0)
        
        timer.stop()
        elapsed2 = timer.elapsed()
        self.assertGreaterEqual(elapsed2, elapsed)
        
        # Context manager
        with Timer() as timer:
            time.sleep(0.1)
        self.assertGreater(timer.elapsed(), 0)


class TestCrypto(unittest.TestCase):
    """Test cryptographic functions."""
    
    def test_generate_aes_key(self):
        """Test AES key generation."""
        key = generate_aes_key(16)
        self.assertEqual(len(key), 16)
        
        key = generate_aes_key(24)
        self.assertEqual(len(key), 24)
        
        key = generate_aes_key(32)
        self.assertEqual(len(key), 32)
        
        # Invalid size
        with self.assertRaises(ValueError):
            generate_aes_key(10)
    
    def test_generate_aes_iv(self):
        """Test AES IV generation."""
        iv = generate_aes_iv()
        self.assertEqual(len(iv), 16)
    
    def test_aes_encryption_decryption(self):
        """Test AES encryption and decryption."""
        key = generate_aes_key(16)
        iv = generate_aes_iv()
        plaintext = b"test message"
        
        encrypted = encrypt_aes_cbc(plaintext, key, iv)
        self.assertNotEqual(encrypted, plaintext)
        
        decrypted = decrypt_aes_cbc(encrypted, key, iv)
        self.assertEqual(decrypted, plaintext)
        
        # Without padding
        encrypted = encrypt_aes_cbc(plaintext, key, iv, padding=False)
        decrypted = decrypt_aes_cbc(encrypted, key, iv, padding=False)
        self.assertEqual(decrypted, plaintext)
    
    def test_aes_errors(self):
        """Test AES error handling."""
        # Wrong key
        key1 = generate_aes_key(16)
        key2 = generate_aes_key(16)
        iv = generate_aes_iv()
        plaintext = b"test message"
        
        encrypted = encrypt_aes_cbc(plaintext, key1, iv)
        
        with self.assertRaises(CryptoError):
            decrypt_aes_cbc(encrypted, key2, iv)
        
        # Wrong IV
        with self.assertRaises(CryptoError):
            decrypt_aes_cbc(encrypted, key1, generate_aes_iv())
        
        # Invalid data
        with self.assertRaises(CryptoError):
            decrypt_aes_cbc(b"invalid data", key1, iv)


class TestLogging(unittest.TestCase):
    """Test logging functions."""
    
    def test_color_formatter(self):
        """Test ColorFormatter."""
        formatter = ColorFormatter()
        
        # Create a log record
        import logging
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        
        # Format without colors
        formatter.use_colors = False
        result = formatter.format(record)
        self.assertIn("Test message", result)
        
        # Format with colors (won't actually add colors in test environment)
        formatter.use_colors = True
        result = formatter.format(record)
        self.assertIn("Test message", result)
    
    def test_json_formatter(self):
        """Test JSONFormatter."""
        formatter = JSONFormatter()
        
        import logging
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        
        result = formatter.format(record)
        self.assertIn('"message": "Test message"', result)
        self.assertIn('"level": "INFO"', result)
    
    def test_file_formatter(self):
        """Test FileFormatter."""
        formatter = FileFormatter()
        
        import logging
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        
        result = formatter.format(record)
        self.assertIn("Test message", result)


class TestAsyncUtilities(unittest.TestCase):
    """Test async utility functions."""
    
    def test_retry_async_success(self):
        """Test retry_async with successful function."""
        async def successful_func():
            return "success"
        
        result = asyncio.run(retry_async(successful_func))
        self.assertEqual(result, "success")
    
    def test_retry_async_retry(self):
        """Test retry_async with retries."""
        call_count = 0
        
        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success after retries"
        
        result = asyncio.run(retry_async(failing_func, max_retries=3, delay=0.01))
        self.assertEqual(result, "success after retries")
        self.assertEqual(call_count, 3)
    
    def test_retry_async_all_fail(self):
        """Test retry_async with all attempts failing."""
        async def always_failing_func():
            raise Exception("Always fails")
        
        result = asyncio.run(retry_async(always_failing_func, max_retries=2, delay=0.01))
        self.assertIsNone(result)
    
    def test_async_timed(self):
        """Test async_timed decorator."""
        @async_timed
        async def timed_func():
            await asyncio.sleep(0.1)
            return "done"
        
        result = asyncio.run(timed_func())
        self.assertEqual(result, "done")


if __name__ == "__main__":
    unittest.main()
