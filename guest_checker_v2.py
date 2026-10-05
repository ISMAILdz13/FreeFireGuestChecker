#!/usr/bin/env python3
"""
Free Fire Guest Account Checker v2.0
Enhanced version with:
- Configuration management
- Proxy support
- Rate limiting
- Database storage
- Multiple input formats
- Better error handling
- Web interface support
- Comprehensive logging

Usage:
    python guest_checker_v2.py              # Check all accounts with defaults
    python guest_checker_v2.py --json data/guests.json  # Check from JSON file
    python guest_checker_v2.py --db data/guests.db  # Check from database
    python guest_checker_v2.py --concurrent 10  # Use 10 concurrent workers
    python guest_checker_v2.py --proxy http://proxy:8080  # Use proxy
    python guest_checker_v2.py --web  # Start web interface
"""

import os
import sys
import json
import asyncio
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# Import configuration
from config import config_manager, secrets_manager, runtime_config
from config.settings import Settings, LogLevel, ProxyType, Region
from config.runtime import ProgressState, RateLimitState

# Import utilities
from src.utils import (
    setup_logging,
    get_logger,
    ColorFormatter,
    format_bytes,
    format_seconds,
    format_timestamp,
    retry_async,
    chunk_list,
    validate_uid,
    validate_password,
)

# Import database
from src.database import (
    Database,
    Account,
    AccountStatus,
    AccountSource,
    AccountFilter,
    CheckResult,
)

# Import auth and info modules
from src.level.auth import LevelAuth
from src.level.guest_info import GuestInfo

# Import network utilities
from src.utils.network import (
    create_http_client,
    get_proxy_url,
    check_connectivity,
    ProxyRotator,
)

# Import validators
from src.utils.validators import (
    validate_account_data,
    validate_concurrency,
    validate_proxy_config,
)

# Set up logging
logger = get_logger(__name__)


@dataclass
class AccountData:
    """Holds account data for processing."""
    uid: str
    password: str
    name: str = ""
    source: str = ""
    index: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "uid": self.uid,
            "password": self.password,
            "name": self.name,
            "source": self.source,
            "index": self.index,
        }


@dataclass
class CheckOptions:
    """Options for account checking."""
    concurrent: int = 5
    timeout: float = 30.0
    retries: int = 3
    use_proxy: bool = False
    proxy_url: Optional[str] = None
    validate_passwords: bool = True
    save_results: bool = True
    auto_save_interval: int = 10
    continue_on_error: bool = True


@dataclass
class CheckResult:
    """Result of checking a single account."""
    uid: str
    name: str
    status: AccountStatus = AccountStatus.UNKNOWN
    oauth_status: str = "UNKNOWN"
    ban_reason: str = ""
    nickname: str = ""
    level: int = 0
    exp: int = 0
    likes: int = 0
    rank: int = 0
    region: str = "Unknown"
    clan_name: str = ""
    clan_level: int = 0
    release_version: str = ""
    credit_score: int = 0
    last_login: str = ""
    account_created: str = ""
    checked_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None
    duration: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "uid": self.uid,
            "name": self.name,
            "status": self.status.value,
            "oauth_status": self.oauth_status,
            "ban_reason": self.ban_reason,
            "nickname": self.nickname,
            "level": self.level,
            "exp": self.exp,
            "likes": self.likes,
            "rank": self.rank,
            "region": self.region,
            "clan_name": self.clan_name,
            "clan_level": self.clan_level,
            "release_version": self.release_version,
            "credit_score": self.credit_score,
            "last_login": self.last_login,
            "account_created": self.account_created,
            "checked_at": self.checked_at.isoformat(),
            "error": self.error,
            "duration": self.duration,
        }


class AccountLoader:
    """Loads accounts from various sources."""
    
    def __init__(self, config: Settings):
        self.config = config
        self._sources: Dict[str, List[AccountData]] = {}
        
    def load_all(self) -> List[AccountData]:
        """Load accounts from all configured sources."""
        accounts = []
        
        # Load from JSON files
        accounts.extend(self._load_from_json_files())
        
        # Load from database
        accounts.extend(self._load_from_database())
        
        # Load from CSV files
        accounts.extend(self._load_from_csv_files())
        
        # Deduplicate by UID
        unique_accounts = {}
        for account in accounts:
            if account.uid not in unique_accounts:
                unique_accounts[account.uid] = account
        
        return list(unique_accounts.values())
    
    def _load_from_json_files(self) -> List[AccountData]:
        """Load accounts from JSON files."""
        accounts = []
        
        # Check default locations
        json_files = [
            os.path.join(PROJECT_ROOT, "data", "guests.json"),
            os.path.join(PROJECT_ROOT, "data", "level_accounts.json"),
            os.path.join(PROJECT_ROOT, "data", "level_accounts.example.json"),
        ]
        
        # Add custom JSON file if specified
        if hasattr(self.config.checker, 'input_file'):
            json_files.append(self.config.checker.input_file)
        
        for json_file in json_files:
            if os.path.exists(json_file):
                try:
                    accounts.extend(self._load_json_file(json_file))
                    logger.info(f"Loaded {len(accounts)} accounts from {json_file}")
                except Exception as e:
                    logger.error(f"Failed to load {json_file}: {e}")
        
        return accounts
    
    def _load_json_file(self, json_file: str) -> List[AccountData]:
        """Load accounts from a single JSON file."""
        accounts = []
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle different JSON formats
        if isinstance(data, list):
            # List of account objects
            for item in data:
                account = self._parse_account_item(item, f"{json_file} (list)")
                if account:
                    accounts.append(account)
        elif isinstance(data, dict):
            # Dictionary with UID as key or list of accounts
            if all(isinstance(k, str) and k.isdigit() for k in data.keys()):
                # Format: {"uid": {"password": "...", "name": "..."}}
                for uid, values in data.items():
                    account = AccountData(
                        uid=uid,
                        password=values.get("password", ""),
                        name=values.get("name", values.get("nickname", "")),
                        source=json_file,
                    )
                    if account.uid and account.password:
                        accounts.append(account)
            else:
                # Format: {"accounts": [...]}
                for item in data.get("accounts", []):
                    account = self._parse_account_item(item, json_file)
                    if account:
                        accounts.append(account)
        
        return accounts
    
    def _parse_account_item(self, item: Dict[str, Any], source: str) -> Optional[AccountData]:
        """Parse a single account item from JSON."""
        uid = item.get("uid", item.get("id", ""))
        password = item.get("password", "")
        name = item.get("name", item.get("nickname", ""))
        
        if not uid or not password:
            return None
        
        return AccountData(
            uid=str(uid),
            password=str(password),
            name=str(name),
            source=source,
        )
    
    def _load_from_database(self) -> List[AccountData]:
        """Load accounts from database."""
        accounts = []
        
        if not self.config.database.enabled:
            return accounts
        
        try:
            db = Database(self.config.database.path)
            db_accounts = db.get_all_accounts()
            
            for db_account in db_accounts:
                account = AccountData(
                    uid=db_account.uid,
                    password=db_account.password,
                    name=db_account.name,
                    source=f"database ({db_account.source.value})",
                )
                accounts.append(account)
            
            logger.info(f"Loaded {len(accounts)} accounts from database")
            
        except Exception as e:
            logger.error(f"Failed to load from database: {e}")
        
        return accounts
    
    def _load_from_csv_files(self) -> List[AccountData]:
        """Load accounts from CSV files."""
        accounts = []
        
        # Check default locations
        csv_files = [
            os.path.join(PROJECT_ROOT, "data", "accounts.csv"),
            os.path.join(PROJECT_ROOT, "data", "guests.csv"),
        ]
        
        for csv_file in csv_files:
            if os.path.exists(csv_file):
                try:
                    accounts.extend(self._load_csv_file(csv_file))
                    logger.info(f"Loaded {len(accounts)} accounts from {csv_file}")
                except Exception as e:
                    logger.error(f"Failed to load {csv_file}: {e}")
        
        return accounts
    
    def _load_csv_file(self, csv_file: str) -> List[AccountData]:
        """Load accounts from a single CSV file."""
        import csv
        accounts = []
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                account = AccountData(
                    uid=row.get("uid", row.get("id", "")),
                    password=row.get("password", ""),
                    name=row.get("name", row.get("nickname", "")),
                    source=csv_file,
                )
                if account.uid and account.password:
                    accounts.append(account)
        
        return accounts


class AccountChecker:
    """Checks Free Fire guest accounts."""
    
    def __init__(self, config: Settings, options: CheckOptions):
        self.config = config
        self.options = options
        self._http_client = None
        self._proxy_rotator = None
        
    async def __aenter__(self):
        """Initialize HTTP client."""
        await self._initialize_http()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up HTTP client."""
        await self._cleanup_http()
    
    async def _initialize_http(self) -> None:
        """Initialize HTTP client with proxy support."""
        proxy_url = None
        
        if self.options.use_proxy:
            proxy_url = self.options.proxy_url
        elif self.config.proxy.enabled:
            proxy_url = get_proxy_url()
        
        self._http_client = create_http_client(
            proxy_url=proxy_url,
            timeout=self.options.timeout,
            verify_ssl=False,
            follow_redirects=True,
        )
        
        # Initialize proxy rotator if configured
        if self.config.proxy.rotate_on_failure and self.config.proxy.rotation_list:
            self._proxy_rotator = ProxyRotator(self.config.proxy.rotation_list)
    
    async def _cleanup_http(self) -> None:
        """Clean up HTTP client."""
        if self._http_client:
            try:
                await self._http_client.aclose()
            except Exception as e:
                logger.warning(f"Error closing HTTP client: {e}")
            self._http_client = None
    
    async def check_account(self, account: AccountData) -> CheckResult:
        """Check a single account."""
        start_time = datetime.now()
        
        result = CheckResult(
            uid=account.uid,
            name=account.name,
        )
        
        try:
            # Create fresh HTTP client for each account if using proxy rotation
            if self._proxy_rotator:
                http = create_http_client(
                    proxy_url=await self._proxy_rotator.get_next_proxy(),
                    timeout=self.options.timeout,
                    verify_ssl=False,
                )
            else:
                http = self._http_client
            
            # Step 1: OAuth authentication
            auth = LevelAuth(http)
            oauth_result = await auth.guest_token(
                account.uid,
                account.password,
                retries=self.options.retries,
            )
            
            if not oauth_result:
                result.status = AccountStatus.DEAD
                result.oauth_status = "FAILED"
                result.ban_reason = "OAuth failed - account deleted or password invalid"
                result.checked_at = datetime.now()
                result.duration = (datetime.now() - start_time).total_seconds()
                return result
            
            access_token, open_id = oauth_result
            result.oauth_status = "ALIVE"
            
            # Step 2: MajorLogin
            login_result = await auth.major_login(
                access_token,
                open_id,
                retries=self.options.retries,
            )
            
            if login_result and not login_result.get("error"):
                result.status = AccountStatus.ALIVE
                jwt_token = login_result["token"]
                
                # Step 3: Get player info
                try:
                    info = GuestInfo(http)
                    player_data = await info._get_player_personal_show(
                        account.uid,
                        jwt_token,
                    )
                    
                    if player_data:
                        # Parse player data
                        self._parse_player_data(result, player_data)
                        
                except Exception as e:
                    logger.debug(f"Failed to get player info for {account.uid}: {e}")
                    result.error = str(e)
                    
            else:
                # Handle MajorLogin failure
                last_status = login_result.get("last_status", 0) if isinstance(login_result, dict) else 0
                
                if last_status == 503:
                    result.status = AccountStatus.SERVER_DOWN
                    result.ban_reason = "Garena servers down (503) - not a ban"
                elif last_status in (400, 401, 403):
                    result.status = AccountStatus.BANNED
                    result.ban_reason = f"Account banned (HTTP {last_status})"
                else:
                    result.status = AccountStatus.UNKNOWN
                    result.ban_reason = f"MajorLogin failed (HTTP {last_status})"
            
            # Clean up HTTP client if we created one
            if http != self._http_client:
                try:
                    await http.aclose()
                except Exception:
                    pass
                    
        except Exception as e:
            result.status = AccountStatus.ERROR
            result.error = str(e)
            logger.error(f"Error checking account {account.uid}: {e}")
        
        result.checked_at = datetime.now()
        result.duration = (datetime.now() - start_time).total_seconds()
        return result
    
    def _parse_player_data(self, result: CheckResult, player_data: bytes) -> None:
        """Parse player data from protobuf."""
        try:
            from src.level.data_pb2 import AccountPersonalShowInfo
            
            info = AccountPersonalShowInfo()
            info.ParseFromString(player_data)
            
            # Basic info
            basic = info.basic_info
            if basic:
                result.nickname = basic.nickname or result.name or ""
                result.level = basic.level or 0
                result.exp = basic.exp or 0
                result.likes = basic.liked or 0
                result.rank = basic.rank or 0
                result.region = basic.region or result.region
                
                if basic.last_login_at:
                    result.last_login = datetime.fromtimestamp(
                        basic.last_login_at / 1000
                    ).strftime("%Y-%m-%d %H:%M")
                
                if basic.create_at:
                    result.account_created = datetime.fromtimestamp(
                        basic.create_at / 1000
                    ).strftime("%Y-%m-%d")
            
            # Clan info
            clan = info.clan_basic_info
            if clan and clan.clan_id:
                result.clan_name = clan.clan_name or ""
                result.clan_level = clan.clan_level or 0
            
            # Credit score
            credit = info.credit_score_info
            if credit and credit.HasField("score"):
                result.credit_score = credit.score
                if credit.status >= 100:
                    result.status = AccountStatus.BLACKLISTED
                    result.ban_reason = f"Credit score penalty (status={credit.status})"
            
            # Release version
            result.release_version = basic.release_version or ""
            
        except Exception as e:
            logger.debug(f"Failed to parse player data: {e}")
            # Fallback to raw parsing
            self._parse_player_data_raw(result, player_data)
    
    def _parse_player_data_raw(self, result: CheckResult, player_data: bytes) -> None:
        """Parse player data using raw protobuf decoder."""
        try:
            from protobuf_decoder.protobuf_decoder import Parser
            
            hex_data = player_data.hex()
            parsed = Parser().parse(hex_data)
            
            for r in parsed:
                field_num = int(r.field)
                
                if r.wire_type == "length_delimited":
                    for sub in r.data.results:
                        sub_num = int(sub.field)
                        
                        # Field 1 = basic_info
                        if field_num == 1:
                            if sub_num == 3 and sub.wire_type in ("string", "bytes"):
                                result.nickname = sub.data
                            elif sub_num == 6 and sub.wire_type == "varint":
                                result.level = int(sub.data)
                            elif sub_num == 7 and sub.wire_type == "varint":
                                result.exp = int(sub.data)
                            elif sub_num == 21 and sub.wire_type == "varint":
                                result.likes = int(sub.data)
                            elif sub_num == 5 and sub.wire_type in ("string", "bytes"):
                                result.region = sub.data
                            elif sub_num == 14 and sub.wire_type == "varint":
                                result.rank = int(sub.data)
                            elif sub_num == 50 and sub.wire_type in ("string", "bytes"):
                                result.release_version = sub.data
                        
                        # Field 6 = clan_info
                        elif field_num == 6:
                            if sub_num == 2 and sub.wire_type in ("string", "bytes"):
                                result.clan_name = sub.data
                            elif sub_num == 4 and sub.wire_type == "varint":
                                result.clan_level = int(sub.data)
                            
        except Exception as e:
            logger.debug(f"Raw parsing also failed: {e}")


class ResultReporter:
    """Generates reports from check results."""
    
    def __init__(self, config: Settings):
        self.config = config
        
    def print_summary(self, results: List[CheckResult]) -> None:
        """Print a summary of check results."""
        # ANSI color codes
        class C:
            R = "\033[0m"
            B = "\033[1m"
            D = "\033[2m"
            R1 = "\033[91m"
            G = "\033[92m"
            Y = "\033[93m"
            CY = "\033[96m"
            W = "\033[97m"
        
        # Count statuses
        status_counts = {}
        for result in results:
            status = result.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        total = len(results)
        alive = status_counts.get("ALIVE", 0)
        banned = status_counts.get("BANNED", 0)
        dead = status_counts.get("DEAD", 0)
        server_down = status_counts.get("SERVER_DOWN", 0)
        blacklisted = status_counts.get("BLACKLISTED", 0)
        unknown = status_counts.get("UNKNOWN", 0)
        error = status_counts.get("ERROR", 0)
        
        # Print header
        print(f"\n  {C.CY}========================================{C.R}")
        print(f"  {C.B}  GUEST ACCOUNT REPORT{C.R}")
        print(f"  {C.CY}========================================{C.R}")
        print()
        
        # Print table header
        print(f"  {'UID':15s} {'STATUS':8s} {'NICK':12s} {'LVL':>4s} {'LIKES':>5s} {'REGION':6s} {'CLAN':12s}")
        print(f"  {'-'*15} {'-'*8} {'-'*12} {'-'*4} {'-'*5} {'-'*6} {'-'*12}")
        
        # Print each result
        for result in results:
            status = result.status.value
            
            if status == "ALIVE":
                sc = C.G
            elif status == "DEAD":
                sc = C.R1
            elif status == "BANNED":
                sc = C.R1
            elif status == "SERVER_DOWN":
                sc = C.Y
            elif status == "BLACKLISTED":
                sc = C.Y
            elif status == "UNKNOWN":
                sc = C.Y
            else:
                sc = C.Y
            
            nick = (result.nickname or result.name or "?")[:12]
            clan = (result.clan_name or "None")[:12]
            
            print(f"  {result.uid:15s} {sc}{status:8s}{C.R} {nick:12s} {result.level:4d} {result.likes:5d} {result.region:6s} {clan:12s}")
        
        print()
        print(f"  {C.CY}----------------------------------------{C.R}")
        print(f"  {C.B}Summary:{C.R}")
        
        if alive:
            print(f"  {C.G}Alive:       {alive}{C.R}")
        if server_down:
            print(f"  {C.Y}Server Down: {server_down}{C.R}")
        if banned:
            print(f"  {C.R1}Banned:      {banned}{C.R}")
        if blacklisted:
            print(f"  {C.Y}Blacklisted: {blacklisted}{C.R}")
        if dead:
            print(f"  {C.R1}Dead:        {dead}{C.R}")
        if unknown:
            print(f"  {C.Y}Unknown:     {unknown}{C.R}")
        if error:
            print(f"  {C.R1}Errors:      {error}{C.R}")
        
        print(f"  {C.B}Total:       {total}{C.R}")
        print(f"  {C.CY}========================================{C.R}")
        print()
    
    def save_report(self, results: List[CheckResult], 
                    output_file: Optional[str] = None) -> str:
        """Save check results to JSON file."""
        if not output_file:
            output_file = os.path.join(PROJECT_ROOT, "data", "guest_report.json")
        
        # Prepare report data
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_accounts": len(results),
            "summary": {},
            "accounts": [],
        }
        
        # Calculate summary
        status_counts = {}
        for result in results:
            status = result.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        report["summary"] = {
            "alive": status_counts.get("ALIVE", 0),
            "banned": status_counts.get("BANNED", 0),
            "dead": status_counts.get("DEAD", 0),
            "server_down": status_counts.get("SERVER_DOWN", 0),
            "blacklisted": status_counts.get("BLACKLISTED", 0),
            "unknown": status_counts.get("UNKNOWN", 0),
            "error": status_counts.get("ERROR", 0),
        }
        
        # Add account details
        for result in results:
            report["accounts"].append(result.to_dict())
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Report saved to: {output_file}")
        return output_file
    
    def save_to_database(self, results: List[CheckResult]) -> int:
        """Save check results to database."""
        if not self.config.database.enabled:
            return 0
        
        saved_count = 0
        
        try:
            db = Database(self.config.database.path)
            
            for result in results:
                # Get or create account
                account = db.get_account(result.uid)
                
                if not account:
                    account = Account(
                        uid=result.uid,
                        password="",  # Password not available in results
                        name=result.name,
                        source=AccountSource.MANUAL,
                        region=result.region,
                    )
                    db.add_account(account)
                
                # Update account with check result
                check_result = CheckResult(
                    checked_at=result.checked_at,
                    status=result.status,
                    oauth_status=result.oauth_status,
                    ban_reason=result.ban_reason,
                    nickname=result.nickname,
                    level=result.level,
                    exp=result.exp,
                    likes=result.likes,
                    rank=result.rank,
                    region=result.region,
                    clan_name=result.clan_name,
                    clan_level=result.clan_level,
                    release_version=result.release_version,
                    credit_score=result.credit_score,
                    last_login=result.last_login,
                    account_created=result.account_created,
                    error=result.error,
                )
                
                # Update account
                account.update_from_check(check_result)
                db.update_account(account)
                
                # Add check result
                db.add_check_result(account.id, check_result)
                
                saved_count += 1
            
            logger.info(f"Saved {saved_count} results to database")
            
        except Exception as e:
            logger.error(f"Failed to save to database: {e}")
        
        return saved_count


class CLIColors:
    """ANSI color codes for CLI output."""
    R = "\033[0m"
    B = "\033[1m"
    D = "\033[2m"
    R1 = "\033[91m"
    G = "\033[92m"
    Y = "\033[93m"
    CY = "\033[96m"
    W = "\033[97m"


def print_header():
    """Print application header."""
    print()
    print(f"  {CLIColors.CY}{CLIColors.B}========================================{CLIColors.R}")
    print(f"  {CLIColors.CY}{CLIColors.B}  Free Fire Guest Account Checker v2.0{CLIColors.R}")
    print(f"  {CLIColors.CY}{CLIColors.B}========================================{CLIColors.R}")
    print()


def print_account_list(accounts: List[AccountData]) -> None:
    """Print list of accounts to be checked."""
    print(f"  Found {len(accounts)} accounts:")
    for account in accounts[:10]:  # Show first 10
        print(f"  {CLIColors.D}{account.uid:15s} {CLIColors.W}{account.name:12s} {CLIColors.D}({account.source}){CLIColors.R}")
    if len(accounts) > 10:
        print(f"  {CLIColors.D}... and {len(accounts) - 10} more{CLIColors.R}")
    print()


async def check_all_accounts(
    accounts: List[AccountData],
    config: Settings,
    options: CheckOptions,
) -> List[CheckResult]:
    """Check all accounts with concurrency control."""
    
    results = []
    semaphore = asyncio.Semaphore(options.concurrent)
    
    async def check_with_semaphore(account: AccountData, index: int) -> CheckResult:
        """Check an account with semaphore for concurrency control."""
        async with semaphore:
            checker = AccountChecker(config, options)
            async with checker:
                result = await checker.check_account(account)
                
                # Print progress
                status = result.status.value
                if status == "ALIVE":
                    icon = f"{CLIColors.G}OK{CLIColors.R}"
                    extra = f"Lv{result.level} {result.likes}likes {result.nickname or result.name}"
                elif status == "SERVER_DOWN":
                    icon = f"{CLIColors.Y}SVR{CLIColors.R}"
                    extra = f"{CLIColors.D}oauth=alive, servers down{CLIColors.R}"
                elif status == "BANNED":
                    icon = f"{CLIColors.R1}BAN{CLIColors.R}"
                    extra = f"{CLIColors.D}{result.ban_reason}{CLIColors.R}"
                elif status == "DEAD":
                    icon = f"{CLIColors.R1}DEAD{CLIColors.R}"
                    extra = f"{CLIColors.D}account deleted{CLIColors.R}"
                else:
                    icon = f"{CLIColors.Y}??{CLIColors.R}"
                    extra = f"{CLIColors.D}{result.ban_reason or result.error}{CLIColors.R}"
                
                print(f"  [{index}/{len(accounts)}] {account.uid:15s} {icon}  {extra}")
                
                # Auto-save progress
                if options.auto_save_interval and index % options.auto_save_interval == 0:
                    reporter = ResultReporter(config)
                    reporter.save_report(results)
                
                return result
    
    # Create tasks
    tasks = []
    for i, account in enumerate(accounts, 1):
        tasks.append(check_with_semaphore(account, i))
    
    # Run tasks
    results = await asyncio.gather(*tasks, return_exceptions=False)
    
    return results


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Free Fire Guest Account Checker v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python guest_checker_v2.py                         # Check all accounts
  python guest_checker_v2.py --json data/guests.json # Check from JSON
  python guest_checker_v2.py --concurrent 10          # Use 10 workers
  python guest_checker_v2.py --proxy http://proxy:8080 # Use proxy
  python guest_checker_v2.py --web                   # Start web interface
        """,
    )
    
    # Input options
    parser.add_argument(
        "--json", "-j",
        type=str,
        default=None,
        help="Path to JSON file with accounts",
    )
    parser.add_argument(
        "--csv", "-c",
        type=str,
        default=None,
        help="Path to CSV file with accounts",
    )
    parser.add_argument(
        "--db", "-d",
        type=str,
        default=None,
        help="Path to SQLite database file",
    )
    
    # Processing options
    parser.add_argument(
        "--concurrent", "-w",
        type=int,
        default=None,
        help="Number of concurrent workers (default: 5)",
    )
    parser.add_argument(
        "--timeout", "-t",
        type=float,
        default=None,
        help="Request timeout in seconds (default: 30)",
    )
    parser.add_argument(
        "--retries", "-r",
        type=int,
        default=None,
        help="Number of retry attempts (default: 3)",
    )
    
    # Proxy options
    parser.add_argument(
        "--proxy", "-p",
        type=str,
        default=None,
        help="Proxy URL (e.g., http://proxy:8080)",
    )
    parser.add_argument(
        "--proxy-type",
        type=str,
        choices=["http", "https", "socks4", "socks5"],
        default=None,
        help="Proxy type (default: http)",
    )
    parser.add_argument(
        "--proxy-user",
        type=str,
        default=None,
        help="Proxy username",
    )
    parser.add_argument(
        "--proxy-pass",
        type=str,
        default=None,
        help="Proxy password",
    )
    
    # Output options
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output file path (default: data/guest_report.json)",
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["json", "csv", "db"],
        default=None,
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save results to file",
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Don't save results to database",
    )
    
    # Web interface
    parser.add_argument(
        "--web",
        action="store_true",
        help="Start web interface",
    )
    parser.add_argument(
        "--web-host",
        type=str,
        default=None,
        help="Web interface host (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--web-port",
        type=int,
        default=None,
        help="Web interface port (default: 8080)",
    )
    
    # Configuration
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to configuration file",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=None,
        help="Logging level (default: INFO)",
    )
    
    # Other options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate input without checking accounts",
    )
    parser.add_argument(
        "--version", "-v",
        action="store_true",
        help="Show version and exit",
    )
    
    return parser.parse_args()


def create_check_options(args: argparse.Namespace, config: Settings) -> CheckOptions:
    """Create check options from command line arguments and configuration."""
    return CheckOptions(
        concurrent=args.concurrent or config.checker.concurrent_workers,
        timeout=args.timeout or config.rate_limit.request_timeout,
        retries=args.retries or config.rate_limit.retry_attempts,
        use_proxy=bool(args.proxy or config.proxy.enabled),
        proxy_url=args.proxy or get_proxy_url(),
        validate_passwords=config.checker.validate_passwords,
        save_results=not args.no_save,
        auto_save_interval=config.checker.save_interval,
        continue_on_error=True,
    )


def validate_input_files(args: argparse.Namespace) -> List[AccountData]:
    """Validate and load input files."""
    accounts = []
    
    # Load from JSON if specified
    if args.json:
        if not os.path.exists(args.json):
            logger.error(f"JSON file not found: {args.json}")
            sys.exit(1)
        
        loader = AccountLoader(config_manager.get())
        accounts.extend(loader._load_json_file(args.json))
    
    # Load from CSV if specified
    if args.csv:
        if not os.path.exists(args.csv):
            logger.error(f"CSV file not found: {args.csv}")
            sys.exit(1)
        
        loader = AccountLoader(config_manager.get())
        accounts.extend(loader._load_csv_file(args.csv))
    
    return accounts


async def main():
    """Main entry point."""
    args = parse_args()
    
    # Show version if requested
    if args.version:
        print("Free Fire Guest Account Checker v2.0")
        sys.exit(0)
    
    # Load configuration
    config = config_manager.get()
    
    # Set up logging
    setup_logging(
        level=LogLevel[args.log_level.upper()] if args.log_level else config.logging.level,
        log_file=config.logging.log_file,
        console=True,
        file_output=config.logging.file_output,
        use_colors=True,
    )
    
    # Print header
    print_header()
    
    # Handle web interface
    if args.web:
        logger.info("Starting web interface...")
        # Import and start web server
        try:
            from web.app import create_app
            app = create_app(config)
            
            host = args.web_host or config.web.host
            port = args.web_port or config.web.port
            
            logger.info(f"Web interface running on http://{host}:{port}")
            
            # For production, use a proper WSGI server
            # For development, use Flask's built-in server
            if config.environment == "development":
                app.run(host=host, port=port, debug=config.web.debug)
            else:
                # In production, you should use gunicorn, uvicorn, etc.
                logger.warning("For production, use a WSGI server like gunicorn")
                app.run(host=host, port=port)
                
        except ImportError:
            logger.error("Web interface not available. Install required packages.")
            logger.error("pip install flask flask-cors")
            sys.exit(1)
        
        return
    
    # Validate input files
    if args.json or args.csv:
        accounts = validate_input_files(args)
    else:
        # Load from all sources
        loader = AccountLoader(config)
        accounts = loader.load_all()
    
    if not accounts:
        logger.error("No accounts found to check!")
        logger.error("Please provide accounts in:")
        logger.error("  - data/guests.json")
        logger.error("  - data/level_accounts.json")
        logger.error("  - data/guests.db")
        logger.error("  - Or specify with --json or --csv")
        sys.exit(1)
    
    # Dry run - just validate and exit
    if args.dry_run:
        logger.info(f"Dry run: {len(accounts)} accounts validated successfully")
        print_account_list(accounts)
        sys.exit(0)
    
    # Print account list
    print_account_list(accounts)
    
    # Create check options
    options = create_check_options(args, config)
    
    # Print checking info
    print(f"  {CLIColors.B}Checking {len(accounts)} accounts...{CLIColors.R}")
    print(f"  {CLIColors.D}Concurrency: {options.concurrent} workers{CLIColors.R}")
    print(f"  {CLIColors.D}Timeout: {options.timeout}s{CLIColors.R}")
    if options.use_proxy:
        print(f"  {CLIColors.D}Proxy: {options.proxy_url}{CLIColors.R}")
    print(f"  {CLIColors.D}(OAuth works even if game servers are down){CLIColors.R}")
    print()
    
    # Check accounts
    try:
        results = await check_all_accounts(accounts, config, options)
    except KeyboardInterrupt:
        print(f"\n\n  {CLIColors.Y}Interrupted by user.{CLIColors.R}\n")
        sys.exit(0)
    
    # Generate and print report
    reporter = ResultReporter(config)
    reporter.print_summary(results)
    
    # Save results
    if options.save_results:
        output_file = args.output or os.path.join(PROJECT_ROOT, "data", "guest_report.json")
        reporter.save_report(results, output_file)
    
    if not args.no_db:
        reporter.save_to_database(results)
    
    # Print completion
    print(f"  {CLIColors.D}Done!{CLIColors.R}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n\n  {CLIColors.Y}Interrupted.{CLIColors.R}\n")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
