"""The stars prototype (branch `stars`, 2026-11-14): a deck holds at most decks.STAR_BUDGET stars, counted per copy, a
card's level (0 to 3; none below ordinary, Martin 2026-11-15) set in cards.json or its recorded rarity's; the old caps (8 rare cards, 4 legendaries) are gone.
Commons and rares are one kind of card (Martin, 2026-11-15): two copies of any non-legendary, one of a legendary."""

from __future__ import annotations

import dataclasses
import json
import shutil
import sys
from pathlib import Path

import pytest

from animal_kingdom.decks import DECK_SIZE, PREMADE_DECKS, STAR_BUDGET, deck_stars, decklist_problems
from animal_kingdom.engine.cards import COPY_LIMITS, CardDataError, load_cards, validate_card_record
from animal_kingdom.engine.stars import STAR_DEFAULTS, merge_rarities

CARDS = load_cards()
ROOT = Path(__file__).resolve().parents[2]


def _with_stars(levels: dict[str, int]) -> dict:
    """The card registry with some cards' levels changed (a card's other values stay)."""
    return {cid: dataclasses.replace(c, stars=levels[cid]) if cid in levels else c for cid, c in CARDS.items()}


def _pick(stars: int, legendary: bool, n: int) -> list[str]:
    return [cid for cid, c in sorted(CARDS.items()) if c.collectible and (c.rarity == "legendary") == legendary and c.stars == stars][:n]


def _deck(legendaries: int, rares: int) -> list[str]:
    """A 30-card deck at the copy limits: `legendaries` legendaries, `rares` copies of one-star cards (the former rares),
    unmarked cards for the rest, two of each."""
    deck = _pick(2, True, legendaries)
    deck += [cid for cid in _pick(1, False, (rares + 1) // 2) for _ in range(2)][:rares]
    plain = DECK_SIZE - len(deck)
    deck += [cid for cid in _pick(0, False, (plain + 1) // 2) for _ in range(2)][:plain]
    assert len(deck) == DECK_SIZE
    return deck


def test_levels_default_from_rarity_and_the_budget_is_sixteen():
    assert STAR_DEFAULTS == {"common": 0, "rare": 1, "legendary": 2} and STAR_BUDGET == 20   # Martin, 2026-11-15
    assert CARDS["toad"].stars == 0 and CARDS["lynx"].stars == 1 and CARDS["lion_legend_3"].stars == 2


def test_commons_and_rares_are_one_kind_two_copies_each():
    assert COPY_LIMITS["common"] == 2 and COPY_LIMITS["legendary"] == 1
    assert {c.rarity for c in CARDS.values()} == {"common", "legendary"}, "a rare is read as a common"
    assert CARDS["lynx"].rarity == "common" and CARDS["lynx"].stars == 1, "a former rare keeps its star"
    raw = [{"id": "x", "rarity": "rare"}, {"id": "y", "rarity": "rare", "stars": 3}, {"id": "z", "rarity": "common"}]
    assert merge_rarities(raw) == [{"id": "x", "rarity": "common", "stars": 1}, {"id": "y", "rarity": "common", "stars": 3},
                                   {"id": "z", "rarity": "common", "stars": 0}]
    assert merge_rarities(merge_rarities(raw)) == merge_rarities(raw)
    assert raw[0] == {"id": "x", "rarity": "rare"}, "the records as recorded stay as they are"
    assert load_cards(as_played=False)["lynx"].rarity == "rare"     # the design docs read the recorded rarity


def test_a_third_copy_is_illegal_for_any_non_legendary():
    deck = _deck(4, 8)
    plain = next(cid for cid in deck if CARDS[cid].stars == 0)
    third = deck[:]
    third[third.index(next(c for c in deck if c != plain and CARDS[c].stars == 0))] = plain
    assert decklist_problems(third) == [f"at most 2 {CARDS[plain].name}"]


def test_the_budget_counts_each_copy():
    deck = _deck(4, 12)
    assert deck_stars(deck, CARDS) == 4 * 2 + 12 * 1 == STAR_BUDGET
    assert decklist_problems(deck) == []


def test_one_star_over_is_illegal_and_says_so():
    deck = _deck(4, 13)
    assert deck_stars(deck, CARDS) == 21
    assert decklist_problems(deck) == ["21 stars, over the 20 a deck may hold"]


def test_the_old_caps_are_gone_the_mix_is_a_choice():
    legends = [cid for cid, c in sorted(CARDS.items()) if c.collectible and c.rarity == "legendary"]
    while deck_stars(legends, CARDS) > 20:        # as many legendaries as the stars allow: drop the dearest
        legends.remove(max(legends, key=lambda cid: deck_stars([cid], CARDS)))
    six_legends = legends + [cid for cid in _pick(0, False, 10) for _ in range(2)][:DECK_SIZE - len(legends)]   # six legendaries: over the old cap of 4
    twenty_one_star = _deck(0, 20)         # twenty one-star cards: over the old cap of 8 rares
    assert decklist_problems(six_legends) == [] and decklist_problems(twenty_one_star) == []


def test_a_three_star_card_counts_three():
    deck = _deck(4, 12)
    big = next(cid for cid in deck if CARDS[cid].rarity == "legendary")
    cards = _with_stars({big: 3})
    assert deck_stars(deck, cards) == 21 and decklist_problems(deck, cards=cards)


def test_copy_limits_and_deck_size_still_hold():
    deck = _deck(0, 0)
    assert decklist_problems(deck[:-1])
    jaguar3 = deck[:-3] + ["jaguar"] * 3
    assert any("Jaguar" in p for p in decklist_problems(jaguar3))


def test_every_shipped_and_ladder_deck_is_legal_but_those_holding_cards_out_of_the_collection():
    """A deck holding a card since benched (a reserve card) was illegal before the prototype and stays so; every other
    deck, and the six pool decks (the bots' lists since 2026-11-16), fit the rules."""
    from animal_kingdom.decks import BOT_DECKS
    assert len(PREMADE_DECKS) > 30
    over = {slug: p for slug, d in PREMADE_DECKS.items() if (p := decklist_problems(d)) and not any("collectible" in x for x in p)}
    assert over == {}
    assert BOT_DECKS and all(not decklist_problems(PREMADE_DECKS[slug]) for slug in BOT_DECKS)


def test_card_data_checks_the_range():
    rec = {"id": "x", "name": "X", "status": "reserve", "rarity": "common", "tags": [], "base_strength": 1}
    for ok in (0, 1, 2, 3, 4):
        validate_card_record({**rec, "stars": ok})
    for bad in (-1, 5, "2", True, 1.5):
        with pytest.raises(CardDataError):
            validate_card_record({**rec, "stars": bad})


def test_the_server_hands_the_client_the_rules_and_each_cards_level():
    from animal_kingdom.web.match import card_pool
    pool = {c["id"]: c for c in card_pool()}
    assert pool["toad"]["stars"] == 0 and pool["lynx"]["stars"] == 1 and pool["lion_legend_3"]["stars"] == 2
    assert pool["lynx"]["rarity"] == "common"
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
    hq.set_value("mouse", "stars", "1", by="claude")
    assert _rec(hq, "mouse")["stars"] == 1
    assert next(r for r in hq.load()["rows"] if r["id"] == "mouse")["stars"] == 1
    hq.set_value("mouse", "stars", 0, by="claude")
    assert "stars" not in _rec(hq, "mouse")                       # back at its rarity's: nothing stored
    hq.set_value("tiger_legend", "stars", 3, by="claude")
    assert _rec(hq, "tiger_legend")["stars"] == 3
    for bad in ("5", "-1", "two"):
        with pytest.raises(hq.Refused):
            hq.set_value("mouse", "stars", bad, by="claude")
