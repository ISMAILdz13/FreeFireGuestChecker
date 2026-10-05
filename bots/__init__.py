"""
Bots module for Free Fire Guest Account Checker
Contains Telegram and Discord bot implementations
"""

from __future__ import annotations

__all__ = [
    "telegram_bot",
    "discord_bot",
    "run_telegram_bot",
    "run_discord_bot"
]

from . import telegram_bot, discord_bot
from .telegram_bot import run_telegram_bot
from .discord_bot import run_discord_bot
