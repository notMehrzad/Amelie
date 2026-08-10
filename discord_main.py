#!/usr/bin/env python3

"""The main file of Amélie that needs to be run directly.

It's the entry point for modules.
"""

from __future__ import annotations

__all__ = []

import asyncio
import json
import pkgutil
from itertools import cycle
from pathlib import Path
from typing import NoReturn, TypedDict, cast

import discord
from discord.ext import commands, tasks

from core import terminal
from core.database import initialize_tables
from core.log_handler import setup_logger
from discord_bot import cogs

BOT = commands.Bot(
    command_prefix=".",
    help_command=None,
    intents=discord.Intents.all(),
    case_insensitive=True,
)  # Bot instance


class _Config(TypedDict):
    TOKEN: str
    ADMINS: list[int]


# Read the stored token from config.json file.
with Path("config.json").open("r") as file:
    CONFIG: _Config = cast("_Config", json.load(file))

logger = setup_logger(__name__)


async def _load_cogs() -> None:
    """Load all cogs from cog directory."""
    successful: list[str] = []
    failing: list[str] = []

    solo: list[str] = ["help", "blackjack", "synccommandtree"]

    for module_info in pkgutil.walk_packages(cogs.__path__, cogs.__name__ + "."):
        module_name = module_info.name.split(".")[-1]

        # Skip if it's a directory.
        if module_info.ispkg:
            continue

        if solo and module_name not in solo:
            continue

        try:
            # Load the cog.
            await BOT.load_extension(module_info.name)
            successful.append(module_name)
        except commands.errors.ExtensionError:
            logger.exception("❌ %s couldn't be loaded: ", module_name)
            failing.append(module_name)

    if failing:
        logger.error("%s cogs failed to get loaded ❌", failing)
    logger.info("%s cogs have been loaded ☑️", successful)


async def _terminal_listener() -> NoReturn:
    """Start listening to terminal commands."""
    loop = asyncio.get_running_loop()
    term = terminal.Terminal(BOT)
    while True:
        cmd = await loop.run_in_executor(None, input, ">> ")
        await term.command(cmd)


@BOT.event
async def on_ready() -> None:
    """Print a message when bot is ready."""
    logger.info("--------------\nWe have logged in as %s ✅", BOT.user)

    # Run terminal listener for in-line commands.
    _ = BOT.loop.create_task(_terminal_listener())

    _ = bot_status_change.start()


# Store Amélie's different status.
bot_status = cycle(
    [
        discord.Activity(
            type=discord.ActivityType.playing,
            name="Fortnite",
            platform="PS4",
        ),
        discord.Activity(
            type=discord.ActivityType.playing,
            name="playing with your server",
        ),
        discord.Activity(
            type=discord.ActivityType.listening,
            name="listening to your complaints",
        ),
        discord.Activity(type=discord.ActivityType.watching, name="watching reels"),
        discord.Activity(type=discord.ActivityType.playing, name="lanat be in zendegi"),
    ],
)


@tasks.loop(minutes=2)
async def bot_status_change() -> None:
    """Change bot status message every 2 minutes."""
    await BOT.change_presence(activity=next(bot_status))


async def _main() -> None:
    # Initialize DB tables.
    await initialize_tables()

    async with BOT:
        await _load_cogs()

        try:
            # Start the bot.
            await BOT.start(CONFIG["TOKEN"])
        except Exception:
            logger.critical("❌ Failed to start the bot:", exc_info=True)
            raise


if __name__ == "__main__":
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        logger.info("\n--------------\nThe Bot has been shut down. ⏹️")
