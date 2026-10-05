"""
Telegram Bot for Free Fire Guest Account Checker
Provides account checking via Telegram
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import aiohttp

# Import local modules
from config.settings import Settings, get_settings
from config.runtime import RuntimeState, get_runtime_state
from src.database.database import Database, get_database, init_database
from src.utils.logging import get_logger, setup_logging
from src.utils.helpers import generate_id, format_timestamp, get_timestamp
from src.utils.validators import validate_account_id
from src.level.auth import Authenticator, AuthResult
from src.level.guest_info import GuestInfoFetcher, GuestInfo

logger = get_logger(__name__)


@dataclass
class TelegramBotConfig:
    """Telegram bot configuration"""
    token: str
    admin_id: Optional[int] = None
    api_url: str = "http://localhost:5000"
    webhook_url: Optional[str] = None
    webhook_port: int = 8443
    use_webhook: bool = False
    poll_interval: float = 1.0
    max_concurrent: int = 5
    rate_limit: float = 1.0
    allowed_user_ids: Set[int] = field(default_factory=set)
    banned_user_ids: Set[int] = field(default_factory=set)


@dataclass
class TelegramUser:
    """Telegram user information"""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: Optional[str] = None
    is_admin: bool = False
    last_command: Optional[str] = None
    last_command_at: float = field(default_factory=time.time)
    check_count: int = 0
    error_count: int = 0


@dataclass
class BotState:
    """Telegram bot state"""
    config: TelegramBotConfig
    database: Database
    runtime: RuntimeState
    authenticator: Authenticator
    guest_fetcher: GuestInfoFetcher
    http_client: aiohttp.ClientSession
    users: Dict[int, TelegramUser] = field(default_factory=dict)
    active_checks: Dict[str, float] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)
    request_count: int = 0
    error_count: int = 0
    last_update_id: int = 0


class TelegramBot:
    """Telegram bot implementation"""

    def __init__(self, config: TelegramBotConfig):
        self.config = config
        self.state: Optional[BotState] = None
        self.bot: Optional[Any] = None  # Will be set in initialize()
        self._running: bool = False

    async def initialize(self) -> None:
        """Initialize the bot"""
        logger.info("Initializing Telegram bot...")

        # Initialize settings
        settings = get_settings()
        setup_logging(level=settings.log_level, json_format=False)

        # Initialize database
        db_path = settings.database_path or "data/accounts.db"
        database = await init_database(db_path)

        # Initialize runtime state
        runtime = RuntimeState()

        # Create HTTP client
        http_client = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
            headers={"User-Agent": "FreeFireGuestChecker-TelegramBot/2.0"}
        )

        # Create authenticator
        authenticator = Authenticator(
            http_client=http_client,
            settings=settings
        )

        # Create guest fetcher
        guest_fetcher = GuestInfoFetcher(
            http_client=http_client,
            authenticator=authenticator
        )

        # Initialize state
        self.state = BotState(
            config=self.config,
            database=database,
            runtime=runtime,
            authenticator=authenticator,
            guest_fetcher=guest_fetcher,
            http_client=http_client
        )

        # Import telegram library
        try:
            from telegram import Update, Bot as TelegramBotClient
            from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
            self.Bot = TelegramBotClient
            self.Update = Update
            self.Application = Application
            self.CommandHandler = CommandHandler
            self.MessageHandler = MessageHandler
            self.filters = filters
            self.ContextTypes = ContextTypes
        except ImportError:
            logger.warning("python-telegram-bot not installed. Install with: pip install python-telegram-bot")
            raise

        # Create bot instance
        self.bot = self.Bot(token=self.config.token)

        # Setup admin
        if self.config.admin_id:
            self.state.users[self.config.admin_id] = TelegramUser(
                user_id=self.config.admin_id,
                is_admin=True
            )

        logger.info("Telegram bot initialized successfully")

    async def start(self) -> None:
        """Start the bot"""
        if not self.state:
            await self.initialize()

        self._running = True

        # Setup handlers
        app = self.Application.builder() \
            .token(self.config.token) \
            .build()

        # Command handlers
        app.add_handler(self.CommandHandler("start", self._handle_start))
        app.add_handler(self.CommandHandler("help", self._handle_help))
        app.add_handler(self.CommandHandler("check", self._handle_check_command))
        app.add_handler(self.CommandHandler("batch", self._handle_batch_command))
        app.add_handler(self.CommandHandler("stats", self._handle_stats))
        app.add_handler(self.CommandHandler("me", self._handle_me))
        app.add_handler(self.CommandHandler("admin", self._handle_admin))
        app.add_handler(self.CommandHandler("broadcast", self._handle_broadcast))
        app.add_handler(self.CommandHandler("ban", self._handle_ban))
        app.add_handler(self.CommandHandler("unban", self._handle_unban))

        # Message handlers
        app.add_handler(self.MessageHandler(self.filters.TEXT & ~self.filters.COMMAND, self._handle_text_message))

        # Error handler
        app.add_error_handler(self._handle_error)

        # Start the bot
        if self.config.use_webhook:
            await app.run_webhook(
                listen="0.0.0.0",
                port=self.config.webhook_port,
                webhook_url=self.config.webhook_url,
                cert=None,
                key=None,
                drop_pending_updates=True
            )
        else:
            await app.run_polling(
                poll_interval=self.config.poll_interval,
                drop_pending_updates=True
            )

    async def stop(self) -> None:
        """Stop the bot"""
        self._running = False
        if self.state and self.state.http_client:
            await self.state.http_client.close()
        if self.state and self.state.database:
            await self.state.database.close()
        logger.info("Telegram bot stopped")

    def is_running(self) -> bool:
        """Check if bot is running"""
        return self._running

    # =========================================================================
    # Command Handlers
    # =========================================================================

    async def _handle_start(self, update: Any, context: Any) -> None:
        """Handle /start command"""
        user = update.effective_user
        chat = update.effective_chat

        user_id = user.id
        username = user.username
        first_name = user.first_name
        last_name = user.last_name

        # Register user
        if user_id not in self.state.users:
            self.state.users[user_id] = TelegramUser(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                is_admin=user_id in (self.config.admin_id or set())
            )

        user_obj = self.state.users[user_id]
        user_obj.last_command = "start"
        user_obj.last_command_at = time.time()

        welcome_msg = f"""
🔥 <b>Free Fire Guest Account Checker</b> 🔥

Welcome, {first_name}!

This bot helps you check Free Fire guest accounts.

<b>Commands:</b>
• /check <account_id> - Check a single account
• /batch <count> - Check multiple random accounts
• /stats - Show your statistics
• /me - Show your profile
• /help - Show all commands

<b>Usage:</b>
Just send an account ID to check it!

<b>Example:</b>
<code>/check 123456789</code>
"""

        await self._send_message(chat.id, welcome_msg, parse_mode="HTML")

    async def _handle_help(self, update: Any, context: Any) -> None:
        """Handle /help command"""
        chat = update.effective_chat

        help_msg = f"""
📖 <b>Free Fire Guest Checker - Help</b> 📖

<b>Available Commands:</b>

<b>Account Checking:</b>
• /check <account_id> - Check a specific account
• /batch <count> - Check multiple random accounts
• Send account ID directly - Quick check

<b>Information:</b>
• /stats - Your checking statistics
• /me - Your user profile
• /status - Bot status

<b>Admin Commands:</b>
• /broadcast <message> - Send message to all users
• /ban <user_id> - Ban a user
• /unban <user_id> - Unban a user
• /admin - Admin panel

<b>Examples:</b>
<code>/check 123456789</code>
<code>/batch 10</code>
<code>/stats</code>

<b>Note:</b> Maximum 20 concurrent checks per user.
"""

        await self._send_message(chat.id, help_msg, parse_mode="HTML")

    async def _handle_check_command(self, update: Any, context: Any) -> None:
        """Handle /check command"""
        chat = update.effective_chat
        user = update.effective_user
        args = context.args

        if not args:
            await self._send_message(chat.id, "❌ Please provide an account ID. Example: /check 123456789")
            return

        account_id = args.strip()

        if not validate_account_id(account_id):
            await self._send_message(chat.id, f"❌ Invalid account ID: {account_id}")
            return

        user_id = user.id
        user_obj = self.state.users.get(user_id)

        if user_obj:
            user_obj.last_command = "check"
            user_obj.last_command_at = time.time()

        # Check if user is banned
        if user_id in self.config.banned_user_ids:
            await self._send_message(chat.id, "❌ You are banned from using this bot.")
            return

        # Rate limiting
        if user_id in self.state.active_checks:
            last_check = self.state.active_checks[user_id]
            if time.time() - last_check < self.config.rate_limit:
                await self._send_message(chat.id, f"⏳ Please wait {self.config.rate_limit:.1f} seconds between checks.")
                return

        self.state.active_checks[user_id] = time.time()

        # Send typing action
        await self._send_chat_action(chat.id, "typing")

        try:
            result = await self._check_account(account_id)
            
            if result.get("error"):
                if user_obj:
                    user_obj.error_count += 1
                await self._send_message(chat.id, f"❌ Error: {result['error']}")
                return

            data = result.get("data", {})
            status = result.get("status", "unknown")

            if user_obj:
                user_obj.check_count += 1

            # Format response
            if status == "success":
                guest_data = data.get("data", {})
                msg = f"""
✅ <b>Account Check Result</b> ✅

<b>Account ID:</b> <code>{account_id}</code>
<b>Status:</b> {status}
<b>Checked:</b> {format_timestamp(time.time())}
"""

                if guest_data:
                    nickname = guest_data.get("nickname", "N/A")
                    level = guest_data.get("level", "N/A")
                    diamonds = guest_data.get("diamonds", "N/A")
                    coins = guest_data.get("coins", "N/A")

                    msg += f"""
<b>Player Info:</b>
• Nickname: {nickname}
• Level: {level}
• Diamonds: {diamonds}
• Coins: {coins}
"""

                await self._send_message(chat.id, msg, parse_mode="HTML")
            else:
                await self._send_message(chat.id, f"⚠️ Account {account_id}: {status}")

        except Exception as e:
            logger.error(f"Error checking account {account_id}: {e}")
            if user_obj:
                user_obj.error_count += 1
            await self._send_message(chat.id, f"❌ Error checking account: {e}")

    async def _handle_batch_command(self, update: Any, context: Any) -> None:
        """Handle /batch command"""
        chat = update.effective_chat
        user = update.effective_user
        args = context.args

        user_id = user.id
        user_obj = self.state.users.get(user_id)

        if user_obj:
            user_obj.last_command = "batch"
            user_obj.last_command_at = time.time()

        # Check if user is banned
        if user_id in self.config.banned_user_ids:
            await self._send_message(chat.id, "❌ You are banned from using this bot.")
            return

        # Parse count
        try:
            count = int(args.strip()) if args else 5
            if count < 1 or count > 50:
                await self._send_message(chat.id, "❌ Please provide a count between 1 and 50.")
                return
        except ValueError:
            await self._send_message(chat.id, "❌ Invalid count. Please provide a number.")
            return

        # Rate limiting
        if user_id in self.state.active_checks:
            last_check = self.state.active_checks[user_id]
            if time.time() - last_check < self.config.rate_limit * 2:
                await self._send_message(chat.id, f"⏳ Please wait {self.config.rate_limit * 2:.1f} seconds between batch checks.")
                return

        self.state.active_checks[user_id] = time.time()

        # Send typing action
        await self._send_chat_action(chat.id, "typing")

        try:
            # Generate random accounts
            from scripts.generate_accounts import generate_random_accounts
            accounts = generate_random_accounts(count)

            msg = f"🔍 <b>Checking {count} accounts...</b>\n\n"
            await self._send_message(chat.id, msg, parse_mode="HTML")

            results = []
            for account_id in accounts:
                try:
                    result = await self._check_account(account_id)
                    if not result.get("error"):
                        status = result.get("status", "unknown")
                        results.append(f"{account_id}: {status}")
                        if user_obj:
                            user_obj.check_count += 1
                except Exception as e:
                    results.append(f"{account_id}: ERROR")
                    if user_obj:
                        user_obj.error_count += 1

            # Send results
            results_msg = "\n".join(results)
            await self._send_message(chat.id, f"📊 <b>Results:</b>\n{results_msg}", parse_mode="HTML")

        except Exception as e:
            logger.error(f"Error in batch check: {e}")
            await self._send_message(chat.id, f"❌ Error in batch check: {e}")

    async def _handle_stats(self, update: Any, context: Any) -> None:
        """Handle /stats command"""
        chat = update.effective_chat
        user = update.effective_user

        user_id = user.id
        user_obj = self.state.users.get(user_id)

        if not user_obj:
            await self._send_message(chat.id, "❌ User not registered. Use /start first.")
            return

        user_obj.last_command = "stats"
        user_obj.last_command_at = time.time()

        # Get user stats
        total_checks = user_obj.check_count
        total_errors = user_obj.error_count

        # Get database stats
        db_stats = await self.state.database.get_statistics()

        msg = f"""
📈 <b>Your Statistics</b> 📈

<b>User:</b> {user_obj.first_name or user_id}
<b>Total Checks:</b> {total_checks}
<b>Total Errors:</b> {total_errors}
<b>Success Rate:</b> {(total_checks - total_errors) / max(total_checks, 1) * 100:.1f}%

<b>Bot Statistics:</b>
<b>Total Accounts in DB:</b> {db_stats.get('total_accounts', 0)}
<b>Checked Today:</b> {db_stats.get('checked_today', 0)}
<b>Bot Uptime:</b> {format_timestamp(self.state.started_at)}
"""

        await self._send_message(chat.id, msg, parse_mode="HTML")

    async def _handle_me(self, update: Any, context: Any) -> None:
        """Handle /me command"""
        chat = update.effective_chat
        user = update.effective_user

        user_id = user.id
        user_obj = self.state.users.get(user_id)

        if not user_obj:
            await self._send_message(chat.id, "❌ User not registered. Use /start first.")
            return

        user_obj.last_command = "me"
        user_obj.last_command_at = time.time()

        is_admin = "✅ Yes" if user_obj.is_admin else "❌ No"

        msg = f"""
👤 <b>Your Profile</b> 👤

<b>User ID:</b> <code>{user_id}</code>
<b>Username:</b> @{user_obj.username or "N/A"}
<b>Name:</b> {user_obj.first_name or "N/A"} {user_obj.last_name or ""}
<b>Language:</b> {user_obj.language_code or "N/A"}
<b>Admin:</b> {is_admin}
<b>Total Checks:</b> {user_obj.check_count}
<b>Total Errors:</b> {user_obj.error_count}
<b>Last Command:</b> /{user_obj.last_command or "none"}
<b>Joined:</b> {format_timestamp(user_obj.last_command_at)}
"""

        await self._send_message(chat.id, msg, parse_mode="HTML")

    async def _handle_admin(self, update: Any, context: Any) -> None:
        """Handle /admin command"""
        chat = update.effective_chat
        user = update.effective_user

        user_id = user.id
        user_obj = self.state.users.get(user_id)

        if not user_obj or not user_obj.is_admin:
            await self._send_message(chat.id, "❌ You are not an admin.")
            return

        user_obj.last_command = "admin"
        user_obj.last_command_at = time.time()

        # Get bot stats
        total_users = len(self.state.users)
        total_checks = sum(u.check_count for u in self.state.users.values())
        total_errors = sum(u.error_count for u in self.state.users.values())
        banned_users = len(self.config.banned_user_ids)

        msg = f"""
👑 <b>Admin Panel</b> 👑

<b>Bot Statistics:</b>
• Total Users: {total_users}
• Total Checks: {total_checks}
• Total Errors: {total_errors}
• Banned Users: {banned_users}
• Uptime: {format_timestamp(self.state.started_at)}

<b>Commands:</b>
• /broadcast <message> - Send to all users
• /ban <user_id> - Ban a user
• /unban <user_id> - Unban a user
"""

        await self._send_message(chat.id, msg, parse_mode="HTML")

    async def _handle_broadcast(self, update: Any, context: Any) -> None:
        """Handle /broadcast command"""
        chat = update.effective_chat
        user = update.effective_user
        args = context.args

        user_id = user.id
        user_obj = self.state.users.get(user_id)

        if not user_obj or not user_obj.is_admin:
            await self._send_message(chat.id, "❌ You are not an admin.")
            return

        if not args:
            await self._send_message(chat.id, "❌ Please provide a message to broadcast.")
            return

        message = args.strip()
        sent_count = 0

        for user_id, user_obj in self.state.users.items():
            if user_id in self.config.banned_user_ids:
                continue

            try:
                await self._send_message(user_id, f"📢 <b>Broadcast:</b>\n\n{message}", parse_mode="HTML")
                sent_count += 1
                await asyncio.sleep(0.1)  # Rate limit
            except Exception as e:
                logger.error(f"Failed to send broadcast to {user_id}: {e}")

        await self._send_message(chat.id, f"✅ Broadcast sent to {sent_count} users")

    async def _handle_ban(self, update: Any, context: Any) -> None:
        """Handle /ban command"""
        chat = update.effective_chat
        user = update.effective_user
        args = context.args

        user_id = user.id
        user_obj = self.state.users.get(user_id)

        if not user_obj or not user_obj.is_admin:
            await self._send_message(chat.id, "❌ You are not an admin.")
            return

        if not args:
            await self._send_message(chat.id, "❌ Please provide a user ID to ban.")
            return

        try:
            target_user_id = int(args.strip())
        except ValueError:
            await self._send_message(chat.id, "❌ Invalid user ID. Must be a number.")
            return

        self.config.banned_user_ids.add(target_user_id)
        await self._send_message(chat.id, f"✅ User {target_user_id} banned")

    async def _handle_unban(self, update: Any, context: Any) -> None:
        """Handle /unban command"""
        chat = update.effective_chat
        user = update.effective_user
        args = context.args

        user_id = user.id
        user_obj = self.state.users.get(user_id)

        if not user_obj or not user_obj.is_admin:
            await self._send_message(chat.id, "❌ You are not an admin.")
            return

        if not args:
            await self._send_message(chat.id, "❌ Please provide a user ID to unban.")
            return

        try:
            target_user_id = int(args.strip())
        except ValueError:
            await self._send_message(chat.id, "❌ Invalid user ID. Must be a number.")
            return

        self.config.banned_user_ids.discard(target_user_id)
        await self._send_message(chat.id, f"✅ User {target_user_id} unbanned")

    # =========================================================================
    # Message Handlers
    # =========================================================================

    async def _handle_text_message(self, update: Any, context: Any) -> None:
        """Handle text messages"""
        chat = update.effective_chat
        user = update.effective_user
        text = update.message.text

        user_id = user.id
        user_obj = self.state.users.get(user_id)

        # Check if user is banned
        if user_id in self.config.banned_user_ids:
            return

        # Check if it looks like an account ID
        if text.strip().isdigit() and len(text.strip()) >= 6:
            account_id = text.strip()
            
            if user_obj:
                user_obj.last_command = "quick_check"
                user_obj.last_command_at = time.time()

            # Rate limiting
            if user_id in self.state.active_checks:
                last_check = self.state.active_checks[user_id]
                if time.time() - last_check < self.config.rate_limit:
                    await self._send_message(chat.id, f"⏳ Please wait {self.config.rate_limit:.1f} seconds between checks.")
                    return

            self.state.active_checks[user_id] = time.time()

            # Send typing action
            await self._send_chat_action(chat.id, "typing")

            try:
                result = await self._check_account(account_id)
                
                if result.get("error"):
                    if user_obj:
                        user_obj.error_count += 1
                    await self._send_message(chat.id, f"❌ Error: {result['error']}")
                    return

                data = result.get("data", {})
                status = result.get("status", "unknown")

                if user_obj:
                    user_obj.check_count += 1

                if status == "success":
                    await self._send_message(chat.id, f"✅ Account {account_id}: {status}")
                else:
                    await self._send_message(chat.id, f"⚠️ Account {account_id}: {status}")

            except Exception as e:
                logger.error(f"Error checking account {account_id}: {e}")
                if user_obj:
                    user_obj.error_count += 1
                await self._send_message(chat.id, f"❌ Error: {e}")

    async def _handle_error(self, update: Any, context: Any) -> None:
        """Handle errors"""
        logger.error(f"Telegram bot error: {context.error}")
        if update and update.effective_chat:
            try:
                await self._send_message(update.effective_chat.id, "❌ An error occurred. Please try again.")
            except:
                pass

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _check_account(self, account_id: str) -> Dict[str, Any]:
        """Check a single account"""
        state = self.state
        state.request_count += 1

        # Check if already in database
        existing = await state.database.get_account(account_id)
        if existing:
            return {
                "account_id": account_id,
                "status": existing.status.value,
                "data": existing.to_dict(),
                "cached": True,
                "checked_at": format_timestamp(existing.updated_at)
            }

        # Authenticate
        auth_result = await state.authenticator.authenticate()
        if not auth_result.success:
            state.error_count += 1
            return {"error": f"Authentication failed: {auth_result.error}"}

        # Fetch guest info
        guest_info = await state.guest_fetcher.fetch_guest_info(
            account_id=account_id,
            auth_data=auth_result.data
        )

        if not guest_info:
            state.error_count += 1
            return {"error": f"Account not found: {account_id}"}

        # Save to database
        await state.database.save_account(
            account_id=account_id,
            data=guest_info.to_dict(),
            region="telegram",
            source="telegram_bot"
        )

        return {
            "account_id": account_id,
            "status": "success",
            "data": guest_info.to_dict(),
            "cached": False,
            "checked_at": format_timestamp(time.time())
        }

    async def _send_message(self, chat_id: int, text: str, **kwargs) -> Any:
        """Send a message"""
        try:
            return await self.bot.send_message(chat_id=chat_id, text=text, **kwargs)
        except Exception as e:
            logger.error(f"Failed to send message to {chat_id}: {e}")
            raise

    async def _send_chat_action(self, chat_id: int, action: str) -> Any:
        """Send a chat action"""
        try:
            return await self.bot.send_chat_action(chat_id=chat_id, action=action)
        except Exception as e:
            logger.error(f"Failed to send chat action to {chat_id}: {e}")


# =============================================================================
# Main Entry Point
# =============================================================================

async def run_telegram_bot() -> None:
    """Run the Telegram bot"""
    # Load configuration from environment
    token = os.getenv("TELEGRAM_TOKEN")
    admin_id_str = os.getenv("TELEGRAM_ADMIN_ID")
    api_url = os.getenv("API_URL", "http://localhost:5000")

    if not token:
        logger.error("TELEGRAM_TOKEN environment variable not set")
        return

    admin_id = None
    if admin_id_str:
        try:
            admin_id = int(admin_id_str)
        except ValueError:
            logger.error("Invalid TELEGRAM_ADMIN_ID")
            return

    config = TelegramBotConfig(
        token=token,
        admin_id=admin_id,
        api_url=api_url,
        use_webhook=os.getenv("TELEGRAM_USE_WEBHOOK", "false").lower() == "true",
        webhook_url=os.getenv("TELEGRAM_WEBHOOK_URL"),
        webhook_port=int(os.getenv("TELEGRAM_WEBHOOK_PORT", "8443"))
    )

    bot = TelegramBot(config)
    await bot.initialize()
    await bot.start()


def run_telegram_bot_sync() -> None:
    """Run the Telegram bot synchronously"""
    asyncio.run(run_telegram_bot())


if __name__ == "__main__":
    run_telegram_bot_sync()
