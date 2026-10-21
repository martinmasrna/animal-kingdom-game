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
KEYWORDS = {"Flight", "Armor", "Apex Predator", "Stealth", "Spikes", "Poison", "Roam", "Reach", "Hungry", "Titan",
            "Flee"}  # static keywords only;
# Roar/Dawn/Dusk/Deathrattle are trigger prefixes printed in `text`, not stored keywords. A numbered keyword carries its
# number in its own field: Hungry 3 is {"keywords": ["Hungry"], "hungry": 3}. Reach has none (its distance is config.reach).
# Family + role tags (dec. B). Retired umbrellas (Reptile, Insect) are forbidden.
TAGS = {
    "Cat", "Canine", "Colony", "Snake", "Lizard", "Bird", "Rodent",
    "Arachnid", "Bear", "Megafauna", "Egg", "Fish", "Primate", "Hoofed",   # species families
    "Queen", "Worker",                                # roles
}
DYNAMIC_STRENGTHS = {"removed_units_count", "removed_eggs_count"}  # Python, Egg Eater

# A card's status. Cards are cards and decks are decks (Martin, 2026-10-19): a card belongs to no deck, and the
# decks the game ships (decklists.json: the starter decks a new profile gets, the decks the bots play) are lists over
# the collectible cards, read by decks.py.
# "collectible" = a card a deck may hold: the starter decks' cards and the bench (finished cards in no starter deck).
# "reserve" = shelved designs kept out of play (open designs, a later habitat's cards, the sim tools' calibration bodies).
# "tutorial" = the tutorial's fixed deal, cards as they were when it was written.
# "token" = made by effects (Baby Turtle, a Stork's younglings, the Butterfly's stages); never in a decklist.
# A "planned" record in cards.json (an animal and habitat waiting for a design) is no card yet: the loader skips it.
STATUSES = {"collectible", "reserve", "tutorial", "token"}
PLANNED = "planned"

# The decks the game ships (decklists.json), in menu order:
# slug, name, cover (the card whose art faces it), starter (a new profile gets it), bot (the bots play it), cards
# (id: copies). Starter slugs align to docs/cards/decks/ filenames.
DECKLISTS: list[dict] = sorted(load_bundled_json("decklists.json")["decks"], key=lambda d: d.get("order", 0))
STARTER_DECKS: list[dict] = [d for d in DECKLISTS if d.get("starter")]
DECK_SLUGS = {d["slug"] for d in STARTER_DECKS}          # the starter decks

# Copy limits per rarity for the locked 4-4-6 decklist shape (legendary 1 / rare 2 / common 3).
COPY_LIMITS = {"common": 3, "rare": 2, "legendary": 1}


class CardDataError(ValueError):
    """Raised when card data fails validation."""


@dataclass(frozen=True)
class Card:
    """Static data for one card design (one record in cards.json)."""

    id: str
    name: str
    status: str                    # collectible / reserve / tutorial / token (STATUSES)
    rarity: str
    tags: frozenset[str]
    base_strength: int | str       # int 0-10, or the string "dynamic"
    keywords: frozenset[str] = field(default_factory=frozenset)
    dynamic_strength: Optional[str] = None  # rule name when base_strength == "dynamic"
    food_cost: int = 0             # placement cost; only on "Costs X food" cards
    text: str = ""
    hungry: int = 0                # Hungry N: eats N food at the start of your turn, else loses N strength (0: not Hungry)
    unnamed: bool = False          # a legendary still waiting for its name: `name` shows its species meanwhile
    mate: Optional[str] = None     # the card it pairs with in hand (the Eagles): a buff to either counts for both
    habitat: str = ""              # the habitat (set) the card belongs to; display only, no rule reads it
    related: tuple[str, ...] = ()  # the cards it makes, shown beside it when read large; display only
    evolves: bool = False          # its related cards are what it becomes, in order (display only)

    @property
    def is_dynamic(self) -> bool:
        return self.base_strength == "dynamic"

    @property
    def collectible(self) -> bool:
        """Whether a deck may hold this card (not a reserve design, the tutorial's or a token)."""
        return self.status == "collectible"

    @property
    def has_roar(self) -> bool:
        """Whether the printed rules text declares an on-placement Roar."""
        return "Roar:" in self.text

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
    required = ("id", "name", "status", "rarity", "tags", "base_strength")
    for key in required:
        if key not in rec:
            raise CardDataError(f"card {rec.get('id', rec)!r} missing required field {key!r}")
    # keywords/text/dynamic_strength/food_cost are optional and default during construction.

    cid = rec["id"]
    if rec["rarity"] not in RARITIES:
        raise CardDataError(f"card {cid!r}: bad rarity {rec['rarity']!r}, expected one of {sorted(RARITIES)}")
    if rec["status"] not in STATUSES:
        raise CardDataError(f"card {cid!r}: bad status {rec['status']!r}, expected one of {sorted(STATUSES)}")

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

    hungry = rec.get("hungry")
    if hungry is not None and (isinstance(hungry, bool) or not isinstance(hungry, int) or hungry < 1):
        raise CardDataError(f"card {cid!r}: hungry must be a positive int, got {hungry!r}")
    if ("Hungry" in rec.get("keywords", [])) != (hungry is not None):
        raise CardDataError(f"card {cid!r}: the Hungry keyword and its `hungry` number go together")

    if "reach" in rec:
        raise CardDataError(f"card {cid!r}: Reach has no number (every Reach lands two crossroads out, config.reach)")


def _build_card(rec: dict) -> Card:
    return Card(
        id=rec["id"],
        name=rec["name"],
        status=rec["status"],
        rarity=rec["rarity"],
        tags=frozenset(rec["tags"]),
        base_strength=rec["base_strength"],
        keywords=frozenset(rec.get("keywords", [])),
        dynamic_strength=rec.get("dynamic_strength"),
        food_cost=rec.get("food_cost", 0),
        text=rec.get("text", ""),
        hungry=rec.get("hungry", 0),
        unnamed=rec.get("unnamed", False),
        mate=rec.get("mate"),
        habitat=rec.get("habitat", ""),
        related=tuple(rec.get("related", ())),
        evolves=bool(rec.get("evolves", False)),
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
        if rec.get("status") == PLANNED:
            continue
        if validate:
            validate_card_record(rec)
        cid = rec["id"]
        if cid in registry:
            raise CardDataError(f"duplicate card id {cid!r}")
        registry[cid] = _build_card(rec)
    return registry
