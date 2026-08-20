"""rolldice command."""

from __future__ import annotations

__all__ = []

from typing import final

import discord
from discord import app_commands
from discord.ext import commands

from core.dice import (
    MAX_DICE_COUNT,
    MAX_DIE_SIDES,
    MIN_DIE_SIDES,
    Dice,
    parse_dice_expression,
)
from core.help_data_constants import ROLLDICE_HELP
from core.log_handler import setup_logger

logger = setup_logger(__name__)


@final
class RollDice(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name=ROLLDICE_HELP.name, **ROLLDICE_HELP.kwargs)
    async def rolldice(
        self,
        ctx: commands.Context[commands.Bot],
        dice_expression: str = "1d6",
    ) -> None:
        # Parse expression.
        parsed_expression = parse_dice_expression(dice_expression)
        # Raise an error if entered expression is invalid and can't be parsed.
        if parsed_expression is None:
            await ctx.reply("You must enter a valid dice expression like `3d20`.")
            return
        count, sides = parsed_expression

        # Raise an error if count is less than minimum dice count.
        if count < 1:
            await ctx.reply("You must roll at least 1 die.")
            return
        # Raise an error if count is more than maximum dice count.
        if count > MAX_DICE_COUNT:
            await ctx.reply(f"The maximum number of dice to roll is {MAX_DICE_COUNT}")
            return

        # Raise an error if side is less than minimum die side.
        if sides < MIN_DIE_SIDES:
            await ctx.reply(f"A die can not have less than {MIN_DIE_SIDES} sides.")
            return
        # Raise an error if sides are more than maximum die sides.
        if sides > MAX_DIE_SIDES:
            await ctx.reply(f"Maximum number of die sides is {MAX_DIE_SIDES}.")
            return

        # Create the die.
        die = Dice(sides)

        # Roll dice and save the result.
        result, rolls = die.roll(count)

        if count == 1:
            result_string = f"🎲 **{count}d{sides}** -> **{result}**"
        else:
            result_string = (
                f"🎲 **{count}d{sides}** -> **{result}**"
                f"\n\nRolls: {', '.join(map(str, rolls))}"
                f"\nTotal: **{result}**"
            )

        # Send result.
        await ctx.reply(result_string)

    @rolldice.error
    async def rolldice_error(
        self,
        ctx: commands.Context[commands.Bot],
        error: commands.CommandError,
    ) -> None:
        logger.error("❌ Something went wrong with rolldice command:", exc_info=error)
        await ctx.reply("Something went wrong with **rolldice**.")

    # rolldice slash command
    @app_commands.command(
        name=ROLLDICE_HELP.name,
        description=ROLLDICE_HELP.brief,
        extras=ROLLDICE_HELP.extras,
    )
    @app_commands.describe(dice="The dice to roll. Format: d6, 2d6, or 6")
    async def slash_rolldice(
        self,
        interaction: discord.Interaction,
        dice: str = "1d6",
    ) -> None:
        # Parse expression.
        parsed_expression = parse_dice_expression(dice)
        # Raise an error if entered expression is invalid and can't be parsed.
        if parsed_expression is None:
            await interaction.response.send_message(
                "You must enter a valid dice expression like `3d20`.",
                ephemeral=True,
            )
            return
        count, sides = parsed_expression

        # Raise an error if count is less than minimum dice count.
        if count < 1:
            await interaction.response.send_message(
                "You must roll at least 1 die.",
                ephemeral=True,
            )
            return
        # Raise an error if count is more than maximum dice count.
        if count > MAX_DICE_COUNT:
            await interaction.response.send_message(
                f"The maximum number of dice to roll is {MAX_DICE_COUNT}",
                ephemeral=True,
            )
            return

        # Raise an error if side is less than minimum die side.
        if sides < MIN_DIE_SIDES:
            await interaction.response.send_message(
                f"A die can not have less than {MIN_DIE_SIDES} sides.",
                ephemeral=True,
            )
            return
        # Raise an error if sides are more than maximum die sides.
        if sides > MAX_DIE_SIDES:
            await interaction.response.send_message(
                f"Maximum number of die sides is {MAX_DIE_SIDES}.",
                ephemeral=True,
            )
            return

        # Creat the die.
        die = Dice(sides)

        # Roll dice and save the result.
        result, rolls = die.roll(count)

        if count == 1:
            result_string = f"🎲 **{count}d{sides}** -> **{result}**"
        else:
            result_string = (
                f"🎲 **{count}d{sides}** -> **{result}**"
                f"\n\nRolls: {', '.join(map(str, rolls))}"
                f"\nTotal: **{result}**"
            )

        # Send result.
        await interaction.response.send_message(result_string)

    @slash_rolldice.error
    async def slash_rolldice_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        logger.error("❌ Something went wrong with /rolldice command:", exc_info=error)
        try:
            await interaction.response.send_message(
                "Something went wrong with **rolldice**.",
                ephemeral=True,
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "Something went wrong with **rolldice**.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RollDice(bot))
