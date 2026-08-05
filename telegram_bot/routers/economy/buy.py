from aiogram import Router, types, filters
from database import db
from cogs.economy.itemshop import items
from telegramRouters.utility.help import HelpData

router = Router(name=__name__)

HelpData = HelpData(
    category=HelpData.Category.Economy,
    dmOnly=False,
    serverOnly=False,
    subcommands=None,
    permissions=None,
    help=None,
    brief="Buys an Item from the Itemshop.",
    usage="<item_name> <quantity[*optional*]>",
    aliases=None,
)


@router.message(filters.Command("buy", *HelpData.aliases))
async def buy(message: types.Message, command: filters.command.CommandObject):
    if not message.from_user:
        return

    args = command.args if command.args else None
    item = args[0] if args and len(args) >= 1 else None
    quantity = args[1] if args and len(args) >= 2 else 1

    # trys to fetch user's balance
    row = await db.fetchone(
        """
        SELECT balance FROM user
        WHERE user_id = ?;
        """,
        (message.from_user.id,),
    )
    # if user has not account
    if not row:
        return await message.answer(
            "You have no account to but anything for it. Try `/daily` to claim your first daily and create an account."
        )

    # if user doesn't enter any item name
    if not item:
        return await message.answer("You must enter the Item name you want to buy.")

    # checks if entered item is available
    match = None
    for i in items:
        if i.name == item.lower():
            match = i
    if not match:
        return await message.answer(f"{item} is not a valid Item. See `/itemshop`.")

    try:
        quantity = int(quantity)
    except ValueError:
        return await message.answer("Enter a valid integer quantity.")

    # if user's balance is lower than the price
    if row["balance"] < (match.price * quantity):
        return await message.answer(
            f"Your current balance is lower than the amount that this amount of {match.name} will cost."
        )

    # updates user's balance
    await db.execute(
        """
        UPDATE user
        SET balance = ?
        WHERE user_id = ?;
        """,
        (row["balance"] - (match.price * quantity), message.from_user.id),
    )

    row = await db.fetchone(
        """
        SELECT quantity FROM inventory
        WHERE user_id = ? AND item_name = ?;
        """,
        (message.from_user.id, match.name),
    )
    # if user already has the item in the inventory, updates quantity
    if row:
        await db.execute(
            """
            UPDATE inventory
            SET quantity = ?
            WHERE user_id = ? AND item_name = ?;
            """,
            (row["quantity"] + quantity, message.from_user.id, match.name),
        )

    # adds the item to user's inventory otherwise
    else:
        await db.execute(
            """
            INSERT INTO inventory (user_id, item_name, quantity)
            VALUES (?, ?, ?);
            """,
            (message.from_user.id, match.name, quantity),
        )

    await message.answer(f"You have bought {quantity} {match.name} successfully.")
