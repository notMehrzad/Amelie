"""/help command."""

from __future__ import annotations

__all__ = []

import contextlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, cast, final

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from arg_parser import parse_args
from core.help import ExtrasTyped, HelpData
from core.help_data_constants import HELP_HELP

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery

ROUTER = Router(name=__name__)

with Path("config.json").open("r") as file:
    CONFIG = json.load(file)


def _create_message(help_data: HelpData) -> str:
    """Create a help message.

    Args:
        help_data (HelpData): Help data of the command.

    Returns:
        str: Return the message.

    """
    msg = (
        f"/{help_data.name}"
        f"\n\n{
            help_data.help
            or help_data.brief
            or '*No description provided for this command.*'
        }"
    )
    # Add Aliases field if command has aliases.
    if help_data.aliases:
        msg += f"\n\nAliases: {' - '.join(help_data.aliases)}"

    # Add Usage field if command has usage.
    if help_data.usage:
        msg += f"\n\nUsage: /{help_data.name} {help_data.usage}"

    extras: ExtrasTyped = cast("ExtrasTyped", help_data.extras)
    # Add Subcommand field if command has subcommands.
    if extras["subcommands"]:
        msg += f"\n\nSubcommands: {' - '.join(extras['subcommands'])}"

    # Add DM-only field if command is DM strict.
    if extras["dm_only"]:
        msg += "\n\nDM-only: Yes"

    # Add Server-only field if command is server strict.
    if extras["server_only"]:
        msg += "\n\nServer-only: Yes"

    # Add Permission field if command needs some permissions.
    if extras["permissions"]:
        msg += f"\n\nPermissions: {' - '.join(extras['permissions'])}"

    return msg


@ROUTER.message(Command(HELP_HELP.name, *HELP_HELP.aliases, ignore_case=True))
@parse_args
async def help_(message: Message, command_: str | None) -> None:
    if message.from_user is None:
        return

    show_hidden: bool = bool(
        str(message.from_user.id) in CONFIG["TELEGRAM_ADMINS"]
        and message.chat.type == "private",
    )

    # Show command help if user wants help for a specific command.
    if command_ and command_.lower() not in ("all", "list", "menu"):
        # Fetch the command.
        help_data = HelpData.get_help(command_.lower())

        # Raise an error if the command can't be fetched.
        if help_data is None:
            await message.answer(f"*{command_}* doesn't exist. Enter a valid command.")
            return

        if isinstance(help_data, HelpData):
            # Raise an error if command is hidden and user isn't a developer.
            if help_data.is_hidden and not show_hidden:
                await message.answer("Help menu for this command is not avaiable.")
                return

            msg = _create_message(help_data)

            # Send help message.
            await message.answer(msg)

    # Show help menu if user enters no command name.
    else:
        categorized = HelpData.get_help(show_hidden=show_hidden)

        if isinstance(categorized, dict):
            # Define a list to store different category embed.
            pages: list[str] = []
            for category, help_datas in categorized.items():
                msg = category
                # Add command field for each command.
                for help_data in help_datas:
                    msg += (
                        f"\n\n-/{help_data.name} :"
                        f"\n{help_data.brief or '*No description.*'}"
                    )

                pages.append(msg)

            # Show the only embed if there's only one embed.
            if len(pages) == 1:
                await message.answer(pages[0])

            # Send the view if there's multiple embeds.
            else:
                await HelpView(message, pages).start()


@final
class ButtonCallback(CallbackData, prefix="help"):
    user_id: int
    action: str


@final
class HelpView:
    timeout = 60

    views: ClassVar[dict[int, HelpView]] = {}

    def __init__(self, message: Message, pages: list[str]) -> None:
        self.message: Message = message
        if message.from_user:
            self.user = message.from_user
        self.pages: list[str] = pages
        self.page_index: int = 0
        self.expires_at: datetime = datetime.now(timezone.utc) + timedelta(
            seconds=HelpView.timeout,
        )

        HelpView.views[self.user.id] = self

    @property
    def is_timedout(self) -> bool:
        """Whether the view is timedout."""
        return datetime.now(timezone.utc) >= self.expires_at

    async def start(self) -> None:
        """Start the view."""
        # Add related buttons.
        self.builder = InlineKeyboardBuilder()
        self.builder.button(
            text="◀️",
            callback_data=ButtonCallback(user_id=self.user.id, action="previous"),
        )
        self.builder.button(
            text="▶️",
            callback_data=ButtonCallback(user_id=self.user.id, action="next"),
        )
        self.builder.button(
            text="close",
            callback_data=ButtonCallback(user_id=self.user.id, action="close"),
        )
        self.builder.adjust(2, 1)

        self.msg = await self.message.answer(
            text=self.pages[0],
            reply_markup=self.builder.as_markup(),
        )  # sends the first page of the help menu

    async def on_timeout(self) -> None:
        # Remove the buttons on timeout.
        with contextlib.suppress(TelegramBadRequest):
            await self.msg.delete_reply_markup()


# previous button
@ROUTER.callback_query(ButtonCallback.filter(F.action == "previous"))
async def previous(
    callback: CallbackQuery,
    callback_data: ButtonCallback,
) -> None:
    await callback.answer()

    # Raise an error if interaction is not from the user.
    if callback.from_user.id != callback_data.user_id:
        await callback.answer("You can't control this help menu. try `/help` yourself.")
        return

    view = HelpView.views.get(callback_data.user_id)

    # Timeout the view if it's expired.
    if view is None or view.is_timedout:
        if isinstance(callback.message, Message):
            await callback.message.delete_reply_markup()
        return

    # Calculate the index number of the previous page.
    view.page_index = (view.page_index - 1) % len(view.pages)

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            text=view.pages[view.page_index],
            reply_markup=view.builder.as_markup(),
        )


# next button
@ROUTER.callback_query(ButtonCallback.filter(F.action == "next"))
async def next_(callback: CallbackQuery, callback_data: ButtonCallback) -> None:
    await callback.answer()

    # Raise an error if interaction is not from the user.
    if callback.from_user.id != callback_data.user_id:
        await callback.answer("You can't control this help menu. try `/help` yourself.")
        return

    view = HelpView.views.get(callback_data.user_id)

    # Timeout the view if it's expired.
    if view is None or view.is_timedout:
        if isinstance(callback.message, Message):
            await callback.message.delete_reply_markup()
        return

    # Calculate the index number of the next page.
    view.page_index = (view.page_index + 1) % len(view.pages)

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            text=view.pages[view.page_index],
            reply_markup=view.builder.as_markup(),
        )


# close button
@ROUTER.callback_query(ButtonCallback.filter(F.action == "close"))
async def close(callback: CallbackQuery, callback_data: ButtonCallback) -> None:
    await callback.answer()

    # Raise an error if interaction is not from the user.
    if callback.from_user.id != callback_data.user_id:
        await callback.answer("You can't control this help menu. try `/help` yourself.")
        return

    view = HelpView.views.get(callback_data.user_id)

    # Timeout the view if it's expired.
    if view is None or view.is_timedout:
        if isinstance(callback.message, Message):
            await callback.message.delete_reply_markup()
        return

    # Delete the help menu.
    if isinstance(callback.message, Message):
        await callback.message.delete()
