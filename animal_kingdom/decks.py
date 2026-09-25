"""Deck construction helpers.

The reworked pool ships as **7 premade 4-4-6 decks** (`PREMADE_DECKS` /
`load_premade_deck`), each a fixed 30-card list expanded from its 14 designs by the
per-rarity copy limits (4 legendary ×1 + 4 rare ×2 + 6 common ×3 = 30). These are the
real decks games are played with.

`make_vanilla_deck` survives as a fuzz/CLI helper: it builds a legal-ish deck from
integer-strength cards only (the two dynamic cards, Goliath and Chameleon, are excluded
until their strength rules land), respecting the copy limits.
"""

from __future__ import annotations

import json
import os
import random
from typing import Optional, Sequence

from .engine.cards import COPY_LIMITS, Card, DECK_SLUGS, NON_DECK_SLUGS, load_cards


def _build_premade_decks(cards: dict[str, Card]) -> dict[str, list[str]]:
    """Expand each deck's 14 designs into its 30-card decklist via the copy limits.

    Non-draftable cards (tokens, reserve designs; see NON_DECK_SLUGS) are skipped — they
    live in the registry but belong to no premade deck.
    """
    decks: dict[str, list[str]] = {slug: [] for slug in DECK_SLUGS}
    for card in cards.values():
        if card.deck in NON_DECK_SLUGS:
            continue
        copies = card.copies if card.copies is not None else COPY_LIMITS[card.rarity]
        decks[card.deck].extend([card.id] * copies)
    return decks


# Deck slug -> 30 card ids. Built once from the bundled pool (single source of truth:
# each card's `deck`/`rarity`), so it can never drift from cards.json.
PREMADE_DECKS: dict[str, list[str]] = _build_premade_decks(load_cards())


# The no-synergy "baseline" deck: 30 distinct self-sufficient cards (18 common / 8 rare /
# 4 legendary, 1 copy each) plus minted calibration bodies (the `mock_*` reserve cards). Not a
# shipped deck; self-play trains against it as an eighth, synergy-free opponent.
BASELINE_DECK: list[str] = [
    # common
    "lion", "eagle", "bat", "squirrel", "mock_scout", "mock_saboteur", "african_wild_dog",
    "anaconda", "gray_wolf", "mock_immovable_6", "black_bear", "grizzly_bear", "mock_vanilla_5",
    "mock_vanilla_6", "mock_vanilla_8", "mock_vanilla_9", "mock_apex_5", "mock_apex_6",
    # rare
    "jerboa", "jaguar", "serval", "stoop", "porcupine", "polar_bear", "rhinoceros", "mock_draw2",
    # legendary
    "greywhisker", "mock_removal", "mock_vanilla_10", "mock_flyer_7",
]

# Decks loadable by slug that are not shipped premades: the baseline, plus synthetic decks the sim
# tools register (optimizer candidates, goodstuff piles). Registered decks are mirrored into
# $AK_EXTRA_DECKS so `spawn`ed worker processes, which re-import this module, load them too.
EXTRA_DECKS: dict[str, list[str]] = {"baseline": BASELINE_DECK}
EXTRA_DECKS.update(json.loads(os.environ.get("AK_EXTRA_DECKS", "{}")))


def register_deck(slug: str, decklist: Sequence[str]) -> None:
    """Make `decklist` loadable as `slug` in this process and in any worker it spawns later."""
    if slug in DECK_SLUGS:
        raise ValueError(f"{slug!r} collides with a premade deck slug")
    EXTRA_DECKS[slug] = list(decklist)
    os.environ["AK_EXTRA_DECKS"] = json.dumps(
        {s: d for s, d in EXTRA_DECKS.items() if s != "baseline"})


def load_premade_deck(slug: str, *, cards: Optional[dict[str, Card]] = None) -> list[str]:
    """Return a fresh copy of the 30-card decklist for `slug`."""
    decks = _build_premade_decks(cards) if cards is not None else PREMADE_DECKS
    decks = {**decks, **EXTRA_DECKS}
    if slug not in decks:
        raise ValueError(f"unknown deck slug {slug!r}, expected one of {sorted(decks)}")
    return list(decks[slug])


def make_vanilla_deck(
    n: int = 32,
    *,
    cards: Optional[dict[str, Card]] = None,
    rng: Optional[random.Random] = None,
    seed: Optional[int] = None,
) -> list[str]:
    """Return a list of `n` card ids drawn from integer-strength cards within copy limits."""
    cards = cards or load_cards()
    rng = rng if rng is not None else random.Random(seed)

    pool: list[str] = []
    for card in cards.values():
        if not isinstance(card.base_strength, int):
            continue  # exclude dynamic-strength cards (Goliath, Chameleon)
        if card.deck in NON_DECK_SLUGS:
            continue  # exclude tokens / reserve designs
        pool.extend([card.id] * COPY_LIMITS[card.rarity])

    if len(pool) < n:
        raise ValueError(f"vanilla pool too small ({len(pool)}) for deck size {n}")

    rng.shuffle(pool)
    return pool[:n]
