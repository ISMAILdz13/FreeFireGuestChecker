"""
Discord Bot for Free Fire Guest Account Checker
Provides account checking via Discord
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
class DiscordBotConfig:
    """Discord bot configuration"""
    token: str
    guild_id: Optional[int] = None
    api_url: str = "http://localhost:5000"
    command_prefix: str = "/"
    max_concurrent: int = 5
    rate_limit: float = 1.0
    allowed_role_ids: Set[int] = field(default_factory=set)
    banned_user_ids: Set[int] = field(default_factory=set)
    admin_user_ids: Set[int] = field(default_factory=set)


@dataclass
class DiscordUser:
    """Discord user information"""
    user_id: int
    username: str
    discriminator: str
    avatar: Optional[str] = None
    is_admin: bool = False
    last_command: Optional[str] = None
    last_command_at: float = field(default_factory=time.time)
    check_count: int = 0
    error_count: int = 0


@dataclass
class BotState:
    """Discord bot state"""
    config: DiscordBotConfig
    database: Database
    runtime: RuntimeState
    authenticator: Authenticator
    guest_fetcher: GuestInfoFetcher
    http_client: aiohttp.ClientSession
    users: Dict[int, DiscordUser] = field(default_factory=dict)
    active_checks: Dict[str, float] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)
    request_count: int = 0
    error_count: int = 0


class DiscordBot:
    """Discord bot implementation"""

    def __init__(self, config: DiscordBotConfig):
        self.config = config
        self.state: Optional[BotState] = None
        self.bot: Optional[Any] = None  # Will be set in initialize()
        self._running: bool = False

    async def initialize(self) -> None:
        """Initialize the bot"""
        logger.info("Initializing Discord bot...")

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
            headers={"User-Agent": "FreeFireGuestChecker-DiscordBot/2.0"}
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

        # Import discord library
        try:
            import discord
            from discord.ext import commands
            self.discord = discord
            self.commands = commands
        except ImportError:
            logger.warning("discord.py not installed. Install with: pip install discord.py")
            raise

        # Create bot instance
        intents = self.discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True

        self.bot = self.commands.Bot(
            command_prefix=self.config.command_prefix,
            intents=intents
        )

        # Setup admin users
        for admin_id in self.config.admin_user_ids:
            self.state.users[admin_id] = DiscordUser(
                user_id=admin_id,
                username="Admin",
                discriminator="0000",
                is_admin=True
            )

        # Setup event handlers
        self.bot.event(self._on_ready)
        self.bot.event(self._on_message)
        self.bot.event(self._on_error)

        # Setup command handlers
        self.bot.command(name="check")(self._handle_check_command)
        self.bot.command(name="batch")(self._handle_batch_command)
        self.bot.command(name="stats")(self._handle_stats)
        self.bot.command(name="me")(self._handle_me)
        self.bot.command(name="help")(self._handle_help)
        self.bot.command(name="admin")(self._handle_admin)
        self.bot.command(name="broadcast")(self._handle_broadcast)
        self.bot.command(name="ban")(self._handle_ban)
        self.bot.command(name="unban")(self._handle_unban)
        self.bot.command(name="ping")(self._handle_ping)

        logger.info("Discord bot initialized successfully")

    async def start(self) -> None:
        """Start the bot"""
        if not self.state:
            await self.initialize()

        self._running = True

        try:
            await self.bot.start(self.config.token)
        except Exception as e:
            logger.error(f"Error starting Discord bot: {e}")
            raise

    async def stop(self) -> None:
        """Stop the bot"""
        self._running = False
        if self.bot:
            await self.bot.close()
        if self.state and self.state.http_client:
            await self.state.http_client.close()
        if self.state and self.state.database:
            await self.state.database.close()
        logger.info("Discord bot stopped")

    def is_running(self) -> bool:
        """Check if bot is running"""
        return self._running

    # =========================================================================
    # Event Handlers
    # =========================================================================

    async def _on_ready(self) -> None:
        """Handle bot ready event"""
        if self.bot:
            logger.info(f"Logged in as {self.bot.user.name} (ID: {self.bot.user.id})")
            logger.info(f"Connected to {len(self.bot.guilds)} guild(s)")
            
            # Set presence
            await self.bot.change_presence(
                activity=self.discord.Game(name="Free Fire Guest Checker")
            )

    async def _on_message(self, message: Any) -> None:
        """Handle messages"""
        # Ignore messages from bots
        if message.author.bot:
            return

        # Process commands
        await self.bot.process_commands(message)

        # Check if message is just an account ID
        if not message.content.startswith(self.config.command_prefix):
            content = message.content.strip()
            if content.isdigit() and len(content) >= 6:
                await self._handle_quick_check(message, content)

    async def _on_error(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Handle errors"""
        logger.error(f"Discord bot error in {event}: {args[0] if args else 'Unknown error'}")

    # =========================================================================
    # Command Handlers
    # =========================================================================

    async def _handle_ping(self, ctx: Any) -> None:
        """Handle /ping command"""
        latency = round(self.bot.latency * 1000)
        await ctx.send(f"🏓 Pong! {latency}ms")

    async def _handle_help(self, ctx: Any) -> None:
        """Handle /help command"""
        embed = self.discord.Embed(
            title="Free Fire Guest Account Checker - Help",
            description="Check Free Fire guest accounts via Discord",
            color=self.discord.Color.blue()
        )

        embed.add_field(
            name="Account Checking",
            value="""
• `/check <account_id>` - Check a specific account
• `/batch <count>` - Check multiple random accounts
• Send account ID directly - Quick check
""",
            inline=False
        )

        embed.add_field(
            name="Information",
            value="""
• `/stats` - Your checking statistics
• `/me` - Your user profile
• `/status` - Bot status
""",
            inline=False
        )

        embed.add_field(
            name="Admin Commands",
            value="""
• `/broadcast <message>` - Send to all users
• `/ban <user_id>` - Ban a user
• `/unban <user_id>` - Unban a user
• `/admin` - Admin panel
""",
            inline=False
        )

        embed.add_field(
            name="Examples",
            value="""
`/check 123456789`
`/batch 10`
`/stats`
""",
            inline=False
        )

        embed.set_footer(text="Maximum 20 concurrent checks per user")

        await ctx.send(embed=embed)

    async def _handle_check_command(self, ctx: Any, account_id: str) -> None:
        """Handle /check command"""
        user_id = ctx.author.id
        user_obj = self.state.users.get(user_id)

        if user_obj:
            user_obj.last_command = "check"
            user_obj.last_command_at = time.time()

        # Check if user is banned
        if user_id in self.config.banned_user_ids:
            await ctx.send("❌ You are banned from using this bot.")
            return

        # Validate account ID
        if not validate_account_id(account_id):
            await ctx.send(f"❌ Invalid account ID: {account_id}")
            return

        # Rate limiting
        if user_id in self.state.active_checks:
            last_check = self.state.active_checks[user_id]
            if time.time() - last_check < self.config.rate_limit:
                await ctx.send(f"⏳ Please wait {self.config.rate_limit:.1f} seconds between checks.")
                return

        self.state.active_checks[user_id] = time.time()

        # Send typing indicator
        async with ctx.typing():
            try:
                result = await self._check_account(account_id)
                
                if result.get("error"):
                    if user_obj:
                        user_obj.error_count += 1
                    await ctx.send(f"❌ Error: {result['error']}")
                    return

                data = result.get("data", {})
                status = result.get("status", "unknown")

                if user_obj:
                    user_obj.check_count += 1

                # Format response
                if status == "success":
                    guest_data = data.get("data", {})
                    embed = self.discord.Embed(
                        title=f"Account Check: {account_id}",
                        color=self.discord.Color.green()
                    )

                    embed.add_field(name="Status", value=status, inline=True)
                    embed.add_field(name="Checked", value=format_timestamp(time.time()), inline=True)

                    if guest_data:
                        nickname = guest_data.get("nickname", "N/A")
                        level = guest_data.get("level", "N/A")
                        diamonds = guest_data.get("diamonds", "N/A")
                        coins = guest_data.get("coins", "N/A")

                        embed.add_field(name="Nickname", value=nickname, inline=True)
                        embed.add_field(name="Level", value=str(level), inline=True)
                        embed.add_field(name="Diamonds", value=str(diamonds), inline=True)
                        embed.add_field(name="Coins", value=str(coins), inline=True)

                    await ctx.send(embed=embed)
                else:
                    await ctx.send(f"⚠️ Account {account_id}: {status}")

            except Exception as e:
                logger.error(f"Error checking account {account_id}: {e}")
                if user_obj:
                    user_obj.error_count += 1
                await ctx.send(f"❌ Error checking account: {e}")

    async def _handle_batch_command(self, ctx: Any, count: int = 5) -> None:
        """Handle /batch command"""
        user_id = ctx.author.id
        user_obj = self.state.users.get(user_id)

        if user_obj:
            user_obj.last_command = "batch"
            user_obj.last_command_at = time.time()

        # Check if user is banned
        if user_id in self.config.banned_user_ids:
            await ctx.send("❌ You are banned from using this bot.")
            return

        # Validate count
        if count < 1 or count > 50:
            await ctx.send("❌ Please provide a count between 1 and 50.")
            return

        # Rate limiting
        if user_id in self.state.active_checks:
            last_check = self.state.active_checks[user_id]
            if time.time() - last_check < self.config.rate_limit * 2:
                await ctx.send(f"⏳ Please wait {self.config.rate_limit * 2:.1f} seconds between batch checks.")
                return

        self.state.active_checks[user_id] = time.time()

        # Send typing indicator
        async with ctx.typing():
            try:
                # Generate random accounts
                from scripts.generate_accounts import generate_random_accounts
                accounts = generate_random_accounts(count)

                await ctx.send(f"🔍 Checking {count} accounts...")

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
                if results:
                    results_str = "\n".join(results)
                    embed = self.discord.Embed(
                        title=f"Batch Check Results ({count} accounts)",
                        description=results_str,
                        color=self.discord.Color.blue()
                    )
                    await ctx.send(embed=embed)

            except Exception as e:
                logger.error(f"Error in batch check: {e}")
                await ctx.send(f"❌ Error in batch check: {e}")

    async def _handle_stats(self, ctx: Any) -> None:
        """Handle /stats command"""
        user_id = ctx.author.id
        user_obj = self.state.users.get(user_id)

        if not user_obj:
            # Create user if not exists
            user_obj = DiscordUser(
                user_id=user_id,
                username=str(ctx.author),
                discriminator=ctx.author.discriminator if hasattr(ctx.author, 'discriminator') else "0",
                avatar=str(ctx.author.avatar) if hasattr(ctx.author, 'avatar') else None
            )
            self.state.users[user_id] = user_obj

        user_obj.last_command = "stats"
        user_obj.last_command_at = time.time()

        # Get user stats
        total_checks = user_obj.check_count
        total_errors = user_obj.error_count

        # Get database stats
        db_stats = await self.state.database.get_statistics()

        embed = self.discord.Embed(
            title=f"Statistics for {ctx.author.display_name}",
            color=self.discord.Color.purple()
        )

        embed.add_field(name="Total Checks", value=str(total_checks), inline=True)
        embed.add_field(name="Total Errors", value=str(total_errors), inline=True)
        embed.add_field(
            name="Success Rate",
            value=f"{(total_checks - total_errors) / max(total_checks, 1) * 100:.1f}%",
            inline=True
        )

        embed.add_field(name="Bot Statistics", value=f"Total Accounts in DB: {db_stats.get('total_accounts', 0)}", inline=False)
        embed.add_field(name="Bot Uptime", value=format_timestamp(self.state.started_at), inline=False)

        await ctx.send(embed=embed)

    async def _handle_me(self, ctx: Any) -> None:
        """Handle /me command"""
        user_id = ctx.author.id
        user_obj = self.state.users.get(user_id)

        if not user_obj:
            # Create user if not exists
            user_obj = DiscordUser(
                user_id=user_id,
                username=str(ctx.author),
                discriminator=ctx.author.discriminator if hasattr(ctx.author, 'discriminator') else "0",
                avatar=str(ctx.author.avatar) if hasattr(ctx.author, 'avatar') else None
            )
            self.state.users[user_id] = user_obj

        user_obj.last_command = "me"
        user_obj.last_command_at = time.time()

        is_admin = "✅ Yes" if user_obj.is_admin else "❌ No"

        embed = self.discord.Embed(
            title=f"User Profile: {ctx.author.display_name}",
            color=self.discord.Color.orange()
        )

        embed.set_thumbnail(url=ctx.author.avatar.url if hasattr(ctx.author.avatar, 'url') else None)

        embed.add_field(name="User ID", value=str(user_id), inline=True)
        embed.add_field(name="Username", value=str(ctx.author), inline=True)
        embed.add_field(name="Admin", value=is_admin, inline=True)
        embed.add_field(name="Total Checks", value=str(user_obj.check_count), inline=True)
        embed.add_field(name="Total Errors", value=str(user_obj.error_count), inline=True)
        embed.add_field(name="Last Command", value=f"/{user_obj.last_command or 'none'}", inline=True)

        await ctx.send(embed=embed)

    async def _handle_admin(self, ctx: Any) -> None:
        """Handle /admin command"""
        user_id = ctx.author.id
        user_obj = self.state.users.get(user_id)

        if not user_obj or not user_obj.is_admin:
            await ctx.send("❌ You are not an admin.")
            return

        user_obj.last_command = "admin"
        user_obj.last_command_at = time.time()

        # Get bot stats
        total_users = len(self.state.users)
        total_checks = sum(u.check_count for u in self.state.users.values())
        total_errors = sum(u.error_count for u in self.state.users.values())
        banned_users = len(self.config.banned_user_ids)

        embed = self.discord.Embed(
            title="Admin Panel",
            color=self.discord.Color.red()
        )

        embed.add_field(name="Total Users", value=str(total_users), inline=True)
        embed.add_field(name="Total Checks", value=str(total_checks), inline=True)
        embed.add_field(name="Total Errors", value=str(total_errors), inline=True)
        embed.add_field(name="Banned Users", value=str(banned_users), inline=True)
        embed.add_field(name="Bot Uptime", value=format_timestamp(self.state.started_at), inline=False)

        embed.add_field(
            name="Commands",
            value="`/broadcast <message>` - Send to all users\n`/ban <user_id>` - Ban a user\n`/unban <user_id>` - Unban a user",
            inline=False
        )

        await ctx.send(embed=embed)

    async def _handle_broadcast(self, ctx: Any, *, message: str) -> None:
        """Handle /broadcast command"""
        user_id = ctx.author.id
        user_obj = self.state.users.get(user_id)

        if not user_obj or not user_obj.is_admin:
            await ctx.send("❌ You are not an admin.")
            return

        user_obj.last_command = "broadcast"
        user_obj.last_command_at = time.time()

        if not message:
            await ctx.send("❌ Please provide a message to broadcast.")
            return

        sent_count = 0
        for user_id, user_obj in self.state.users.items():
            if user_id in self.config.banned_user_ids:
                continue

            try:
                user = self.bot.get_user(user_id)
                if user:
                    await user.send(f"📢 **Broadcast:**\n\n{message}")
                    sent_count += 1
                await asyncio.sleep(0.1)  # Rate limit
            except Exception as e:
                logger.error(f"Failed to send broadcast to {user_id}: {e}")

        await ctx.send(f"✅ Broadcast sent to {sent_count} users")

    async def _handle_ban(self, ctx: Any, user_id: int) -> None:
        """Handle /ban command"""
        author_id = ctx.author.id
        user_obj = self.state.users.get(author_id)

        if not user_obj or not user_obj.is_admin:
            await ctx.send("❌ You are not an admin.")
            return

        user_obj.last_command = "ban"
        user_obj.last_command_at = time.time()

        self.config.banned_user_ids.add(user_id)
        await ctx.send(f"✅ User {user_id} banned")

    async def _handle_unban(self, ctx: Any, user_id: int) -> None:
        """Handle /unban command"""
        author_id = ctx.author.id
        user_obj = self.state.users.get(author_id)

        if not user_obj or not user_obj.is_admin:
            await ctx.send("❌ You are not an admin.")
            return

        user_obj.last_command = "unban"
        user_obj.last_command_at = time.time()

        self.config.banned_user_ids.discard(user_id)
        await ctx.send(f"✅ User {user_id} unbanned")

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _handle_quick_check(self, message: Any, account_id: str) -> None:
        """Handle quick check from direct message"""
        user_id = message.author.id
        user_obj = self.state.users.get(user_id)

        # Check if user is banned
        if user_id in self.config.banned_user_ids:
            return

        # Create user if not exists
        if not user_obj:
            user_obj = DiscordUser(
                user_id=user_id,
                username=str(message.author),
                discriminator=message.author.discriminator if hasattr(message.author, 'discriminator') else "0",
                avatar=str(message.author.avatar) if hasattr(message.author, 'avatar') else None
            )
            self.state.users[user_id] = user_obj

        user_obj.last_command = "quick_check"
        user_obj.last_command_at = time.time()

        # Rate limiting
        if user_id in self.state.active_checks:
            last_check = self.state.active_checks[user_id]
            if time.time() - last_check < self.config.rate_limit:
                await message.channel.send(f"⏳ Please wait {self.config.rate_limit:.1f} seconds between checks.")
                return

        self.state.active_checks[user_id] = time.time()

        # Send typing indicator
        async with message.channel.typing():
            try:
                result = await self._check_account(account_id)
                
                if result.get("error"):
                    if user_obj:
                        user_obj.error_count += 1
                    await message.channel.send(f"❌ Error: {result['error']}")
                    return

                data = result.get("data", {})
                status = result.get("status", "unknown")

                if user_obj:
                    user_obj.check_count += 1

                if status == "success":
                    await message.channel.send(f"✅ Account {account_id}: {status}")
                else:
                    await message.channel.send(f"⚠️ Account {account_id}: {status}")

            except Exception as e:
                logger.error(f"Error checking account {account_id}: {e}")
                if user_obj:
                    user_obj.error_count += 1
                await message.channel.send(f"❌ Error: {e}")

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
            region="discord",
            source="discord_bot"
        )

        return {
            "account_id": account_id,
            "status": "success",
            "data": guest_info.to_dict(),
            "cached": False,
            "checked_at": format_timestamp(time.time())
        }


# =============================================================================
# Main Entry Point
# =============================================================================

async def run_discord_bot() -> None:
    """Run the Discord bot"""
    # Load configuration from environment
    token = os.getenv("DISCORD_TOKEN")
    guild_id_str = os.getenv("DISCORD_GUILD_ID")
    api_url = os.getenv("API_URL", "http://localhost:5000")

    if not token:
        logger.error("DISCORD_TOKEN environment variable not set")
        return

    guild_id = None
    if guild_id_str:
        try:
            guild_id = int(guild_id_str)
        except ValueError:
            logger.error("Invalid DISCORD_GUILD_ID")
            return

    config = DiscordBotConfig(
        token=token,
        guild_id=guild_id,
        api_url=api_url
    )

    bot = DiscordBot(config)
    await bot.initialize()
    await bot.start()


def run_discord_bot_sync() -> None:
    """Run the Discord bot synchronously"""
    asyncio.run(run_discord_bot())


if __name__ == "__main__":
    run_discord_bot_sync()
