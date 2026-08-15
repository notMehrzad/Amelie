"""coinflip command."""

from __future__ import annotations

__all__ = []

import secrets
from typing import final

import discord
from discord import app_commands
from discord.ext import commands

from core.help_data_constants import COINFLIP_HELP
from core.log_handler import setup_logger

OPTIONS = ("Heads", "Tails")

logger = setup_logger(__name__)


@final
class CoinFlip(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="coinflip", **COINFLIP_HELP.kwargs)
    async def coinflip(self, ctx: commands.Context[commands.Bot]) -> None:
        # Flip the coin.
        result = secrets.choice(OPTIONS)

        # Send result.
        await ctx.reply(f"{result}.")

    @coinflip.error
    async def coinflip_error(
        self,
        ctx: commands.Context[commands.Bot],
        error: commands.CommandError,
    ) -> None:
        logger.error("❌ Something went wrong with coinflip command:", exc_info=error)
        await ctx.reply("Something went wrong with **coinflip**.")

    # coinflip slash command
    @app_commands.command(
        name="coinflip",
        description=COINFLIP_HELP.brief,
        extras=COINFLIP_HELP.extras,
    )
    async def slash_coinflip(self, interaction: discord.Interaction) -> None:
        # Flip the coin.
        result = secrets.choice(OPTIONS)

        # Send result.
        await interaction.response.send_message(f"{result}.")

    @slash_coinflip.error
    async def slash_coinflip_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        logger.error("❌ Something went wrong with /coinflip command:", exc_info=error)
        try:
            await interaction.response.send_message(
                "Something went wrong with **coinflip**.",
                ephemeral=True,
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "Something went wrong with **coinflip**.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CoinFlip(bot))
