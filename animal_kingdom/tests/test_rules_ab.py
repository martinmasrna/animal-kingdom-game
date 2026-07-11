"""Tests for the rule/config A/B simulation helper."""

from __future__ import annotations

import json

from animal_kingdom.engine.config import Config
from animal_kingdom.sim.rules_ab import (
    Arm,
    deck_deltas,
    format_ab_summary,
    matchup_deltas,
    write_ab_artifacts,
)
from animal_kingdom.sim.runner import GameRecord


def test_deck_deltas_compare_field_win_rates_from_each_decks_perspective():
    control = [
        GameRecord("ramp", "egg_control", 0, "A", "A", "food", 10),
        GameRecord("ramp", "egg_control", 1, "B", "B", "food", 10),
    ]
    treatment = [
        GameRecord("ramp", "egg_control", 0, "A", "A", "food", 10),
        GameRecord("ramp", "egg_control", 1, "B", "A", "food", 10),
    ]

    rows = {row.deck: row for row in deck_deltas(control, treatment)}

    assert rows["ramp"].control_win_rate == 0.5
    assert rows["ramp"].treatment_win_rate == 1.0
    assert rows["ramp"].delta == 0.5
    assert rows["egg_control"].delta == -0.5


def test_matchup_deltas_include_both_matrix_directions():
    control = [
        GameRecord("ramp", "egg_control", 0, "A", "A", "food", 10),
        GameRecord("ramp", "egg_control", 1, "B", "B", "food", 10),
    ]
    treatment = [
        GameRecord("ramp", "egg_control", 0, "A", "A", "food", 10),
        GameRecord("ramp", "egg_control", 1, "B", "A", "food", 10),
    ]

    rows = {(row["deck_a"], row["deck_b"]): row for row in matchup_deltas(control, treatment)}

    assert rows[("ramp", "egg_control")]["delta"] == 0.5
    assert rows[("egg_control", "ramp")]["delta"] == -0.5


def test_write_ab_artifacts_creates_arm_metrics_and_summary(tmp_path):
    control_arm = Arm("control_draw1", Config.default())
    treatment_arm = Arm("treatment_draw2", Config.default().sweep(draw_action_count=2))
    control = [GameRecord("ramp", "egg_control", 0, "A", "A", "food", 10)]
    treatment = [GameRecord("ramp", "egg_control", 0, "A", "B", "hq_capture", 8)]

    summary = write_ab_artifacts(
        str(tmp_path),
        control=control_arm,
        treatment=treatment_arm,
        control_records=control,
        treatment_records=treatment,
        games_per_matchup=1,
        seed=123,
        bots=("greedy", "greedy"),
        map_id="map_b",
    )

    assert (tmp_path / "control_draw1" / "matchup_matrix.csv").exists()
    assert (tmp_path / "treatment_draw2" / "summary.json").exists()
    assert (tmp_path / "deck_delta.csv").exists()
    assert (tmp_path / "matchup_delta.csv").exists()
    saved = json.loads((tmp_path / "summary.json").read_text())
    assert saved["treatment"]["config"]["draw_action_count"] == 2
    assert saved["seed"] == 123
    assert summary["games_per_arm"] == {"control": 1, "treatment": 1}
    assert "First-player WR" in format_ab_summary(summary)
