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
`bots/turn_search.py`. Referee v2 keeps all five sampled worlds and the legacy
reply-based comparison of final-action candidates, but allocates that expensive work
in stages: a cheap one-action screen narrows the root beam from eight to five while
always retaining Draw; the existing four-action reply beam is preserved. The selected
information-set-safe continuation is retained for the next decision instead of being
replanned. Each retained root receives an equal explicit node budget; pathological
effect chains finish with a deterministic Greedy policy instead of expanding
exponentially.
Immediate HQ captures short-circuit all search.

`staged=False, max_search_nodes=None` preserves the original exhaustive PIMC-lite
algorithm as the comparison control. The legacy algorithm additionally uses reply
rollouts to compare retained last-action candidates and repeats the chosen boundary
reply, which costs roughly (beam_width+1) x determinizations opponent turns per
decision.

Inherited approximations, documented in determinize.py: publicly-returned but
unmarked hand cards (Shuck/Opossum) count as unknown, hidden-hand strength counters
are dropped - both err toward the referee knowing less than a perfect observer.
"""

from __future__ import annotations

import random
from typing import Optional, Sequence

from ..engine import rules
from ..engine.actions import Action, DrawAction, PlaceAction
from ..engine.state import GameState, StateView
from .greedy_bot import GreedyWeights, _battlecry_fizzled
from .turn_search import TurnSearcher


class RefereeBot(TurnSearcher):
    def __init__(self, weights: Optional[GreedyWeights] = None,
                 rng: Optional[random.Random] = None, seed: Optional[int] = None,
                 determinizations: int = 5, beam_width: int = 8,
                 staged: bool = True, root_width: int = 5,
                 reply_width: int = 4,
                 max_search_nodes: Optional[int] = 1_000):
        super().__init__(weights=weights, rng=rng, seed=seed,
                         determinizations=determinizations, beam_width=beam_width)
        self.staged = staged
        self.root_width = root_width
        self.reply_width = reply_width
        self.max_search_nodes = max_search_nodes
        # `self._policy` (the GreedyBot that plays every rollout seat) and `self._search_nodes`
        # are set identically by TurnSearcher.__init__; RefereeBot uses them for reply rollouts
        # and its staged node budget.
        self._screening = False
        self.last_search_stats: dict[str, float | int] = {}
        self._candidate_plans: dict[Action, dict[tuple, Action]] = {}
        self._active_plan: Optional[dict[tuple, Action]] = None
        self._continuation_plan: dict[tuple, Action] = {}

    def choose(
        self,
        view: StateView,
        legal: Sequence[Action],
        state: Optional[GameState] = None,
    ) -> Action:
        legal = list(legal)
        self.last_search_stats = {
            "root_candidates": len(legal),
            "screened_candidates": len(legal),
            "reply_world_rollouts": 0,
            "plan_reused": 0,
            "budget_fallbacks": 0,
        }
        self._search_nodes = 0
        if self.staged:
            captures = [
                action for action in legal
                if isinstance(action, PlaceAction) and action.is_hq_capture
            ]
            if captures:
                self._continuation_plan = {}
                self.last_search_stats["screened_candidates"] = 1
                return captures[0]
        if self.staged and state is not None and self._continuation_plan:
            observation = self._observation_key(state, view.player)
            planned = self._continuation_plan.get(observation)
            if planned in legal:
                del self._continuation_plan[observation]
                self.last_search_stats["screened_candidates"] = 1
                self.last_search_stats["plan_reused"] = 1
                return planned
            # The real observation was not represented by the sampled policy tree.
            self._continuation_plan = {}
        self._candidate_plans = {}
        self._active_plan = None
        return super().choose(view, legal, state)

    def _complete_own_turn(
        self,
        branches: list[tuple[GameState, float]],
        me: str,
        *,
        guard: int,
    ) -> list[tuple[GameState, float]]:
        self._search_nodes += len(branches)
        self.last_search_stats["search_nodes"] = max(
            self.last_search_stats.get("search_nodes", 0),
            self._search_nodes,
        )
        if (
            self.staged
            and self.max_search_nodes is not None
            and self._search_nodes > self.max_search_nodes
        ):
            self.last_search_stats["budget_fallbacks"] += 1
            return self._greedy_complete_turn(branches, me, guard=guard)
        return super()._complete_own_turn(branches, me, guard=guard)

    # ---- hook overrides: RefereeBot adds the sampled opponent reply to the shared planner --

    def _score_final_line(
        self,
        branches: list[tuple[GameState, float]],
        me: str,
    ) -> float:
        return self._mean_reply_score(branches, me)

    def _use_reply_comparison(self, representative: GameState) -> bool:
        return (
            not self._screening
            and representative.pending is None
            and representative.actions_taken_this_turn
            >= representative.config.actions_per_turn - 1
        )

    def _score_candidate_group(
        self,
        candidate_group: list[tuple[GameState, float]],
        me: str,
        compare: bool,
    ) -> float:
        if compare and not self._screening:
            trial = [(state.clone(), penalty) for state, penalty in candidate_group]
            scores = self._reply_scores(trial, me)
            return sum(scores) / len(scores)
        return self._mean_planning_score(candidate_group, me)

    def _select_root_candidates(
        self,
        worlds: list[GameState],
        candidates: list[Action],
        state: GameState,
        me: str,
    ) -> list[Action]:
        self.last_search_stats["root_candidates"] = len(candidates)
        if (
            not self.staged
            or not self.root_width
            or len(candidates) <= self.root_width
        ):
            self.last_search_stats["screened_candidates"] = len(candidates)
            return candidates

        self._screening = True
        try:
            scored = []
            for index, action in enumerate(candidates):
                branches = self._branches_after_action(
                    worlds, action, me, complete_turn=False)
                score = self._mean_planning_score(branches, me)
                scored.append((score, -index, action))
        finally:
            self._screening = False
        scored.sort(reverse=True)
        cutoff = self.root_width
        self.last_search_stats["root_cutoff_gap"] = (
            scored[cutoff - 1][0] - scored[cutoff][0]
            if cutoff < len(scored) else float("inf")
        )
        selected = {
            action for _, _, action in scored[:self.root_width]
        }
        # Draw is strategically distinct and deliberately protected by the generic beam;
        # retain it through the cheap screen even when its immediate score is low.
        selected.update(
            action for action in candidates if isinstance(action, DrawAction)
        )
        narrowed = [action for action in candidates if action in selected]
        self.last_search_stats["screened_candidates"] = len(narrowed)
        return narrowed

    def _record_root_scores(
        self,
        scores: list[tuple[Action, float]],
    ) -> None:
        ranked = sorted((score for _, score in scores), reverse=True)
        self.last_search_stats["decision_gap"] = (
            ranked[0] - ranked[1] if len(ranked) > 1 else float("inf")
        )

    def _begin_root_candidate(self, action: Action) -> None:
        if self.staged:
            # Every root receives the same budget; candidate order must not determine
            # which line gets a full search and which line falls back.
            self._search_nodes = 0
            self._active_plan = {}

    def _end_root_candidate(self, action: Action) -> None:
        if self.staged and self._active_plan is not None:
            self._candidate_plans[action] = self._active_plan
            self._active_plan = None

    def _record_planned_action(self, observation: tuple, action: Action) -> None:
        if self.staged and not self._screening and self._active_plan is not None:
            self._active_plan[observation] = action

    def _record_chosen_root(self, action: Action) -> None:
        if self.staged:
            self._continuation_plan = self._candidate_plans.get(action, {})

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
        limit = self.reply_width if self.staged else 4
        if not limit or len(candidates) <= limit:
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
        self.last_search_stats["reply_min_cutoff_gap"] = min(
            self.last_search_stats.get("reply_min_cutoff_gap", float("inf")),
            (
                scored[limit - 1][0] - scored[limit][0]
                if limit < len(scored) else float("inf")
            ),
        )
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
            if len(selected) >= limit:
                break
            selected.add(action)
        return [a for a in candidates if a in selected]

    def _reply_scores(
        self,
        branches: list[tuple[GameState, float]],
        me: str,
    ) -> list[float]:
        scores = []
        for state, penalty in branches:
            self._advance(state, me)
            scores.append(self._clamped_eval(state, me) - penalty)
            self.last_search_stats["reply_world_rollouts"] += 1
        return scores

    def _mean_reply_score(
        self,
        branches: list[tuple[GameState, float]],
        me: str,
    ) -> float:
        scores = self._reply_scores(branches, me)
        return sum(scores) / len(scores)

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
