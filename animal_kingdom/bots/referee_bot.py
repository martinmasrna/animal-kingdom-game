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

The own-turn planning - determinization, information-set grouping, beam pruning, the
HQ-safety filter, fizzle-penalty accumulation - is shared with TurnBot in
`bots/turn_search.py`; RefereeBot is that `TurnSearcher` plus the opponent-reply
rollout. It differs from TurnBot in exactly three places, all expressed here as hook
overrides: it scores a finished line *after* the sampled reply (`_score_final_line`),
it compares the last pre-reply action by that reply too (`_use_reply_comparison` /
`_reply_candidates`), and it resolves opponent-owned sub-choices with its Greedy policy
rather than adversarially (`_resolve_opponent_subchoice`).

Cost: roughly (beam_width+1) x determinizations opponent-turn rollouts per decision,
~100-200x GreedyBot. Intended for low-volume calibration runs (50-150 games per
matchup), not the high-throughput balance sims - TurnBot is the scalable middle tier.

Inherited approximations, documented in determinize.py: publicly-returned but
unmarked hand cards (Shuck/Opossum) count as unknown, hidden-hand strength counters
are dropped - both err toward the referee knowing less than a perfect observer.
"""

from __future__ import annotations

import random
from typing import Optional

from ..engine import rules
from ..engine.actions import Action, DrawAction, PlaceAction
from ..engine.state import GameState
from .greedy_bot import GreedyBot, GreedyWeights, _battlecry_fizzled
from .turn_search import TurnSearcher


class RefereeBot(TurnSearcher):
    def __init__(self, weights: Optional[GreedyWeights] = None,
                 rng: Optional[random.Random] = None, seed: Optional[int] = None,
                 determinizations: int = 5, beam_width: int = 8):
        super().__init__(weights=weights, rng=rng, seed=seed,
                         determinizations=determinizations, beam_width=beam_width)
        # One policy bot plays every rollout seat: the opponent's reply turn out of its
        # sampled hand, their pending sub-choices, and my own sub-choices opened mid-rollout.
        # Being the real GreedyBot, it brings the lethal-avoidance and fizzle logic along, so
        # the simulated opponent is exactly the sim's greedy.
        self._policy = GreedyBot(weights=self.weights,
                                 seed=None if seed is None else seed + 1)

    # ---- hook overrides: RefereeBot adds the sampled opponent reply to the shared planner --

    def _score_final_line(
        self,
        branches: list[tuple[GameState, float]],
        me: str,
    ) -> float:
        return self._mean_reply_score(branches, me)

    def _use_reply_comparison(self, representative: GameState) -> bool:
        return (
            representative.pending is None
            and representative.actions_taken_this_turn
            >= representative.config.actions_per_turn - 1
        )

    def _score_candidate_group(
        self,
        candidate_group: list[tuple[GameState, float]],
        me: str,
        compare: bool,
    ) -> float:
        if compare:
            trial = [(state.clone(), penalty) for state, penalty in candidate_group]
            return self._mean_reply_score(trial, me)
        return self._mean_planning_score(candidate_group, me)

    def _resolve_opponent_subchoice(
        self,
        group: list[tuple[GameState, float]],
        me: str,
        actor: str,
        guard: int,
    ) -> list[tuple[GameState, float]]:
        advanced = []
        for state, penalty in group:
            legal = rules.legal_actions(state)
            action = self._policy.choose(state.view_for(actor), legal, state)
            rules.apply_action(state, action)
            advanced.append((state, penalty))
        return self._complete_own_turn(advanced, me, guard=guard + 1)

    # -------------------------------------------------------------- reply-rollout scoring

    def _reply_candidates(
        self,
        state: GameState,
        candidates: list[Action],
        me: str,
    ) -> list[Action]:
        """Small diverse beam for the last top-level action before an opponent reply."""
        if len(candidates) <= 4:
            return candidates
        scored = []
        live = []
        for index, action in enumerate(candidates):
            nxt = state.clone()
            rules.apply_action(nxt, action)
            score = self._planning_eval(nxt, me)
            scored.append((score, -index, action))
            if (isinstance(action, PlaceAction)
                    and state.cards[action.card_id].has_battlecry
                    and not _battlecry_fizzled(state, nxt, me, action)):
                live.append((score, -index, action))
        scored.sort(reverse=True)
        selected = {scored[0][2]}
        selected.update(a for a in candidates if isinstance(a, DrawAction))
        selected.update(
            a for a in candidates
            if isinstance(a, PlaceAction) and a.is_hq_capture
        )
        home = [
            row for row in scored
            if isinstance(row[2], PlaceAction)
            and not row[2].is_hq_capture
            and row[2].crossroad in state.game_map.hq_front(me)
        ]
        if home:
            selected.add(home[0][2])
        if live:
            selected.add(max(live)[2])
        for _, _, action in scored:
            if len(selected) >= 4:
                break
            selected.add(action)
        return [a for a in candidates if a in selected]

    def _mean_reply_score(
        self,
        branches: list[tuple[GameState, float]],
        me: str,
    ) -> float:
        total = 0.0
        for state, penalty in branches:
            self._advance(state, me)
            total += self._clamped_eval(state, me) - penalty
        return total / len(branches)

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
