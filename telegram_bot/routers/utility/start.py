"""start command."""

from __future__ import annotations

__all__ = []

from aiogram import Router, filters, types

router = Router(name=__name__)


@router.message(filters.CommandStart())
async def start(message: types.Message) -> None:
    if message.from_user:
        await message.answer(f"Hi there, {message.from_user.mention_html()}.")
