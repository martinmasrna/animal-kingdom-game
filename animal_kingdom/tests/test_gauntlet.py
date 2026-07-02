"""Tests for the bot-version comparison harness (sim/gauntlet.py): does `run_gauntlet` +
`compare_gauntlets` actually let you tell whether a candidate bot is better, not just
different, against a pinned opponent pool.
"""

from __future__ import annotations

import json

import pytest

from animal_kingdom.bots.greedy_bot import GreedyWeights
from animal_kingdom.engine.cards import DECK_SLUGS
from animal_kingdom.sim.gauntlet import (
    GauntletResult, _load_weights, compare_gauntlets, run_gauntlet,
)

POOL = ["egg_control", "aggro_hq_rush"]


def test_run_gauntlet_default_pool_is_every_other_deck():
    result = run_gauntlet("ramp", 1, base_seed=0)
    assert "ramp" not in result.opponent_pool
    assert set(result.opponent_pool) == DECK_SLUGS - {"ramp"}


def test_run_gauntlet_shape():
    result = run_gauntlet("ramp", 2, base_seed=0, opponent_pool=POOL)
    assert result.deck == "ramp"
    assert result.opponent_pool == tuple(POOL)
    assert result.games_per_opponent == 2
    assert set(result.per_opponent_win_rate) == set(POOL)
    assert 0.0 <= result.overall_win_rate <= 1.0
    for rate in result.per_opponent_win_rate.values():
        assert 0.0 <= rate <= 1.0


def test_run_gauntlet_is_deterministic():
    a = run_gauntlet("ramp", 3, base_seed=0, opponent_pool=POOL)
    b = run_gauntlet("ramp", 3, base_seed=0, opponent_pool=POOL)
    assert a == b


def test_gauntlet_result_roundtrips_through_dict():
    result = run_gauntlet("ramp", 1, base_seed=0, opponent_pool=POOL)
    again = GauntletResult.from_dict(json.loads(json.dumps(result.to_dict())))
    assert again == result


def test_compare_gauntlets_computes_deltas_for_a_weight_change():
    # Full default pool + enough games for the weight change to reliably show up somewhere;
    # a 2-opponent/5-game sample was too small and landed on an exact-zero delta by chance.
    old = run_gauntlet("ramp", 10, base_seed=0)
    boosted = GreedyWeights(enemy_hq_threat=200.0)
    new = run_gauntlet("ramp", 10, base_seed=0, candidate_weights=boosted)

    diff = compare_gauntlets(old, new)
    assert diff["deck"] == "ramp"
    assert diff["overall_delta"] == pytest.approx(new.overall_win_rate - old.overall_win_rate)
    assert set(diff["per_opponent_delta"]) == set(old.opponent_pool)
    # A strongly HQ-threat-favouring candidate should actually change the outcome against
    # at least one opponent - otherwise the harness isn't sensitive to weight changes at all.
    assert any(delta != 0.0 for delta in diff["per_opponent_delta"].values())


def test_compare_gauntlets_rejects_mismatched_deck():
    a = run_gauntlet("ramp", 1, base_seed=0, opponent_pool=["egg_control"])
    b = run_gauntlet("aggro_hq_rush", 1, base_seed=0, opponent_pool=["egg_control"])
    with pytest.raises(ValueError):
        compare_gauntlets(a, b)


def test_run_gauntlet_accepts_lookahead_candidate_kind():
    # Small games/pool since lookahead search is meaningfully slower than plain greedy.
    result = run_gauntlet("ramp", 1, base_seed=0, opponent_pool=["egg_control"],
                          candidate_kind="lookahead")
    assert result.deck == "ramp"


def test_run_gauntlet_accepts_referee_candidate_kind():
    # Single game/opponent: the referee is ~100-200x slower per decision than greedy.
    result = run_gauntlet("ramp", 1, base_seed=0, opponent_pool=["egg_control"],
                          candidate_kind="referee")
    assert result.deck == "ramp"


def test_compare_gauntlets_rejects_mismatched_pool():
    a = run_gauntlet("ramp", 1, base_seed=0, opponent_pool=["egg_control"])
    b = run_gauntlet("ramp", 1, base_seed=0, opponent_pool=["aggro_hq_rush"])
    with pytest.raises(ValueError):
        compare_gauntlets(a, b)


# ------------------------------------------------------------------- _load_weights

def test_load_weights_none_path_returns_none():
    assert _load_weights(None) is None


def test_load_weights_applies_overrides(tmp_path):
    path = tmp_path / "weights.json"
    path.write_text(json.dumps({"food_progress": 5.0}))
    assert _load_weights(str(path)) == GreedyWeights(food_progress=5.0)


def test_load_weights_rejects_unknown_field(tmp_path):
    path = tmp_path / "weights.json"
    path.write_text(json.dumps({"not_a_real_field": 1.0}))
    with pytest.raises(SystemExit):
        _load_weights(str(path))
