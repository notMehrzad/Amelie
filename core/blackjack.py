"""Contains logic for blackjack game."""

from __future__ import annotations

__all__ = [
    "DEALER_STAND_VALUE",
    "MAX_BET",
    "MIN_BET",
    "BlackjackHand",
    "generate_deck",
]

import random
from typing import ClassVar, final, override

MAX_BET = 300
MIN_BET = 100

# Game logic constants
_BLACKJACK_CARD_NUMBER = 2
_BLACKJACK_SCORE = 21
DEALER_STAND_VALUE = 16


@final
class _Card:
    """Represents a card from the standard 52-card deck."""

    RANKS = (2, 3, 4, 5, 6, 7, 8, 9, 10, "J", "Q", "K", "A")
    SUITS = ("H", "C", "D", "S")
    SYMBOLS: ClassVar = {"H": "♥️", "C": "♣️", "D": "♦️", "S": "♠️"}

    def __init__(self, rank: int | str, suit: str) -> None:
        """Initialize a card."""
        if rank not in _Card.RANKS or suit not in _Card.SUITS:
            raise ValueError

        self.rank = rank
        self.suit = suit
        self.symbol = _Card.SYMBOLS[suit]


@final
class BlackjackHand:
    """Represents a Blackjack hand."""

    def __init__(self, initial_card: list[_Card]) -> None:
        """Initialize a Blackjack hand."""
        self.cards: list[_Card] = initial_card
        # Hole card is initially hidden if it's dealer's hand.
        self.hide_hole_card: bool | None = None

    @property
    def is_blackjack(self) -> bool:
        """Determine if the hand is Blackjack."""
        return bool(
            len(self.cards) == _BLACKJACK_CARD_NUMBER
            and self.value == _BLACKJACK_SCORE,
        )

    @property
    def is_busted(self) -> bool:
        """Determine if the hand is busted."""
        return self.value > _BLACKJACK_SCORE

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

        while value > _BLACKJACK_SCORE and aces > 0:
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

    def hit(self, card: _Card) -> None:
        """Add a card to the hand (aka. hit)."""
        self.cards.append(card)


def generate_deck(*, shoe: int = 1, shuffle: bool = True) -> list[_Card]:
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

    deck: list[_Card] = []
    # Generate deck.
    deck.extend(
        _Card(rank, suit)
        for _ in range(shoe)
        for rank in _Card.RANKS
        for suit in _Card.SUITS
    )

    # Shuffle deck if shuffle is True.
    if shuffle:
        random.shuffle(deck)

    return deck
