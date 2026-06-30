"""Structural tests for the reworked 98-design pool + 7 premade 4-4-6 decks.

These assert the *shape* of the static data (counts, uniqueness, domains, the 4-4-6
expansion) — not card behavior, which is Phase 2.
"""

from __future__ import annotations

from collections import Counter

from animal_kingdom.engine.cards import (
    COPY_LIMITS,
    DECK_SLUGS,
    DYNAMIC_STRENGTHS,
    KEYWORDS,
    LANDMARK_IDS,
    TAGS,
    TYPES,
    load_cards,
)
from animal_kingdom.decks import PREMADE_DECKS, load_premade_deck

RETIRED_TAGS = {"Reptile", "Insect"}
DYNAMIC_IDS = {"goliath", "chameleon"}


# ----------------------------------------------------------------- pool composition

def test_98_designs_in_exactly_7_decks():
    cards = load_cards()
    assert len(cards) == 98
    by_deck: dict[str, list] = {slug: [] for slug in DECK_SLUGS}
    for c in cards.values():
        by_deck[c.deck].append(c)
    assert len(by_deck) == 7
    for slug, designs in by_deck.items():
        assert len(designs) == 14, f"{slug} has {len(designs)} designs, expected 14"
        rarities = Counter(c.rarity for c in designs)
        assert rarities == {"legendary": 4, "rare": 4, "common": 6}, f"{slug}: {rarities}"


def test_ids_and_names_globally_unique():
    cards = load_cards()
    ids = [c.id for c in cards.values()]
    names = [c.name for c in cards.values()]
    assert len(set(ids)) == len(ids) == 98
    assert len(set(names)) == len(names) == 98


def test_each_deck_expands_to_30():
    for slug in DECK_SLUGS:
        deck = load_premade_deck(slug)
        assert len(deck) == 30, f"{slug} expands to {len(deck)}"
        # Exactly the 14 distinct designs at their copy limits.
        counts = Counter(deck)
        assert len(counts) == 14
    assert PREMADE_DECKS.keys() == DECK_SLUGS


def test_copy_limits_locked_446():
    assert COPY_LIMITS == {"legendary": 1, "rare": 2, "common": 3}
    cards = load_cards()
    for slug in DECK_SLUGS:
        counts = Counter(load_premade_deck(slug))
        for cid, n in counts.items():
            assert n == COPY_LIMITS[cards[cid].rarity]


# ------------------------------------------------------------------ field domains

def test_dynamic_strength_present_iff_dynamic_and_only_goliath_chameleon():
    cards = load_cards()
    dynamic = set()
    for c in cards.values():
        if c.is_dynamic:
            dynamic.add(c.id)
            assert c.dynamic_strength in DYNAMIC_STRENGTHS
        else:
            assert c.dynamic_strength is None
            assert isinstance(c.base_strength, int) and 0 <= c.base_strength <= 10
    assert dynamic == DYNAMIC_IDS


def test_keywords_and_tags_within_allowed_sets_no_retired_tags():
    for c in load_cards().values():
        assert c.keywords <= KEYWORDS
        assert c.tags <= TAGS
        assert not (c.tags & RETIRED_TAGS)


def test_types_domain_and_landmarks_are_only_the_two():
    cards = load_cards()
    landmarks = {c.id for c in cards.values() if c.type == "landmark"}
    assert landmarks == LANDMARK_IDS
    for c in cards.values():
        assert c.type in TYPES


def test_food_cost_present_only_where_text_says_costs():
    for c in load_cards().values():
        has_cost = c.food_cost > 0
        says_costs = "Costs" in c.text
        assert has_cost == says_costs, f"{c.id}: food_cost={c.food_cost} text={c.text!r}"
