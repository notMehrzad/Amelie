"""/balance command."""

from __future__ import annotations

__all__ = []

from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.filters import Command

from arg_parser import parse_args
from core.bank import CURRENCY_NAME, create_bank_account, get_bank_account
from core.help_data_constants import BALANCE_HELP

if TYPE_CHECKING:
    from aiogram.types import Message

ROUTER = Router(name=__name__)


@ROUTER.message(
    Command(BALANCE_HELP.name, *BALANCE_HELP.aliases, ignore_case=True),
)
@parse_args
async def balance(message: Message) -> None:
    if message.from_user is None:
        return

    # Fetch user's bank account.
    account = await get_bank_account(message.from_user.id)
    # Raise an error if user's bank account can't be fetched.
    if account is None:
        account = await create_bank_account(user_id=message.from_user.id)

    if message.from_user.username is not None:
        mention = f"@{message.from_user.username}"
    else:
        mention = message.from_user.mention_html()

    # Send result embed.
    msg = f"{mention} 's Balance\n\n{account.balance} {CURRENCY_NAME}s"
    _ = await message.reply(msg, parse_mode="HTML")
