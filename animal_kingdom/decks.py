"""The decks registered for play by slug (players' decks: web/custom_decks.py). What makes a deck legal is the engine's
rule (`game.deck_problems`): 25 cards, collectible cards only, at most two copies of a card and one of a legendary, and
a leader, one of its own legendaries that can lead."""

from __future__ import annotations

from typing import Optional, Sequence

from .game import DECK_SIZE, deck_problems  # noqa: F401  (read from here by the server and the tests)

DECKS: dict[str, list[str]] = {}          # slug -> its 25 card ids
DECK_LEADERS: dict[str, str] = {}         # slug -> its leader's card id


def register_deck(slug: str, decklist: Sequence[str], leader: Optional[str]) -> None:
    DECKS[slug] = list(decklist)
    if leader:
        DECK_LEADERS[slug] = leader


def load_deck(slug: str) -> list[str]:
    if slug not in DECKS:
        raise ValueError(f"unknown deck {slug!r}")
    return list(DECKS[slug])
