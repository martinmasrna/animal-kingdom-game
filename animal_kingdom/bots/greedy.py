"""The bot: plays each decision by trying every legal action on a copy of the game and keeping the one whose position it
scores best. It reads only what its seat may know: the board, the food, the Remove Pile, its own hand, and the number of
cards in the opponent's hand. It keeps its opening hand."""

from __future__ import annotations

import random
from typing import Optional, Sequence

from ..engine import rules
from ..engine.actions import SKIP, Action, ChoiceAction, PassAction
from ..engine.state import GameState, StateView, other_player
from ..engine.strength import effective_strength

WIN = 1_000_000.0


def evaluate(state: GameState, me: str) -> float:
    """How good the position is for `me`."""
    opp = other_player(me)
    if state.result is not None:
        return WIN if state.result.winner == me else -WIN if state.result.winner == opp else 0.0
    gm = state.game_map
    score = state.food[me] - state.food[opp]
    score += 2.0 * (rules.region_income(state, me) - rules.region_income(state, opp))
    for cr, stack in state.board.items():
        top = stack[-1]
        sign = 1.0 if top.owner == me else -1.0
        score += sign * (1.0 + 0.3 * effective_strength(state, top))
    # a connected animal on the other side's base can raid next turn
    for p, sign in ((me, 1.0), (opp, -1.0)):
        occ = state.connected_occupied(p)
        score += sign * 4.0 * sum(1 for cr in gm.hq_front(other_player(p)) if cr in occ)
    score += 0.8 * (len(state.hands[me]) - len(state.hands[opp]))
    return score


class GreedyBot:
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)

    def choose(self, view: StateView, legal: Sequence[Action], state: GameState) -> Action:
        legal = list(legal)
        if not legal:
            return PassAction()
        if view.pending is not None and view.pending.get("kind") == "mulligan":
            return ChoiceAction(SKIP)
        me = view.player
        best_score, best = -float("inf"), []
        for action in legal:
            nxt = state.clone()
            rules.apply_action(nxt, action, validate=False)
            score = evaluate(nxt, me)
            if score > best_score:
                best_score, best = score, [action]
            elif score == best_score:
                best.append(action)
        return best[0] if len(best) == 1 else self.rng.choice(best)
