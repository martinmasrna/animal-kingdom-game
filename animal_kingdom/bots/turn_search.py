"""Shared determinized own-turn search - the honesty machinery behind TurnBot and RefereeBot.

Both bots plan a *complete own turn* the same way: sample a handful of determinized worlds
(bots/determinize.py) so unknown draws are modelled without reading the true hidden state,
then beam-search every own placement/draw/sub-choice to the point where control passes to
the opponent. The two differ only in what they do at the turn boundary:

  - TurnBot stops there and scores the finished own-turn position (the shared evaluator plus
    the projected end-of-turn readiness adjustment). It never simulates the opponent's reply,
    which is what keeps it cheap enough for large balance sims.
  - RefereeBot (bots/referee_bot.py) plays the opponent's whole reply out of the sampled hand
    and scores *that* - roughly (beam+1) x determinizations opponent rollouts per decision.

`TurnSearcher` owns everything shared: determinization, the information-set grouping that
keeps the search honest (worlds indistinguishable to `me` must pick the same action, and may
diverge only after an observable event such as drawing a different card), beam pruning with
the reserved tactical candidates, the hard next-turn-HQ-loss filter, wasted-battlecry penalty
accumulation, and the projected-readiness planning eval. The three behaviours that differ are
isolated as override hooks (`_score_final_line`, `_use_reply_comparison`/`_reply_candidates`,
`_resolve_opponent_subchoice`, `_score_candidate_group`); the base implementations are exactly
TurnBot's, so RefereeBot is expressed purely as overrides of them.

Hidden-information honesty holds by construction: nothing is ever searched on the true state -
only on determinized worlds - and every decision is taken once per indistinguishable group of
worlds. See `test_turn_bot.py` / `test_referee_bot.py` for the no-cheat assertions.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from typing import Optional, Sequence

from ..engine import rules
from ..engine.actions import Action, DrawAction, PlaceAction
from ..engine.state import GameState, StateView, other_player
from .base import Bot
from .determinize import determinize
from .greedy_bot import (
    GreedyWeights,
    _battlecry_fizzled,
    _enabled_battlecry_count,
    _opponent_lethal_next_turn,
    evaluate,
)

# Terminal evals are +/-inf; averaging a won world with a lost one must yield a large
# finite number (fraction-of-worlds-won), not NaN.
_DECISIVE = 1e9

# det_rng must not shadow the tie-break RNG stream; offset the seed by a fixed salt.
_DET_SEED_SALT = 0x9E3779B9

# Recursion guard: no legal own turn expands anywhere near this many decision points, so
# hitting it means a pathological state - bail out with the branches searched so far.
_MAX_DEPTH = 40


class TurnSearcher(Bot):
    """Determinized complete-own-turn planner. Base behaviour is TurnBot's; RefereeBot
    subclasses and overrides the reply/opponent-policy hooks."""

    def __init__(self, weights: Optional[GreedyWeights] = None,
                 rng: Optional[random.Random] = None, seed: Optional[int] = None,
                 determinizations: int = 3, beam_width: int = 8):
        self.weights = weights or GreedyWeights()
        # RNG only breaks exact score ties, so policy stays reproducible.
        self.rng = rng if rng is not None else random.Random(seed)
        self.det_rng = random.Random(None if seed is None else seed + _DET_SEED_SALT)
        self.determinizations = determinizations
        self.beam_width = beam_width

    def choose(
        self,
        view: StateView,
        legal: Sequence[Action],
        state: Optional[GameState] = None,
    ) -> Action:
        legal = list(legal)
        if state is None or len(legal) == 1:
            return legal[0]
        # view.player, not state.current: we may be answering a pending sub-choice, including
        # one the opponent's action opened on their turn.
        me = view.player

        worlds = [determinize(state, me, self.det_rng)
                  for _ in range(self.determinizations)]
        legal = self._safe_actions(worlds[0], legal, me)
        candidates = self._beam(worlds[0], legal, me)

        best_score = -math.inf
        best: list[Action] = []
        for action in candidates:
            branches = []
            for world in worlds:
                nxt = world.clone()
                rules.apply_action(nxt, action)
                penalty = (self.weights.wasted_battlecry
                           if _battlecry_fizzled(world, nxt, me, action) else 0.0)
                branches.append((nxt, penalty))
            if state.current == me:
                branches = self._complete_own_turn(branches, me, guard=0)
            score = self._score_final_line(branches, me)
            if score > best_score:
                best_score, best = score, [action]
            elif score == best_score:
                best.append(action)
        # `legal` is already deterministically ordered; RNG only splits exact ties.
        return best[0] if len(best) == 1 else self.rng.choice(best)

    # ------------------------------------------------------------- own-turn completion

    def _complete_own_turn(
        self,
        branches: list[tuple[GameState, float]],
        me: str,
        *,
        guard: int,
    ) -> list[tuple[GameState, float]]:
        """Beam-plan the remainder of `me`'s turn as an information-set tree.

        Worlds with identical observations share one chosen action. Worlds may split only
        after something the player can observe (notably a draw), preventing sampled hidden
        hands/deck orders from leaking into the decision. Continuations are pruned by their
        end-of-own-turn evaluation (`_score_candidate_group`); the surviving complete line is
        then scored by `_score_final_line` in `choose`.
        """
        if not branches:
            return []
        if guard >= _MAX_DEPTH:
            return branches

        completed: list[tuple[GameState, float]] = []
        ongoing: list[tuple[GameState, float]] = []
        for state, penalty in branches:
            result = rules.is_terminal(state)
            if result is not None:
                state.result = result
                completed.append((state, penalty))
            elif state.current != me:
                completed.append((state, penalty))
            else:
                ongoing.append((state, penalty))

        if not ongoing:
            return completed

        groups: dict[tuple, list[tuple[GameState, float]]] = defaultdict(list)
        for item in ongoing:
            groups[self._observation_key(item[0], me)].append(item)

        for group in groups.values():
            representative = group[0][0]
            actor = representative.player_to_act()
            if actor != me:
                chosen_group = self._resolve_opponent_subchoice(group, me, actor, guard)
            else:
                legal = self._safe_actions(
                    representative, rules.legal_actions(representative), me)
                candidates = self._beam(representative, legal, me)
                compare = self._use_reply_comparison(representative)
                if compare:
                    candidates = self._reply_candidates(representative, candidates, me)
                best_score = -math.inf
                chosen_group = []
                for action in candidates:
                    next_group = []
                    for state, penalty in group:
                        nxt = state.clone()
                        rules.apply_action(nxt, action)
                        extra = (self.weights.wasted_battlecry
                                 if _battlecry_fizzled(state, nxt, me, action) else 0.0)
                        next_group.append((nxt, penalty + extra))
                    candidate_group = self._complete_own_turn(
                        next_group, me, guard=guard + 1)
                    score = self._score_candidate_group(candidate_group, me, compare)
                    if score > best_score:
                        best_score = score
                        chosen_group = candidate_group
            completed.extend(chosen_group)
        return completed

    # --------------------------------------------------------------- overridable hooks

    def _score_final_line(
        self,
        branches: list[tuple[GameState, float]],
        me: str,
    ) -> float:
        """Score a completed own-turn line. TurnBot: mean end-of-turn planning eval.

        RefereeBot overrides this to advance the sampled opponent reply first.
        """
        return self._mean_planning_score(branches, me)

    def _use_reply_comparison(self, representative: GameState) -> bool:
        """Whether the last top-level action before the opponent replies should be compared
        by a real reply rollout. TurnBot never does this; RefereeBot does."""
        return False

    def _reply_candidates(
        self,
        state: GameState,
        candidates: list[Action],
        me: str,
    ) -> list[Action]:
        """Narrow the last-action candidate set before a reply rollout. No-op for TurnBot
        (it never enables reply comparison); RefereeBot overrides with a diverse small beam."""
        return candidates

    def _score_candidate_group(
        self,
        candidate_group: list[tuple[GameState, float]],
        me: str,
        compare: bool,
    ) -> float:
        """Prune-time score of one candidate continuation. TurnBot always uses the planning
        eval; RefereeBot swaps in the reply rollout when `compare` is set."""
        return self._mean_planning_score(candidate_group, me)

    def _resolve_opponent_subchoice(
        self,
        group: list[tuple[GameState, float]],
        me: str,
        actor: str,
        guard: int,
    ) -> list[tuple[GameState, float]]:
        """Resolve an opponent-owned sub-choice opened during `me`'s turn.

        TurnBot models it adversarially: over the information set, pick the single public
        continuation with the *lowest* mean score for `me`. RefereeBot overrides this to let
        its Greedy policy play the choice per world (its opponent model is greedy, not
        worst-case). The adversarial pick reads only the representative's legal actions
        (public within the info set), never a true hidden hand.
        """
        representative = group[0][0]
        legal = rules.legal_actions(representative)
        if not legal:
            return self._complete_own_turn(list(group), me, guard=guard + 1)
        worst_score = math.inf
        chosen_group: list[tuple[GameState, float]] = []
        for action in legal:
            next_group = []
            for state, penalty in group:
                nxt = state.clone()
                rules.apply_action(nxt, action)
                next_group.append((nxt, penalty))
            candidate_group = self._complete_own_turn(next_group, me, guard=guard + 1)
            score = self._mean_planning_score(candidate_group, me)
            if score < worst_score:
                worst_score = score
                chosen_group = candidate_group
        return chosen_group

    # ---------------------------------------------------------------- shared scoring

    def _mean_planning_score(
        self,
        branches: list[tuple[GameState, float]],
        me: str,
    ) -> float:
        return sum(
            self._planning_eval(state, me) - penalty for state, penalty in branches
        ) / len(branches)

    def _clamped_eval(self, state: GameState, me: str) -> float:
        score = evaluate(state, me, self.weights)
        return max(-_DECISIVE, min(_DECISIVE, score))

    def _planning_eval(self, state: GameState, me: str) -> float:
        """End-of-own-turn beam score, including effects prepared for the next turn.

        The normal evaluator correctly reports zero readiness while the opponent is to act.
        For pruning our own complete turn lines, briefly project the same public position to
        our next top-level decision so setup value survives to the turn boundary.
        """
        score = self._clamped_eval(state, me)
        if state.result is not None or state.current == me:
            return score
        projected = state.clone()
        projected.current = me
        projected.pending = None
        projected.effect_stack = []
        projected.actions_taken_this_turn = 0
        readiness = _enabled_battlecry_count(projected, me)
        return max(
            -_DECISIVE,
            min(_DECISIVE, score + self.weights.effect_readiness * readiness),
        )

    # ------------------------------------------------------------------ pruning

    def _beam(self, world: GameState, legal: list[Action], me: str) -> list[Action]:
        """Prune to the `beam_width` most promising candidates by 1-ply eval on a sampled
        world (never the real state).

        Besides the numerical top N, preserve tactically distinct candidates that a one-ply
        score commonly underprices: Draw, HQ capture, an enemy cover, a connected placement,
        and a placement whose Battlecry is live.
        """
        if not self.beam_width or len(legal) <= self.beam_width:
            return legal
        scored = []
        for i, action in enumerate(legal):
            nxt = world.clone()
            rules.apply_action(nxt, action)
            scored.append((self._clamped_eval(nxt, me), -i, action))
        scored.sort(reverse=True)   # -i: stable toward `legal`'s deterministic order
        score_of = {action: score for score, _, action in scored}
        reserved: set[Action] = {
            a for a in legal
            if isinstance(a, DrawAction)
            or (isinstance(a, PlaceAction) and a.is_hq_capture)
        }

        by_card: dict[str, list[PlaceAction]] = defaultdict(list)
        for action in legal:
            if isinstance(action, PlaceAction) and not action.is_hq_capture:
                by_card[action.card_id].append(action)
        opponent = other_player(me)
        occ = world.connected_occupied(me)   # one BFS shared by every is_connected below
        for card_actions in by_card.values():
            connected = [
                a for a in card_actions
                if world.is_connected(me, a.crossroad, occ)
            ]
            home_front = [
                a for a in card_actions
                if a.crossroad in world.game_map.hq_front(me)
            ]
            covers = [
                a for a in card_actions
                if world.top_unit(a.crossroad) is not None
                and world.top_unit(a.crossroad).owner == opponent
            ]
            live = []
            if world.cards[card_actions[0].card_id].has_battlecry:
                for a in card_actions:
                    nxt = world.clone()
                    rules.apply_action(nxt, a)
                    if not _battlecry_fizzled(world, nxt, me, a):
                        live.append(a)
            for group in (connected, home_front, covers, live):
                if group:
                    reserved.add(max(group, key=lambda a: score_of[a]))

        kept = set(reserved)
        for _, _, action in scored:
            if len(kept) >= self.beam_width and action not in reserved:
                continue
            kept.add(action)
            if len(kept) >= max(self.beam_width, len(reserved)):
                break
        return [a for a in legal if a in kept]

    def _safe_actions(self, world: GameState, legal: Sequence[Action], me: str) -> list[Action]:
        """Hard-filter actions that leave an avoidable next-turn HQ capture."""
        safe = []
        opponent = other_player(me)
        for action in legal:
            nxt = world.clone()
            rules.apply_action(nxt, action)
            if nxt.result is not None or not _opponent_lethal_next_turn(nxt, opponent):
                safe.append(action)
        return safe or list(legal)

    # -------------------------------------------------------------- observation key

    @staticmethod
    def _observation_key(state: GameState, me: str) -> tuple:
        """Canonical public/own-visible state; deliberately excludes hidden card identities."""
        opp = other_player(me)

        def freeze(value):
            if isinstance(value, dict):
                return tuple(sorted((k, freeze(v)) for k, v in value.items()))
            if isinstance(value, (list, tuple)):
                return tuple(freeze(v) for v in value)
            if isinstance(value, (set, frozenset)):
                return tuple(sorted(freeze(v) for v in value))
            return value

        board = tuple(
            (cr, tuple(
                (u.card_id, u.owner, u.strength_counter, u.placed_on_turn,
                 u.locked_until_turn)
                for u in stack
            ))
            for cr, stack in sorted(state.board.items())
        )
        own_hand = tuple(
            (u.card_id, u.strength_counter, u.locked_until_turn)
            for u in state.hands[me]
        )
        return (
            state.current,
            state.player_to_act(),
            state.turn_counter,
            state.actions_taken_this_turn,
            state.units_placed_this_turn,
            board,
            own_hand,
            len(state.hands[opp]),
            len(state.decks[me]),
            len(state.decks[opp]),
            tuple(state.remove_pile),
            tuple(sorted(state.food.items())),
            freeze(state.pending),
            freeze(state.effect_stack),
            freeze(state.scheduled),
            freeze(state.card_strength_counters),
            freeze(state.turn_flags),
            freeze(state.result.to_dict()) if state.result else None,
        )
