"""Contains the core logic of inventory system."""

from __future__ import annotations

__all__ = ["get_inventory"]

from typing import TYPE_CHECKING, final

if TYPE_CHECKING:
    from core.itemshop import Item

from core.database import execute, fetchall
from core.dbconstants import InventoryTable


@final
class Inventory:
    """Represents an inventory."""

    def __init__(
        self,
        user_id: int,
    ) -> None:
        """Initialize  an inventory.

        Args:
            user_id (int): User ID of the owner of inventory.

        """
        self.user_id: int = user_id

        self.items: dict[Item, int] = {}

    async def add_item(self, item: Item, quantity: int) -> None:
        """Add the desired quantity of an item to the inventory.

        Args:
            item (Item): Item to add.
            quantity (int): Quantity to add.

        """
        # Add the item.
        _ = await execute(
            f"""
            INSERT INTO {InventoryTable.TABLE_NAME} {InventoryTable.columns()}
            VALUES (?, ?, ?)
            ON CONFLICT({InventoryTable.COL_USER_ID},
            {InventoryTable.COL_ITEM_NAME}) DO UPDATE
            SET {InventoryTable.COL_QUANTITY} = {InventoryTable.COL_QUANTITY} + ?;
            """,  # noqa: S608
            (self.user_id, item.name, quantity, quantity),
        )
        self.items[item] = self.items.setdefault(item, 0) + quantity

    async def remove_item(self, item: Item, quantity: int) -> None:
        """Remove desired amount of an item from the inventory.

        Args:
            item (Item): Item to remove.
            quantity (int): Quantity to remove.

        """
        # Fetch current owned quantity of item.
        item_quantity: int = self.items.get(item, 0)
        # Raise an error if item quantity is 0 or negative.
        if item_quantity == 0 or item_quantity < quantity:
            msg = "Insufficient item amount to remove."
            raise ValueError(msg)

        # Remove the item.
        await execute(
            f"""
            UPDATE {InventoryTable.TABLE_NAME}
            SET {InventoryTable.COL_QUANTITY} = {InventoryTable.COL_QUANTITY} - ?
            WHERE {InventoryTable.COL_USER_ID} = ?
            AND {InventoryTable.COL_ITEM_NAME} = ?;
            """,  # noqa: S608
            (quantity, self.user_id, item.name),
        )
        self.items[item] -= quantity


async def get_inventory(user_id: int) -> Inventory:
    """Fetch an inventory.

    Args:
        user_id (int): User ID to fetch inventory with.

    Returns:
        Inventory: Return the inventory.

    """
    items = await fetchall(
        f"""
        SELECT * FROM {InventoryTable.TABLE_NAME}
        WHERE {InventoryTable.COL_USER_ID} = ?;
        """,  # noqa: S608
        (user_id,),
    )
    inventory = Inventory(user_id)
    for item in items:
        inventory.items[item[InventoryTable.COL_ITEM_NAME]] = item[
            InventoryTable.COL_QUANTITY
        ]

    return inventory
