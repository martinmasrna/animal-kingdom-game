"""M3 tests for the simulation harness: runner determinism + metrics aggregation.

Uses RandomBot (fast, still seed-deterministic) so the suite stays quick.
"""

from __future__ import annotations

import json
import os

from animal_kingdom.sim import metrics
from animal_kingdom.sim.runner import (
    GameRecord, make_bot, play_game, run_matchup, run_round_robin,
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


def test_matchup_is_deterministic():
    a = run_matchup("ramp", "egg_control", 3, base_seed=0, bots=("random", "random"))
    b = run_matchup("ramp", "egg_control", 3, base_seed=0, bots=("random", "random"))
    assert a == b


def test_parallel_matches_serial():
    slugs = ["ramp", "aggro_hq_rush"]
    serial = run_round_robin(slugs, 2, base_seed=0, bots=("random", "random"), jobs=1)
    parallel = run_round_robin(slugs, 2, base_seed=0, bots=("random", "random"), jobs=2)
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


def test_per_card_winrate_delta_shape():
    rows = metrics.per_card_winrate_delta(_records())
    assert rows                                    # non-empty
    keys = set(rows[0])
    assert keys == {"card_id", "games", "win_rate", "delta"}
    assert rows == sorted(rows, key=lambda r: r["win_rate"], reverse=True)


def test_write_all_emits_bundle(tmp_path):
    summary = metrics.write_all(_records(), str(tmp_path))
    for name in ("matchup_matrix.csv", "per_card_winrate.csv", "summary.json"):
        assert os.path.exists(tmp_path / name)
    saved = json.loads((tmp_path / "summary.json").read_text())
    assert saved["games"] == 3
    assert "caveat" in saved and saved["caveat"]
