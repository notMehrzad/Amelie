from __future__ import annotations

__all__ = ["RPSGame", "RPSOption"]

from enum import Enum
from typing import final


@final
class RPSOption(Enum):
    """Represents different rock paper scissors options."""

    ROCK = ("rock", "🪨")
    PAPER = ("paper", "📃")
    SCISSORS = ("scissors", "✂️")

    @property
    def name(self) -> str:
        """Return the name of the option."""
        return self.value[0]

    @property
    def emoji(self) -> str:
        """Return the emoji of the option."""
        return self.value[1]

    @property
    def beats(self) -> RPSOption:
        """Return the option that this option beats."""
        return {
            RPSOption.ROCK: RPSOption.SCISSORS,
            RPSOption.PAPER: RPSOption.ROCK,
            RPSOption.SCISSORS: RPSOption.PAPER,
        }[self]


@final
class RPSGame:
    """Represents a rock paper scissors game."""

    def __init__(self, player1_id: int, player2_id: int) -> None:
        """Initialize a rps game.

        Args:
            player1_id (int): ID of player 1.
            player2_id (int): ID of player 2.

        """
        self.player1_id: int = player1_id
        self.player2_id: int = player2_id

        self.player1_choice: RPSOption | None = None
        self.player2_choice: RPSOption | None = None

    def player1_plays(self, choice: RPSOption) -> None:
        """Play player 1's turn.

        Args:
            choice (RPSOption): Chosen option.

        """
        self.player1_choice = choice

    def player2_plays(self, choice: RPSOption) -> None:
        """Play player 2's turn.

        Args:
            choice (RPSOption): Chosen option.

        """
        self.player2_choice = choice

    def calculate_winner(self) -> int | None:
        """Calculate the winner of a rock paper scissors game.

        Returns:
            int | None: Return ID of the winner. None, if it's draw.

        """
        # Raise an error if at least one player hasn't made their choice.
        if self.player1_choice is None or self.player2_choice is None:
            msg = "Both RPS players must choose first to calculate the winner."
            raise RuntimeError(msg)

        # Return None if it's draw.
        if self.player1_choice == self.player2_choice:
            return None

        # Return ID of the winner.
        if self.player1_choice.beats == self.player2_choice:
            return self.player1_id
        return self.player2_id
