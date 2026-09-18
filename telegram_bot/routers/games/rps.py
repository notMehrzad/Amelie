from __future__ import annotations

__all__ = []

import secrets
from datetime import datetime, timedelta, timezone
from enum import Enum, auto
from typing import TYPE_CHECKING, ClassVar, final

from aiogram import Dispatcher, Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.help_data_constants import RPS_HELP
from core.rps import RPSGame, RPSOption
from telegram_bot.arg_parser import parse_args

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery, Message, User

ROUTER = Router(name=__name__)


@ROUTER.message(Command(RPS_HELP.name, *RPS_HELP.aliases, ignore_case=True))
@parse_args
async def rps(message: Message, *, dispatcher: Dispatcher) -> None:
    if message.reply_to_message is None:
        target: User = dispatcher["bot_user"]

    else:
        target = message.reply_to_message.from_user

        # Raise an error if user wants to play with themselves.
        if target.id == message.from_user.id:
            await message.reply("You can't play with yourself.")
            return

        # Raise an error if user wants to play with a bot.
        if target.is_bot and target.id != dispatcher["bot_user"].id:
            await message.reply("You can't play with bots. (except me!)")
            return

        if message.chat.type == "private" and target.id != dispatcher["bot_user"].id:
            await message.reply(
                "You can play this game with others only in a server they are also in.",
            )
            return

    await RpsView(message, target).start()


@final
class _RPSGameState(Enum):
    USER_TURN = auto()
    TARGET_TURN = auto()

    FINISHED = auto()


@final
class RPSCallbackData(CallbackData, prefix="RPS"):
    user_id: int
    option: str


@final
class RpsView:
    TIMEOUT: float = 180

    games: ClassVar[dict[int, RpsView]] = {}

    def __init__(self, message: Message, target: User) -> None:
        self.expires_at: datetime = datetime.now(timezone.utc) + timedelta(
            seconds=RpsView.TIMEOUT,
        )
        self.message: Message = message
        self.user: User = self.message.from_user
        self.target: User = target
        self.bot_plays: bool = self.target.id == self.message.bot.id

        self.game: RPSGame = RPSGame(self.user.id, self.target.id)
        self.state: _RPSGameState = _RPSGameState.TARGET_TURN

        RpsView.games[self.user.id] = self

    def play_bot_turn(self) -> None:
        """Play bot's turn.

        Bot picks a random RPS option.
        """
        self.game.player2_plays(secrets.choice(list(RPSOption)))
        self.state = _RPSGameState.USER_TURN

    async def start(self) -> None:
        """Start the view."""
        self.builder = InlineKeyboardBuilder()
        for option in RPSOption:
            self.builder.button(
                text=option.label.title(),
                callback_data=RPSCallbackData(user_id=self.user.id, option=option.name),
            )
        self.builder.adjust(3)
        if self.bot_plays:
            self.play_bot_turn()

            content = None
            description = "<i>You wanna play with ME??\nsounds fine-\nlets start the game then.</i>"
        else:
            content = (
                f"{self.target.mention_html()}, You're challenged to a game of"
                f" <i>Rock, Paper, Scissors !</i> by {self.user.mention_html()}"
            )
            description = f"It's currently {self.target.mention_html()}'s turn to play."

        # Send initial message.
        self.msg = await self.message.reply(
            text=f"{content}\n\n{description}" if content else description,
            reply_markup=self.builder.as_markup(),
        )

    async def finish_game(self) -> None:
        """Finish and calculate the result of the game."""
        if self.game.player1_choice is None or self.game.player2_choice is None:
            return

        # Calculate the RPS winner.
        winner_user_id = self.game.calculate_winner()
        # Draw
        if winner_user_id is None:
            description = "<b>It was a Draw !</b>"
            bot_dialogue = (
                f"{self.user.mention_html()} escaped this time."
                if self.bot_plays
                else None
            )

        # User wins.
        elif winner_user_id == self.user.id:
            description = f"<b>{self.user.mention_html()} has Won !</b>"
            bot_dialogue = "-ahh. maybe another time." if self.bot_plays else None

        # Target wins.
        else:
            description = (
                f"<b>{self.target.mention_html()} has Won !</b>"
                if not self.bot_plays
                else "<b>I have Won !</b>"
            )
            bot_dialogue = "huh. not even a single sweat-" if self.bot_plays else None

        # Send result embed.
        await self.msg.edit_text(
            text=(
                f"{description}"
                f"\n\n{self.user.full_name}'s Choice: {self.game.player1_choice.label.title()} {self.game.player1_choice.emoji}"
                f"\n\n{self.target.full_name}'s Choice: {self.game.player2_choice.label.title()} {self.game.player2_choice.emoji}"
            ),
            reply_markup=None,
        )

    async def on_timeout(self) -> None:
        if self.bot_plays:
            description = (
                f"{self.user.mention_html()} didn't make a move.\n*shame on you..*"
            )
        elif self.state == _RPSGameState.TARGET_TURN:
            description = (
                f"{self.target.mention_html()} didn't seem brave enough"
                " to accept the challenge."
            )
        else:
            description = f"{self.user.mention_html()} seemed to have more important buisness to do."

        # Send timeout embed.
        await self.msg.edit_text(
            text=f"⏰ The game has timed out! {description}",
            reply_markup=None,
        )


@ROUTER.callback_query(RPSCallbackData.filter())
async def rps_option_callback(
    callback: CallbackQuery,
    callback_data: RPSCallbackData,
) -> None:
    # Find the game.
    game = RpsView.games[callback_data.user_id]

    # Check game's timeout.
    if datetime.now(timezone.utc) > game.expires_at:
        await game.on_timeout()
        return

    # Raise an error if interaction is not from players.
    if callback.from_user.id not in (game.user.id, game.target.id):
        await callback.answer("You can't play in this game.", show_alert=True)
        return

    # Raise an error if it's target's turn and interaction is from user.
    if (
        game.state == _RPSGameState.TARGET_TURN
        and callback.from_user.id != game.target.id
    ):
        if game.game.player1_choice is None:
            await callback.answer(
                f"It's currently {game.target.mention_html()}'s turn to play.",
                show_alert=True,
            )
            return
        await callback.answer(
            (f"You've already played your turn. ({game.game.player1_choice.emoji})"),
            show_alert=True,
        )
        return

    # Raise an error if it's user's turn and interaction is from target.
    if game.state == _RPSGameState.USER_TURN and callback.from_user.id != game.user.id:
        if game.game.player2_choice is None:
            await callback.answer(
                f"It's currently {game.user.mention_html()}'s turn to play.",
                show_alert=True,
            )
            return
        await callback.answer(
            (f"You've already played your turn. ({game.game.player2_choice.emoji})"),
            show_alert=True,
        )
        return

    # Target's turn
    if game.state == _RPSGameState.TARGET_TURN:
        game.game.player2_plays(RPSOption[callback_data.option])
        game.state = _RPSGameState.USER_TURN

        await callback.answer(
            f"You played {RPSOption[callback_data.option].emoji}.",
            show_alert=True,
        )

        # Send notification embed.
        await game.msg.edit_text(
            text=(
                f"{game.target.mention_html()} played their turn.\n\nIt's"
                " currently {self.user.mention}'s turn to play."
            ),
            reply_markup=game.builder.as_markup(),
        )
        await game.msg.reply(
            f"{game.user.mention_html()}, It's your turn now !",
        )

        return

    # User's turn
    if game.state == _RPSGameState.USER_TURN:
        game.game.player1_plays(RPSOption[callback_data.option])
        game.state = _RPSGameState.FINISHED

        await callback.answer(
            f"You played {RPSOption[callback_data.option].emoji}.",
            show_alert=True,
        )

        await game.finish_game()

        return
