"""Tarot card deck definitions and drawing logic.

Builds the full 78-card tarot deck (22 Major Arcana + 56 Minor Arcana across
Swords, Wands, Cups, and Pentacles) as a flat list of formatted card strings,
and exposes `TarotCard.draw()` to sample N unique cards from that deck.

The deck is built once at import time as a side effect of instantiating
`TarotCard` for every card; instances register themselves into the shared
`TarotCard.cards` class-level list.
"""

from __future__ import annotations

__all__ = ["MAX_DRAW_NUMBER", "TarotCard", "draw_tarot_card"]

import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import Final, final, override

MAX_DRAW_NUMBER = 15

_MAJOR_ARCANAS = (
    ("The Fool", "🪶"),
    ("The Magician", "🪄"),
    ("The High Priestess", "🌙"),
    ("The Empress", "🌹"),
    ("The Emperor", "👑"),
    ("The Hierophant", "⛪"),
    ("The Lovers", "💞"),
    ("The Chariot", "🛡️"),
    ("Strength", "🦁"),
    ("The Hermit", "🏮"),
    ("Wheel of Fortune", "🎡"),
    ("Justice", "⚖️"),
    ("The Hanged Man", "🪢"),
    ("Death", "☠️"),
    ("Temperance", "🏺"),
    ("The Devil", "🔱"),
    ("The Tower", "🗼"),
    ("The Star", "🌟"),
    ("The Moon", "🌘"),
    ("The Sun", "☀️"),
    ("Judgement", "📯"),
    ("The World", "🌐"),
)

_NUM_TO_WORD: dict[int, str] = {
    1: "Ace",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
}


@final
class _Suits(Enum):
    """Represents suits of tarot."""

    SWORDS = auto()
    WANDS = auto()
    CUPS = auto()
    PENTACLES = auto()

    @property
    def emoji(self) -> str:
        """Return corresponding emoji of the suit."""
        return {
            _Suits.SWORDS: "⚔️",
            _Suits.WANDS: "🪾",
            _Suits.CUPS: "💧",
            _Suits.PENTACLES: "🪙",
        }[self]


@final
class _CourtCards(Enum):
    """Represents court cards of tarot."""

    PAGE = auto()
    KNIGHT = auto()
    QUEEN = auto()
    KING = auto()

    @property
    def emoji(self) -> str:
        """Return corresponding emoji of the court card."""
        return {
            _CourtCards.PAGE: "🧑‍🎓",
            _CourtCards.KNIGHT: "🐎",
            _CourtCards.QUEEN: "👸",
            _CourtCards.KING: "🤴",
        }[self]


@final
@dataclass(frozen=True, slots=True)
class TarotCard:
    """Represents a tarot card."""

    number: int | None
    title: str
    emoji: str

    def __post_init__(self) -> None:
        """Raise an error if entered number is negative after initialization."""
        if self.number is not None and self.number < 0:
            msg = "Tarot card number can not be negative."
            raise ValueError(msg)

    @override
    def __str__(self) -> str:
        """Return formatted string of the card."""
        number_string = f"{self.number}" if self.number is not None else "-"
        return f"({number_string}) {self.title} {self.emoji}"


def _build_deck() -> list[TarotCard]:
    """Construct the full 78-card tarot deck.

    Returns:
        list[TarotCard]: Return the created deck.

    """
    # Add major arcana cards to the deck.
    deck = [
        TarotCard(number=index, title=title, emoji=emoji)
        for index, (title, emoji) in enumerate(_MAJOR_ARCANAS)
    ]

    # Add minor arcana cards to the deck.
    for suit in _Suits:
        # Add ace through ten cards.
        deck += [
            TarotCard(
                number=number,
                title=f"{_NUM_TO_WORD[number]} of {suit.name.title()}",
                emoji=suit.emoji,
            )
            for number in range(1, 11)
        ]

        # Add court cards.
        deck += [
            TarotCard(
                number=None,
                title=f"{court.name.title()} of {suit.name.title()}",
                emoji=f"{court.emoji}{suit.emoji}",
            )
            for court in _CourtCards
        ]

    return deck


_DECK: Final[list[TarotCard]] = _build_deck()


def draw_tarot_card(count: int = 1) -> list[TarotCard]:
    """Draw N cards from the tarot deck.

    Args:
        count (int): Number of cards to draw.

    Returns:
        list[TarotCard]: Return a list containing chosen cards.

    """
    # Raise an error if entered draw number is zero or negative.
    if count <= 0:
        msg = "Draw number must be positive."
        raise ValueError(msg)

    # Raise an error if entered draw number is greater than maximum allowed draw number.
    if count > MAX_DRAW_NUMBER:
        msg = f"Maximum draw number is {MAX_DRAW_NUMBER}."
        raise ValueError(msg)

    return random.sample(_DECK, count)
