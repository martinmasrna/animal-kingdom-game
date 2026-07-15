"""Tests for the card-power benchmark rig's folding + checkpoint identity.

The rig's load-bearing property: one game scores BOTH seats. The games are the expensive part
(referee search), so a run must never have to be repeated just to read the other seat.
"""

from __future__ import annotations

import json
import os

import pytest

from animal_kingdom.decks import PREMADE_DECKS
from animal_kingdom.sim import benchmark_set as bs
from animal_kingdom.sim import deck_optimizer
from animal_kingdom.sim.runner import GameRecord


@pytest.fixture(autouse=True)
def restore_deck_registry():
    """`main()` publishes the synthetic 'baseline' deck into process-global state (PREMADE_DECKS +
    $AK_EXTRA_DECKS, for spawned workers). Undo it, or test_pool's PREMADE_DECKS == DECK_SLUGS
    invariant fails depending on test order."""
    decks = dict(PREMADE_DECKS)
    synth = dict(deck_optimizer._SYNTHETIC_DECKS)
    env = os.environ.get("AK_EXTRA_DECKS")
    yield
    PREMADE_DECKS.clear()
    PREMADE_DECKS.update(decks)
    deck_optimizer._SYNTHETIC_DECKS.clear()
    deck_optimizer._SYNTHETIC_DECKS.update(synth)
    if env is None:
        os.environ.pop("AK_EXTRA_DECKS", None)
    else:
        os.environ["AK_EXTRA_DECKS"] = env


def _rec(winner, drawn_a=(), drawn_b=()):
    return GameRecord("baseline", "cats_midrange", 0, "A", winner, "food", 10,
                      frozenset(drawn_a), frozenset(drawn_b))


def test_fold_scores_both_seats_from_the_same_games():
    recs = [_rec("A", ["lion"], ["tiger"]), _rec("B", ["lion"], ["tiger"])]
    agg = bs._fold(recs)
    assert set(agg) == {"A", "B"}
    assert agg["A"]["n"] == agg["B"]["n"] == 2
    # both seats saw every game, and the credit splits between them
    assert agg["A"]["credit"] == 1.0 and agg["B"]["credit"] == 1.0
    assert agg["A"]["cards"]["lion"] == [1.0, 2]
    assert agg["B"]["cards"]["tiger"] == [1.0, 2]


def test_fold_keeps_each_seats_cards_separate():
    agg = bs._fold([_rec("A", ["lion"], ["tiger"])])
    assert "tiger" not in agg["A"]["cards"]
    assert "lion" not in agg["B"]["cards"]


def test_fold_credits_a_draw_to_both_seats():
    agg = bs._fold([_rec(None, ["lion"], ["tiger"])])
    assert agg["A"]["credit"] == 0.5 and agg["B"]["credit"] == 0.5
    assert agg["A"]["cards"]["lion"] == [0.5, 1]


def test_fold_only_counts_a_card_in_games_it_was_drawn():
    recs = [_rec("A", ["lion"], []), _rec("B", [], [])]
    agg = bs._fold(recs)
    assert agg["A"]["cards"]["lion"] == [1.0, 1]  # drawn once, won that one
    assert agg["A"]["n"] == 2


def test_report_mode_is_not_part_of_the_run_identity(tmp_path, monkeypatch):
    """--report picks what's printed; it must not fork the checkpoint or the games."""
    ckpt = tmp_path / "x.ckpt.json"
    args = ["--pilot", "random", "--games", "1", "--field", "cats_midrange",
            "--checkpoint", str(ckpt)]
    bs.main(args + ["--report", "self"])
    key = json.loads(ckpt.read_text())["run_key"]
    assert "measure" not in key and "report" not in key
    # a differing --report resumes the same checkpoint rather than re-running
    bs.main(args + ["--report", "opponent"])
    assert json.loads(ckpt.read_text())["run_key"] == key


def test_v1_checkpoint_is_refused_rather_than_misread(tmp_path):
    """v1 stored one seat; silently treating it as v2 would fabricate the missing seat."""
    ckpt = tmp_path / "old.ckpt.json"
    ckpt.write_text(json.dumps({
        "run_key": {"pilot": "random", "games": 1, "base_seed": 715000,
                    "field": ["cats_midrange"], "deck": bs.DECKLIST, "config": "None",
                    "measure": "self"},
        "matchups": {"cats_midrange": {"n": 2, "credit": 1.0, "cards": {"lion": [1.0, 2]}}},
    }))
    with pytest.raises(SystemExit, match="one seat only"):
        bs.main(["--pilot", "random", "--games", "1", "--field", "cats_midrange",
                 "--checkpoint", str(ckpt)])
