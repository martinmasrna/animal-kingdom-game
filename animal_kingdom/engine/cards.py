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

# Allowed value domains (validation). Reworked 98-design pool: README decisions B-E.
RARITIES = {"common", "rare", "legendary"}
KEYWORDS = {"Flight", "Immovable", "Fragile", "Apex Predator", "Stealth"}  # static keywords only;
# Battlecry/Deathrattle are trigger prefixes printed in `text`, not stored keywords.
TYPES = {"unit", "landmark"}                 # landmark is the lone non-unit type (dec. C)
LANDMARK_IDS = {"fig_tree", "watering_hole"}  # the only two landmarks in the pool
# Family + role tags (dec. B). Retired umbrellas (Reptile, Insect) are forbidden.
TAGS = {
    "Cat", "Canine", "Colony", "Snake", "Lizard", "Bird", "Rodent",
    "Arachnid", "Bear", "Megafauna", "Egg", "Fish",   # species families
    "Queen", "Worker",                                # roles
}
DYNAMIC_STRENGTHS = {"removed_units_count", "chameleon"}  # only Goliath + Chameleon

# The seven premade deck slugs (align to docs/cards/decks/ filenames).
DECK_SLUGS = {
    "cats_midrange", "egg_control", "colony_food_swarm", "ramp",
    "food_otk", "aggro_hq_rush", "canine_buff_tempo",
}

# Copy limits per rarity for the locked 4-4-6 decklist shape (legendary 1 / rare 2 / common 3).
COPY_LIMITS = {"common": 3, "rare": 2, "legendary": 1}


class CardDataError(ValueError):
    """Raised when card data fails validation."""


@dataclass(frozen=True)
class Card:
    """Static data for one card design (one record in cards.json)."""

    id: str
    name: str
    deck: str
    rarity: str
    type: str
    tags: frozenset[str]
    base_strength: int | str       # int 0-10, or the string "dynamic"
    keywords: frozenset[str] = field(default_factory=frozenset)
    dynamic_strength: Optional[str] = None  # rule name when base_strength == "dynamic"
    food_cost: int = 0             # placement cost; only on "Costs X food" cards
    text: str = ""

    @property
    def is_dynamic(self) -> bool:
        return self.base_strength == "dynamic"

    @property
    def is_unit(self) -> bool:
        """Units and Eggs are units (dec. C); Landmarks are not."""
        return self.type == "unit"

    @property
    def has_battlecry(self) -> bool:
        """Whether the printed rules text declares an on-placement Battlecry."""
        return "Battlecry:" in self.text

    def has_keyword(self, kw: str) -> bool:
        return kw in self.keywords

    def has_tag(self, tag: str) -> bool:
        return tag in self.tags


def validate_card_record(rec: dict) -> None:
    """Check that a raw card record is well-formed; raise CardDataError on the first problem.

    Separate from construction (parse, don't validate): the loader is the trust boundary,
    so a constructed Card is always valid and the engine needs no defensive checks.
    Directly unit-testable on its own.
    """
    required = ("id", "name", "deck", "rarity", "type", "tags", "base_strength")
    for key in required:
        if key not in rec:
            raise CardDataError(f"card {rec.get('id', rec)!r} missing required field {key!r}")
    # keywords/text/dynamic_strength/food_cost are optional and default during construction.

    cid = rec["id"]
    if rec["rarity"] not in RARITIES:
        raise CardDataError(f"card {cid!r}: bad rarity {rec['rarity']!r}, expected one of {sorted(RARITIES)}")
    if rec["deck"] not in DECK_SLUGS:
        raise CardDataError(f"card {cid!r}: bad deck {rec['deck']!r}, expected one of {sorted(DECK_SLUGS)}")

    ctype = rec["type"]
    if ctype not in TYPES:
        raise CardDataError(f"card {cid!r}: bad type {ctype!r}, expected one of {sorted(TYPES)}")
    if ctype == "landmark" and cid not in LANDMARK_IDS:
        raise CardDataError(f"card {cid!r}: only {sorted(LANDMARK_IDS)} may be landmarks (dec. C)")

    tags = rec["tags"]
    if not isinstance(tags, list):
        raise CardDataError(f"card {cid!r}: tags must be a list, got {tags!r}")
    for tag in tags:
        if tag not in TAGS:
            raise CardDataError(f"card {cid!r}: unknown tag {tag!r}, expected subset of {sorted(TAGS)}")

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

    food_cost = rec.get("food_cost", 0)
    if isinstance(food_cost, bool) or not isinstance(food_cost, int) or food_cost < 0:
        raise CardDataError(f"card {cid!r}: food_cost must be an int >= 0, got {food_cost!r}")

    for kw in rec.get("keywords", []):
        if kw not in KEYWORDS:
            raise CardDataError(f"card {cid!r}: unknown keyword {kw!r}, expected subset of {sorted(KEYWORDS)}")


def _build_card(rec: dict) -> Card:
    return Card(
        id=rec["id"],
        name=rec["name"],
        deck=rec["deck"],
        rarity=rec["rarity"],
        type=rec["type"],
        tags=frozenset(rec["tags"]),
        base_strength=rec["base_strength"],
        keywords=frozenset(rec.get("keywords", [])),
        dynamic_strength=rec.get("dynamic_strength"),
        food_cost=rec.get("food_cost", 0),
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
