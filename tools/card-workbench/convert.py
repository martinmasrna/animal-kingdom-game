"""Write the game's card data from the card workbench's export.

    .venv/bin/python tools/card-workbench/convert.py [EXPORT] [--check]

Reads tools/card-workbench/export.json (the workbench snapshot, the source of truth for which cards exist, their
names, strengths, families and text) and rewrites animal_kingdom/data/cards.json: the twelve starter decks (each
card's `deck` and rarity give its copies, so the decklists follow), the pool as the bench, and the cards the
engine makes itself (tokens, the Butterfly's stages, the Eagle's mate), which are listed here. Cards the workbench
doesn't know are kept as they are when they sit in the reserve or the tutorial deal; every other old card goes.

A card keeps its engine id across runs: the id recorded with its workbench id last time, else (the first run) the
old card of the same name, else one made from its name, or from deck and species for an unnamed legendary
(`food_aggro_legend_repeat`). Effects are bound to ids in engine/effects.py, so a card whose text changed in the
workbench needs its behaviour changed there too; `--check` lists what changed without writing anything.

Run `python -m animal_kingdom.render.deck_docs` afterwards to refresh the deck docs' tables.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPORT = ROOT / "tools" / "card-workbench" / "export.json"
CARDS = ROOT / "animal_kingdom" / "data" / "cards.json"

COMMENT = ("Static card data, written by tools/card-workbench/convert.py from the card workbench's export (the source "
           "of truth for the starter decks and the pool); reserve and tutorial cards are kept by it as they are. Effect "
           "logic lives in engine code (effects/statics/strength), bound by id; numbers an effect uses live in "
           "engine/config.py. Schema: decks (starter decks: slug, name, order, cover); cards: id (unique, stable across "
           "runs), name (the species while `unnamed`), deck (a starter slug, or bench/token/reserve/tutorial), rarity, "
           "tags (families and roles), base_strength (int 0-10, or 'dynamic' with dynamic_strength), keywords (printed "
           "static keywords), reach and hungry (their numbers), food_cost (a printed 'Costs X food'), text (verbatim), "
           "mate (the Eagle pair), species, habitat and workbench_id (where it came from).")
RARITY = {"L": "legendary", "R": "rare", "C": "common"}
BENCH = "pool"                       # the workbench's deck of cards in no starter deck
KEPT_DECKS = {"reserve", "tutorial"}  # old cards the workbench doesn't know, kept as they are

# The first run's ids for cards renamed since the old pool, by workbench name.
RENAMED = {"Stray Cat": "house_cat", "Stray Dog": "dog"}
# Unnamed legendaries with no species to name them by: id and the name shown meanwhile.
UNNAMED = {"food-aggro-0": ("food_aggro_legend_repeat", "Rodent"), "food-aggro-1": ("food_aggro_legend_refill", "Rodent")}
# Engine numbers the text doesn't carry.
DYNAMIC = {"goliath": "removed_units_count", "egg_eater": "removed_eggs_count"}
# The card whose art covers each starter deck in the menus (its first legendary otherwise).
COVERS = {"cats": "king_theron", "canines": "lobo", "colony": "queen_honoria", "den_rush": "pestis",
          "egg_control": "eon", "food_aggro": "rat_king", "food_otk": "fathom", "giants": "bulwark",
          "aristocrats": "ember", "fish": "fish_legend_tuna", "handlock": "silverback", "hoofed": "hoofed_legend_giraffe"}

# Printed keywords, as the first sentences of a card's text ("Flight. Roar: ...", "Titan. Hungry 4. ...").
KEYWORD = re.compile(r"(Flight|Armor|Stealth|Spikes|Poison|Roam|Apex Predator|Titan|Flee|Reach (\d+)|Hungry (\d+))\.(?: |$)")
COSTS = re.compile(r"Costs (\d+) food")


def _token(cid, name, strength, tags=(), text="", keywords=(), rarity="common", **extra):
    return {"id": cid, "name": name, "deck": "token", "rarity": rarity, "tags": list(tags), "base_strength": strength,
            "keywords": list(keywords), "text": text, **extra}


# Cards the engine makes, never in a decklist. Their text and strength are the design's (docs/design/effects-pass.md).
TOKENS = [
    _token("baby_turtle", "Baby Turtle", 0),                                   # Sea Turtle
    _token("worm", "Worm", 0, text="When this is removed, draw a card."),     # Earthworm
    _token("baby_fish", "Baby Fish", 0, ["Fish"]),                            # Sunfish
    _token("cuckoo_egg", "Cuckoo Egg", 0, ["Egg"], "When you draw this, your opponent draws a card."),   # Cuckoo
    _token("pup", "Pup", 1, ["Canine"]),                                      # the tutorial's opponent
    _token("poppy", "Poppy", 1, ["Canine"]),                                  # Scarlett
    _token("rusty", "Rusty", 1, ["Canine"]),
    # The Stork's younglings, one per family.
    _token("baby_lion", "Baby Lion", 1, ["Cat"]),
    _token("baby_wolf", "Baby Wolf", 1, ["Canine"]),
    _token("baby_squirrel", "Baby Squirrel", 1, ["Rodent"]),
    _token("baby_owl", "Baby Owl", 1, ["Bird"]),
    _token("baby_python", "Baby Python", 1, ["Snake"]),
    _token("baby_bear", "Baby Bear", 1, ["Bear"]),
    _token("baby_gorilla", "Baby Gorilla", 1, ["Primate"]),
    _token("baby_zebra", "Baby Zebra", 1, ["Hoofed"]),
    # The legendary Butterfly's stages 2-5 (stage 1 is the card itself): the egg's 1 plus its buffs is its strength.
    _token("handlock_legend_butterfly_2", "Caterpillar", 1, rarity="legendary", text="Roar: draw a card.", stage=2),
    _token("handlock_legend_butterfly_3", "Chrysalis", 1, rarity="legendary", keywords=["Stealth"], stage=3,
           text="Stealth. Roar: draw a card, then give an animal in your hand +1 strength."),
    _token("handlock_legend_butterfly_4", "Butterfly", 1, rarity="legendary", keywords=["Stealth", "Flight"], stage=4,
           text="Stealth. Flight. Roar: draw a card, then give all animals in your hand +1 strength."),
    _token("handlock_legend_butterfly_5", "Monarch", 1, rarity="legendary", keywords=["Stealth", "Flight"], stage=5,
           text="Stealth. Flight. Roar: draw 2 cards, then give all animals in your hand +2 strength."),
    # The legendary Eagle's mate, made by it in your hand.
    _token("handlock_legend_eagle_mate", "Eagle", 2, ["Bird"], rarity="legendary", keywords=["Flight", "Apex Predator"],
           text="Flight. Apex Predator. While this and its mate are in your hand, they share their strength.",
           mate="handlock_legend_eagle", unnamed=True),
]
# Cards made from the workbench that the engine pairs with a token.
MATES = {"handlock_legend_eagle": "handlock_legend_eagle_mate"}


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def deck_slug(key: str) -> str:
    return "bench" if key == BENCH else slug(key)


def parse_text(text: str) -> dict:
    """The keywords a card's text opens with, their numbers, and a printed food cost."""
    out: dict = {"keywords": []}
    pos = 0
    while (m := KEYWORD.match(text, pos)):
        word = m.group(1)
        if m.group(2):
            out["keywords"].append("Reach"); out["reach"] = int(m.group(2))
        elif m.group(3):
            out["keywords"].append("Hungry"); out["hungry"] = int(m.group(3))
        else:
            out["keywords"].append(word)
        pos = m.end()
    if (m := COSTS.search(text)):
        out["food_cost"] = int(m.group(1))
    return out


def resolve_id(wc: dict, deck: str, old: list[dict], taken: set) -> str:
    """The engine id for workbench card `wc` (see the module docstring)."""
    for rec in old:
        if rec.get("workbench_id") == wc["id"]:
            return rec["id"]
    if wc["id"] in UNNAMED:
        return UNNAMED[wc["id"]][0]
    name = wc["name"].strip()
    if not name:                                   # an unnamed legendary: by deck and species
        return f"{deck}_legend_{slug(wc['species'])}"
    if name in RENAMED:
        return RENAMED[name]
    for rec in old:
        if rec["name"] == name and rec["deck"] not in KEPT_DECKS | {"token"} and rec["id"] not in taken:
            return rec["id"]
    return slug(name)


def convert(export: dict, old_data: dict) -> tuple[dict, list[str]]:
    old = old_data.get("cards", [])
    by_id = {r["id"]: r for r in old}
    cards, notes, taken = [], [], set()
    decks = []
    for key, deck in sorted(export["decks"].items(), key=lambda kv: kv[1].get("order", 0)):
        dslug = deck_slug(key)
        if deck.get("precon"):
            decks.append({"slug": dslug, "name": deck["name"], "order": deck.get("order", 0)})
        for wc in deck["cards"]:
            if wc.get("str") is None:
                notes.append(f"skipped {wc['id']} ({wc['name'] or wc['species']}): no strength yet")
                continue
            cid = resolve_id(wc, dslug, old, taken)
            if cid in taken:
                raise SystemExit(f"two workbench cards map to the id {cid!r} ({wc['id']}); add one to UNNAMED or RENAMED")
            taken.add(cid)
            text = wc["text"].strip()
            if text == "—":                              # the workbench's mark for a deliberately vanilla animal
                text = ""
            unnamed = not wc["name"].strip()
            name = UNNAMED[wc["id"]][1] if wc["id"] in UNNAMED else (wc["species"] if unnamed else wc["name"].strip())
            in_deck = dslug
            if dslug == "bench" and wc.get("status") == "open":
                in_deck = "reserve"                 # an open design: not collectible until it has its effect
            rec = {"id": cid, "name": name, "deck": in_deck, "rarity": RARITY[wc["rarity"]],
                   "tags": [t.strip() for t in wc.get("tag", "").split(",") if t.strip()],
                   "base_strength": "dynamic" if cid in DYNAMIC else wc["str"], "text": text}
            rec.update(parse_text(text))
            if cid in DYNAMIC:
                rec["dynamic_strength"] = DYNAMIC[cid]
            if cid in MATES:
                rec["mate"] = MATES[cid]
            if unnamed:
                rec["unnamed"] = True
            rec.update({"species": wc.get("species", ""), "habitat": wc.get("habitat", ""), "workbench_id": wc["id"]})
            prev = by_id.get(cid)
            if prev is None:
                notes.append(f"new      {cid:32} {name}")
            elif (prev.get("text", ""), prev["base_strength"], sorted(prev.get("keywords", []))) != (
                    text, rec["base_strength"], sorted(rec["keywords"])):
                notes.append(f"changed  {cid:32} {name}: {prev['base_strength']} {prev.get('text', '')!r} -> "
                             f"{rec['base_strength']} {text!r}")
            cards.append(rec)
    for d in decks:
        legends = [c["id"] for c in cards if c["deck"] == d["slug"] and c["rarity"] == "legendary"]
        d["cover"] = COVERS.get(d["slug"], legends[0] if legends else "")
    for tok in TOKENS:
        if tok["id"] in taken:
            raise SystemExit(f"token id {tok['id']!r} collides with a workbench card")
        taken.add(tok["id"])
        cards.append(tok)
    for rec in old:
        if rec["deck"] in KEPT_DECKS and rec["id"] not in taken:
            taken.add(rec["id"])
            cards.append(rec)
    for rec in old:
        if rec["id"] not in taken:
            notes.append(f"retired  {rec['id']:32} {rec['name']}")
    data = {"_comment": COMMENT, "decks": decks, "cards": cards}
    return data, notes


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("export", nargs="?", default=str(EXPORT))
    ap.add_argument("--check", action="store_true", help="list what would change; write nothing")
    args = ap.parse_args(argv)
    export = json.loads(Path(args.export).read_text())
    old = json.loads(CARDS.read_text())
    data, notes = convert(export, old)
    print("\n".join(notes) or "no changes")
    if args.check:
        return
    CARDS.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {CARDS.relative_to(ROOT)}: {len(data['decks'])} starter decks, {len(data['cards'])} cards",
          file=sys.stderr)


if __name__ == "__main__":
    main()
