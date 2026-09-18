from __future__ import annotations

__all__ = ["MAX_DRAW_NUMBER", "TarotCard"]

import random
from enum import Enum, auto
from typing import ClassVar, final

MAX_DRAW_NUMBER = 15

MAJOR_ARCANAS = (
    ("The Fool", "🪶"),
    ("The Magician", "🪄"),
    ("The High Priestess", "🌙"),
    ("The Empress", "🌹"),
    ("The Emperor", "👑"),
    ("The Hierophant", "⛪"),
    ("The Lovers", "💞"),
    ("The Chariot", "🛡️"),
    ("Justice", "⚖️"),
    ("The Hermit", "🏮"),
    ("Wheel of Fortune", "🎡"),
    ("Strength", "🦁"),
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

NUM_TO_WORD: dict[int, str] = {
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
        """Return coresponding emoji of the suit."""
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
        """Return coresponding emoji of the court card."""
        return {
            _CourtCards.PAGE: "🧑‍🎓",
            _CourtCards.KNIGHT: "🐎",
            _CourtCards.QUEEN: "👸",
            _CourtCards.KING: "🤴",
        }[self]


@final
class TarotCard:
    """Represents all tarot cards."""

    cards: ClassVar[list[str]] = []

    def __init__(self, number: int | None, title: str, emoji: str) -> None:
        """Initialize a tarot card.

        Args:
            number (int | None): Number of the card (court cards have no number).
            title (str): Title of the card.
            emoji (str): Emoji of the card.

        Raises:
            ValueError: Raise when entered number is invalid.

        """
        if number and number < 0:
            msg = "Tarot card number can not be negative."
            raise ValueError(msg)
        self.number: int | None = number
        self.title: str = title
        self.emoji: str = emoji

        TarotCard.cards.append(self.formatted)

    @property
    def formatted(self) -> str:
        """Return formatted string of the card."""
        number_string = f"{self.number}" if self.number is not None else "-"
        return f"({number_string}) {self.title} {self.emoji}"

    @classmethod
    def draw(cls, number: int) -> list[str]:
        """Draw N cards from the tarot deck.

        Args:
            number (int): Number of cards to draw.

        Returns:
            list[str]: Return a list containing chosen cards.

        """
        if number < 0:
            msg = "Draw number can not be negative."
            raise ValueError(msg)
        if number == 0:
            msg = "Draw number can not be zero."
            raise ValueError(msg)
        if number > MAX_DRAW_NUMBER:
            msg = f"Maximum draw number is {MAX_DRAW_NUMBER}."
            raise ValueError(msg)

        return random.sample(TarotCard.cards, number)


# Add major arcana cards to the deck.
for index, (title, emoji) in enumerate(MAJOR_ARCANAS):
    TarotCard(index, title, emoji)

# Add minor arcana cards to the deck.
for suit in _Suits:
    # Ace through ten
    for number in range(1, 11):
        TarotCard(
            number=number,
            title=f"{NUM_TO_WORD[number]} of {suit.name.title()}",
            emoji=suit.emoji,
        )

    # Court cards
    for court in _CourtCards:
        TarotCard(
            number=None,
            title=f"{court.name.title()} of {suit.name.title()}",
            emoji=f"{court.emoji}{suit.emoji}",
        )
