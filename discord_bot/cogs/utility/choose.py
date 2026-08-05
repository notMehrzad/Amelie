import random

import discord
from discord import app_commands
from discord.ext import commands

from cogs.utility.help import Help
from core.log_handler import setup_logger

logger = setup_logger(__name__)


class Choose(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    Help = Help(
        category=Help.Category.Utility,
        is_dm_only=False,
        is_server_only=False,
        subcommands=None,
        permissions=None,
        help_=None,
        brief="Chooses one option between given choices",
        usage='<count[*optional*]> <choices(separated with "|")>',
        aliases=None,
    )

    @commands.command(name="choose", **Help.to_kwargs)
    async def choose(
        self,
        ctx: commands.Context[commands.Bot],
        count: int = 1,
        *,
        choices: str | None,
    ):
        # if user doesn't enter any options
        if not choices:
            return await ctx.reply(
                'You must enter at least two choices separated with "|".'
            )

        choicesList = [
            c.strip() for c in choices.split("|") if c.strip()
        ]  # fetches the options

        # if user doesn't enter at least two options to choose
        if len(choicesList) < 2:
            return await ctx.reply(
                'You must enter at least two choices separated with "|".'
            )

        # if user wants to choose more than given options
        if count >= len(choicesList):
            return await ctx.reply(
                "You can't choose greater than or equal to the number of choices."
            )

        choice = random.sample(choicesList, count)  # makes a choice
        await ctx.reply(f"I'd go with: {'and'.join(choice)}")  # sends the result

    @choose.error
    async def choose_error(self, ctx: commands.Context[commands.Bot], error: Exception):
        logger.exception(f"❌ something went wrong with choose command:")
        await ctx.reply("something went wrong with **choose**.")

    # choose slash command
    @app_commands.command(name="choose", description=Help.brief, extras=Help.extras)
    @app_commands.describe(
        choices='The choices to choose from, separated with "|".',
        count="The number of choices to make.",
    )
    async def slashChoose(
        self, interaction: discord.Interaction, choices: str, count: int = 1
    ):
        choicesList = [
            c.strip() for c in choices.split("|") if c.strip()
        ]  # fetches the options

        # if user doesn't enter at least two options to choose
        if len(choicesList) < 2:
            return await interaction.response.send_message(
                'You must enter at least two choices separated with "|".',
                ephemeral=True,
            )

        # if user wants to choose more than given options
        if count >= len(choicesList):
            return await interaction.response.send_message(
                "You can't choose greater than or equal to the number of choices.",
                ephemeral=True,
            )

        choice = random.sample(choicesList, count)  # makes a choice
        await interaction.response.send_message(
            f"I'd go with: {'and'.join(choice)}"
        )  # sends the result

    @slashChoose.error
    async def slashChoose_error(
        self, interaction: discord.Interaction, error: Exception
    ):
        logger.exception(f"❌ something went wrong with /choose command:")
        try:
            await interaction.response.send_message(
                "something went wrong with **choose**.", ephemeral=True
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "something went wrong with **choose**.", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Choose(bot))
