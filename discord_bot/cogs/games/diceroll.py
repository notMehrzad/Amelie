import random
import re

import discord
from discord import app_commands
from discord.ext import commands

from cogs.utility.help import Help
from core.log_handler import setup_logger

logger = setup_logger(__name__)

maxDiceSide = 1000  # the maximum number of dice sides
maxDiceCount = 100  # the maximum number of dice to roll at once


def dice_roll(dice: str):
    dice = dice.strip().lower()

    match = re.fullmatch(r"(\d*)d([1-9]\d*)", dice)  # trys to regex the entered format

    # if the format is NdS
    if match:
        countStr, sideStr = match.groups()  # extracts the number of dice and sides
        count = int(countStr) if countStr else 1
        sides = int(sideStr)

    # if the format is dS
    elif dice.isdigit():
        count = 1
        sides = int(dice)

    # invalid format
    else:
        raise ValueError("Invalid format. Use d6, 2d6, or 6")

    # if entered count is less than 1
    if count < 1:
        raise ValueError("You must roll at least one die")

    # if entered count is greater than the allowed number
    if count > maxDiceCount:
        raise ValueError(f"Cannot roll more than {maxDiceCount} dice at once.")

    # if entered side is less than 2
    if sides < 2:
        raise ValueError("Dice side must be at least 2.")

    # if entered side is greater than the allowed number
    if sides > maxDiceSide:
        raise ValueError(f"Dice side cannot be greater than {maxDiceSide}.")

    rolls = [random.randint(1, sides) for _ in range(count)]  # rolls the dice
    total = sum(rolls)  # sums the results

    return rolls, total, count, sides


class DiceRoll(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    Help = Help(
        category=Help.Category.Games,
        is_dm_only=False,
        is_server_only=False,
        subcommands=None,
        permissions=None,
        help_=(
            "Rolls dice using standard notation."
            "\n\nDice formats:"
            '\n• "6" → rolls 1d6'
            '\n• "d6" → rolls 1d6'
            '\n• "2d6" → rolls 2d6'
        ),
        brief="Rolls dice.",
        usage="<dice[*optional*]>",
        aliases=["dr", "dicer", "droll", "dice", "roll"],
    )

    @commands.command(name="diceroll", **Help.to_kwargs)
    async def diceroll(self, ctx: commands.Context[commands.Bot], dice: str = "6"):
        try:
            rolls, total, count, sides = dice_roll(dice)

            # sends the result
            await ctx.reply(
                f"🎲 **{count}d{sides}**\n"
                f"Rolls: {', '.join(map(str, rolls))}\n"
                f"Total: **{total}**"
            )

        except ValueError as e:
            await ctx.reply(f"{e}")

    @diceroll.error
    async def diceroll_error(
        self, ctx: commands.Context[commands.Bot], error: Exception
    ):
        logger.exception(f"❌ something went wrong with diceroll command:")
        await ctx.reply("something went wrong with **diceroll**.")

    # diceroll slash command
    @app_commands.command(name="diceroll", description=Help.brief, extras=Help.extras)
    @app_commands.describe(dice="The dice to roll. Format: d6, 2d6, or 6")
    async def slashDiceroll(self, interaction: discord.Interaction, dice: str = "6"):
        try:
            rolls, total, count, sides = dice_roll(dice)

            # sends the result
            await interaction.response.send_message(
                f"🎲 **{count}d{sides}**\n"
                f"Rolls: {', '.join(map(str, rolls))}\n"
                f"Total: **{total}**"
            )

        except ValueError as e:
            await interaction.response.send_message(f"{e}", ephemeral=True)

    @slashDiceroll.error
    async def slashDiceroll_error(
        self, interaction: discord.Interaction, error: Exception
    ):
        logger.exception(f"❌ something went wrong with /diceroll command:")
        try:
            await interaction.response.send_message(
                "something went wrong with **diceroll**.", ephemeral=True
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "something went wrong with **diceroll**.", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(DiceRoll(bot))
