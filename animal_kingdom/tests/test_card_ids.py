"""A card's id names its animal, never its display name (AGENTS.md, Invariants; Martin, 2026-10-21): ids are what
decks, logs and code hold, so they must not drift when names change, and must change when the animal does
(tools/cards/hq.py rename)."""
import json
import re
from pathlib import Path

CARDS = json.loads((Path(__file__).parents[1] / "data" / "cards.json").read_text(encoding="utf-8"))["cards"]
slug = lambda s: re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def test_every_collected_card_id_names_its_animal():
    wrong = []
    for c in CARDS:
        if c["status"] != "collectible" or not c.get("species"):
            continue
        animal = slug(c["species"])
        if c["rarity"] == "legendary":
            ok = re.fullmatch(rf"{animal}_legend(_\d+)?", c["id"])
        else:   # the animal as players say it: Dart Frog for the Poison Dart Frog, Caterpillar for the Butterfly's young
            ok = c["id"] == animal or set(c["id"].split("_")) & set(animal.split("_")) or c["id"] == slug(c["name"])
        if not ok:
            wrong.append(f"{c['id']} ({c['species']}, {c['rarity']})")
    assert not wrong, "ids that don't name their animal (tools/cards/hq.py rename OLD NEW): " + ", ".join(wrong)
