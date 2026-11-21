"""Card ids that changed, old -> new, and how anything written before the change reads in the new ids: players' saved
decks (web/profiles.py), saved matches and registered decks (web/server.py, web/custom_decks.py). static/cardnums.js
SUCCESSOR is the same map for the client; tools/cards/hq.py rename adds to both."""
from __future__ import annotations

from ..game import CARDS

RENAMED_IDS = {"shade_enemy": "shade_combo", "djinn_enemy": "djinn_combo", "shade_food": "shade_region", "djinn_food": "djinn_region", }


def renamed(x):
    """`x` (a saved match, a deck list, any JSON) with every old id that no card holds any more read as the new one."""
    if isinstance(x, str):
        return RENAMED_IDS[x] if x in RENAMED_IDS and x not in CARDS else x
    if isinstance(x, list):
        return [renamed(v) for v in x]
    if isinstance(x, dict):
        return {renamed(k): renamed(v) for k, v in x.items()}
    return x
