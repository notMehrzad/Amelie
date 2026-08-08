"""whisper command."""

from __future__ import annotations

__all__ = []

import contextlib
from typing import final

import discord
from discord import app_commands
from discord.ext import commands

from core.help_data_constants import WHISPER_HELP
from core.log_handler import setup_logger

logger = setup_logger(__name__)


@final
class Whisper(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="whisper", **WHISPER_HELP.kwargs)
    async def whisper(  # noqa: PLR0911
        self,
        ctx: commands.Context[commands.Bot],
        user: discord.abc.User | str | None,
        *,
        message: str | None,
    ) -> None:
        # Raise an error if user runs the command in DM.
        if ctx.guild is None:
            await ctx.reply("Whispering is only available in a server.")
            return

        # Raise an error if user enters no user to whisper.
        if user is None:
            await ctx.reply("A user must be mentioned to whisper to.")
            return

        # Raise an error if user enters an invalid user.
        if not isinstance(user, discord.abc.User):
            await ctx.reply("A valid user must be mentioned to whisper to.")
            return

        # Fetch the target user from the guild.
        target = ctx.guild.get_member(user.id)
        if target is None:
            await ctx.reply(f"{user.display_name} is not a member of this server.")
            return

        # Raise an error if user wants to whisper to themselves.
        if target.id == ctx.author.id:
            await ctx.reply("You can't whisper to yourself.")
            return

        # Raise an error if user wants to whisper to a bot.
        if target.bot:
            if target.id == ctx.me.id:
                await ctx.reply("I hear your words..")
            else:
                await ctx.reply("Why whispering to bots though??")
            return

        # Raise an error if user enters no message.
        if message is None:
            await ctx.reply("A message must be written to be whispered.")
            return

        # Delete the command message.
        await ctx.message.delete()

        # Send the view.
        await WhisperView(ctx, target, message).start()

    @whisper.error
    async def whisper_error(
        self,
        ctx: commands.Context[commands.Bot],
        error: commands.CommandError,
    ) -> None:
        logger.error("❌ Something went wrong with whisper command:", exc_info=error)
        await ctx.reply("Something went wrong with **whisper**.")

    # whisper slash command
    @app_commands.command(
        name="whisper",
        description=WHISPER_HELP.brief,
        extras=WHISPER_HELP.extras,
    )
    @app_commands.guild_only()
    @app_commands.describe(
        target="The Member to whisper.",
        message="The message to be whispered.",
    )
    async def slash_whisper(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        message: str,
    ) -> None:
        # Raise an error if user wants to whisper to themselves.
        if target.id == interaction.user.id:
            await interaction.response.send_message(
                "You can't whisper to yourself.",
                ephemeral=True,
            )
            return

        # Raise an error if user wants to whisper to a bot.
        if target.bot:
            if target.id == interaction.application_id:
                await interaction.response.send_message(
                    "I hear your words..",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "Why whispering to bots though??",
                    ephemeral=True,
                )
            return

        # Defer the response.
        await interaction.response.defer(ephemeral=True)

        # Send the view.
        await WhisperView(interaction, target, message).start()

    @slash_whisper.error
    async def slash_whisper_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        logger.error("❌ Something went wrong with /whisper command:", exc_info=error)
        try:
            await interaction.response.send_message(
                "Something went wrong with **whisper**.",
                ephemeral=True,
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "Something went wrong with **whisper**.",
                ephemeral=True,
            )


class WhisperView(discord.ui.View):
    def __init__(
        self,
        ctx: commands.Context[commands.Bot] | discord.Interaction,
        user: discord.Member,
        message: str,
    ) -> None:
        super().__init__(timeout=300)
        if isinstance(ctx, discord.Interaction):
            self.slash_command = True
            self.interaction = ctx
            self.user = self.interaction.user
        else:
            self.slash_command = False
            self.ctx = ctx
            self.user = self.ctx.author
        self.target_user: discord.Member = user
        self.message: str = message

    async def start(self) -> None:
        """Start the view."""
        desctiption = (
            f"{self.target_user.mention}, You have a whisper from {self.user.mention}."
        )
        if self.slash_command:
            if isinstance(self.interaction.channel, discord.abc.MessageableChannel):
                self.msg = await self.interaction.channel.send(
                    content=desctiption,
                    view=self,
                )
            await self.interaction.followup.send(content="Whisper has been sent.")
        else:
            self.msg = await self.ctx.send(content=desctiption, view=self)

    # read button
    @discord.ui.button(label="read", style=discord.ButtonStyle.grey)
    async def read(
        self,
        interaction: discord.Interaction,
        _: discord.ui.Button[discord.ui.View],
    ) -> None:
        # Raise an error if interaction is not from the user.
        if interaction.user.id not in (self.target_user.id, self.user.id):
            await interaction.response.send_message(
                "You can't read other's whisper.",
                ephemeral=True,
            )
            return

        # Show the whisper to user if user wants to read their own whisper.
        if interaction.user.id == self.user.id:
            await interaction.response.send_message(
                f"*You whisper to {self.target_user.mention}:*\n{self.message}",
                ephemeral=True,
            )
            return

        # Show the whisper message to the target user.
        await interaction.response.send_message(
            f"*{self.user.mention} whispers to you:*\n{self.message}",
            ephemeral=True,
        )

        result_embed = discord.Embed(
            title="whisper",
            description=(
                f"{self.target_user.display_name} has read the"
                " whisper from {self.user.display_name}."
            ),
        )
        # Send result embed.
        await self.msg.edit(content=None, embed=result_embed, view=None)

        # Stop the view.
        self.stop()

    async def on_timeout(self) -> None:
        self.read.disabled = True

        timeout_embed = discord.Embed(
            title="whisper",
            description=(
                "⏰ The whisper got forgotten.."
                " {self.target_user.display_name} didn't get it early."
            ),
        )
        # Send timeout embed.
        with contextlib.suppress(discord.NotFound):
            await self.msg.edit(embed=timeout_embed, view=self)

        # Stop the view.
        self.stop()

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item[discord.ui.View],
    ) -> None:
        logger.error(
            "❌ Something went wrong with whisper interaction - button: %s",
            getattr(item, "label", "unknown"),
            exc_info=error,
        )
        try:
            await interaction.response.send_message(
                "Something went wrong with **whisper**.",
                ephemeral=True,
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "Something went wrong with **whisper**.",
                ephemeral=True,
            )

        self.stop()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Whisper(bot))
