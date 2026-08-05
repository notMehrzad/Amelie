import asyncio
import time

import discord
from discord import app_commands
from discord.ext import commands

from cogs.utility.help import Help
from core.log_handler import setup_logger

logger = setup_logger(__name__)

pingNumbers = 4  # number of attempt to get pings


class Ping(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    Help = Help(
        category=Help.Category.Utility,
        is_dm_only=False,
        is_server_only=False,
        subcommands=None,
        permissions=None,
        help_=(
            "Checks Amelies conenction speed by measuring WebSocket Latency (which is the delay between bots server and Discord Gateway) and Bot Latency"
            "\n(which is the time it takes Amélie to send a message and recieve a response)."
        ),
        brief="Pings Amélie.",
        usage=None,
        aliases=None,
    )

    @commands.command(name="ping", **Help.to_kwargs)
    async def ping(self, ctx: commands.Context[commands.Bot]):
        pings: list[float] | None = []  # stores pings results
        pingNumbers = 4

        msg = await ctx.reply("pinging...")  # initial message

        ws = self.bot.latency * 1000  # getting websocket latency
        # starts pinging n times
        for i in range(pingNumbers):
            try:
                start = time.perf_counter()
                await msg.edit(content=f"ping {i + 1}..")
                end = time.perf_counter()
            # if user deletes the pings message
            except discord.NotFound:
                pings = None
                break

            msg_latency = (end - start) * 1000
            pings.append(msg_latency)  # stores the nth ping in a list
            await asyncio.sleep(0.1)

        if pings:
            avg = round(sum(pings) / pingNumbers, 2)  # getting REST latency
            minping = round(min(pings), 2)
            maxping = round(max(pings), 2)
        else:
            avg = minping = maxping = None

        # defining color based on ws ping strength
        if ws <= 100:
            color = discord.Color.from_str("#00ff59")  # green
        elif ws <= 200:
            color = discord.Color.from_str("#ffff00")  # yellow
        elif ws <= 400:
            color = discord.Color.from_str("#ffab00")  # orange
        else:
            color = discord.Color.from_str("#ff3800")  # red

        resultEmbed = discord.Embed(
            title="Pong! 🏓",
            description=(
                f"📡 WebSocket: `{ws:.2f} ms`"
                + (f"\n🌐 REST: `{avg:.2f} ms`" if pings else f"🌐 REST: Failed")
                + (
                    f"\n\nMin: `{minping:.2f} ms` | Max: `{maxping:.2f} ms`"
                    if pings
                    else ""
                )
            ),
            color=color,
            timestamp=discord.utils.utcnow(),
        ).set_footer(text=f"requested by {ctx.author.name}")
        try:
            await msg.edit(content=None, embed=resultEmbed)  # sends the final results
        # if user deletes the pings message
        except discord.NotFound:
            await ctx.reply(content=None, embed=resultEmbed)

    @ping.error
    async def ping_error(self, ctx: commands.Context[commands.Bot], error: Exception):
        logger.exception(f"❌ something went wrong with ping command:")
        await ctx.reply("something went wrong with **ping**.")

    # ping slash command
    @app_commands.command(name="ping", description=Help.brief, extras=Help.extras)
    @app_commands.describe(
        hidden="Whether the result should be visible only to you or not."
    )
    async def slashPing(self, interaction: discord.Interaction, hidden: bool = False):
        pings: list[float] | None = []  # stores pings results

        await interaction.response.send_message(
            "pinging...", ephemeral=hidden
        )  # initial message

        ws = self.bot.latency * 1000  # getting websocket latency
        # starts pinging n times
        for i in range(pingNumbers):
            try:
                start = time.perf_counter()
                await interaction.edit_original_response(content=f"ping {i + 1}..")
                end = time.perf_counter()
            # if user deletes the pings message
            except discord.NotFound:
                pings = None
                break

            msg_latency = (end - start) * 1000
            pings.append(msg_latency)  # stores the nth ping in a list
            await asyncio.sleep(0.1)
        if pings:
            avg = round(sum(pings) / pingNumbers, 2)  # getting REST latency
            minping = round(min(pings), 2)
            maxping = round(max(pings), 2)
        else:
            avg = minping = maxping = None

        # defining color based on ws ping strength
        if ws <= 100:
            color = discord.Color.from_str("#00ff59")  # green
        elif ws <= 200:
            color = discord.Color.from_str("#ffff00")  # yellow
        elif ws <= 400:
            color = discord.Color.from_str("#ffab00")  # orange
        else:
            color = discord.Color.from_str("#ff3800")  # red

        resultEmbed = discord.Embed(
            title="Pong! 🏓",
            description=(
                f"📡 WebSocket: `{ws:.2f} ms`"
                + (f"\n🌐 REST: `{avg:.2f} ms`" if pings else f"🌐 REST: Failed")
                + (
                    f"\n\nMin: `{minping:.2f} ms` | Max: `{maxping:.2f} ms`"
                    if pings
                    else ""
                )
            ),
            color=color,
            timestamp=discord.utils.utcnow(),
        ).set_footer(text=f"requested by {interaction.user.name}")
        try:
            await interaction.edit_original_response(
                content=None, embed=resultEmbed
            )  # sends the final results
        # if user deletes the pings message
        except discord.NotFound:
            await interaction.followup.send(embed=resultEmbed, ephemeral=hidden)

    @slashPing.error
    async def slashPing_error(self, interaction: discord.Interaction, error: Exception):
        logger.exception(f"❌ something went wrong with /ping command:")
        try:
            await interaction.response.send_message(
                "something went wrong with **ping**.", ephemeral=True
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "something went wrong with **ping**.", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Ping(bot))
