"""Shared, card-agnostic feature extraction for the learned evaluator (`bots/learned_eval.py`)
and the hand-written `evaluate()` (`bots/greedy_bot.py`).

**Rung 0** (`feature_set="rung0"`) is exactly the 11 terms `GreedyWeights`/`evaluate()` already
score - the bodies below are the *same code*, moved here so both the hand path and the learned
path share one implementation (rung 0 is definitionally identical to the hand eval, not
re-implemented: see the hand-mimic equivalence test in `test_learned_eval.py`). `wasted_roar`
is a `choose()`-level bot-policy adjustment, not a position feature, and is not included here -
see `_roar_fizzled`'s docstring.

**Rung 1** (`feature_set="rung1"`) adds ~13 generic "dynamics" features - growth, scheduled
payoffs, economy, board geometry - so TD learning can price a multi-turn plan (a state where
"my units are growing" or "my payoffs are near") without a hand-written horizon discount. Every
rung-1 feature is a *difference* of the same-shaped quantity computed for both seats (mine minus
theirs), so antisymmetry holds by construction (see `test_features.py`).

Honesty (regression-tested, mirrors `evaluate()`'s existing contract): every feature reads only
what `me` may legitimately know - the public board (including on-board strength counters/anthems,
which are visible board state, not hidden information - see `evaluate()`'s docstring), own hand
contents, own food, the shared Remove Pile, deck *sizes* (never contents/order - not even
`me`'s own deck order), and static card metadata limited to `base_strength`, `is_dynamic`,
`keywords`, `food_cost`, `has_roar` - never a card id or deck slug. Rung 2 adds two generic
reads: whether two cards share a tag (never which tag), and whether a card's text holds an
ability beyond keywords and a food cost (`has_ability`, never what it does). The one belief
term (`coverage_exposure`) reads the opponent's hand+deck as one combined unseen multiset (never
distinguishing which unseen card sits where - see `opponent_unseen_card_ids`), exactly as
`evaluate()`'s existing `_p_opponent_can_cover` already did.
"""

from __future__ import annotations

import hashlib
import json
import bisect
import math
from collections import deque
from typing import Iterator, Optional

from ..engine import rules
from ..engine.actions import PlaceAction
from ..engine.state import GameState, other_player
from ..engine.strength import effective_strength, aura_sources

# --------------------------------------------------------------------- schema constants
# Fixed, part of schema_hash() - changing any of these invalidates every artifact trained
# against the old schema (loud failure on load, not silent drift - see learned_eval.py).

# Mean game length in turns on the shipped ruleset (map_b, 2 actions/turn), measured by the
# Session-1 step-0 throughput benchmark (~13.0-13.3 turns across two independent samples).
# Used only to build `phase` (turn/T_NORM, clamped to 1) for the rung-1 interaction features.
T_NORM = 13.0

DECK_NORM = 30.0          # a premade decklist's card count (deck_diff normalization)
TOTAL_CARDS_NORM = 60.0   # both 30-card decks combined (dynamic_fuel's remove-pile fraction)
HQ_DIST_CAP = 12          # BFS distance sentinel when a target set is unreachable

RUNG0_FEATURES: tuple[str, ...] = (
    "food_progress",
    "food_proximity",
    "board_presence",
    "connection",
    "region_control",
    "enemy_hq_threat",
    "own_hq_threat",
    "coverage_exposure",
    "card_economy",
    "effect_readiness",
    "pending_payoff",
)

RUNG1_EXTRA_FEATURES: tuple[str, ...] = (
    "growth_board_diff",
    "growth_rate_diff",
    "dynamic_board_diff",
    "dynamic_fuel",
    "phase_x_growth",
    "sched_near_diff",
    "sched_far_diff",
    "income_diff",
    "income_x_future",
    "deck_diff",
    "phase_x_food",
    "hq_dist_diff",
    "flight_hand_expected_diff",
)

# Rung 2: context for a nonlinear evaluator - what is in hand and on the board, so a net can
# learn when a card is worth more played now than later (a hand of Roars that would fizzle vs.
# engines that pay for every later unit). Per-side counts rather than differences, since the
# net can combine them. Tags are read only as "shares a tag with", never by name.
RUNG2_EXTRA_FEATURES: tuple[str, ...] = (
    "to_move",
    "phase",
    "hand_mine",
    "hand_theirs",
    "hand_roars",
    "hand_dead_roars",
    "hand_strength_mean",
    "hand_strength_max",
    "hand_small",
    "hand_fliers",
    "hand_food_cards",
    "hand_food_affordable",
    "hand_tag_matches",
    "units_mine",
    "units_theirs",
    "engines_mine",
    "engines_theirs",
    "board_tag_pairs",
    "extra_actions_mine",
    "extra_actions_theirs",
    "den_front_held",
    "den_front_pressure",
    "pending_target_strength",
    "buried_presence",
)

FEATURE_SETS: dict[str, tuple[str, ...]] = {
    "rung0": RUNG0_FEATURES,
    "rung1": RUNG0_FEATURES + RUNG1_EXTRA_FEATURES,
    "rung2": RUNG0_FEATURES + RUNG1_EXTRA_FEATURES + RUNG2_EXTRA_FEATURES,
}


def feature_names(feature_set: str) -> tuple[str, ...]:
    """The ordered feature names for `feature_set` (`extract()`'s output order)."""
    try:
        return FEATURE_SETS[feature_set]
    except KeyError:
        raise ValueError(f"unknown feature_set {feature_set!r}, expected one of {sorted(FEATURE_SETS)}")


def schema_hash(feature_set: str) -> str:
    """A short, stable hash of `feature_set`'s name/order/normalization constants.

    Weight artifacts store the hash they were trained against; `learned_eval.load_eval`
    recomputes it on load and fails loudly on a mismatch (stale artifact vs. a
    features.py that has since changed) rather than silently scoring with the wrong
    feature meanings.
    """
    payload = {
        "feature_set": feature_set,
        "features": list(feature_names(feature_set)),
        "constants": {
            "T_NORM": T_NORM,
            "DECK_NORM": DECK_NORM,
            "TOTAL_CARDS_NORM": TOTAL_CARDS_NORM,
            "HQ_DIST_CAP": HQ_DIST_CAP,
        },
    }
    blob = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def extract(state: GameState, me: str, feature_set: str = "rung0") -> list[float]:
    """The feature vector for `state` from `me`'s perspective, in `feature_names()` order.

    `state` must be non-terminal (`state.result is None`) - callers scoring a finished game
    use the evaluator's own terminal contract (+/-inf / 0.0), never this vector (see
    `learned_eval.LinearEval.value`).
    """
    if state.result is not None:
        raise ValueError("extract() is for non-terminal states only - check state.result first")
    names = feature_names(feature_set)
    opp = other_player(me)
    my_connection = state.connected_occupied(me)
    opp_connection = state.connected_occupied(opp)

    values: dict[str, float] = {}
    food_progress, food_proximity = food_terms(state, me, opp)
    values["food_progress"] = food_progress
    values["food_proximity"] = food_proximity
    values["board_presence"] = board_presence(state, me, opp)
    values["connection"] = float(len(my_connection))
    # Computed once and reused by rung1's income_diff below (same corner-ownership scan).
    region_fractions = list(_region_fractions(state, me, opp))
    values["region_control"] = region_control(state, me, opp, fractions=region_fractions)
    enemy_threat, own_threat = hq_threat_terms(state, me, opp, my_connection, opp_connection)
    values["enemy_hq_threat"] = enemy_threat
    values["own_hq_threat"] = -own_threat
    values["coverage_exposure"] = -coverage_exposure_worst(state, me, opp, opp_connection)
    values["card_economy"] = card_economy(state, me, opp)
    values["effect_readiness"] = float(enabled_roar_count(state, me))
    values["pending_payoff"] = pending_payoff(state, me, opp)

    if feature_set in ("rung1", "rung2"):
        phase = min(1.0, state.turn_counter / T_NORM)
        growth = growth_board_diff(state, me, opp)
        values["growth_board_diff"] = growth
        values["growth_rate_diff"] = growth_rate_diff_from(state, me, opp, growth=growth)
        dyn = dynamic_board_diff(state, me, opp)
        values["dynamic_board_diff"] = float(dyn)
        values["dynamic_fuel"] = (len(state.remove_pile) / TOTAL_CARDS_NORM) * dyn
        values["phase_x_growth"] = phase * growth
        near, far = scheduled_horizon_diffs(state, me, opp)
        values["sched_near_diff"] = near
        values["sched_far_diff"] = far
        income = income_diff(state, me, opp, fractions=region_fractions)
        values["income_diff"] = income
        values["income_x_future"] = income * (1.0 - phase)
        values["deck_diff"] = (len(state.decks[me]) - len(state.decks[opp])) / DECK_NORM
        values["phase_x_food"] = phase * food_progress
        values["hq_dist_diff"] = hq_dist_diff(state, me, opp, my_connection, opp_connection)
        values["flight_hand_expected_diff"] = flight_hand_expected_diff(state, me, opp)

    if feature_set == "rung2":
        values.update(context_features(state, me, opp, opp_connection))

    return [values[name] for name in names]


# =============================================================== rung-0 term helpers
# Moved verbatim from bots/greedy_bot.py's evaluate() - rung 0 is the hand eval, not a
# re-implementation of it. `evaluate()` now calls these same functions.

def food_terms(state: GameState, me: str, opp: str) -> tuple[float, float]:
    """(food_progress, food_proximity): net food, and pull toward the food win."""
    gm = state.game_map
    return (
        float(state.food[me] - state.food[opp]),
        state.food[me] / gm.win_food,
    )


def board_presence(state: GameState, me: str, opp: str) -> float:
    """Net effective strength of controlled crossroads (mine - theirs)."""
    presence = 0.0
    sources = aura_sources(state)
    for stack in state.board.values():
        if not stack:
            continue
        top = stack[-1]
        s = effective_strength(state, top, sources)
        presence += s if top.owner == me else -s
    return presence


def _region_fractions(state: GameState, me: str, opp: str) -> Iterator[tuple[int, float, float]]:
    """Yield (region.food, mine_fraction, theirs_fraction) for every region on the map."""
    board = state.board
    for r in state.game_map.regions.values():
        n = len(r.corners)
        mine = theirs = 0
        for c in r.corners:                 # owner_of(c), inlined: evaluated for every position the search imagines
            st = board.get(c)
            if st:
                if st[-1].owner == me:
                    mine += 1
                elif st[-1].owner == opp:
                    theirs += 1
        yield r.food, mine / n, theirs / n


def region_control(state: GameState, me: str, opp: str, *, fractions=None) -> float:
    """Nonlinear, symmetric region-control score (cubing keeps a lone speculative corner
    small while a 3/4 or completed region matters strategically - see evaluate())."""
    region = 0.0
    for food, mine, theirs in (fractions if fractions is not None else _region_fractions(state, me, opp)):
        region += food * (mine ** 3 - theirs ** 3)
    return region


def hq_threat_terms(
    state: GameState, me: str, opp: str, my_connection: set, opp_connection: set, reach: float = 0.0,
) -> tuple[float, float]:
    """(enemy_hq_threat, own_hq_threat): crossroads I/they hold connected in front of the
    other's HQ. Only a connected chain can capture next turn.

    `reach` (0 = off) adds that fraction for every front crossroad the attacker holds cut off but one placement from
    connected: an empty crossroad next to both their chain and the cut-off piece. With two actions a turn, placing the
    connector and capturing is one turn, so a cut-off Falcon in the den front is a threat the chain rule cannot see
    (Martin's game GMIDKA, 2026-10-21: the Advanced bot left two of them standing for two turns)."""
    gm = state.game_map
    enemy_threat = float(sum(1 for cr in gm.hq_front(opp) if cr in my_connection))
    own_threat = float(sum(1 for cr in gm.hq_front(me) if cr in opp_connection))
    if reach:
        enemy_threat += reach * _reachable_front(state, me, opp, my_connection)
        own_threat += reach * _reachable_front(state, opp, me, opp_connection)
    return enemy_threat, own_threat


def _reachable_front(state: GameState, attacker: str, defender: str, connection: set) -> int:
    """Front crossroads of `defender` that `attacker` holds cut off, but that one placement on an empty crossroad
    would connect to the attacker's chain (or to the attacker's own front, which counts as the chain's start)."""
    gm = state.game_map
    board = state.board
    cut = [cr for cr in gm.hq_front(defender) if cr not in connection and (st := board.get(cr)) and st[-1].owner == attacker]
    if not cut:
        return 0
    home = gm.hq_front(attacker)
    count = 0
    for front in cut:
        # the cut-off group the front piece belongs to (attacker-topped crossroads, none of them connected)
        group, queue = {front}, [front]
        while queue:
            cr = queue.pop()
            for nb in gm.neighbors(cr):
                if nb not in group and (st := board.get(nb)) and st[-1].owner == attacker:
                    group.add(nb)
                    queue.append(nb)
        for cr in group:
            hit = False
            for nb in gm.neighbors(cr):
                if board.get(nb):
                    continue                     # a placement must land on an empty crossroad
                if nb in home or any(x in connection for x in gm.neighbors(nb)):
                    hit = True
                    break
            if hit:
                count += 1
                break
    return count


def opponent_unseen_card_ids(state: GameState, opp: str) -> list[str]:
    """The opponent's unseen cards (hand + deck) as one combined multiset of card ids.

    Public under the open-list rules: this equals the opponent's fixed 30-card list minus
    everything already observed (their units on the board, cards in the shared Remove Pile).
    Hand and deck are read *together* and never distinguished by which card sits where - the
    only honest use is the partition-invariant (multiset, hand-size) pair.
    """
    ids = [u.card_id for u in state.hands[opp]]
    ids += state.decks[opp]
    return ids


def p_opponent_can_cover(state: GameState, opp: str, defender_strength: int) -> float:
    """Exact P(the opponent's hidden hand holds >=1 unit that can cover `defender_strength`).

    Covering needs a *unit* of printed strength strictly greater. The unseen multiset splits
    into `h` cards in hand and the rest in deck uniformly at random, so the marginal is a
    closed-form hypergeometric - no determinization/sampling. Dynamic-strength units can't be
    read before placement, so they're conservatively excluded from the coverer count (they
    still occupy hand/deck slots, i.e. stay in the denominator).
    """
    unseen = opponent_unseen_card_ids(state, opp)
    N = len(unseen)
    h = len(state.hands[opp])
    if N == 0 or h == 0:
        return 0.0
    k = 0
    for cid in unseen:
        c = state.cards[cid]
        if not c.is_dynamic and c.base_strength > defender_strength:  # type: ignore[operator]
            k += 1
    if k == 0:
        return 0.0
    if k > N - h:                      # more coverers than deck slots -> at least one in hand
        return 1.0
    return 1.0 - math.comb(N - k, h) / math.comb(N, h)


def held_region_control(state: GameState, me: str, opp: str) -> float:
    """Region control counted by what each side can hold (Martin, 2026-10-22: the bot counts a contested middle as owned;
    his swing turns took back 50 region points a round with one or two cards). A corner is worth 1 minus the chance the
    other side holds a unit that covers it: for my corners the exact chance their hidden hand holds a stronger unit
    (`p_opponent_can_cover`), for theirs whether my own hand holds one. Reach is not asked: with two actions a turn a
    connector and the cover are one turn, and in Martin's swing replies 37 of the 48 pieces the bot had just placed were
    coverable from his hand while only 13 stood next to his chain. A Lion on their six takes a corner they held and adds
    one almost nothing covers; an Owl in the middle adds a corner every hand covers. Same cube and food weighting as
    `region_control`."""
    board = state.board
    unseen = opponent_unseen_card_ids(state, opp)
    n_unseen, h_opp = len(unseen), len(state.hands[opp])
    their_strengths = sorted(c.base_strength for c in (state.cards[cid] for cid in unseen) if not c.is_dynamic)  # type: ignore[type-var]
    my_best = max((effective_strength(state, u) for u in state.hands[me] if not state.cards[u.card_id].is_dynamic), default=-1)
    sources = aura_sources(state)
    region = 0.0
    for r in state.game_map.regions.values():
        n = len(r.corners)
        mine = theirs = 0.0
        for cr in r.corners:
            st = board.get(cr)
            if not st:
                continue
            top = st[-1]
            if top.owner == me:
                hold = 1.0
                if n_unseen and h_opp:
                    s = effective_strength(state, top, sources)
                    k = len(their_strengths) - bisect.bisect_right(their_strengths, s)
                    if k:
                        hold = math.comb(n_unseen - k, h_opp) / math.comb(n_unseen, h_opp) if k <= n_unseen - h_opp else 0.0
                mine += hold
            elif top.owner == opp:
                covered = my_best > effective_strength(state, top, sources)
                theirs += 0.0 if covered else 1.0
        region += r.food * ((mine / n) ** 3 - (theirs / n) ** 3)
    return region


def coverage_exposure_worst(state: GameState, me: str, opp: str, opp_connection: set) -> float:
    """Expected own-HQ danger one ply ahead: P(opponent's hidden hand can cover a currently-
    safe HQ-front defender of mine next turn). Opponent gets one placement, so this charges
    the single worst breach, not the sum (which would fantasize a multi-cover turn)."""
    gm = state.game_map
    worst = 0.0
    for cr in gm.hq_front(me):
        top = state.top_unit(cr)
        if top is not None and top.owner == me and state.is_connected(opp, cr, opp_connection):
            p = p_opponent_can_cover(state, opp, effective_strength(state, top))
            worst = max(worst, p)
    return worst


def card_economy(state: GameState, me: str, opp: str) -> float:
    """Net cards in hand (not deck - hand size is the real flexibility/tempo resource)."""
    return float(len(state.hands[me]) - len(state.hands[opp]))


def _roar_fizzled(pre: GameState, post: GameState, me: str, action) -> bool:
    """True if `action` played a card with ability text but nothing beyond the unit landing
    on the board actually happened - e.g. a removal roar with no adjacent target.

    Needs the before/after state pair plus the action taken, so it isn't itself a position
    feature (it can't be computed from a single state); it's shared here because
    `enabled_roar_count` (a real feature) uses it to decide whether a candidate
    Roar would actually do anything. Generic over card text - only checks whether
    anything *observable* moved, never a specific card id.
    """
    if not isinstance(action, PlaceAction) or action.is_hq_capture:
        return False
    if not pre.cards[action.card_id].has_roar:
        return False  # passives, keywords, Deathrattles, and vanilla units are not Roars
    if post.current != pre.current or post.turn_counter != pre.turn_counter:
        # The turn's last action: `post` already holds the turn's end (region food, Dusk), which would read as the Roar
        # doing something. Judge it on a copy with an action to spare, so the turn doesn't end.
        post = pre.clone()
        post.actions_taken_this_turn -= 1
        rules.apply_action(post, action, validate=False)
    if post.pending is not None:
        return False  # roar offered a real choice - it hasn't fizzled, its outcome just
                       # isn't resolved yet
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
        return False  # delayed Roar payoff (Grizzly Bear, Black Bear, Scrooge)
    return True


def _unit_count(state: GameState) -> int:
    return sum(len(stack) for stack in state.board.values())


def _total_strength_counters(state: GameState) -> int:
    board = sum(u.strength_counter for stack in state.board.values() for u in stack)
    hands = sum(u.strength_counter for hand in state.hands.values() for u in hand)
    return board + hands


def enabled_roar_count(state: GameState, player: str) -> int:
    """Count distinct Roars in hand that have at least one live legal placement (see `enabled_roar_ids`)."""
    return len(enabled_roar_ids(state, player))


HAND_RANK_WEIGHTS = (1.0, 1.0, 1.0, 1.0, 1.0, 0.5)   # a hand's five best cards count fully, the sixth half, the rest not
HAND_CARD_BONUS = 0.5                        # per card: having a choice is worth a little, however weak the cards
HAND_UNSEEN_CARD = 3.0                       # the opponent's hidden cards, valued by count only (honesty)


def hand_value(state: GameState, me: str, opp: str, ranks=HAND_RANK_WEIGHTS) -> float:
    """What each hand can do, mine minus theirs (Martin, 2026-10-14: a hand is worth its best few plays, not its size).
    A card's play value is what placing it adds (half its strength, like board_presence, plus 1 for the connection,
    like `connection`). My hand counts its best cards by `ranks`; the opponent's is hidden, so it is valued by its
    size alone. Paired tests, 2026-10-15: every deck gains under ExpertBot (about +10 points on average)."""
    vals = sorted((0.5 * effective_strength(state, u) + 1.0 for u in state.hands[me]), reverse=True)
    mine = sum(w * v for w, v in zip(ranks, vals)) + HAND_CARD_BONUS * len(vals)
    n = len(state.hands[opp])
    theirs = sum(w * HAND_UNSEEN_CARD for w in ranks[:n]) + HAND_CARD_BONUS * n
    return mine - theirs


def enabled_roar_ids(state: GameState, player: str) -> set:
    """The distinct Roars in hand that have at least one live legal placement.

    Only outcome *shape* is observed (draw count, pending choice, removal, and so on);
    drawn card identities never enter the score. Call only at a top-level decision for
    `player`; pending effect choices are already concrete and need no readiness estimate.
    """
    from ..engine.effects import legal_placements  # local: avoid a bots<->engine import cycle

    if (state.result is not None or state.pending is not None
            or state.player_to_act() != player
            or state.actions_taken_this_turn != 0):
        return set()
    roars = {
        u.card_id for u in state.hands[player]
        if state.cards[u.card_id].has_roar
    }
    if not roars:
        return set()
    placements = [
        a for a in legal_placements(state, player, allowed_cards=roars)
        if not a.is_hq_capture
    ]
    by_card: dict[str, list[PlaceAction]] = {}
    for action in placements:
        by_card.setdefault(action.card_id, []).append(action)
    representatives: list[PlaceAction] = []
    opponent = other_player(player)
    occ = state.connected_occupied(player)
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
        rules.apply_action(nxt, action, validate=False)
        if not _roar_fizzled(state, nxt, player, action):
            enabled.add(action.card_id)
    return enabled


def pending_payoff(state: GameState, me: str, opp: str) -> float:
    """Net imminence-discounted scheduled future effects (Egg hatch, Bear, ...)."""
    pending = 0.0
    for s in state.scheduled:
        horizon = 2 * max(0, s["remaining"]) - (0 if state.current == s["owner"] else 1)
        disc = 1.0 / (1.0 + max(0, horizon))
        pending += disc if s["owner"] == me else -disc
    return pending


def pending_target_strength(state: GameState, me: str, opp: str) -> float:
    """Net effective strength of the units that scheduled removals will take (a Taipan's marked animal), imminence-
    discounted as `pending_payoff`. `pending_payoff` pays the same for any delayed effect, so a removal scored the same
    whatever it marked (the bot marked a Raven over a Python, 2026-09-30); this term is what the mark is worth."""
    total = 0.0
    for s in state.scheduled:
        step = s["step"]
        if step.get("op") != "remove_iid":
            continue
        target = _unit_by_iid(state, step["iid"])
        if target is None or target.owner == s["owner"]:
            continue
        horizon = 2 * max(0, s["remaining"]) - (0 if state.current == s["owner"] else 1)
        value = effective_strength(state, target) / (1.0 + 0.25 * max(0, horizon))   # a mark almost always lands: a soft discount
        total += value if s["owner"] == me else -value
    return total


def buried_presence(state: GameState, me: str, opp: str) -> float:
    """Net effective strength of the units under a cover (mine - theirs). A covered unit is not gone: it is back on top
    the moment its coverer leaves, so an enemy 8 under my 3 is a liability `board_presence` (top units only) can't see,
    and the eval otherwise scores covering it like removing it (the Taipan puzzle, 2026-10-17)."""
    total = 0.0
    for stack in state.board.values():
        for u in stack[:-1]:
            s = effective_strength(state, u)
            total += s if u.owner == me else -s
    return total


def _unit_by_iid(state: GameState, iid):
    for stack in state.board.values():
        for u in stack:
            if u.iid == iid:
                return u
    return None


# =============================================================== rung-1 dynamics helpers
# All public-info, card-agnostic (only base_strength/is_dynamic/keywords/food_cost/
# has_roar ever read from Card), and antisymmetric by construction (mine - theirs).

def growth_board_diff(state: GameState, me: str, opp: str) -> float:
    """Net accumulated strength growth: on-board stored counters + global per-card growth
    (Rattlesnake-style), mine minus theirs. Hand-instance counters are excluded on both
    sides - this is about growth that has actually reached the board."""
    board_mine = 0
    board_theirs = 0
    for stack in state.board.values():
        for u in stack:
            if u.owner == me:
                board_mine += u.strength_counter
            elif u.owner == opp:
                board_theirs += u.strength_counter
    global_mine = sum(state.card_strength_counters.get(me, {}).values())
    global_theirs = sum(state.card_strength_counters.get(opp, {}).values())
    return float((board_mine - board_theirs) + (global_mine - global_theirs))


def growth_rate_diff_from(state: GameState, me: str, opp: str, *, growth: Optional[float] = None) -> float:
    """`growth_board_diff` normalized per elapsed turn - a cheap proxy for "growing turn over
    turn" rather than just "grown so far". `growth` may be passed in to avoid recomputing it
    when the caller already has it (see `extract`)."""
    if growth is None:
        growth = growth_board_diff(state, me, opp)
    return growth / max(1, state.turn_counter)


def dynamic_board_diff(state: GameState, me: str, opp: str) -> int:
    """Net count of dynamic-strength top units on the board (mine - theirs) - e.g. a Goliath
    that keeps growing off the shared Remove Pile is a real, publicly visible investment."""
    mine = 0
    theirs = 0
    for stack in state.board.values():
        if not stack:
            continue
        top = stack[-1]
        if state.cards[top.card_id].is_dynamic:
            if top.owner == me:
                mine += 1
            elif top.owner == opp:
                theirs += 1
    return mine - theirs


def scheduled_horizon_diffs(state: GameState, me: str, opp: str) -> tuple[float, float]:
    """(sched_near_diff, sched_far_diff): net scheduled-effect counts split by how soon they
    fire (<=1 vs >=2 owner-turns remaining), undiscounted - unlike `pending_payoff`, this
    lets TD learn its own near/far weighting instead of a hand-imposed horizon discount."""
    near = 0.0
    far = 0.0
    for s in state.scheduled:
        remaining = max(0, s["remaining"])
        sign = 1.0 if s["owner"] == me else -1.0
        if remaining <= 1:
            near += sign
        else:
            far += sign
    return near, far


def income_diff(state: GameState, me: str, opp: str, *, fractions=None) -> float:
    """Net food/turn from *fully*-controlled regions (mine - theirs) - the literal food
    income the region-control engine already pays out, vs. `region_control`'s smoothed
    fractional-progress heuristic."""
    mine_income = 0
    theirs_income = 0
    for food, mine, theirs in (fractions if fractions is not None else _region_fractions(state, me, opp)):
        if mine >= 1.0:
            mine_income += food
        if theirs >= 1.0:
            theirs_income += food
    return float(mine_income - theirs_income)


def _bfs_distance(state: GameState, sources: set, targets: frozenset) -> int:
    """Shortest hop count (map topology only, not gated by occupancy) from any crossroad in
    `sources` to any crossroad in `targets`; `HQ_DIST_CAP` if unreachable within the cap."""
    gm = state.game_map
    if not sources:
        return HQ_DIST_CAP
    if sources & targets:
        return 0
    seen = set(sources)
    frontier = deque(sources)
    dist = 0
    while frontier and dist < HQ_DIST_CAP:
        dist += 1
        next_frontier: deque = deque()
        for cr in frontier:
            for nb in gm.neighbors(cr):
                if nb in targets:
                    return dist
                if nb not in seen:
                    seen.add(nb)
                    next_frontier.append(nb)
        frontier = next_frontier
    return HQ_DIST_CAP


def hq_dist_diff(
    state: GameState, me: str, opp: str, my_connection: set, opp_connection: set,
) -> float:
    """Net HQ-ward board proximity: my closeness to the enemy HQ front minus their closeness
    to mine, each mapped through 1/(1+dist) so a growing connected chain visibly shrinks the
    distance long before it becomes a literal `enemy_hq_threat` hit."""
    gm = state.game_map
    my_sources = my_connection or gm.hq_front(me)
    opp_sources = opp_connection or gm.hq_front(opp)
    my_dist = _bfs_distance(state, set(my_sources), gm.hq_front(opp))
    opp_dist = _bfs_distance(state, set(opp_sources), gm.hq_front(me))
    return (1.0 / (1.0 + my_dist)) - (1.0 / (1.0 + opp_dist))


def flight_hand_expected_diff(state: GameState, me: str, opp: str) -> float:
    """Net Flight-keyword units expected in hand: my exact count vs. the opponent's expected
    count over the public unseen (hand+deck) multiset - Flight/reach cards are the ones that
    let a plan skip the connection grind (see docs/rules/mental-model.md)."""
    own = sum(1 for u in state.hands[me] if state.cards[u.card_id].has_keyword("Flight"))
    unseen = opponent_unseen_card_ids(state, opp)
    N = len(unseen)
    h = len(state.hands[opp])
    if N == 0 or h == 0:
        expected_opp = 0.0
    else:
        flight_count = sum(1 for cid in unseen if state.cards[cid].has_keyword("Flight"))
        expected_opp = h * (flight_count / N)
    return float(own) - expected_opp


# =============================================================== rung-2 context helpers

def has_ability(card) -> bool:
    """Rules text beyond keywords and a food cost: a Roar, a trigger, an aura (generic - reads
    only the printed text's shape, never which card it is)."""
    rest = [t.strip() for t in card.text.split(".") if t.strip()]
    rest = [t for t in rest if t not in card.keywords and not t.startswith("Costs ")]
    return bool(rest)


def _extra_actions(state: GameState, player: str) -> float:
    """Extra top-level actions `player` has coming: granted this turn, or scheduled."""
    pending = sum(s["step"].get("n", 1) for s in state.scheduled
                  if s["owner"] == player and s["step"].get("op") == "grant_action")
    return float(state.turn_flags.get(f"bonus_actions_{player}", 0) + pending)


def context_features(state: GameState, me: str, opp: str, opp_connection: set) -> dict:
    cards = state.cards
    hand = [cards[u.card_id] for u in state.hands[me]]
    strengths = [c.base_strength for c in hand if not c.is_dynamic]
    roars = sum(c.has_roar for c in hand)
    live = enabled_roar_count(state, me)
    tops = [st[-1] for st in state.board.values() if st]
    mine = [u for u in tops if u.owner == me]
    theirs = [u for u in tops if u.owner == opp]
    my_tags = [cards[u.card_id].tags for u in mine]
    board_tags = set().union(*my_tags) if my_tags else set()
    pairs = sum(1 for i in range(len(my_tags)) for j in range(i + 1, len(my_tags))
                if my_tags[i] & my_tags[j])
    gm = state.game_map
    front = gm.hq_front(me)
    held = sum(1 for cr in front if (t := state.top_unit(cr)) is not None and t.owner == me)  # type: ignore[misc]
    near_front = {n for cr in front for n in gm.neighbors(cr)} | set(front)
    pressure = sum(1 for cr in near_front if cr in opp_connection)
    return {
        "to_move": float(state.current == me),
        "phase": min(1.0, state.turn_counter / T_NORM),
        "hand_mine": float(len(hand)),
        "hand_theirs": float(len(state.hands[opp])),
        "hand_roars": float(roars),
        "hand_dead_roars": float(max(0, roars - live)),
        "hand_strength_mean": sum(strengths) / len(strengths) if strengths else 0.0,  # type: ignore[arg-type]
        "hand_strength_max": float(max(strengths, default=0)),
        "hand_small": float(sum(1 for x in strengths if x <= 2)),  # type: ignore[misc, operator]
        "hand_fliers": float(sum(c.has_keyword("Flight") for c in hand)),  # type: ignore[arg-type]
        "hand_food_cards": float(sum(bool(c.food_cost) for c in hand)),
        "hand_food_affordable": float(sum(bool(c.food_cost) and c.food_cost <= state.food[me]
                                          for c in hand)),
        "hand_tag_matches": float(sum(bool(c.tags & board_tags) for c in hand)),
        "units_mine": float(len(mine)),
        "units_theirs": float(len(theirs)),
        "engines_mine": float(sum(has_ability(cards[u.card_id]) and not cards[u.card_id].has_roar
                                  for u in mine)),
        "engines_theirs": float(sum(has_ability(cards[u.card_id]) and not cards[u.card_id].has_roar
                                    for u in theirs)),
        "board_tag_pairs": float(pairs),
        "extra_actions_mine": _extra_actions(state, me),
        "extra_actions_theirs": _extra_actions(state, opp),
        "den_front_held": float(held),
        "den_front_pressure": float(pressure),
        "pending_target_strength": pending_target_strength(state, me, opp),
        "buried_presence": buried_presence(state, me, opp),
    }
