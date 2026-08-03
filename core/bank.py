"""Contains the core structure of Bank system.

It contains all the logic such as required classes and related functions to do various
operations listed below:
1- Accounts: creating, depositing, withdrawing etc.
2- Checks: issuing and depositing
3- Transactions: Storing transactions

Also, it should be noted that the logic in this module is only and only made for
Amelie's developers' workspace ease and no real user should be able to work, interact or
see any of the operations, messages or raised errors below.
"""

from __future__ import annotations

__all__ = [
    "FORMATTED_CURRENCY",
    "AccountAlreadyExistsError",
    "AccountNotFoundError",
    "BankAccount",
    "BankError",
    "Check",
    "CheckAlreadyCashedError",
    "CheckAlreadyIssuedError",
    "InsufficientBalanceError",
    "close_bank_account",
    "create_bank_account",
    "get_bank_account",
    "get_bank_check",
    "issue_bank_check",
    "transfer",
]

import uuid
from datetime import datetime, timezone
from enum import Enum, auto
from typing import final

from core.database import execute, fetchone
from core.dbconstants import AccountTable, CheckTable, TransactionTable

# Define currency information.
CURRENCY_NAME = "Cookie"
CURRENCY_ICON = "<:1lvl:1027191671328354304>"  # discord emoji
FORMATTED_CURRENCY = CURRENCY_ICON + " " + CURRENCY_NAME + "s"


# Define exception classes.
class BankError(Exception):
    """Common base class for all bank exceptions."""


@final
class AccountAlreadyExistsError(BankError):
    """Raised when trying to create an account for a user who already has one."""

    def __init__(self) -> None:
        """Initialize exception."""
        super().__init__("User already has an account.")


@final
class AccountNotFoundError(BankError):
    """Raised when trying to do an operation on an account that doesn't exist."""

    def __init__(self) -> None:
        """Initialize exception."""
        super().__init__("Account doesn't exist.")


@final
class CheckAlreadyCashedError(BankError):
    """Raised when trying to deposit a check that is already deposited."""

    def __init__(self, check: Check) -> None:
        """Initialize exception."""
        self.check: Check = check
        super().__init__(f"{self.check.check_id}: Check has been already deposited.")


@final
class CheckAlreadyIssuedError(BankError):
    """Raised when trying to issue a check that is issued already."""

    def __init__(self, check: Check) -> None:
        """Initialize exception."""
        self.check: Check = check
        super().__init__(f"{self.check.check_id}: Check has been already issued.")


@final
class InsufficientBalanceError(BankError):
    """Raised when trying to transfer an amount of balance that is insufficient."""

    def __init__(self) -> None:
        """Initialize exception."""
        super().__init__("The balance amount is insufficient for the operation.")


@final
class BankAccount:
    """Represents a bank Account."""

    def __init__(
        self,
        *,
        user_id: int,
        balance: float = 0,
    ) -> None:
        """Initialize a bank account.

        Args:
            user_id (int): ID of the user.
            balance (float, optional): Initial balance of the account. Defaults to 0.

        Raises:
            ValueError: Raise when a negative balance is given.

        """
        # Raise an error if a negative balance is given.
        if balance < 0:
            msg = "Balance can not be a negative number."
            raise ValueError(msg)

        self.user_id: int = user_id
        self.balance: float = balance
        self.created_at: datetime | None = None
        self.last_daily_date: datetime | None = None
        self.last_work_date: datetime | None = None

    @property
    def formatted_balance(self) -> str:
        """Return a string made of balance number plus currency name and icon."""
        return str(self.balance) + " " + FORMATTED_CURRENCY

    async def deposit(
        self,
        amount: float,
        memo: str | None = None,
    ) -> Transaction:
        """Deposit to the account.

        Args:
            amount (float): Amount to deposit.
            memo (str | None, optional): Memo of the transaction. Defaults to None.

        Raises:
            ValueError: Raise when a negative amount is given.

        Returns:
            Transaction: Return the transaction.

        """
        # Raise an error if a negative amount is given.
        if amount < 0:
            msg = "Deposition amount can not be negative."
            raise ValueError(msg)

        # Raise an error if amount is zero.
        if amount == 0:
            msg = "Unnecessary operation: Deposition amount can not be 0."
            raise ValueError(msg)

        # Update the user's balance.
        self.balance += amount
        await execute(
            f"""
            UPDATE {AccountTable.TABLE_NAME}
            SET {AccountTable.COL_BALANCE} = ?
            WHERE {AccountTable.COL_USER_ID} = ?;
            """,  # noqa: S608
            (self.balance, self.user_id),
        )

        # Create  and return the transaction.
        return await Transaction(
            transaction_type=Transaction.TransactionTypes.DEPOSIT,
            user_id=self.user_id,
            amount=amount,
            memo=memo,
        ).commit()

    async def withdraw(
        self,
        amount: float,
        memo: str | None = None,
    ) -> Transaction:
        """Withdraw from the account.

        Args:
            amount (float): Amount to withdraw.
            memo (str | None, optional): Memo of the transaction. Defaults to None.

        Raises:
            ValueError: Raise when a negative amount is given.
            InsufficientBalance: Raise when the withdrawal amount is higher than
                the current balance.

        Returns:
            Transaction: Return the transaction.

        """
        # Raise an error if a negative amount is given.
        if amount < 0:
            msg = "Withdrawal amount can not be negative."
            raise ValueError(msg)

        # Raise an error if amount is zero.
        if amount == 0:
            msg = "Unnecessary operation: Withdrawl amount can not be 0."
            raise ValueError(msg)

        # Raise if  withdraw amount is higher than the current balance.
        if amount > self.balance:
            raise InsufficientBalanceError

        # Update the user's balance.
        self.balance -= amount
        await execute(
            f"""
            UPDATE {AccountTable.TABLE_NAME}
            SET {AccountTable.COL_BALANCE} = ?
            WHERE {AccountTable.COL_USER_ID} = ?;
            """,  # noqa: S608
            (self.balance, self.user_id),
        )

        # Create and return the transaction
        return await Transaction(
            transaction_type=Transaction.TransactionTypes.WITHDRAW,
            user_id=self.user_id,
            amount=amount,
            memo=memo,
        ).commit()

    async def transfer_to(
        self,
        receiver_id: int,
        amount: float,
        memo: str | None = None,
    ) -> Transaction:
        """Transfer balance from an account to another.

        Args:
            receiver_id (int): ID of receiver.
            amount (float): Amount to transfer.
            memo (str | None, optional): Memo of transaction. Defaults to None.

        Raises:
            ValueError: Raise when amount is negative.
            ValueError: Raise when amount is zero.
            InsufficientBalance: Raise when amount is higher than current balance.
            AccountDoesntExist: Raise when receiver's account is not found.

        Returns:
            Transaction: Return transaction.

        """
        # Raise an error if amount is negative.
        if amount < 0:
            msg = "Transfer amount can not be negative."
            raise ValueError(msg)

        # Raise an error if amount is zero.
        if amount == 0:
            msg = "Unnecessary operation: Transfer amount can not be 0."
            raise ValueError(msg)

        # Raise an error if amount is higher than current balance.
        if amount > self.balance:
            raise InsufficientBalanceError

        # Fetch receiver's account.
        receiver_account = await get_bank_account(receiver_id)

        # Raise an error if receiver's account couldn't be found.
        if receiver_account is None:
            raise AccountNotFoundError

        # Withdraw from sender's account.
        self.balance -= amount
        await execute(
            f"""
            UPDATE {AccountTable.TABLE_NAME}
            SET {AccountTable.COL_BALANCE} = ?
            WHERE {AccountTable.COL_USER_ID} = ?;
            """,  # noqa: S608
            (self.balance, self.user_id),
        )

        # Deposits to receiver's account.
        receiver_account.balance += amount
        await execute(
            f"""
            UPDATE {AccountTable.TABLE_NAME}
            SET {AccountTable.COL_BALANCE} = ?
            WHERE {AccountTable.COL_USER_ID} = ?;
            """,  # noqa: S608
            (receiver_account.balance, receiver_account.user_id),
        )

        # Create and return transaction.
        return await Transaction(
            transaction_type=Transaction.TransactionTypes.TRANSFER,
            user_id=self.user_id,
            amount=amount,
            receiver_id=receiver_id,
            memo=memo,
        ).commit()

    async def set_balance(
        self,
        amount: float,
        memo: str | None = None,
    ) -> Transaction:
        """Set the account's balance.

        Args:
            amount (float): Balance to be set.
            memo (str | None, optional): Memo of transaction. Defaults to None.

        Raises:
            ValueError: Raise when amount is negative.
            ValueError: Raise when amount is zero.

        Returns:
            Transaction: Return transaction.

        """
        # Raise an error if amount is negative.
        if amount < 0:
            msg = "Balance number can not be negative."
            raise ValueError(msg)

        # Raise an error if amount is equal to the current balance.
        if amount == self.balance:
            msg = "Unnecessary operation: New balance is equal to the current balance."
            raise ValueError(msg)

        # Update user's balance.
        self.balance = amount
        await execute(
            f"""
            UPDATE {AccountTable.TABLE_NAME}
            SET {AccountTable.COL_BALANCE} = ?
            WHERE {AccountTable.COL_USER_ID} = ?;
            """,  # noqa: S608
            (self.balance, self.user_id),
        )

        # Create and return transaction.
        return await Transaction(
            transaction_type=Transaction.TransactionTypes.ADJUSTMENT,
            user_id=self.user_id,
            amount=amount,
            memo=memo,
        ).commit()

    async def close(self) -> None:
        """Close bank account."""
        await execute(
            f"""
            DELETE FROM {AccountTable.TABLE_NAME}
            WHERE {AccountTable.COL_USER_ID} = ?;
            """,  # noqa: S608
            (self.user_id,),
        )

    async def update_last_daily_date(self) -> datetime:
        """Update last daily date of account.

        Returns:
            datetime: Return updated datetime.

        """
        now = datetime.now(timezone.utc)
        await execute(
            f"""
            UPDATE {AccountTable.TABLE_NAME}
            SET {AccountTable.COL_LAST_DAILY_DATE} = ?
            WHERE {AccountTable.COL_USER_ID} = ?;
            """,  # noqa: S608
            (int(now.timestamp()), self.user_id),
        )
        self.last_daily_date = now
        return now


@final
class Check:
    """Represents a bank check."""

    def __init__(
        self,
        *,
        sender_id: int,
        amount: float,
        receiver_id: int,
        memo: str | None = None,
    ) -> None:
        """Initialize a bank check.

        Args:
            sender_id (int): ID of sender.
            amount (float): Amount of check.
            receiver_id (int): ID of receiver.
            memo (str | None, optional): Memo for issuing check. Defaults to None.

        Raises:
            ValueError: Raise if amount is negative.
            ValueError: Raise if amount is zero.

        """
        # Raise an error if amount is negative.
        if amount < 0:
            msg = "Check amount can not be negative."
            raise ValueError(msg)

        # Raise an error if amount is zero.
        if amount == 0:
            msg = "Unnecessary operation: Check amount can not be 0."
            raise ValueError(msg)

        self.check_id: str | None = str(uuid.uuid4())
        self.sender_id: int = sender_id
        self.amount: float = amount
        self.receiver_id: int = receiver_id
        self.memo: str | None = memo
        self.issued_at: datetime | None = None
        self.is_cashed: bool = False

    async def issue(self) -> Transaction:
        """Issue bank check.

        Raises:
            AlreadyIssuedCheck: If trying to issue an already issued check.
            AccountNotFoundError: If the sender bank account can not be fetched.

        Returns:
            Transaction: The transaction.

        """
        # Raise an error if check is already issued.
        if self.issued_at is not None:
            raise CheckAlreadyIssuedError(self)

        # Fetch sender's account.
        sender_account = await get_bank_account(self.sender_id)

        # Raise an error if sender's account couldn't be found.
        if sender_account is None:
            raise AccountNotFoundError

        self.issued_at = datetime.now(timezone.utc)  # Check issue date

        # Withdraw check amount from sender's account and save transaction.
        tran = await sender_account.withdraw(self.amount, memo="Check Issuance.")

        # Save check info in DB.
        await execute(
            f"""
            INSERT INTO {CheckTable.TABLE_NAME} ({CheckTable.columns})
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,  # noqa: S608
            (
                self.check_id,
                self.sender_id,
                self.amount,
                self.receiver_id,
                self.memo,
                int(self.issued_at.timestamp()),
                0,
            ),
        )

        return tran

    async def cash(self) -> Transaction:
        """Cash check into receiver's account.

        Raises:
            AlreadyDepositedCheckError: Raise when trying to cash an already
                cashed check.
            AccountNotFoundError: Raise when receiver's bank account can not be
                fetched.

        Returns:
            Transaction: Return transaction.

        """
        # Raise an error if check is already deposited.
        if self.is_cashed:
            raise CheckAlreadyCashedError(self)

        # Fetch receiver's account.
        receiver_account = await get_bank_account(self.receiver_id)

        # Raise an error if receiver's account couldn't be found.
        if receiver_account is None:
            raise AccountNotFoundError

        # Deposit check amount to receiver's account and save transaction.
        tran = await receiver_account.deposit(self.amount, memo="Check Deposition.")

        # Update state of check in DB.
        await execute(
            f"""
            UPDATE {CheckTable.TABLE_NAME}
            SET {CheckTable.COL_IS_CASHED} = ?
            WHERE {CheckTable.COL_ID} = ?;
            """,  # noqa: S608
            (1, self.check_id),
        )

        return tran


@final
class Transaction:
    """Represents a bank transaction."""

    class TransactionTypes(Enum):
        """Represents different transaction types."""

        DEPOSIT = auto()
        WITHDRAW = auto()
        TRANSFER = auto()
        ADJUSTMENT = auto()

    def __init__(
        self,
        *,
        transaction_type: TransactionTypes,
        user_id: int,
        amount: float,
        receiver_id: int | None = None,
        memo: str | None = None,
    ) -> None:
        """Initialize a bank transaction.

        Args:
            transaction_type (Type): Type of transaction.
            user_id (int): ID of user.
            amount (float): Amount of operation.
            receiver_id (int | None, optional): ID of receiver if transaction type is to
                transfer. Defaults to None.
            memo (str | None, optional): Memo of transaction. Defaults to None.

        Raises:
            ValueError: Raise when transaction type is to transfer but no receiver ID is
                given.

        """
        # Raise an error if transaction type is to transfer but no receiver ID is given.
        if (
            transaction_type.value == Transaction.TransactionTypes.TRANSFER.value
            and receiver_id is None
        ):
            msg = 'Receiver ID can\'t be empty while transaction type is "Transfer".'
            raise ValueError(
                msg,
            )

        # Raise an error if amount is zero.
        if amount < 0:
            msg = "Transaction amount can not be negative."
            raise ValueError(msg)

        self.created_at: datetime | None = None
        self.transaction_id: str = str(uuid.uuid4())
        self.type: Transaction.TransactionTypes = transaction_type
        self.user_id: int = user_id
        self.amount: float = amount
        self.receiver_id: int | None = receiver_id
        self.memo: str | None = memo

    async def commit(self) -> Transaction:
        """Commit changes and store transaction.

        This method must be called right after creation.

        Returns:
            Transaction: Return transaction.

        """
        # Create transaction and save it in DB.
        self.created_at = datetime.now(timezone.utc)  # Transaction creation date
        await execute(
            f"""
            INSERT INTO {TransactionTable.TABLE_NAME} ({TransactionTable.columns()})
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,  # noqa: S608
            (
                self.transaction_id,
                self.type,
                self.user_id,
                self.amount,
                int(self.created_at.timestamp()),
                self.receiver_id,
                self.memo,
            ),
        )

        return self


async def close_bank_account(user_id: int) -> None:
    """Close a bank account.

    Args:
        user_id (int): ID of user.

    Raises:
        AccountNotFoundError: Raise when trying to close the account of a user who
            already has none.

    """
    # Fetch user's account.
    account = await get_bank_account(user_id)

    # Raise an error if user has already no account.
    if account is None:
        raise AccountNotFoundError

    # Close account.
    await account.close()


async def create_bank_account(*, user_id: int, balance: float = 0) -> BankAccount:
    """Create a bank account.

    Args:
        user_id (int): ID of user.
        balance (float, optional): Initial balance that user will start with. Defaults
            to 0.

    Raises:
        AccountExists: Raise when trying to create account for a user who already has
            one.
        ValueError: Raise when balance is negative.

    Returns:
        Account: Return created account.

    """
    # Fetch user's account.
    account = await get_bank_account(user_id)

    # Raise an error if user already has an account.
    if account is not None:
        raise AccountAlreadyExistsError

    # Raise an error if balance is negative.
    if balance < 0:
        msg = "Balance can not be negative."
        raise ValueError(msg)

    now = datetime.now(timezone.utc)  # Account creation date
    # Save account in DB.
    await execute(
        f"""
        INSERT INTO {AccountTable.TABLE_NAME} ({AccountTable.columns()})
        VALUES (?, ?, ?, ?, ?);
        """,  # noqa: S608
        (user_id, balance, int(now.timestamp()), None, None),
    )

    account = BankAccount(user_id=user_id, balance=balance)
    account.created_at = now

    return account


async def get_bank_account(user_id: int) -> BankAccount | None:
    """Fetch a bank account via user's ID.

    Args:
        user_id (int): ID of user.

    Returns:
        Account | None: The fetched account, if the user with given ID has an account.
            `None`, otherwise.

    """
    # Fetch the account.
    row = await fetchone(
        f"""
        SELECT * FROM {AccountTable.TABLE_NAME}
        WHERE {AccountTable.COL_USER_ID} = ?;
        """,  # noqa: S608
        (user_id,),
    )
    if row is None:
        return None

    # Create an account instance based on the fetched data.
    account = BankAccount(
        user_id=row[AccountTable.COL_USER_ID],
        balance=row[AccountTable.COL_BALANCE],
    )
    account.created_at = datetime.fromtimestamp(
        row[AccountTable.COL_CREATED_AT],
        timezone.utc,
    )
    account.last_daily_date = (
        datetime.fromtimestamp(row[AccountTable.COL_LAST_DAILY_DATE], timezone.utc)
        if row[AccountTable.COL_LAST_DAILY_DATE]
        else None
    )
    account.last_work_date = (
        datetime.fromtimestamp(row[AccountTable.COL_LAST_WORK_DATE], timezone.utc)
        if row[AccountTable.COL_LAST_WORK_DATE]
        else None
    )

    return account


async def get_bank_check(check_id: str) -> Check | None:
    """Fetch a bank check via its ID.

    Args:
        check_id (str): The ID of the check.

    Returns:
        Check | None: The fetched check if found. `None`, otherwise.

    """
    # Fetch the check.
    row = await fetchone(
        f"""
        SELECT * FROM {CheckTable.TABLE_NAME}
        WHERE {CheckTable.COL_ID} = ?;
        """,  # noqa: S608
        (check_id,),
    )
    if row is None:
        return None

    # Create a check instance based on the fetched data.
    check = Check(
        sender_id=row[CheckTable.COL_SENDER_ID],
        amount=row[CheckTable.COL_AMOUNT],
        receiver_id=row[CheckTable.COL_RECEIVER_ID],
        memo=row[CheckTable.COL_MEMO],
    )
    check.check_id = row[CheckTable.COL_ID]
    check.issued_at = datetime.fromtimestamp(
        row[CheckTable.COL_ISSUED_AT],
        timezone.utc,
    )
    check.is_cashed = row[CheckTable.COL_IS_CASHED] == 1

    return check


async def issue_bank_check(
    *,
    sender_id: int,
    amount: float,
    receiver_id: int,
    memo: str | None = None,
) -> Transaction:
    """Issue a bank check in an alternative way.

    Args:
        sender_id (int): The ID of the sender.
        amount (float): The amount of the check.
        receiver_id (int): The ID of the receiver.
        memo (str | None, optional): Memo of check. Defaults to None.

    Returns:
        Transaction | None: The transaction. `None` if the amount is 0.

    """
    return await Check(
        sender_id=sender_id,
        amount=amount,
        receiver_id=receiver_id,
        memo=memo,
    ).issue()


async def transfer(
    *,
    sender_id: int,
    receiver_id: int,
    amount: float,
    memo: str | None = None,
) -> Transaction:
    """Transfer balance between bank accounts in an alternative way through sender's ID.

    Args:
        sender_id (int): ID of the sender.
        receiver_id (int): ID of the receiver.
        amount (float): Amount to transfer.
        memo (str | None, optional): Memo of the transaction. Defaults to None.

    Raises:
        ValueError: Raise when amount is zero.
        AccountNotFoundError: Raise when receiver's account can not be fetched.

    Returns:
        Transaction: Return transaction.

    """
    # Raise an error if amount is zero.
    if amount == 0:
        msg = "Unnecessary operation: Transfer amount can not be 0."
        raise ValueError(msg)

    # Fetch sender's account.
    sender_account = await get_bank_account(sender_id)

    # Raise an error if sender's account couldn't be found.
    if sender_account is None:
        raise AccountNotFoundError

    # Transfer the money and return transaction.
    return await sender_account.transfer_to(receiver_id, amount, memo)
