"""The `balance` command. It can be run via user to see their current balance."""

from __future__ import annotations

__all__ = []

from typing import final

import discord
from discord import app_commands
from discord.ext import commands

from core.bank import create_bank_account, get_bank_account
from core.help_data_constants import BALANCE_HELP
from core.log_handler import setup_logger

logger = setup_logger(__name__)


@final
class Balance(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="balance", **BALANCE_HELP.kwargs)
    async def balance(self, ctx: commands.Context[commands.Bot]) -> None:
        # Fetch user's bank account.
        account = await get_bank_account(ctx.author.id)
        # Raise an error if user's bank account can't be fetched.
        if account is None:
            account = await create_bank_account(user_id=ctx.author.id)

        # Send result embed.
        result_embed = discord.Embed(
            title=f"{ctx.author.mention}'s Balance",
            description=f"*{account.formatted_balance}*",
            timestamp=discord.utils.utcnow(),
        )
        _ = await ctx.reply(embed=result_embed)

    @balance.error
    async def balance_error(
        self,
        ctx: commands.Context[commands.Bot],
        error: commands.CommandError,
    ) -> None:
        logger.error("❌ Something went wrong with balance command:", exc_info=error)
        _ = await ctx.reply("Something went wrong with **balance**.")

    # balance slash command
    @app_commands.command(
        name="balance",
        description=BALANCE_HELP.brief,
        extras=BALANCE_HELP.extras,
    )
    @app_commands.describe(hidden="Whether result should be only visible to you.")
    async def slash_balance(
        self,
        interaction: discord.Interaction,
        *,
        hidden: bool = False,
    ) -> None:
        # Fetch user's bank account.
        account = await get_bank_account(interaction.user.id)
        # Raise an error if user's bank account can't be fetched.
        if account is None:
            account = await create_bank_account(user_id=interaction.user.id)

        # Send result embed.
        result_embed = discord.Embed(
            title=f"{interaction.user.mention}'s Balance",
            description=f"*{account.formatted_balance}*",
            timestamp=discord.utils.utcnow(),
        )
        _ = await interaction.response.send_message(
            embed=result_embed,
            ephemeral=hidden,
        )

    @slash_balance.error
    async def slash_balance_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        logger.error("❌ Something went wrong with /balance command:", exc_info=error)
        try:
            _ = await interaction.response.send_message(
                "Something went wrong with **balance**.",
                ephemeral=True,
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "Something went wrong with **balance**.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Balance(bot))
