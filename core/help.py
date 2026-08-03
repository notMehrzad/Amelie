"""Contains the structure and logic of the command's help.

It makes it easier to make and generate helps for various commands rather than
old-fashion handwritten helps.
"""

from __future__ import annotations

__all__ = ["ExtrasTyped", "HelpData"]

from enum import Enum, auto
from typing import Any, ClassVar, TypedDict, cast, final


class ExtrasTyped(TypedDict):
    """Represents command extras attribute type."""

    category: str
    dm_only: bool
    server_only: bool
    subcommands: list[str]
    permissions: list[str]


class _KwargsTyped(TypedDict):
    """Represents command kwargs type."""

    enabled: bool
    help: str | None
    brief: str
    usage: str | None
    aliases: list[str]
    extras: dict[Any, Any]


@final
class HelpData:
    """Represents a command help data."""

    helps: ClassVar[dict[str, HelpData]] = {}

    class CommandCategory(Enum):
        """Represents different command categories."""

        ANONYMOUSE = auto()
        DEV = auto()
        ECONOMY = auto()
        GAMES = auto()
        MODERATION = auto()
        UTILITY = auto()
        MISC = auto()

    def __init__(  # noqa: PLR0913
        self,
        *,
        is_enabled: bool,
        name: str,
        category: CommandCategory,
        is_dm_only: bool,
        is_server_only: bool,
        subcommands: list[str] | None,
        permissions: list[str] | None,
        help_: str | None,
        brief: str,
        usage: str | None,
        aliases: list[str] | None,
        is_hidden: bool,
    ) -> None:
        """Initialize help data.

        Args:
            is_enabled (bool): Whether the command is enabled.
            name (str): Name of command.
            category (CommandCategory): Category of command.
            is_dm_only (bool): Whether the command is DM-restricted.
            is_server_only (bool): Whether the command is guild-restricted.
            subcommands (list[str] | None): Subcommands of command.
            permissions (list[str] | None): Required permissions to run the
                command.
            help_ (str | None): Long command help text.
            brief (str): Short command help text.
            usage (str | None): Usage format of command.
            aliases (list[str] | None): Aliases of command.
            is_hidden (bool, optional): Whether command should be hidden. Defaults to
                False.

        """
        self.is_enabled: bool = is_enabled
        self.name: str = name.lower()
        self.category: str = category.name.title()
        self.is_dm_only: bool = is_dm_only
        self.is_server_only: bool = is_server_only
        self.subcommands: list[str] = subcommands or []
        self.permissions: list[str] = permissions or []
        self.help: str | None = help_
        self.brief: str = brief
        self.usage: str | None = usage
        self.aliases: list[str] = aliases or []
        self.is_hidden: bool = is_hidden

        HelpData.helps[self.name] = self
        for alias in self.aliases:
            HelpData.helps[alias] = HelpData.helps[self.name]

    @property
    def extras(self) -> dict[Any, Any]:
        """Return extras attributes."""
        extras: ExtrasTyped = {
            "category": self.category,
            "dm_only": self.is_dm_only,
            "server_only": self.is_server_only,
            "subcommands": self.subcommands,
            "permissions": self.permissions,
        }
        return cast("dict[Any, Any]", extras)

    @property
    def kwargs(self) -> _KwargsTyped:
        """Return attributes as a dict(keywords) to pass."""
        return {
            "enabled": self.is_enabled,
            "help": self.help,
            "brief": self.brief,
            "usage": self.usage,
            "aliases": self.aliases,
            "extras": self.extras,
        }

    @classmethod
    def get_help(
        cls,
        command: str | None = None,
        *,
        show_hidden: bool = False,
    ) -> HelpData | None | dict[str, list[HelpData]]:
        """Get the help data of a command.

        Args:
            command (str | None, optional): Name of command. Defaults to None.
            show_hidden (bool, optional): Whether the hidden commands should be shown.

        Returns:
            dict[str, list[HelpData]] | HelpData | None: Return the sorted dictionary of
                categories containing their commands in a list or the help data of the
                specified command or None if the command help data can't be fetched.

        """
        # Get help data of a specific command.
        if command is not None:
            return cls.helps.get(command)

        # Define a dictionary to store every command category commands.
        categorized: dict[str, list[HelpData]] = {}

        # Fetch all commands.
        for cmd, help_data in cls.helps.items():
            # Skip the hidden commands.
            if help_data.is_hidden and not show_hidden:
                continue

            # Skip aliases.
            if cmd != help_data.name:
                continue

            # Fetch command's category.
            category = help_data.extras.get("category", "etc.")
            # Add the command and the category to the dictionary.
            categorized.setdefault(category, []).append(help_data)

        # Sort the commands of each category.
        for help_datas in categorized.values():
            help_datas.sort(key=lambda help_data: help_data.name)

        # Sort the categories dictionary and return it.
        return dict(
            sorted(categorized.items(), key=lambda item: item[0].lower()),
        )
