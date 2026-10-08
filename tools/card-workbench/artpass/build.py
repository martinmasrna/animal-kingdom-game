"""Build the art-pass review page from the game's data and art.

    .venv/bin/python tools/card-workbench/artpass/build.py

Writes results/artpass/index.html (template.html with the cards embedded) and prints the `files` map to publish
alongside it (each art file at art/<id>.webp). Reviews live in the artifact's database, keyed by the workbench card
id, so they survive renames and republishes. Launch decks only; the Pool waits for its habitats.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).parent
ART = ROOT / "animal_kingdom/web/static/art"
HABITATS = ["Savanna", "Forest", "Meadow", "Jungle", "City", "Open Ocean"]
RARITY = {"C": "common", "R": "rare", "L": "legendary"}


def main() -> None:
    export = json.loads((ROOT / "tools/card-workbench/export.json").read_text())["decks"]
    data = json.loads((ROOT / "animal_kingdom/data/cards.json").read_text())
    by_wb = {c["workbench_id"]: c for c in data["cards"] if c.get("workbench_id")}
    have = {p.stem for p in ART.glob("*.webp")}
    cards, used = [], set()
    for deck_key, deck in export.items():
        if deck_key == "pool":
            continue
        for wc in deck["cards"]:
            rec = by_wb.get(wc["id"])
            cid = rec["id"] if rec else None
            art = cid if cid in have else None
            if art:
                used.add(art)
            cards.append({"key": wc["id"], "name": wc["name"].strip(), "species": wc["species"], "rarity": wc["rarity"],
                          "str": wc["str"], "tag": wc["tag"], "habitat": wc["habitat"], "text": wc["text"],
                          "deck": deck["name"], "art": art, "status": wc.get("status", "")})
    orphans = sorted(have - used - {"back"})
    payload = {"habitats": HABITATS, "cards": cards, "orphans": orphans}
    html = (HERE / "template.html").read_text().replace("/*DATA*/null", json.dumps(payload, ensure_ascii=False))
    out = ROOT / "results/artpass"
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(html)
    files = {f"art/{a}.webp": str((ART / f"{a}.webp").relative_to(ROOT)) for a in sorted(used | set(orphans))}
    (out / "files.json").write_text(json.dumps(files, indent=1))
    print(f"{len(cards)} cards, {len(used)} with art, {len(orphans)} orphan art files; files map in results/artpass/files.json")


if __name__ == "__main__":
    main()
