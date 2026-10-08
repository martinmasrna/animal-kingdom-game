"""Build the legendary-naming page: every legendary with its current name, effect, art and candidate names.

    .venv/bin/python tools/card-workbench/names/build.py

Writes results/names/index.html (template.html with the data embedded) and results/names/files.json (the art files to
publish alongside). Candidates come from candidates.json, matched to a card by "<current name or species> (<deck>)";
picks and notes live in the artifact's database under `picks/<workbench id>`.
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).parent
ART = ROOT / "animal_kingdom/web/static/art"
DECK = {"Canines": "canines", "Cats": "cats", "Colony": "colony", "Den Rush": "den-rush", "Egg Control": "egg-control",
        "Fish": "fish", "Food Aggro": "food-aggro", "Food OTK": "food-otk", "Giants": "giants", "Handlock": "handlock",
        "Hoofed": "hoofed", "Aristocrats": "aristocrats", "pool": "pool"}
# Names that cite a work, a character or a real individual (draft rule 3).
CITES = {"Scrooge": "Dickens", "Falstaff": "Shakespeare", "Raksha": "The Jungle Book", "Mocha": "Mocha Dick, the real whale",
         "Lobo": "the real wolf of Seton's story"}


def main() -> None:
    export = json.loads((ROOT / "tools/card-workbench/export.json").read_text())["decks"]
    data = json.loads((ROOT / "animal_kingdom/data/cards.json").read_text())
    by_wb = {c["workbench_id"]: c for c in data["cards"] if c.get("workbench_id")}
    have = {p.stem for p in ART.glob("*.webp")}
    cands = {}
    for row in json.loads((HERE / "candidates.json").read_text()):
        m = re.match(r"(.+?)(?: → .+?)? \((.+?)\)$", row["card"])
        cands[(m.group(1).strip(), DECK[m.group(2)])] = row["candidates"]
    out, files = [], {}
    for dk, deck in export.items():
        for wc in deck["cards"]:
            if wc["rarity"] != "L":
                continue
            name = wc["name"].strip()
            rec = by_wb.get(wc["id"])
            art = rec["id"] if rec and rec["id"] in have else None
            if art:
                files[f"art/{art}.webp"] = str((ART / f"{art}.webp").relative_to(ROOT))
            out.append({"key": wc["id"], "name": name, "species": wc["species"], "deck": deck["name"], "pool": dk == "pool",
                        "text": wc["text"], "str": wc["str"], "status": wc.get("status", ""), "art": art,
                        "cites": CITES.get(name), "candidates": cands.get((name or wc["species"], dk), [])})
    html = (HERE / "template.html").read_text().replace("/*DATA*/null", json.dumps(out, ensure_ascii=False))
    dest = ROOT / "results/names"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "index.html").write_text(html)
    (dest / "files.json").write_text(json.dumps(files, indent=1))
    print(f"{len(out)} legendaries, {sum(1 for o in out if not o['name'])} unnamed, "
          f"{sum(1 for o in out if o['candidates'])} with candidates, {len(files)} art files")


if __name__ == "__main__":
    main()
