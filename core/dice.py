from __future__ import annotations

__all__ = [
    "MAX_DICE_COUNT",
    "MAX_DIE_SIDES",
    "MIN_DIE_SIDES",
    "Dice",
    "parse_dice_expression",
]

import re
import secrets
from typing import final

MAX_DICE_COUNT = 100

MIN_DIE_SIDES = 2
MAX_DIE_SIDES = 100


# Define exception classes.
class DiceError(Exception):
    """Base class for all dice exceptions."""


@final
class DiceCountError(DiceError):
    """Raised when trying to roll an invalid number of dice."""

    def __init__(self) -> None:
        """Initialize exception."""
        super().__init__(
            f"Dice rolling count must be between 1 and {MAX_DICE_COUNT}.",
        )


@final
class DieSidesError(DiceError):
    """Raised when trying to create a die with invalid side number."""

    def __init__(self) -> None:
        """Initialize exception."""
        super().__init__(
            f"Die side must be between {MIN_DIE_SIDES} and {MAX_DIE_SIDES}.",
        )


@final
class Dice:
    """Represents a dice."""

    def __init__(self, side: int) -> None:
        """Initialize a dice.

        Args:
            side (int): Number of sides the dice should have.

        """
        # Raise an error if entered side is invalid.
        if not (MIN_DIE_SIDES <= side <= MAX_DIE_SIDES):
            raise DieSidesError
        self.side: int = side

    def roll(self, count: int = 1) -> tuple[int, list[int]]:
        """Roll dice.

        Args:
            count (int, optional): Number of times to roll the die. Defaults to 1.

        Raises:
            InvalidDiceCountError: Raise when trying to roll the die for an invalid
                number of times.

        Returns:
            tuple[int, list[int]]: Return sum of rolls and the rolls in a list.

        """
        # Raise an error if entered count is invalid.
        if not (1 <= count <= MAX_DICE_COUNT):
            raise DiceCountError

        # Roll the die.
        rolls = [secrets.randbelow(self.side) + 1 for _ in range(count)]

        # Return result.
        return sum(rolls), rolls


def parse_dice_expression(expression: str) -> tuple[int, int] | None:
    """Parse a dice expression.

    e.x: 2d20, d8, 2d, 2d6

    Args:
        expression (str): Expression to parse count and sides.

    Raises:
        DiceExpressionError: Raise when expression is invalid.

    Returns:
        tuple[int, int] | None: Return count and sides. None, if not found.

    """
    expression = expression.strip().lower()

    # Return sided number if expression is a simple digit.
    if expression.isdigit():
        return 1, int(expression)

    # Regex expression.
    match = re.fullmatch(r"(\d*)d([1-9]\d*)", expression)
    # Raise an error if expression is invalid.
    if match is None:
        return None
    count, sides = match.groups()
    count = int(count) if count else 1
    sides = int(sides) if sides else 6
    return count, sides
