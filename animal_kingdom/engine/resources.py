"""Domain-neutral access to data files bundled inside the package.

Lives here (rather than in cards.py/maps.py) so both loaders can share it without one
data module depending on another. Uses importlib.resources so it works whether the
package is run from source or installed.
"""

from __future__ import annotations

import json
import os
from importlib import resources

# The energy prototype (branch `energy`, never merged; ENERGY_PLAN.md): with AK_ENERGY=1 the game runs the energy rules
# on the overlaid card data (data/energy.json: each card's cost, its strength by the animal's size, changed texts, benched
# cards, the rule numbers, the sample decks). Without it this is the game as on main, and the tests run that way.
ENERGY = os.environ.get("AK_ENERGY") == "1"


def load_bundled_json(filename: str) -> dict:
    """Parse and return data/<filename> shipped inside the animal_kingdom package."""
    resource = resources.files("animal_kingdom") / "data" / filename
    with resources.as_file(resource) as path:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    if ENERGY and filename == "cards." + "json":
        _overlay_cards(data)
    return data


_variant: dict | None = None


def variant() -> dict:
    """The energy prototype's data (rules, cards, decks); empty when the switch is off."""
    global _variant
    if not ENERGY:
        return {}
    if _variant is None:
        resource = resources.files("animal_kingdom") / "data" / "energy.json"
        with resources.as_file(resource) as path:
            with open(path, "r", encoding="utf-8") as fh:
                _variant = json.load(fh)
    return _variant


def _overlay_cards(data: dict) -> None:
    """Lay the prototype's values over the card records: `cost` (energy), `strength`, `text`, `status`, `keywords`,
    `hungry`. A collectible card the overlay doesn't list is benched (reserve): it has no cost yet. The prototype has
    two kinds of card, the legendary (one copy) and every other (two copies): a rare is recorded as a common."""
    over = variant().get("cards", {})
    for rec in data.get("cards", []):
        if rec.get("rarity") == "rare":
            rec["rarity"] = "common"
        o = over.get(rec.get("id"))
        if o is None:
            if rec.get("status") == "collectible":
                rec["status"] = "reserve"
            rec["price"] = 1 if rec.get("status") == "token" else 2
            continue
        rec["price"] = o.get("cost", 2)
        if "strength" in o:
            rec["base_strength"] = o["strength"]
        for k in ("text", "status", "keywords", "hungry"):
            if k in o:
                rec[k] = o[k]
        if rec.get("hungry") == 0:
            del rec["hungry"]
