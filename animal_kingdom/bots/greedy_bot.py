"""GreedyBot: a board-evaluation heuristic with configurable own-line lookahead
(handoff §10.1).

At `depth=1` (the default) the bot clones the live game, applies each legal action through
the engine, scores the resulting position with `evaluate`, and plays the highest-scoring
action - unchanged from the original 1-ply bot. Because it searches by really applying
actions, it needs the full `GameState` (the read-only view cannot clone/resolve) - this is
the documented in-process escape hatch on `Bot.choose`.

The eval weights live here (bot policy), separate from `config.py` (game-balance dials).
`evaluate` reads only what the acting seat could legitimately know - the public board,
its own food, the public Remove Pile, and the static map geometry - never the opponent's
hand contents. It does use real unit instances (so strength counters / anthems / dynamic
strength count), which is public board information.

Caveat (handoff §10): a 1-ply greedy bot underplays Combo / multi-turn sequencing. Balance
conclusions drawn from greedy self-play are bot-limited; the sim harness records this.

`depth > 1` ("own-line" lookahead - see sim/gauntlet.py) searches `depth` of *my own*
placements in a row instead of stopping at 1 ply. This is deliberately not adversarial
minimax: simulating the opponent's actual best reply would mean playing cards out of their
real (hidden) hand to predict their move, which the project's evaluate() explicitly refuses
to read even though the full GameState is technically available (see
`test_eval_ignores_opponent_hand_contents`). Instead, between my own placements the
opponent's turn is fast-forwarded with a neutral filler action - Draw if legal, else
whatever placement sorts first - never chosen by reading their hand strategically.

Gauntlet-tested result (2024): this genuinely fixes the *specific* blind spot described
above - it finds delayed effects (Grizzly Bear) and multi-turn setups that 1-ply misses -
but it's a *net loss* overall (-23 to -32% win rate vs. plain 1-ply, worse at higher depth).
The passive filler opponent makes every simulated line look artificially safe, so the search
systematically favours patient setups a live, actively-playing opponent punishes
immediately. Left in as an opt-in `depth`/`beam_width` knob (never the default) - a
validated negative result, not a recommended configuration. Fixing it for real would mean
letting the opponent's simulated replies use their actual hand (true minimax), which was
deliberately ruled out for now since this bot could plausibly face a real human later.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Optional, Sequence

from ..engine import rules
from ..engine.actions import Action, DrawAction
from ..engine.state import GameState, StateView, other_player
from .base import Bot
from . import features as _features
from .learned_eval import LinearEval
# Re-exported for backward compatibility: turn_search.py/referee_bot.py import these names
# from greedy_bot (their bodies now live in features.py - the shared rung-0/rung-1 module -
# see features.py's module docstring for why).
from .features import (  # noqa: F401
    _battlecry_fizzled,
    enabled_battlecry_count as _enabled_battlecry_count,
)


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
    card_economy: float = 3.0        # per net card *in hand* (mine - theirs). Deliberately not
                                      # hand+deck: drawing must visibly help (hand+deck is
                                      # invariant under a draw), and deck size alone isn't a
                                      # real resource with the current card pool - hand size is
                                      # the actual flexibility/tempo/denial resource.
    effect_readiness: float = 16.0   # per distinct Battlecry in hand that can currently
                                      # produce an observable effect on at least one legal play
    pending_payoff: float = 20.0     # per delayed effect I own on state.scheduled (Egg hatch,
                                      # Bear, ...), imminence-discounted. board_presence can't
                                      # see these - the placed card is weak *now* and only pays
                                      # off when it fires later, the "weak now, strong later"
                                      # the 1-ply eval is otherwise blind to. Card-agnostic
                                      # (reads scheduled, names no card). Validated 2026-07-04:
                                      # paired benchmark egg +5.3 / ramp +10.4, all decks
                                      # improve-or-tie (see docs/bots + human_scorer value-rank).
    coverage_exposure: float = 0.0   # belief term (default OFF): expected own-HQ danger one
                                      # ply ahead, = P(opponent's hidden hand can cover a
                                      # currently-safe HQ-front defender next turn). Exact
                                      # hypergeometric over the public unseen multiset, no
                                      # determinization; honest (see `_p_opponent_can_cover`).
    wasted_battlecry: float = 8.0    # penalty for playing a card whose ability text fired for
                                      # nothing (e.g. a removal battlecry with no target) - a
                                      # bot policy adjustment, not part of evaluate() (see
                                      # `_battlecry_fizzled`)


class GreedyBot(Bot):
    def __init__(self, weights: Optional[GreedyWeights] = None,
                 rng: Optional[random.Random] = None, seed: Optional[int] = None,
                 depth: int = 1, beam_width: int = 8,
                 evaluator: Optional[LinearEval] = None):
        self.weights = weights or GreedyWeights()
        # RNG only breaks exact eval ties, so policy stays reproducible.
        self.rng = rng if rng is not None else random.Random(seed)
        self.depth = depth
        self.beam_width = beam_width
        # Learned-pilot seam (default None => the hand path below is byte-identical to
        # before this existed). See `_eval`.
        self.evaluator = evaluator

    def _eval(self, state: GameState, me: str) -> float:
        """Routes to the learned evaluator if one was supplied, else the hand-written
        `evaluate()`. The one chokepoint every scoring call in this bot goes through."""
        if self.evaluator is not None:
            return self.evaluator.value(state, me)
        return evaluate(state, me, self.weights)

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

        opp = other_player(me)
        best_score = -math.inf
        best: list[Action] = []
        fallback_score = -math.inf
        fallback: list[Action] = []
        for action in legal:
            nxt = state.clone()
            rules.apply_action(nxt, action)
            score = self._rollout_value(nxt, me, self.depth - 1)
            if _battlecry_fizzled(state, nxt, me, action):
                score -= self.weights.wasted_battlecry
            # Every candidate is a fallback in case *all* of them hang mate (see below).
            if score > fallback_score:
                fallback_score, fallback = score, [action]
            elif score == fallback_score:
                fallback.append(action)
            # `own_hq_threat`/`enemy_hq_threat` are ordinary point terms an aggressive play
            # can outbid even when the "threat" is actually a guaranteed capture next turn.
            # Mirror the already-decisive self-win (evaluate() returns +inf for it) with a
            # decisive self-loss check: never walk into a position where the opponent's turn
            # opens with a legal HQ capture, if a legal action avoids it.
            # Check at every decision point, not only on the action that hands over the
            # turn. Effects can open a target choice while another top-level action remains;
            # choosing the wrong target there may make the eventual HQ loss unavoidable.
            if nxt.result is None and _opponent_lethal_next_turn(nxt, opp):
                continue
            if score > best_score:
                best_score, best = score, [action]
            elif score == best_score:
                best.append(action)
        # `legal` is already in deterministic (sorted) order; the RNG only splits exact ties.
        if best:
            return best[0] if len(best) == 1 else self.rng.choice(best)
        return fallback[0] if len(fallback) == 1 else self.rng.choice(fallback)

    def _rollout_value(self, state: GameState, me: str, remaining_depth: int) -> float:
        """The value of `state` (right after one of my placements) `remaining_depth` more of
        my own placements deep. `remaining_depth <= 0` is exactly the original 1-ply score."""
        if remaining_depth <= 0 or state.result is not None:
            return self._eval(state, me)

        state = self._advance_to_my_turn(state, me)
        if state.result is not None:
            return self._eval(state, me)

        candidates = rules.legal_actions(state)
        if not candidates:
            return self._eval(state, me)

        scored: list[tuple[float, GameState]] = []
        for action in candidates:
            nxt = state.clone()
            rules.apply_action(nxt, action)
            scored.append((self._eval(nxt, me), nxt))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        beam = scored[: self.beam_width] if self.beam_width else scored

        return max(self._rollout_value(nxt, me, remaining_depth - 1) for _, nxt in beam)

    @staticmethod
    def _advance_to_my_turn(state: GameState, me: str) -> GameState:
        """Fast-forward the opponent's turn(s) with a neutral filler action (whichever
        placement/choice sorts first, else Draw) until it's my turn again or the game ends.
        Never chosen by reading the opponent's hand strategically - see the module docstring.

        Placement is preferred over Draw so the simulated opponent actually develops a board
        instead of stalling for free (an earlier Draw-first filler made every rollout look
        artificially safe - see the module docstring's gauntlet-tested history).
        """
        guard = 0
        while state.result is None and state.player_to_act() != me and guard < 20:
            guard += 1
            legal = rules.legal_actions(state)
            if not legal:
                break
            filler = next((a for a in legal if not isinstance(a, DrawAction)), legal[0])
            rules.apply_action(state, filler)
        return state


def _opponent_lethal_next_turn(state: GameState, opponent: str) -> bool:
    """True if `opponent` can capture an HQ on their upcoming turn.

    Only consults board connectivity (public) and hand *size* (also legitimately public -
    see `test_eval_ignores_opponent_hand_contents`), never hidden card identities. With two
    actions per turn an empty-handed opponent can draw and *then* capture if their deck is
    non-empty; the hand check covers the case where they already hold a card.
    """
    me = other_player(opponent)
    gm = state.game_map
    reaches_my_hq = any(cr in state.connected_occupied(opponent) for cr in gm.hq_front(me))
    if not reaches_my_hq:
        return False
    if state.hands[opponent]:
        return True
    can_draw_then_place = (
        state.config.actions_per_turn >= 2
        and state.config.draw_action_count > 0
        and bool(state.decks[opponent])
        and len(state.hands[opponent]) < state.config.hand_limit
    )
    return can_draw_then_place


def evaluate(state: GameState, me: str, weights: GreedyWeights) -> float:
    """Heuristic value of `state` from `me`'s perspective (higher is better).

    Term bodies live in `bots/features.py` (rung 0 is exactly these 11 terms - see its module
    docstring); this function just applies `weights` to them, preserving the original
    skip-when-zero-weight short-circuits (`coverage_exposure`, `pending_payoff`) so perf is
    unchanged.
    """
    opp = other_player(me)

    if state.result is not None:                       # terminal: decisive
        if state.result.winner == me:
            return math.inf
        if state.result.winner == opp:
            return -math.inf
        return 0.0                                     # draw

    w = weights
    score = 0.0

    # --- Food: net total + proximity to the food win ---
    food_progress, food_proximity = _features.food_terms(state, me, opp)
    score += w.food_progress * food_progress
    score += w.food_proximity * food_proximity

    # --- Board presence: net effective strength of controlled crossroads ---
    score += w.board_presence * _features.board_presence(state, me, opp)

    # --- Connection: own units linked to my HQ (placement reach + resilience) ---
    # Computed once and reused for the HQ-threat term below (same BFS, was run twice).
    my_connection = state.connected_occupied(me)
    score += w.connection * len(my_connection)

    # --- Region progress: nonlinear and symmetric ---
    # A lone central unit can touch four regions but is nowhere close to producing any of
    # them. Cubing the completion fraction keeps that speculative footprint small while
    # still making a 3/4 or completed region strategically meaningful.
    score += w.region_control * _features.region_control(state, me, opp)

    # --- HQ threat: only a connected chain can capture next turn. An isolated Flight unit
    # in front of an HQ is board presence, not an immediate HQ threat.
    opp_connection = state.connected_occupied(opp)
    enemy_threat, own_threat = _features.hq_threat_terms(state, me, opp, my_connection, opp_connection)
    score += w.enemy_hq_threat * enemy_threat
    score -= w.own_hq_threat * own_threat

    # --- Coverage exposure: expected own-HQ danger one ply ahead, from the *belief* over the
    # opponent's hidden hand. GreedyBot is 1-ply and only sees threats already on the board;
    # this adds the probability that a currently-safe HQ-front defender of mine gets covered
    # next turn (opponent lands strength > mine on it, opening the capture lane). The belief is
    # exact - open decklists make the unseen multiset public, so P(cover) is a closed-form
    # hypergeometric, not a determinization. Scoped to *defended* HQ-front crossroads to
    # isolate the belief signal (empty walk-ins are a deterministic threat the lethal-check /
    # own_hq_threat already handle). Off at weight 0.
    if w.coverage_exposure:
        score -= w.coverage_exposure * _features.coverage_exposure_worst(state, me, opp, opp_connection)

    # --- Card economy: net cards in hand (not deck - see GreedyWeights.card_economy) ---
    score += w.card_economy * _features.card_economy(state, me, opp)

    # --- Immediately enabled effects in hand ---
    # This is deliberately card-agnostic: the engine itself tells us whether a printed
    # Battlecry would do anything. It values setup states (duplicates, tag thresholds,
    # adjacent targets, eligible follow-up cards) without naming a deck or card.
    score += w.effect_readiness * _features.enabled_battlecry_count(state, me)

    # --- Pending delayed payoffs: net scheduled future effects, imminence-discounted ---
    # A just-placed Egg/Bear contributes ~nothing to board_presence (it's weak now) yet is a
    # real investment that pays off when it fires. Reading state.scheduled credits that future
    # value generically - any delayed effect counts, no card is named. Sooner-firing effects
    # are worth more (less time for the board to change under them). `remaining` counts the
    # OWNER's remaining turns; equals the pre-2026-07-15 `due - turn_counter` exactly - this
    # term's 20.0 was tuned to that.
    if w.pending_payoff:
        score += w.pending_payoff * _features.pending_payoff(state, me, opp)

    return score
