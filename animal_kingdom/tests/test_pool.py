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

# food_otk is the one deliberate exception to the locked 4-4-6/14-design template
# (2026-07-06): a 7th common (2 copies) was added alongside Hedgehog/Hamster dropping to
# 2 copies each, so the design count and rarity mix - not the 30-card total - move for
# this deck only. See Card.copies (engine/cards.py) for the per-design override.
DESIGN_COUNT_OVERRIDES = {"food_otk": 15}
RARITY_MIX_OVERRIDES = {"food_otk": {"legendary": 4, "rare": 4, "common": 7}}


# ----------------------------------------------------------------- pool composition

def test_98_designs_in_exactly_7_decks():
    cards = load_cards()
    # 99 draftable designs across the 7 decks (98 base + food_otk's 1 override); tokens/reserve
    # live outside the deck pool.
    draftable = [c for c in cards.values() if c.deck in DECK_SLUGS]
    expected_total = 14 * len(DECK_SLUGS) + sum(
        n - 14 for n in DESIGN_COUNT_OVERRIDES.values()
    )
    assert len(draftable) == expected_total
    by_deck: dict[str, list] = {slug: [] for slug in DECK_SLUGS}
    for c in draftable:
        by_deck[c.deck].append(c)
    assert len(by_deck) == 7
    for slug, designs in by_deck.items():
        expected = DESIGN_COUNT_OVERRIDES.get(slug, 14)
        assert len(designs) == expected, f"{slug} has {len(designs)} designs, expected {expected}"
        rarities = Counter(c.rarity for c in designs)
        expected_mix = RARITY_MIX_OVERRIDES.get(slug, {"legendary": 4, "rare": 4, "common": 6})
        assert rarities == expected_mix, f"{slug}: {rarities}"


def test_ids_and_names_globally_unique():
    cards = load_cards()
    # Every id and name in the registry (draftable + tokens + reserve) is unique.
    ids = [c.id for c in cards.values()]
    names = [c.name for c in cards.values()]
    assert len(set(ids)) == len(ids) == len(cards)
    assert len(set(names)) == len(names) == len(cards)


def test_each_deck_expands_to_30():
    for slug in DECK_SLUGS:
        deck = load_premade_deck(slug)
        assert len(deck) == 30, f"{slug} expands to {len(deck)}"
        counts = Counter(deck)
        assert len(counts) == DESIGN_COUNT_OVERRIDES.get(slug, 14)
    assert PREMADE_DECKS.keys() == DECK_SLUGS


def test_copy_limits_locked_446():
    assert COPY_LIMITS == {"legendary": 1, "rare": 2, "common": 3}
    cards = load_cards()
    for slug in DECK_SLUGS:
        counts = Counter(load_premade_deck(slug))
        for cid, n in counts.items():
            card = cards[cid]
            expected = card.copies if card.copies is not None else COPY_LIMITS[card.rarity]
            assert n == expected


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
