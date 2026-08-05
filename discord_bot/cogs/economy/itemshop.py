from typing import final, override

import discord
from discord import app_commands
from discord.ext import commands

from core.bank import FORMATTED_CURRENCY
from core.help import HelpData
from core.itemshop import item_
from core.log_handler import setup_logger

logger = setup_logger(__name__)


@final
class ItemShop(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    Help = HelpData(
        category=HelpData.CommandCategory.ECONOMY,
        is_dm_only=False,
        is_server_only=False,
        subcommands=None,
        permissions=None,
        help_=None,
        brief="Shows the Item shop.",
        usage=None,
        aliases=["is", "items"],
    )

    @commands.command(name="itemshop", **Help.kwargs)
    async def item_shop(self, ctx: commands.Context[commands.Bot]) -> None:
        # stores different embeds for different categories
        embeds: list[discord.Embed] = []
        for category, itemList in item_.items():
            # creates a different embed for every each category
            embed = discord.Embed(
                title=category.title(),
                description="\n\n".join(
                    f"{item.name.title()} - {item.price}{FORMATTED_CURRENCY} - {item.rarity.name}:\n{item.description or 'No description provided for this item.'}"
                    for item in itemList
                ),
                color=discord.Color.blurple(),
            ).set_author(name="Item Shop")
            embeds.append(embed)

        # if there's only one category and one embed, sends it without view and buttons
        if len(embeds) == 1:
            _ = await ctx.reply(embed=embeds[0])

        # sends the view otherwise
        else:
            view = ItemShopView(ctx, categoryEmbeds=embeds)  # initializes the view
            await view.start()

    @item_shop.error
    async def item_shop_error(
        self, ctx: commands.Context[commands.Bot], error: commands.CommandError
    ) -> None:
        logger.exception("❌ something went wrong with itemshop command:")
        _ = await ctx.reply("something went wrong with **itemshop**.")

    # itemshop slash command
    @app_commands.command(name="itemshop", description=Help.brief, extras=Help.extras)
    async def slash_item_shop(
        self, interaction: discord.Interaction, ephemeral: bool = False
    ) -> None:
        # stores different embeds for different categories
        embeds: list[discord.Embed] = []
        for category, itemList in item_.items():
            # creates a different embed for every each category
            embed = discord.Embed(
                title=category.title(),
                description="\n\n".join(
                    f"{item.name.title()} - {item.price}{FORMATTED_CURRENCY} - {item.rarity.name}:\n{item.description or 'No description provided for this item.'}"
                    for item in itemList
                ),
                color=discord.Color.blurple(),
            ).set_author(name="Item Shop")
            embeds.append(embed)

        # if there's only one category and one embed, sends it without view and buttons
        if len(embeds) == 1:
            _ = await interaction.response.send_message(
                embed=embeds[0], ephemeral=ephemeral
            )

        # sends the view otherwise
        else:
            view = ItemShopView(
                interaction, categoryEmbeds=embeds
            )  # initializes the view
            await view.start()

    @slash_item_shop.error
    async def slash_item_shop_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.errors.AppCommandError,
    ) -> None:
        logger.exception("❌ something went wrong with /itemshop command:")
        try:
            _ = await interaction.response.send_message(
                "something went wrong with **itemshop**.", ephemeral=True
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "something went wrong with **itemshop**.", ephemeral=True
            )


@final
class ItemShopView(discord.ui.View):
    def __init__(
        self,
        ctx: commands.Context[commands.Bot] | discord.Interaction,
        *,
        categoryEmbeds: list[discord.Embed],
        ephemeral: bool = False,
    ) -> None:
        super().__init__(timeout=60)
        if isinstance(ctx, discord.Interaction):
            self.slash = True
            self.interaction = ctx
            self.user = ctx.user
        else:
            self.slash = False
            self.ctx = ctx
            self.user = ctx.author
        self.categoryEmbeds = categoryEmbeds
        self.EmbedIndex = 0
        self.ephemeral = ephemeral

        _ = self.start()

    async def start(self) -> None:
        # sends the itemshop menu from the first category
        if self.slash:
            _ = await self.interaction.response.send_message(
                embed=self.categoryEmbeds[0], view=self, ephemeral=self.ephemeral
            )
        else:
            self.msg = await self.ctx.reply(embed=self.categoryEmbeds[0], view=self)

    # close button
    @discord.ui.button(label="Close", style=discord.ButtonStyle.red, row=0)
    async def close(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button[discord.ui.View],
    ) -> discord.InteractionCallbackResponse[discord.Client] | None:
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message(
                "You can't control this Item Shop menu. try `/itemshop` yourself.",
                ephemeral=True,
            )

        # deletes the menu
        if self.slash:
            await self.interaction.delete_original_response()
        else:
            await self.msg.delete()

        self.stop()
        return None

    # previous button
    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.grey, row=0)
    async def previous(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button[discord.ui.View],
    ) -> discord.InteractionCallbackResponse[discord.Client] | None:
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message(
                "You can't control this Item Shop menu. try `/itemshop` yourself.",
                ephemeral=True,
            )

        self.EmbedIndex = (self.EmbedIndex - 1) % len(
            self.categoryEmbeds
        )  # previous embed

        _ = await interaction.response.edit_message(
            embed=self.categoryEmbeds[self.EmbedIndex]
        )
        return None

    # next button
    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.grey, row=0)
    async def next(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button[discord.ui.View],
    ) -> None:
        if interaction.user.id != self.user.id:
            _ = await interaction.response.send_message(
                "You can't control this Item Shop menu. try `/itemshop` yourself.",
                ephemeral=True,
            )
            return None

        self.EmbedIndex = (self.EmbedIndex + 1) % len(self.categoryEmbeds)  # next embed

        _ = await interaction.response.edit_message(
            embed=self.categoryEmbeds[self.EmbedIndex]
        )
        return None

    @override
    async def on_timeout(self) -> None:
        # disables buttons on timeout
        for btn in self.children:
            if isinstance(btn, discord.ui.Button):
                btn.disabled = True

        try:
            # edits the message to remove buttons on timeout
            if self.slash:
                _ = await self.interaction.edit_original_response(view=None)
            else:
                _ = await self.msg.edit(view=None)
        except discord.NotFound:
            pass

        self.stop()  # stops further interaction on timeout

    @override
    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item[discord.ui.View],
    ) -> None:
        logger.exception(
            f"❌ something went wrong with itemshop interaction - button: {getattr(item, 'emoji', 'unknown')}"
        )
        if not interaction.response.is_done():
            _ = await interaction.response.send_message(
                "something went wrong with **itemshop**.", ephemeral=True
            )
        else:
            await interaction.followup.send(
                "something went wrong with **itemshop**.", ephemeral=True
            )

        self.stop()  # stops further interaction on error


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ItemShop(bot))
