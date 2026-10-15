"""The bots' mulligan: send back the weakest card while the deck's average replacement is better.

A card's worth here is its opening-hand impact (`data/learned/opening_hand.json`, built by `sim.opening_hand`): how many
points its deck's win rate moves when the card is in the opening hand, measured over logged games whose hands were dealt
at random. The mulligan returns one card at a time (overview.md §4.4) and the replacement is the top deck card that is no
copy of anything returned, so each step compares the hand's lowest-impact card with the average impact of the deck cards
that could replace it. Honest: it reads the deck's contents, which its owner knows, never their order. A card without
data counts as 0. Generic: the table is learned from games, not written per card.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Sequence

from ..engine.actions import SKIP, Action, ChoiceAction
from ..engine.state import GameState

TABLE = Path(__file__).resolve().parent.parent / "data" / "learned" / "opening_hand.json"
MULLIGAN_MARGIN = 1.0    # points of win rate the average replacement must beat the card by


@lru_cache(maxsize=1)
def impacts() -> dict[str, float]:
    try:
        return json.loads(TABLE.read_text())["impact"]
    except FileNotFoundError:
        return {}


def mulligan_choice(state: GameState, me: str, legal: Sequence[Action]) -> Action:
    """Keep (SKIP) or the hand card to send back, at one step of `me`'s mulligan."""
    keep = next(a for a in legal if isinstance(a, ChoiceAction) and a.choice == SKIP)
    table = impacts()
    step = next((st for st in reversed(state.effect_stack) if st["op"] == "mulligan" and st["player"] == me), None)
    returned = set(step["returned"]) if step else set()
    options = [u for u in state.hands[me] if ChoiceAction(u.iid) in legal]
    if not options:
        return keep
    worst = min(options, key=lambda u: table.get(u.card_id, 0.0))
    pool = [table.get(c, 0.0) for c in state.decks[me] if c not in returned and c != worst.card_id]
    if pool and sum(pool) / len(pool) > table.get(worst.card_id, 0.0) + MULLIGAN_MARGIN:
        return ChoiceAction(worst.iid)
    return keep
