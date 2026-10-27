"""Structural tests for the launch pool: 12 starter decks, lists over the collectible cards (decklists.json).

These assert the *shape* of the static data (counts, uniqueness, domains) — not card behavior, which is Phase 2. A
starter has no fixed rarity split: any legal deck will do (Martin, 2026-10-22).
"""

from __future__ import annotations

from animal_kingdom.engine.cards import (
    COPY_LIMITS,
    DECKLISTS,
    DECK_SLUGS,
    DYNAMIC_STRENGTHS,
    KEYWORDS,
    STARTER_DECKS,
    TAGS,
    load_cards,
)
from animal_kingdom.decks import BOT_DECKS, PREMADE_DECKS, load_premade_deck

RETIRED_TAGS = {"Reptile", "Insect"}
DYNAMIC_IDS = {"egg_eater"}


# ----------------------------------------------------------------- pool composition

def test_12_starter_decks_of_collectible_cards():
    cards = load_cards()
    assert len(STARTER_DECKS) == 12 and DECK_SLUGS == {d["slug"] for d in STARTER_DECKS}
    for d in STARTER_DECKS:
        assert all(cards[cid].collectible for cid in d["cards"])
        assert d.get("cover") in d["cards"], f"{d['slug']}: its cover is not one of its cards"


def test_starter_decks_share_no_card():
    # A new player meets as many cards as possible: no card ships in two starter decks (Martin, 2026-10-19). Bot decks
    # are free to overlap with anything.
    seen: dict[str, str] = {}
    for d in STARTER_DECKS:
        for cid in d["cards"]:
            assert cid not in seen, f"{cid} ships in both {seen[cid]} and {d['slug']}"
            seen[cid] = d["slug"]


def test_shipped_slugs_are_unique_and_the_bots_play_shipped_decks():
    # Legality isn't held here: a card change may leave a deck illegal until the decks' pass before shipping; the loader
    # warns about it (decks.shipped_problems) and the deck still plays (Martin, 2026-10-27).
    slugs = [d["slug"] for d in DECKLISTS]
    assert len(set(slugs)) == len(slugs)
    assert set(BOT_DECKS) <= set(PREMADE_DECKS) and BOT_DECKS


def test_ids_and_names_globally_unique():
    cards = load_cards()
    # Every id in the registry is unique, and so is every name a player can collect: an unnamed legendary shows its
    # species meanwhile (the Wolf beside the common Wolf), and tokens and the tutorial's cards share their animals' names.
    ids = [c.id for c in cards.values()]
    assert len(set(ids)) == len(ids) == len(cards)
    names = [c.name for c in cards.values() if not c.unnamed and c.status not in ("token", "tutorial")]
    assert len(set(names)) == len(names)


def test_each_deck_expands_to_30():
    for slug in DECK_SLUGS:
        deck = load_premade_deck(slug)
        assert len(deck) == 30, f"{slug} expands to {len(deck)}"
    assert DECK_SLUGS <= PREMADE_DECKS.keys()


def test_copy_limits():
    assert COPY_LIMITS == {"legendary": 1, "rare": 2, "common": 3}


# ------------------------------------------------------------------ field domains

def test_dynamic_strength_present_iff_dynamic_and_only_goliath():
    cards = load_cards()
    dynamic = set()
    for c in cards.values():
        if c.is_dynamic:
            dynamic.add(c.id)
            assert c.dynamic_strength in DYNAMIC_STRENGTHS
        else:
            assert c.dynamic_strength is None
            assert isinstance(c.base_strength, int) and c.base_strength >= 0
    assert dynamic == DYNAMIC_IDS


def test_keywords_and_tags_within_allowed_sets_no_retired_tags():
    for c in load_cards().values():
        assert c.keywords <= KEYWORDS
        assert c.tags <= TAGS
        assert not (c.tags & RETIRED_TAGS)


def test_food_cost_present_only_where_text_says_costs():
    for c in load_cards().values():
        has_cost = c.food_cost > 0
        says_costs = "Costs" in c.text
        assert has_cost == says_costs, f"{c.id}: food_cost={c.food_cost} text={c.text!r}"
