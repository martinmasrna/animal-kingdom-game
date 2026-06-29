"""Deck construction helpers.

M1 needs simple, legal-ish decks to fuzz and to drive the CLI. `make_vanilla_deck`
builds one from integer-strength cards only (the 3 dynamic-strength cards are excluded
until M2, per plan decision 5), respecting the per-rarity copy limits. The real,
hand-built 32-card archetype decks arrive in M3.
"""

from __future__ import annotations

import random
from typing import Optional

from .engine.cards import COPY_LIMITS, Card, load_cards


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
            continue  # exclude dynamic-strength cards in M1
        pool.extend([card.id] * COPY_LIMITS[card.rarity])

    if len(pool) < n:
        raise ValueError(f"vanilla pool too small ({len(pool)}) for deck size {n}")

    rng.shuffle(pool)
    return pool[:n]
