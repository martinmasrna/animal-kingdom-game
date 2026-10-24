"""Archetypes by shared cards (league/archetypes.py), and Martin's grouping on file names only real lists."""

import json
from pathlib import Path

from animal_kingdom.league.archetypes import archetypes


def test_close_lists_share_an_archetype_and_far_ones_do_not():
    a = ["lion"] * 3 + ["tiger"] * 3 + [f"c{i}" for i in range(24)]
    b = a[:-6] + [f"d{i}" for i in range(6)]        # 24 of 30 shared: same archetype, another variant
    c = [f"e{i}" for i in range(30)]
    out = archetypes({"a": a, "b": b, "c": c})
    assert sorted(map(sorted, (x["lists"] for x in out))) == [["a", "b"], ["c"]]
    assert len(next(x for x in out if "a" in x["lists"])["variants"]) == 2


def test_martins_archetypes_name_each_list_once():
    data = json.loads((Path(__file__).resolve().parents[1] / "data" / "archetypes.json").read_text())
    lists = [s for a in data["archetypes"] for s in a["lists"]]
    assert len(lists) == len(set(lists)) and all(a["name"] for a in data["archetypes"])
