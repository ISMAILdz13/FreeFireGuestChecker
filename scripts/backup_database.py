#!/usr/bin/env python3
"""
Database Backup Script
Handles database backup and restore operations.
"""

import os
import sys
import json
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from config import config_manager
from src.database import Database
from src.utils import get_logger

logger = get_logger(__name__)


def get_backup_dir() -> str:
    """Get the backup directory path."""
    config = config_manager.get()
    backup_path = config.database.backup_path
    return os.path.dirname(backup_path)


def get_backup_files() -> List[str]:
    """Get list of backup files."""
    backup_dir = get_backup_dir()
    if not os.path.exists(backup_dir):
        return []
    
    backup_pattern = os.path.basename(config_manager.get().database.backup_path).replace("{timestamp}", "*")
    backup_files = list(Path(backup_dir).glob(backup_pattern))
    return sorted(backup_files, key=lambda f: f.stat().st_mtime, reverse=True)


def backup_database(
    db_path: Optional[str] = None,
    backup_dir: Optional[str] = None,
    backup_name: Optional[str] = None,
    max_backups: Optional[int] = None,
) -> str:
    """
    Create a backup of the database.
    
    Args:
        db_path: Path to database file (defaults to config)
        backup_dir: Backup directory (defaults to config)
        backup_name: Custom backup filename (without extension)
        max_backups: Maximum number of backups to keep (defaults to config)
        
    Returns:
        Path to the created backup file
    """
    config = config_manager.get()
    
    # Use provided values or defaults
    if db_path is None:
        db_path = config.database.path
    if backup_dir is None:
        backup_dir = get_backup_dir()
    if max_backups is None:
        max_backups = config.database.max_backups
    
    # Ensure database exists
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found: {db_path}")
    
    # Ensure backup directory exists
    Path(backup_dir).mkdir(parents=True, exist_ok=True)
    
    # Generate backup filename
    if backup_name is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"guests_backup_{timestamp}"
    
    backup_path = os.path.join(backup_dir, f"{backup_name}.db")
    
    # Copy the database file
    shutil.copy2(db_path, backup_path)
    
    # Clean up old backups
    cleanup_old_backups(backup_dir, max_backups, backup_pattern=backup_name.replace(timestamp, "*"))
    
    logger.info(f"Database backup created: {backup_path}")
    return backup_path


def cleanup_old_backups(
    backup_dir: str,
    max_backups: int,
    backup_pattern: str = "guests_backup_*.db",
) -> int:
    """
    Remove old backup files.
    
    Args:
        backup_dir: Backup directory
        max_backups: Maximum number of backups to keep
        backup_pattern: Pattern to match backup files
        
    Returns:
        Number of backups removed
    """
    removed_count = 0
    
    try:
        backup_files = list(Path(backup_dir).glob(backup_pattern))
        
        # Sort by modification time (oldest first)
        backup_files.sort(key=lambda f: f.stat().st_mtime)
        
        # Remove excess backups
        while len(backup_files) > max_backups:
            old_backup = backup_files.pop(0)
            try:
                old_backup.unlink()
                logger.info(f"Removed old backup: {old_backup}")
                removed_count += 1
            except Exception as e:
                logger.warning(f"Failed to remove backup {old_backup}: {e}")
                
    except Exception as e:
        logger.error(f"Failed to cleanup old backups: {e}")
    
    return removed_count


def restore_database(
    backup_path: str,
    db_path: Optional[str] = None,
    verify: bool = True,
) -> str:
    """
    Restore database from backup.
    
    Args:
        backup_path: Path to backup file
        db_path: Target database path (defaults to config)
        verify: Whether to verify backup file exists
        
    Returns:
        Path to the restored database
    """
    config = config_manager.get()
    
    if db_path is None:
        db_path = config.database.path
    
    # Verify backup file
    if verify and not os.path.exists(backup_path):
        raise FileNotFoundError(f"Backup file not found: {backup_path}")
    
    # Ensure target directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir:
        Path(db_dir).mkdir(parents=True, exist_ok=True)
    
    # Close existing database connection if any
    try:
        db = Database(db_path)
        db.close()
    except Exception:
        pass
    
    # Copy backup to database
    shutil.copy2(backup_path, db_path)
    
    logger.info(f"Database restored from: {backup_path}")
    return db_path


def list_backups() -> List[dict]:
    """
    List all available backups.
    
    Returns:
        List of backup info dictionaries
    """
    backup_files = get_backup_files()
    backups = []
    
    for backup_file in backup_files:
        stat = backup_file.stat()
        backups.append({
            "path": str(backup_file),
            "filename": backup_file.name,
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    
    return backups


def get_backup_info(backup_path: str) -> dict:
    """
    Get information about a backup file.
    
    Args:
        backup_path: Path to backup file
        
    Returns:
        Dictionary with backup information
    """
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Backup file not found: {backup_path}")
    
    stat = Path(backup_path).stat()
    
    return {
        "path": backup_path,
        "filename": os.path.basename(backup_path),
        "size": stat.st_size,
        "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }


def verify_backup(backup_path: str) -> bool:
    """
    Verify a backup file is valid.
    
    Args:
        backup_path: Path to backup file
        
    Returns:
        True if backup is valid, False otherwise
    """
    try:
        # Check file exists
        if not os.path.exists(backup_path):
            return False
        
        # Check file size
        size = Path(backup_path).stat().st_size
        if size == 0:
            return False
        
        # Try to open as SQLite
        import sqlite3
        conn = sqlite3.connect(backup_path)
        cursor = conn.cursor()
        
        # Check for required tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        if "accounts" not in tables:
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to verify backup: {e}")
        return False


def create_backup_archive(
    db_path: Optional[str] = None,
    backup_dir: Optional[str] = None,
    include_logs: bool = True,
    include_config: bool = True,
) -> str:
    """
    Create a compressed archive of database and related files.
    
    Args:
        db_path: Path to database file
        backup_dir: Backup directory
        include_logs: Whether to include log files
        include_config: Whether to include config files
        
    Returns:
        Path to the created archive
    """
    import zipfile
    
    config = config_manager.get()
    
    if db_path is None:
        db_path = config.database.path
    if backup_dir is None:
        backup_dir = get_backup_dir()
    
    # Ensure backup directory exists
    Path(backup_dir).mkdir(parents=True, exist_ok=True)
    
    # Generate archive filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = os.path.join(backup_dir, f"backup_{timestamp}.zip")
    
    # Create archive
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add database
        if os.path.exists(db_path):
            zipf.write(db_path, os.path.basename(db_path))
        
        # Add logs if requested
        if include_logs and os.path.exists(config.logging.log_file):
            zipf.write(config.logging.log_file, "logs/app.log")
        
        # Add config if requested
        if include_config and os.path.exists(config.config_file):
            zipf.write(config.config_file, "config/settings.json")
    
    logger.info(f"Backup archive created: {archive_path}")
    return archive_path


def extract_backup_archive(
    archive_path: str,
    extract_dir: Optional[str] = None,
) -> str:
    """
    Extract a backup archive.
    
    Args:
        archive_path: Path to archive file
        extract_dir: Directory to extract to (defaults to current directory)
        
    Returns:
        Path to the extracted directory
    """
    import zipfile
    
    if extract_dir is None:
        extract_dir = os.path.dirname(archive_path)
    
    # Ensure extract directory exists
    Path(extract_dir).mkdir(parents=True, exist_ok=True)
    
    # Extract archive
    with zipfile.ZipFile(archive_path, 'r') as zipf:
        zipf.extractall(extract_dir)
    
    logger.info(f"Backup archive extracted to: {extract_dir}")
    return extract_dir


if __name__ == "__main__":
    # Command line interface
    import argparse
    
    parser = argparse.ArgumentParser(description="Database Backup Tool")
    parser.add_argument("command", choices=["backup", "restore", "list", "verify", "cleanup"])
    parser.add_argument("--db", help="Database path")
    parser.add_argument("--backup-dir", help="Backup directory")
    parser.add_argument("--backup-name", help="Custom backup name")
    parser.add_argument("--max-backups", type=int, help="Maximum backups to keep")
    parser.add_argument("--backup-path", help="Path to backup file (for restore/verify)")
    parser.add_argument("--verify", action="store_true", help="Verify backup before restore")
    parser.add_argument("--force", action="store_true", help="Force overwrite")
    
    args = parser.parse_args()
    
    try:
        if args.command == "backup":
            backup_path = backup_database(
                db_path=args.db,
                backup_dir=args.backup_dir,
                backup_name=args.backup_name,
                max_backups=args.max_backups,
            )
            print(f"Backup created: {backup_path}")
            
        elif args.command == "restore":
            if not args.backup_path:
                parser.error("--backup-path is required for restore")
            
            restore_database(
                backup_path=args.backup_path,
                db_path=args.db,
                verify=args.verify,
            )
            print(f"Database restored from: {args.backup_path}")
            
        elif args.command == "list":
            backups = list_backups()
            if not backups:
                print("No backups found")
            else:
                print(f"Found {len(backups)} backups:")
                for backup in backups:
                    size_mb = backup["size"] / (1024 * 1024)
                    print(f"  {backup['filename']} - {size_mb:.2f} MB - {backup['created']}")
            
        elif args.command == "verify":
            if not args.backup_path:
                parser.error("--backup-path is required for verify")
            
            if verify_backup(args.backup_path):
                print(f"Backup is valid: {args.backup_path}")
            else:
                print(f"Backup is invalid or corrupted: {args.backup_path}")
                sys.exit(1)
                
        elif args.command == "cleanup":
            backup_dir = args.backup_dir or get_backup_dir()
            removed = cleanup_old_backups(
                backup_dir=backup_dir,
                max_backups=args.max_backups or config_manager.get().database.max_backups,
            )
            print(f"Removed {removed} old backups")
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
