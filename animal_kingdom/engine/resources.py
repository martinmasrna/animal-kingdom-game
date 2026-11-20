"""Access to the data files bundled inside the package (data/), whether run from source or installed."""

from __future__ import annotations

import json
from importlib import resources


def load_bundled_json(filename: str) -> dict:
    resource = resources.files("animal_kingdom") / "data" / filename
    with resources.as_file(resource) as path:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
