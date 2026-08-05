"""The `buy` command. It allows the users to but different items from the itemshop."""

import discord
from discord import app_commands
from discord.ext import commands

from core.database import execute, fetchone
from core.dbconstants import AccountTable, InventoryTable
from core.help import HelpData
from core.itemshop import item_
from core.log_handler import setup_logger

logger = setup_logger(__name__)


class Buy(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    Help = HelpData(
        category=HelpData.CommandCategory.ECONOMY,
        is_dm_only=False,
        is_server_only=False,
        subcommands=None,
        permissions=None,
        help_=None,
        brief="Buys an Item from the Itemshop.",
        usage="<item_name> <quantity[*optional*]>",
        aliases=None,
    )

    @commands.command(name="buy", **Help.kwargs)
    async def buy(
        self,
        ctx: commands.Context[commands.Bot],
        item: str | None,
        quantity: int | str = 1,
    ) -> discord.Message | None:
        # trys to fetch user's balance
        row = await fetchone(
            f"""
            SELECT balance FROM {AccountTable.TABLE_NAME}
            WHERE {AccountTable.COL_USER_ID} = ?;
            """,
            (ctx.author.id,),
        )
        # if user has not account
        if not row:
            return await ctx.reply(
                "You have no account to but anything for it. Try `/daily` to claim your first daily and create an account."
            )

        # if user doesn't enter any item name
        if not item:
            return await ctx.reply("You must enter the Item name you want to buy.")

        # checks if entered item is available
        match = None
        for i in item_:
            if i.name == item.lower():
                match = i
        if not match:
            return await ctx.reply(f"{item} is not a valid Item. See `/itemshop`.")

        # if user doesn't enter a valid quantity
        if not isinstance(quantity, int):
            return await ctx.reply("Enter a valid quantity.")

        # if user's balance is lower than the price
        if row["balance"] < (match.price * quantity):
            return await ctx.reply(
                f"Your current balance is lower than the amount that this amount of {match.name} will cost."
            )

        # updates user's balance
        await execute(
            f"""
            UPDATE {AccountTable.TABLE_NAME}
            SET {AccountTable.COL_BALANCE} = ?
            WHERE {AccountTable.COL_USER_ID} = ?;
            """,
            (row["balance"] - (match.price * quantity), ctx.author.id),
        )

        row = await fetchone(
            f"""
            SELECT {InventoryTable.COL_QUANTITY} FROM {InventoryTable.TABLE_NAME}
            WHERE {InventoryTable.COL_USER_ID} = ? AND {InventoryTable.COL_ITEM_NAME} = ?;
            """,
            (ctx.author.id, match.name),
        )
        # if user already has the item in the inventory, updates quantity
        if row:
            await execute(
                f"""
                UPDATE {InventoryTable.TABLE_NAME}
                SET {InventoryTable.COL_QUANTITY} = ?
                WHERE {InventoryTable.COL_USER_ID} = ? AND {InventoryTable.COL_ITEM_NAME} = ?;
                """,
                (row["quantity"] + quantity, ctx.author.id, match.name),
            )

        # adds the item to user's inventory otherwise
        else:
            await execute(
                f"""
                INSERT INTO {InventoryTable.TABLE_NAME} ({InventoryTable.columns()})
                VALUES (?, ?, ?);
                """,
                (ctx.author.id, match.name, quantity),
            )

        await ctx.reply(f"You have bought {quantity} {match.name} successfully.")

    @buy.error
    async def buy_error(
        self, ctx: commands.Context[commands.Bot], error: commands.CommandError
    ) -> None:
        logger.exception("❌ something went wrong with buy command:")
        await ctx.reply("something went wrong with **buy**.")

    # buy slash command
    @app_commands.command(name="buy", description=Help.brief, extras=Help.extras)
    @app_commands.describe(
        item="The Item to buy.", quantity="The amount of Item to buy."
    )
    async def slashBuy(
        self, interaction: discord.Interaction, item: str, quantity: int = 1
    ) -> discord.InteractionCallbackResponse[discord.Client] | None:
        # trys to fetch user's balance
        row = await fetchone(
            f"""
            SELECT balance FROM {AccountTable.TABLE_NAME}
            WHERE {AccountTable.COL_USER_ID} = ?;
            """,
            (interaction.user.id,),
        )
        # if user has not account
        if not row:
            return await interaction.response.send_message(
                "You have no account to but anything for it. Try `/daily` to claim your first daily and create an account.",
                ephemeral=True,
            )

        # if user doesn't enter any item name
        if not item:
            return await interaction.response.send_message(
                "You must enter the Item name you want to buy.", ephemeral=True
            )

        # checks if entered item is available
        match = None
        for i in items:
            if i.name == item.lower():
                match = i
        if not match:
            return await interaction.response.send_message(
                f"{item} is not a valid Item. See `/itemshop`.", ephemeral=True
            )

        # if user's balance is lower than the price
        if row["balance"] < (match.price * quantity):
            return await interaction.response.send_message(
                f"Your current balance is lower than the amount that this amount of {match.name} will cost.",
                ephemeral=True,
            )

        # updates user's balance
        await execute(
            f"""
            UPDATE {AccountTable.TABLE_NAME}
            SET {AccountTable.COL_BALANCE} = ?
            WHERE {AccountTable.COL_USER_ID} = ?;
            """,
            (row["balance"] - (match.price * quantity), interaction.user.id),
        )

        row = await fetchone(
            f"""
            SELECT {InventoryTable.COL_QUANTITY} FROM {InventoryTable.TABLE_NAME}
            WHERE {InventoryTable.COL_USER_ID} = ? AND {InventoryTable.COL_ITEM_NAME} = ?;
            """,
            (interaction.user.id, match.name),
        )
        # if user already has the item in the inventory, updates quantity
        if row:
            await execute(
                f"""
                UPDATE {InventoryTable.TABLE_NAME}
                SET {InventoryTable.COL_QUANTITY} = ?
                WHERE {InventoryTable.COL_USER_ID} = ? AND {InventoryTable.COL_ITEM_NAME} = ?;
                """,
                (row["quantity"] + quantity, interaction.user.id, match.name),
            )

        # adds the item to user's inventory otherwise
        else:
            await execute(
                f"""
                INSERT INTO {InventoryTable.TABLE_NAME} ({InventoryTable.columns()})
                VALUES (?, ?, ?);
                """,
                (interaction.user.id, match.name, quantity),
            )

        await interaction.response.send_message(
            f"You have bought {quantity} {match.name} successfully."
        )

    @slashBuy.error
    async def slashBuy_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        logger.exception("❌ something went wrong with /buy command:")
        try:
            await interaction.response.send_message(
                "something went wrong with **buy**.", ephemeral=True
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "something went wrong with **buy**.", ephemeral=True
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Buy(bot))
