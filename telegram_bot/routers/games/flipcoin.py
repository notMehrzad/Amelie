"""flipcoin command."""

from __future__ import annotations

__all__ = []

import secrets
from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.filters import Command

from core.help_data_constants import FLIPCOIN_HELP
from telegram_bot.arg_parser import parse_args

if TYPE_CHECKING:
    from aiogram.types import Message

OPTIONS = ("Heads", "Tails")

ROUTER = Router(name=__name__)


@ROUTER.message(Command(FLIPCOIN_HELP.name, *FLIPCOIN_HELP.aliases, ignore_case=True))
@parse_args
async def flipcoin(message: Message) -> None:
    # Flip the coin.
    result = secrets.choice(OPTIONS)

    # Send result.
    await message.reply(result)
