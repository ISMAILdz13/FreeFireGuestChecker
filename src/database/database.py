"""
Database Module
Handles SQLite database operations for account storage.
"""

import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
from pathlib import Path

from ..config import config_manager
from .models import Account, AccountStatus, AccountSource, AccountFilter, CheckResult

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Base exception for database errors."""
    pass


class AccountAlreadyExists(DatabaseError):
    """Exception raised when account already exists."""
    def __init__(self, uid: str):
        self.uid = uid
        super().__init__(f"Account with UID {uid} already exists")


class AccountNotFound(DatabaseError):
    """Exception raised when account is not found."""
    def __init__(self, uid: str):
        self.uid = uid
        super().__init__(f"Account with UID {uid} not found")


class Database:
    """
    SQLite database manager for Free Fire guest accounts.
    
    Provides CRUD operations for accounts and check results.
    """
    
    def __init__(self, db_path: Optional[str] = None, auto_backup: bool = True):
        """
        Initialize the database.
        
        Args:
            db_path: Path to SQLite database file
            auto_backup: Whether to automatically create backups
        """
        settings = config_manager.get()
        self.db_path = db_path or settings.database.path
        self.auto_backup = auto_backup and settings.database.auto_backup
        self.backup_path = settings.database.backup_path
        self.max_backups = settings.database.max_backups
        
        self._connection: Optional[sqlite3.Connection] = None
        self._ensure_directory()
        self._initialize()
        
    def _ensure_directory(self) -> None:
        """Ensure database directory exists."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            Path(db_dir).mkdir(parents=True, exist_ok=True)
            
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        if self._connection is None:
            self._connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
            )
            self._connection.row_factory = sqlite3.Row
            
            # Enable foreign keys
            self._connection.execute("PRAGMA foreign_keys = ON")
            
            # Set journal mode for better performance
            self._connection.execute("PRAGMA journal_mode = WAL")
            
            # Set synchronous mode
            self._connection.execute("PRAGMA synchronous = NORMAL")
            
        return self._connection
    
    @contextmanager
    def _get_cursor(self):
        """Get a database cursor as a context manager."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise DatabaseError(f"Database operation failed: {e}") from e
        finally:
            cursor.close()
    
    def _initialize(self) -> None:
        """Initialize database schema."""
        try:
            with self._get_cursor() as cursor:
                # Create tables
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS accounts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        uid TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        name TEXT DEFAULT '',
                        source TEXT DEFAULT 'MANUAL',
                        region TEXT DEFAULT 'GLOBAL',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        last_checked TEXT,
                        status TEXT DEFAULT 'UNKNOWN',
                        check_count INTEGER DEFAULT 0,
                        notes TEXT DEFAULT '',
                        tags TEXT DEFAULT '[]',
                        custom_data TEXT DEFAULT '{}'
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS check_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        account_id INTEGER NOT NULL,
                        checked_at TEXT NOT NULL,
                        status TEXT NOT NULL,
                        oauth_status TEXT DEFAULT 'UNKNOWN',
                        ban_reason TEXT DEFAULT '',
                        nickname TEXT DEFAULT '',
                        level INTEGER DEFAULT 0,
                        exp INTEGER DEFAULT 0,
                        likes INTEGER DEFAULT 0,
                        rank INTEGER DEFAULT 0,
                        region TEXT DEFAULT 'Unknown',
                        clan_name TEXT DEFAULT '',
                        clan_level INTEGER DEFAULT 0,
                        release_version TEXT DEFAULT '',
                        credit_score INTEGER DEFAULT 0,
                        last_login TEXT DEFAULT '',
                        account_created TEXT DEFAULT '',
                        error TEXT,
                        FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
                    )
                """)
                
                # Create indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_uid ON accounts(uid)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_region ON accounts(region)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_source ON accounts(source)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_last_checked ON accounts(last_checked)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_account_id ON check_results(account_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_checked_at ON check_results(checked_at)")
                
                logger.info(f"Database initialized at {self.db_path}")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise DatabaseError(f"Database initialization failed: {e}") from e
    
    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            try:
                self._connection.close()
                self._connection = None
                logger.info("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing database: {e}")
    
    def backup(self) -> bool:
        """Create a backup of the database."""
        if not self.auto_backup:
            return False
        
        try:
            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.dirname(self.backup_path)
            if backup_dir:
                Path(backup_dir).mkdir(parents=True, exist_ok=True)
            
            backup_file = self.backup_path.format(timestamp=timestamp)
            
            # Copy the database file
            import shutil
            shutil.copy2(self.db_path, backup_file)
            
            # Clean up old backups
            self._cleanup_old_backups()
            
            logger.info(f"Database backup created: {backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False
    
    def _cleanup_old_backups(self) -> None:
        """Remove old backup files."""
        try:
            backup_dir = os.path.dirname(self.backup_path)
            if not backup_dir:
                return
            
            backup_pattern = os.path.basename(self.backup_path).replace("{timestamp}", "*")
            backup_files = list(Path(backup_dir).glob(backup_pattern))
            
            # Sort by modification time (oldest first)
            backup_files.sort(key=lambda f: f.stat().st_mtime)
            
            # Remove excess backups
            while len(backup_files) > self.max_backups:
                old_backup = backup_files.pop(0)
                try:
                    old_backup.unlink()
                    logger.debug(f"Removed old backup: {old_backup}")
                except Exception as e:
                    logger.warning(f"Failed to remove backup {old_backup}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
    
    def vacuum(self) -> bool:
        """Vacuum the database to reclaim space."""
        try:
            with self._get_cursor() as cursor:
                cursor.execute("VACUUM")
            logger.info("Database vacuum completed")
            return True
        except Exception as e:
            logger.error(f"Failed to vacuum database: {e}")
            return False
    
    def optimize(self) -> bool:
        """Optimize the database."""
        try:
            with self._get_cursor() as cursor:
                cursor.execute("ANALYZE")
                cursor.execute("REINDEX")
            logger.info("Database optimization completed")
            return True
        except Exception as e:
            logger.error(f"Failed to optimize database: {e}")
            return False
    
    # Account CRUD operations
    
    def add_account(self, account: Account) -> Account:
        """
        Add a new account to the database.
        
        Args:
            account: Account to add
            
        Returns:
            The added account with updated ID
            
        Raises:
            AccountAlreadyExists: If account with UID already exists
        """
        try:
            with self._get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO accounts (uid, password, name, source, region, 
                                       created_at, updated_at, last_checked, status, 
                                       check_count, notes, tags, custom_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        account.uid,
                        account.password,
                        account.name,
                        account.source.value,
                        account.region,
                        account.created_at.isoformat(),
                        account.updated_at.isoformat(),
                        account.last_checked.isoformat() if account.last_checked else None,
                        account.status.value,
                        account.check_count,
                        account.notes,
                        json.dumps(account.tags),
                        json.dumps(account.custom_data),
                    )
                )
                
                # Get the inserted account
                account.id = cursor.lastrowid
                return account
                
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed: accounts.uid" in str(e):
                raise AccountAlreadyExists(account.uid) from e
            raise DatabaseError(f"Integrity error: {e}") from e
        except Exception as e:
            raise DatabaseError(f"Failed to add account: {e}") from e
    
    def get_account(self, uid: str) -> Optional[Account]:
        """
        Get an account by UID.
        
        Args:
            uid: Account UID
            
        Returns:
            Account object or None if not found
        """
        try:
            with self._get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM accounts WHERE uid = ?",
                    (uid,)
                )
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_account(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get account {uid}: {e}")
            raise DatabaseError(f"Failed to get account: {e}") from e
    
    def get_account_by_id(self, account_id: int) -> Optional[Account]:
        """
        Get an account by database ID.
        
        Args:
            account_id: Database ID
            
        Returns:
            Account object or None if not found
        """
        try:
            with self._get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM accounts WHERE id = ?",
                    (account_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_account(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get account by ID {account_id}: {e}")
            raise DatabaseError(f"Failed to get account: {e}") from e
    
    def update_account(self, account: Account) -> Account:
        """
        Update an existing account.
        
        Args:
            account: Account to update
            
        Returns:
            The updated account
            
        Raises:
            AccountNotFound: If account does not exist
        """
        try:
            with self._get_cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE accounts 
                    SET password = ?, name = ?, source = ?, region = ?,
                        updated_at = ?, last_checked = ?, status = ?,
                        check_count = ?, notes = ?, tags = ?, custom_data = ?
                    WHERE uid = ?
                    """,
                    (
                        account.password,
                        account.name,
                        account.source.value,
                        account.region,
                        account.updated_at.isoformat(),
                        account.last_checked.isoformat() if account.last_checked else None,
                        account.status.value,
                        account.check_count,
                        account.notes,
                        json.dumps(account.tags),
                        json.dumps(account.custom_data),
                        account.uid,
                    )
                )
                
                if cursor.rowcount == 0:
                    raise AccountNotFound(account.uid)
                
                return account
                
        except Exception as e:
            logger.error(f"Failed to update account {account.uid}: {e}")
            raise DatabaseError(f"Failed to update account: {e}") from e
    
    def delete_account(self, uid: str) -> bool:
        """
        Delete an account.
        
        Args:
            uid: Account UID
            
        Returns:
            True if account was deleted, False otherwise
        """
        try:
            with self._get_cursor() as cursor:
                cursor.execute(
                    "DELETE FROM accounts WHERE uid = ?",
                    (uid,)
                )
                
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Failed to delete account {uid}: {e}")
            raise DatabaseError(f"Failed to delete account: {e}") from e
    
    def _row_to_account(self, row: sqlite3.Row) -> Account:
        """Convert database row to Account object."""
        return Account(
            id=row["id"],
            uid=row["uid"],
            password=row["password"],
            name=row["name"] or "",
            source=AccountSource(row["source"] or "MANUAL"),
            region=row["region"] or "GLOBAL",
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now(),
            last_checked=datetime.fromisoformat(row["last_checked"]) if row["last_checked"] else None,
            status=AccountStatus(row["status"] or "UNKNOWN"),
            check_count=row["check_count"] or 0,
            notes=row["notes"] or "",
            tags=json.loads(row["tags"] or "[]"),
            custom_data=json.loads(row["custom_data"] or "{}"),
        )
    
    # Query operations
    
    def get_all_accounts(self, limit: Optional[int] = None) -> List[Account]:
        """
        Get all accounts.
        
        Args:
            limit: Maximum number of accounts to return
            
        Returns:
            List of Account objects
        """
        try:
            with self._get_cursor() as cursor:
                if limit:
                    cursor.execute("SELECT * FROM accounts LIMIT ?", (limit,))
                else:
                    cursor.execute("SELECT * FROM accounts")
                
                rows = cursor.fetchall()
                return [self._row_to_account(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get all accounts: {e}")
            raise DatabaseError(f"Failed to get accounts: {e}") from e
    
    def query_accounts(self, filter: AccountFilter) -> Tuple[List[Account], int]:
        """
        Query accounts with filters.
        
        Args:
            filter: Filter criteria
            
        Returns:
            Tuple of (accounts, total_count)
        """
        try:
            # Build query
            query = "SELECT * FROM accounts"
            conditions = []
            params = []
            
            if filter.status:
                conditions.append("status = ?")
                params.append(filter.status.value)
            
            if filter.region:
                conditions.append("region = ?")
                params.append(filter.region)
            
            if filter.source:
                conditions.append("source = ?")
                params.append(filter.source.value)
            
            if filter.tags:
                for tag in filter.tags:
                    conditions.append("tags LIKE ?")
                    params.append(f"%{tag}%")
            
            if filter.min_check_count is not None:
                conditions.append("check_count >= ?")
                params.append(filter.min_check_count)
            
            if filter.max_check_count is not None:
                conditions.append("check_count <= ?")
                params.append(filter.max_check_count)
            
            if filter.has_been_checked is not None:
                if filter.has_been_checked:
                    conditions.append("last_checked IS NOT NULL")
                else:
                    conditions.append("last_checked IS NULL")
            
            if filter.last_checked_after:
                conditions.append("last_checked >= ?")
                params.append(filter.last_checked_after.isoformat())
            
            if filter.last_checked_before:
                conditions.append("last_checked <= ?")
                params.append(filter.last_checked_before.isoformat())
            
            if filter.created_after:
                conditions.append("created_at >= ?")
                params.append(filter.created_after.isoformat())
            
            if filter.created_before:
                conditions.append("created_at <= ?")
                params.append(filter.created_before.isoformat())
            
            if filter.search:
                search_pattern = f"%{filter.search}%"
                conditions.append("(uid LIKE ? OR name LIKE ? OR notes LIKE ?)")
                params.extend([search_pattern, search_pattern, search_pattern])
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            # Add order by
            if filter.order_by:
                order_direction = "DESC" if filter.order_desc else "ASC"
                query += f" ORDER BY {filter.order_by} {order_direction}"
            else:
                query += " ORDER BY created_at DESC"
            
            # Add limit and offset
            if filter.limit:
                query += " LIMIT ?"
                params.append(filter.limit)
            
            if filter.offset:
                query += " OFFSET ?"
                params.append(filter.offset)
            
            # Count query
            count_query = f"SELECT COUNT(*) FROM accounts"
            if conditions:
                count_query += " WHERE " + " AND ".join(conditions)
            
            with self._get_cursor() as cursor:
                # Get count
                cursor.execute(count_query, params[:len(params) - (2 if filter.limit and filter.offset else (1 if filter.limit or filter.offset else 0))])
                total_count = cursor.fetchone()[0]
                
                # Get accounts
                cursor.execute(query, params)
                rows = cursor.fetchall()
                accounts = [self._row_to_account(row) for row in rows]
                
                return accounts, total_count
                
        except Exception as e:
            logger.error(f"Failed to query accounts: {e}")
            raise DatabaseError(f"Failed to query accounts: {e}") from e
    
    def count_accounts(self, filter: Optional[AccountFilter] = None) -> int:
        """
        Count accounts matching filter.
        
        Args:
            filter: Optional filter criteria
            
        Returns:
            Number of matching accounts
        """
        try:
            query = "SELECT COUNT(*) FROM accounts"
            conditions = []
            params = []
            
            if filter:
                if filter.status:
                    conditions.append("status = ?")
                    params.append(filter.status.value)
                
                if filter.region:
                    conditions.append("region = ?")
                    params.append(filter.region)
                
                if filter.source:
                    conditions.append("source = ?")
                    params.append(filter.source.value)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            with self._get_cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchone()[0]
                
        except Exception as e:
            logger.error(f"Failed to count accounts: {e}")
            raise DatabaseError(f"Failed to count accounts: {e}") from e
    
    # Check result operations
    
    def add_check_result(self, account_id: int, check_result: CheckResult) -> int:
        """
        Add a check result for an account.
        
        Args:
            account_id: Database ID of the account
            check_result: Check result to add
            
        Returns:
            ID of the added check result
        """
        try:
            with self._get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO check_results (
                        account_id, checked_at, status, oauth_status, ban_reason,
                        nickname, level, exp, likes, rank, region, clan_name,
                        clan_level, release_version, credit_score, last_login,
                        account_created, error
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        account_id,
                        check_result.checked_at.isoformat(),
                        check_result.status.value,
                        check_result.oauth_status,
                        check_result.ban_reason,
                        check_result.nickname,
                        check_result.level,
                        check_result.exp,
                        check_result.likes,
                        check_result.rank,
                        check_result.region,
                        check_result.clan_name,
                        check_result.clan_level,
                        check_result.release_version,
                        check_result.credit_score,
                        check_result.last_login,
                        check_result.account_created,
                        check_result.error,
                    )
                )
                
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"Failed to add check result: {e}")
            raise DatabaseError(f"Failed to add check result: {e}") from e
    
    def get_check_results(self, account_id: int, limit: int = 10) -> List[CheckResult]:
        """
        Get check results for an account.
        
        Args:
            account_id: Database ID of the account
            limit: Maximum number of results to return
            
        Returns:
            List of CheckResult objects
        """
        try:
            with self._get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM check_results 
                    WHERE account_id = ? 
                    ORDER BY checked_at DESC 
                    LIMIT ?
                    """,
                    (account_id, limit)
                )
                
                rows = cursor.fetchall()
                return [self._row_to_check_result(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get check results for account {account_id}: {e}")
            raise DatabaseError(f"Failed to get check results: {e}") from e
    
    def _row_to_check_result(self, row: sqlite3.Row) -> CheckResult:
        """Convert database row to CheckResult object."""
        return CheckResult(
            checked_at=datetime.fromisoformat(row["checked_at"]) if row["checked_at"] else datetime.now(),
            status=AccountStatus(row["status"] or "UNKNOWN"),
            oauth_status=row["oauth_status"] or "UNKNOWN",
            ban_reason=row["ban_reason"] or "",
            nickname=row["nickname"] or "",
            level=row["level"] or 0,
            exp=row["exp"] or 0,
            likes=row["likes"] or 0,
            rank=row["rank"] or 0,
            region=row["region"] or "Unknown",
            clan_name=row["clan_name"] or "",
            clan_level=row["clan_level"] or 0,
            release_version=row["release_version"] or "",
            credit_score=row["credit_score"] or 0,
            last_login=row["last_login"] or "",
            account_created=row["account_created"] or "",
            error=row["error"],
        )
    
    def get_latest_check_result(self, account_id: int) -> Optional[CheckResult]:
        """
        Get the latest check result for an account.
        
        Args:
            account_id: Database ID of the account
            
        Returns:
            Latest CheckResult or None
        """
        results = self.get_check_results(account_id, limit=1)
        return results[0] if results else None
    
    def get_check_history(self, account_id: int, days: int = 30) -> List[CheckResult]:
        """
        Get check history for an account within a time period.
        
        Args:
            account_id: Database ID of the account
            days: Number of days to look back
            
        Returns:
            List of CheckResult objects
        """
        try:
            from datetime import timedelta
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            with self._get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM check_results 
                    WHERE account_id = ? AND checked_at >= ?
                    ORDER BY checked_at DESC
                    """,
                    (account_id, cutoff_date)
                )
                
                rows = cursor.fetchall()
                return [self._row_to_check_result(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get check history: {e}")
            raise DatabaseError(f"Failed to get check history: {e}") from e
    
    # Bulk operations
    
    def add_accounts_batch(self, accounts: List[Account]) -> Tuple[int, List[str]]:
        """
        Add multiple accounts in a batch.
        
        Args:
            accounts: List of accounts to add
            
        Returns:
            Tuple of (success_count, list of duplicate UIDs)
        """
        success_count = 0
        duplicates = []
        
        try:
            with self._get_cursor() as cursor:
                for account in accounts:
                    try:
                        cursor.execute(
                            """
                            INSERT INTO accounts (uid, password, name, source, region, 
                                               created_at, updated_at, last_checked, status, 
                                               check_count, notes, tags, custom_data)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                account.uid,
                                account.password,
                                account.name,
                                account.source.value,
                                account.region,
                                account.created_at.isoformat(),
                                account.updated_at.isoformat(),
                                account.last_checked.isoformat() if account.last_checked else None,
                                account.status.value,
                                account.check_count,
                                account.notes,
                                json.dumps(account.tags),
                                json.dumps(account.custom_data),
                            )
                        )
                        success_count += 1
                    except sqlite3.IntegrityError:
                        duplicates.append(account.uid)
                        
                return success_count, duplicates
                
        except Exception as e:
            logger.error(f"Failed to add batch: {e}")
            raise DatabaseError(f"Failed to add batch: {e}") from e
    
    def update_accounts_batch(self, updates: List[Tuple[str, Dict[str, Any]]]) -> int:
        """
        Update multiple accounts in a batch.
        
        Args:
            updates: List of (uid, update_dict) tuples
            
        Returns:
            Number of accounts updated
        """
        updated_count = 0
        
        try:
            with self._get_cursor() as cursor:
                for uid, update_data in updates:
                    # Build update query dynamically
                    set_clauses = []
                    params = []
                    
                    for key, value in update_data.items():
                        if key == "tags" or key == "custom_data":
                            set_clauses.append(f"{key} = ?")
                            params.append(json.dumps(value))
                        elif isinstance(value, datetime):
                            set_clauses.append(f"{key} = ?")
                            params.append(value.isoformat())
                        elif isinstance(value, AccountStatus):
                            set_clauses.append(f"{key} = ?")
                            params.append(value.value)
                        elif isinstance(value, AccountSource):
                            set_clauses.append(f"{key} = ?")
                            params.append(value.value)
                        else:
                            set_clauses.append(f"{key} = ?")
                            params.append(value)
                    
                    params.append(uid)
                    
                    if set_clauses:
                        query = f"UPDATE accounts SET {', '.join(set_clauses)} WHERE uid = ?"
                        cursor.execute(query, params)
                        updated_count += cursor.rowcount
                        
                return updated_count
                
        except Exception as e:
            logger.error(f"Failed to update batch: {e}")
            raise DatabaseError(f"Failed to update batch: {e}") from e
    
    # Import/Export operations
    
    def import_from_json(self, json_data: List[Dict[str, Any]], 
                        source: AccountSource = AccountSource.IMPORTED_JSON) -> Tuple[int, List[str]]:
        """
        Import accounts from JSON data.
        
        Args:
            json_data: List of account dictionaries
            source: Source to mark imported accounts with
            
        Returns:
            Tuple of (imported_count, list of duplicate UIDs)
        """
        accounts = []
        for data in json_data:
            account = Account.from_dict(data)
            account.source = source
            accounts.append(account)
        
        return self.add_accounts_batch(accounts)
    
    def export_to_json(self, filter: Optional[AccountFilter] = None) -> List[Dict[str, Any]]:
        """
        Export accounts to JSON format.
        
        Args:
            filter: Optional filter criteria
            
        Returns:
            List of account dictionaries
        """
        accounts, _ = self.query_accounts(filter or AccountFilter())
        return [account.to_dict_with_password() for account in accounts]
    
    def export_to_csv(self, filter: Optional[AccountFilter] = None) -> str:
        """
        Export accounts to CSV format.
        
        Args:
            filter: Optional filter criteria
            
        Returns:
            CSV string
        """
        accounts, _ = self.query_accounts(filter or AccountFilter())
        
        # Build CSV header
        header = [
            "uid", "name", "password", "region", "status", 
            "check_count", "last_checked", "created_at", "notes"
        ]
        
        # Build CSV rows
        rows = []
        for account in accounts:
            row = [
                account.uid,
                account.name,
                account.password,
                account.region,
                account.status.value,
                account.check_count,
                account.last_checked.isoformat() if account.last_checked else "",
                account.created_at.isoformat() if account.created_at else "",
                account.notes,
            ]
            rows.append(row)
        
        # Format CSV
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(header)
        writer.writerows(rows)
        
        return output.getvalue()
    
    def import_from_csv(self, csv_data: str, 
                       source: AccountSource = AccountSource.IMPORTED_CSV) -> Tuple[int, List[str]]:
        """
        Import accounts from CSV data.
        
        Args:
            csv_data: CSV string
            source: Source to mark imported accounts with
            
        Returns:
            Tuple of (imported_count, list of duplicate UIDs)
        """
        import csv
        from io import StringIO
        
        accounts = []
        reader = csv.DictReader(StringIO(csv_data))
        
        for row in reader:
            account = Account(
                uid=row.get("uid", ""),
                password=row.get("password", ""),
                name=row.get("name", ""),
                region=row.get("region", "GLOBAL"),
                source=source,
                status=AccountStatus(row.get("status", "UNKNOWN")),
                notes=row.get("notes", ""),
            )
            accounts.append(account)
        
        return self.add_accounts_batch(accounts)


# Global database instance
database = Database()
