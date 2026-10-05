#!/usr/bin/env python3
"""
Account Generation Script
Generates Free Fire guest account UIDs and passwords.
"""

import os
import sys
import json
import random
import string
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from config import config_manager
from src.database import Database, Account, AccountSource
from src.utils import get_logger, generate_uid, validate_uid

logger = get_logger(__name__)


def generate_guest_uid() -> str:
    """
    Generate a Free Fire guest UID.
    
    Returns:
        Random 10-12 digit UID
    """
    length = random.choice([10, 11, 12])
    return generate_uid(length)


def generate_password(length: int = 16) -> str:
    """
    Generate a random password for guest accounts.
    
    Args:
        length: Password length
        
    Returns:
        Random password string
    """
    chars = string.ascii_uppercase + string.digits + "-"
    return ''.join(random.choices(chars, k=length))


def generate_account(
    uid: Optional[str] = None,
    password: Optional[str] = None,
    name_prefix: str = "BOT",
    region: str = "GLOBAL",
) -> Account:
    """
    Generate a single guest account.
    
    Args:
        uid: Custom UID (generates random if None)
        password: Custom password (generates random if None)
        name_prefix: Prefix for account name
        region: Account region
        
    Returns:
        Generated Account object
    """
    if uid is None:
        uid = generate_guest_uid()
    
    if password is None:
        password = generate_password()
    
    # Generate name
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    name = f"{name_prefix}{random_suffix}"
    
    return Account(
        uid=uid,
        password=password,
        name=name,
        source=AccountSource.GENERATED,
        region=region,
    )


def generate_accounts(
    count: int = 10,
    name_prefix: str = "BOT",
    region: str = "GLOBAL",
    save_to_db: bool = False,
    save_to_json: bool = False,
    output_file: Optional[str] = None,
) -> List[Account]:
    """
    Generate multiple guest accounts.
    
    Args:
        count: Number of accounts to generate
        name_prefix: Prefix for account names
        region: Account region
        save_to_db: Whether to save to database
        save_to_json: Whether to save to JSON file
        output_file: Output file path (defaults to data/generated_accounts.json)
        
    Returns:
        List of generated Account objects
    """
    config = config_manager.get()
    
    accounts = []
    for i in range(count):
        account = generate_account(
            name_prefix=name_prefix,
            region=region,
        )
        accounts.append(account)
        logger.info(f"Generated account {i+1}/{count}: {account.uid}")
    
    # Save to database if requested
    if save_to_db and config.database.enabled:
        db = Database(config.database.path)
        for account in accounts:
            try:
                db.add_account(account)
                logger.info(f"Saved account {account.uid} to database")
            except Exception as e:
                logger.warning(f"Failed to save account {account.uid}: {e}")
    
    # Save to JSON if requested
    if save_to_json:
        if output_file is None:
            output_file = os.path.join(PROJECT_ROOT, "data", "generated_accounts.json")
        
        # Ensure directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Convert to JSON-safe format
        accounts_data = []
        for account in accounts:
            accounts_data.append(account.to_dict_with_password())
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(accounts_data, f, indent=2)
        
        logger.info(f"Saved {len(accounts)} accounts to {output_file}")
    
    return accounts


def generate_batch(
    batch_size: int = 100,
    region: str = "GLOBAL",
    name_prefix: str = "BOT",
) -> Dict[str, Any]:
    """
    Generate a batch of accounts with summary.
    
    Args:
        batch_size: Number of accounts to generate
        region: Account region
        name_prefix: Prefix for account names
        
    Returns:
        Dictionary with generated accounts and summary
    """
    start_time = datetime.now()
    
    accounts = generate_accounts(
        count=batch_size,
        name_prefix=name_prefix,
        region=region,
    )
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    return {
        "generated_at": datetime.now().isoformat(),
        "batch_size": batch_size,
        "time_seconds": elapsed,
        "accounts_per_second": batch_size / elapsed if elapsed > 0 else 0,
        "accounts": [acc.to_dict_with_password() for acc in accounts],
    }


def export_to_json(
    accounts: List[Account],
    output_file: Optional[str] = None,
    include_passwords: bool = True,
) -> str:
    """
    Export accounts to JSON file.
    
    Args:
        accounts: List of accounts to export
        output_file: Output file path
        include_passwords: Whether to include passwords in export
        
    Returns:
        Path to the exported file
    """
    if output_file is None:
        output_file = os.path.join(PROJECT_ROOT, "data", "exported_accounts.json")
    
    # Ensure directory exists
    output_dir = os.path.dirname(output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # Convert to JSON-safe format
    accounts_data = []
    for account in accounts:
        if include_passwords:
            accounts_data.append(account.to_dict_with_password())
        else:
            accounts_data.append(account.to_dict())
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(accounts_data, f, indent=2)
    
    logger.info(f"Exported {len(accounts)} accounts to {output_file}")
    return output_file


def generate_from_template(
    template: Dict[str, Any],
    count: int = 10,
) -> List[Account]:
    """
    Generate accounts from a template.
    
    Args:
        template: Template with default values
        count: Number of accounts to generate
        
    Returns:
        List of generated Account objects
    """
    accounts = []
    
    for i in range(count):
        uid = template.get("uid", generate_guest_uid())
        password = template.get("password", generate_password())
        name_prefix = template.get("name_prefix", "BOT")
        region = template.get("region", "GLOBAL")
        
        account = generate_account(
            uid=uid if isinstance(uid, str) else generate_guest_uid(),
            password=password if isinstance(password, str) else generate_password(),
            name_prefix=name_prefix,
            region=region,
        )
        accounts.append(account)
    
    return accounts


def generate_unique_accounts(
    count: int = 10,
    existing_uids: Optional[List[str]] = None,
) -> List[Account]:
    """
    Generate accounts with unique UIDs.
    
    Args:
        count: Number of accounts to generate
        existing_uids: List of existing UIDs to avoid
        
    Returns:
        List of Account objects with unique UIDs
    """
    if existing_uids is None:
        existing_uids = []
    
    accounts = []
    generated_uids = set(existing_uids)
    
    for _ in range(count):
        while True:
            account = generate_account()
            if account.uid not in generated_uids:
                generated_uids.add(account.uid)
                accounts.append(account)
                break
    
    return accounts


if __name__ == "__main__":
    # Command line interface
    import argparse
    
    parser = argparse.ArgumentParser(description="Account Generation Tool")
    parser.add_argument("count", type=int, nargs="?", default=10, help="Number of accounts to generate")
    parser.add_argument("--name-prefix", default="BOT", help="Prefix for account names")
    parser.add_argument("--region", default="GLOBAL", help="Account region")
    parser.add_argument("--save-db", action="store_true", help="Save to database")
    parser.add_argument("--save-json", action="store_true", help="Save to JSON file")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--no-passwords", action="store_true", help="Don't include passwords in JSON")
    parser.add_argument("--batch", type=int, help="Generate in batch mode")
    parser.add_argument("--template", help="Path to template JSON file")
    
    args = parser.parse_args()
    
    try:
        if args.template:
            # Load template
            with open(args.template, 'r') as f:
                template = json.load(f)
            
            accounts = generate_from_template(template, args.count)
        else:
            accounts = generate_accounts(
                count=args.count,
                name_prefix=args.name_prefix,
                region=args.region,
                save_to_db=args.save_db,
                save_to_json=args.save_json,
                output_file=args.output,
            )
        
        if args.save_json and not args.template:
            # Already saved above
            pass
        elif args.output:
            export_to_json(
                accounts,
                output_file=args.output,
                include_passwords=not args.no_passwords,
            )
        else:
            # Print generated accounts
            print(f"Generated {len(accounts)} accounts:")
            for account in accounts:
                print(f"  UID: {account.uid}, Password: {account.password}, Name: {account.name}")
        
        if args.batch:
            # Generate in batch mode
            batch = generate_batch(
                batch_size=args.batch,
                region=args.region,
                name_prefix=args.name_prefix,
            )
            print(f"\nBatch Summary:")
            print(f"  Generated: {batch['batch_size']} accounts")
            print(f"  Time: {batch['time_seconds']:.2f} seconds")
            print(f"  Speed: {batch['accounts_per_second']:.2f} accounts/second")
            
    except Exception as e:
        print(f"Error: {e}")
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)
