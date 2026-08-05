import random

import discord
from discord import app_commands
from discord.ext import commands

from cogs.utility.help import Help
from core.log_handler import setup_logger

logger = setup_logger(__name__)


class CoinFlip(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    Help = Help(
        category=Help.Category.Games,
        is_dm_only=False,
        is_server_only=False,
        subcommands=None,
        permissions=None,
        help_=None,
        brief="Flips a coin.",
        usage=None,
        aliases=["cf", "coinf"],
    )

    @commands.command(name="coinflip", **Help.to_kwargs)
    async def coinflip(self, ctx: commands.Context[commands.Bot]):
        result = random.choice(("Heads", "Tails"))  # flips the coin
        await ctx.reply(result + ".")  # sends the result

    @coinflip.error
    async def coinflip_error(
        self, ctx: commands.Context[commands.Bot], error: Exception
    ):
        logger.exception(f"❌ something went wrong with coinflip command:")
        await ctx.reply("something went wrong with **coinflip**.")

    # coinflip slash command
    @app_commands.command(name="coinflip", description=Help.brief, extras=Help.extras)
    async def slashCoinflip(self, interaction: discord.Interaction):
        result = random.choice(("Heads", "Tails"))  # flips the coin
        await interaction.response.send_message(result + ".")  # sends the result

    @slashCoinflip.error
    async def slashCoinflip_error(
        self, interaction: discord.Interaction, error: Exception
    ):
        logger.exception(f"❌ something went wrong with /coinflip command:")
        try:
            await interaction.response.send_message(
                "something went wrong with **coinflip**.", ephemeral=True
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "something went wrong with **coinflip**.", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(CoinFlip(bot))
