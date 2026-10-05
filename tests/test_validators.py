"""
Test Validators
Tests for validation functions.
"""

import unittest
import pytest
from src.utils.validators import (
    validate_account_data,
    validate_batch_size,
    validate_concurrency,
    validate_proxy_config,
    validate_endpoint_url,
    validate_oauth_config,
    validate_rate_limit_config,
    validate_checker_config,
    validate_web_config,
    validate_all_config,
    validate_and_raise,
    ValidationResult,
    ValidationError,
)
from src.utils.helpers import validate_uid, validate_password


class TestValidators(unittest.TestCase):
    """Test validation functions."""
    
    def test_validate_uid(self):
        """Test UID validation."""
        # Valid UIDs
        self.assertTrue(validate_uid("1234567890"))
        self.assertTrue(validate_uid("12345678"))
        self.assertTrue(validate_uid("123456789012"))
        
        # Invalid UIDs
        self.assertFalse(validate_uid("123"))  # Too short
        self.assertFalse(validate_uid("1234567890123"))  # Too long
        self.assertFalse(validate_uid("abc123"))  # Non-numeric
        self.assertFalse(validate_uid(""))  # Empty
        
    def test_validate_password(self):
        """Test password validation."""
        # Valid passwords
        self.assertTrue(validate_password("password123"))
        self.assertTrue(validate_password("PASSWORD-123"))
        self.assertTrue(validate_password("a1b2c3d4e5f6"))
        
        # Invalid passwords
        self.assertFalse(validate_password("short"))  # Too short
        self.assertFalse(validate_password("password with spaces"))  # Spaces
        self.assertFalse(validate_password(""))  # Empty
        
    def test_validate_account_data(self):
        """Test account data validation."""
        # Valid account
        valid_account = {
            "uid": "1234567890",
            "password": "password123",
        }
        result = validate_account_data(valid_account)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
        
        # Missing UID
        invalid_account = {
            "password": "password123",
        }
        result = validate_account_data(invalid_account)
        self.assertFalse(result.is_valid)
        self.assertTrue(any(e.field == "uid" for e in result.errors))
        
        # Missing password
        invalid_account = {
            "uid": "1234567890",
        }
        result = validate_account_data(invalid_account)
        self.assertFalse(result.is_valid)
        self.assertTrue(any(e.field == "password" for e in result.errors))
        
        # Invalid UID format
        invalid_account = {
            "uid": "abc",
            "password": "password123",
        }
        result = validate_account_data(invalid_account)
        self.assertFalse(result.is_valid)
        self.assertTrue(any(e.field == "uid" for e in result.errors))
        
        # Long nickname
        invalid_account = {
            "uid": "1234567890",
            "password": "password123",
            "nickname": "a" * 33,
        }
        result = validate_account_data(invalid_account)
        self.assertFalse(result.is_valid)
        self.assertTrue(any(e.field == "nickname" for e in result.errors))
        
    def test_validate_batch_size(self):
        """Test batch size validation."""
        # Valid batch sizes
        self.assertTrue(validate_batch_size(1).is_valid)
        self.assertTrue(validate_batch_size(100).is_valid)
        self.assertTrue(validate_batch_size(10000).is_valid)
        
        # Invalid batch sizes
        self.assertFalse(validate_batch_size(0).is_valid)
        self.assertFalse(validate_batch_size(-1).is_valid)
        self.assertFalse(validate_batch_size(10001).is_valid)
        self.assertFalse(validate_batch_size("100").is_valid)  # Not an integer
        
    def test_validate_concurrency(self):
        """Test concurrency validation."""
        # Valid concurrency
        self.assertTrue(validate_concurrency(1).is_valid)
        self.assertTrue(validate_concurrency(10).is_valid)
        self.assertTrue(validate_concurrency(50).is_valid)
        
        # Invalid concurrency
        self.assertFalse(validate_concurrency(0).is_valid)
        self.assertFalse(validate_concurrency(-1).is_valid)
        self.assertFalse(validate_concurrency(51).is_valid)
        self.assertFalse(validate_concurrency("10").is_valid)  # Not an integer
        
    def test_validate_proxy_config(self):
        """Test proxy configuration validation."""
        # Valid proxy config
        valid_config = {
            "enabled": True,
            "proxy_type": "http",
            "host": "proxy.example.com",
            "port": 8080,
        }
        result = validate_proxy_config(valid_config)
        self.assertTrue(result.is_valid)
        
        # Disabled proxy (no other fields required)
        disabled_config = {"enabled": False}
        result = validate_proxy_config(disabled_config)
        self.assertTrue(result.is_valid)
        
        # Missing host
        invalid_config = {
            "enabled": True,
            "proxy_type": "http",
        }
        result = validate_proxy_config(invalid_config)
        self.assertFalse(result.is_valid)
        self.assertTrue(any(e.field == "proxy.host" for e in result.errors))
        
        # Invalid proxy type
        invalid_config = {
            "enabled": True,
            "proxy_type": "invalid",
            "host": "proxy.example.com",
        }
        result = validate_proxy_config(invalid_config)
        self.assertFalse(result.is_valid)
        self.assertTrue(any(e.field == "proxy.proxy_type" for e in result.errors))
        
        # Invalid port
        invalid_config = {
            "enabled": True,
            "proxy_type": "http",
            "host": "proxy.example.com",
            "port": 70000,
        }
        result = validate_proxy_config(invalid_config)
        self.assertFalse(result.is_valid)
        self.assertTrue(any(e.field == "proxy.port" for e in result.errors))
        
    def test_validate_endpoint_url(self):
        """Test endpoint URL validation."""
        # Valid URLs
        self.assertTrue(validate_endpoint_url("https://example.com/api").is_valid)
        self.assertTrue(validate_endpoint_url("http://localhost:8080/api").is_valid)
        
        # Invalid URLs
        self.assertFalse(validate_endpoint_url("").is_valid)
        self.assertFalse(validate_endpoint_url("not-a-url").is_valid)
        self.assertFalse(validate_endpoint_url("ftp://example.com").is_valid)
        
        # HTTPS required
        result = validate_endpoint_url("http://example.com", require_https=True)
        self.assertFalse(result.is_valid)
        
    def test_validate_oauth_config(self):
        """Test OAuth configuration validation."""
        # Valid OAuth config
        valid_config = {
            "client_id": "12345",
            "client_secret": "secret",
            "oauth_endpoints": ["https://oauth.example.com"],
        }
        result = validate_oauth_config(valid_config)
        self.assertTrue(result.is_valid)
        
        # Missing client_id
        invalid_config = {
            "client_secret": "secret",
            "oauth_endpoints": ["https://oauth.example.com"],
        }
        result = validate_oauth_config(invalid_config)
        self.assertFalse(result.is_valid)
        
        # Missing client_secret
        invalid_config = {
            "client_id": "12345",
            "oauth_endpoints": ["https://oauth.example.com"],
        }
        result = validate_oauth_config(invalid_config)
        self.assertFalse(result.is_valid)
        
        # No endpoints
        invalid_config = {
            "client_id": "12345",
            "client_secret": "secret",
            "oauth_endpoints": [],
        }
        result = validate_oauth_config(invalid_config)
        self.assertFalse(result.is_valid)
        
    def test_validate_rate_limit_config(self):
        """Test rate limit configuration validation."""
        # Valid config
        valid_config = {
            "max_requests_per_minute": 60,
            "max_concurrent_requests": 10,
            "request_timeout": 15.0,
            "retry_attempts": 3,
        }
        result = validate_rate_limit_config(valid_config)
        self.assertTrue(result.is_valid)
        
        # Invalid max requests
        invalid_config = {
            "max_requests_per_minute": -1,
        }
        result = validate_rate_limit_config(invalid_config)
        self.assertFalse(result.is_valid)
        
        # Invalid timeout
        invalid_config = {
            "request_timeout": -5.0,
        }
        result = validate_rate_limit_config(invalid_config)
        self.assertFalse(result.is_valid)
        
    def test_validate_checker_config(self):
        """Test checker configuration validation."""
        # Valid config
        valid_config = {
            "concurrent_workers": 5,
            "batch_size": 100,
        }
        result = validate_checker_config(valid_config)
        self.assertTrue(result.is_valid)
        
        # Invalid concurrency
        invalid_config = {
            "concurrent_workers": 100,
        }
        result = validate_checker_config(invalid_config)
        self.assertFalse(result.is_valid)
        
        # Invalid batch size
        invalid_config = {
            "batch_size": 20000,
        }
        result = validate_checker_config(invalid_config)
        self.assertFalse(result.is_valid)
        
    def test_validate_web_config(self):
        """Test web configuration validation."""
        # Valid config
        valid_config = {
            "enabled": True,
            "host": "0.0.0.0",
            "port": 8080,
        }
        result = validate_web_config(valid_config)
        self.assertTrue(result.is_valid)
        
        # Invalid port
        invalid_config = {
            "enabled": True,
            "port": 70000,
        }
        result = validate_web_config(invalid_config)
        self.assertFalse(result.is_valid)
        
    def test_validate_all_config(self):
        """Test full configuration validation."""
        # Valid full config
        valid_config = {
            "proxy": {"enabled": False},
            "auth": {
                "client_id": "12345",
                "client_secret": "secret",
                "oauth_endpoints": ["https://oauth.example.com"],
            },
            "rate_limit": {
                "max_requests_per_minute": 60,
            },
            "checker": {
                "concurrent_workers": 5,
            },
            "web": {
                "enabled": True,
                "port": 8080,
            },
        }
        result = validate_all_config(valid_config)
        self.assertTrue(result.is_valid)
        
        # Invalid config with multiple errors
        invalid_config = {
            "proxy": {"enabled": True},  # Missing host
            "auth": {},  # Missing required fields
            "rate_limit": {"max_requests_per_minute": -1},
            "checker": {"concurrent_workers": 100},
            "web": {"port": 70000},
        }
        result = validate_all_config(invalid_config)
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)


class TestValidationExceptions(unittest.TestCase):
    """Test validation exception handling."""
    
    def test_validate_and_raise_valid(self):
        """Test validate_and_raise with valid data."""
        data = {"uid": "1234567890", "password": "password123"}
        result = validate_and_raise(data, validate_account_data)
        self.assertEqual(result, data)
        
    def test_validate_and_raise_invalid(self):
        """Test validate_and_raise with invalid data."""
        data = {"password": "password123"}  # Missing UID
        
        with self.assertRaises(ValueError):
            validate_and_raise(data, validate_account_data)


class TestValidationModels(unittest.TestCase):
    """Test validation model classes."""
    
    def test_validation_error(self):
        """Test ValidationError class."""
        error = ValidationError(
            field="test_field",
            message="Test error message",
            value="test_value",
        )
        
        self.assertEqual(error.field, "test_field")
        self.assertEqual(error.message, "Test error message")
        self.assertEqual(error.value, "test_value")
        self.assertIn("test_field", str(error))
        
    def test_validation_result(self):
        """Test ValidationResult class."""
        result = ValidationResult(is_valid=True)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
        
        result.add_error("field1", "Error 1")
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.errors), 1)
        
        result.add_error("field2", "Error 2", "value2")
        self.assertEqual(len(result.errors), 2)
        
        self.assertIn("Validation failed", str(result))


if __name__ == "__main__":
    unittest.main()
