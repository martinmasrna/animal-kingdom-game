"""The decks: the shipped lists (decklists.json) and the rules a list must obey.

Cards are cards and decks are decks (Martin, 2026-10-19). The game ships its decks as lists over the collectible
cards in data/decklists.json: the **starter decks** (`starter: true`), the 12 4-4-6 decks a new profile gets, which
share no card so a new player meets as many cards as possible; and the **bot decks** (`bot: true`), what the bots
play ranked and in Practice's Random, which may overlap with anything. A deck can be both. `PREMADE_DECKS` holds
every shipped deck and every ladder deck (data/ladder_decks.json, the decks people built and played) as its 30-card list;
`BOT_DECKS` the bot pool's slugs, all of them; `load_premade_deck` any loadable slug.

`make_vanilla_deck` survives as a fuzz/CLI helper: it builds a legal-ish deck from
integer-strength cards only (the dynamic ones are excluded), respecting the copy limits.
"""

from __future__ import annotations

import json
import os
import random
from typing import Optional, Sequence

from .engine.cards import COPY_LIMITS, Card, DECKLISTS, DECK_SLUGS, load_cards


def _expand(deck: dict) -> list[str]:
    """A shipped deck's 30-card list from its design counts, in the file's order (the order the seed shuffles: a
    set's order changes with each process's hash seed, and with it every sim's game seeds)."""
    return [cid for cid, n in deck["cards"].items() for _ in range(n)]


# Deck slug -> 30 card ids, every shipped deck (starters and bot decks), in menu order. Built once from
# decklists.json, so it can never drift from it.
PREMADE_DECKS: dict[str, list[str]] = {d["slug"]: _expand(d) for d in DECKLISTS}

# The ladder's wider pool (data/ladder_decks.json, built by sim/ladder_decks.py): the decks people built and played, as
# the bots play them. Loadable like a shipped deck; `LADDER_DECK_NAMES` carries their builders' names.
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ladder_decks.json"), encoding="utf-8") as _fh:
    LADDER_DECKS: list[dict] = json.load(_fh)["decks"]
LADDER_DECK_NAMES: dict[str, str] = {d["slug"]: d["name"] for d in LADDER_DECKS}
PREMADE_DECKS.update({d["slug"]: list(d["list"]) for d in LADDER_DECKS})

# The decks the bots play: every shipped deck and every ladder deck (Martin, 2026-10-24: the bots play many more decks
# than a hand-picked pool, every pilot-and-deck pairing a player of its own on the ladder; a deck a pilot plays badly sits
# low on the ladder, which is the ladder's own information). Ranked matchmaking, the ladder seed, Practice's 'Random'
# and the bot benchmark panel draw from these.
BOT_DECKS: tuple[str, ...] = tuple(d["slug"] for d in DECKLISTS) + tuple(d["slug"] for d in LADDER_DECKS)
PANEL_OPPONENTS: tuple[str, ...] = ("cats", "den_rush", "fish")   # the benchmark's standing opponents, from the pool
assert all(d in BOT_DECKS for d in PANEL_OPPONENTS), PANEL_OPPONENTS


# The no-synergy "baseline" deck: 30 distinct self-sufficient cards (18 common / 8 rare /
# 4 legendary, 1 copy each) plus minted calibration bodies (the `mock_*` reserve cards). Not a
# shipped deck; self-play trains against it as an eighth, synergy-free opponent.
BASELINE_DECK: list[str] = [
    # common
    "lion", "eagle", "bat", "squirrel", "mock_scout", "mock_saboteur", "fox",
    "anaconda", "jackal", "mock_armor_6", "black_bear", "grizzly_bear", "mock_vanilla_5",
    "mock_vanilla_6", "mock_vanilla_8", "mock_vanilla_9", "mock_apex_5", "mock_apex_6",
    # rare
    "jerboa", "jaguar", "serval", "hawk", "porcupine", "polar_bear", "rhinoceros", "mock_draw2",
    # legendary
    "greywhisker", "mock_removal", "mock_vanilla_10", "mock_flyer_7",
]

# The goodstuff pile: the greedy optimizer's best cross-deck list over the old seven-deck pool
# (2026-09-29), its cards as they are now (Gaboon Viper for the retired Taipan). Stale since the
# launch decks: kept loadable as the sim tools' default pile until the optimizer runs again.
GOODSTUFF_DECK: list[str] = (
    ["fox_legend", "rhinoceros_legend", "falcon_legend", "rat_legend_2"]
    + ["chinchilla", "polar_bear", "rhinoceros", "cottonmouth"] * 2
    + ["wolf", "elephant", "lemming", "lion", "mouse", "tiger"] * 3
)

# Decks loadable by slug that are not shipped premades: the baseline, the goodstuff pile, and
# synthetic decks the sim tools register (optimizer candidates, other piles, which may take the
# "goodstuff" slug over for their own run). Registered decks are mirrored into
# $AK_EXTRA_DECKS so `spawn`ed worker processes, which re-import this module, load them too.
# A test opponent for the web client, reached by link only (#/?botdeck=lions30): Martin's heuristic that every deck
# must beat 30 vanilla Lions. Not a legal deck (three copies at most), so never offered in the deck pickers.
TEST_BOT_DECKS = {"lions30": ["lion"] * 30}
EXTRA_DECKS: dict[str, list[str]] = {"baseline": BASELINE_DECK, "goodstuff": GOODSTUFF_DECK, **TEST_BOT_DECKS}
EXTRA_DECKS.update(json.loads(os.environ.get("AK_EXTRA_DECKS", "{}")))


def register_deck(slug: str, decklist: Sequence[str]) -> None:
    """Make `decklist` loadable as `slug` in this process and in any worker it spawns later."""
    if slug in PREMADE_DECKS:
        raise ValueError(f"{slug!r} collides with a shipped deck's slug")
    EXTRA_DECKS[slug] = list(decklist)
    os.environ["AK_EXTRA_DECKS"] = json.dumps(
        {s: d for s, d in EXTRA_DECKS.items() if s != "baseline"})


DECK_SIZE = 30
RARITY_CAPS = {"rare": 8, "legendary": 4}   # rules §13: at most 8 rares and 4 legendaries in a deck


def decklist_problems(decklist: Sequence[str], *, cards: Optional[dict[str, Card]] = None) -> list[str]:
    """What makes `decklist` illegal under the deck rules (rules §13); empty when it's legal.
    Only collectible cards (the starter decks' and the bench) may be in it."""
    cards = cards if cards is not None else load_cards()
    problems = []
    if len(decklist) != DECK_SIZE:
        problems.append(f"a deck has {DECK_SIZE} cards, not {len(decklist)}")
    counts: dict[str, int] = {}
    for cid in decklist:
        counts[cid] = counts.get(cid, 0) + 1
    by_rarity: dict[str, int] = {}
    for cid, n in counts.items():
        card = cards.get(cid)
        if card is None or not card.collectible:
            problems.append(f"{cid!r} is not a collectible card")
            continue
        limit = COPY_LIMITS[card.rarity]
        if n > limit:
            problems.append(f"at most {limit} {card.name}")
        by_rarity[card.rarity] = by_rarity.get(card.rarity, 0) + n
    for rarity, cap in RARITY_CAPS.items():
        if by_rarity.get(rarity, 0) > cap:
            problems.append(f"at most {cap} {rarity} cards")
    return problems


def load_premade_deck(slug: str, *, cards: Optional[dict[str, Card]] = None) -> list[str]:
    """Return a fresh copy of the 30-card decklist for `slug`: a shipped deck's, or a registered one's."""
    decks = {**PREMADE_DECKS, **EXTRA_DECKS}
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
        if not card.collectible:
            continue  # exclude tokens / reserve designs
        pool.extend([card.id] * COPY_LIMITS[card.rarity])

    if len(pool) < n:
        raise ValueError(f"vanilla pool too small ({len(pool)}) for deck size {n}")

    rng.shuffle(pool)
    return pool[:n]


def _check_shipped() -> None:
    """Every shipped deck is a legal list over the collectible cards (the loader is the trust boundary)."""
    cards = load_cards()
    for slug, decklist in PREMADE_DECKS.items():
        if problems := decklist_problems(decklist, cards=cards):
            raise ValueError(f"decklists.json: {slug}: " + "; ".join(problems))


_check_shipped()
