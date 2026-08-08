"""ping command."""

from __future__ import annotations

__all__ = []

import asyncio
import time
from typing import final

import discord
from discord import app_commands
from discord.ext import commands

from core.help_data_constants import PING_HELP
from core.log_handler import setup_logger

PING_NUMBER = 4  # Number of attempts to get ping

COLOR_STATUS: dict[str, int] = {"great": 100, "good": 200, "weak": 400}

logger = setup_logger(__name__)


@final
class Ping(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="ping", **PING_HELP.kwargs)
    async def ping(self, ctx: commands.Context[commands.Bot]) -> None:
        # Define a list to store pings.
        pings: list[float] = []

        # Send the initial message.
        msg = await ctx.reply("pinging...")

        # Get bot's web socket latency.
        web_socket = self.bot.latency * 1000

        # Start pinging.
        for i in range(PING_NUMBER):
            try:
                start = time.perf_counter()
                await msg.edit(content=f"ping {i + 1}..")
                end = time.perf_counter()

            # Delete the result if user deletes the ping message.
            except discord.NotFound:
                pings = []
                return

            # Calculate message latency.
            msg_latency = (end - start) * 1000

            # Append the result.
            pings.append(msg_latency)

            await asyncio.sleep(0.1)

        if pings:
            # Get REST latency.
            average_ping = round((sum(pings) / PING_NUMBER), 2)
            min_ping = round(min(pings), 2)
            max_ping = round(max(pings), 2)
        else:
            average_ping = min_ping = max_ping = None

        # Define color status based on ws ping strength.
        if web_socket <= COLOR_STATUS["great"]:
            color = discord.Color.from_str("#00ff59")  # Green

        elif web_socket <= COLOR_STATUS["good"]:
            color = discord.Color.from_str("#ffff00")  # Yellow

        elif web_socket <= COLOR_STATUS["weak"]:
            color = discord.Color.from_str("#ffab00")  # Orange

        else:
            color = discord.Color.from_str("#ff3800")  # Red

        result_embed = discord.Embed(
            color=color,
            title="Pong! 🏓",
            description=(
                f"📡 WebSocket: `{web_socket:.2f} ms`"
                f"\n🌐 REST: `{average_ping:.2f} ms`"
                f"\n\nMin: `{min_ping:.2f} ms` | Max: `{max_ping:.2f} ms`"
            ),
            timestamp=discord.utils.utcnow(),
        ).set_footer(text=f"requested by {ctx.author.name}")
        # Send result embed.
        await msg.edit(content=None, embed=result_embed)

    @ping.error
    async def ping_error(
        self,
        ctx: commands.Context[commands.Bot],
        error: commands.CommandError,
    ) -> None:
        logger.error("❌ Something went wrong with ping command:", exc_info=error)
        await ctx.reply("Something went wrong with **ping**.")

    # ping slash command
    @app_commands.command(
        name="ping",
        description=PING_HELP.brief,
        extras=PING_HELP.extras,
    )
    @app_commands.describe(hidden="Whether only you can see the response.")
    async def slash_ping(
        self,
        interaction: discord.Interaction,
        *,
        hidden: bool = False,
    ) -> None:
        # Define a list to store pings.
        pings: list[float] = []

        # Send the initial message.
        await interaction.response.send_message("pinging...", ephemeral=hidden)

        # Get bot's web socket latency.
        web_socket = self.bot.latency * 1000

        # Start pinging.
        for i in range(PING_NUMBER):
            try:
                start = time.perf_counter()
                await interaction.edit_original_response(content=f"ping {i + 1}..")
                end = time.perf_counter()

            # Delete the result if user deletes the ping message.
            except discord.NotFound:
                pings = []
                return

            # Calculate message latency.
            msg_latency = (end - start) * 1000

            # Append the result.
            pings.append(msg_latency)

            await asyncio.sleep(0.1)

        if pings:
            # Get REST latency.
            average_ping = round((sum(pings) / PING_NUMBER), 2)
            min_ping = round(min(pings), 2)
            max_ping = round(max(pings), 2)
        else:
            average_ping = min_ping = max_ping = None

        # Define color status based on ws ping strength.
        if web_socket <= COLOR_STATUS["great"]:
            color = discord.Color.from_str("#00ff59")  # Green

        elif web_socket <= COLOR_STATUS["good"]:
            color = discord.Color.from_str("#ffff00")  # Yellow

        elif web_socket <= COLOR_STATUS["weak"]:
            color = discord.Color.from_str("#ffab00")  # Orange

        else:
            color = discord.Color.from_str("#ff3800")  # Red

        result_embed = discord.Embed(
            color=color,
            title="Pong! 🏓",
            description=(
                f"📡 WebSocket: `{web_socket:.2f} ms`"
                f"\n🌐 REST: `{average_ping:.2f} ms`"
                f"\n\nMin: `{min_ping:.2f} ms` | Max: `{max_ping:.2f} ms`"
            ),
            timestamp=discord.utils.utcnow(),
        ).set_footer(text=f"requested by {interaction.user.name}")
        # Send result embed.
        await interaction.edit_original_response(content=None, embed=result_embed)

    @slash_ping.error
    async def slash_ping_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        logger.error("❌ Something went wrong with /ping command:", exc_info=error)
        try:
            await interaction.response.send_message(
                "Something went wrong with **ping**.",
                ephemeral=True,
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "Something went wrong with **ping**.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Ping(bot))
