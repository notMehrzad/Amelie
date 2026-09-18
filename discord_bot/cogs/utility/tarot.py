"""tarot command."""

from __future__ import annotations

__all__ = []

from typing import final

import discord
from discord import app_commands
from discord.ext import commands

from core.help_data_constants import TAROT_HELP
from core.tarot import MAX_DRAW_NUMBER, TarotCard


@final
class Tarot(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name=TAROT_HELP.name, **TAROT_HELP.kwargs)
    async def tarot(
        self,
        ctx: commands.Context[commands.Bot],
        number: int | str | None = 1,
    ) -> None:
        # Raise an error if user enters an invalid draw number.
        if not isinstance(number, int):
            await ctx.reply("Enter a valid number.")
            return

        # Raise an error if user enters a negative draw number.
        if number < 0:
            await ctx.reply("Draw number can not be negative.")
            return

        # Raise an error if user enters zero draw number.
        if number == 0:
            await ctx.reply("Draw number can not be zero.")
            return

        # Raise an error if user wants to draw more than allowed maximum draw number.
        if number > MAX_DRAW_NUMBER:
            await ctx.reply(f"Maximum draw number is {MAX_DRAW_NUMBER}.")
            return

        # Draw the cards and send the result.
        await ctx.reply(" | ".join(TarotCard.draw(number)))

    # tarot slash command
    @app_commands.command(
        name=TAROT_HELP.name,
        description=TAROT_HELP.brief,
        extras=TAROT_HELP.extras,
    )
    @app_commands.describe(number="Number of cards to draw from tarot deck.")
    async def slash_tarot(
        self,
        interaction: discord.Interaction,
        number: int = 1,
    ) -> None:
        # Raise an error if user enters a negative draw number.
        if number < 0:
            await interaction.response.send_message(
                "Draw number can not be negative.",
                ephemeral=True,
            )
            return

        # Raise an error if user enters zero draw number.
        if number == 0:
            await interaction.response.send_message(
                "Draw number can not be zero.",
                ephemeral=True,
            )
            return

        # Raise an error if user wants to draw more than allowed maximum draw number.
        if number > MAX_DRAW_NUMBER:
            await interaction.response.send_message(
                f"Maximum draw number is {MAX_DRAW_NUMBER}.",
                ephemeral=True,
            )
            return

        # Draw the cards and send the result.
        await interaction.response.send_message(" | ".join(TarotCard.draw(number)))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Tarot(bot))
