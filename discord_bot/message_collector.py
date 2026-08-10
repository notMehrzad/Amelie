from __future__ import annotations

__all__ = ["MessageCollector"]


from typing import TYPE_CHECKING, final

from core.session import Session, get_session
from discord_main import BOT

if TYPE_CHECKING:
    import discord


# Define exception classes.
class MessageCollectorError(Exception):
    """Common base class for all message collector exceptions."""


@final
class NoSessionFoundError(MessageCollectorError):
    """Raised when trying to collect messages for a user who has no open session."""

    def __init__(self) -> None:
        super().__init__("User has no open session.")


@final
class InvalidSessionTypeError(MessageCollectorError):
    """Raised when trying to collect messages whitin an invalid session type."""

    def __init__(self) -> None:
        super().__init__("Invalid session type for message collecting.")


@final
class MessageCollector:
    """Represents a message collector."""

    def __init__(self, user_id: int) -> None:
        """Initialize a message collector.

        Args:
            user_id (int): ID of the message collector owner.

        """
        self.user_id: int = user_id
        self.messages: list[discord.Message] = []

    async def collect_message(self, *, dm_only: bool) -> None:
        """Start collecting discord messages.

        Access the collected messages using MessageCollector.messages.

        Args:
            user_id (int): User ID to collect messages for.
            dm_only (bool): Whether it should collect messages only from DM or not.

        """
        # Fetch user's session.
        session = get_session(self.user_id, Session.SessionTypes.MESSAGING)
        if session is None:
            raise NoSessionFoundError

        # Raise an error if trying to collect messages for a non messaging session type.
        if session.type.value != Session.SessionTypes.MESSAGING.value:
            raise InvalidSessionTypeError

        def __check(msg_: discord.Message) -> bool:
            return (
                (msg_.author.id == self.user_id and not msg_.guild)
                if dm_only
                else msg_.author.id == self.user_id
            )

        # Collect messages.
        while get_session(self.user_id, Session.SessionTypes.MESSAGING) is not None:
            msg = await BOT.wait_for("message", check=__check)
            self.messages.append(msg)
