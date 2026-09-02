"""ban command."""

from __future__ import annotations

__all__ = []

from typing import final

import discord
from discord import app_commands
from discord.ext import commands

from core.help_data_constants import BAN_HELP
from core.log_handler import setup_logger

logger = setup_logger(__name__)


@final
class Ban(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name=BAN_HELP.name, **BAN_HELP.kwargs)
    async def ban(
        self,
        ctx: commands.Context[commands.Bot],
        user: discord.User | int | str | None,
        *,
        reason: str | None = None,
    ) -> None:
        # Raise an error if user runs the command in DM.
        if ctx.guild is None or not isinstance(ctx.author, discord.Member):
            await ctx.reply("You can only run moderation commands in a server.")
            return

        # Raise an error if user doesn't have the permission to ban users.
        if not ctx.author.guild_permissions.ban_members:
            await ctx.reply("You have no permission to *ban* Members.")
            return

        # Raise an error if the bot doesn't have the permission to ban users.
        if not ctx.guild.me.guild_permissions.ban_members:
            await ctx.reply("I have no permisson to *ban* Members.")
            return

        # Raise an error if user enters no target user.
        if user is None:
            await ctx.reply("You must mention a target Member for this command.")
            return

        # Raise an error if user enters an invalid user.
        if not isinstance(user, (discord.abc.User, int)):
            await ctx.reply("Enter a valid member to ban.")
            return

        # Fetch target user.
        try:
            target = (
                (
                    ctx.guild.get_member(user)
                    or self.bot.get_user(user)
                    or await self.bot.fetch_user(user)
                )
                if isinstance(user, int)
                else user
            )
        except discord.NotFound:
            await ctx.reply("User with given ID doesn't exist.")
            return

        # Check if target is already in the ban list if target is not a member.
        if not isinstance(target, discord.Member):
            try:
                await ctx.guild.fetch_ban(
                    discord.Object(id=target.id, type=discord.User),
                )
                await ctx.reply(f"{target.display_name} is banned already.")
            except discord.NotFound:
                await ctx.reply(
                    f"{target.display_name} is not a Member of this server.",
                )
            return

        # Raise an error if user wants to ban themselves.
        if target.id == ctx.author.id:
            await ctx.reply("You can't ban yourself.")
            return

        # Raise an error if user wants to ban guild owner.
        if target.id == ctx.guild.owner_id:
            await ctx.reply("You can't ban the server *Owner*.")
            return

        # Raise an error if user wants to ban the bot.
        if target.id == ctx.me.id:
            await ctx.reply(
                "You can't run my moderation commands on myself.\nnice try.",
            )
            return

        # Raise an error if target has higher or equal role positions than user.
        if (
            target.top_role >= ctx.author.top_role
            and ctx.author.id != ctx.guild.owner_id
        ):
            await ctx.reply(
                "You can't ban a Member with *higher or equal* role position as you.",
            )
            return

        # Raise an error if target has higher or equal role positions than the bot.
        if target.top_role >= ctx.guild.me.top_role:
            await ctx.reply(
                "I can't ban a Member with *higher or equal* role position as me.",
            )
            return

        # Ban target user.
        await ctx.guild.ban(user=target, reason=reason)

        await ctx.reply(
            f"{target.display_name} has been *banned* via {ctx.author.display_name}."
            + (f"\nreason: {reason}" if reason else ""),
        )

    # ban slash command
    @app_commands.command(
        name=BAN_HELP.name,
        description=BAN_HELP.brief,
        extras=BAN_HELP.extras,
    )
    @app_commands.guild_only()
    @app_commands.describe(
        user="The target Member to ban from the server.",
        reason="The reason you want to ban the target.",
    )
    async def slash_ban(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str | None = None,
    ) -> None:
        # Raise an error if user runs the command in DM.
        if interaction.guild is None or not isinstance(
            interaction.user,
            discord.Member,
        ):
            await interaction.response.send_message(
                "You can only run moderation commands in a server.",
                ephemeral=True,
            )
            return

        # Raise an error if user doesn't have the permission to ban users.
        if not interaction.user.guild_permissions.ban_members:
            await interaction.response.send_message(
                "You have no permission to *ban* Members.",
                ephemeral=True,
            )
            return

        # Raise an error if the bot doesn't have the permission to ban users.
        if not interaction.guild.me.guild_permissions.ban_members:
            await interaction.response.send_message(
                "I have no permisson to *ban* Members.",
                ephemeral=True,
            )
            return

        # Raise an error if user wants to ban themselves.
        if user.id == interaction.user.id:
            await interaction.response.send_message(
                "You can't ban yourself.",
                ephemeral=True,
            )
            return

        # Raise an error if user wants to ban guild owner.
        if user.id == interaction.guild.owner_id:
            await interaction.response.send_message(
                "You can't ban the server *Owner*.",
                ephemeral=True,
            )
            return

        # Raise an error if user wants to ban the bot.
        if user.id == interaction.application_id:
            await interaction.response.send_message(
                "You can't run my moderation commands on myself.\nnice try.",
                ephemeral=True,
            )
            return

        # Raise an error if target has higher or equal role positions than user.
        if (
            user.top_role >= interaction.user.top_role
            and interaction.user.id != interaction.guild.owner_id
        ):
            await interaction.response.send_message(
                "You can't ban a Member with *higher or equal* role position as you.",
                ephemeral=True,
            )
            return

        # Raise an error if target has higher or equal role positions than the bot.
        if user.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                "I can't ban a Member with *higher or equal* role position as me.",
                ephemeral=True,
            )
            return

        # Ban target user.
        await interaction.guild.ban(user=user, reason=reason)

        await interaction.response.send_message(
            f"{user.display_name} has been *banned*"
            " via {interaction.user.display_name}."
            + (f"\nreason: {reason}" if reason else ""),
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Ban(bot))
