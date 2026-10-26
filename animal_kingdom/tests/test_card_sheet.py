"""The sheet (tools/cards/check.py) prints its facts for an existing card and for a proposed one, without a browser."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CHECK = ROOT / "tools" / "cards" / "check.py"
pytestmark = pytest.mark.skipif(not CHECK.is_file(), reason="the deploy image ships no tools/cards")
SECTIONS = ["card", "keywords", "pool", "anchors", "record", "grid", "text", "play"]


def sheet(*args: str) -> str:
    r = subprocess.run([sys.executable, str(CHECK), *args, "--no-fit"], capture_output=True, text=True, cwd=ROOT, timeout=120)
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_existing_card_sheet_has_every_section_and_plays():
    out = sheet("mouse", "--play")
    for s in SECTIONS:
        assert any(line.startswith(s) for line in out.splitlines()), s
    assert "Rodent (" in out                      # the family listed
    assert "Draw anchors" in out                  # the anchor for its verb
    assert "neighbours" in out                    # the grid
    assert "placed on" in out and "Mouse(A)4" in out   # the scratch placement happened and the board shows it


def test_proposed_card_sheet_reads_terms_and_counts_neighbours():
    out = sheet("--new", "Rat", "--rarity", "C", "--str", "3", "--tag", "Rodent",
                "--text", "Has +2 strength for each adjacent allied Rodent.")
    assert "Strength modifiers" in out            # "has +" is read from the registry
    assert "at most 11" in out and "at most 7" in out   # centre 4 neighbours, corner 2
    assert "rat (collectible)" in out             # the animal is already in the pool
    assert "not in the engine" in out             # a proposal can't be played
