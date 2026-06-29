"""M0 acceptance: the full card pool and Map A load and validate."""

from __future__ import annotations

import pytest

from animal_kingdom.engine.cards import (
    COPY_LIMITS,
    Card,
    CardDataError,
    KEYWORDS,
    load_cards,
    validate_card_record,
)
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.maps import (
    MapDataError,
    load_map,
    load_maps,
    validate_map_record,
)


# --------------------------------------------------------------------------- cards

def test_cards_load_full_pool():
    cards = load_cards()
    # 4 archetypes + 2 General + parked Rabbit, as listed in cards.md.
    assert len(cards) == 55
    assert all(isinstance(c, Card) for c in cards.values())


def test_every_card_has_valid_static_fields():
    cards = load_cards()
    for cid, c in cards.items():
        assert c.id == cid
        assert c.name
        assert c.rarity in COPY_LIMITS
        assert c.keywords <= KEYWORDS
        if c.is_dynamic:
            assert c.dynamic_strength in {"control_count", "discard_count", "chameleon"}
        else:
            assert isinstance(c.base_strength, int) and 0 <= c.base_strength <= 10


def test_known_cards_present_with_expected_data():
    cards = load_cards()
    assert cards["nile_crocodile"].is_dynamic
    assert cards["nile_crocodile"].dynamic_strength == "control_count"
    assert cards["anaconda"].dynamic_strength == "discard_count"
    assert cards["chameleon"].dynamic_strength == "chameleon"
    assert cards["matriarch_elephant"].has_keyword("Immovable")
    assert cards["egg"].has_keyword("Fragile")
    assert cards["golden_eagle"].has_keyword("Flight")
    assert cards["lion"].tag == "Cat"
    assert cards["honey_badger"].tag is None  # printed as '-'


def test_archetype_counts_match_docs():
    cards = load_cards()
    counts: dict[str, int] = {}
    for c in cards.values():
        counts[c.archetype] = counts.get(c.archetype, 0) + 1
    assert counts == {
        "aggro": 12,
        "control": 14,
        "combo": 13,
        "midrange": 13,
        "general": 2,
        "parking": 1,
    }


def test_duplicate_card_id_rejected():
    raw = {"cards": [
        {"id": "x", "name": "X", "archetype": "general", "rarity": "common", "tag": None, "base_strength": 1},
        {"id": "x", "name": "X2", "archetype": "general", "rarity": "common", "tag": None, "base_strength": 1},
    ]}
    with pytest.raises(CardDataError):
        load_cards(raw)


def test_bad_strength_rejected():
    raw = {"cards": [
        {"id": "x", "name": "X", "archetype": "general", "rarity": "common", "tag": None, "base_strength": 99},
    ]}
    with pytest.raises(CardDataError):
        load_cards(raw)


def test_validate_card_record_directly():
    good = {"id": "x", "name": "X", "archetype": "general", "rarity": "common",
            "tag": None, "base_strength": 3}
    validate_card_record(good)  # no raise
    with pytest.raises(CardDataError):
        validate_card_record({**good, "rarity": "mythic"})
    with pytest.raises(CardDataError):
        validate_card_record({**good, "base_strength": "dynamic"})  # missing dynamic_strength


def test_validate_false_skips_checks():
    # A record that would fail validation still builds when validation is skipped.
    bad_but_buildable = {"cards": [
        {"id": "x", "name": "X", "archetype": "general", "rarity": "mythic",
         "tag": None, "base_strength": 3},
    ]}
    cards = load_cards(bad_but_buildable, validate=False)
    assert cards["x"].rarity == "mythic"
    with pytest.raises(CardDataError):
        load_cards(bad_but_buildable)  # default validates and rejects


# ---------------------------------------------------------------------------- maps

def test_map_a_loads():
    m = load_map("map_a")
    assert m.name == "Savanna Crossing"
    assert len(m.crossroads) == 12
    assert m.win_food == 100


def test_map_a_topology():
    m = load_map("map_a")
    # 17 crossroad edges (9 horizontal + 8 vertical); HQ fronts are 3 + 3.
    assert len(m.edges) == 17
    assert m.hq_front("A") == frozenset({"1,1", "1,2", "1,3"})
    assert m.hq_front("B") == frozenset({"4,1", "4,2", "4,3"})
    # Adjacency is symmetric and matches the orthogonal grid.
    assert m.adjacent("2,2", "3,2")
    assert m.adjacent("3,2", "2,2")
    assert not m.adjacent("1,1", "2,2")  # diagonal, no edge
    assert m.neighbors("2,2") == frozenset({"1,2", "3,2", "2,1", "2,3"})


def test_map_a_regions():
    m = load_map("map_a")
    assert len(m.regions) == 6
    assert m.regions["R2"].food == 20
    assert m.regions["R5"].food == 20
    # Center regions higher than flanks.
    flanks = [m.regions[r].food for r in ("R1", "R3", "R4", "R6")]
    assert all(f == 10 for f in flanks)
    # Every region corner is a real crossroad.
    for region in m.regions.values():
        for cr in region.corners:
            assert cr in m.crossroads


def test_region_corner_must_exist():
    raw = {"maps": [{
        "id": "bad", "name": "Bad",
        "crossroads": ["1,1", "2,1"],
        "edges": [["1,1", "2,1"]],
        "hqs": {"A": {"connects": ["1,1"]}, "B": {"connects": ["2,1"]}},
        "regions": {"R1": {"corners": ["1,1", "9,9"], "food": 10}},
        "win_food": 100,
    }]}
    with pytest.raises(MapDataError):
        load_maps(raw)


def test_edge_to_unknown_crossroad_rejected():
    raw = {"maps": [{
        "id": "bad", "name": "Bad",
        "crossroads": ["1,1"],
        "edges": [["1,1", "2,2"]],
        "hqs": {"A": {"connects": ["1,1"]}, "B": {"connects": ["1,1"]}},
        "regions": {},
        "win_food": 100,
    }]}
    with pytest.raises(MapDataError):
        load_maps(raw)


def test_validate_map_record_directly():
    good = {
        "id": "m", "name": "M",
        "crossroads": ["1,1", "2,1"],
        "edges": [["1,1", "2,1"]],
        "hqs": {"A": {"connects": ["1,1"]}, "B": {"connects": ["2,1"]}},
        "regions": {"R1": {"corners": ["1,1", "2,1"], "food": 10}},
        "win_food": 100,
    }
    validate_map_record(good)  # no raise
    with pytest.raises(MapDataError):
        validate_map_record({**good, "win_food": 0})
    with pytest.raises(MapDataError):
        validate_map_record({**good, "edges": [["1,1", "1,1"]]})  # self-loop


# -------------------------------------------------------------------------- config

def test_config_defaults_and_sweep():
    cfg = Config.default()
    assert cfg.spotted_hyena_threshold == 4
    assert cfg.raven_cost == 12
    swept = cfg.sweep(spotted_hyena_threshold=5)
    assert swept.spotted_hyena_threshold == 5
    assert cfg.spotted_hyena_threshold == 4  # original unchanged (frozen)
