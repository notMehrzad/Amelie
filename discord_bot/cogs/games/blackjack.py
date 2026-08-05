"""blackjack command.

Implements all game logic with interacting buttons in discord.
"""

from __future__ import annotations

__all__ = []

import asyncio
import contextlib
from typing import final, override

import discord
from discord import app_commands
from discord.ext import commands

from core.bank import FORMATTED_CURRENCY, BankAccount, get_bank_account
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

BLACKJACK_EMBED_TITLE = "Blackjack ♠️"


logger = setup_logger(__name__)


@final
class Blackjack(commands.Cog):
    """Blackjack command."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="blackjack", **BLACKJACK_HELP.kwargs)
    async def blackjack(
        self,
        ctx: commands.Context[commands.Bot],
        bet: int | str | None = None,
    ) -> None:
        session = get_session(ctx.author.id, Session.SessionTypes.GAMBLING)
        # Raise an error if user has an active session.
        if session is not None:
            _ = await ctx.reply("You have an open gambling session somewhere.")
            return

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

        # Open a gambling session for user.
        session = Session(ctx.author.id, Session.SessionTypes.GAMBLING)

        # Start Blackjack view.
        await BlackjackView(ctx, bet, bank_account, session).start()

    @blackjack.error
    async def blackjack_error(
        self,
        ctx: commands.Context[commands.Bot],
        error: commands.CommandError,
    ) -> None:
        # Close user's gambling session if an error occurs.
        session = get_session(ctx.author.id, Session.SessionTypes.GAMBLING)
        if session:
            _ = session.close()

        logger.error("❌ Something went wrong with blackjack command.", exc_info=error)
        _ = await ctx.reply("Something went wrong with **blackjack**.")

    # blackjack slash command
    @app_commands.command(
        name="blackjack",
        description=BLACKJACK_HELP.brief,
        extras=BLACKJACK_HELP.extras,
    )
    @app_commands.describe(bet="The amount you want to bet.")
    async def slash_blackjack(
        self,
        interaction: discord.Interaction,
        bet: int | None = None,
    ) -> None:
        session = get_session(interaction.user.id, Session.SessionTypes.GAMBLING)
        # Raise an error if user has an active session.
        if session is not None:
            _ = await interaction.response.send_message(
                "You have an open gambling session somewhere.",
                ephemeral=True,
            )
            return

        # Check bet validity if player bets.
        if bet is not None:
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
        session = Session(interaction.user.id, Session.SessionTypes.GAMBLING)

        # Start Blackjack view.
        await BlackjackView(interaction, bet, bank_account, session).start()

    @slash_blackjack.error
    async def slash_blackjack_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        # Close user's gambling session if an error occurs.
        session = get_session(interaction.user.id, Session.SessionTypes.GAMBLING)
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

        self.insurance: bool | None = None

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
    def formatted_hand(self) -> str:
        """Return a formatted string of players hand to display."""
        dealer_value_string = (
            self.dealer_hand.value if not self.dealer_hand.hide_hole_card else "?"
        )
        bet_string = (
            f"\n\nBet: {self.bet} {FORMATTED_CURRENCY}" if self.player_bets else ""
        )
        separator = "\n----" if self.player_bets else "\n\n----"
        return (
            f"Dealer ({dealer_value_string})"
            f"\n{self.dealer_hand}"
            f"\n\nYou ({self.player_hand.value})"
            f"\n{self.player_hand}"
            f"{bet_string}"
            f"{separator}"
        )

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
        """Offer insurance if the face up card is A."""
        # Add related buttons.
        _ = self.add_item(self.refuse)
        _ = self.add_item(self.accept)

        insurance_offering_embed = discord.Embed(
            color=self.embed_color,
            title=BLACKJACK_EMBED_TITLE,
            description=(
                f"{self.formatted_hand}"
                "\nCards have been distributed and it seems like"
                " my first card is an ACE !"
                "\nI'm offering you an Insurance (a side bet) with a cost of the half"
                " amount your bet before I peek over my hole card."
                "\nIf I peek my hole card and turns out I got Blackjack, you'll win an"
                " amount equal to your bet."
                "\nIf I get not Blackjack, you'll lose half of your bet."
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
                        f"{self.formatted_hand}"
                        f"\n{self.formatted_insurance_info}"
                        "\n\nWe both got Blackjack ! It's a push."
                    ),
                    timestamp=self.timestamp,
                )

            # Player loses their bet if they're not dealt Blackjack too.
            else:
                result_embed = discord.Embed(
                    color=self.embed_color,
                    title=BLACKJACK_EMBED_TITLE,
                    description=(
                        f"{self.formatted_hand}"
                        f"\n{self.formatted_insurance_info}"
                        "\n\nI got Blackjack ! I won this whole darling..."
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
        """Enter player's turn state."""
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
                    f"{self.formatted_hand}"
                    f"\n{self.formatted_insurance_info}"
                    "\n\nYou got a Blackjack ! You Won this match."
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
                    f"{self.formatted_hand}"
                    f"\n{self.formatted_insurance_info}"
                    "\n\nSince Neither of us got Blackjack, It's your turn now"
                    " to decide what to do."
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
                    f"{self.formatted_hand}"
                    f"\n{self.formatted_insurance_info}"
                    "\n\nYou Hit and Bust ! You lost.."
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
                    f"{self.formatted_hand}"
                    f"\n{self.formatted_insurance_info}"
                    "\n\nYou Hit."
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
                    f"{self.formatted_hand}"
                    f"\n{self.formatted_insurance_info}"
                    "\n\nYou Doubled Down and Bust ! You lost it so bad.."
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
                f"{self.formatted_hand}"
                f"\n{self.formatted_insurance_info}"
                "\n\nYou surrendered and forfeit half of your bet."
            )
        else:
            description = (
                f"{self.formatted_hand}"
                f"\n{self.formatted_insurance_info}"
                "\n\nYou surrendered."
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
        """Play dealer's turn."""
        # Reveal the hole card.
        self.dealer_hand.hide_hole_card = False

        dealer_turn_embed = discord.Embed(
            color=self.embed_color,
            title=BLACKJACK_EMBED_TITLE,
            description=(
                f"{self.formatted_hand}"
                f"\n{self.formatted_insurance_info}"
                "\n\nIt's now my turn to play the hole card."
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
                    f"{self.formatted_hand}"
                    f"\n{self.formatted_insurance_info}"
                    f"\n\nI got {self.dealer_hand.value}. I must Hit."
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
                        f"{self.formatted_hand}"
                        f"\n{self.formatted_insurance_info}"
                        f"\n\nI got {self.dealer_hand.value}. I Bust !"
                        " You Won the match."
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
                    f"{self.formatted_hand}"
                    f"\n{self.formatted_insurance_info}"
                    "\n\nWe have equal scores ! This match is a push."
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
                    f"{self.formatted_hand}"
                    f"\n{self.formatted_insurance_info}"
                    "\n\nYou have a higher score ! You Won."
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
                    f"{self.formatted_hand}"
                    f"\n{self.formatted_insurance_info}"
                    "\n\nI have a higher score ! You lost."
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
