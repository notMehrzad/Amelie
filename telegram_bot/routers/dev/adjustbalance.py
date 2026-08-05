"""/adjustbalance command."""

from __future__ import annotations

__all__ = []


from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.filters import Command

from arg_parser import parse_args
from core.bank import get_bank_account
from core.help_data_constants import ADJUSTBALANCE_HELP

if TYPE_CHECKING:
    from aiogram.types import Message

ROUTER = Router(name=__name__)


@ROUTER.message(
    Command(
        ADJUSTBALANCE_HELP.name,
        *ADJUSTBALANCE_HELP.aliases,
        ignore_case=True,
    ),
)
@parse_args
async def balance(
    message: Message,
    subcommand: str | None,
    user_id: int | str | None,
    amount: int | str | None,
    memo: str | None = None,
) -> None:
    if message.from_user is None:
        return

    if subcommand is None:
        await message.reply("You need to enter a subcommand.")
        return
    subcommand = subcommand.lower()
    if subcommand not in ADJUSTBALANCE_HELP.subcommands:
        await message.reply("Enter a valid subcommand.")
        return

    if user_id is None:
        await message.reply("You need to enter a target user ID.")
        return

    if not isinstance(user_id, int):
        await message.reply("Enter a valid user ID.")
        return

    account = await get_bank_account(user_id)
    if account is None:
        await message.reply(
            "Account of the user with specified user ID couldn't be fetched.",
        )
        return

    if amount is None:
        await message.reply("You need to enter an amount.")
        return
    if not isinstance(amount, int):
        await message.reply("Enter a valid integer amount.")
        return
    if amount < 0:
        await message.reply("Enter a positive integer amount.")
        return

    if subcommand == "deposit":
        await account.deposit(amount, memo)

    elif subcommand == "withdraw":
        await account.withdraw(amount, memo)

    elif subcommand == "set":
        await account.set_balance(amount, memo)

    await message.reply("Done.")
