"""rolldice command."""

from __future__ import annotations

__all__ = []

from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.filters import Command

from core.dice import (
    MAX_DICE_COUNT,
    MAX_DIE_SIDES,
    MIN_DIE_SIDES,
    Dice,
    parse_dice_expression,
)
from core.help_data_constants import ROLLDICE_HELP
from telegram_bot.arg_parser import parse_args

if TYPE_CHECKING:
    from aiogram.types import Message

ROUTER = Router(name=__name__)


@ROUTER.message(Command(ROLLDICE_HELP.name, *ROLLDICE_HELP.aliases, ignore_case=True))
@parse_args
async def rolldice(message: Message, dice_expression: str = "1d6") -> None:
    # Parse expression.
    parsed_expression = parse_dice_expression(dice_expression)
    # Raise an error if entered expression is invalid and can't be parsed.
    if parsed_expression is None:
        await message.reply("You must enter a valid dice expression like <i>3d20</i>.")
        return
    count, sides = parsed_expression

    # Raise an error if count is less than minimum dice count.
    if count < 1:
        await message.reply("You must roll at least 1 die.")
        return
    # Raise an error if count is more than maximum dice count.
    if count > MAX_DICE_COUNT:
        await message.reply(f"The maximum number of dice to roll is {MAX_DICE_COUNT}")
        return

    # Raise an error if side is less than minimum die side.
    if sides < MIN_DIE_SIDES:
        await message.reply(f"A die can not have less than {MIN_DIE_SIDES} sides.")
        return
    # Raise an error if sides are more than maximum die sides.
    if sides > MAX_DIE_SIDES:
        await message.reply(f"Maximum number of die sides is {MAX_DIE_SIDES}.")
        return

    # Throw a dice animation if it's 1d6.
    if count == 1 and sides == 6:
        await message.reply_dice(emoji="🎲")
        return

    # Create the die.
    die = Dice(sides)

    # Roll dice and save the result.
    result, rolls = die.roll(count)

    if count == 1:
        result_string = f"🎲 <b>{count}d{sides}</b> -> <b>{result}</b>"
    else:
        result_string = (
            f"🎲 <b>{count}d{sides}</b> -> <b>{result}</b>"
            f"\n\nRolls: {', '.join(map(str, rolls))}"
            f"\nTotal: <b>{result}</b>"
        )

    # Send result.
    await message.reply(result_string)
