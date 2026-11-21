"""The card registry: static card data from data/cards.json, validated on load. Behaviour lives in effects.py (keyed by
card id), statics.py and strength.py."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .resources import load_bundled_json

RARITIES = {"common", "legendary"}
KEYWORDS = {"Flight", "Armor", "Stealth", "Spikes", "Poison", "Hungry"}
# A dynamic strength: the Shades' "+1 for each card in your hand, ally, enemy, food of yours, animal in your opponent's
# Remove Pile".
DYNAMIC_STRENGTHS = {"hand_count", "ally_count", "enemy_count", "region_count"}
# "collectible": a deck may hold it. "reserve": benched, out of every deck. A "planned" record is no card yet: the loader
# skips it.
STATUSES = {"collectible", "reserve"}
PLANNED = "planned"

COPY_LIMITS = {"common": 2, "legendary": 1}


class CardDataError(ValueError):
    """Raised when card data fails validation."""


@dataclass(frozen=True)
class Card:
    id: str
    name: str
    status: str
    rarity: str
    base_strength: int | str       # an int, or "dynamic"
    cost: int
    keywords: frozenset[str] = field(default_factory=frozenset)
    dynamic_strength: Optional[str] = None
    text: str = ""

    @property
    def is_dynamic(self) -> bool:
        return self.base_strength == "dynamic"

    @property
    def collectible(self) -> bool:
        return self.status == "collectible"


def validate_card_record(rec: dict) -> None:
    """Raise CardDataError on the first problem with a raw card record."""
    for key in ("id", "name", "status", "rarity", "base_strength", "cost"):
        if key not in rec:
            raise CardDataError(f"card {rec.get('id', rec)!r} missing required field {key!r}")
    cid = rec["id"]
    if rec["rarity"] not in RARITIES:
        raise CardDataError(f"card {cid!r}: bad rarity {rec['rarity']!r}, expected one of {sorted(RARITIES)}")
    if rec["status"] not in STATUSES:
        raise CardDataError(f"card {cid!r}: bad status {rec['status']!r}, expected one of {sorted(STATUSES)}")
    strength = rec["base_strength"]
    if strength == "dynamic":
        if rec.get("dynamic_strength") not in DYNAMIC_STRENGTHS:
            raise CardDataError(f"card {cid!r}: base_strength 'dynamic' needs a 'dynamic_strength' of {sorted(DYNAMIC_STRENGTHS)}")
    elif isinstance(strength, bool) or not isinstance(strength, int) or strength < 0:
        raise CardDataError(f"card {cid!r}: base_strength must be an int >= 0 or 'dynamic', got {strength!r}")
    for kw in rec.get("keywords", []):
        if kw not in KEYWORDS:
            raise CardDataError(f"card {cid!r}: unknown keyword {kw!r}, expected one of {sorted(KEYWORDS)}")
    cost = rec["cost"]
    if isinstance(cost, bool) or not isinstance(cost, int) or not 0 <= cost <= 10:
        raise CardDataError(f"card {cid!r}: cost must be a whole number from 0 to 10, got {cost!r}")


def _build_card(rec: dict) -> Card:
    return Card(id=rec["id"], name=rec["name"], status=rec["status"], rarity=rec["rarity"],
                base_strength=rec["base_strength"], cost=rec["cost"], keywords=frozenset(rec.get("keywords", [])),
                dynamic_strength=rec.get("dynamic_strength"), text=rec.get("text", ""))


def load_cards(raw: Optional[dict] = None, *, validate: bool = True) -> dict[str, Card]:
    """id -> Card, from the bundled data/cards.json or `raw` (a dict shaped like it)."""
    if raw is None:
        raw = load_bundled_json("cards.json")
    records = raw.get("cards")
    if not isinstance(records, list) or not records:
        raise CardDataError("cards.json must contain a non-empty 'cards' list")
    registry: dict[str, Card] = {}
    for rec in records:
        if rec.get("status") == PLANNED:
            continue
        if validate:
            validate_card_record(rec)
        if rec["id"] in registry:
            raise CardDataError(f"duplicate card id {rec['id']!r}")
        registry[rec["id"]] = _build_card(rec)
    return registry
