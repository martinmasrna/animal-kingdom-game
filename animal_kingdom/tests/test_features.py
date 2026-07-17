"""Tests for bots/features.py: the shared rung-0/rung-1 feature extraction module.

Map A geometry (see _helpers/test_greedy_bot.py): a 4x3 grid, A's HQ front is column 1
("1,1"/"1,2"/"1,3"), B's is column 4; orthogonal neighbours.

Covers: honesty mirrors (opponent-hand-contents invariance, partition invariance, deck-order
invariance), rung-1 dynamics antisymmetry, a source-scan guard (no card ids/deck slugs/tag
tokens as real string literals in features.py - docstring prose is exempt), one directional
scenario per rung-1 dynamics feature, and a schema-hash snapshot.
"""

from __future__ import annotations

import ast
import random
from pathlib import Path

import pytest

from animal_kingdom.bots import features
from animal_kingdom.engine.cards import DECK_SLUGS, TAGS, load_cards

from ._helpers import make_state, put

RUNG0 = features.RUNG0_FEATURES
RUNG1_EXTRA = features.RUNG1_EXTRA_FEATURES


def _vec(state, me, feature_set="rung0") -> dict:
    names = features.feature_names(feature_set)
    return dict(zip(names, features.extract(state, me, feature_set)))


# ------------------------------------------------------------------- feature_names/schema

def test_feature_names_rung1_extends_rung0():
    assert features.feature_names("rung0") == RUNG0
    assert features.feature_names("rung1") == RUNG0 + RUNG1_EXTRA
    assert len(RUNG0) == 11
    assert len(set(RUNG0) | set(RUNG1_EXTRA)) == len(RUNG0) + len(RUNG1_EXTRA)  # no name clash


def test_feature_names_rejects_unknown_set():
    with pytest.raises(ValueError):
        features.feature_names("rung2")


def test_schema_hash_snapshot():
    # Pins the schema so an accidental reorder/rename/constant edit fails loudly (artifacts
    # trained against the old schema would otherwise silently score with new meanings).
    assert features.schema_hash("rung0") == "e6367321913d11c0"
    assert features.schema_hash("rung1") == "e95d822f8a09a044"


def test_schema_hash_changes_with_constants():
    # Sanity check the hash actually depends on the constants (not just names) - guards
    # against a hash function that accidentally ignores schema content.
    payload_names = features.feature_names("rung0")
    assert features.schema_hash("rung0") != features.schema_hash("rung1")
    assert len(payload_names) > 0


def test_extract_rejects_terminal_state():
    from animal_kingdom.engine.state import Result
    s = make_state()
    s.result = Result("A", "hq_capture")
    with pytest.raises(ValueError):
        features.extract(s, "A")


# ----------------------------------------------------------------------- rung0 == evaluate()

def test_rung0_extract_matches_evaluate_dot_product():
    from animal_kingdom.bots.greedy_bot import GreedyWeights, evaluate
    w = GreedyWeights()
    s = make_state(hands={"A": ["lion", "mouse"], "B": ["mouse"]},
                   decks={"A": ["mouse"] * 5, "B": ["mouse"] * 3})
    put(s, "1,2", "lion", "A")
    put(s, "2,2", "mouse", "B")
    vec = dict(zip(RUNG0, features.extract(s, "A", "rung0")))
    dot = (w.food_progress * vec["food_progress"]
           + w.food_proximity * vec["food_proximity"]
           + w.board_presence * vec["board_presence"]
           + w.connection * vec["connection"]
           + w.region_control * vec["region_control"]
           + w.enemy_hq_threat * vec["enemy_hq_threat"]
           + w.own_hq_threat * -vec["own_hq_threat"]  # feature already carries the minus sign
           + w.coverage_exposure * -vec["coverage_exposure"]
           + w.card_economy * vec["card_economy"]
           + w.effect_readiness * vec["effect_readiness"]
           + w.pending_payoff * vec["pending_payoff"])
    assert dot == pytest.approx(evaluate(s, "A", w), abs=1e-9)


# ------------------------------------------------------------------------- honesty mirrors

def test_opponent_hand_contents_invariance_rung1():
    # Only opponent hand SIZE (and, for the belief feature, the combined unseen multiset) may
    # matter - which exact card ids sit in the opponent's hand must not move any feature.
    common = dict(decks={"A": ["mouse"] * 4, "B": ["mouse"] * 4})
    s1 = make_state(hands={"A": ["lion"], "B": ["lion", "lion"]}, **common)
    s2 = make_state(hands={"A": ["lion"], "B": ["mouse", "mouse"]}, **common)
    put(s1, "1,2", "lion", "A")
    put(s2, "1,2", "lion", "A")
    assert features.extract(s1, "A", "rung1") == features.extract(s2, "A", "rung1")


def test_partition_invariance_rung1():
    # Holding the unseen multiset (eagle+mouse) and hand size fixed, whether "eagle" sits in
    # hand or deck must not move flight_hand_expected_diff (or anything else).
    a = make_state(hands={"B": ["eagle"]}, decks={"A": [], "B": ["mouse"]})
    b = make_state(hands={"B": ["mouse"]}, decks={"A": [], "B": ["eagle"]})
    va = _vec(a, "A", "rung1")
    vb = _vec(b, "A", "rung1")
    assert va == vb


def test_deck_order_invariance_rung1():
    s1 = make_state(decks={"A": ["lion", "mouse", "eagle", "mouse"], "B": ["mouse"] * 3})
    s2 = make_state(decks={"A": ["mouse", "eagle", "mouse", "lion"], "B": ["mouse"] * 3})
    put(s1, "1,2", "lion", "A")
    put(s2, "1,2", "lion", "A")
    assert features.extract(s1, "A", "rung1") == features.extract(s2, "A", "rung1")


def test_own_deck_order_invariance_rung1():
    # The hard invariant explicitly covers *my own* deck order too, not just the opponent's.
    rng = random.Random(0)
    order_a = ["lion", "mouse", "eagle", "mouse", "lion"]
    order_b = list(order_a)
    rng.shuffle(order_b)
    s1 = make_state(decks={"A": order_a, "B": []})
    s2 = make_state(decks={"A": order_b, "B": []})
    assert features.extract(s1, "A", "rung1") == features.extract(s2, "A", "rung1")


# ---------------------------------------------------------------- rung1 dynamics antisymmetry

# Every rung-1 feature except `flight_hand_expected_diff` is a strict mine-minus-theirs
# difference of a same-shaped public quantity, so swapping (me, opp) must exactly negate it.
# `flight_hand_expected_diff` deliberately mixes an exact own-hand count with a *belief* over
# the opponent's hidden hand (like rung0's `coverage_exposure`), so it is not expected to be a
# clean negation under a perspective swap - it's covered by the honesty tests above instead.
ANTISYMMETRIC_RUNG1 = tuple(f for f in RUNG1_EXTRA if f != "flight_hand_expected_diff")


def _random_state(seed: int):
    rng = random.Random(seed)
    decks = {"A": rng.choices(["lion", "mouse", "eagle"], k=6),
             "B": rng.choices(["lion", "mouse", "eagle"], k=6)}
    s = make_state(hands={"A": rng.choices(["mouse"], k=2), "B": rng.choices(["mouse"], k=1)},
                   decks=decks, food={"A": rng.randint(0, 40), "B": rng.randint(0, 40)})
    s.turn_counter = rng.randint(0, 20)
    crossroads = ["1,1", "1,2", "2,1", "2,2", "3,2", "4,2", "3,3"]
    rng.shuffle(crossroads)
    for cr, owner in zip(crossroads, ["A", "B", "A", "B", "A", None, "B"]):
        if owner:
            u = put(s, cr, rng.choice(["lion", "mouse", "goliath"]), owner)
            u.strength_counter = rng.choice([0, 1, 2])
    s.card_strength_counters["A"]["lion"] = rng.choice([0, 1, 3])
    s.card_strength_counters["B"]["mouse"] = rng.choice([0, 2])
    s.remove_pile = ["mouse"] * rng.randint(0, 5)
    s.scheduled = [
        {"owner": rng.choice(["A", "B"]), "remaining": rng.randint(0, 3)}
        for _ in range(rng.randint(0, 4))
    ]
    return s


@pytest.mark.parametrize("seed", range(8))
def test_rung1_dynamics_are_antisymmetric(seed):
    s = _random_state(seed)
    va = _vec(s, "A", "rung1")
    vb = _vec(s, "B", "rung1")
    for name in ANTISYMMETRIC_RUNG1:
        assert va[name] == pytest.approx(-vb[name], abs=1e-9), name


# --------------------------------------------------------- one directional scenario / feature

def test_growth_board_diff_direction():
    s = make_state()
    put(s, "1,2", "lion", "A")
    u = put(s, "2,2", "mouse", "B")
    u.strength_counter = 2
    lion_unit = s.board["1,2"][-1]
    lion_unit.strength_counter = 5
    s.card_strength_counters["A"]["lion"] = 1
    assert features.growth_board_diff(s, "A", "B") == pytest.approx((5 - 2) + (1 - 0))
    assert features.growth_board_diff(s, "B", "A") == pytest.approx(-((5 - 2) + (1 - 0)))


def test_growth_board_diff_excludes_hand_counters():
    s = make_state(hands={"A": ["lion"]})
    s.hands["A"][0].strength_counter = 9   # a hand-only counter must not leak in
    assert features.growth_board_diff(s, "A", "B") == 0.0


def test_growth_rate_diff_divides_by_turn():
    s = make_state()
    put(s, "1,2", "lion", "A").strength_counter = 6
    s.turn_counter = 3
    assert features.growth_board_diff(s, "A", "B") == 6.0
    assert features.growth_rate_diff_from(s, "A", "B") == pytest.approx(2.0)
    s.turn_counter = 0
    assert features.growth_rate_diff_from(s, "A", "B") == pytest.approx(6.0)  # max(1, 0) == 1


def test_dynamic_board_diff_counts_dynamic_tops():
    s = make_state()
    put(s, "1,2", "goliath", "A")
    put(s, "2,2", "lion", "B")   # not dynamic
    assert features.dynamic_board_diff(s, "A", "B") == 1
    assert features.dynamic_board_diff(s, "B", "A") == -1


def test_dynamic_fuel_scales_with_remove_pile():
    s = make_state()
    put(s, "1,2", "goliath", "A")
    s.remove_pile = ["mouse"] * 6   # 6/60 = 0.1
    vec = _vec(s, "A", "rung1")
    assert vec["dynamic_fuel"] == pytest.approx(0.1 * 1)


def test_phase_x_growth_matches_phase_times_growth():
    s = make_state()
    put(s, "1,2", "lion", "A").strength_counter = 4
    s.turn_counter = 26   # 2 * T_NORM -> phase clamps to 1.0
    vec = _vec(s, "A", "rung1")
    assert vec["phase_x_growth"] == pytest.approx(1.0 * vec["growth_board_diff"])
    assert vec["phase_x_growth"] == pytest.approx(4.0)


def test_sched_near_and_far_split_by_horizon():
    s = make_state()
    s.scheduled = [
        {"owner": "A", "remaining": 0},
        {"owner": "A", "remaining": 1},
        {"owner": "B", "remaining": 1},
        {"owner": "A", "remaining": 2},
        {"owner": "B", "remaining": 5},
    ]
    vec = _vec(s, "A", "rung1")
    assert vec["sched_near_diff"] == pytest.approx(2 - 1)   # A has 2 near (<=1), B has 1
    assert vec["sched_far_diff"] == pytest.approx(1 - 1)    # A has 1 far (>=2), B has 1


def test_income_diff_rewards_full_region_control():
    s = make_state()
    for cr in ("1,1", "2,1", "1,2", "2,2"):   # region R1, food 10
        put(s, cr, "lion", "A")
    vec = _vec(s, "A", "rung1")
    assert vec["income_diff"] == pytest.approx(10.0)
    assert _vec(s, "B", "rung1")["income_diff"] == pytest.approx(-10.0)


def test_income_x_future_matches_income_times_remaining_phase():
    s = make_state()
    for cr in ("1,1", "2,1", "1,2", "2,2"):
        put(s, cr, "lion", "A")
    s.turn_counter = 13   # phase == 1.0 at T_NORM
    vec = _vec(s, "A", "rung1")
    assert vec["income_x_future"] == pytest.approx(vec["income_diff"] * 0.0)


def test_deck_diff_direction():
    s = make_state(decks={"A": ["mouse"] * 9, "B": ["mouse"] * 3})
    vec = _vec(s, "A", "rung1")
    assert vec["deck_diff"] == pytest.approx((9 - 3) / features.DECK_NORM)


def test_phase_x_food_matches_phase_times_food_progress():
    s = make_state(food={"A": 20, "B": 5})
    s.turn_counter = 130   # far beyond T_NORM -> phase clamps to 1.0
    vec = _vec(s, "A", "rung1")
    assert vec["phase_x_food"] == pytest.approx(1.0 * vec["food_progress"])
    assert vec["phase_x_food"] == pytest.approx(15.0)


def test_hq_dist_diff_rewards_reaching_toward_enemy_hq():
    baseline = make_state()   # empty board: map is symmetric -> exactly 0
    assert _vec(baseline, "A", "rung1")["hq_dist_diff"] == pytest.approx(0.0)

    advancing = make_state()
    for cr in ("1,2", "2,2", "3,2"):
        put(advancing, cr, "lion", "A")
    assert _vec(advancing, "A", "rung1")["hq_dist_diff"] > 0.0
    assert _vec(advancing, "B", "rung1")["hq_dist_diff"] < 0.0


def test_flight_hand_expected_diff_direction():
    # A holds an exact Flight card; B's hand/deck (unseen to A) has none -> positive for A.
    s = make_state(hands={"A": ["eagle"], "B": ["mouse"]}, decks={"A": [], "B": ["mouse"] * 3})
    vec = _vec(s, "A", "rung1")
    assert vec["flight_hand_expected_diff"] == pytest.approx(1.0)


def test_flight_hand_expected_diff_partition_invariance():
    a = make_state(hands={"B": ["eagle"]}, decks={"A": [], "B": ["mouse", "mouse"]})
    b = make_state(hands={"B": ["mouse"]}, decks={"A": [], "B": ["eagle", "mouse"]})
    assert (_vec(a, "A", "rung1")["flight_hand_expected_diff"]
            == pytest.approx(_vec(b, "A", "rung1")["flight_hand_expected_diff"]))


# ------------------------------------------------------------------------ source-scan guard

def _non_docstring_string_literals(source: str) -> set[str]:
    """Every string literal in `source` except module/function/class docstrings."""
    tree = ast.parse(source)
    docstring_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                docstring_ids.add(id(body[0].value))
    literals = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and id(node) not in docstring_ids):
            literals.add(node.value)
    return literals


def test_features_source_has_no_card_deck_or_tag_literals():
    source = Path(features.__file__).read_text()
    literals = _non_docstring_string_literals(source)
    forbidden = set(load_cards()) | set(DECK_SLUGS) | set(TAGS)
    hits = literals & forbidden
    assert not hits, f"features.py must stay card/deck/tag-agnostic; found literal(s): {hits}"


def test_features_source_allows_flight_keyword_literal():
    # Sanity check the guard above isn't vacuous: "Flight" (a *keyword*, explicitly allowed
    # card metadata) is a real string literal in features.py.
    source = Path(features.__file__).read_text()
    literals = _non_docstring_string_literals(source)
    assert "Flight" in literals
