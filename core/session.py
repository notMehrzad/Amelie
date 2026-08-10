"""Contains all session logic."""

from __future__ import annotations

__all__ = ["Session", "get_session"]

from enum import Enum, auto
from typing import TYPE_CHECKING, ClassVar, final

if TYPE_CHECKING:
    import discord


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
