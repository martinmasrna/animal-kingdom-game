"""M3 tests for the simulation harness: runner determinism + metrics aggregation.

Uses RandomBot (fast, still seed-deterministic) so the suite stays quick.
"""

from __future__ import annotations

import json
import os

import pytest

from animal_kingdom.bots.greedy_bot import GreedyWeights
from animal_kingdom.decks import load_premade_deck
from animal_kingdom.sim import metrics
from animal_kingdom.sim.runner import (
    GameRecord, make_bot, play_game, run_matchup, run_pairs, run_round_robin,
)

REASONS = {"hq_capture", "food", "exhaustion", "max_turns"}


# ---------------------------------------------------------------------- runner

def test_play_game_returns_a_complete_record():
    rec = play_game("ramp", "aggro_hq_rush", 0,
                    bot_a=make_bot("random", 1), bot_b=make_bot("random", 2))
    assert rec.deck_a == "ramp" and rec.deck_b == "aggro_hq_rush"
    assert rec.winner in ("A", "B", None)
    assert rec.reason in REASONS
    assert rec.first_player in ("A", "B")
    assert rec.turns > 0


def test_play_game_tracks_drawn_cards_end_to_end():
    rec = play_game("ramp", "aggro_hq_rush", 0,
                    bot_a=make_bot("random", 1), bot_b=make_bot("random", 2))
    assert rec.cards_drawn_a and rec.cards_drawn_b   # opening hand alone guarantees non-empty
    assert rec.cards_drawn_a <= set(load_premade_deck("ramp"))
    assert rec.cards_drawn_b <= set(load_premade_deck("aggro_hq_rush"))


def test_matchup_is_deterministic():
    a = run_matchup("ramp", "egg_control", 3, base_seed=0, bots=("random", "random"))
    b = run_matchup("ramp", "egg_control", 3, base_seed=0, bots=("random", "random"))
    assert a == b


def test_parallel_matches_serial():
    slugs = ["ramp", "aggro_hq_rush"]
    serial = run_round_robin(slugs, 2, base_seed=0, bots=("random", "random"), jobs=1)
    parallel = run_round_robin(slugs, 2, base_seed=0, bots=("random", "random"), jobs=2)
    assert serial == parallel


def test_run_round_robin_delegates_to_run_pairs():
    # run_round_robin should just be run_pairs over the full (slug x slug) cross product.
    slugs = ["ramp", "aggro_hq_rush"]
    via_round_robin = run_round_robin(slugs, 2, base_seed=0, bots=("random", "random"))
    pairs = [(a, b) for a in slugs for b in slugs]
    via_pairs = run_pairs(pairs, 2, base_seed=0, bots=("random", "random"))
    assert via_round_robin == via_pairs


# ------------------------------------------------------- weight-injection plumbing

def test_make_bot_applies_custom_weights():
    custom = GreedyWeights(food_progress=99.0)
    bot = make_bot("greedy", seed=1, weights=custom)
    assert bot.weights == custom


def test_make_bot_defaults_weights_when_omitted():
    bot = make_bot("greedy", seed=1)
    assert bot.weights == GreedyWeights()


def test_make_bot_lookahead_kind_uses_deeper_search():
    bot = make_bot("lookahead", seed=1)
    assert bot.depth > 1


def test_run_matchup_threads_weights_and_stays_deterministic():
    custom = GreedyWeights(food_progress=99.0, food_proximity=0.0, board_presence=0.0,
                           connection=0.0, region_control=0.0, enemy_hq_threat=0.0,
                           own_hq_threat=0.0, card_economy=0.0)
    a = run_matchup("ramp", "egg_control", 3, base_seed=0, bots=("greedy", "greedy"),
                    weights=(custom, None))
    b = run_matchup("ramp", "egg_control", 3, base_seed=0, bots=("greedy", "greedy"),
                    weights=(custom, None))
    assert a == b


def test_run_pairs_parallel_matches_serial_with_weights():
    # Custom GreedyWeights must survive the ProcessPoolExecutor round-trip (picklability).
    custom = GreedyWeights(enemy_hq_threat=999.0)
    pairs = [("ramp", "aggro_hq_rush"), ("aggro_hq_rush", "ramp")]
    serial = run_pairs(pairs, 2, base_seed=0, bots=("greedy", "greedy"),
                       weights=(custom, None), jobs=1)
    parallel = run_pairs(pairs, 2, base_seed=0, bots=("greedy", "greedy"),
                         weights=(custom, None), jobs=2)
    assert serial == parallel


# --------------------------------------------------------------------- metrics

def _records():
    # Hand-built records over two real deck slugs to exercise aggregation precisely.
    return [
        GameRecord("ramp", "egg_control", 0, "A", "A", "hq_capture", 10),
        GameRecord("ramp", "egg_control", 1, "A", "B", "food", 20),   # second player wins
        GameRecord("egg_control", "ramp", 2, "A", None, "max_turns", 400),  # draw
    ]


def test_matchup_matrix_shape_and_values():
    m = metrics.matchup_matrix(_records())
    assert m["decks"] == ["egg_control", "ramp"]
    assert m["win_rate"]["ramp"]["egg_control"] == 0.5      # one A-win, one B-win
    assert m["win_rate"]["egg_control"]["ramp"] == 0.5      # the single draw = half


def test_win_condition_split_sums_to_one():
    split = metrics.win_condition_split(_records())
    assert split["total"] == 3
    assert abs(sum(split["percent"].values()) - 1.0) < 1e-9
    assert split["counts"]["hq_capture"] == 1


def test_first_player_win_rate_excludes_draws():
    fp = metrics.first_player_win_rate(_records())
    assert fp["decided_games"] == 2          # the max_turns draw is excluded
    assert fp["first_player_wins"] == 1      # game 0: first=A, winner=A
    assert fp["rate"] == 0.5


def test_avg_game_length():
    avg = metrics.avg_game_length(_records())
    assert avg["overall"] == (10 + 20 + 400) / 3


def test_per_card_stats_shape():
    rows = metrics.per_card_stats(_records())
    assert rows                                    # non-empty
    keys = set(rows[0])
    assert keys == {"card_id", "deck", "games", "draw_rate",
                    "win_rate_when_drawn", "deck_win_rate", "impact"}


def test_per_card_stats_differentiates_drawn_vs_never_drawn():
    deck = load_premade_deck("ramp")
    always_drawn, never_drawn = deck[0], deck[1]
    assert always_drawn != never_drawn
    records = [
        GameRecord("ramp", "egg_control", 0, "A", "A", "hq_capture", 10,
                  cards_drawn_a=frozenset({always_drawn})),
        GameRecord("ramp", "egg_control", 1, "A", "A", "hq_capture", 12,
                  cards_drawn_a=frozenset({always_drawn})),
        GameRecord("ramp", "egg_control", 2, "A", "B", "food", 20,
                  cards_drawn_a=frozenset()),
    ]
    rows = {r["card_id"]: r for r in metrics.per_card_stats(records)}

    never = rows[never_drawn]
    assert never["draw_rate"] == 0.0
    assert never["win_rate_when_drawn"] is None
    assert never["impact"] is None

    always = rows[always_drawn]
    assert always["draw_rate"] == pytest.approx(2 / 3, abs=1e-4)
    assert always["win_rate_when_drawn"] == 1.0                # won both games it was drawn in
    assert always["deck_win_rate"] == pytest.approx(2 / 3, abs=1e-4)  # 2/3 wins for ramp
    assert always["impact"] == pytest.approx(1.0 - 2 / 3, abs=1e-4)


def test_per_card_stats_sorted_by_impact_desc():
    deck = load_premade_deck("ramp")
    good, bad = deck[0], deck[1]
    records = [
        GameRecord("ramp", "egg_control", 0, "A", "A", "hq_capture", 10,
                  cards_drawn_a=frozenset({good})),
        GameRecord("ramp", "egg_control", 1, "A", "B", "food", 20,
                  cards_drawn_a=frozenset({bad})),
    ]
    rows = metrics.per_card_stats(records)
    impacts = [r["impact"] for r in rows if r["impact"] is not None]
    assert impacts == sorted(impacts, reverse=True)
    good_row = next(r for r in rows if r["card_id"] == good)
    bad_row = next(r for r in rows if r["card_id"] == bad)
    assert rows.index(good_row) < rows.index(bad_row)


def test_write_all_emits_bundle(tmp_path):
    summary = metrics.write_all(_records(), str(tmp_path))
    for name in ("matchup_matrix.csv", "per_card_stats.csv", "summary.json"):
        assert os.path.exists(tmp_path / name)
    saved = json.loads((tmp_path / "summary.json").read_text())
    assert saved["games"] == 3
    assert "caveat" in saved and saved["caveat"]
