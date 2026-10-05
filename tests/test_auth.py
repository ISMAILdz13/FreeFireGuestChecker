"""
Test Authentication
Tests for authentication module.
"""

import os
import sys
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.level.auth import LevelAuth, _encrypt_api, TEMPLATE_HEX
from src.utils.crypto import DEFAULT_API_KEY, DEFAULT_API_IV


class TestAuthEncryption(unittest.TestCase):
    """Test authentication encryption functions."""
    
    def test_encrypt_api(self):
        """Test API encryption."""
        # Test with known data
        test_hex = "0123456789abcdef0123456789abcdef"  # 32 hex chars = 16 bytes
        
        result = _encrypt_api(test_hex)
        
        # Result should be different from input
        self.assertNotEqual(result, test_hex)
        
        # Result should be valid hex
        self.assertTrue(all(c in "0123456789abcdef" for c in result))
        
        # Result should be longer (due to padding)
        self.assertGreater(len(result), len(test_hex))
    
    def test_template_hex(self):
        """Test template hex is valid."""
        # Template should be valid hex
        self.assertTrue(all(c in "0123456789abcdef" for c in TEMPLATE_HEX))
        
        # Should be able to convert to bytes
        try:
            bytes.fromhex(TEMPLATE_HEX)
        except ValueError:
            self.fail("TEMPLATE_HEX is not valid hex")


class TestLevelAuth(unittest.IsolatedAsyncioTestCase):
    """Test LevelAuth class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_http = AsyncMock()
        self.auth = LevelAuth(self.mock_http)
    
    async def test_guest_token_v2_success(self):
        """Test successful OAuth v2 authentication."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "access_token": "test_access_token",
                "open_id": "test_open_id",
            }
        }
        
        self.mock_http.post.return_value = mock_response
        
        result = await self.auth.guest_token("1234567890", "test_password")
        
        self.assertIsNotNone(result)
        self.assertEqual(result, ("test_access_token", "test_open_id"))
        
        # Check that v2 endpoint was called
        self.mock_http.post.assert_called()
        call_args = self.mock_http.post.call_args
        self.assertIn("ffmconnect.live.gop.garenanow.com", call_args[0][0])
    
    async def test_guest_token_v2_fallback_to_v1(self):
        """Test OAuth v2 failure falls back to v1."""
        # Mock v2 failure, v1 success
        mock_v2_response = MagicMock()
        mock_v2_response.status_code = 400
        
        mock_v1_response = MagicMock()
        mock_v1_response.status_code = 200
        mock_v1_response.json.return_value = {
            "access_token": "test_access_token_v1",
            "open_id": "test_open_id_v1",
        }
        
        self.mock_http.post.side_effect = [mock_v2_response, mock_v1_response]
        
        result = await self.auth.guest_token("1234567890", "test_password")
        
        self.assertIsNotNone(result)
        self.assertEqual(result, ("test_access_token_v1", "test_open_id_v1"))
        
        # Should have called both endpoints
        self.assertEqual(self.mock_http.post.call_count, 2)
    
    async def test_guest_token_failure(self):
        """Test OAuth failure."""
        # Mock all failures
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Invalid credentials"}
        
        self.mock_http.post.return_value = mock_response
        
        result = await self.auth.guest_token("1234567890", "wrong_password")
        
        self.assertIsNone(result)
    
    async def test_major_login_success(self):
        """Test successful MajorLogin."""
        # Mock successful OAuth first
        mock_oauth_response = MagicMock()
        mock_oauth_response.status_code = 200
        mock_oauth_response.json.return_value = {
            "access_token": "test_access_token",
            "open_id": "test_open_id",
        }
        
        # Mock successful MajorLogin
        mock_major_response = MagicMock()
        mock_major_response.status_code = 200
        
        # Create a mock protobuf response
        from src.database.models import AccountStatus
        
        # We'll mock the parsing to return a success
        with patch.object(self.auth, '_parse_major_login_response') as mock_parse:
            mock_parse.return_value = {
                "token": "test_jwt_token",
                "key": b"test_key",
                "iv": b"test_iv",
                "timestamp": 1234567890,
                "url": "https://test.url",
                "region": "GLOBAL",
            }
            
            self.mock_http.post.return_value = mock_major_response
            
            result = await self.auth.major_login("test_access_token", "test_open_id")
            
            self.assertIsNotNone(result)
            self.assertEqual(result["token"], "test_jwt_token")
    
    async def test_major_login_failure(self):
        """Test MajorLogin failure."""
        # Mock all failures
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.content = b"Service Unavailable"
        
        self.mock_http.post.return_value = mock_response
        
        result = await self.auth.major_login("test_access_token", "test_open_id")
        
        self.assertIsNotNone(result)
        self.assertIn("error", result)
        self.assertEqual(result["last_status"], 503)
    
    async def test_major_login_endpoint_rotation(self):
        """Test MajorLogin endpoint rotation."""
        # Mock failures on first endpoints, success on last
        mock_fail_response = MagicMock()
        mock_fail_response.status_code = 503
        mock_fail_response.content = b"Service Unavailable"
        
        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        
        # Mock parsing to return success
        with patch.object(self.auth, '_parse_major_login_response') as mock_parse:
            mock_parse.return_value = {
                "token": "test_jwt_token",
                "key": b"test_key",
                "iv": b"test_iv",
                "timestamp": 1234567890,
                "url": "https://test.url",
                "region": "GLOBAL",
            }
            
            self.mock_http.post.side_effect = [
                mock_fail_response,
                mock_fail_response,
                mock_success_response,
            ]
            
            result = await self.auth.major_login("test_access_token", "test_open_id")
            
            self.assertIsNotNone(result)
            self.assertEqual(result["token"], "test_jwt_token")
            
            # Should have tried multiple endpoints
            self.assertGreater(self.mock_http.post.call_count, 1)


class TestAuthIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for authentication flow."""
    
    async def test_full_auth_flow(self):
        """Test complete authentication flow."""
        mock_http = AsyncMock()
        auth = LevelAuth(mock_http)
        
        # Mock OAuth v2 success
        mock_oauth_response = MagicMock()
        mock_oauth_response.status_code = 200
        mock_oauth_response.json.return_value = {
            "data": {
                "access_token": "test_access_token",
                "open_id": "test_open_id",
            }
        }
        
        # Mock MajorLogin success
        mock_major_response = MagicMock()
        mock_major_response.status_code = 200
        
        # Mock parsing
        with patch.object(auth, '_parse_major_login_response') as mock_parse:
            mock_parse.return_value = {
                "token": "test_jwt_token",
                "key": b"test_key",
                "iv": b"test_iv",
                "timestamp": 1234567890,
                "url": "https://test.url",
                "region": "GLOBAL",
            }
            
            mock_http.post.side_effect = [mock_oauth_response, mock_major_response]
            
            # Step 1: OAuth
            oauth_result = await auth.guest_token("1234567890", "test_password")
            self.assertIsNotNone(oauth_result)
            
            # Step 2: MajorLogin
            access_token, open_id = oauth_result
            major_result = await auth.major_login(access_token, open_id)
            self.assertIsNotNone(major_result)
            self.assertEqual(major_result["token"], "test_jwt_token")


class TestAuthErrorHandling(unittest.IsolatedAsyncioTestCase):
    """Test error handling in authentication."""
    
    async def test_network_error_recovery(self):
        """Test recovery from network errors."""
        mock_http = AsyncMock()
        auth = LevelAuth(mock_http)
        
        # Mock network error on first attempt, success on retry
        mock_error = Exception("Network error")
        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.json.return_value = {
            "data": {
                "access_token": "test_access_token",
                "open_id": "test_open_id",
            }
        }
        
        mock_http.post.side_effect = [mock_error, mock_success]
        
        result = await self.auth.guest_token("1234567890", "test_password", retries=2)
        
        self.assertIsNotNone(result)
        self.assertEqual(result, ("test_access_token", "test_open_id"))
    
    async def test_all_retries_exhausted(self):
        """Test when all retries are exhausted."""
        mock_http = AsyncMock()
        auth = LevelAuth(mock_http)
        
        # Mock all failures
        mock_error = Exception("Network error")
        mock_http.post.side_effect = mock_error
        
        result = await self.auth.guest_token("1234567890", "test_password", retries=3)
        
        self.assertIsNone(result)
        self.assertEqual(mock_http.post.call_count, 4)  # 1 initial + 3 retries


class TestAuthTemplate(unittest.TestCase):
    """Test template handling."""
    
    def test_template_substitution(self):
        """Test template substitution in MajorLogin."""
        auth = LevelAuth(MagicMock())
        
        # Test that template contains expected placeholders
        self.assertIn("996a629dbcdb3964be6b6978f5d814db", TEMPLATE_HEX)  # open_id placeholder
        self.assertIn("ff90c07eb9815af30a43b4a9f6019516e0e4c703b44092516d0defa4cef51f2a", TEMPLATE_HEX)  # access_token placeholder
    
    def test_template_encryption(self):
        """Test that template can be encrypted."""
        # Should be able to encrypt the template
        try:
            encrypted = _encrypt_api(TEMPLATE_HEX)
            self.assertIsNotNone(encrypted)
            self.assertNotEqual(encrypted, TEMPLATE_HEX)
        except Exception as e:
            self.fail(f"Failed to encrypt template: {e}")


if __name__ == "__main__":
    unittest.main()
