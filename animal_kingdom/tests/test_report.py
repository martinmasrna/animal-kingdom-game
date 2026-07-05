"""Tests for the per-card balance report's formatting logic (animal_kingdom.sim.report)."""

from __future__ import annotations

import pytest

from animal_kingdom.decks import load_premade_deck
from animal_kingdom.engine.cards import DECK_SLUGS, load_cards
from animal_kingdom.sim import report as report_module
from animal_kingdom.sim.report import (
    _crossed_progress_decile,
    _resolve_deck,
    format_focused_matrix,
    format_matrix,
    format_report,
)
from animal_kingdom.sim.runner import GameRecord


def test_format_matrix_shows_each_deck_and_its_win_rate():
    records = [
        GameRecord("ramp", "egg_control", 0, "A", "A", "hq_capture", 10),
        GameRecord("egg_control", "ramp", 1, "A", "B", "food", 20),
    ]
    matrix = format_matrix(records)

    assert "### Matchup matrix" in matrix
    assert "ramp" in matrix and "egg_" in matrix  # row label + column abbreviation
    assert "100%" in matrix  # ramp beat egg_control every time it was seat A
    assert "egg_ = egg_control" not in matrix  # legend dropped

    # ramp went 1-0 as A and 1-0 as B (it won both recorded games) -> TotA/Both both 100%.
    ramp_line = next(line for line in matrix.splitlines() if line.startswith("ramp"))
    assert "TotA" in matrix and "Both" in matrix
    assert ramp_line.count("100%") == 3  # vs egg_control, TotA, Both

    tot_b_line = next(line for line in matrix.splitlines() if line.startswith("TotB"))
    assert "100%" in tot_b_line  # ramp's average win rate as seat B (from the 2nd record)


def test_format_report_leads_with_the_matrix():
    records = [GameRecord("ramp", "egg_control", 0, "A", "A", "hq_capture", 10)]
    report = format_report(records, load_cards())
    assert report.index("### Matchup matrix") < report.index("### egg_control")


def test_format_report_groups_by_deck_sorted_by_impact():
    ramp = load_premade_deck("ramp")
    good, bad = ramp[0], ramp[1]
    records = [
        GameRecord("ramp", "egg_control", 0, "A", "A", "hq_capture", 10,
                  cards_drawn_a=frozenset({good})),
        GameRecord("ramp", "egg_control", 1, "A", "B", "food", 20,
                  cards_drawn_a=frozenset({bad})),
    ]
    report = format_report(records, load_cards())

    assert "### egg_control" in report
    assert "### ramp" in report
    # `good` (drawn only in the win) must appear before `bad` (drawn only in the loss).
    ramp_section = report.split("### ramp")[1]
    assert ramp_section.index(good) < ramp_section.index(bad)
    # every card line is prefixed with a rarity marker.
    assert "\U0001F7E1" in report or "\U0001F535" in report or "⚪" in report


def test_resolve_deck_matches_exact_and_abbreviation():
    slugs = sorted(DECK_SLUGS)
    assert _resolve_deck("aggro_hq_rush", slugs) == "aggro_hq_rush"
    assert _resolve_deck("aggro", slugs) == "aggro_hq_rush"


def test_resolve_deck_rejects_no_match_or_ambiguous_match():
    slugs = sorted(DECK_SLUGS)
    with pytest.raises(SystemExit):
        _resolve_deck("zzz", slugs)
    with pytest.raises(SystemExit):
        _resolve_deck("ca", slugs)          # matches both canine_buff_tempo and cats_midrange


def test_format_focused_matrix_shows_both_seats_for_each_opponent():
    records = [
        GameRecord("ramp", "egg_control", 0, "A", "A", "hq_capture", 10),   # ramp (A) beats egg (B)
        GameRecord("egg_control", "ramp", 1, "A", "A", "hq_capture", 10),   # egg (A) beats ramp (B)
        GameRecord("ramp", "ramp", 2, "A", "A", "hq_capture", 10),          # mirror
    ]
    matrix = format_focused_matrix(records, "ramp")

    assert "### ramp matchups" in matrix
    assert "ramp (mirror)" in matrix
    assert "cats_midrange" not in matrix        # never played, shouldn't appear as a row
    # ramp went 1-0 as seat A and 0-1 as seat B against egg_control.
    egg_line = next(line for line in matrix.splitlines() if line.startswith("egg_control"))
    assert "100%" in egg_line and "0%" in egg_line


def test_format_report_with_focus_deck_only_prints_that_decks_table():
    records = [GameRecord("ramp", "egg_control", 0, "A", "A", "hq_capture", 10)]
    report = format_report(records, load_cards(), focus_deck="ramp")
    assert "### ramp matchups" in report
    assert "### ramp (deck win rate" in report
    assert "### egg_control" not in report
    assert "### Matchup matrix" not in report


def test_progress_deciles_scale_with_matchup_size():
    assert [done for done in range(1, 201) if _crossed_progress_decile(done, 200)] == [
        20, 40, 60, 80, 100, 120, 140, 160, 180, 200,
    ]
    assert [done for done in range(1, 96) if _crossed_progress_decile(done, 95)] == [
        10, 19, 29, 38, 48, 57, 67, 76, 86, 95,
    ]
    assert [done for done in range(1, 6) if _crossed_progress_decile(done, 5)] == [
        1, 2, 3, 4, 5,
    ]


def test_report_cli_prints_game_progress_and_completed_matchup_win_rates(monkeypatch, capsys):
    records = [
        GameRecord("ramp", "ramp", 0, "A", "A", "food", 10),
        GameRecord("ramp", "ramp", 1, "A", "A", "food", 10),
        GameRecord("ramp", "ramp", 2, "A", "B", "food", 10),
        GameRecord("ramp", "ramp", 3, "A", "B", "food", 10),
        GameRecord("ramp", "ramp", 4, "A", None, "max_turns", 10),
    ]

    def fake_run_pairs(pairs, n_games, base_seed, **kwargs):
        for done in range(1, n_games + 1):
            kwargs["game_progress"]("ramp", "ramp", done, n_games)
        kwargs["matchup_progress"]("ramp", "ramp", 1, 1, records)
        return records

    monkeypatch.setattr(report_module, "run_pairs", fake_run_pairs)
    report_module.main(["5", "--deck", "ramp", "--opponent", "ramp"])

    output = capsys.readouterr().err
    assert "[ 20%] ramp vs ramp | 1/5 games" in output
    assert "[ 40%] ramp vs ramp | 2/5 games" in output
    assert "[100%] ramp vs ramp | 5/5 games" in output
    assert "=== MATCHUP 1/1 COMPLETE === ramp vs ramp" in output
    assert "WR A=50.0%, B=50.0%, draws=20.0%" in output
    banner_start = output.index("  === MATCHUP 1/1 COMPLETE ===")
    banner_end = output.index("\n", banner_start)
    assert output[banner_start - 2:banner_start] == "\n\n"
    assert output[banner_end:banner_end + 2] == "\n\n"


def test_unified_cli_files_mode_accepts_legacy_arguments(monkeypatch, tmp_path, capsys):
    records = [GameRecord("ramp", "ramp", 0, "A", "A", "food", 10)]
    writes = []

    monkeypatch.setattr(report_module, "DECK_SLUGS", ("ramp",))
    monkeypatch.setattr(report_module, "run_pairs", lambda *args, **kwargs: records)
    monkeypatch.setattr(
        report_module.metrics,
        "write_all",
        lambda received, out: writes.append((received, out)) or {
            "games": 1,
            "win_condition_split": {"percent": {"food": 1.0}},
            "first_player_win_rate": {"rate": 1.0},
            "avg_game_length": {"overall": 10.0},
            "caveat": "test",
        },
    )
    monkeypatch.setattr(
        report_module,
        "format_report",
        lambda *args, **kwargs: pytest.fail("files mode must not render a report"),
    )

    report_module.main([
        "--decks", "all",
        "--games", "1",
        "--format", "files",
        "--out", str(tmp_path),
    ])

    assert writes == [(records, str(tmp_path))]
    assert f"Wrote 1 games to {tmp_path}/" in capsys.readouterr().out
