"""flipcoin command."""

from __future__ import annotations

__all__ = []

import secrets
from typing import final

import discord
from discord import app_commands
from discord.ext import commands

from core.help_data_constants import FLIPCOIN_HELP
from core.log_handler import setup_logger

OPTIONS = ("Heads", "Tails")

logger = setup_logger(__name__)


@final
class FlipCoin(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name=FLIPCOIN_HELP.name, **FLIPCOIN_HELP.kwargs)
    async def flipcoin(self, ctx: commands.Context[commands.Bot]) -> None:
        # Flip the coin.
        result = secrets.choice(OPTIONS)

        # Send result.
        await ctx.reply(f"{result}.")

    @flipcoin.error
    async def flipcoin_error(
        self,
        ctx: commands.Context[commands.Bot],
        error: commands.CommandError,
    ) -> None:
        logger.error("❌ Something went wrong with flipcoin command:", exc_info=error)
        await ctx.reply("Something went wrong with **flipcoin**.")

    # flipcoin slash command
    @app_commands.command(
        name=FLIPCOIN_HELP.name,
        description=FLIPCOIN_HELP.brief,
        extras=FLIPCOIN_HELP.extras,
    )
    async def slash_flipcoin(self, interaction: discord.Interaction) -> None:
        # Flip the coin.
        result = secrets.choice(OPTIONS)

        # Send result.
        await interaction.response.send_message(f"{result}.")

    @slash_flipcoin.error
    async def slash_flipcoin_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        logger.error("❌ Something went wrong with /flipcoin command:", exc_info=error)
        try:
            await interaction.response.send_message(
                "Something went wrong with **flipcoin**.",
                ephemeral=True,
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "Something went wrong with **flipcoin**.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FlipCoin(bot))
