"""
Test Database
Tests for database operations.
"""

import os
import sys
import tempfile
import unittest
import sqlite3
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.database import (
    Database,
    Account,
    AccountStatus,
    AccountSource,
    AccountFilter,
    CheckResult,
    AccountAlreadyExists,
    AccountNotFound,
)
from src.database.migrations import MigrationManager, run_migrations


class TestDatabase(unittest.TestCase):
    """Test database operations."""
    
    def setUp(self):
        """Set up test database."""
        # Create a temporary database file
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        
        # Create database instance
        self.db = Database(self.db_path, auto_backup=False)
        
    def tearDown(self):
        """Clean up test database."""
        # Close database connection
        self.db.close()
        
        # Remove temporary files
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        
        # Remove temp directory
        try:
            os.rmdir(self.temp_dir)
        except OSError:
            pass
    
    def test_database_creation(self):
        """Test database creation."""
        # Database should exist
        self.assertTrue(os.path.exists(self.db_path))
        
        # Check tables exist
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        self.assertIn("accounts", tables)
        self.assertIn("check_results", tables)
        self.assertIn("_migrations", tables)
        
        conn.close()
    
    def test_add_account(self):
        """Test adding an account."""
        account = Account(
            uid="1234567890",
            password="test_password",
            name="Test Account",
            source=AccountSource.MANUAL,
            region="GLOBAL",
        )
        
        result = self.db.add_account(account)
        
        self.assertEqual(result.uid, "1234567890")
        self.assertIsNotNone(result.id)
        
        # Verify account was added
        retrieved = self.db.get_account("1234567890")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.uid, "1234567890")
        self.assertEqual(retrieved.password, "test_password")
        self.assertEqual(retrieved.name, "Test Account")
    
    def test_add_duplicate_account(self):
        """Test adding duplicate account raises exception."""
        account = Account(
            uid="1234567890",
            password="test_password",
        )
        
        self.db.add_account(account)
        
        with self.assertRaises(AccountAlreadyExists):
            self.db.add_account(account)
    
    def test_get_account_not_found(self):
        """Test getting non-existent account."""
        result = self.db.get_account("9999999999")
        self.assertIsNone(result)
    
    def test_get_account_by_id(self):
        """Test getting account by ID."""
        account = Account(
            uid="1234567890",
            password="test_password",
        )
        
        added = self.db.add_account(account)
        retrieved = self.db.get_account_by_id(added.id)
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.uid, "1234567890")
    
    def test_update_account(self):
        """Test updating an account."""
        account = Account(
            uid="1234567890",
            password="test_password",
            name="Test Account",
            region="GLOBAL",
        )
        
        self.db.add_account(account)
        
        # Update account
        account.name = "Updated Account"
        account.region = "INDIA"
        
        result = self.db.update_account(account)
        
        self.assertEqual(result.name, "Updated Account")
        self.assertEqual(result.region, "INDIA")
        
        # Verify update
        retrieved = self.db.get_account("1234567890")
        self.assertEqual(retrieved.name, "Updated Account")
        self.assertEqual(retrieved.region, "INDIA")
    
    def test_update_nonexistent_account(self):
        """Test updating non-existent account raises exception."""
        account = Account(
            uid="9999999999",
            password="test_password",
        )
        
        with self.assertRaises(AccountNotFound):
            self.db.update_account(account)
    
    def test_delete_account(self):
        """Test deleting an account."""
        account = Account(
            uid="1234567890",
            password="test_password",
        )
        
        self.db.add_account(account)
        
        result = self.db.delete_account("1234567890")
        self.assertTrue(result)
        
        # Verify deletion
        retrieved = self.db.get_account("1234567890")
        self.assertIsNone(retrieved)
    
    def test_delete_nonexistent_account(self):
        """Test deleting non-existent account."""
        result = self.db.delete_account("9999999999")
        self.assertFalse(result)
    
    def test_get_all_accounts(self):
        """Test getting all accounts."""
        # Add multiple accounts
        for i in range(5):
            account = Account(
                uid=f"12345678{i:02d}",
                password=f"password{i}",
                name=f"Account {i}",
            )
            self.db.add_account(account)
        
        accounts = self.db.get_all_accounts()
        self.assertEqual(len(accounts), 5)
    
    def test_query_accounts(self):
        """Test querying accounts with filters."""
        # Add accounts with different statuses
        accounts_data = [
            ("1111111111", AccountStatus.ALIVE),
            ("2222222222", AccountStatus.BANNED),
            ("3333333333", AccountStatus.DEAD),
            ("4444444444", AccountStatus.ALIVE),
        ]
        
        for uid, status in accounts_data:
            account = Account(
                uid=uid,
                password="password",
                status=status,
            )
            self.db.add_account(account)
        
        # Query by status
        filter = AccountFilter(status=AccountStatus.ALIVE)
        accounts, total = self.db.query_accounts(filter)
        self.assertEqual(len(accounts), 2)
        self.assertEqual(total, 2)
        
        # Query by region
        filter = AccountFilter(region="GLOBAL")
        accounts, total = self.db.query_accounts(filter)
        self.assertEqual(len(accounts), 4)
    
    def test_count_accounts(self):
        """Test counting accounts."""
        # Add accounts
        for i in range(5):
            account = Account(
                uid=f"12345678{i:02d}",
                password=f"password{i}",
            )
            self.db.add_account(account)
        
        count = self.db.count_accounts()
        self.assertEqual(count, 5)
        
        # Count by filter
        filter = AccountFilter(status=AccountStatus.ALIVE)
        count = self.db.count_accounts(filter)
        self.assertEqual(count, 0)  # All have default UNKNOWN status
    
    def test_check_results(self):
        """Test check result operations."""
        # Add account
        account = Account(
            uid="1234567890",
            password="test_password",
        )
        added = self.db.add_account(account)
        
        # Add check result
        check_result = CheckResult(
            checked_at=datetime.now(),
            status=AccountStatus.ALIVE,
            oauth_status="ALIVE",
            nickname="Test Player",
            level=10,
            likes=100,
            region="GLOBAL",
        )
        
        result_id = self.db.add_check_result(added.id, check_result)
        self.assertIsNotNone(result_id)
        
        # Get check results
        results = self.db.get_check_results(added.id)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].nickname, "Test Player")
        
        # Get latest check result
        latest = self.db.get_latest_check_result(added.id)
        self.assertIsNotNone(latest)
        self.assertEqual(latest.level, 10)
    
    def test_check_history(self):
        """Test getting check history."""
        # Add account
        account = Account(
            uid="1234567890",
            password="test_password",
        )
        added = self.db.add_account(account)
        
        # Add multiple check results
        for i in range(5):
            check_result = CheckResult(
                checked_at=datetime.now(),
                status=AccountStatus.ALIVE,
                level=i * 10,
            )
            self.db.add_check_result(added.id, check_result)
        
        # Get history
        history = self.db.get_check_history(added.id, days=30)
        self.assertEqual(len(history), 5)
    
    def test_batch_operations(self):
        """Test batch operations."""
        # Create batch of accounts
        accounts = []
        for i in range(10):
            account = Account(
                uid=f"batch{i:010d}",
                password=f"password{i}",
                name=f"Batch Account {i}",
            )
            accounts.append(account)
        
        # Add batch
        success, duplicates = self.db.add_accounts_batch(accounts)
        self.assertEqual(success, 10)
        self.assertEqual(len(duplicates), 0)
        
        # Verify all added
        all_accounts = self.db.get_all_accounts()
        self.assertEqual(len(all_accounts), 10)
    
    def test_import_export(self):
        """Test import and export operations."""
        # Import JSON data
        json_data = [
            {"uid": "1111111111", "password": "pass1", "name": "Import 1"},
            {"uid": "2222222222", "password": "pass2", "name": "Import 2"},
        ]
        
        imported, duplicates = self.db.import_from_json(json_data)
        self.assertEqual(imported, 2)
        self.assertEqual(len(duplicates), 0)
        
        # Export JSON
        exported = self.db.export_to_json()
        self.assertEqual(len(exported), 2)
        
        # Export CSV
        csv_data = self.db.export_to_csv()
        self.assertIn("1111111111", csv_data)
        self.assertIn("2222222222", csv_data)
    
    def test_account_model(self):
        """Test Account model."""
        account = Account(
            uid="1234567890",
            password="test_password",
            name="Test Account",
        )
        
        # Test to_dict
        data = account.to_dict()
        self.assertEqual(data["uid"], "1234567890")
        self.assertEqual(data["password"], "***")  # Masked
        self.assertEqual(data["name"], "Test Account")
        
        # Test to_dict_with_password
        data = account.to_dict_with_password()
        self.assertEqual(data["password"], "test_password")
        
        # Test from_dict
        account_data = {
            "uid": "1234567890",
            "password": "test_password",
            "name": "Test Account",
            "status": "ALIVE",
        }
        account = Account.from_dict(account_data)
        self.assertEqual(account.uid, "1234567890")
        self.assertEqual(account.password, "test_password")
        self.assertEqual(account.name, "Test Account")
        self.assertEqual(account.status, AccountStatus.ALIVE)
        
        # Test is_valid
        self.assertTrue(account.is_valid())
        
        # Test matches
        self.assertTrue(account.matches("1234567890", "test_password"))
        self.assertFalse(account.matches("1234567890", "wrong"))
        
        # Test update_from_check
        check_result = CheckResult(
            status=AccountStatus.BANNED,
            nickname="Banned Player",
            level=5,
        )
        account.update_from_check(check_result)
        self.assertEqual(account.status, AccountStatus.BANNED)
        self.assertEqual(account.name, "Banned Player")
        self.assertEqual(account.check_count, 1)
    
    def test_check_result_model(self):
        """Test CheckResult model."""
        result = CheckResult(
            checked_at=datetime.now(),
            status=AccountStatus.ALIVE,
            oauth_status="ALIVE",
            nickname="Test Player",
            level=10,
            likes=100,
            region="GLOBAL",
            clan_name="Test Clan",
            clan_level=5,
        )
        
        # Test to_dict
        data = result.to_dict()
        self.assertEqual(data["status"], "ALIVE")
        self.assertEqual(data["nickname"], "Test Player")
        self.assertEqual(data["level"], 10)
        
        # Test from_dict
        result_data = {
            "status": "BANNED",
            "oauth_status": "FAILED",
            "ban_reason": "Test ban",
            "nickname": "Banned Player",
        }
        result = CheckResult.from_dict(result_data)
        self.assertEqual(result.status, AccountStatus.BANNED)
        self.assertEqual(result.oauth_status, "FAILED")
        self.assertEqual(result.ban_reason, "Test ban")


class TestDatabaseModels(unittest.TestCase):
    """Test database model classes."""
    
    def test_account_status(self):
        """Test AccountStatus enum."""
        self.assertEqual(AccountStatus.ALIVE.value, "ALIVE")
        self.assertEqual(AccountStatus.BANNED.value, "BANNED")
        self.assertEqual(AccountStatus.DEAD.value, "DEAD")
        self.assertEqual(AccountStatus.SERVER_DOWN.value, "SERVER_DOWN")
        self.assertEqual(AccountStatus.BLACKLISTED.value, "BLACKLISTED")
        self.assertEqual(AccountStatus.UNKNOWN.value, "UNKNOWN")
        self.assertEqual(AccountStatus.PENDING.value, "PENDING")
    
    def test_account_source(self):
        """Test AccountSource enum."""
        self.assertEqual(AccountSource.MANUAL.value, "MANUAL")
        self.assertEqual(AccountSource.GENERATED.value, "GENERATED")
        self.assertEqual(AccountSource.IMPORTED_JSON.value, "IMPORTED_JSON")
        self.assertEqual(AccountSource.IMPORTED_DB.value, "IMPORTED_DB")
        self.assertEqual(AccountSource.IMPORTED_CSV.value, "IMPORTED_CSV")
    
    def test_account_filter(self):
        """Test AccountFilter class."""
        filter = AccountFilter(
            status=AccountStatus.ALIVE,
            region="GLOBAL",
            tags=["test"],
            min_check_count=1,
            max_check_count=10,
            limit=50,
            offset=0,
        )
        
        self.assertEqual(filter.status, AccountStatus.ALIVE)
        self.assertEqual(filter.region, "GLOBAL")
        self.assertEqual(filter.tags, ["test"])
        self.assertEqual(filter.min_check_count, 1)
        self.assertEqual(filter.limit, 50)


if __name__ == "__main__":
    unittest.main()
