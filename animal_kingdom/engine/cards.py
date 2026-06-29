"""Card registry: load static card data from data/cards.json and validate it.

This module owns only *static* data (stats + printed text). Card *behavior* (effect
handlers, static modifiers, dynamic strength) is bound in later milestones (effects.py,
statics.py, strength.py) keyed by `Card.id`; the JSON↔logic split keeps a future TS
client able to read stats/text from JSON while logic stays in Python (handoff §6.3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .resources import load_bundled_json

# Allowed value domains (validation).
RARITIES = {"common", "rare", "legendary"}
KEYWORDS = {"Flight", "Immovable", "Fragile"}
DYNAMIC_STRENGTHS = {"control_count", "discard_count", "chameleon"}
ARCHETYPES = {"aggro", "control", "combo", "midrange", "general", "parking"}

# Copy limits per rarity for roster construction (overview.md §14).
COPY_LIMITS = {"common": 4, "rare": 2, "legendary": 1}


class CardDataError(ValueError):
    """Raised when card data fails validation."""


@dataclass(frozen=True)
class Card:
    """Static data for one card design (one record in cards.json)."""

    id: str
    name: str
    archetype: str
    rarity: str
    tag: Optional[str]
    base_strength: int | str       # int 0-10, or the string "dynamic"
    keywords: frozenset[str] = field(default_factory=frozenset)
    dynamic_strength: Optional[str] = None  # rule name when base_strength == "dynamic"
    text: str = ""

    @property
    def is_dynamic(self) -> bool:
        return self.base_strength == "dynamic"

    def has_keyword(self, kw: str) -> bool:
        return kw in self.keywords


def validate_card_record(rec: dict) -> None:
    """Check that a raw card record is well-formed; raise CardDataError on the first problem.

    Separate from construction (parse, don't validate): the loader is the trust boundary,
    so a constructed Card is always valid and the engine needs no defensive checks.
    Directly unit-testable on its own.
    """
    required = ("id", "name", "archetype", "rarity", "base_strength")
    for key in required:
        if key not in rec:
            raise CardDataError(f"card {rec.get('id', rec)!r} missing required field {key!r}")
    # `tag` is required but may be null (printed '-'); keywords/text/dynamic_strength
    # are optional and default during construction.
    if "tag" not in rec:
        raise CardDataError(f"card {rec['id']!r} missing required field 'tag' (use null for '-')")

    cid = rec["id"]
    if rec["rarity"] not in RARITIES:
        raise CardDataError(f"card {cid!r}: bad rarity {rec['rarity']!r}, expected one of {sorted(RARITIES)}")
    if rec["archetype"] not in ARCHETYPES:
        raise CardDataError(f"card {cid!r}: bad archetype {rec['archetype']!r}")

    strength = rec["base_strength"]
    if strength == "dynamic":
        ds = rec.get("dynamic_strength")
        if ds not in DYNAMIC_STRENGTHS:
            raise CardDataError(
                f"card {cid!r}: base_strength 'dynamic' needs a valid 'dynamic_strength' "
                f"(got {ds!r}, expected one of {sorted(DYNAMIC_STRENGTHS)})"
            )
    elif isinstance(strength, bool) or not isinstance(strength, int):
        raise CardDataError(f"card {cid!r}: base_strength must be an int or 'dynamic', got {strength!r}")
    elif not 0 <= strength <= 10:
        raise CardDataError(f"card {cid!r}: base_strength {strength} out of range 0-10")

    for kw in rec.get("keywords", []):
        if kw not in KEYWORDS:
            raise CardDataError(f"card {cid!r}: unknown keyword {kw!r}, expected subset of {sorted(KEYWORDS)}")


def _build_card(rec: dict) -> Card:
    return Card(
        id=rec["id"],
        name=rec["name"],
        archetype=rec["archetype"],
        rarity=rec["rarity"],
        tag=rec["tag"],
        base_strength=rec["base_strength"],
        keywords=frozenset(rec.get("keywords", [])),
        dynamic_strength=rec.get("dynamic_strength"),
        text=rec.get("text", ""),
    )


def load_cards(raw: Optional[dict] = None, *, validate: bool = True) -> dict[str, Card]:
    """Return a dict id -> Card. Loads bundled data/cards.json by default.

    Pass `raw` (an already-parsed dict shaped like cards.json) to load custom data,
    e.g. in tests. `validate` defaults to True (the loader is the trust boundary); pass
    validate=False only for data already known to be well-formed.
    """
    if raw is None:
        raw = load_bundled_json("cards.json")

    records = raw.get("cards")
    if not isinstance(records, list) or not records:
        raise CardDataError("cards.json must contain a non-empty 'cards' list")

    registry: dict[str, Card] = {}
    for rec in records:
        if validate:
            validate_card_record(rec)
        cid = rec["id"]
        if cid in registry:
            raise CardDataError(f"duplicate card id {cid!r}")
        registry[cid] = _build_card(rec)
    return registry
