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
from collections import defaultdict
from typing import Optional, Sequence

from ..engine import rules
from ..engine.actions import Action, DrawAction, PlaceAction
from ..engine.state import GameState, StateView, other_player
from .base import Bot
from .determinize import determinize
from .greedy_bot import (
    GreedyBot,
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
            mean = self._mean_reply_score(branches, me)
            if mean > best_score:
                best_score, best = mean, [action]
            elif mean == best_score:
                best.append(action)
        # `legal` is already deterministically ordered; RNG only splits exact ties.
        return best[0] if len(best) == 1 else self.rng.choice(best)

    def _beam(self, world: GameState, legal: list[Action], me: str) -> list[Action]:
        """Prune to the `beam_width` most promising candidates by 1-ply eval on a
        sampled world (never the real state).

        Besides the numerical top N, preserve tactically distinct candidates that a
        one-ply score commonly underprices: Draw, HQ capture, an enemy cover, a connected
        placement, and a placement whose Battlecry is live.
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
        for card_actions in by_card.values():
            connected = [
                a for a in card_actions
                if world.is_connected(me, a.crossroad)
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
        end-of-own-turn evaluation; the surviving complete line then receives the expensive
        opponent-reply rollout in `choose`.
        """
        if not branches:
            return []
        if guard >= 40:
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
                advanced = []
                for state, penalty in group:
                    legal = rules.legal_actions(state)
                    action = self._policy.choose(state.view_for(actor), legal, state)
                    rules.apply_action(state, action)
                    advanced.append((state, penalty))
                chosen_group = self._complete_own_turn(advanced, me, guard=guard + 1)
            else:
                legal = self._safe_actions(
                    representative, rules.legal_actions(representative), me)
                candidates = self._beam(representative, legal, me)
                compare_after_reply = (
                    representative.pending is None
                    and representative.actions_taken_this_turn
                    >= representative.config.actions_per_turn - 1
                )
                if compare_after_reply:
                    candidates = self._reply_candidates(
                        representative, candidates, me)
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
                    if compare_after_reply:
                        trial = [(state.clone(), penalty)
                                 for state, penalty in candidate_group]
                        score = self._mean_reply_score(trial, me)
                    else:
                        score = sum(
                            self._planning_eval(state, me) - penalty
                            for state, penalty in candidate_group
                        ) / len(candidate_group)
                    if score > best_score:
                        best_score = score
                        chosen_group = candidate_group
            completed.extend(chosen_group)
        return completed

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
            freeze(state.turn_flags),
            freeze(state.result.to_dict()) if state.result else None,
        )

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

    def _planning_eval(self, state: GameState, me: str) -> float:
        """End-of-own-turn beam score, including effects prepared for the next turn.

        The normal evaluator correctly reports zero readiness while the opponent is to act.
        For pruning our own complete turn lines, briefly project the same public position to
        our next top-level decision so setup value survives long enough to face the real
        sampled opponent reply. The final candidate score is still taken only post-reply.
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
