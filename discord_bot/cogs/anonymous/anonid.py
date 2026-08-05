"""Get anonymous ID for anonymous messaging."""

from __future__ import annotations

__all__ = []

from typing import final

import discord
from discord import app_commands
from discord.ext import commands

from core.anonymous import create_anonymous_user, get_anonymous_user
from core.help import HelpData
from core.log_handler import setup_logger

logger = setup_logger(__name__)


@final
class AnonId(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    Help = HelpData(
        category=HelpData.CommandCategory.ANONYMOUSE,
        is_dm_only=True,
        is_server_only=False,
        subcommands=None,
        permissions=None,
        help_=(
            "Shows the public Anonymous ID for the user."
            "\n\nIf user had no ID before, creates one for them."
            "\n\nUser can share this public ID anywhere and people can start sending"
            "\nanonymous messages to them with it. (try `/help anonsend` for more"
            "\ninformation."
        ),
        brief="Shows the public Anonymous ID for the user.",
        usage=None,
        aliases=["anonymousid"],
    )

    @commands.command(name="anonid", **Help.kwargs)
    async def anonid(self, ctx: commands.Context[commands.Bot]) -> None:
        # Warn the user if trying to run the command in a guild.
        if ctx.guild is not None:
            await ctx.reply("This command can only be run in Amélie's DM.")
            return

        # Fetch user's anonymous account.
        user = await get_anonymous_user(user_id=ctx.author.id)

        # Create an anonymous account for user if they haven't one.
        if user is None:
            user = await create_anonymous_user(ctx.author.id)

        # Send result.
        result_embed = discord.Embed(
            title="Anonymous ID",
            description=(
                f"Your anonymous ID is: `{user.public_id}`"
                "\nShare this somewhere and people can message you anonymously"
                "\nwith `/anonsend`."
            ),
            color=discord.Color.blurple(),
        )
        await ctx.reply(embed=result_embed)

    @anonid.error
    async def anonid_error(
        self,
        ctx: commands.Context[commands.Bot],
        error: Exception,  # noqa: ARG002
    ) -> None:
        logger.exception("❌ something went wrong with anonid command:")
        await ctx.reply("something went wrong with **anonid**.")

    # anonid slash command
    @app_commands.command(name="anonid", description=Help.brief, extras=Help.extras)
    @app_commands.dm_only()
    async def slash_anonid(self, interaction: discord.Interaction) -> None:
        # Warn the user if trying to run the command in a guild.
        if interaction.guild is not None:
            await interaction.response.send_message(
                "This command can only be run in Amélie's DM.",
                ephemeral=True,
            )
            return

        # Fetch user's anonymous account.
        user = await get_anonymous_user(user_id=interaction.user.id)

        # Create an anonymous account for user if they haven't one.
        if user is None:
            user = await create_anonymous_user(interaction.user.id)

        # Send result.
        result_embed = discord.Embed(
            title="Anonymous ID",
            description=(
                f"Your anonymous ID is: `{user.public_id}`"
                "\nShare this somewhere and people can message you anonymously"
                "\nwith `/anonsend`."
            ),
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(embed=result_embed)

    @slash_anonid.error
    async def slash_anonid_error(
        self,
        interaction: discord.Interaction,
        error: Exception,  # noqa: ARG002
    ) -> None:
        logger.exception("❌ something went wrong with /anonid command:")
        try:
            await interaction.response.send_message(
                "something went wrong with **anonid**.",
                ephemeral=True,
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "something went wrong with **anonid**.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AnonId(bot))
