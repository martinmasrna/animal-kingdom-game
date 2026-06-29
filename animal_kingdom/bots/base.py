"""The single bot interface. A bot (and, later, a human UI) picks from legal_actions.

Bots receive only the per-seat `StateView` (never the full state / hidden info) plus the
list of legal actions for the seat to act. This same contract drives both M1's RandomBot
and M3's GreedyBot.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from ..engine.actions import Action
from ..engine.state import StateView


class Bot(ABC):
    @abstractmethod
    def choose(self, view: StateView, legal: Sequence[Action]) -> Action:
        """Return one action from `legal`, given the seat's view of the game."""
