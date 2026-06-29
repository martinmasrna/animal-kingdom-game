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
            return json.load(fh)
