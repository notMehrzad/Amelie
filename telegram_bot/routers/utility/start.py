from aiogram import types, Router, filters
from telegramRouters.utility.help import HelpData

router = Router(name=__name__)

HelpData = HelpData(
    category=HelpData.Category.Utility,
    dmOnly=False,
    serverOnly=False,
    subcommands=None,
    permissions=None,
    help=None,
    brief="The base start command.",
    usage=None,
    aliases=None,
    hidden=True,
)


@router.message(filters.CommandStart())
async def start(message: types.Message):
    if message.from_user:
        await message.answer(f"Hi there, {message.from_user.username}.")
