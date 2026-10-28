"""Structural tests for the card pool and the shipped deck lists (decklists.json).

These assert the *shape* of the static data (uniqueness, domains), not card behavior. The starter decks' shape (how
many, sharing no card, 30 each) isn't held here while the cards change (Martin, 2026-10-28).
"""

from __future__ import annotations

from animal_kingdom.engine.cards import (
    COPY_LIMITS,
    DECKLISTS,
    DYNAMIC_STRENGTHS,
    KEYWORDS,
    TAGS,
    load_cards,
)
from animal_kingdom.decks import BOT_DECKS, PREMADE_DECKS

RETIRED_TAGS = {"Reptile", "Insect"}
DYNAMIC_IDS = {"egg_eater"}


# ----------------------------------------------------------------- pool composition

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
