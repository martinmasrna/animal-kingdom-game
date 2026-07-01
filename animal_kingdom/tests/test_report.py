"""Tests for the per-card balance report's formatting logic (animal_kingdom.sim.report)."""

from __future__ import annotations

from animal_kingdom.decks import load_premade_deck
from animal_kingdom.engine.cards import load_cards
from animal_kingdom.sim.report import format_matrix, format_report
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
    assert "egg_ = egg_control" in matrix  # legend spells the abbreviation out


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
