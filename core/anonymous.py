"""Contains the logic core of the anonymous messaging system."""

from __future__ import annotations

__all__ = ["create_anonymous_user", "get_anonymous_user"]

from datetime import datetime, timezone
from typing import final

from core.database import execute, fetchall, fetchone
from core.dbconstants import AnonymousContactTable, AnonymousUserTable
from core.utils import generate_id

PUBLIC_ID_LENGTH = 12
ALIAS_LENGTH = 6


# Define exception classes.
class AnonymousError(Exception):
    """Common base class for all anonymous exceptions."""


@final
class ContactAlreadyExistsError(AnonymousError):
    """Raised when trying to add an anonymous contact that exists in contact book."""

    def __init__(self) -> None:
        super().__init__("Anonymous contact already exists in user's contact book.")


@final
class AnonymousUserAlreadyExistsError(AnonymousError):
    """Raised when trying to create an anonymous user for a user who already has one."""

    def __init__(self) -> None:
        super().__init__("User already has an anonymous account.")


@final
class Contact:
    """Represents an anonymous contact."""

    def __init__(self, *, user_id: int, alias: str, is_blocked: bool = False) -> None:
        """Initialize an anonymous contact."""
        self.user_id = user_id
        self.alias = alias
        self.is_blocked = is_blocked


@final
class ContactBook:
    """Represents a contact book."""

    def __init__(self) -> None:
        """Initialize a contact book."""
        self.by_user_id: dict[int, Contact] = {}
        self.by_alias: dict[str, Contact] = {}

    def get_by_user_id(self, user_id: int) -> Contact | None:
        return self.by_user_id.get(user_id)

    def get_by_alias(self, alias: str) -> Contact | None:
        return self.by_alias.get(alias)


@final
class AnonymousUser:
    """Represents an anonymous user."""

    def __init__(self, user_id: int, public_id: str) -> None:
        """Initialize anonymous user.

        Args:
            user_id (int): Real ID of user.
            public_id (str): Public ID of user.

        """
        self.user_id: int = user_id
        self.public_id: str = public_id
        self.contacts: ContactBook = ContactBook()

    async def add_contact(self, user_id: int) -> Contact:
        """Create anonymous contact.

        Args:
            user_id (int): Real ID of the anonymous user.

        Raises:
            ContactAlreadyExistsError: Raise when contact already exists.

        Returns:
            Contact: Return the added contact.

        """
        # Fetch contact book.
        contact = self.contacts.get_by_user_id(user_id)
        # If contact already exists, raise an error.
        if contact is not None:
            raise ContactAlreadyExistsError

        # Create an alias for the contact.
        alias = await _generate_alias(self.user_id)

        # Save the contact in DB.
        await execute(
            f"""
            INSERT INTO {AnonymousContactTable.TABLE_NAME}
            ({AnonymousContactTable.columns()})
            VALUES (?, ?, ?, ?, ?);
            """,  # noqa: S608
            (None, self.user_id, user_id, alias, False),
        )

        contact = Contact(user_id=user_id, alias=alias)
        self.contacts.by_user_id[user_id] = contact
        self.contacts.by_alias[alias] = contact

        return contact


async def _generate_public_id() -> str:
    """Generate a public ID for an anonymous user.

    Returns:
        str: Return a unique public ID.

    """
    while True:
        public_id = generate_id(PUBLIC_ID_LENGTH)
        user = await fetchone(
            f"""
            SELECT 1 FROM {AnonymousUserTable.TABLE_NAME}
            WHERE {AnonymousUserTable.COL_PUBLIC_ID} = ?
            """,  # noqa: S608
            (public_id,),
        )
        if user is None:
            return public_id


async def _generate_alias(user_id: int) -> str:
    """Generate an alias for a contact.

    Args:
        user_id (int): Real ID of the user whos contact is being created.

    Returns:
        str: Return a unique alias.

    """
    while True:
        alias = generate_id(ALIAS_LENGTH)
        contact = await fetchone(
            f"""
            SELECT 1 FROM {AnonymousContactTable.TABLE_NAME}
            WHERE {AnonymousContactTable.COL_RECIPIENT_ID} = ?
            AND {AnonymousContactTable.COL_ALIAS} = ?;
            """,  # noqa: S608
            (user_id, alias),
        )
        if contact is None:
            return alias


async def create_anonymous_user(user_id: int) -> AnonymousUser:
    """Create anonymous user.

    Args:
        user_id (int): Real ID of user.

    Raises:
        AnonUserExistsAlreadyError: Raise when trying to create an anonymous account for
        a user who already has one.

    Returns:
        AnonUser: Return created anonymous user.

    """
    # Check if user with given real ID already has an anonymous account.
    user = await get_anonymous_user(user_id=user_id)
    # Raise an error if user already has an anonymous account.
    if user is not None:
        raise AnonymousUserAlreadyExistsError

    now = datetime.now(timezone.utc)  # Creation date

    # Generate account's public ID.
    public_id = await _generate_public_id()

    # Store in DB.
    await execute(
        f"""
        INSERT INTO {AnonymousUserTable.TABLE_NAME} ({AnonymousUserTable.columns()})
        VALUES (?, ?, ?);
        """,  # noqa: S608
        (user_id, public_id, int(now.timestamp())),
    )
    # Return the created account instance.
    return AnonymousUser(user_id, public_id)


async def get_anonymous_user(
    *,
    user_id: int | None = None,
    public_id: str | None = None,
) -> AnonymousUser | None:
    """Fetch an anonymous user.

    Can be done either with user ID or user's public ID so at least one of them must be
    given.

    Args:
        user_id (int | None, optional): Real ID of user. Defaults to None.
        public_id (str | None, optional): Public ID of user. Defaults to None.

    Raises:
        ValueError: Raise when neither user ID or user's public ID is given.

    Returns:
        AnonUser | None: Return fetched anonymous user. None, not found.

    """
    if user_id is not None:
        user = await fetchone(
            f"""
            SELECT {AnonymousUserTable.COL_USER_ID}, {AnonymousUserTable.COL_PUBLIC_ID}
            FROM {AnonymousUserTable.TABLE_NAME}
            WHERE {AnonymousUserTable.COL_USER_ID} = ?;
            """,  # noqa: S608
            (user_id,),
        )

    elif public_id is not None:
        user = await fetchone(
            f"""
            SELECT {AnonymousUserTable.COL_USER_ID}, {AnonymousUserTable.COL_PUBLIC_ID}
            FROM {AnonymousUserTable.TABLE_NAME}
            WHERE {AnonymousUserTable.COL_PUBLIC_ID} = ?;
            """,  # noqa: S608
            (public_id,),
        )

    else:
        msg = "At least one argument must be given."
        raise ValueError(msg)

    # Return None if user has no public anonymous ID.
    if user is None:
        return None

    user_id = int(user[AnonymousUserTable.COL_USER_ID])
    public_id = str(user[AnonymousUserTable.COL_PUBLIC_ID])

    if len(public_id) != PUBLIC_ID_LENGTH:
        public_id = await _generate_public_id()
        await execute(
            f"""
            UPDATE {AnonymousUserTable.TABLE_NAME}
            SET {AnonymousUserTable.COL_PUBLIC_ID} = ?
            WHERE {AnonymousUserTable.COL_USER_ID} = ?;
            """,  # noqa: S608
            (public_id, user_id),
        )

    user = AnonymousUser(user_id, public_id)

    # Fetch user's anonymous contacts.
    contacts = await fetchall(
        f"""
        SELECT {AnonymousContactTable.COL_USER_ID}, {AnonymousContactTable.COL_ALIAS}
        , {AnonymousContactTable.COL_IS_BLOCKED} from {AnonymousContactTable.TABLE_NAME}
        WHERE {AnonymousContactTable.COL_RECIPIENT_ID} = ?;
        """,  # noqa: S608
        (user_id,),
    )
    if contacts:
        for contact in contacts:
            contact_ = Contact(
                user_id=contact[AnonymousContactTable.COL_USER_ID],
                alias=contact[AnonymousContactTable.COL_ALIAS],
                is_blocked=contact[AnonymousContactTable.COL_IS_BLOCKED],
            )
            user.contacts.by_user_id[contact[AnonymousContactTable.COL_USER_ID]] = (
                contact_
            )
            user.contacts.by_alias[contact[AnonymousContactTable.COL_ALIAS]] = contact_

    return user
