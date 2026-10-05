"""
Database Module
Handles SQLite database operations for account storage and management.
"""

from .models import (
    Account,
    AccountStatus,
    AccountSource,
    CheckResult,
)
from .database import (
    Database,
    DatabaseError,
    AccountAlreadyExists,
    AccountNotFound,
)
from .migrations import (
    MigrationManager,
    run_migrations,
)

__all__ = [
    # Models
    'Account',
    'AccountStatus',
    'AccountSource',
    'CheckResult',
    # Database
    'Database',
    'DatabaseError',
    'AccountAlreadyExists',
    'AccountNotFound',
    # Migrations
    'MigrationManager',
    'run_migrations',
]
