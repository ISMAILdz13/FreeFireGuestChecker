"""
Database Migrations Module
Handles database schema migrations and version management.
"""

import os
import json
import logging
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """Exception for migration errors."""
    pass


@dataclass
class Migration:
    """Represents a database migration."""
    version: str
    description: str
    sql: str
    rollback_sql: str = ""
    
    def __post_init__(self):
        if not self.version:
            raise ValueError("Migration version is required")
        if not self.sql:
            raise ValueError("Migration SQL is required")


class MigrationManager:
    """
    Manages database migrations.
    
    Tracks which migrations have been applied and applies new ones.
    """
    
    MIGRATIONS_TABLE = """
        CREATE TABLE IF NOT EXISTS _migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL,
            description TEXT
        )
    """
    
    def __init__(self, db_path: str, migrations_dir: str = "migrations"):
        self.db_path = db_path
        self.migrations_dir = migrations_dir
        self._migrations: List[Migration] = []
        self._applied_versions: List[str] = []
        
    def _ensure_migrations_table(self, conn: sqlite3.Connection) -> None:
        """Ensure migrations table exists."""
        conn.execute(self.MIGRATIONS_TABLE)
        conn.commit()
    
    def _get_applied_migrations(self, conn: sqlite3.Connection) -> List[str]:
        """Get list of applied migration versions."""
        cursor = conn.cursor()
        cursor.execute("SELECT version FROM _migrations ORDER BY version")
        return [row[0] for row in cursor.fetchall()]
    
    def _mark_migration_applied(self, conn: sqlite3.Connection, version: str, 
                                description: str) -> None:
        """Mark a migration as applied."""
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO _migrations (version, applied_at, description) VALUES (?, ?, ?)",
            (version, datetime.now().isoformat(), description)
        )
        conn.commit()
    
    def _mark_migration_rolled_back(self, conn: sqlite3.Connection, version: str) -> None:
        """Remove a migration from the applied list."""
        cursor = conn.cursor()
        cursor.execute("DELETE FROM _migrations WHERE version = ?", (version,))
        conn.commit()
    
    def load_migrations(self) -> List[Migration]:
        """Load migrations from the migrations directory."""
        migrations = []
        
        # Check if migrations directory exists
        if not os.path.exists(self.migrations_dir):
            logger.debug(f"Migrations directory not found: {self.migrations_dir}")
            return migrations
        
        # Load migrations from files
        for filename in sorted(os.listdir(self.migrations_dir)):
            if filename.endswith('.sql'):
                filepath = os.path.join(self.migrations_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        content = f.read()
                    
                    # Parse migration file
                    # Format: -- version: x.x.x
                    #         -- description: Migration description
                    #         -- up
                    #         SQL statements...
                    #         -- down
                    #         Rollback SQL...
                    
                    version = None
                    description = ""
                    up_sql = ""
                    down_sql = ""
                    
                    lines = content.split('\n')
                    current_section = None
                    
                    for line in lines:
                        line = line.strip()
                        
                        if line.startswith('-- version:'):
                            version = line.split(':', 1)[1].strip()
                        elif line.startswith('-- description:'):
                            description = line.split(':', 1)[1].strip()
                        elif line.startswith('-- up'):
                            current_section = 'up'
                        elif line.startswith('-- down'):
                            current_section = 'down'
                        elif line and not line.startswith('--'):
                            if current_section == 'up':
                                up_sql += line + '\n'
                            elif current_section == 'down':
                                down_sql += line + '\n'
                    
                    if version and up_sql:
                        migrations.append(Migration(
                            version=version,
                            description=description,
                            sql=up_sql.strip(),
                            rollback_sql=down_sql.strip(),
                        ))
                        
                except Exception as e:
                    logger.error(f"Failed to load migration {filename}: {e}")
        
        # Sort migrations by version
        migrations.sort(key=lambda m: m.version)
        self._migrations = migrations
        
        return migrations
    
    def get_pending_migrations(self) -> List[Migration]:
        """Get list of migrations that haven't been applied yet."""
        if not self._migrations:
            self.load_migrations()
        
        if not self._applied_versions:
            conn = sqlite3.connect(self.db_path)
            try:
                self._ensure_migrations_table(conn)
                self._applied_versions = self._get_applied_migrations(conn)
            finally:
                conn.close()
        
        return [m for m in self._migrations if m.version not in self._applied_versions]
    
    def apply_migration(self, migration: Migration) -> bool:
        """Apply a single migration."""
        conn = sqlite3.connect(self.db_path)
        try:
            self._ensure_migrations_table(conn)
            
            # Execute migration SQL
            cursor = conn.cursor()
            for statement in migration.sql.split(';'):
                statement = statement.strip()
                if statement:
                    cursor.execute(statement)
            
            conn.commit()
            
            # Mark as applied
            self._mark_migration_applied(conn, migration.version, migration.description)
            self._applied_versions.append(migration.version)
            
            logger.info(f"Applied migration {migration.version}: {migration.description}")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to apply migration {migration.version}: {e}")
            raise MigrationError(f"Migration {migration.version} failed: {e}") from e
        finally:
            conn.close()
    
    def rollback_migration(self, version: str) -> bool:
        """Rollback a migration."""
        # Find the migration
        migration = None
        for m in self._migrations:
            if m.version == version:
                migration = m
                break
        
        if not migration:
            logger.error(f"Migration {version} not found")
            return False
        
        if not migration.rollback_sql:
            logger.error(f"Migration {version} has no rollback SQL")
            return False
        
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            
            # Execute rollback SQL
            for statement in migration.rollback_sql.split(';'):
                statement = statement.strip()
                if statement:
                    cursor.execute(statement)
            
            conn.commit()
            
            # Mark as rolled back
            self._mark_migration_rolled_back(conn, version)
            self._applied_versions.remove(version)
            
            logger.info(f"Rolled back migration {version}: {migration.description}")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to rollback migration {version}: {e}")
            raise MigrationError(f"Rollback {version} failed: {e}") from e
        finally:
            conn.close()
    
    def apply_all_migrations(self) -> List[str]:
        """
        Apply all pending migrations.
        
        Returns:
            List of applied migration versions
        """
        applied = []
        pending = self.get_pending_migrations()
        
        for migration in pending:
            try:
                self.apply_migration(migration)
                applied.append(migration.version)
            except MigrationError:
                logger.error(f"Stopping migration process due to error")
                break
        
        return applied
    
    def get_current_version(self) -> str:
        """Get the current database schema version."""
        if not self._applied_versions:
            conn = sqlite3.connect(self.db_path)
            try:
                self._ensure_migrations_table(conn)
                self._applied_versions = self._get_applied_migrations(conn)
            finally:
                conn.close()
        
        if self._applied_versions:
            return self._applied_versions[-1]
        return "0.0.0"
    
    def get_migration_history(self) -> List[Dict[str, Any]]:
        """Get the migration history."""
        conn = sqlite3.connect(self.db_path)
        try:
            self._ensure_migrations_table(conn)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT version, applied_at, description FROM _migrations ORDER BY version"
            )
            return [
                {"version": row[0], "applied_at": row[1], "description": row[2]}
                for row in cursor.fetchall()
            ]
        except Exception as e:
            logger.error(f"Failed to get migration history: {e}")
            return []
        finally:
            conn.close()


def run_migrations(db_path: str, migrations_dir: str = "migrations") -> List[str]:
    """
    Run all pending migrations for a database.
    
    Args:
        db_path: Path to the database file
        migrations_dir: Directory containing migration files
        
    Returns:
        List of applied migration versions
    """
    manager = MigrationManager(db_path, migrations_dir)
    return manager.apply_all_migrations()


def create_migration_file(version: str, description: str, filename: Optional[str] = None) -> str:
    """
    Create a new migration file template.
    
    Args:
        version: Migration version (e.g., "1.0.0")
        description: Migration description
        filename: Optional filename (defaults to version.sql)
        
    Returns:
        Path to the created migration file
    """
    if not filename:
        filename = f"{version}.sql"
    
    if not os.path.exists("migrations"):
        os.makedirs("migrations")
    
    filepath = os.path.join("migrations", filename)
    
    template = f"""-- version: {version}
-- description: {description}
-- up

-- Add your SQL statements here
-- Example: CREATE TABLE new_table (id INTEGER PRIMARY KEY, name TEXT);

-- down

-- Add rollback SQL here
-- Example: DROP TABLE new_table;
"""
    
    with open(filepath, 'w') as f:
        f.write(template)
    
    logger.info(f"Created migration file: {filepath}")
    return filepath


# Built-in migrations for the database
BUILT_IN_MIGRATIONS = [
    Migration(
        version="1.0.0",
        description="Initial schema",
        sql="""
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
            );
            
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
            );
            
            CREATE INDEX IF NOT EXISTS idx_accounts_uid ON accounts(uid);
            CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts(status);
            CREATE INDEX IF NOT EXISTS idx_accounts_region ON accounts(region);
            CREATE INDEX IF NOT EXISTS idx_accounts_source ON accounts(source);
            CREATE INDEX IF NOT EXISTS idx_accounts_last_checked ON accounts(last_checked);
            CREATE INDEX IF NOT EXISTS idx_results_account_id ON check_results(account_id);
            CREATE INDEX IF NOT EXISTS idx_results_checked_at ON check_results(checked_at);
        """,
        rollback_sql="""
            DROP TABLE IF EXISTS check_results;
            DROP TABLE IF EXISTS accounts;
        """,
    ),
]


# Global migration manager
def get_migration_manager(db_path: str) -> MigrationManager:
    """Get a migration manager for the specified database."""
    return MigrationManager(db_path)
