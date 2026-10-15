"""The card table's data: every card's values, read from and written to the game's own files, and how settled each one is.

The values live where the game keeps them: tools/card-workbench/decks.json (habitat, rarity, name and species, tag,
strength, text; convert.py then rewrites animal_kingdom/data/cards.json) and animal_kingdom/web/static/art.js (the
crops). The engine makes some cards itself (tokens, evolution stages, the Eagle's mate); they are listed in convert.py,
shown under the card that makes them, and their values are read-only here.

How settled each value is lives in tools/cards/levels.json, one entry per card and column:
    {"lv": "empty|draft|problem|fine|locked", "note": "...", "by": "martin|claude", "review": {"prev": ..., "prev_lv": ...}}
A missing entry is draft when the value exists, else empty. `review` marks a change Claude made that Martin hasn't
seen; he accepts it (the mark goes) or reverts it (the old value and level come back).

The rule for Claude (by="claude"): a locked value is never changed; changing a fine one drops it to draft; Claude never
sets fine or locked. Martin's edits have no limits.

As a command, for Claude:
    .venv/bin/python tools/cards/hq.py show [ID...]                  the rows, as JSON
    .venv/bin/python tools/cards/hq.py set ID COLUMN VALUE [--note N] a value (animal: "Name/Species" for a legendary)
    .venv/bin/python tools/cards/hq.py level ID COLUMN LEVEL [--note N]
    .venv/bin/python tools/cards/hq.py crop ID [--crop x,y,d] [--strip x,y,z] [--full y|reset]
    .venv/bin/python tools/cards/hq.py add NAME HABITAT [--species S]   a planned card: animal and habitat only

This is the only way cards change: a hook (.claude/hooks/cards-one-path.py) refuses direct edits of decks.json,
cards.json and the crop tables in art.js.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DECKS = ROOT / "tools" / "card-workbench" / "decks.json"
CARDS = ROOT / "animal_kingdom" / "data" / "cards.json"
ART_JS = ROOT / "animal_kingdom" / "web" / "static" / "art.js"
LEVELS = Path(__file__).parent / "levels.json"
PY = ROOT / ".venv" / "bin" / "python"

COLUMNS = ["habitat", "rarity", "animal", "tag", "strength", "effect", "art", "crop"]
VALUE_COLS = ["habitat", "rarity", "animal", "tag", "strength", "effect"]
LEVELS_ORDER = ["empty", "draft", "problem", "fine", "locked"]
HABITATS = ["Savanna", "Jungle", "Forest", "Meadow", "City", "Open Ocean", "Polar", "Desert", "Mountains", "Australia", "Ice Age"]
RARITY = {"L": "legendary", "R": "rare", "C": "common"}


class Refused(Exception):
    """An edit the rules don't allow (Claude on a locked value, or setting fine/locked)."""


def _read(p: Path):
    return json.loads(p.read_text())


def _write(p: Path, data) -> None:
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1 if p == DECKS else 2, ensure_ascii=False) + ("" if p == DECKS else "\n"))
    tmp.replace(p)


# ---------- art.js ----------

TABLES = ("CROP", "STRIP", "FULL")


def _table_span(src: str, name: str) -> tuple[int, int]:
    m = re.search(rf"export const {name} = \{{\n", src)
    end = src.index("\n};", m.end())
    return m.end(), end


def _num(s: str):
    return json.loads(re.sub(r"(?<![\d])\.(\d)", r"0.\1", s))


def read_art() -> dict:
    src = ART_JS.read_text()
    out = {}
    for t in TABLES:
        a, b = _table_span(src, t)
        body = src[a:b]
        out[t] = {m.group(1): _num(m.group(2)) for m in re.finditer(r"\b([a-z0-9_]+): (\[[^\]]*\]|[\d.]+)", body)}
    return out


def _fmt(v) -> str:
    f = lambda x: (f"{round(x, 3):g}".replace("0.", ".", 1) if 0 < abs(x) < 1 else f"{round(x, 3):g}")
    return "[" + ", ".join(f(x) for x in v) + "]" if isinstance(v, list) else f(v)


def write_art(card_id: str, table: str, value) -> None:
    """Set (or with None remove) one card's entry in CROP, STRIP or FULL, keeping the file's layout."""
    src = ART_JS.read_text()
    a, b = _table_span(src, table)
    body = src[a:b]
    pat = re.compile(rf"(?<![a-z0-9_]){re.escape(card_id)}: (\[[^\]]*\]|[\d.]+),? ?")
    m = pat.search(body)
    if value is None:
        body = pat.sub("", body, count=1) if m else body
        body = re.sub(r"\n  \n", "\n", body)
    elif m:
        body = body[:m.start()] + f"{card_id}: {_fmt(value)}," + (" " if body[m.end() - 1:m.end()] == " " else "") + body[m.end():]
    else:
        body = f"  {card_id}: {_fmt(value)},\n" + body
    ART_JS.write_text(src[:a] + body + src[b:])


# ---------- rows ----------

def _deck_index(decks: dict) -> dict:
    return {c["id"]: (slug, i) for slug, d in decks["decks"].items() for i, c in enumerate(d["cards"])}


def load() -> dict:
    """Everything the page shows: the rows in table order, and the levels."""
    decks, cards, art = _read(DECKS), _read(CARDS), read_art()
    levels = _read(LEVELS) if LEVELS.exists() else {}
    by_wid = {c["workbench_id"]: c for c in cards["cards"] if c.get("workbench_id")}
    by_id = {c["id"]: c for c in cards["cards"]}
    rows = []
    for slug, d in decks["decks"].items():
        for wc in d["cards"]:
            eng = by_wid.get(wc["id"])
            key = eng["id"] if eng else wc["id"]
            rows.append({
                "id": key, "wid": wc["id"], "deck": slug, "editable": True,
                "habitat": wc.get("habitat", ""), "rarity": wc["rarity"], "name": wc["name"].strip(),
                "species": wc.get("species", ""), "tag": wc.get("tag", ""), "str": wc.get("str"),
                "text": wc.get("text", ""), "related": (eng or {}).get("related", []), "evolves": bool((eng or {}).get("evolves")),
                "art": key in art["CROP"],
            })
    for c in cards["cards"]:
        if c["deck"] != "token":
            continue
        rows.append({
            "id": c["id"], "wid": None, "deck": "token", "editable": False, "habitat": "",
            "rarity": {"legendary": "L", "rare": "R"}.get(c["rarity"], "C"), "name": c["name"], "species": "",
            "tag": ", ".join(c.get("tags", [])), "str": c["base_strength"], "text": c.get("text", ""),
            "related": [], "evolves": False, "art": c["id"] in art["CROP"],
        })
    ids = {r["id"] for r in rows}
    parent = {}
    for r in rows:
        for k in r["related"]:
            if k in ids and k not in parent and k != r["id"]:
                parent[k] = r["id"]
    for r in rows:
        r["parent"] = parent.get(r["id"])
        if r["parent"] and not r["habitat"]:
            r["habitat"] = next(x["habitat"] for x in rows if x["id"] == r["parent"])
    for r in rows:
        r["lv"] = {col: cell(levels, r, col) for col in COLUMNS}
    return {"rows": rows, "crops": {t: art[t] for t in TABLES}, "habitats": HABITATS, "stamp": stamp()}


def value_of(r: dict, col: str):
    return {"habitat": r["habitat"], "rarity": r["rarity"], "animal": {"name": r["name"], "species": r["species"]},
            "tag": r["tag"], "strength": r["str"], "effect": r["text"], "art": r["art"], "crop": r["art"]}[col]


def _blank(r: dict, col: str) -> bool:
    v = value_of(r, col)
    if col == "animal":
        return not (v["name"] if r["rarity"] == "L" else (v["name"] or v["species"]))
    if col == "effect":
        return not v and r["deck"] != "token"   # a vanilla animal says so with "—"; a token may have no text
    return v is None or v is False or v == ""


def cell(levels: dict, r: dict, col: str) -> dict:
    e = dict(levels.get(r["id"], {}).get(col, {}))
    if _blank(r, col):
        e.setdefault("lv", "empty")
    e.setdefault("lv", "draft")
    return e


def stamp() -> float:
    return max(p.stat().st_mtime for p in (DECKS, CARDS, ART_JS, LEVELS) if p.exists())


# ---------- edits ----------

def _levels() -> dict:
    return _read(LEVELS) if LEVELS.exists() else {}


def _row(card_id: str) -> dict:
    for r in load()["rows"]:
        if r["id"] == card_id or r["wid"] == card_id:
            return r
    raise KeyError(f"no card {card_id!r}")


def _guard(r: dict, col: str, by: str) -> dict:
    cur = r["lv"][col]
    if by == "claude" and cur["lv"] == "locked":
        raise Refused(f"{r['id']} {col} is locked; ask Martin")
    return cur


def _mark(levels: dict, r: dict, col: str, by: str, new_lv: str | None, note: str | None, prev_value=None, changed_value=False):
    cur = r["lv"][col]
    e = levels.setdefault(r["id"], {}).setdefault(col, {})
    if by == "claude" and "review" not in e:
        e["review"] = {"prev_lv": cur["lv"], "prev_note": cur.get("note", "")}
        if changed_value:
            e["review"]["prev"] = prev_value
    if by == "martin":
        e.pop("review", None)
    if new_lv:
        e["lv"] = new_lv
    if note is not None:
        if note:
            e["note"] = note
        else:
            e.pop("note", None)
    e["by"], e["at"] = by, int(time.time())


def regenerate() -> str:
    """cards.json from decks.json, then the deck docs' tables. Returns convert's report."""
    out = subprocess.run([str(PY), "tools/card-workbench/convert.py"], cwd=ROOT, capture_output=True, text=True)
    if out.returncode:
        raise RuntimeError(out.stderr or out.stdout)
    subprocess.run([str(PY), "-m", "animal_kingdom.render.deck_docs"], cwd=ROOT, capture_output=True)
    return "\n".join(l for l in out.stdout.splitlines() if not l.startswith("skipped "))   # planned cards: no strength yet


def _apply_value(r: dict, col: str, value) -> None:
    decks = _read(DECKS)
    slug, i = _deck_index(decks)[r["wid"]]
    wc = decks["decks"][slug]["cards"][i]
    if col == "habitat":
        wc["habitat"] = value
    elif col == "rarity":
        wc["rarity"] = value
    elif col == "animal":
        name, species = value.get("name", "").strip(), value.get("species", "").strip()
        if wc["rarity"] != "L":
            name = name or species
            species = species or name
        wc["name"], wc["species"] = name, species
    elif col == "tag":
        wc["tag"] = value.strip()
    elif col == "strength":
        wc["str"] = None if value in ("", None) else int(value)
    elif col == "effect":
        wc["text"] = value.strip()
    _write(DECKS, decks)


def set_value(card_id: str, col: str, value, by: str = "martin", note: str | None = None) -> str:
    r = _row(card_id)
    if col not in VALUE_COLS or not r["editable"]:
        raise Refused(f"{r['id']} {col} isn't editable here")
    cur = _guard(r, col, by)
    prev = value_of(r, col)
    if col == "strength" and value not in ("", None):
        value = int(value)
    if value == prev:
        return ""
    _apply_value(r, col, value)
    report = regenerate()
    levels = _levels()
    new_lv = None
    if cur["lv"] == "empty":
        new_lv = "draft"
    if by == "claude" and cur["lv"] == "fine":
        new_lv = "draft"
    _mark(levels, r, col, by, new_lv, note, prev, True)
    _write(LEVELS, levels)
    return report


def set_level(card_id: str, col: str, lv: str, by: str = "martin", note: str | None = None) -> None:
    if lv not in LEVELS_ORDER:
        raise Refused(f"no level {lv!r}")
    if by == "claude" and lv in ("fine", "locked"):
        raise Refused("only Martin marks a value fine or locked; leave a note instead")
    r = _row(card_id)
    _guard(r, col, by)
    levels = _levels()
    _mark(levels, r, col, by, lv, note)
    _write(LEVELS, levels)


def set_note(card_id: str, col: str, note: str, by: str = "martin") -> None:
    r = _row(card_id)
    levels = _levels()
    _mark(levels, r, col, by, None, note)
    _write(LEVELS, levels)


def set_crop(card_id: str, crop=None, strip=None, full=None, by: str = "martin") -> None:
    r = _row(card_id)
    cur = _guard(r, "crop", by)
    art = read_art()
    same = lambda t, v: v is None or (art[t].get(r["id"]) is None if v == "reset" else art[t].get(r["id"]) == v)
    if same("CROP", crop) and same("STRIP", strip) and same("FULL", full):
        return
    if crop is not None:
        write_art(r["id"], "CROP", crop)
    if strip is not None:
        write_art(r["id"], "STRIP", strip)
    if full is not None:
        write_art(r["id"], "FULL", None if full == "reset" else full)
    levels = _levels()
    prev = {t: art[t].get(r["id"]) for t in TABLES}
    _mark(levels, r, "crop", by, "draft" if by == "claude" and cur["lv"] == "fine" else None, None, prev, True)
    _write(LEVELS, levels)


def accept(card_id: str, col: str) -> None:
    r = _row(card_id)
    levels = _levels()
    levels.get(r["id"], {}).get(col, {}).pop("review", None)
    _write(LEVELS, levels)


def revert(card_id: str, col: str) -> None:
    """Undo Claude's unreviewed change: the old value, level and note come back."""
    r = _row(card_id)
    levels = _levels()
    e = levels.get(r["id"], {}).get(col, {})
    rv = e.pop("review", None)
    if not rv:
        return
    if "prev" in rv:
        if col == "crop":
            for t in TABLES:
                write_art(r["id"], t, rv["prev"][t])
        else:
            _apply_value(r, col, rv["prev"])
            regenerate()
    e["lv"] = rv["prev_lv"]
    if rv.get("prev_note"):
        e["note"] = rv["prev_note"]
    else:
        e.pop("note", None)
    e["by"] = "martin"
    _write(LEVELS, levels)


def add(name: str, habitat: str, species: str = "") -> str:
    """A planned card: only its animal and habitat, everything else blank (it waits in the pool; convert.py skips a card
    with no strength, so the game doesn't see it yet). Returns its id."""
    decks = _read(DECKS)
    pool = decks["decks"]["pool"]["cards"]
    if any((c["name"] or c["species"]).lower() == name.lower() for d in decks["decks"].values() for c in d["cards"]):
        raise Refused(f"{name} already has a card")
    wid = "pool-" + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    pool.append({"habitat": habitat, "id": wid, "name": name, "note": "", "rarity": "", "species": species or name,
                 "status": "open", "str": None, "tag": "", "text": ""})
    _write(DECKS, decks)
    return wid


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="The card table, for Claude: every edit is marked for Martin's review.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show"); s.add_argument("ids", nargs="*")
    s = sub.add_parser("set"); s.add_argument("id"); s.add_argument("col", choices=VALUE_COLS); s.add_argument("value"); s.add_argument("--note")
    s = sub.add_parser("level"); s.add_argument("id"); s.add_argument("col", choices=COLUMNS); s.add_argument("lv", choices=LEVELS_ORDER); s.add_argument("--note")
    s = sub.add_parser("note"); s.add_argument("id"); s.add_argument("col", choices=COLUMNS); s.add_argument("note")
    s = sub.add_parser("add"); s.add_argument("name"); s.add_argument("habitat", choices=HABITATS); s.add_argument("--species", default="")
    s = sub.add_parser("crop"); s.add_argument("id"); s.add_argument("--crop"); s.add_argument("--strip"); s.add_argument("--full")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "show":
            rows = load()["rows"]
            print(json.dumps([r for r in rows if not a.ids or r["id"] in a.ids or r["wid"] in a.ids], ensure_ascii=False, indent=1))
        elif a.cmd == "set":
            v = a.value
            if a.col == "animal":
                name, _, species = v.partition("/")
                v = {"name": name, "species": species}
            print(set_value(a.id, a.col, v, "claude", a.note))
        elif a.cmd == "level":
            set_level(a.id, a.col, a.lv, "claude", a.note)
        elif a.cmd == "note":
            set_note(a.id, a.col, a.note, "claude")
        elif a.cmd == "add":
            print(add(a.name, a.habitat, a.species))
        elif a.cmd == "crop":
            nums = lambda v: [float(x) for x in v.split(",")] if v else None
            full = None if a.full is None else "reset" if a.full == "reset" else float(a.full)
            set_crop(a.id, nums(a.crop), nums(a.strip), full, "claude")
    except (Refused, KeyError) as e:
        sys.exit(f"refused: {e}")


if __name__ == "__main__":
    main()
