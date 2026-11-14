"""The stars prototype (branch `stars`, 2026-11-14): a deck holds at most decks.STAR_BUDGET stars, counted per copy, a
card's level (-1 to 3) set in cards.json or its rarity's; the old caps (8 rare cards, 4 legendaries) are gone."""

from __future__ import annotations

import dataclasses
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

import pytest

from animal_kingdom.decks import DECK_SIZE, PREMADE_DECKS, STAR_BUDGET, deck_stars, decklist_problems
from animal_kingdom.engine.cards import COPY_LIMITS, STAR_DEFAULTS, CardDataError, load_cards, validate_card_record

CARDS = load_cards()
ROOT = Path(__file__).resolve().parents[2]


def _with_stars(levels: dict[str, int]) -> dict:
    """The card registry with some cards' levels changed (a card's other values stay)."""
    return {cid: dataclasses.replace(c, stars=levels[cid]) if cid in levels else c for cid, c in CARDS.items()}


def _pick(rarity: str, n: int, skip=()) -> list[str]:
    return [cid for cid, c in sorted(CARDS.items()) if c.collectible and c.rarity == rarity and c.stars == STAR_DEFAULTS[rarity]
            and cid not in skip][:n]


def _deck(legendaries: int, rares: int) -> list[str]:
    """A 30-card deck at the copy limits: `legendaries` legendaries, `rares` rare cards, commons for the rest."""
    deck = _pick("legendary", legendaries)
    deck += [cid for cid in _pick("rare", (rares + 1) // 2) for _ in range(2)][:rares]
    commons = DECK_SIZE - len(deck)
    deck += [cid for cid in _pick("common", (commons + 2) // 3) for _ in range(3)][:commons]
    assert len(deck) == DECK_SIZE
    return deck


def test_levels_default_from_rarity_and_the_budget_is_sixteen():
    assert STAR_DEFAULTS == {"common": 0, "rare": 1, "legendary": 2} and STAR_BUDGET == 16
    assert CARDS["lion"].stars == 0 and CARDS["lynx"].stars == 1 and CARDS["lion_legend_3"].stars == 2


def test_the_budget_counts_each_copy():
    deck = _deck(4, 8)
    assert deck_stars(deck, CARDS) == 4 * 2 + 8 * 1 == 16
    assert decklist_problems(deck) == []


def test_one_star_over_is_illegal_and_says_so():
    deck = _deck(4, 9)
    assert deck_stars(deck, CARDS) == 17
    assert decklist_problems(deck) == ["17 stars, over the 16 a deck may hold"]


def test_the_old_caps_are_gone_the_mix_is_a_choice():
    six_legends = _deck(6, 4)            # six legendaries: over the old cap of 4
    sixteen_rares = _deck(0, 16)         # sixteen rare cards: over the old cap of 8
    assert decklist_problems(six_legends) == [] and decklist_problems(sixteen_rares) == []


def test_a_minus_one_card_gives_a_star_back_per_copy():
    deck = _deck(4, 9)                                           # 17 stars
    small = next(cid for cid in deck if CARDS[cid].rarity == "common")
    cards = _with_stars({small: -1})
    assert deck_stars(deck, cards) == 17 - 3                     # its three copies give three back
    assert decklist_problems(deck, cards=cards) == []


def test_a_three_star_card_counts_three():
    deck = _deck(4, 8)
    big = next(cid for cid in deck if CARDS[cid].rarity == "legendary")
    cards = _with_stars({big: 3})
    assert deck_stars(deck, cards) == 17 and decklist_problems(deck, cards=cards)


def test_copy_limits_and_deck_size_still_hold():
    deck = _deck(0, 0)
    assert decklist_problems(deck[:-1])
    lynx4 = deck[:-4] + ["lynx"] * 4      # a rare's third copy: still too many though the stars fit
    assert any("Lynx" in p for p in decklist_problems(lynx4))
    assert COPY_LIMITS == {"common": 3, "rare": 2, "legendary": 1}


def _old_rules_problems(decklist) -> list[str]:
    """The deck rules as they were before the prototype: size, copies, collectible, 8 rare cards, 4 legendaries."""
    problems = [p for p in decklist_problems(decklist) if "stars" not in p]
    by = Counter(CARDS[c].rarity for c in decklist if c in CARDS)
    if by["rare"] > 8:
        problems.append("rares")
    if by["legendary"] > 4:
        problems.append("legendaries")
    return problems


def test_every_shipped_and_ladder_deck_legal_before_is_legal_now():
    legal_before = [slug for slug, d in PREMADE_DECKS.items() if not _old_rules_problems(d)]
    assert len(legal_before) > 20
    assert {slug: decklist_problems(PREMADE_DECKS[slug]) for slug in legal_before if decklist_problems(PREMADE_DECKS[slug])} == {}


def test_card_data_checks_the_range():
    rec = {"id": "x", "name": "X", "status": "reserve", "rarity": "common", "tags": [], "base_strength": 1}
    for ok in (-1, 0, 1, 2, 3):
        validate_card_record({**rec, "stars": ok})
    for bad in (-2, 4, "2", True, 1.5):
        with pytest.raises(CardDataError):
            validate_card_record({**rec, "stars": bad})


def test_the_server_hands_the_client_the_rules_and_each_cards_level():
    from animal_kingdom.web.match import card_pool
    pool = {c["id"]: c for c in card_pool()}
    assert pool["lion"]["stars"] == 0 and pool["lynx"]["stars"] == 1 and pool["lion_legend_3"]["stars"] == 2
    assert all(c["stars"] == 0 for c in pool.values() if c["status"] == "token")   # a token is in no deck


@pytest.fixture
def hq(tmp_path, monkeypatch):
    """tools/cards/hq.py working on copies of the card files."""
    sys.path.insert(0, str(ROOT / "tools" / "cards"))
    import hq as mod
    for name in ("CARDS", "DECKLISTS", "LEVELS"):
        src = getattr(mod, name)
        dst = tmp_path / src.name
        if src.exists():
            shutil.copy(src, dst)
        monkeypatch.setattr(mod, name, dst)
    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **k: None)   # no deck docs regenerated from the copy
    return mod


def _rec(hq, cid):
    return next(c for c in json.loads(hq.CARDS.read_text())["cards"] if c["id"] == cid)


def test_hq_sets_stars_in_range_and_stores_only_a_change(hq):
    hq.set_value("mouse", "stars", "-1", by="claude")
    assert _rec(hq, "mouse")["stars"] == -1
    assert next(r for r in hq.load()["rows"] if r["id"] == "mouse")["stars"] == -1
    hq.set_value("mouse", "stars", 0, by="claude")
    assert "stars" not in _rec(hq, "mouse")                       # back at its rarity's: nothing stored
    hq.set_value("tiger_legend", "stars", 3, by="claude")
    assert _rec(hq, "tiger_legend")["stars"] == 3
    for bad in ("4", "-2", "two"):
        with pytest.raises(hq.Refused):
            hq.set_value("mouse", "stars", bad, by="claude")
