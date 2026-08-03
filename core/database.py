"""Contains the logic and structure of database(aiosqlite) that Amélie uses.

It simplifies the process of executing or fetching data using a handler that manages
creating connection, commiting changes and closing connection automatically with just
simple functions.
Custom functions can be made and used like _run(CustomFunction).
"""

from __future__ import annotations

__all__ = ["execute", "fetchall", "fetchone", "initialize_tables"]

from typing import TYPE_CHECKING, Any, TypeVar

import aiosqlite

from core.dbconstants import (
    AccountTable,
    AnonSessionTable,
    AnonymousContactTable,
    AnonymousUserTable,
    CheckTable,
    InventoryTable,
    LotteryTable,
    TicketTable,
    TransactionTable,
    WarnTable,
)
from core.log_handler import setup_logger

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable
    from sqlite3 import Row


DATABASE_PATH = "bot_database.db"
TABLES: tuple[str, ...] = (
    f"""
    CREATE TABLE IF NOT EXISTS {AccountTable.TABLE_NAME} (
        {AccountTable.COL_USER_ID} INTEGER PRIMARY KEY NOT NULL,
        {AccountTable.COL_BALANCE} INTEGER NOT NULL,
        {AccountTable.COL_CREATED_AT} INTEGER NOT NULL,
        {AccountTable.COL_LAST_DAILY_DATE} INTEGER,
        {AccountTable.COL_LAST_WORK_DATE} INTEGER
    );
    """,
    f"""
    CREATE TABLE IF NOT EXISTS {AnonymousContactTable.TABLE_NAME} (
        {AnonymousContactTable.COL_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
        {AnonymousContactTable.COL_RECIPIENT_ID} INTEGER NOT NULL,
        {AnonymousContactTable.COL_USER_ID} INTEGER NOT NULL,
        {AnonymousContactTable.COL_ALIAS} TEXT NOT NULL,
        {AnonymousContactTable.COL_IS_BLOCKED} BOOLEAN DEFAULT FALSE,
        FOREIGN KEY ({AnonymousContactTable.COL_RECIPIENT_ID}) REFERENCES
        {AnonymousUserTable.TABLE_NAME}({AnonymousUserTable.COL_USER_ID}),
        UNIQUE({AnonymousContactTable.COL_RECIPIENT_ID},
        {AnonymousContactTable.COL_USER_ID}),
        UNIQUE({AnonymousContactTable.COL_RECIPIENT_ID},
        {AnonymousContactTable.COL_ALIAS})
    );
    """,
    f"""
    CREATE TABLE IF NOT EXISTS {AnonSessionTable.TABLE_NAME} (
        {AnonSessionTable.COL_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
        {AnonSessionTable.COL_SESSION_ID} INTEGER NOT NULL,
        {AnonSessionTable.COL_RECEIVER_ID} INTEGER NOT NULL,
        {AnonSessionTable.COL_CONTACT_ANON_ID} TEXT NOT NULL,
        {AnonSessionTable.COL_CONTACT_MESSAGE_COLLECTOR_ID} INTEGER NOT NULL,
        {AnonSessionTable.COL_SESSION_DATE} DATETIME DEFAULT CURRENT_TIMESTAMP,
        {AnonSessionTable.COL_RESPONDED} INTEGER DEFAULT 0,
        FOREIGN KEY ({AnonSessionTable.COL_RECEIVER_ID}) REFERENCES
        {AnonymousUserTable.TABLE_NAME}({AnonymousUserTable.COL_USER_ID}),
        UNIQUE({AnonSessionTable.COL_RECEIVER_ID},
        {AnonSessionTable.COL_CONTACT_ANON_ID}, {AnonSessionTable.COL_SESSION_ID})
    );
    """,
    f"""
    CREATE TABLE IF NOT EXISTS {AnonymousUserTable.TABLE_NAME} (
        {AnonymousUserTable.COL_USER_ID} INTEGER PRIMARY KEY NOT NULL,
        {AnonymousUserTable.COL_PUBLIC_ID} TEXT NOT NULL,
        {AnonymousUserTable.COL_CREATED_AT} INTEGER NOT NULL
    );
    """,
    f"""
    CREATE TABLE IF NOT EXISTS {CheckTable.TABLE_NAME} (
        {CheckTable.COL_ID} TEXT PRIMARY KEY NOT NULL,
        {CheckTable.COL_SENDER_ID} INTEGER NOT NULL,
        {CheckTable.COL_AMOUNT} INTEGER NOT NULL,
        {CheckTable.COL_RECEIVER_ID} INTEGER NOT NULL,
        {CheckTable.COL_MEMO} TEXT,
        {CheckTable.COL_ISSUED_AT} INTEGER NOT NULL,
        {CheckTable.COL_IS_CASHED} BOOLEAN DEFAULT FALSE
    );
    """,
    f"""
    CREATE TABLE IF NOT EXISTS {InventoryTable.TABLE_NAME} (
        {InventoryTable.COL_USER_ID} INTEGER NOT NULL,
        {InventoryTable.COL_ITEM_NAME} TEXT NOT NULL,
        {InventoryTable.COL_QUANTITY} INTEGER NOT NULL,
        PRIMARY KEY ({InventoryTable.COL_USER_ID}, {InventoryTable.COL_ITEM_NAME})
    );
    """,
    f"""
    CREATE TABLE IF NOT EXISTS {LotteryTable.TABLE_NAME} (
        {LotteryTable.COL_USER_ID} INTEGER PRIMARY KEY NOT NULL,
        {LotteryTable.COL_SIGNED_AT} DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """,
    f"""
    CREATE TABLE IF NOT EXISTS {TicketTable.TABLE_NAME} (
        {TicketTable.COL_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
        {TicketTable.COL_USER_ID} INTEGER NOT NULL,
        {TicketTable.COL_MESSAGE_COLLECTOR_ID} INTEGER NOT NULL,
        {TicketTable.COL_SUBJECT} TEXT NOT NULL,
        {TicketTable.COL_STATE} TEXT NOT NULL DEFAULT "open",
        {TicketTable.COL_CREATED_AT} DATETIME DEFAULT CURRENT_TIMESTAMP,
        {TicketTable.COL_CLOSED_AT} DATETIME
    );
    """,
    f"""
    CREATE TABLE IF NOT EXISTS {TransactionTable.TABLE_NAME} (
        {TransactionTable.COL_ID} TEXT PRIMARY KEY NOT NULL,
        {TransactionTable.COL_TYPE} TEXT NOT NULL,
        {TransactionTable.COL_USER_ID} INTEGER NOT NULL,
        {TransactionTable.COL_AMOUNT} INTEGER NOT NULL,
        {TransactionTable.COL_CREATED_AT} INTEGER NOT NULL,
        {TransactionTable.COL_RECEIVER_ID} INTEGER,
        {TransactionTable.COL_MEMO} TEXT
    );
    """,
    f"""
    CREATE TABLE IF NOT EXISTS {WarnTable.TABLE_NAME} (
        {WarnTable.COL_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
        {WarnTable.COL_SERVER_ID} INTEGER NOT NULL,
        {WarnTable.COL_USER_WARN_ID} INTEGER NOT NULL,
        {WarnTable.COL_MOD_ID} INTEGER NOT NULL,
        {WarnTable.COL_USER_ID} INTEGER NOT NULL,
        {WarnTable.COL_REASON} TEXT,
        {WarnTable.COL_TIMESTAMP} DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """,
)

T = TypeVar("T")
logger = setup_logger(__name__)


async def _run(func: Callable[..., Awaitable[T]]) -> T:
    """Core function to run DB commands.

    Every database function must be called inside this function to be run and executed
    properly.

    Args:
        func (Callable[..., Awaitable[T]]): Function to be run.

    Returns:
        T: Varies from function it runs to another.

    """
    # Connect to database.
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("PRAGMA foreign_keys = ON"):
            pass
        async with db.execute("PRAGMA journal_mode = WAL"):
            pass

        # Run the command.
        return await func(db)


async def execute(query: str, params: Iterable[Any] | None = None) -> None:
    """Execute a SQL query in aiosqlite.

    Args:
        query (str): Query to execute.
        params (Iterable[Any] | None, optional): Parameters to pass. Defaults
            to None.

    """

    async def _execute(conn: aiosqlite.Connection) -> None:
        try:
            async with conn.execute(query, params):
                pass
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise

    return await _run(_execute)


async def fetchone(
    query: str,
    params: Iterable[Any] | None = None,
) -> Row | None:
    """Fetch a row in aiosqlite.

    Args:
        query (str): Query to fetch.
        params (Iterable[Any, ...] | None, optional): Parameters to pass.
            Defaults to None.

    Returns:
        Row | None: Return fetched Row if it's found. `None`, otherwise.

    """

    async def _fetchone(conn: aiosqlite.Connection) -> Row | None:
        try:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(query, params) as cursor:
                return await cursor.fetchone()
        except Exception:
            await conn.rollback()
            raise

    return await _run(_fetchone)


async def fetchall(
    query: str,
    params: Iterable[Any] | None = None,
) -> Iterable[Row]:
    """Fetch all rows in aiosqlite.

    Args:
        query (str): Query to fetch.
        params (Iterable[Any, ...] | None, optional): Parameters to pass. Defaults to
            None.

    Returns:
        Iterable[Row]: Return An iterable containing the fetched rows.

    """

    async def _fetchall(conn: aiosqlite.Connection) -> Iterable[Row]:
        try:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(query, params) as cursor:
                return await cursor.fetchall()
        except Exception:
            await conn.rollback()
            raise

    return await _run(_fetchall)


async def initialize_tables() -> None:
    """Initialize new database tables."""

    async def _initialize_tables(conn: aiosqlite.Connection) -> None:
        try:
            # Execute every table initialization.
            for table in TABLES:
                _ = await conn.execute(table)
            # Commit changes.
            await conn.commit()

            logger.info("💾 Database tables have been initialized successfully.")
        except Exception:
            await conn.rollback()

            logger.exception("❌ Failed to initialize database tables.")

    return await _run(_initialize_tables)
