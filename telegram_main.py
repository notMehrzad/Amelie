"""The main telegram file of Amélie that needs to be run directly.

It's the entry point for routers.
"""

from __future__ import annotations

__all__ = []

import asyncio
import importlib
import json
import pkgutil
from pathlib import Path
from typing import TypedDict, cast

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from core.database import initialize_tables
from core.log_handler import setup_logger
from telegram_bot import routers

CONFIG_DIR = Path("telegram_bot") / "config.json"


class _Config(TypedDict):
    TOKEN: str
    ADMINS: list[int]


with CONFIG_DIR.open("r") as file:
    CONFIG: _Config = cast("_Config", json.load(file))
BOT = Bot(
    token=CONFIG["TOKEN"],
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)  # Telegram bot instance

logger = setup_logger(__name__)


def _load_router(dp: Dispatcher) -> None:
    """Load the routers from the directory.

    Args:
        dp (Dispatcher): Dispatcher to add the routers to.

    """
    successful: list[str] = []

    solo: list[str] = ["flipcoin", "rolldice"]

    for modul_info in pkgutil.walk_packages(
        routers.__path__,
        routers.__name__ + ".",
    ):
        module_name = modul_info.name.split(".")[-1]

        # Skip if it's a directory.
        if modul_info.ispkg:
            continue

        if solo and module_name not in solo:
            continue

        # Import the module.
        module = importlib.import_module(modul_info.name)
        # Check if the module has a router attribute.
        if hasattr(module, "ROUTER"):
            # Include the router to the dispatcher.
            dp.include_router(module.ROUTER)
            successful.append(module_name)

    logger.info("%s routers have been loaded ☑️", successful)


async def _main() -> None:
    # Initialize DB tables.
    await initialize_tables()

    async with BOT:
        # Initialize dispatcher.
        dp = Dispatcher()
        # Load all routers.
        _load_router(dp)

        # Log a message when bot is ready.
        me = await BOT.get_me()
        logger.info("-" * 14)
        logger.info("We have logged in as %s ✅", me.username)

        # Start listening to events.
        await dp.start_polling(BOT)  # pyright: ignore[reportUnknownMemberType]


if __name__ == "__main__":
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        logger.info("\n--------------\nThe Bot has been shut down. ⏹️")
