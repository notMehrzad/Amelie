"""The `daily` command. It is used by users to claim the daily reward."""

from __future__ import annotations

__all__ = []

from datetime import timedelta
from typing import final

import discord
from discord import app_commands
from discord.ext import commands

from core.bank import create_bank_account, get_bank_account
from core.help_data_constants import DAILY_HELP
from core.log_handler import setup_logger
from core.utils import format_timedelta

DAILY_AMOUNT = 500
DAILY_COOLDOWN = 24 * 60  # minutes

logger = setup_logger(__name__)


@final
class Daily(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="daily", **DAILY_HELP.kwargs)
    async def daily(self, ctx: commands.Context[commands.Bot]) -> None:
        # Fetch user's bank account.
        account = await get_bank_account(ctx.author.id)

        # Create a bank account if user hasn't one.
        if not account:
            account = await create_bank_account(user_id=ctx.author.id)

        now = discord.utils.utcnow()
        # Raise an error if user wants to claim daily within 24 hours.
        if (
            account.last_daily_date
            and account.last_daily_date + timedelta(minutes=DAILY_COOLDOWN) > now
        ):
            _ = await ctx.reply(
                "You must wait `"
                + format_timedelta(
                    account.last_daily_date + timedelta(minutes=DAILY_COOLDOWN) - now,
                )
                + "` to claim your next Daily reward.",
            )
            return

        # Deposit daily reward.
        _ = await account.deposit(DAILY_AMOUNT, "Daily reward.")

        # Update last daily date of account.
        date = await account.update_last_daily_date()

        # Send result.
        result_embed = discord.Embed(
            color=discord.Color.blurple(),
            title="Daily Reward !",
            description=(
                f"You have claimed your Daily reward for today."
                f"\nCurrent balance: *{account.formatted_balance}*"
            ),
            timestamp=date,
        )
        _ = await ctx.reply(embed=result_embed)

    @daily.error
    async def daily_error(
        self,
        ctx: commands.Context[commands.Bot],
        error: commands.CommandError,
    ) -> None:
        logger.error("❌ Something went wrong with daily command:", exc_info=error)
        _ = await ctx.reply("Something went wrong with **daily**.")

    # daily slash command
    @app_commands.command(
        name="daily",
        description=DAILY_HELP.brief,
        extras=DAILY_HELP.extras,
    )
    async def slash_daily(self, interaction: discord.Interaction) -> None:
        # Fetch user's bank account.
        account = await get_bank_account(interaction.user.id)

        # Create a bank account if user hasn't one.
        if not account:
            account = await create_bank_account(user_id=interaction.user.id)

        now = discord.utils.utcnow()
        # Raise an error if user wants to claim daily within 24 hours.
        if (
            account.last_daily_date
            and account.last_daily_date + timedelta(minutes=DAILY_COOLDOWN) > now
        ):
            _ = await interaction.response.send_message(
                "You must wait `"
                + format_timedelta(
                    account.last_daily_date + timedelta(minutes=DAILY_COOLDOWN) - now,
                )
                + "` to claim your next Daily reward.",
                ephemeral=True,
            )
            return

        # Deposit daily reward.
        _ = await account.deposit(DAILY_AMOUNT, "Daily reward.")

        # Update last daily date of account.
        date = await account.update_last_daily_date()

        # Send result.
        result_embed = discord.Embed(
            color=discord.Color.blurple(),
            title="Daily Reward !",
            description=(
                f"You have claimed your Daily reward for today."
                f"\nCurrent balance: *{account.formatted_balance}*"
            ),
            timestamp=date,
        )
        _ = await interaction.response.send_message(embed=result_embed)

    @slash_daily.error
    async def slash_daily_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        logger.error("❌ Something went wrong with /daily command:", exc_info=error)
        try:
            _ = await interaction.response.send_message(
                "Ssomething went wrong with **daily**.",
                ephemeral=True,
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "Something went wrong with **daily**.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Daily(bot))
