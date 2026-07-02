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
from ..engine.actions import Action, DrawAction, PlaceAction
from ..engine.effects import legal_placements
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
    card_economy: float = 3.0        # per net card *in hand* (mine - theirs). Deliberately not
                                      # hand+deck: drawing must visibly help (hand+deck is
                                      # invariant under a draw), and deck size alone isn't a
                                      # real resource with the current card pool - hand size is
                                      # the actual flexibility/tempo/denial resource.
    effect_readiness: float = 16.0   # per distinct Battlecry in hand that can currently
                                      # produce an observable effect on at least one legal play
    wasted_battlecry: float = 8.0    # penalty for playing a card whose ability text fired for
                                      # nothing (e.g. a removal battlecry with no target) - a
                                      # bot policy adjustment, not part of evaluate() (see
                                      # `_battlecry_fizzled`)


class GreedyBot(Bot):
    def __init__(self, weights: Optional[GreedyWeights] = None,
                 rng: Optional[random.Random] = None, seed: Optional[int] = None,
                 depth: int = 1, beam_width: int = 8):
        self.weights = weights or GreedyWeights()
        # RNG only breaks exact eval ties, so policy stays reproducible.
        self.rng = rng if rng is not None else random.Random(seed)
        self.depth = depth
        self.beam_width = beam_width

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
            return evaluate(state, me, self.weights)

        state = self._advance_to_my_turn(state, me)
        if state.result is not None:
            return evaluate(state, me, self.weights)

        candidates = rules.legal_actions(state)
        if not candidates:
            return evaluate(state, me, self.weights)

        scored: list[tuple[float, GameState]] = []
        for action in candidates:
            nxt = state.clone()
            rules.apply_action(nxt, action)
            scored.append((evaluate(nxt, me, self.weights), nxt))
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
    see `test_eval_ignores_opponent_hand_contents`), never hidden card identities. Under the
    classic one-action rules the opponent must already hold a card. Under the two-action
    variant, an empty-handed opponent can draw and then capture if their deck is non-empty.
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
    # Computed once and reused for the HQ-threat term below (same BFS, was run twice).
    my_connection = state.connected_occupied(me)
    score += w.connection * len(my_connection)

    # --- Region progress: nonlinear and symmetric ---
    # A lone central unit can touch four regions but is nowhere close to producing any of
    # them. Cubing the completion fraction keeps that speculative footprint small while
    # still making a 3/4 or completed region strategically meaningful.
    region = 0.0
    for r in gm.regions.values():
        n = len(r.corners)
        mine = sum(1 for c in r.corners if state.owner_of(c) == me) / n
        theirs = sum(1 for c in r.corners if state.owner_of(c) == opp) / n
        region += r.food * (mine ** 3 - theirs ** 3)
    score += w.region_control * region

    # --- HQ threat: only a connected chain can capture next turn. An isolated Flight unit
    # in front of an HQ is board presence, not an immediate HQ threat.
    opp_connection = state.connected_occupied(opp)
    score += w.enemy_hq_threat * sum(1 for cr in gm.hq_front(opp) if cr in my_connection)
    score -= w.own_hq_threat * sum(1 for cr in gm.hq_front(me) if cr in opp_connection)

    # --- Card economy: net cards in hand (not deck - see GreedyWeights.card_economy) ---
    score += w.card_economy * (len(state.hands[me]) - len(state.hands[opp]))

    # --- Immediately enabled effects in hand ---
    # This is deliberately card-agnostic: the engine itself tells us whether a printed
    # Battlecry would do anything. It values setup states (duplicates, tag thresholds,
    # adjacent targets, eligible follow-up cards) without naming a deck or card.
    score += w.effect_readiness * _enabled_battlecry_count(state, me)

    return score


# ------------------------------------------------------------- wasted-battlecry detection

def _battlecry_fizzled(pre: GameState, post: GameState, me: str, action: Action) -> bool:
    """True if `action` played a card with ability text but nothing beyond the unit landing
    on the board actually happened - e.g. a removal battlecry with no adjacent target.

    A `choose()`-level bot-policy adjustment, not part of `evaluate()`: it needs the
    before/after pair plus the action taken, which `evaluate()`'s pure-state contract
    deliberately doesn't carry (see its tests). Generic over card text - it only checks
    whether anything *observable* moved besides "one fewer card in my hand, one more unit on
    the board", never the specific card id, so it doesn't special-case any one card.
    """
    if not isinstance(action, PlaceAction) or action.is_hq_capture:
        return False
    if not pre.cards[action.card_id].has_battlecry:
        return False  # passives, keywords, Deathrattles, and vanilla units are not Battlecries
    if post.pending is not None:
        return False  # battlecry offered a real choice (e.g. which adjacent enemy to
                       # remove) - it hasn't fizzled, its outcome just isn't resolved yet
    if post.food != pre.food:
        return False
    if len(post.remove_pile) != len(pre.remove_pile):
        return False
    opp = other_player(me)
    if len(post.hands[me]) != len(pre.hands[me]) - 1:
        return False  # drew/removed extra cards -> something happened
    if len(post.hands[opp]) != len(pre.hands[opp]):
        return False  # e.g. bounced an enemy unit back to hand
    if _unit_count(post) != _unit_count(pre) + 1:
        return False  # e.g. "play another unit"
    if _total_strength_counters(post) != _total_strength_counters(pre):
        return False  # e.g. a buff granted, even with no removal/draw/food attached
    if len(post.scheduled) != len(pre.scheduled):
        return False  # delayed Battlecry payoff (Grizzly Bear, Black Bear, Scrooge)
    return True


def _enabled_battlecry_count(state: GameState, player: str) -> int:
    """Count distinct Battlecries in hand that have at least one live legal placement.

    Only outcome *shape* is observed (draw count, pending choice, removal, and so on);
    drawn card identities never enter the score. Call only at a top-level decision for
    `player`; pending effect choices are already concrete and need no readiness estimate.
    """
    if (state.result is not None or state.pending is not None
            or state.player_to_act() != player
            or state.actions_taken_this_turn != 0):
        return 0
    battlecries = {
        u.card_id for u in state.hands[player]
        if state.cards[u.card_id].has_battlecry
    }
    if not battlecries:
        return 0
    # Only battlecry cards can enable a battlecry, so enumerate placements for just those
    # cards (allowed_cards) instead of every hand card. At a top-level decision (guarded
    # above) rules.legal_actions == [Draw?] + legal_placements(state, player), so filtering
    # its battlecry PlaceActions is byte-identical to this restricted enumeration.
    placements = [
        a for a in legal_placements(state, player, allowed_cards=battlecries)
        if not a.is_hq_capture
    ]
    # Most Battlecry conditions are board-wide; target-sensitive ones care primarily about
    # landing on/adjacent to an enemy. Sample those tactical shapes plus one ordinary legal
    # landing instead of cloning every Flight destination on the map.
    by_card: dict[str, list[PlaceAction]] = {}
    for action in placements:
        by_card.setdefault(action.card_id, []).append(action)
    representatives: list[PlaceAction] = []
    opponent = other_player(player)
    occ = state.connected_occupied(player)   # one BFS for all the is_connected checks below
    for actions in by_card.values():
        tactical = [
            a for a in actions
            if state.owner_of(a.crossroad) == opponent
            or any(state.owner_of(nb) == opponent
                   for nb in state.game_map.neighbors(a.crossroad))
        ]
        empty = [a for a in actions if state.top_unit(a.crossroad) is None]
        connected = [a for a in actions if state.is_connected(player, a.crossroad, occ)]
        chosen = []
        for group in (tactical, empty, connected, actions):
            if group and group[0] not in chosen:
                chosen.append(group[0])
        representatives.extend(chosen)

    enabled: set[str] = set()
    for action in representatives:
        if action.card_id in enabled:
            continue
        nxt = state.clone()
        rules.apply_action(nxt, action)
        if not _battlecry_fizzled(state, nxt, player, action):
            enabled.add(action.card_id)
    return len(enabled)


def _unit_count(state: GameState) -> int:
    return sum(len(stack) for stack in state.board.values())


def _total_strength_counters(state: GameState) -> int:
    board = sum(u.strength_counter for stack in state.board.values() for u in stack)
    hands = sum(u.strength_counter for hand in state.hands.values() for u in hand)
    return board + hands
