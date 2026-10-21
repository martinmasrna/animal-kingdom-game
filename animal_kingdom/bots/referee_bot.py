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

import time

import random
from typing import Optional, Sequence

from ..engine import rules
from .base import keep_hand
from ..engine.actions import Action, DrawAction, PlaceAction, RoamAction
from ..engine.state import GameState, StateView
from ..engine.strength import card_strength
from ..engine.state import UnitInstance
from .features import opponent_unseen_card_ids
from collections import Counter
from math import comb
from .greedy_bot import GreedyWeights, _roar_fizzled
from .learned_eval import LinearEval
from .turn_search import _DECISIVE, TurnSearcher

# Bound on the lost-world tiebreak: far below the 2e8 that one more lost world (of five)
# costs, so it only orders moves that lose in the same worlds.
_LOSS_TIEBREAK = 1e6


class RefereeBot(TurnSearcher):
    def __init__(self, weights: Optional[GreedyWeights] = None,
                 rng: Optional[random.Random] = None, seed: Optional[int] = None,
                 determinizations: int = 5, beam_width: int = 8,
                 staged: bool = True, root_width: int = 5,
                 reply_width: int = 4,
                 max_search_nodes: Optional[int] = 1_000,
                 evaluator: Optional[LinearEval] = None,
                 quiesce: bool = False, mulligan: bool = False,
                 depth: int = 0, next_width: int = 3, deepen_top: int = 4, deepen_roots: int = 3, time_budget: float = 0.0,
                 den_sense: bool = False, reply_turns: int = 0):
        super().__init__(weights=weights, rng=rng, seed=seed,
                         determinizations=determinizations, beam_width=beam_width,
                         evaluator=evaluator, quiesce=quiesce, mulligan=mulligan)
        self.staged = staged
        self.root_width = root_width
        self.reply_width = reply_width
        self.max_search_nodes = max_search_nodes
        # Sight past the reply (2026-10-17): at the leaf, after the opponent's sampled reply, play `depth` more rounds
        # of my own turn (the `next_width` best first actions by one-move score, each finished by the fast policy) and
        # their reply (the fast policy), and score after; the best of my lines counts. Depth 0 scores at the reply, as
        # before: the one-turn horizon that never saw the Zebra draw three next turn.
        self.depth = depth
        self.next_width = next_width
        self.deepen_top = deepen_top        # only this many of a root's best lines (by the one-turn score) get the extra sight
        self.deepen_roots = deepen_roots    # only this many root candidates (the one-turn search's best) get it at all
        self.time_budget = time_budget      # seconds per move after which no further root is deepened (0: no limit)
        self._move_started = 0.0
        # Den sense (2026-10-17, from Martin's three dens lost in a row that evening, each with a one-card guard on the
        # table): the fast policy that plays the reply picks one action at a time, so a capture behind a setup action
        # (cover my weak den guard, then walk in) was only seen when the setup happened to be its best single move. Now
        # every reply leaf carries the exact chance of that capture, computed over the opponent's public unseen pool
        # (which of their cards would open my den from where they stand, and the odds their hand holds one), and the
        # leaf scores as a loss by that chance. Five sampled hands made every guard look equally lost; the exact odds
        # tell a guard of 7 from a guard of 3 and the threatened square from the other two. The root screen also keeps
        # the strongest guard for each den approach (the one-move score ranked a Meerkat above the Groundhog on the
        # square that decided a game, so the only defence was never searched).
        self.den_sense = den_sense
        # The reply as a turn (2026-10-17, Martin: "a turn is an atomic event consisting of 2 actions"): at the start of
        # the opponent's sampled reply, their first action is chosen by the position after their whole turn (the
        # `reply_turns` best openings by one-move score, each finished by the fast policy) instead of by the one-move
        # score alone, so a setup-then-payoff reply is seen. With a second turn of sight it runs only in the second stage
        # (the best roots' final scoring), where the decision is made: everywhere, it cost 2.7x the move. 0: the fast
        # policy picks both actions, as before.
        self.reply_turns = reply_turns
        self._deepening = False             # on only while _rescore_roots scores a root's final lines
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
        self._move_started = time.monotonic()
        self.last_search_stats = {
            "root_candidates": len(legal),
            "screened_candidates": len(legal),
            "reply_world_rollouts": 0,
            "plan_reused": 0,
            "budget_fallbacks": 0,
        }
        if (keep := self._keep_hand(view, legal, state)) is not None:
            return keep
        self._search_nodes = 0
        if self.staged:
            captures = [
                action for action in legal
                if isinstance(action, (PlaceAction, RoamAction)) and action.is_hq_capture
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
                score = self._mean_planning_score(
                    [(self._settled(state, me), penalty) for state, penalty in branches], me)
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
        if self.den_sense:
            for cr in state.game_map.hq_front(me):
                guards = [a for a in candidates
                          if isinstance(a, PlaceAction) and not a.is_hq_capture and a.crossroad == cr]
                if guards:
                    selected.add(max(guards, key=lambda a: card_strength(state, a.card_id, me)))
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
            rules.apply_action(state, action, validate=False)
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
            rules.apply_action(nxt, action, validate=False)
            score = self._planning_eval(self._settled(nxt, me), me)
            scored.append((score, -index, action))
            if (isinstance(action, PlaceAction)
                    and state.cards[action.card_id].has_roar
                    and not _roar_fizzled(state, nxt, me, action)):
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
            if isinstance(a, (PlaceAction, RoamAction)) and a.is_hq_capture
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
        scores, leaves = [], []
        for state, penalty in branches:
            # A lost world is a flat -_DECISIVE, so when every world is lost all moves tie
            # and the bot plays a random one. Keep the position it handed the opponent as a
            # tiebreak: still a decisive loss, but the most resistant one ranks first.
            before = max(-_LOSS_TIEBREAK, min(_LOSS_TIEBREAK, self._planning_eval(state, me)))
            threat = self._advance(state, me)
            score = self._clamped_eval(state, me)
            if score == -_DECISIVE:
                score += before
            if threat:
                score = threat * (-_DECISIVE + before) + (1.0 - threat) * score
            scores.append(score - penalty)
            leaves.append((state, penalty, before))
            self.last_search_stats["reply_world_rollouts"] += 1
        if self.depth and self._deepening and leaves:
            # The extra sight goes to the lines the one-turn score likes best (ties and near-ties are where it decides),
            # while the move's time budget lasts.
            order = sorted(range(len(scores)), key=lambda i: -scores[i])[:self.deepen_top]
            for i in order:
                if self.time_budget and time.monotonic() - self._move_started > self.time_budget:
                    self.last_search_stats["lookahead_cut"] = self.last_search_stats.get("lookahead_cut", 0) + 1
                    break
                state, penalty, before = leaves[i]
                if state.result is not None:
                    continue
                score = self._leaf_score(state, me, self.depth)
                if score == -_DECISIVE:
                    score += before
                scores[i] = score - penalty
        return scores

    def _mean_reply_score(
        self,
        branches: list[tuple[GameState, float]],
        me: str,
    ) -> float:
        scores = self._reply_scores(branches, me)
        return sum(scores) / len(scores)

    def _rescore_roots(self, worlds, root_scores, state, me):
        """Two stages (2026-10-17): the one-turn search ranks every root candidate; the best `deepen_roots` of them are
        then scored again with `depth` more rounds of sight on their best lines, and the move is chosen among those.
        Out of time (`time_budget`), the one-turn ranking stands."""
        if not self.depth or len(root_scores) < 2:
            return root_scores
        top = sorted(root_scores, key=lambda row: -row[1])[:self.deepen_roots]
        deep = []
        for action, _shallow in top:
            if self.time_budget and time.monotonic() - self._move_started > self.time_budget:
                self.last_search_stats["lookahead_cut"] = 1
                return root_scores
            self._begin_root_candidate(action)
            branches = self._branches_after_action(worlds, action, me, complete_turn=(state.current == me))
            self._deepening = True
            try:
                score = self._mean_reply_score(branches, me)
            finally:
                self._deepening = False
            self._end_root_candidate(action)
            deep.append((action, score))
        self.last_search_stats["deepened_roots"] = len(deep)
        return deep

    def _leaf_score(self, state: GameState, me: str, depth: int) -> float:
        """The score at a leaf: the board as it stands (depth 0), or the best of my next turns played out with their
        replies (depth 1: one more round of sight, and so on). `state` is at my next top-level decision or terminal."""
        if depth <= 0 or state.result is not None or state.pending is not None or state.player_to_act() != me:
            return self._clamped_eval(state, me)
        legal = rules.legal_actions(state)
        if not legal:
            return self._clamped_eval(state, me)
        best = None
        for action in self._greedy_topn(state, legal, me, self.next_width):
            nxt = state.clone()
            rules.apply_action(nxt, action, validate=False)
            self._play_turn(nxt, me)        # the rest of my turn, by the fast policy
            threat = self._advance(nxt, me) # their reply, to my next decision or a terminal state
            self.last_search_stats["lookahead_lines"] = self.last_search_stats.get("lookahead_lines", 0) + 1
            value = self._leaf_score(nxt, me, depth - 1)
            if threat:
                value = threat * -_DECISIVE + (1.0 - threat) * value
            best = value if best is None else max(best, value)
        if best is not None and abs(best) >= _DECISIVE / 2:
            best /= 2        # a game decided a turn later counts half: lose later rather than now, win now rather than later
        return best  # type: ignore[return-value]

    def _play_turn(self, state: GameState, me: str) -> None:
        """Play the rest of my turn with the fast policy (sub-choices included), until the turn passes to the opponent
        or the game ends. Mutates `state`; sets `state.result` at terminals."""
        guard = 0
        while guard < 40:
            guard += 1
            result = rules.is_terminal(state)
            if result is not None:
                state.result = result
                return
            if state.player_to_act() != me:
                return
            legal = rules.legal_actions(state)
            if not legal:
                return
            action = self._policy.choose(state.view_for(me), legal, state)
            rules.apply_action(state, action, validate=False)

    def _advance(self, state: GameState, me: str) -> float:
        """Play the rollout clone forward with the greedy policy - through my pending
        sub-choices, the opponent's whole reply turn (their sampled hand), and any
        pendings that opens - until my next top-level decision or a terminal state.
        Mutates `state`; sets `state.result` at terminals so `evaluate` sees them. Returns the chance (den sense) that
        the opponent's reply captured my den instead; 0.0 without den sense or threat."""
        guard = 0
        threat = 0.0
        while guard < 40:
            guard += 1
            result = rules.is_terminal(state)   # also catches max_turns,
            if result is not None:              # which is_terminal returns without
                state.result = result           # writing to state.result itself
                return threat
            if state.player_to_act() == me and state.pending is None:
                return threat
            actor = state.player_to_act()
            legal = rules.legal_actions(state)
            if self.den_sense and actor != me and state.pending is None and state.actions_taken_this_turn == 0 \
                    and threat == 0.0:
                threat = self._den_threat(state, actor, me)
            if self.reply_turns and (self._deepening or not self.depth) and actor != me and state.pending is None \
                    and state.actions_taken_this_turn == 0:
                opening = self._reply_opening(state, actor, legal)
                if opening is not None:
                    rules.apply_action(state, opening, validate=False)   # the rest of their turn is the policy's
                    continue
            action = self._policy.choose(state.view_for(actor), legal, state)
            rules.apply_action(state, action, validate=False)
        return threat

    def _den_threat(self, state: GameState, opp: str, me: str) -> float:
        """The chance the opponent, to act with their whole turn, can capture my den: 1.0 when they already stand
        connected in front of it with a card to spend, else the odds their hand holds a card that steps onto a front
        crossroad beside their chain and leaves the capture open (exact over the public unseen pool and their hand
        size; the engine decides which cards can step where)."""
        gm = state.game_map
        front = gm.hq_front(me)
        occ = state.connected_occupied(opp)
        hand, deck = len(state.hands[opp]), state.decks[opp]
        if any(cr in occ for cr in front) and (hand or (deck and state.config.actions_per_turn >= 2)):
            return 1.0
        if hand < 2 or state.config.actions_per_turn < 2:
            return 0.0
        reach = [cr for cr in front if any(nb in occ for nb in gm.neighbors(cr))]
        if not reach:
            return 0.0
        unseen = Counter(opponent_unseen_card_ids(state, opp))
        total = sum(unseen.values())
        if total < hand:
            return 0.0
        filler = next((cid for cid in unseen if "Apex Predator" not in state.cards[cid].keywords), None)
        enabling = 0
        for cid, count in unseen.items():
            probe = state.clone()
            probe.hands[opp] = [UnitInstance(cid, opp, 900001), UnitInstance(filler or cid, opp, 900002)]
            for a in rules.legal_actions(probe):
                if isinstance(a, PlaceAction) and a.target[0] == "cr" and a.target[1] in reach:
                    nxt = probe.clone()
                    rules.apply_action(nxt, a, validate=False)
                    if nxt.pending is None and nxt.player_to_act() == opp and rules.is_terminal(nxt) is None and any(
                            isinstance(b, (PlaceAction, RoamAction)) and b.is_hq_capture for b in rules.legal_actions(nxt)):
                        enabling += count
                        break
        if not enabling:
            return 0.0
        return 1.0 - comb(total - enabling, hand) / comb(total, hand)

    def _reply_opening(self, state: GameState, opp: str, legal: Sequence[Action]) -> Optional[Action]:
        """The opponent's first action, judged by the position after their whole turn: each of their `reply_turns` best
        openings by one-move score is finished by the fast policy and the finished turn scored for them."""
        if len(legal) < 2:
            return None
        best, best_score = None, None
        for opening in self._greedy_topn(state, list(legal), opp, self.reply_turns):
            nxt = state.clone()
            rules.apply_action(nxt, opening, validate=False)
            self._play_turn(nxt, opp)
            score = self._clamped_eval(nxt, opp)
            if best_score is None or score > best_score:
                best, best_score = opening, score
        return best
