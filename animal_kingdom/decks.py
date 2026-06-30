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

import random
from typing import Optional

from .engine.cards import COPY_LIMITS, Card, DECK_SLUGS, load_cards


def _build_premade_decks(cards: dict[str, Card]) -> dict[str, list[str]]:
    """Expand each deck's 14 designs into its 30-card decklist via the copy limits."""
    decks: dict[str, list[str]] = {slug: [] for slug in DECK_SLUGS}
    for card in cards.values():
        decks[card.deck].extend([card.id] * COPY_LIMITS[card.rarity])
    return decks


# Deck slug -> 30 card ids. Built once from the bundled pool (single source of truth:
# each card's `deck`/`rarity`), so it can never drift from cards.json.
PREMADE_DECKS: dict[str, list[str]] = _build_premade_decks(load_cards())


def load_premade_deck(slug: str, *, cards: Optional[dict[str, Card]] = None) -> list[str]:
    """Return a fresh copy of the 30-card decklist for `slug`."""
    decks = _build_premade_decks(cards) if cards is not None else PREMADE_DECKS
    if slug not in decks:
        raise ValueError(f"unknown deck slug {slug!r}, expected one of {sorted(DECK_SLUGS)}")
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
        pool.extend([card.id] * COPY_LIMITS[card.rarity])

    if len(pool) < n:
        raise ValueError(f"vanilla pool too small ({len(pool)}) for deck size {n}")

    rng.shuffle(pool)
    return pool[:n]
