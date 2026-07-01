"""GreedyBot: a board-evaluation heuristic with 1-ply lookahead (handoff §10.1).

The bot clones the live game, applies each legal action through the engine, scores the
resulting position with `evaluate`, and plays the highest-scoring action. Because it
searches by really applying actions, it needs the full `GameState` (the read-only view
cannot clone/resolve) - this is the documented in-process escape hatch on `Bot.choose`.

The eval weights live here (bot policy), separate from `config.py` (game-balance dials).
`evaluate` reads only what the acting seat could legitimately know - the public board,
its own food, the public Remove Pile, and the static map geometry - never the opponent's
hand contents. It does use real unit instances (so strength counters / anthems / dynamic
strength count), which is public board information.

Caveat (handoff §10): a 1-ply greedy bot underplays Combo / multi-turn sequencing. Balance
conclusions drawn from greedy self-play are bot-limited; the sim harness records this.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Optional, Sequence

from ..engine import rules
from ..engine.actions import Action
from ..engine.state import GameState, StateView, other_player
from ..engine.strength import effective_strength
from .base import Bot


@dataclass(frozen=True)
class GreedyWeights:
    """Tunable eval weights. Placeholder defaults (untuned, like config.py's dials);
    eval-weight optimization is downstream work."""

    food_progress: float = 1.0       # per net food (mine - theirs)
    food_proximity: float = 30.0     # x (my_food / win_food): pull toward the food win
    board_presence: float = 0.5      # per net effective-strength on controlled crossroads
    connection: float = 1.0          # per own unit connected to my HQ
    region_control: float = 2.0      # per controlled region corner, x that region's food
    enemy_hq_threat: float = 40.0    # per crossroad I hold in front of the enemy HQ
    own_hq_threat: float = 40.0      # per crossroad the enemy holds in front of my HQ
    card_economy: float = 0.5        # per net card (hand + deck)


class GreedyBot(Bot):
    def __init__(self, weights: Optional[GreedyWeights] = None,
                 rng: Optional[random.Random] = None, seed: Optional[int] = None):
        self.weights = weights or GreedyWeights()
        # RNG only breaks exact eval ties, so policy stays reproducible.
        self.rng = rng if rng is not None else random.Random(seed)

    def choose(
        self,
        view: StateView,
        legal: Sequence[Action],
        state: Optional[GameState] = None,
    ) -> Action:
        legal = list(legal)
        me = view.player
        if state is None:
            # No search context (shouldn't happen via cli/sim, which always pass state).
            # TODO(greedy): a view-only fallback eval if a remote driver ever needs one.
            return legal[0]

        best_score = -math.inf
        best: list[Action] = []
        for action in legal:
            nxt = state.clone()
            rules.apply_action(nxt, action)
            score = evaluate(nxt, me, self.weights)
            if score > best_score:
                best_score, best = score, [action]
            elif score == best_score:
                best.append(action)
        # `legal` is already in deterministic (sorted) order; the RNG only splits exact ties.
        return best[0] if len(best) == 1 else self.rng.choice(best)


def evaluate(state: GameState, me: str, weights: GreedyWeights) -> float:
    """Heuristic value of `state` from `me`'s perspective (higher is better)."""
    opp = other_player(me)

    if state.result is not None:                       # terminal: decisive
        if state.result.winner == me:
            return math.inf
        if state.result.winner == opp:
            return -math.inf
        return 0.0                                     # draw

    gm = state.game_map
    w = weights
    score = 0.0

    # --- Food: net total + proximity to the food win ---
    score += w.food_progress * (state.food[me] - state.food[opp])
    score += w.food_proximity * (state.food[me] / gm.win_food)

    # --- Board presence: net effective strength of controlled crossroads ---
    presence = 0.0
    for stack in state.board.values():
        if not stack:
            continue
        top = stack[-1]
        s = effective_strength(state, top)
        presence += s if top.owner == me else -s
    score += w.board_presence * presence

    # --- Connection: own units linked to my HQ (placement reach + resilience) ---
    score += w.connection * len(state.connected_occupied(me))

    # --- Region control: corners I hold, weighted by that region's food output ---
    region = 0.0
    for r in gm.regions.values():
        held = sum(1 for c in r.corners if state.owner_of(c) == me)
        region += held * r.food
    score += w.region_control * region

    # --- HQ threat: who stands in front of whose HQ (one step from capture) ---
    score += w.enemy_hq_threat * sum(1 for cr in gm.hq_front(opp) if state.owner_of(cr) == me)
    score -= w.own_hq_threat * sum(1 for cr in gm.hq_front(me) if state.owner_of(cr) == opp)

    # --- Card economy: net cards in hand + deck ---
    my_cards = len(state.hands[me]) + len(state.decks[me])
    opp_cards = len(state.hands[opp]) + len(state.decks[opp])
    score += w.card_economy * (my_cards - opp_cards)

    return score
