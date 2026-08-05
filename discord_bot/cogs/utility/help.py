"""help command."""

from __future__ import annotations

__all__ = []

import json
from pathlib import Path
from typing import cast, final

import discord
from discord import app_commands
from discord.ext import commands

from core.help import ExtrasTyped, HelpData
from core.help_data_constants import HELP_HELP
from core.log_handler import setup_logger

with Path("config.json").open("r") as file:
    CONFIG = json.load(file)


logger = setup_logger(__name__)


def _create_command_embed(help_data: HelpData) -> discord.Embed:
    """Create a command embed.

    Args:
        help_data (HelpData): Help data of the command.

    Returns:
        Embed: Return the embed.

    """
    embed = discord.Embed(
        color=discord.Color.blurple(),
        title=(f".{help_data.name}"),
        description=help_data.help
        or help_data.brief
        or "*No description provided for this command.*",
    ).set_author(name="Help")
    # Add Aliases field if command has aliases.
    if help_data.aliases:
        embed.add_field(name="Aliases", value=" - ".join(help_data.aliases))

    # Add Usage field if command has usage.
    if help_data.usage:
        embed.add_field(name="Usage", value=f".{help_data.name} {help_data.usage}")

    extras: ExtrasTyped = cast("ExtrasTyped", help_data.extras)
    # Add Subcommand field if command has subcommands.
    if extras["subcommands"]:
        embed.add_field(
            name="Subcommands",
            value=" - ".join(extras["subcommands"]),
        )

    # Add DM-only field if command is DM strict.
    if extras["dm_only"]:
        embed.add_field(name="DM-only", value="Yes")

    # Add Server-only field if command is server strict.
    if extras["server_only"]:
        embed.add_field(name="Server-only", value="Yes")

    # Add Permission field if command needs some permissions.
    if extras["permissions"]:
        embed.add_field(
            name="Permissions",
            value=" - ".join(extras["permissions"]),
        )

    return embed


@final
class Help(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="help", **HELP_HELP.kwargs)
    async def help_(
        self,
        ctx: commands.Context[commands.Bot],
        command: str | None = None,
    ) -> None:
        show_hidden: bool = bool(
            str(ctx.author.id) in CONFIG["ADMINS"] and not ctx.guild,
        )

        # Show command help if user wants help for a specific command.
        if command and command.lower() not in ("all", "list", "menu"):
            # Fetch the command.
            help_data = HelpData.get_help(command.lower())

            # Raise an error if the command can't be fetched.
            if help_data is None:
                await ctx.reply(f"*{command}* doesn't exist. Enter a valid command.")
                return

            if isinstance(help_data, HelpData):
                # Raise an error if command is hidden and user isn't a developer.
                if help_data.is_hidden and not show_hidden:
                    await ctx.reply("Help menu for this command is not avaiable.")
                    return

                embed = _create_command_embed(help_data)

                # Send command embed.
                await ctx.reply(embed=embed)

        # Show help menu if user enters no command name.
        else:
            categorized = HelpData.get_help(show_hidden=show_hidden)

            if isinstance(categorized, dict):
                # Define a list to store different category embed.
                category_embeds: list[discord.Embed] = []
                for category, help_datas in categorized.items():
                    embed = discord.Embed(
                        title=f"{category}",
                        color=discord.Color.blurple(),
                    ).set_author(name="Help Menu")
                    # Add command field for each command.
                    for help_data in help_datas:
                        embed.add_field(
                            name="." + help_data.name,
                            value=help_data.brief or "*No description.*",
                            inline=False,
                        )

                    category_embeds.append(embed)

                # Show the only embed if there's only one embed.
                if len(category_embeds) == 1:
                    await ctx.reply(embed=category_embeds[0])

                # Send the view if there's multiple embeds.
                else:
                    await HelpView(ctx, category_embeds=category_embeds).start()

    @help_.error
    async def help_error(
        self,
        ctx: commands.Context[commands.Bot],
        error: commands.CommandError,
    ) -> None:
        logger.error("❌ Something went wrong with help command:", exc_info=error)
        await ctx.reply("Something went wrong with **help**.")

    # help slash command
    @app_commands.command(name="help", description=HELP_HELP.brief)
    @app_commands.describe(
        command="The command to display help for.",
        hidden="Whether only you can see the response.",
    )
    async def slash_help(
        self,
        interaction: discord.Interaction,
        command: str | None = None,
        *,
        hidden: bool = False,
    ) -> None:
        show_hidden: bool = bool(
            str(interaction.user.id) in CONFIG["ADMINS"] and not interaction.guild,
        )

        # Show command help if user wants help for a specific command.
        if command and command.lower() not in ("all", "list", "menu"):
            # Fetch the command.
            help_data = HelpData.get_help(command.lower())

            # Raise an error if the command can't be fetched.
            if help_data is None:
                await interaction.response.send_message(
                    f"*{command}* doesn't exist. Enter a valid command.",
                    ephemeral=True,
                )
                return

            if isinstance(help_data, HelpData):
                # Raise an error if command is hidden and user isn't a developer.
                if help_data.is_hidden and not show_hidden:
                    await interaction.response.send_message(
                        "Help menu for this command is not avaiable.",
                        ephemeral=True,
                    )
                    return

                embed = _create_command_embed(help_data)

                # Send command embed.
                await interaction.response.send_message(embed=embed, ephemeral=hidden)

        # Show help menu if user enters no command name.
        else:
            categorized = HelpData.get_help(show_hidden=show_hidden)

            if isinstance(categorized, dict):
                # Define a list to store different category embed.
                category_embeds: list[discord.Embed] = []
                for category, help_datas in categorized.items():
                    embed = discord.Embed(
                        title=f"{category}",
                        color=discord.Color.blurple(),
                    ).set_author(name="Help Menu")
                    # Add command field for each command.
                    for help_data in help_datas:
                        embed.add_field(
                            name="." + help_data.name,
                            value=help_data.brief or "*No description.*",
                            inline=False,
                        )

                    category_embeds.append(embed)

                # Show the only embed if there's only one embed.
                if len(category_embeds) == 1:
                    await interaction.response.send_message(
                        embed=category_embeds[0],
                        ephemeral=hidden,
                    )

                # Send the view if there's multiple embeds.
                else:
                    await HelpView(
                        interaction,
                        category_embeds=category_embeds,
                        hidden=hidden,
                    ).start()

    @slash_help.error
    async def slash_help_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        logger.error("❌ Something went wrong with /help command:", exc_info=error)
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "Something went wrong with **help**.",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                "Something went wrong with **help**.",
                ephemeral=True,
            )


@final
class HelpView(discord.ui.View):
    def __init__(
        self,
        ctx: commands.Context[commands.Bot] | discord.Interaction,
        category_embeds: list[discord.Embed],
        *,
        hidden: bool = False,
    ) -> None:
        super().__init__(timeout=60)
        if isinstance(ctx, discord.Interaction):
            self.slash = True
            self.interaction = ctx
            self.user = self.interaction.user
        else:
            self.slash = False
            self.ctx = ctx
            self.user = self.ctx.author
        self.category_embeds = category_embeds
        self.hidden = hidden
        self.embed_index = 0

    async def start(self) -> None:
        """Start Help view."""
        # Send first embed (first page).
        if self.slash:
            await self.interaction.response.send_message(
                embed=self.category_embeds[0],
                view=self,
                ephemeral=self.hidden,
            )
        else:
            self.msg = await self.ctx.reply(embed=self.category_embeds[0], view=self)

    # previous button
    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.grey, row=0)
    async def previous(
        self,
        interaction: discord.Interaction,
        _: discord.ui.Button[discord.ui.View],
    ) -> None:
        # Raise an error if interaction is not from the user.
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "You can't control this help menu. try `/help` yourself.",
                ephemeral=True,
            )
            return

        # Calculate the index number of the previous page.
        self.embed_index = (self.embed_index - 1) % len(self.category_embeds)

        # Edit the embed.
        await interaction.response.edit_message(
            embed=self.category_embeds[self.embed_index],
        )

    # next button
    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.grey, row=0)
    async def next(
        self,
        interaction: discord.Interaction,
        _: discord.ui.Button[discord.ui.View],
    ) -> None:
        # Raise an error if interaction is not from the user.
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "You can't control this help menu. try `/help` yourself.",
                ephemeral=True,
            )
            return

        # Calculate the index number of the next page.
        self.embed_index = (self.embed_index + 1) % len(self.category_embeds)

        # Edit the embed.
        await interaction.response.edit_message(
            embed=self.category_embeds[self.embed_index],
        )

    # close button
    @discord.ui.button(label="close", style=discord.ButtonStyle.red, row=0)
    async def close(
        self,
        interaction: discord.Interaction,
        _: discord.ui.Button[discord.ui.View],
    ) -> None:
        # Raise an error if interaction is not from the user.
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "You can't control this help menu. try `/help` yourself.",
                ephemeral=True,
            )
            return

        # Close the help menu.
        if self.slash:
            await self.interaction.delete_original_response()
        else:
            await self.msg.delete()

        # Stop the view.
        self.stop()

    async def on_timeout(self) -> None:
        # Disable buttons.
        for btn in self.children:
            if isinstance(btn, discord.ui.Button):
                btn.disabled = True

        # Edit the message upon timeout.
        try:
            if self.slash:
                await self.interaction.edit_original_response(view=None)
            else:
                await self.msg.edit(view=None)
        except discord.NotFound:
            pass

        # Stop the view.
        self.stop()

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item[discord.ui.View],
    ) -> None:
        logger.error(
            "❌ Something went wrong with help interaction - button: %s",
            getattr(item, "emoji", "unknown"),
            exc_info=error,
        )
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "Something went wrong with **help**.",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                "Something went wrong with **help**.",
                ephemeral=True,
            )

        # Stop the view.
        self.stop()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Help(bot))
