"""synccommandtree command."""

from __future__ import annotations

__all__ = []

import json
from pathlib import Path
from typing import final

from discord import errors
from discord.ext import commands

from core.help import HelpData
from core.log_handler import setup_logger

with Path("config.json").open("r") as file:
    CONFIG = json.load(file)

HELP = HelpData(
    is_enabled=True,
    name="synccommandtree",
    category=HelpData.CommandCategory.DEV,
    is_dm_only=False,
    is_server_only=False,
    subcommands=None,
    permissions=None,
    help_=None,
    brief="Syncs and updates slash commands.",
    usage=None,
    aliases=["synccommand", "syncc", "sct"],
    is_hidden=True,
)

logger = setup_logger(__name__)


@final
class SyncCommandTree(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="commandsync", hidden=True, **HELP.kwargs)
    async def synccommandtree(self, ctx: commands.Context[commands.Bot]) -> None:
        is_in_guild = ctx.guild is not None

        # Raise an error if user isn't a developer.
        if str(ctx.author.id) not in CONFIG["ADMINS"]:
            msg = await ctx.reply("You can't use this command.")
            # Delete the messages if it's in a guild.
            if is_in_guild:
                await msg.delete(delay=5)
                await ctx.message.delete()
            return

        # Sync the commands.
        try:
            synced_commands = await self.bot.tree.sync()
            synced_commands = [(f"/{cmd.name}") for cmd in synced_commands]
            logger.info(
                "\n--------------\n%s commands have been synced. ✔️",
                synced_commands,
            )
        except errors.HTTPException:
            logger.exception("Syncing command tree failed ❌")

        # Send succession notification.
        msg = await ctx.reply("All slash commands have been synced.")
        if is_in_guild:
            await msg.delete(delay=5)
            await ctx.message.delete(delay=5)

        return

    @synccommandtree.error
    async def synccommandtree_error(
        self,
        ctx: commands.Context[commands.Bot],
        error: commands.CommandError,
    ) -> None:
        logger.error(
            "❌ Something went wrong with commandsync command:",
            exc_info=error,
        )
        await ctx.reply("Something went wrong with **commandsync**.", delete_after=5)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SyncCommandTree(bot))
