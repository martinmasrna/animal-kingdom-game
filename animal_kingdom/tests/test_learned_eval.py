"""Tests for bots/learned_eval.py: LinearEval artifact I/O, terminal contract, and the
hand-mimic equivalence that anchors rung 0 to the hand-written evaluate()."""

from __future__ import annotations

import math

import pytest

from animal_kingdom.bots import features
from animal_kingdom.bots.greedy_bot import GreedyBot, GreedyWeights, evaluate
from animal_kingdom.bots.learned_eval import LinearEval, load_eval
from animal_kingdom.decks import load_premade_deck
from animal_kingdom.engine import rules
from animal_kingdom.engine.state import Result, new_game

from ._helpers import make_state, put


# --------------------------------------------------------------------- construction

def test_rejects_wrong_weight_count():
    with pytest.raises(ValueError):
        LinearEval(feature_set="rung0", weights=(1.0, 2.0))  # rung0 needs 11


def test_terminal_contract_matches_evaluate():
    won = make_state()
    won.result = Result("A", "hq_capture")
    lost = make_state()
    lost.result = Result("B", "hq_capture")
    drawn = make_state()
    drawn.result = Result(None, "max_turns")

    ev = LinearEval.hand_mimic()
    assert ev.value(won, "A") == math.inf
    assert ev.value(lost, "A") == -math.inf
    assert ev.value(drawn, "A") == 0.0
    assert ev.win_prob(won, "A") == 1.0
    assert ev.win_prob(lost, "A") == 0.0
    assert ev.win_prob(drawn, "A") == 0.5


def test_win_prob_is_a_probability_for_nonterminal_states():
    s = make_state(hands={"A": ["lion"]})
    ev = LinearEval.hand_mimic()
    p = ev.win_prob(s, "A")
    assert 0.0 <= p <= 1.0


# --------------------------------------------------------------------------- I/O

def test_round_trip(tmp_path):
    ev = LinearEval(feature_set="rung1",
                    weights=tuple(float(i) for i in range(len(features.RUNG1_EXTRA_FEATURES)
                                                          + len(features.RUNG0_FEATURES))),
                    bias=0.5, provenance={"run_id": "test-1"})
    path = tmp_path / "artifact.json"
    ev.save(str(path))
    loaded = LinearEval.from_file(str(path))
    assert loaded.feature_set == ev.feature_set
    assert loaded.weights == ev.weights
    assert loaded.bias == ev.bias
    assert loaded.provenance == ev.provenance


def test_corrupted_hash_is_rejected_loudly(tmp_path):
    ev = LinearEval.hand_mimic()
    d = ev.to_dict()
    d["feature_schema_hash"] = "0000000000000000"
    path = tmp_path / "stale.json"
    import json
    path.write_text(json.dumps(d))
    with pytest.raises(ValueError, match="stale weight artifact"):
        LinearEval.from_file(str(path))


def test_load_eval_resolves_literal_path(tmp_path):
    ev = LinearEval.hand_mimic()
    path = tmp_path / "custom_name.json"
    ev.save(str(path))
    load_eval.cache_clear()
    loaded = load_eval(str(path))
    assert loaded.weights == ev.weights


def test_load_eval_caches_by_argument(tmp_path):
    ev = LinearEval.hand_mimic()
    path = tmp_path / "cached.json"
    ev.save(str(path))
    load_eval.cache_clear()
    first = load_eval(str(path))
    second = load_eval(str(path))
    assert first is second  # lru_cache: same object, not re-parsed


# ------------------------------------------------------------- hand-mimic equivalence

def _random_scenarios():
    s1 = make_state(hands={"A": ["lion", "mouse"], "B": ["mouse"]},
                    decks={"A": ["mouse"] * 5, "B": ["mouse"] * 3})
    put(s1, "1,2", "lion", "A")
    put(s1, "2,2", "mouse", "B")

    s2 = make_state(hands={"A": ["rat", "mouse"], "B": []},
                    decks={"A": ["mouse"] * 3, "B": ["mouse"] * 6})
    for cr in ("1,2", "2,2", "3,2"):
        put(s2, cr, "lion", "A")
    put(s2, "4,2", "eagle", "B")

    s3 = make_state(food={"A": 40, "B": 10})
    return [s1, s2, s3, make_state()]


@pytest.mark.parametrize("state", _random_scenarios())
def test_hand_mimic_matches_evaluate_to_1e9(state):
    w = GreedyWeights()
    ev = LinearEval.hand_mimic(w)
    assert ev.value(state, "A") == pytest.approx(evaluate(state, "A", w), abs=1e-9)
    assert ev.value(state, "B") == pytest.approx(evaluate(state, "B", w), abs=1e-9)


def test_hand_mimic_chooses_identically_over_a_seeded_game():
    # A full seeded game, decision by decision: the learned (hand-mimic) GreedyBot must pick
    # the exact same action as the hand-eval GreedyBot at every single choice point.
    ev = LinearEval.hand_mimic()
    state = new_game(load_premade_deck("ramp"), load_premade_deck("aggro_hq_rush"), seed=7)
    hand_bot = GreedyBot(seed=0)
    learned_bot = GreedyBot(seed=0, evaluator=ev)

    result = rules.is_terminal(state)
    steps = 0
    while result is None and steps < 500:
        actor = state.player_to_act()
        legal = rules.legal_actions(state)
        a_hand = hand_bot.choose(state.view_for(actor), legal, state)
        a_learned = learned_bot.choose(state.view_for(actor), legal, state)
        assert a_hand == a_learned
        rules.apply_action(state, a_hand)
        result = rules.is_terminal(state)
        steps += 1
    assert result is not None  # the game actually finished within the guard


def test_hand_mimic_matches_turn_bot_planning_eval():
    # The learned path in TurnSearcher._planning_eval re-scores the reframed state instead of
    # adding a manual readiness term; for a hand-mimic evaluator this must still reproduce the
    # hand path's score (readiness is already inside the weighted sum via effect_readiness).
    from animal_kingdom.bots.turn_bot import TurnBot

    ev = LinearEval.hand_mimic()
    state = new_game(load_premade_deck("cats_midrange"), load_premade_deck("egg_control"), seed=11)
    hand_bot = TurnBot(seed=0, determinizations=1, beam_width=4, max_search_nodes=40)
    learned_bot = TurnBot(seed=0, determinizations=1, beam_width=4, max_search_nodes=40,
                         evaluator=ev)

    actor = state.player_to_act()
    legal = rules.legal_actions(state)
    a_hand = hand_bot.choose(state.view_for(actor), legal, state)
    a_learned = learned_bot.choose(state.view_for(actor), legal, state)
    assert a_hand == a_learned
