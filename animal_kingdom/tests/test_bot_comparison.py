"""The full benchmark runs for most of a day: every finished deck must be on disk at once."""
from __future__ import annotations

import json
import os

import pytest

from animal_kingdom.sim.bot_comparison import run_all


class _Stop(Exception):
    pass


def test_a_finished_deck_is_written_before_the_run_ends(tmp_path):
    def stop_after_first(deck, done, total, result):
        raise _Stop(deck)

    with pytest.raises(_Stop) as stopped:
        run_all(1, 0, baseline_kind="greedy", candidate_kind="greedy", opponent_kind="greedy",
                out_dir=str(tmp_path), progress=stop_after_first)
    deck = str(stopped.value)
    summary = json.load(open(tmp_path / "summary.json"))
    assert summary["meta"]["decks_done"] == [deck] and deck in summary["per_deck"]
    assert os.path.exists(tmp_path / "logs" / f"{deck}-baseline.jsonl")
    assert os.path.exists(tmp_path / "logs" / f"{deck}-candidate.jsonl")
