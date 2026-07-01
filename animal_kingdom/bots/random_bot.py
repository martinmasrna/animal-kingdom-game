"""RandomBot: picks a uniformly random legal action. Also the engine's fuzzer.

Carries its **own** seeded RNG, separate from the game's setup/chance RNG, so bot policy
and game randomness stay independent and individually reproducible.
"""

from __future__ import annotations

import random
from typing import Optional, Sequence

from ..engine.actions import Action
from ..engine.state import GameState, StateView
from .base import Bot


class RandomBot(Bot):
    def __init__(self, rng: Optional[random.Random] = None, seed: Optional[int] = None):
        self.rng = rng if rng is not None else random.Random(seed)

    def choose(
        self,
        view: StateView,
        legal: Sequence[Action],
        state: Optional[GameState] = None,
    ) -> Action:
        return self.rng.choice(list(legal))  # state ignored: RandomBot needs no lookahead
