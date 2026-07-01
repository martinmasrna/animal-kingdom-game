"""The single bot interface. A bot (and, later, a human UI) picks from legal_actions.

Bots receive the per-seat `StateView` (hidden info stripped) plus the list of legal actions
for the seat to act. This same contract drives both M1's RandomBot and M3's GreedyBot.

`state` is an **optional, in-process-only** escape hatch for search bots (GreedyBot's 1-ply
lookahead needs to clone and apply candidate actions through the engine, which a read-only
view cannot do). It is the full `GameState`, so it is passed only by trusted in-process
drivers (cli/sim) — never across a network. The `StateView` remains the contract for the
future web/UI boundary; bots that don't search simply ignore `state`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, Sequence

from ..engine.actions import Action
from ..engine.state import StateView

if TYPE_CHECKING:
    from ..engine.state import GameState


class Bot(ABC):
    @abstractmethod
    def choose(
        self,
        view: StateView,
        legal: Sequence[Action],
        state: "Optional[GameState]" = None,
    ) -> Action:
        """Return one action from `legal`, given the seat's view of the game.

        `state` (the full position) is supplied only by in-process drivers for search bots;
        view-only bots ignore it.
        """
