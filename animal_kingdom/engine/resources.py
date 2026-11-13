"""Domain-neutral access to data files bundled inside the package.

Lives here (rather than in cards.py/maps.py) so both loaders can share it without one
data module depending on another. Uses importlib.resources so it works whether the
package is run from source or installed.
"""

from __future__ import annotations

import json
from importlib import resources


def load_bundled_json(filename: str) -> dict:
    """Parse and return data/<filename> shipped inside the animal_kingdom package."""
    resource = resources.files("animal_kingdom") / "data" / filename
    with resources.as_file(resource) as path:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    if filename == "cards." + "json":
        _apply_provisions(data)
    return data


# The provisions test (branch `provisions`, never merged): data/provisions.json prices cards and may change a card's
# strength, laid over the card data at load, so the engine, the Rust bots and the client all see the same cards.
DEFAULT_PRICE = {"common": 2, "rare": 3, "legendary": 4}


def provisions() -> dict:
    resource = resources.files("animal_kingdom") / "data" / "provisions.json"
    with resources.as_file(resource) as path:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)


def _apply_provisions(data: dict) -> None:
    over = provisions().get("cards", {})
    for rec in data.get("cards", []):
        o = over.get(rec.get("id"), {})
        rec["price"] = o.get("price", DEFAULT_PRICE.get(rec.get("rarity"), 2))
        if "strength" in o:
            rec["base_strength"] = o["strength"]
