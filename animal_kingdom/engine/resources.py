"""Domain-neutral access to data files bundled inside the package.

Lives here (rather than in cards.py/maps.py) so both loaders can share it without one
data module depending on another. Uses importlib.resources so it works whether the
package is run from source or installed.
"""

from __future__ import annotations

import json
from importlib import resources


def load_bundled_json(filename: str, *, as_played: bool = True) -> dict:
    """Parse and return data/<filename> shipped inside the animal_kingdom package. cards.json comes as the game reads it
    (the stars prototype, engine/stars.py: each card's level set, a rare read as a common), so the Python engine, the
    Rust bots and the browser's engine, which all load it from here, agree. `as_played=False` gives the file as recorded."""
    resource = resources.files("animal_kingdom") / "data" / filename
    with resources.as_file(resource) as path:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    if filename == "cards.json" and as_played:
        from .stars import merge_rarities
        data["cards"] = merge_rarities(data.get("cards", []))
    return data
