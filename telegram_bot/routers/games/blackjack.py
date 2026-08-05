"""/blackjack command."""

from __future__ import annotations

__all__ = []

import asyncio
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, ClassVar, final

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder

from arg_parser import parse_args
from core.bank import CURRENCY_NAME, BankAccount, get_bank_account
from core.blackjack import (
    DEALER_STAND_VALUE,
    MAX_BET,
    MIN_BET,
    BlackjackHand,
    generate_deck,
)
from core.help_data_constants import BLACKJACK_HELP
from core.log_handler import setup_logger
from core.session import Session, get_session

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery, Message, User

ROUTER = Router(name=__name__)


logger = setup_logger(__name__)


@ROUTER.message(Command(BLACKJACK_HELP.name, *BLACKJACK_HELP.aliases, ignore_case=True))
@parse_args
async def blackjack(message: Message, bet: int | str | None = None) -> None:
    if message.from_user is None:
        return

    session = get_session(message.from_user.id, Session.SessionTypes.GAMBLING)
    # Raise an error if user has an active session.
    if session is not None:
        _ = await message.answer("You have an open gambling session somewhere.")
        return

    if bet == 0:
        bet = None

    # Check bet validity if player bets.
    if bet is not None:
        # Raise an error if bet amount is invalid.
        if not isinstance(bet, int):
            _ = await message.answer(
                "Enter a valid integer for bet.",
            )
            return

        # Raise an error if bet is lower than minimum bet amount.
        if bet < MIN_BET:
            _ = await message.answer(
                f"The minimum bet amount for Blackjack is **{MIN_BET}**.",
            )
            return
        # Raise an error if bet is higher than maximum bet amount.
        if bet > MAX_BET:
            _ = await message.answer(
                f"The maximum bet amount for Blackjack is **{MAX_BET}**.",
            )
            return

        # Fetch user's bank account.
        bank_account = await get_bank_account(message.from_user.id)
        # Raise an error if user has no bank account.
        if bank_account is None:
            _ = await message.answer(
                (
                    "You have no balance account !"
                    "\nTry `/daily` to claim your first daily reward and get your"
                    " balance account."
                ),
                ephemeral=True,
            )
            return

        # Raise an error if bet is higher than user's current balance.
        if bet > bank_account.balance:
            _ = await message.answer(
                (
                    "Your desired bet is higher than your current balance."
                    "\nTry `/balance` to see your balance."
                ),
                ephemeral=True,
            )
            return
    else:
        bank_account = None

    # Open a gambling session for user.
    session = Session(message.from_user.id, Session.SessionTypes.GAMBLING)

    # Start Blackjack view.
    await BlackjackView(message, bet, bank_account, session).start()


class ButtonCallback(CallbackData, prefix="bj"):
    user_id: int
    action: str


@final
class BlackjackView:
    TIMEOUT: float = 180

    games: ClassVar[dict[int, BlackjackView]] = {}

    def __init__(
        self,
        message: Message,
        bet: int | None,
        bank_account: BankAccount | None,
        session: Session,
    ) -> None:
        self.expires_at: datetime = datetime.now(timezone.utc) + timedelta(
            seconds=BlackjackView.TIMEOUT,
        )
        self.message: Message = message
        if message.from_user is not None:
            self.user: User = message.from_user

        # The initial bet will be taken into pot.
        if bet is not None:
            self.bet: int = bet
        if bank_account is not None:
            self.bank_account: BankAccount = bank_account
        self.player_bets: bool = bool(bet is not None and bank_account is not None)
        self.insurance: bool | None = None

        self.session: Session = session
        self.state: str | None = None

        BlackjackView.games[self.user.id] = self

    @property
    def formatted_insurance_info(self) -> str:
        """Return a formatted string that gives information about insurance.

        It must be included in every notification after the peeking hole card phase.
        """
        # If no insurance condition happens
        if self.insurance is None:
            return ""

        # If player accepts the insurance
        if self.insurance:
            # If dealer gets Blackjack.
            if self.dealer_hand.is_blackjack:
                return (
                    "You accepted the insurance and I got a Blackjack !"
                    " You Won the insurance."
                )

            # If dealer doesn't get Blackjack.
            return (
                "You accepted the insurance and I got not a Blackjack !"
                " You Lost the insurance."
            )

        # If player refuses the insurance
        return "You refused the insurance."

    @property
    def formatted_hand(self) -> str:
        """Return a formatted string of players hand to display."""
        dealer_value_string = (
            self.dealer_hand.value if not self.dealer_hand.hide_hole_card else "?"
        )
        bet_string = f"\n\nBet: {self.bet} {CURRENCY_NAME}s" if self.player_bets else ""
        separator = "\n----" if self.player_bets else "\n\n----"
        return (
            f"Dealer ({dealer_value_string})"
            f"\n{self.dealer_hand}"
            f"\n\nYou ({self.player_hand.value})"
            f"\n{self.player_hand}"
            f"{bet_string}"
            f"{separator}"
        )

    async def start(self) -> None:
        """Start Blackjack view."""
        # Withdraw the initial bet if player bets.
        if self.player_bets:
            _ = await self.bank_account.withdraw(self.bet, "Blackjack wager.")

            description = (
                f"Blackjack starts with **{self.bet}** in the pot !"
                "\nAs your Dealer, I may distribute our cards in a second.."
            )
        else:
            description = (
                "Blackjack starts !"
                "\nAs your Dealer, I may distribute our cards in a second.."
            )

        self.msg = await self.message.answer(description)

        # Generate a 6 shoe deck.
        self.deck = generate_deck(shoe=6, shuffle=True)

        # Draw initial cards to both player and dealer.
        self.player_hand = BlackjackHand([self.deck.pop() for _ in range(2)])
        self.dealer_hand = BlackjackHand([self.deck.pop() for _ in range(2)])
        # Dealer has a hole card (The face down card).
        self.dealer_hand.hide_hole_card = True

        await asyncio.sleep(3)  # Dramatic short delay

        # Peek the hole card if face up card is A, K, Q, J, 10.
        if self.dealer_hand.cards[0].rank in ("A", "K", "Q", "J", 10):
            # Offer insurance if face up card is A and player bets.
            if self.dealer_hand.cards[0].rank == "A" and self.player_bets:
                await self.offer_insurance()
            else:
                await self.peek_hole()
        else:
            await self.player_turn()

    async def offer_insurance(self) -> None:
        # Add related buttons.
        builder = InlineKeyboardBuilder()
        builder.button(
            text="refuse",
            callback_data=ButtonCallback(user_id=self.user.id, action="refuse"),
        )
        builder.button(
            text="accept",
            callback_data=ButtonCallback(user_id=self.user.id, action="accept"),
        )
        builder.adjust(2)
        self.state = "insurance_action"

        await self.msg.edit_text(
            text=(
                f"{self.formatted_hand}"
                "\nCards have been distributed and it seems like"
                " my first card is an ACE !"
                "\nI'm offering you an Insurance (a side bet) with a cost of the half"
                " amount your bet before I peek over my hole card."
                "\nIf I peek my hole card and turns out I got Blackjack, you'll win an"
                " amount equal to your bet."
                "\nIf I get not Blackjack, you'll lose half of your bet."
            ),
            reply_markup=builder.as_markup(),
        )

    async def peek_hole(self) -> None:
        # Resolve insurance bet.
        if self.insurance and self.player_bets:
            # Deposit an amount of bet if player wins insurance bet.
            if self.dealer_hand.is_blackjack:
                _ = await self.bank_account.deposit(
                    self.bet,
                    "Blackjack insurance payout.",
                )

            # Withdraw half amount of bet if player loses insurance bet.
            else:
                _ = await self.bank_account.withdraw(
                    self.bet / 2,
                    "Blackjack insurance loss.",
                )

        # If dealer gets blackjack
        if self.dealer_hand.is_blackjack:
            # Reveal the hole card.
            self.dealer_hand.hide_hole_card = False

            # If player is dealt Blackjack, it's a push.
            if self.player_hand.is_blackjack:
                # Deposit the initial bet if it's a push.
                if self.player_bets:
                    _ = await self.bank_account.deposit(
                        self.bet,
                        "Blackjack push refund.",
                    )

                description = (
                    f"{self.formatted_hand}"
                    f"\n{self.formatted_insurance_info}"
                    "\n\nWe both got Blackjack ! It's a push."
                )

            # Player loses their bet if they're not dealt Blackjack too.
            else:
                description = (
                    f"{self.formatted_hand}"
                    f"\n{self.formatted_insurance_info}"
                    "\n\nI got Blackjack ! I won this whole darling..."
                )

            # Send result embed.
            await self.msg.edit_text(text=description, reply_markup=None)

            # Close the session.
            _ = self.session.close()

        else:
            # Player turn starts.
            await self.player_turn()

    async def player_turn(self) -> None:
        # If player gets Blackjack
        if self.player_hand.is_blackjack:
            # Reveal the hole card.
            self.dealer_hand.hide_hole_card = False

            # Deposit initial bet + 6:5 (1.2) of player's bet.
            if self.player_bets:
                _ = await self.bank_account.deposit(
                    self.bet * 2.2,
                    "Blackjack blackjack payout.",
                )

                # Send result embed.
                await self.msg.edit_text(
                    (
                        f"{self.formatted_hand}"
                        f"\n{self.formatted_insurance_info}"
                        "\n\nYou got a Blackjack ! You Won this match."
                    ),
                    reply_markup=None,
                )

            # Close the session.
            _ = self.session.close()

        else:
            # Add player's turn related buttons
            builder = InlineKeyboardBuilder()
            builder.button(
                text="hit",
                callback_data=ButtonCallback(user_id=self.user.id, action="hit"),
            )
            builder.button(
                text="stand",
                callback_data=ButtonCallback(user_id=self.user.id, action="stand"),
            )
            builder.button(
                text="surrender",
                callback_data=ButtonCallback(user_id=self.user.id, action="surrender"),
            )
            if self.player_hand.value in (9, 10, 11) and self.player_bets:
                builder.button(
                    text="doubledown",
                    callback_data=ButtonCallback(
                        user_id=self.user.id,
                        action="doubledown",
                    ),
                )
            builder.adjust(2)
            self.state = "insurance_action"

            self.state = "player_action"
            # Send player's turn notification embed.
            await self.msg.edit_text(
                text=(
                    f"{self.formatted_hand}"
                    f"\n{self.formatted_insurance_info}"
                    "\n\nSince Neither of us got Blackjack, It's your turn now"
                    " to decide what to do."
                ),
                reply_markup=builder.as_markup(),
            )

    async def dealer_turn(self) -> None:
        # Reveal the hole card.
        self.dealer_hand.hide_hole_card = False

        # Send dealer turn notification embed.
        await self.msg.edit_text(
            text=(
                f"{self.formatted_hand}"
                f"\n{self.formatted_insurance_info}"
                "\n\nIt's now my turn to play the hole card."
            ),
            reply_markup=None,
        )

        await asyncio.sleep(3)  # Dramatic short delay

        # Hit one card to the dealer's hand until the value is <= 16.
        while self.dealer_hand.value <= DEALER_STAND_VALUE:
            # Send dealer hit notification embed.
            await self.msg.edit_text(
                text=(
                    f"{self.formatted_hand}"
                    f"\n{self.formatted_insurance_info}"
                    f"\n\nI got {self.dealer_hand.value}. I must Hit."
                ),
                reply_markup=None,
            )

            await asyncio.sleep(2)  # Dramatic short delay

            # Hit one card to the dealer's hand.
            self.dealer_hand.hit(self.deck.pop())

            # If dealer busts
            if self.dealer_hand.is_busted:
                # Deposit initial bet + an amount of bet if the dealer busts.
                if self.player_bets:
                    _ = await self.bank_account.deposit(
                        self.bet * 2,
                        "Blackjack win payout.",
                    )

                # Send result embed.
                await self.msg.edit_text(
                    text=(
                        f"{self.formatted_hand}"
                        f"\n{self.formatted_insurance_info}"
                        f"\n\nI got {self.dealer_hand.value}. I Bust !"
                        " You Won the match."
                    ),
                    reply_markup=None,
                )

                # Close the session.
                _ = self.session.close()

                return

        # If dealer and player value are equal, it's a push.
        if self.dealer_hand.value == self.player_hand.value:
            # Send result embed.
            await self.msg.edit_text(
                text=(
                    f"{self.formatted_hand}"
                    f"\n{self.formatted_insurance_info}"
                    "\n\nWe have equal scores ! This match is a push."
                ),
                reply_markup=None,
            )

        # If player's value is higher
        elif self.player_hand.value > self.dealer_hand.value:
            # Deposit initial bet + an amount of bet if player has higher value.
            if self.player_bets:
                _ = await self.bank_account.deposit(
                    self.bet * 2,
                    "Blackjack win payout.",
                )

            # Send result embed.
            await self.msg.edit_text(
                text=(
                    f"{self.formatted_hand}"
                    f"\n{self.formatted_insurance_info}"
                    "\n\nYou have a higher score ! You Won."
                ),
                reply_markup=None,
            )

        # If dealer's value is higher, player loses their bet.
        else:
            # Send result embed.
            await self.msg.edit_text(
                text=(
                    f"{self.formatted_hand}"
                    f"\n{self.formatted_insurance_info}"
                    "\n\nI have a higher score ! You lost."
                ),
                reply_markup=None,
            )

        # Close the session.
        _ = self.session.close()

    async def on_timeout(self) -> None:
        if self.player_bets:
            # Deposit half amount of bet if player timeouts which results in
            # surrendering and forfeiting half of their bet.
            _ = await self.bank_account.deposit(
                self.bet / 2,
                "Blackjack surrender refund.",
            )

            description = (
                "⏰ Game timeout. which results in surrendering and forfeiting"
                " half amount of bet."
            )
        else:
            description = "⏰ Game timeout. which results in surrendering."

        # Send timeout embed.
        await self.msg.edit_text(text=description, reply_markup=None)

        # Close the session.
        _ = self.session.close()


# refuse button
@ROUTER.callback_query(ButtonCallback.filter(F.action == "refuse"))
async def refuse(
    callback: CallbackQuery,
    callback_data: ButtonCallback,
) -> None:
    view = BlackjackView.games[callback_data.user_id]

    await callback.answer()

    if callback.from_user.id != callback_data.user_id:
        await callback.answer("You can't play in this match.", show_alert=True)
        return

    if view.state == "insurance_action":
        view.state = None

        if datetime.now(timezone.utc) > view.expires_at:
            await view.on_timeout()
            return

        view.insurance = False  # doesn't take the insurance

        await view.message.delete_reply_markup()

        await view.peek_hole()


# accept button
@ROUTER.callback_query(ButtonCallback.filter(F.action == "accept"))
async def accept(
    callback: CallbackQuery,
    callback_data: ButtonCallback,
) -> None:
    view = BlackjackView.games[callback_data.user_id]

    await callback.answer()

    if callback.from_user.id != callback_data.user_id:
        await callback.answer("You can't play in this match.", show_alert=True)
        return

    if view.state == "insurance_action":
        view.state = None

        if datetime.now(timezone.utc) > view.expires_at:
            await view.on_timeout()
            return

        view.insurance = True  # takes the insurance for the player

        await view.message.delete_reply_markup()

        await view.peek_hole()


@ROUTER.callback_query(ButtonCallback.filter(F.action == "hit"))
async def hit(callback: CallbackQuery, callback_data: ButtonCallback) -> None:
    view = BlackjackView.games[callback_data.user_id]

    await callback.answer()

    if callback.from_user.id != callback_data.user_id:
        await callback.answer("You can't play in this match.", show_alert=True)
        return

    if view.state == "player_action":
        view.state = None

        if datetime.now(timezone.utc) > view.expires_at:
            await view.on_timeout()
            return

    # Hit one card to the player's hand.
    view.player_hand.hit(view.deck.pop())

    # If player busts, they lose their bet.
    if view.player_hand.is_busted:
        # Reveal the hole card.
        view.dealer_hand.hide_hole_card = False

        # Send result embed.
        await view.msg.edit_text(
            text=(
                f"{view.formatted_hand}"
                f"\n{view.formatted_insurance_info}"
                "\n\nYou Hit and Bust ! You lost.."
            ),
            reply_markup=None,
        )

        # Close the session.
        _ = view.session.close()

    else:
        builder = InlineKeyboardBuilder()
        builder.button(
            text="hit",
            callback_data=ButtonCallback(user_id=view.user.id, action="hit"),
        )
        builder.button(
            text="stand",
            callback_data=ButtonCallback(user_id=view.user.id, action="stand"),
        )
        builder.adjust(2)

        view.state = "player_action"

        # Send hit embed.
        await view.msg.edit_text(
            text=(
                f"{view.formatted_hand}\n{view.formatted_insurance_info}\n\nYou Hit."
            ),
            reply_markup=builder.as_markup(),
        )


@ROUTER.callback_query(ButtonCallback.filter(F.action == "stand"))
async def stand(callback: CallbackQuery, callback_data: ButtonCallback) -> None:
    view = BlackjackView.games[callback_data.user_id]

    await callback.answer()

    if callback.from_user.id != callback_data.user_id:
        await callback.answer("You can't play in this match.", show_alert=True)
        return

    if view.state == "player_action":
        view.state = None

        if datetime.now(timezone.utc) > view.expires_at:
            await view.on_timeout()
            return

        await view.dealer_turn()


@ROUTER.callback_query(ButtonCallback.filter(F.action == "doubledown"))
async def doubledown(
    callback: CallbackQuery,
    callback_data: ButtonCallback,
) -> None:
    view = BlackjackView.games[callback_data.user_id]

    await callback.answer()

    if callback.from_user.id != callback_data.user_id:
        await callback.answer("You can't play in this match.", show_alert=True)
        return

    if view.state == "player_action":
        view.state = None

        if datetime.now(timezone.utc) > view.expires_at:
            await view.on_timeout()
            return

    # Withdraw bet for double down bet.
    if view.player_bets:
        _ = await view.bank_account.withdraw(
            view.bet,
            "Blackjack double down wager.",
        )
    # Update bet in the pot.
    view.bet *= 2

    # Hit one more card to the player's hand.
    view.player_hand.hit(view.deck.pop())

    # If player busts, they lose their bet.
    if view.player_hand.is_busted:
        # Reveal the hole card.
        view.dealer_hand.hide_hole_card = False

        # Send result embed.
        await view.msg.edit_text(
            text=(
                f"{view.formatted_hand}"
                f"\n{view.formatted_insurance_info}"
                "\n\nYou Doubled Down and Bust ! You lost it so bad.."
            ),
            reply_markup=None,
        )

        # Close the session.
        _ = view.session.close()

    else:
        await view.dealer_turn()


@ROUTER.callback_query(ButtonCallback.filter(F.action == "surrender"))
async def surrender(
    callback: CallbackQuery,
    callback_data: ButtonCallback,
) -> None:
    view = BlackjackView.games[callback_data.user_id]

    await callback.answer()

    if callback.from_user.id != callback_data.user_id:
        await callback.answer("You can't play in this match.", show_alert=True)
        return

    if view.state == "player_action":
        view.state = None

        if datetime.now(timezone.utc) > view.expires_at:
            await view.on_timeout()
            return

    # Reveal the hole card.
    view.dealer_hand.hide_hole_card = False

    # Deposit half of bet if player surrenders and forfeits half of their bet.
    if view.player_bets:
        _ = await view.bank_account.deposit(
            view.bet / 2,
            "Blackjack surrender refund.",
        )

        description = (
            f"{view.formatted_hand}"
            f"\n{view.formatted_insurance_info}"
            "\n\nYou surrendered and forfeit half of your bet."
        )
    else:
        description = (
            f"{view.formatted_hand}"
            f"\n{view.formatted_insurance_info}"
            "\n\nYou surrendered."
        )

    # Send surrender embed.
    await view.msg.edit_text(text=description, reply_markup=None)

    # Close the session.
    _ = view.session.close()
