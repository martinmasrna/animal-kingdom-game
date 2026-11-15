"""The stars prototype (branch `stars`, 2026-11-14; not settled design).

Every card has a level, 0 ordinary (the plain Lion's; most cards; unmarked), 1 strong, 2 legendary, 3 monster,
and a deck holds at most decks.STAR_BUDGET of them, counted per copy. A card's `stars` in
cards.json sets it; without one, its rarity's as the data records it.

Commons and rares are one kind of card here (Martin, 2026-11-15: "merging rare and commons together, and then bringing the
limit for non-legendary cards to 2"): cards.json keeps a card's recorded rarity, which gives its starting level, and the
game reads every rare as a common, so the engines, the client and the deck rules know two kinds, legendary and the rest.
"""

from __future__ import annotations

STAR_LEVELS = (0, 1, 2, 3)   # no level below ordinary: too confusing for players (Martin, 2026-11-15)
STAR_DEFAULTS = {"common": 0, "rare": 1, "legendary": 2}


def merge_rarities(records: list) -> list:
    """The card records as the game reads them: each with its level (`stars`, its recorded rarity's when unset), then a
    rare recorded as a common. Returns new records; a record already merged comes back the same."""
    out = []
    for rec in records:
        if isinstance(rec, dict) and rec.get("rarity") in STAR_DEFAULTS:
            rec = dict(rec)
            if rec.get("stars") is None:
                rec["stars"] = STAR_DEFAULTS[rec["rarity"]]
            if rec["rarity"] == "rare":
                rec["rarity"] = "common"
        out.append(rec)
    return out
