"""RefereeBot: determinized adversarial search ("PIMC-lite") - the calibration bot.

GreedyBot's 1-ply verdicts drive the balance sims, but its known blind spots (never
holds a card to draw, blind to opponent replies, undervalues delayed payoffs) mean
those verdicts need a stronger second opinion. The earlier attempt at one - the
`lookahead` kind's own-line search - was a validated *negative* result (-23 to -32%
win rate): it refused to read the opponent's hidden hand, so it fast-forwarded their
turns with a passive filler, and passive replies make every patient line look safe.

RefereeBot models the opponent's real reply without cheating, via determinization
(see bots/determinize.py): sample K possible worlds in which the opponent's hidden
hand/deck split and both deck orders are re-dealt from public information, then in
each world let a real GreedyBot play the opponent's whole reply turn *out of the
sampled hand* - legitimate, because the hand was sampled, not read. Each candidate
action is scored by the mean post-reply `evaluate` across worlds; nothing is ever
searched on the true state, so the no-cheat property holds by construction (see
`test_referee_ignores_hidden_information`).

Cost: roughly (beam_width+1) x determinizations opponent-turn rollouts per decision,
~100-200x GreedyBot. Intended for low-volume calibration runs (50-150 games per
matchup), not the high-throughput balance sims.

Inherited approximations, documented in determinize.py: publicly-returned but
unmarked hand cards (Shuck/Opossum) count as unknown, hidden-hand strength counters
are dropped - both err toward the referee knowing less than a perfect observer.
"""

from __future__ import annotations

import math
import random
from typing import Optional, Sequence

from ..engine import rules
from ..engine.actions import Action, DrawAction
from ..engine.state import GameState, StateView
from .base import Bot
from .determinize import determinize
from .greedy_bot import GreedyBot, GreedyWeights, _battlecry_fizzled, evaluate

# Terminal evals are +/-inf; averaging a won world with a lost one must yield a large
# finite number (fraction-of-worlds-won), not NaN.
_DECISIVE = 1e9

# det_rng must not shadow the tie-break RNG stream; offset the seed by a fixed salt.
_DET_SEED_SALT = 0x9E3779B9


class RefereeBot(Bot):
    def __init__(self, weights: Optional[GreedyWeights] = None,
                 rng: Optional[random.Random] = None, seed: Optional[int] = None,
                 determinizations: int = 5, beam_width: int = 8):
        self.weights = weights or GreedyWeights()
        # RNG only breaks exact score ties, so policy stays reproducible.
        self.rng = rng if rng is not None else random.Random(seed)
        self.det_rng = random.Random(None if seed is None else seed + _DET_SEED_SALT)
        self.determinizations = determinizations
        self.beam_width = beam_width
        # One policy bot plays every rollout seat: the opponent's reply turn out of
        # its sampled hand, their pending sub-choices, and my own sub-choices opened
        # mid-rollout. Being the real GreedyBot, it brings the lethal-avoidance and
        # fizzle logic along, so the simulated opponent is exactly the sim's greedy.
        self._policy = GreedyBot(weights=self.weights,
                                 seed=None if seed is None else seed + 1)

    def choose(
        self,
        view: StateView,
        legal: Sequence[Action],
        state: Optional[GameState] = None,
    ) -> Action:
        legal = list(legal)
        if state is None or len(legal) == 1:
            return legal[0]
        # view.player, not state.current: the referee may be answering a pending
        # sub-choice, including one the opponent's action opened on their turn.
        me = view.player

        worlds = [determinize(state, me, self.det_rng)
                  for _ in range(self.determinizations)]
        candidates = self._beam(worlds[0], legal, me)

        best_score = -math.inf
        best: list[Action] = []
        for action in candidates:
            total = 0.0
            for world in worlds:
                nxt = world.clone()
                rules.apply_action(nxt, action)
                fizzled = _battlecry_fizzled(world, nxt, me, action)
                self._advance(nxt, me)
                score = self._clamped_eval(nxt, me)
                if fizzled:
                    score -= self.weights.wasted_battlecry
                total += score
            mean = total / len(worlds)
            if mean > best_score:
                best_score, best = mean, [action]
            elif mean == best_score:
                best.append(action)
        # `legal` is already deterministically ordered; RNG only splits exact ties.
        return best[0] if len(best) == 1 else self.rng.choice(best)

    def _beam(self, world: GameState, legal: list[Action], me: str) -> list[Action]:
        """Prune to the `beam_width` most promising candidates by 1-ply eval on a
        sampled world (never the real state). DrawAction always survives the beam:
        holding/drawing is exactly the value a 1-ply eval underprices, and pruning it
        would rebuild GreedyBot's dump-your-hand bias into the referee."""
        if not self.beam_width or len(legal) <= self.beam_width:
            return legal
        scored = []
        for i, action in enumerate(legal):
            nxt = world.clone()
            rules.apply_action(nxt, action)
            scored.append((self._clamped_eval(nxt, me), -i, action))
        scored.sort(reverse=True)   # -i: stable toward `legal`'s deterministic order
        kept = [action for _, _, action in scored[: self.beam_width]]
        draws = [a for a in legal if isinstance(a, DrawAction) and a not in kept]
        return [a for a in legal if a in kept] + draws

    def _advance(self, state: GameState, me: str) -> None:
        """Play the rollout clone forward with the greedy policy - through my pending
        sub-choices, the opponent's whole reply turn (their sampled hand), and any
        pendings that opens - until my next top-level decision or a terminal state.
        Mutates `state`; sets `state.result` at terminals so `evaluate` sees them."""
        guard = 0
        while guard < 40:
            guard += 1
            result = rules.is_terminal(state)   # also catches exhaustion/max_turns,
            if result is not None:              # which is_terminal returns without
                state.result = result           # writing to state.result itself
                return
            if state.player_to_act() == me and state.pending is None:
                return
            actor = state.player_to_act()
            legal = rules.legal_actions(state)
            action = self._policy.choose(state.view_for(actor), legal, state)
            rules.apply_action(state, action)

    def _clamped_eval(self, state: GameState, me: str) -> float:
        score = evaluate(state, me, self.weights)
        return max(-_DECISIVE, min(_DECISIVE, score))
