"""tarot command."""

from __future__ import annotations

__all__ = []

from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.filters import Command

from core.help_data_constants import TAROT_HELP
from core.tarot import MAX_DRAW_NUMBER, TarotCard
from telegram_bot.arg_parser import parse_args

if TYPE_CHECKING:
    from aiogram.types import Message

ROUTER = Router(name=__name__)


@ROUTER.message(
    Command(TAROT_HELP.name, *TAROT_HELP.aliases, ignore_case=True),
)
@parse_args
async def tarot(message: Message, number: int | str | None = 1) -> None:
    # Raise an error if user enters an invalid draw number.
    if not isinstance(number, int):
        await message.reply("Enter a valid number.")
        return

    # Raise an error if user enters a negative draw number.
    if number < 0:
        await message.reply("Draw number can not be negative.")
        return

    # Raise an error if user enters zero draw number.
    if number == 0:
        await message.reply("Draw number can not be zero.")
        return

    # Raise an error if user wants to draw more than allowed maximum draw number.
    if number > MAX_DRAW_NUMBER:
        await message.reply(f"Maximum draw number is {MAX_DRAW_NUMBER}.")
        return

    # Draw the cards and send the result.
    await message.reply(" | ".join(TarotCard.draw(number)))
