"""choose command."""

from __future__ import annotations

__all__ = []

import random
from typing import final

import discord
from discord import app_commands
from discord.ext import commands

from core.help_data_constants import CHOOSE_HELP
from core.log_handler import setup_logger

MIN_OPTIONS = 2

logger = setup_logger(__name__)


@final
class Choose(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="choose", **CHOOSE_HELP.kwargs)
    async def choose(
        self,
        ctx: commands.Context[commands.Bot],
        count: int = 1,
        *,
        raw_options: str | None,
    ) -> None:
        # Raise an error if user enters no options.
        if raw_options is None:
            await ctx.reply('You must enter your options separated with "|".')
            return

        options = [
            option.strip() for option in raw_options.split("|") if option.strip()
        ]

        # Raise an error if the number of options is less than 2.
        if len(options) < MIN_OPTIONS:
            await ctx.reply('You must enter at least two options separated with "|".')
            return

        # Raise an error if user wants to choose more than number of options.
        if count >= len(options):
            await ctx.reply(
                "You can't choose greater than or equal to the number of options.",
            )
            return

        # Choose a random option.
        choice = random.sample(options, count)

        # Send the result.
        await ctx.reply(f"I'd go with: {'and'.join(choice)}")

    @choose.error
    async def choose_error(
        self,
        ctx: commands.Context[commands.Bot],
        error: commands.CommandError,
    ) -> None:
        logger.error("❌ Something went wrong with choose command:", exc_info=error)
        await ctx.reply("something went wrong with **choose**.")

    # choose slash command
    @app_commands.command(
        name="choose",
        description=CHOOSE_HELP.brief,
        extras=CHOOSE_HELP.extras,
    )
    @app_commands.describe(
        options='Options to choose from, separated with " | ".',
        count="Number of choices to make.",
    )
    async def slash_choose(
        self,
        interaction: discord.Interaction,
        options: str,
        count: int = 1,
    ) -> None:
        options_list = [
            option.strip() for option in options.split("|") if option.strip()
        ]

        # Raise an error if the number of options is less than 2.
        if len(options_list) < MIN_OPTIONS:
            await interaction.response.send_message(
                'You must enter at least two options separated with "|".',
                ephemeral=True,
            )
            return

        # Raise an error if user wants to choose more than number of options.
        if count >= len(options_list):
            await interaction.response.send_message(
                "You can't choose greater than or equal to the number of options.",
                ephemeral=True,
            )
            return

        # Choose a random option.
        choice = random.sample(options_list, count)

        # Send the result.
        await interaction.response.send_message(f"I'd go with: {'and'.join(choice)}")

    @slash_choose.error
    async def slash_choose_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        logger.error("❌ Something went wrong with /choose command:", exc_info=error)
        try:
            await interaction.response.send_message(
                "Something went wrong with **choose**.",
                ephemeral=True,
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "Something went wrong with **choose**.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Choose(bot))
