"""The deck rules, and the decks registered for play by slug (players' decks: web/custom_decks.py).

A deck is 25 cards: collectible cards only, at most two copies of a card and one of a legendary, and a leader, one of its
own legendaries that can lead (engine/leaders.py)."""

from __future__ import annotations

from typing import Optional, Sequence

from .engine.cards import COPY_LIMITS, Card, load_cards
from .engine.leaders import leader_problem

DECK_SIZE = 25

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


def deck_problems(decklist: Sequence[str], leader: Optional[str], *, cards: Optional[dict[str, Card]] = None) -> list[str]:
    """What makes a deck illegal; empty when it's legal."""
    cards = cards if cards is not None else load_cards()
    problems = []
    if len(decklist) != DECK_SIZE:
        problems.append(f"a deck has {DECK_SIZE} cards, not {len(decklist)}")
    counts: dict[str, int] = {}
    for cid in decklist:
        counts[cid] = counts.get(cid, 0) + 1
    for cid, n in counts.items():
        card = cards.get(cid)
        if card is None or not card.collectible:
            problems.append(f"{cid!r} is not a collectible card")
        elif n > COPY_LIMITS[card.rarity]:
            problems.append(f"at most {COPY_LIMITS[card.rarity]} {card.name}")
    if (bad := leader_problem(leader, decklist)):
        problems.append(bad)
    return problems
