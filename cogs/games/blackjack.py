"""blackjack command.

Implements all game logic with interacting buttons in discord.
"""

from __future__ import annotations

__all__ = []

import asyncio
import contextlib
import random
from typing import ClassVar, final, override

import discord
from discord import app_commands
from discord.ext import commands

from core.bank import BankAccount, get_bank_account
from core.help import HelpData
from core.log_handler import logger_setup
from core.session import Session, get_session

MAX_BET = 300
MIN_BET = 100

# Game logic constants
BLACKJACK_CARD_NUMBER = 2
BLACKJACK_SCORE = 21
DEALER_STAND_VALUE = 16

BLACKJACK_EMBED_TITLE = "Blackjack 🖤"


logger = logger_setup(__name__)


@final
class Card:
    """Represents a card from the standard 52-card deck."""

    RANKS = (2, 3, 4, 5, 6, 7, 8, 9, 10, "J", "Q", "K", "A")
    SUITS = ("H", "C", "D", "S")
    SYMBOLS: ClassVar = {"H": "♥️", "C": "♣️", "D": "♦️", "S": "♠️"}

    def __init__(self, rank: int | str, suit: str) -> None:
        """Initialize a card."""
        if rank not in Card.RANKS or suit not in Card.SUITS:
            raise ValueError

        self.rank = rank
        self.suit = suit
        self.symbol = Card.SYMBOLS[suit]


class BlackjackHand:
    """Represents a Blackjack hand."""

    def __init__(self, initial_card: list[Card]) -> None:
        """Initialize a Blackjack hand."""
        self.cards: list[Card] = initial_card
        # Hole card is initially hidden if it's dealer's hand.
        self.hide_hole_card: bool | None = None

    @property
    def is_blackjack(self) -> bool:
        """Determine if the hand is Blackjack."""
        return bool(
            len(self.cards) == BLACKJACK_CARD_NUMBER and self.value == BLACKJACK_SCORE,
        )

    @property
    def is_busted(self) -> bool:
        """Determine if the hand is busted."""
        return self.value > BLACKJACK_SCORE

    @property
    def value(self) -> int:
        """Determine the value of the hand."""
        value = 0
        aces = 0
        for card in self.cards:
            if card.rank == "A":
                value += 11
                aces += 1
            elif card.rank in ("K", "Q", "J", 10):
                value += 10
            else:
                value += int(card.rank)

        while value > BLACKJACK_SCORE and aces > 0:
            value -= 10
            aces -= 1

        return value

    @override
    def __str__(self) -> str:
        """Return a formatted string of cards in the hand for display."""
        # Show all cards if hole card is not hidden.
        if not self.hide_hole_card:
            return "   ".join(f"{card.rank}{card.symbol}" for card in self.cards)

        # Second initial card stays hidden if hole card is True.
        return f"{self.cards[0].rank}{self.cards[0].symbol}   🎴"

    def hit(self, card: Card) -> None:
        """Add a card to the hand (aka. hit)."""
        self.cards.append(card)


def format_hands(dealer_hand: BlackjackHand, player_hand: BlackjackHand) -> str:
    """Show a formatted string of two Blackjack hands to display.

    Args:
        dealer_hand (BlackjackHand): Dealer's hand.
        player_hand (BlackjackHand): Player's hand.

    Returns:
        str: Return a formatted string to display.

    """
    return f"{dealer_hand}\n\n{player_hand}"


def generate_deck(*, shoe: int = 1, shuffle: bool = True) -> list[Card]:
    """Generate deck.

    Args:
        shoe (int, optional): Number of standard 52-card to be included in
            deck(a.k.a. shoe). Defaults to 1.
        shuffle (bool, optional): Whether to shuffle the deck list or not. Defaults to
            True.

    Returns:
        list[Card]: Return the generated deck.

    """
    # Raise an error if shoe is 0.
    if shoe == 0:
        msg = "Shoe number can not be 0."
        raise ValueError(msg)

    # Raise an error if shoe is negative.
    if shoe < 0:
        msg = "Shoe number can not be negative."
        raise ValueError(msg)

    deck: list[Card] = []
    # Generate deck.
    deck.extend(
        Card(rank, suit)
        for _ in range(shoe)
        for rank in Card.RANKS
        for suit in Card.SUITS
    )

    # Shuffle deck if shuffle is True.
    if shuffle:
        random.shuffle(deck)

    return deck


@final
class Blackjack(commands.Cog):
    """Blackjack command."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    Help = HelpData(
        category=HelpData.CommandCategory.GAMES,
        is_dm_only=False,
        is_server_only=False,
        subcommands=None,
        permissions=None,
        help_=(
            "A card game where you compete against the dealer."
            " Your goal is to have a hand value closer to 21"
            " than the dealer's without going over 21."
            "\nCard values:"
            "\n2-10: Worth their face value."
            "\nK, Q, J, 10: Worth 10 points."
            "\nA: Worth 11 points by default, but is automatically counted as 1"
            " whenever counting it as 11 would cause the hand to bust."
            "\n1. You and the dealer are each dealt two initial cards. One of the"
            " dealer's cards is face up, while the other"
            " remains hidden as the hole card."
            "\n2. If the dealer's upcard is an Ace, you'll"
            " be offered the option to place"
            " an Insurance side bet before play continues."
            "\n3. On your turn choose `Hit` to draw another card, `Stand` to"
            " end your turn, `Double Down` to double your bet and receive"
            " exactly one more card or `Surrender` to end the game immediately and"
            " forfeit half of your bet."
            "\n4. If your hand exceeds 21, you `Bust` and immediately lose"
            " the game and lose your bet."
            "\n5. Once your turn ends, the dealer reveals the hole card and keeps"
            " hitting until reaching 17 or higher."
            "\n6. If the dealer busts, you win an amount equal to your bet."
            " Otherwise, the hand closest"
            " to 21 wins. If both hands have the same value, the round ends"
            " in a `Push` and your bet is returned."
            "\nNote: `Surrender` and `Double Down` can only be done before taking"
            " any other action (Hit and Stand)."
            "\nNote: Insurance will be offered only when the dealer's upcard is an Ace."
            " You may place a side bet of up to half your original bet. If"
            " the dealer has Blackjack, Insurance pays 2:1."
            " Otherwise, the Insurance bet is lost and the round continues."
            "\nNote: When the dealer's upcard is Ace or any 10-value card,"
            " the dealer peeks at"
            " the hole card; If the hole card makes the dealer's hand a"
            " `Blackjack`, the dealer wins immediately and the player loses"
            " unless they also have Blackjack which ends in a `Push`"
            " and the player's bet will be returned. The Insurance bet is resolved"
            " immediately after the dealer peeks at the hole card."
            "\nNote: If the player is dealt a Blackjack, they immediately win the game"
            " unless the dealer also has Blackjack."
        ),
        brief="The traditional Blackjack game.",
        usage="<bet_amount[*optional*]>",
        aliases=["bj"],
    )

    @commands.command(name="blackjack", **Help.kwargs)
    async def blackjack(
        self,
        ctx: commands.Context[commands.Bot],
        bet: int | str | None = None,
    ) -> None:
        # Check bet validity if player bets.
        if bet is not None:
            # Raise an error if bet is not an integer.
            if not isinstance(bet, int):
                _ = await ctx.reply("Enter a valid integer bet amount.")
                return

            # Raise an error if bet is lower than minimum bet amount.
            if bet < MIN_BET:
                _ = await ctx.reply(
                    f"The minimum bet amount for Blackjack is **{MIN_BET}**.",
                )
                return
            # Raise an error if bet is higher than maximum bet amount.
            if bet > MAX_BET:
                _ = await ctx.reply(
                    f"The maximum bet amount for Blackjack is **{MAX_BET}**.",
                )
                return

            # Fetch user's bank account.
            bank_account = await get_bank_account(ctx.author.id)
            # Raise an error if user has no bank account.
            if bank_account is None:
                _ = await ctx.reply(
                    (
                        "You have no balance account !"
                        "\nTry `/daily` to claim your first daily reward and get your"
                        " balance account."
                    ),
                )
                return

            # Raise an error if bet is higher than user's current balance.
            if bet > bank_account.balance:
                _ = await ctx.reply(
                    (
                        "Your desired bet is higher than your current balance."
                        "\nTry `/balance` to see your balance."
                    ),
                )
                return
        else:
            bank_account = None

        session = get_session(ctx.author.id, Session.Types.GAMBLING)
        # Raise an error if user has an active session.
        if session is not None:
            _ = await ctx.reply("You have an open gambling session somewhere.")
            return

        # Open a gambling session for user.
        session = Session(ctx.author.id, Session.Types.GAMBLING)

        # Start Blackjack view.
        await BlackjackView(ctx, bet, bank_account, session).start()

    @blackjack.error
    async def blackjack_error(
        self,
        ctx: commands.Context[commands.Bot],
        error: commands.CommandError,
    ) -> None:
        # Close user's gambling session if an error occurs.
        session = get_session(ctx.author.id, Session.Types.GAMBLING)
        if session:
            _ = session.close()

        logger.error("❌ Something went wrong with blackjack command.", exc_info=error)
        _ = await ctx.reply("Something went wrong with **blackjack**.")

    # blackjack slash command
    @app_commands.command(name="blackjack", description=Help.brief, extras=Help.extras)
    @app_commands.describe(bet="The amount you want to bet.")
    async def slash_blackjack(
        self,
        interaction: discord.Interaction,
        bet: int | None = None,
    ) -> None:
        # Check bet validity if player bets.
        if bet is not None:
            session = get_session(interaction.user.id, Session.Types.GAMBLING)
            # Raise an error if user has an active session.
            if session is not None:
                _ = await interaction.response.send_message(
                    "You have an open gambling session somewhere.",
                    ephemeral=True,
                )
                return

            # Raise an error if bet is lower than minimum bet amount.
            if bet < MIN_BET:
                _ = await interaction.response.send_message(
                    f"The minimum bet amount for Blackjack is **{MIN_BET}**.",
                    ephemeral=True,
                )
                return
            # Raise an error if bet is higher than maximum bet amount.
            if bet > MAX_BET:
                _ = await interaction.response.send_message(
                    f"The maximum bet amount for Blackjack is **{MAX_BET}**.",
                    ephemeral=True,
                )
                return

            # Fetch user's bank account.
            bank_account = await get_bank_account(interaction.user.id)
            # Raise an error if user has no bank account.
            if bank_account is None:
                _ = await interaction.response.send_message(
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
                _ = await interaction.response.send_message(
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
        session = Session(interaction.user.id, Session.Types.GAMBLING)

        # Start Blackjack view.
        await BlackjackView(interaction, bet, bank_account, session).start()

    @slash_blackjack.error
    async def slash_blackjack_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        # Close user's gambling session if an error occurs.
        session = get_session(interaction.user.id, Session.Types.GAMBLING)
        if session:
            _ = session.close()

        logger.error("❌ Something went wrong with /blackjack command.", exc_info=error)
        try:
            _ = await interaction.response.send_message(
                "Something went wrong with **blackjack**.",
                ephemeral=True,
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "Something went wrong with **blackjack**.",
                ephemeral=True,
            )


@final
class BlackjackView(discord.ui.View):
    def __init__(
        self,
        ctx: commands.Context[commands.Bot] | discord.Interaction,
        bet: int | None,
        bank_account: BankAccount | None,
        session: Session,
    ) -> None:
        super().__init__(timeout=180)
        if isinstance(ctx, discord.Interaction):
            self.slash_command = True
            self.interaction = ctx
            self.user = self.interaction.user
        else:
            self.slash_command = False
            self.ctx = ctx
            self.user = self.ctx.author
        self.embed_color = discord.Color.random()
        self.timestamp = discord.utils.utcnow()

        # The initial bet will be taken into pot.
        if bet is not None:
            self.bet: int = bet
        if bank_account is not None:
            self.bank_account: BankAccount = bank_account
        self.player_bets: bool = bool(bet is not None and bank_account is not None)

        self.session: Session = session

        self.insurance = None

        for button in self.children:
            _ = self.remove_item(button)

    async def _edit_message(
        self,
        embed: discord.Embed,
        view: discord.ui.View | None,
    ) -> None:
        """Edit sent message.

        A helper that edits sent message whether it's application command message or
        command message.

        Args:
            embed (discord.Embed): Embed to replace.
            view (discord.ui.View | None): View to replace.

        """
        if self.slash_command:
            _ = await self.interaction.edit_original_response(embed=embed, view=view)
        else:
            _ = await self.msg.edit(embed=embed, view=view)

    def _finish(self) -> None:
        """Finish the game.

        A helper that finished the game by closing the session and stopping teh view.
        """
        # Close the session.
        _ = self.session.close()

        # Stop the view.
        self.stop()

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

        initial_embed = discord.Embed(
            color=self.embed_color,
            title=BLACKJACK_EMBED_TITLE,
            description=description,
            timestamp=self.timestamp,
        )
        # Send initial embed.
        if self.slash_command:
            _ = await self.interaction.response.send_message(embed=initial_embed)
        else:
            self.msg = await self.ctx.reply(embed=initial_embed)

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
        _ = self.add_item(self.refuse)
        _ = self.add_item(self.accept)

        insurance_offering_embed = discord.Embed(
            color=self.embed_color,
            title=BLACKJACK_EMBED_TITLE,
            description=(
                "Cards have been distributed and it seems like"
                " my first card is an ACE !"
                "\nI'm offering you an Insurance (a side bet) with a cost of the half"
                " amount your bet before I peek over my hole card."
                "\nIf I peek my hole card and turns out I got Blackjack, you'll win an"
                " amount equal to your bet."
                "\nIf I get not Blackjack, you'll lose half of your bet.\n"
                f"{format_hands(self.dealer_hand, self.player_hand)}"
            ),
            timestamp=self.timestamp,
        )
        # Send insurance offering embed.
        await self._edit_message(insurance_offering_embed, self)

    # refuse button
    @discord.ui.button(label="refuse", style=discord.ButtonStyle.red)
    async def refuse(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button[discord.ui.View],
    ) -> None:
        # Raise an error if interaction is not from the user.
        if interaction.user.id != self.user.id:
            _ = await interaction.response.send_message(
                "You can't play in this match.",
                ephemeral=True,
            )
            return

        # Disable and remove refuse and accept buttons.
        button.disabled = self.accept.disabled = True
        _ = self.remove_item(self.refuse)
        _ = self.remove_item(self.accept)

        self.insurance = False

        await self.peek_hole()

    # accept button
    @discord.ui.button(label="accept", style=discord.ButtonStyle.green)
    async def accept(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button[discord.ui.View],
    ) -> None:
        # Raise an error if interaction is not from the user.
        if interaction.user.id != self.user.id:
            _ = await interaction.response.send_message(
                "You can't play in this match.",
                ephemeral=True,
            )
            return

        # Disable and remove accept and refuse buttons.
        button.disabled = self.refuse.disabled = True
        _ = self.remove_item(self.refuse)
        _ = self.remove_item(self.accept)

        self.insurance = True

        await self.peek_hole()

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

                result_embed = discord.Embed(
                    color=self.embed_color,
                    title=BLACKJACK_EMBED_TITLE,
                    description=(
                        f"{self.formatted_insurance_info}"
                        "\n\nWe both got Blackjack ! It's a push.\n\n"
                        f"{format_hands(self.dealer_hand, self.player_hand)}"
                    ),
                    timestamp=self.timestamp,
                )

            # Player loses their bet if they're not dealt Blackjack too.
            else:
                result_embed = discord.Embed(
                    color=self.embed_color,
                    title=BLACKJACK_EMBED_TITLE,
                    description=(
                        f"{self.formatted_insurance_info}"
                        "\n\nI got Blackjack ! I won this whole darling...\n\n"
                        f"{format_hands(self.dealer_hand, self.player_hand)}"
                    ),
                    timestamp=self.timestamp,
                )

            # Send result embed.
            await self._edit_message(result_embed, None)

            # Finish the game.
            self._finish()

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

            result_embed = discord.Embed(
                color=self.embed_color,
                title=BLACKJACK_EMBED_TITLE,
                description=(
                    f"{self.formatted_insurance_info}"
                    "\n\nYou got a Blackjack ! You Won this match.\n\n"
                    f"{format_hands(self.dealer_hand, self.player_hand)}"
                ),
                timestamp=self.timestamp,
            )
            # Send result embed.
            await self._edit_message(result_embed, None)

            # Finish the game.
            self._finish()

        else:
            # Add player's turn related buttons
            _ = self.add_item(self.hit)
            _ = self.add_item(self.stand)
            _ = self.add_item(self.surrender)
            if self.player_hand.value in (9, 10, 11) and self.player_bets:
                _ = self.add_item(self.double_down)

            player_turn_embed = discord.Embed(
                color=self.embed_color,
                title=BLACKJACK_EMBED_TITLE,
                description=(
                    f"{self.formatted_insurance_info}"
                    "\n\nSince Neither of us got Blackjack, It's your turn now"
                    " to decide what to do.\n\n"
                    f"{format_hands(self.dealer_hand, self.player_hand)}"
                ),
                timestamp=self.timestamp,
            )
            # Send player's turn notification embed.
            await self._edit_message(embed=player_turn_embed, view=self)

    # hit button
    @discord.ui.button(label="hit", style=discord.ButtonStyle.gray)
    async def hit(
        self,
        interaction: discord.Interaction,
        _button: discord.ui.Button[discord.ui.View],
    ) -> None:
        # Raise an error if interaction is not from the user.
        if interaction.user.id != self.user.id:
            _ = await interaction.response.send_message(
                "You can't play in this match.",
                ephemeral=True,
            )
            return

        # Disable and remove surrender and double down buttons.
        self.surrender.disabled = self.double_down.disabled = True

        # Hit one card to the player's hand.
        self.player_hand.hit(self.deck.pop())

        # If player busts, they lose their bet.
        if self.player_hand.is_busted:
            # Reveal the hole card.
            self.dealer_hand.hide_hole_card = False

            result_embed = discord.Embed(
                color=self.embed_color,
                title=BLACKJACK_EMBED_TITLE,
                description=(
                    f"{self.formatted_insurance_info}"
                    "\n\nYou Hit and Bust ! You lost..\n\n"
                    f"{format_hands(self.dealer_hand, self.player_hand)}"
                ),
                timestamp=self.timestamp,
            )
            # Send result embed.
            await self._edit_message(embed=result_embed, view=None)

            # Finish the game.
            self._finish()

        else:
            hit_embed = discord.Embed(
                color=self.embed_color,
                title=BLACKJACK_EMBED_TITLE,
                description=(
                    f"{self.formatted_insurance_info}"
                    "\n\nYou Hit.\n\n"
                    f"{format_hands(self.dealer_hand, self.player_hand)}"
                ),
                timestamp=self.timestamp,
            )
            # Send hit embed.
            await self._edit_message(embed=hit_embed, view=self)

    # stand button
    @discord.ui.button(label="stand", style=discord.ButtonStyle.gray)
    async def stand(
        self,
        interaction: discord.Interaction,
        _button: discord.ui.Button[discord.ui.View],
    ) -> None:
        # Raise an error if interaction is not form the user.
        if interaction.user.id != self.user.id:
            _ = await interaction.response.send_message(
                "You can't play in this match.",
                ephemeral=True,
            )
            return

        await self.dealer_turn()

    # double down button
    @discord.ui.button(label="double down", style=discord.ButtonStyle.blurple)
    async def double_down(
        self,
        interaction: discord.Interaction,
        _button: discord.ui.Button[discord.ui.View],
    ) -> None:
        # Raise an error if interaction is not form the user.
        if interaction.user.id != self.user.id:
            _ = await interaction.response.send_message(
                "You can't play in this match.",
                ephemeral=True,
            )
            return

        # Withdraw bet for double down bet.
        if self.player_bets:
            _ = await self.bank_account.withdraw(
                self.bet,
                "Blackjack double down wager.",
            )
        # Update bet in the pot.
        self.bet *= 2

        # Hit one more card to the player's hand.
        self.player_hand.hit(self.deck.pop())

        # If player busts, they lose their bet.
        if self.player_hand.is_busted:
            # Reveal the hole card.
            self.dealer_hand.hide_hole_card = False

            result_embed = discord.Embed(
                color=self.embed_color,
                title=BLACKJACK_EMBED_TITLE,
                description=(
                    f"{self.formatted_insurance_info}"
                    "\n\nYou Doubled Down and Bust ! You lost it so bad..\n\n"
                    f"{format_hands(self.dealer_hand, self.player_hand)}"
                ),
                timestamp=self.timestamp,
            )
            # Send result embed.
            await self._edit_message(embed=result_embed, view=None)

            # Finish the game.
            self._finish()

        else:
            await self.dealer_turn()

    # surrender button
    @discord.ui.button(label="surrender", style=discord.ButtonStyle.red)
    async def surrender(
        self,
        interaction: discord.Interaction,
        _button: discord.ui.Button[discord.ui.View],
    ) -> None:
        # Raise an error if interaction is not form the user.
        if interaction.user.id != self.user.id:
            _ = await interaction.response.send_message(
                "You can't play in this match.",
                ephemeral=True,
            )
            return

        # Reveal the hole card.
        self.dealer_hand.hide_hole_card = False

        # Deposit half of bet if player surrenders and forfeits half of their bet.
        if self.player_bets:
            _ = await self.bank_account.deposit(
                self.bet / 2,
                "Blackjack surrender refund.",
            )

            description = (
                f"{self.formatted_insurance_info}"
                "\n\nYou surrendered and forfeit half of your bet.\n\n"
                f"{format_hands(self.dealer_hand, self.player_hand)}"
            )
        else:
            description = (
                f"{self.formatted_insurance_info}"
                "\n\nYou surrendered.\n\n"
                f"{format_hands(self.dealer_hand, self.player_hand)}"
            )

        surrender_embed = discord.Embed(
            color=self.embed_color,
            title=BLACKJACK_EMBED_TITLE,
            description=description,
            timestamp=self.timestamp,
        )
        # Send surrender embed.
        await self._edit_message(embed=surrender_embed, view=None)

        # Finish the game.
        self._finish()

    async def dealer_turn(self) -> None:
        # Reveal the hole card.
        self.dealer_hand.hide_hole_card = False

        dealer_turn_embed = discord.Embed(
            color=self.embed_color,
            title=BLACKJACK_EMBED_TITLE,
            description=(
                f"{self.formatted_insurance_info}"
                "\n\nIt's now my turn to play the hole card.\n\n"
                f"{format_hands(self.dealer_hand, self.player_hand)}"
            ),
            timestamp=self.timestamp,
        )
        # Send dealer turn notification embed.
        await self._edit_message(embed=dealer_turn_embed, view=None)

        await asyncio.sleep(3)  # Dramatic short delay

        # Hit one card to the dealer's hand until the value is <= 16.
        while self.dealer_hand.value <= DEALER_STAND_VALUE:
            dealer_hit_embed = discord.Embed(
                color=self.embed_color,
                title=BLACKJACK_EMBED_TITLE,
                description=(
                    f"{self.formatted_insurance_info}"
                    f"\n\nI got {self.dealer_hand.value}. I must Hit.\n\n"
                    f"{format_hands(self.dealer_hand, self.player_hand)}"
                ),
                timestamp=self.timestamp,
            )
            # Send dealer hit notification embed.
            await self._edit_message(embed=dealer_hit_embed, view=None)

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

                result_embed = discord.Embed(
                    color=self.embed_color,
                    title=BLACKJACK_EMBED_TITLE,
                    description=(
                        f"{self.formatted_insurance_info}"
                        f"\n\nI got {self.dealer_hand.value}. I Bust !"
                        " You Won the match.\n\n"
                        f"{format_hands(self.dealer_hand, self.player_hand)}"
                    ),
                    timestamp=self.timestamp,
                )
                # Send result embed.
                await self._edit_message(embed=result_embed, view=None)

                # Finish the game.
                self._finish()

                return

        # If dealer and player value are equal, it's a push.
        if self.dealer_hand.value == self.player_hand.value:
            result_embed = discord.Embed(
                color=self.embed_color,
                title=BLACKJACK_EMBED_TITLE,
                description=(
                    f"{self.formatted_insurance_info}"
                    "\n\nWe have equal scores ! This match is a push.\n\n"
                    f"{format_hands(self.dealer_hand, self.player_hand)}"
                ),
                timestamp=self.timestamp,
            )
            # Send result embed.
            await self._edit_message(embed=result_embed, view=None)

        # If player's value is higher
        elif self.player_hand.value > self.dealer_hand.value:
            # Deposit initial bet + an amount of bet if player has higher value.
            if self.player_bets:
                _ = await self.bank_account.deposit(
                    self.bet * 2,
                    "Blackjack win payout.",
                )

            result_embed = discord.Embed(
                color=self.embed_color,
                title=BLACKJACK_EMBED_TITLE,
                description=(
                    f"{self.formatted_insurance_info}"
                    "\n\nYou have a higher score ! You Won.\n\n"
                    f"{format_hands(self.dealer_hand, self.player_hand)}"
                ),
                timestamp=self.timestamp,
            )
            # Send result embed.
            await self._edit_message(embed=result_embed, view=None)

        # If dealer's value is higher, player loses their bet.
        else:
            result_embed = discord.Embed(
                color=self.embed_color,
                title=BLACKJACK_EMBED_TITLE,
                description=(
                    f"{self.formatted_insurance_info}"
                    "\n\nI have a higher score ! You lost.\n\n"
                    f"{format_hands(self.dealer_hand, self.player_hand)}"
                ),
                timestamp=self.timestamp,
            )
            # Send result embed.
            await self._edit_message(embed=result_embed, view=None)

        # Finish the game.
        self._finish()

    @override
    async def on_timeout(self) -> None:
        # Disable buttons upon timeout.
        for btn in self.children:
            if isinstance(btn, discord.ui.Button):
                btn.disabled = True

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

        timeout_embed = discord.Embed(
            color=self.embed_color,
            title=BLACKJACK_EMBED_TITLE,
            description=description,
            timestamp=self.timestamp,
        )
        # Send timeout embed.
        with contextlib.suppress(discord.NotFound):
            await self._edit_message(embed=timeout_embed, view=self)

        # Finish the game.
        self._finish()

    @override
    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item[discord.ui.View],
    ) -> None:
        # Return the initial bet upon error.
        if self.player_bets:
            _ = await self.bank_account.deposit(self.bet, "Blackjack error refund.")

        logger.error(
            "❌ Something went wrong with blackjack interaction - button: %s",
            getattr(item, "label", "unknown"),
            exc_info=error,
        )
        try:
            _ = await interaction.response.send_message(
                "Something went wrong with **blackjack**.",
                ephemeral=True,
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "Something went wrong with **blackjack**.",
                ephemeral=True,
            )
        except discord.HTTPException:
            pass

        # Finish the game.
        self._finish()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Blackjack(bot))
