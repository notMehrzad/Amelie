"""say command."""

from __future__ import annotations

__all__ = []

from typing import final

import discord
from discord import app_commands
from discord.ext import commands

from core.help_data_constants import SAY_HELP
from core.log_handler import setup_logger

logger = setup_logger(__name__)


@final
class Say(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="say", **SAY_HELP.kwargs)
    async def say(
        self,
        ctx: commands.Context[commands.Bot],
        channel: discord.abc.MessageableChannel | str | None,
        *,
        message: str | None,
    ) -> None:
        # Raise an error if user enters no channel.
        if channel is None:
            await ctx.reply(
                "You must enter the channel you want to say something in."
                " (or *here* to choose the current channel)",
            )
            return

        # Raise an error if user enters a string channel and it's not `here`.
        if isinstance(channel, str):
            if channel.lower().strip() == "here":
                target_channel = ctx.channel

            else:
                await ctx.reply("Enter a valid channel.")
                return

        else:
            target_channel = channel

        # If both user and bot are members of the guild.
        if isinstance(ctx.author, discord.Member) and isinstance(
            ctx.me,
            discord.Member,
        ):
            # Raise an error if user doesn't have the permission to send messages.
            if not target_channel.permissions_for(ctx.author).send_messages:
                await ctx.reply(
                    "You have no permission to *say and send*"
                    " messages in this channel.",
                )
                return

            # Raise an error if bot doesn't have the permission to send messages.
            if not target_channel.permissions_for(ctx.me).send_messages:
                await ctx.reply(
                    "I have no permission to *say and send* messages in this channel.",
                )
                return

        # Raise an error if user enters no message.
        if message is None:
            await ctx.reply("You must write your text to be said.")
            return

        # Send the message.
        await target_channel.send(message)

    @say.error
    async def say_error(
        self,
        ctx: commands.Context[commands.Bot],
        error: commands.CommandError,
    ) -> None:
        logger.error("❌ Something went wrong with say command:", exc_info=error)
        await ctx.reply("something went wrong with **say**.")

    # say slash command
    @app_commands.command(
        name="say",
        description=SAY_HELP.brief,
        extras=SAY_HELP.extras,
    )
    @app_commands.describe(
        message="Message to be said.",
        channel="Channel to be said in.",
        visible_slash_command="Whether it should be visible if it was a slash command.",
    )
    async def slash_say(
        self,
        interaction: discord.Interaction,
        message: str,
        channel: discord.interactions.InteractionChannel | None = None,
        *,
        visible_slash_command: bool = True,
    ) -> None:
        # Raise an error if user enters no channel.
        if channel is None:
            channel = interaction.channel

        # Raise an error if channel isn't messageable.
        if not isinstance(channel, discord.abc.Messageable):
            await interaction.response.send_message(
                "The given channel is not messageable.",
                ephemeral=True,
            )
            return

        # If both user and bot are members of the guild.
        if isinstance(interaction.user, discord.Member) and isinstance(
            interaction.client,
            discord.Member,
        ):
            # Raise an error if user doesn't have the permission to send messages.
            if not channel.permissions_for(interaction.user).send_messages:
                await interaction.response.send_message(
                    "You have no permission to *say and send*"
                    " messages in this channel.",
                    ephemeral=True,
                )
                return

            # Raise an error if bot doesn't have the permission to send messages.
            if not channel.permissions_for(interaction.client).send_messages:
                await interaction.response.send_message(
                    "I have no permission to *say and send* messages in this channel.",
                    ephemeral=True,
                )
                return

        # Send the message.
        if channel == interaction.channel:
            if visible_slash_command:
                await interaction.response.send_message(message)
                await interaction.followup.send("Sent!", ephemeral=True)

            else:
                await interaction.response.defer(ephemeral=True)
                await channel.send(message)
                await interaction.followup.send("Sent!")

        else:
            await interaction.response.defer(ephemeral=True)
            await channel.send(message)
            await interaction.followup.send("Sent!")

    @slash_say.error
    async def slash_say_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        logger.error("❌ Something went wrong with /say command:", exc_info=error)
        try:
            await interaction.response.send_message(
                "Something went wrong with **say**.",
                ephemeral=True,
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "Something went wrong with **say**.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Say(bot))
