"""Contains all session logic."""

from __future__ import annotations

__all__ = ["Session", "get_session"]

from enum import Enum, auto
from typing import TYPE_CHECKING, ClassVar, final

if TYPE_CHECKING:
    import discord
    from discord.ext import commands


# Define exception classes.
class SessionError(Exception):
    """Common base class for all session errors."""


@final
class InvalidSessionTypeError(SessionError):
    """Raised when trying to collect messages whitin an invalid session type."""

    def __init__(self) -> None:
        super().__init__("Invalid session type for message collecting.")


@final
class SessionIsEndedError(SessionError):
    """Raised when trying to collect messages whitin an ended session type."""

    def __init__(self) -> None:
        super().__init__("Can't collect messages for an ended session.")


@final
class Session:
    """Represents a session."""

    class SessionTypes(Enum):
        """Represents different session types."""

        GAMBLING = auto()
        MESSAGING = auto()

    sessions: ClassVar[dict[tuple[int, SessionTypes], Session]] = {}

    def __init__(self, user_id: int, type_: SessionTypes) -> None:
        """Initialize session.

        Args:
            user_id (int): User ID of session.
            type_ (Types): Type of the session.

        """
        self.user_id: int = user_id
        self.type: Session.SessionTypes = type_
        self.messages: list[discord.Message] = []

        Session.sessions[(self.user_id, self.type)] = self

    async def collect_message(self, bot: commands.Bot, *, dm_only: bool) -> None:
        """Start collecting discord messages.

        Args:
            bot (commands.Bot): Bot instance.
            dm_only (bool): Whether it should collect messages only from DM or not.

        """
        # Raise an error if trying to collect messages for a non messaging session type.
        if self.type.value != Session.SessionTypes.MESSAGING.value:
            raise InvalidSessionTypeError

        # Raise an error if trying to collect message for an ended session.
        if (self.user_id, self.type) not in Session.sessions:
            raise SessionIsEndedError

        def __check(msg_: discord.Message) -> bool:
            return (
                (msg_.author.id == self.user_id and not msg_.guild)
                if dm_only
                else msg_.author.id == self.user_id
            )

        # Collect messages.
        while (self.user_id, self.type) in Session.sessions:
            msg = await bot.wait_for("message", check=__check)
            self.messages.append(msg)

    def close(self) -> list[discord.Message] | None:
        """Close the session.

        Returns:
            list[Message] | None: Return the list of collected messages if
                 type is messaging else None.

        """
        # End the session.
        _ = Session.sessions.pop((self.user_id, self.type), None)

        # Return the list of messages if session type was messaging.
        if self.type.value == Session.SessionTypes.MESSAGING.value:
            return self.messages

        return None


def get_session(user_id: int, type_: Session.SessionTypes) -> Session | None:
    """Fetch a session.

    Args:
        user_id (int): ID of user.
        type_ (Session.Types): Type of the session.

    Returns:
        Session | None: Return the fetched session.

    """
    return Session.sessions.get((user_id, type_), None)
