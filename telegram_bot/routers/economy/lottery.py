from aiogram import Router, filters, types
from datetime import datetime, timezone
from database import db
from telegramRouters.utility.help import HelpData

router = Router(name=__name__)

HelpData = HelpData(
    category=HelpData.Category.Economy,
    dmOnly=False,
    serverOnly=False,
    subcommands=None,
    permissions=None,
    help=None,
    brief="Signs in for the lottery.",
    usage=None,
    aliases=None,
)


@router.message(filters.Command("lottery", *HelpData.aliases))
async def lottery(message: types.Message):
    if message.from_user:
        # checks if user has already signed in for lottery
        row = await db.fetchone(
            """
            SELECT signed_at FROM lottery
            WHERE user_id = ?;
            """,
            (message.from_user.id,),
        )
        if row:
            return await message.answer(
                f"You have already signed in for Lottery at `{row['signed_at']}`."
            )

        # signs the user for the lottery
        await db.execute(
            """
            INSERT INTO lottery (user_id, signed_at)
            VALUES (?, ?);
            """,
            (message.from_user.id, datetime.now(timezone.utc)),
        )
        await message.answer(
            "You have signed in for the Lottery successfully. Be tuned."
        )
