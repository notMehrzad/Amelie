"""The `lottery` command. allows users to sign up for the lottery."""

import discord
from discord import app_commands
from discord.ext import commands

from core.database import execute, fetchone
from core.dbconstants import LotteryTable
from core.help import HelpData
from core.log_handler import setup_logger

logger = setup_logger(__name__)


class Lottery(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    Help = HelpData(
        category=HelpData.CommandCategory.ECONOMY,
        is_dm_only=False,
        is_server_only=False,
        subcommands=None,
        permissions=None,
        help_=None,
        brief="Signs in for the lottery.",
        usage=None,
        aliases=None,
    )

    @commands.command(name="lottery", **Help.kwargs)
    async def lottery(
        self, ctx: commands.Context[commands.Bot]
    ) -> discord.Message | None:
        # checks if user has already signed in for lottery
        row = await fetchone(
            f"""
            SELECT {LotteryTable.COL_SIGNED_AT} FROM {LotteryTable.TABLE_NAME}
            WHERE {LotteryTable.COL_USER_ID} = ?;
            """,
            (ctx.author.id,),
        )
        if row:
            return await ctx.reply(
                f"You have already signed in for Lottery at `{row['signed_at']}`."
            )

        # signs the user for the lottery
        await execute(
            f"""
            INSERT INTO {LotteryTable.TABLE_NAME} ({LotteryTable.columns()})
            VALUES (?, ?);
            """,
            (ctx.author.id, discord.utils.utcnow()),
        )
        await ctx.reply("You have signed in for the Lottery successfully. Be tuned.")

    @lottery.error
    async def lottery_error(
        self, ctx: commands.Context[commands.Bot], error: commands.CommandError
    ) -> None:
        logger.exception("❌ something went wrong with lottery command:")
        await ctx.reply("something went wrong with **lottery**.")

    # lottery slash command
    @app_commands.command(name="lottery", description=Help.brief, extras=Help.extras)
    async def slashLottery(
        self, interaction: discord.Interaction
    ) -> discord.InteractionCallbackResponse[discord.Client] | None:
        # checks if user has already signed in for lottery
        row = await fetchone(
            f"""
            SELECT {LotteryTable.COL_SIGNED_AT} FROM {LotteryTable.TABLE_NAME}
            WHERE {LotteryTable.COL_USER_ID} = ?;
            """,
            (interaction.user.id,),
        )
        if row:
            return await interaction.response.send_message(
                f"You have already signed in for Lottery at `{row['signed_at']}`.",
                ephemeral=True,
            )

        # signs the user for the lottery
        await execute(
            f"""
            INSERT INTO {LotteryTable.TABLE_NAME} ({LotteryTable.columns()})
            VALUES (?, ?);
            """,
            (interaction.user.id, discord.utils.utcnow()),
        )
        await interaction.response.send_message(
            "You have signed in for the Lottery successfully. Be tuned."
        )

    @slashLottery.error
    async def slashLottery_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        logger.exception("❌ something went wrong with /lottery command:")
        try:
            await interaction.response.send_message(
                "something went wrong with **lottery**.", ephemeral=True
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "something went wrong with **lottery**.", ephemeral=True
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Lottery(bot))
