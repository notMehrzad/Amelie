"""Contains the core logic of item shop system."""

from __future__ import annotations

__all__ = ["buy", "item_"]

from enum import Enum, auto
from typing import TYPE_CHECKING, final, override

from core.inventory import get_inventory

if TYPE_CHECKING:
    from core.bank import BankAccount, Transaction


@final
class Item:
    """Represents an item in item shop."""

    class ItemCategories(Enum):
        """Represents different item categories."""

        DECORATIVE = auto()

    class ItemRarities(Enum):
        """Represents different item rarities."""

        COMMON = 1
        UNCOMMON = 2
        RARE = 3
        EPIC = 4
        LEGENDARY = 5

        def __int__(self) -> int:
            return self.value

        @override
        def __str__(self) -> str:
            return self.name

    def __init__(
        self,
        *,
        category: ItemCategories,
        name: str,
        price: int,
        rarity: ItemRarities,
        description: str | None = None,
    ) -> None:
        """Initialize item.

        Args:
            category (Category): The category of the item.
            name (str): The name of the item.
            price (float): The item price.
            rarity (Rarity): The rarity of the item.
            description (str | None, optional): The item description. Defaults to None.

        """
        self.category: Item.ItemCategories = category
        self.name: str = name
        self.price: int = price
        self.rarity: Item.ItemRarities = rarity
        self.description: str | None = description

    @override
    def __str__(self) -> str:
        return self.name


# Define available items to buy in item shop.
_ITEMS: tuple[Item, ...] = (
    Item(
        category=Item.ItemCategories.DECORATIVE,
        name="cookie",
        price=3,
        rarity=Item.ItemRarities.COMMON,
        description="A decorative item, no purpose.",
    ),
    Item(
        category=Item.ItemCategories.DECORATIVE,
        name="milk",
        price=5,
        rarity=Item.ItemRarities.COMMON,
        description="A decorative item, no purpose.",
    ),
)

# Sort the items.
item_: dict[Item.ItemCategories, list[Item]] = {}
for item in _ITEMS:
    item_.setdefault(item.category, []).append(item)
for items in item_.values():
    items.sort(key=lambda item_: item_.name)

item_ = dict(
    sorted(item_.items(), key=lambda item_: item_[0].name.lower()),
)


async def buy(account: BankAccount, item: Item, quantity: int = 1) -> Transaction:
    """Buy an item from the item shop.

    Args:
        account (BankAccount): Bank account for payout.
        item (Item): Item to buy.
        quantity (int, optional): Quantity to buy. Defaults to 1.

    Raises:
        ValueError: Raise when quantity is 0 or negative.

    Returns:
        Transaction: Return the withdrawl transaction.

    """
    # Raise an error if quantity is 0.
    if quantity == 0:
        msg = "Buying amount can not be 0"
        raise ValueError(msg)
    # Raise an error if quantity is snegative
    if quantity < 0:
        msg = "Buying amount can not be negative."
        raise ValueError(msg)

    # Fetch user's inventory.
    inventory = await get_inventory(account.user_id)

    # Withdraw the price and add the item.
    transaction = await account.withdraw(
        (item.price * quantity),
        memo=f"Bought {quantity} {item.name}.",  # TODO(Mehrzad): update memo.
    )
    await inventory.add_item(item, quantity)

    # Return the transaction.
    return transaction
