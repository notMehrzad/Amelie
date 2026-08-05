"""/daily command."""

from __future__ import annotations

__all__ = []

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.filters import Command

from arg_parser import parse_args
from core.bank import CURRENCY_NAME, create_bank_account, get_bank_account
from core.help_data_constants import DAILY_HELP
from core.utils import format_timedelta

if TYPE_CHECKING:
    from aiogram.types import Message

DAILY_AMOUNT = 500
DAILY_COOLDOWN = 24 * 60  # minutes

ROUTER = Router(name=__name__)


@ROUTER.message(Command(DAILY_HELP.name, *DAILY_HELP.aliases, ignore_case=True))
@parse_args
async def daily(message: Message) -> None:
    if message.from_user is None:
        return

    # Fetch user's bank account.
    account = await get_bank_account(message.from_user.id)

    # Create a bank account if user hasn't one.
    if not account:
        account = await create_bank_account(user_id=message.from_user.id)

    now = datetime.now(timezone.utc)
    # Raise an error if user wants to claim daily within 24 hours.
    if (
        account.last_daily_date
        and account.last_daily_date + timedelta(minutes=DAILY_COOLDOWN) > now
    ):
        _ = await message.reply(
            "You must wait `"
            + format_timedelta(
                account.last_daily_date + timedelta(minutes=DAILY_COOLDOWN) - now,
            )
            + "` to claim your next Daily reward.",
        )
        return

    # Deposit daily reward.
    _ = await account.deposit(DAILY_AMOUNT, "Daily reward.")

    # Update last daily date of account.
    await account.update_last_daily_date()

    # Send result.
    msg = (
        "Daily Reward !"
        "\n\nYou have claimed your Daily reward for today."
        f"\nCurrent balance: *{account.balance} {CURRENCY_NAME}*"
    )
    _ = await message.reply(msg)
