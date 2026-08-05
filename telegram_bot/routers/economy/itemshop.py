from aiogram import Router, filters, types, F, exceptions
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import eco
from datetime import datetime, timezone, timedelta
from enum import Enum
from telegramRouters.utility.help import HelpData

router = Router(name=__name__)


class Item:
    class Category(Enum):
        Decorative = "decorative"

        def __str__(self):
            return self.name

    class Rarity(Enum):
        common = 1
        uncommon = 2
        rare = 3
        epic = 4
        legendary = 5

        def __int__(self):
            return self.value

    def __init__(
        self,
        *,
        category: Category,
        name: str,
        price: float,
        rarity: Rarity,
        desc: str | None = None,
    ):
        self.category = category
        self.name = name
        self.price = price
        self.rarity = rarity
        self.desc = desc


items = [
    Item(
        category=Item.Category.Decorative,
        name="cookie",
        price=3,
        rarity=Item.Rarity.common,
        desc="A decorative item, no purpose.",
    ),
    Item(
        category=Item.Category.Decorative,
        name="milk",
        price=5,
        rarity=Item.Rarity.common,
        desc="A decorative item, no purpose.",
    ),
]
categorized: dict[str, list[Item]] = {}
for item in items:
    categorized.setdefault(item.category.value, []).append(item)
for category in categorized:
    categorized[category].sort(key=lambda item: item.name)
categorized = dict(
    sorted(categorized.items(), key=lambda item: item[0].lower())
)  # rebuilds the dictionary but sorted keys this time

HelpData = HelpData(
    category=HelpData.Category.Economy,
    dmOnly=False,
    serverOnly=False,
    subcommands=None,
    permissions=None,
    help=None,
    brief="Shows the Itemshop.",
    usage=None,
    aliases=["is", "items"],
)


@router.message(filters.Command("itemshop", *HelpData.aliases))
async def itemshop(message: types.Message):
    categoryMessages: list[str] = []  # store different embeds for different categories
    for category, itemList in categorized.items():
        # creates a different embed for every each category
        msgStr = f"{category.title()}\n\n\n\n".join(
            f"{item.name.title()} - {item.price}{eco.currency_postfix} - {item.rarity.name}:\n{item.desc if item.desc else 'No description provided for this item.'}"
            for item in itemList
        )
        categoryMessages.append(msgStr)

    # if there's only one category and one embed, sends it without without view and buttons
    if len(categoryMessages) == 1:
        await message.answer(categoryMessages[0])

    # sends the view otherwise
    else:
        view = ItemshopView(
            message, categoryMessages=categoryMessages
        )  # initializes the view
        await view.start()


class ButtonCallback(CallbackData, prefix="itemshop"):
    user_id: int
    action: str


class ItemshopView:
    timeout = 60

    def __init__(self, message: types.Message, *, categoryMessages: list[str]):
        self.message = message
        if message.from_user:
            self.user = message.from_user
        self.categoryMessages = categoryMessages
        self.messageIndex = 0
        self.expiresAt = datetime.now(timezone.utc) + timedelta(
            seconds=ItemshopView.timeout
        )

    async def start(self):
        # creates the related buttons
        self.builder = InlineKeyboardBuilder()
        self.builder.button(
            text="◀️",
            callback_data=ButtonCallback(user_id=self.user.id, action="previous"),
        )
        self.builder.button(
            text="▶️", callback_data=ButtonCallback(user_id=self.user.id, action="next")
        )
        self.builder.button(
            text="close",
            callback_data=ButtonCallback(user_id=self.user.id, action="close").pack(),
        )
        self.builder.adjust(2, 1)
        self.registerButtons()

        self.msg = await self.message.answer(
            text=self.categoryMessages[0], reply_markup=self.builder.as_markup()
        )  # sends the first page of the itemshop menu

    def registerButtons(self):
        # previous button handler
        @router.callback_query(ButtonCallback.filter(F.action == "previous"))
        async def previous(
            callback: types.CallbackQuery, callback_data: ButtonCallback
        ):  # type: ignore
            await callback.answer()

            if callback.from_user.id != callback_data.user_id:
                return await callback.answer(
                    "You can't control this itemshop menu. try /itemshop command yourself."
                )

            if datetime.now(timezone.utc) > self.expiresAt:
                return await self.on_timeout()

            self.messageIndex = (self.messageIndex - 1) % len(
                self.categoryMessages
            )  # previous embed

            await callback.message.edit_text(
                text=self.pages[self.messageIndex],
                reply_markup=self.builder.as_markup(),
            )  # type: ignore

        # next button handler
        @router.callback_query(ButtonCallback.filter(F.action == "next"))
        async def next(callback: types.CallbackQuery, callback_data: ButtonCallback):  # type: ignore
            await callback.answer()

            if callback.from_user.id != callback_data.user_id:
                return await callback.answer(
                    "You can't control this itemshop menu. try /itemshop command yourself."
                )

            if datetime.now(timezone.utc) > self.expiresAt:
                return await self.on_timeout()

            self.messageIndex = (self.messageIndex + 1) % len(
                self.categoryMessages
            )  # next embed

            await callback.message.edit_text(
                text=self.pages[self.messageIndex],
                reply_markup=self.builder.as_markup(),
            )  # type: ignore

        # close button handler
        @router.callback_query(ButtonCallback.filter(F.action == "close"))
        async def close(callback: types.CallbackQuery, callback_data: ButtonCallback):  # type: ignore
            await callback.answer()

            if callback.from_user.id != callback_data.user_id:
                return await callback.answer(
                    "You can't control this itemshop menu. try /itemshop command yourself."
                )

            if datetime.now(timezone.utc) > self.expiresAt:
                return await self.on_timeout()

            try:
                await self.message.delete()
            except:
                pass
            await callback.message.delete()  # type: ignore

    async def on_timeout(self):
        try:
            await self.msg.delete_reply_markup()
        except exceptions.TelegramBadRequest:
            pass
