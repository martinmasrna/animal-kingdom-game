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
MULLIGAN_MARGIN = 5.0    # points of win rate the average replacement must beat the card by: per-card noise is ±4-5


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


# ================================================================== the searched mulligan (2026-10-21)
# Martin: the rules of a good mulligan (a Python at 0 goes back, four commons are a weak hand, an Egg or a Bear is worth
# more now than later, two Hornets are one too many, a card that acts from the deck is dead in hand, a Honey Badger
# against a deck with nothing to target) are too many to write and all fall out of one thing: play the kept hand's first
# turns and look. So each step of the mulligan plays every option (keep, or send back one card) through the opening
# against the opponent's open list sampled many ways, with the bot's own fast policy and evaluation, and takes the best.

SEARCH_WORLDS = 24          # sampled worlds: my deck order, their hand and deck; the same worlds score every option
SEARCH_TURNS = 2            # rounds of the opening played out before the evaluation
SEARCH_MARGIN = 0.5         # points a return must beat keeping by (a kept hand also keeps the deck order untouched)
_DECISIVE = 1e9


def search_choice(state: GameState, me: str, legal: Sequence[Action], policy, evaluate, rng,
                  worlds: int = SEARCH_WORLDS, turns: int = SEARCH_TURNS) -> Action:
    """Keep (SKIP) or the hand card to send back at one step of `me`'s mulligan, by play-out: each option is tried in
    `worlds` sampled worlds (`determinize`: my deck's order and the opponent's hidden cards drawn afresh, never the true
    ones), both mulligans then kept, `turns` rounds played by `policy` for both sides, and the result scored by
    `evaluate(state, me)`. Honest: nothing here reads the true deck order or the opponent's hand."""
    from ..engine import rules
    from .determinize import determinize
    keep = next(a for a in legal if isinstance(a, ChoiceAction) and a.choice == SKIP)
    options = [u for u in state.hands[me] if ChoiceAction(u.iid) in legal]
    if not options:
        return keep

    base = [determinize(state, me, rng) for _ in range(worlds)]   # one set of worlds for every option: paired, not noisy

    def score(choice) -> float:
        total = 0.0
        for b in base:
            world = b.clone()
            if choice != SKIP:
                rules.apply_action(world, ChoiceAction(choice), validate=False)   # replaced from the sampled deck order
            guard = 0
            while world.pending is not None and world.effect_stack and world.effect_stack[-1].get("op") == "mulligan" and guard < 12:
                rules.apply_action(world, ChoiceAction(SKIP), validate=False)     # the rest of both mulligans: keep
                guard += 1
            target = world.turn_counter + 2 * turns
            steps = 0
            while world.turn_counter < target and rules.is_terminal(world) is None and steps < 80:
                actor = world.player_to_act()
                lg = rules.legal_actions(world)
                if not lg:
                    break
                rules.apply_action(world, policy.choose(world.view_for(actor), lg, world), validate=False)
                steps += 1
            result = rules.is_terminal(world)
            if result is not None:
                world.result = result
            total += max(-_DECISIVE, min(_DECISIVE, evaluate(world, me)))
        return total / worlds

    kept = score(SKIP)
    best_score, best = kept, None
    for u in options:
        s = score(u.iid)
        if s > best_score:
            best_score, best = s, u.iid
    if best is None or best_score < kept + SEARCH_MARGIN:
        return keep
    return ChoiceAction(best)
