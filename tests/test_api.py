"""
Test API
Tests for web API routes.
"""

import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Set up Flask app for testing
os.environ['FLASK_ENV'] = 'testing'

from web.app import create_app
from config.settings import Settings


class TestAPIRoutes(unittest.TestCase):
    """Test API routes."""
    
    def setUp(self):
        """Set up test client."""
        # Create test config
        self.test_config = Settings()
        self.test_config.environment = "testing"
        self.test_config.web.secret_key = "test-secret-key"
        self.test_config.web.debug = True
        self.test_config.database.enabled = False  # Disable database for most tests
        
        # Create Flask app
        self.app = create_app(self.test_config)
        self.client = self.app.test_client()
        
        # Disable CORS for testing
        self.app.config['CORS_ENABLED'] = False
    
    def tearDown(self):
        """Clean up."""
        pass
    
    def test_api_status(self):
        """Test API status endpoint."""
        response = self.client.get('/api/v1/status')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertIn('success', data)
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        self.assertIn('app_name', data['data'])
        self.assertIn('version', data['data'])
    
    def test_api_status_with_api_key(self):
        """Test API status with API key."""
        response = self.client.get('/api/v1/status', headers={
            'X-API-Key': 'test-secret-key'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])


class TestAPIAccounts(unittest.TestCase):
    """Test API account endpoints."""
    
    def setUp(self):
        """Set up test client with database."""
        import tempfile
        
        # Create temporary database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        
        # Create test config
        self.test_config = Settings()
        self.test_config.environment = "testing"
        self.test_config.web.secret_key = "test-secret-key"
        self.test_config.web.debug = True
        self.test_config.database.enabled = True
        self.test_config.database.path = self.db_path
        
        # Create Flask app
        self.app = create_app(self.test_config)
        self.client = self.app.test_client()
        
        # Initialize database
        from src.database import Database
        self.db = Database(self.db_path, auto_backup=False)
    
    def tearDown(self):
        """Clean up."""
        import shutil
        
        # Close database
        self.db.close()
        
        # Remove temporary files
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_accounts(self):
        """Test getting accounts."""
        # Add test accounts
        from src.database import Account, AccountStatus
        
        for i in range(3):
            account = Account(
                uid=f"test{i:010d}",
                password=f"password{i}",
                name=f"Test Account {i}",
                status=AccountStatus.ALIVE,
            )
            self.db.add_account(account)
        
        # Get accounts via API
        response = self.client.get('/api/v1/accounts', headers={
            'X-API-Key': 'test-secret-key'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertTrue(data['success'])
        self.assertIn('accounts', data['data'])
        self.assertEqual(len(data['data']['accounts']), 3)
    
    def test_get_single_account(self):
        """Test getting a single account."""
        # Add test account
        from src.database import Account
        
        account = Account(
            uid="test12345678",
            password="test_password",
            name="Test Account",
        )
        self.db.add_account(account)
        
        # Get account via API
        response = self.client.get('/api/v1/accounts/test12345678', headers={
            'X-API-Key': 'test-secret-key'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['uid'], "test12345678")
        self.assertEqual(data['data']['name'], "Test Account")
        # Password should be masked
        self.assertNotIn('password', data['data'])
    
    def test_get_nonexistent_account(self):
        """Test getting non-existent account."""
        response = self.client.get('/api/v1/accounts/nonexistent', headers={
            'X-API-Key': 'test-secret-key'
        })
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
    
    def test_create_account(self):
        """Test creating an account."""
        # Create account via API
        response = self.client.post('/api/v1/accounts', 
            headers={'X-API-Key': 'test-secret-key'},
            json={
                "uid": "new12345678",
                "password": "new_password",
                "name": "New Account",
            }
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['uid'], "new12345678")
        
        # Verify account was created
        account = self.db.get_account("new12345678")
        self.assertIsNotNone(account)
        self.assertEqual(account.password, "new_password")
    
    def test_create_account_missing_fields(self):
        """Test creating account with missing fields."""
        response = self.client.post('/api/v1/accounts',
            headers={'X-API-Key': 'test-secret-key'},
            json={"name": "Incomplete Account"}
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
    
    def test_update_account(self):
        """Test updating an account."""
        # Add test account
        from src.database import Account
        
        account = Account(
            uid="update123456",
            password="original_password",
            name="Original Name",
        )
        self.db.add_account(account)
        
        # Update account via API
        response = self.client.put('/api/v1/accounts/update123456',
            headers={'X-API-Key': 'test-secret-key'},
            json={"name": "Updated Name"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
        # Verify update
        updated = self.db.get_account("update123456")
        self.assertEqual(updated.name, "Updated Name")
    
    def test_delete_account(self):
        """Test deleting an account."""
        # Add test account
        from src.database import Account
        
        account = Account(
            uid="delete123456",
            password="test_password",
        )
        self.db.add_account(account)
        
        # Delete account via API
        response = self.client.delete('/api/v1/accounts/delete123456',
            headers={'X-API-Key': 'test-secret-key'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
        # Verify deletion
        deleted = self.db.get_account("delete123456")
        self.assertIsNone(deleted)
    
    def test_delete_nonexistent_account(self):
        """Test deleting non-existent account."""
        response = self.client.delete('/api/v1/accounts/nonexistent',
            headers={'X-API-Key': 'test-secret-key'}
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertFalse(data['success'])


class TestAPIStats(unittest.TestCase):
    """Test API stats endpoint."""
    
    def setUp(self):
        """Set up test client with database."""
        import tempfile
        
        # Create temporary database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        
        # Create test config
        self.test_config = Settings()
        self.test_config.environment = "testing"
        self.test_config.web.secret_key = "test-secret-key"
        self.test_config.web.debug = True
        self.test_config.database.enabled = True
        self.test_config.database.path = self.db_path
        
        # Create Flask app
        self.app = create_app(self.test_config)
        self.client = self.app.test_client()
        
        # Initialize database
        from src.database import Database, Account, AccountStatus
        self.db = Database(self.db_path, auto_backup=False)
        
        # Add test accounts with different statuses
        for i, status in enumerate([AccountStatus.ALIVE, AccountStatus.BANNED, 
                                     AccountStatus.DEAD, AccountStatus.ALIVE]):
            account = Account(
                uid=f"stats{i:010d}",
                password=f"password{i}",
                status=status,
                region="GLOBAL",
            )
            self.db.add_account(account)
    
    def tearDown(self):
        """Clean up."""
        import shutil
        
        # Close database
        self.db.close()
        
        # Remove temporary files
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_stats(self):
        """Test getting statistics."""
        response = self.client.get('/api/v1/stats', headers={
            'X-API-Key': 'test-secret-key'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertTrue(data['success'])
        self.assertIn('total', data['data'])
        self.assertEqual(data['data']['total'], 4)
        self.assertIn('by_status', data['data'])
        self.assertEqual(data['data']['by_status']['ALIVE'], 2)
        self.assertEqual(data['data']['by_status']['BANNED'], 1)
        self.assertEqual(data['data']['by_status']['DEAD'], 1)


class TestAPIErrorHandling(unittest.TestCase):
    """Test API error handling."""
    
    def setUp(self):
        """Set up test client."""
        # Create test config
        self.test_config = Settings()
        self.test_config.environment = "testing"
        self.test_config.web.secret_key = "test-secret-key"
        self.test_config.web.debug = True
        self.test_config.database.enabled = False
        
        # Create Flask app
        self.app = create_app(self.test_config)
        self.client = self.app.test_client()
    
    def test_missing_api_key(self):
        """Test request without API key."""
        response = self.client.get('/api/v1/accounts')
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('API key required', data['error'])
    
    def test_invalid_api_key(self):
        """Test request with invalid API key."""
        response = self.client.get('/api/v1/accounts', headers={
            'X-API-Key': 'wrong-key'
        })
        
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
    
    def test_disabled_database(self):
        """Test account endpoints with disabled database."""
        response = self.client.get('/api/v1/accounts', headers={
            'X-API-Key': 'test-secret-key'
        })
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('Database is disabled', data['error'])


if __name__ == "__main__":
    unittest.main()
