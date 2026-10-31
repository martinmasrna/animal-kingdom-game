"""The card table's data: every card's values, read from and written to the game's own files, and how settled each one is.

The values live where the game keeps them, one place each: animal_kingdom/data/cards.json (habitat, rarity, name and
species, tags, strength, text, and the status: collectible, reserve, planned; the keywords are read from the text as it
is written), animal_kingdom/data/decklists.json (which starter deck a card ships in, and the starters' names) and
animal_kingdom/web/static/art.js (the crops). The cards the engine makes itself (tokens, evolution stages, the Eagle's
mate) are shown under the card that makes them; only their strength and text are edited here. The old pool's shelved cards (no
habitat) and the tutorial's deal stay off the table.

How settled each value is lives in tools/cards/levels.json, one entry per card id and column:
    {"lv": "empty|draft|problem|fine|locked", "note": "...", "by": "martin|claude", "review": {"prev": ..., "prev_lv": ...}}
A missing entry is draft when the value exists, else empty. `review` marks a change Claude made that Martin hasn't
seen; he accepts it (the mark goes) or reverts it (the old value and level come back).

The rule for Claude (by="claude"): a locked value is never changed; changing a fine one drops it to draft; Claude never
sets fine or locked. Martin's edits have no limits.

As a command, for Claude:
    .venv/bin/python tools/cards/hq.py show [ID...]                  the rows, as JSON
    .venv/bin/python tools/cards/hq.py set ID COLUMN VALUE [--note N] a value (animal: "Name/Species" for a legendary)
    .venv/bin/python tools/cards/hq.py level ID COLUMN LEVEL [--note N]
    .venv/bin/python tools/cards/hq.py move ID DECK                  into a starter deck (its slug), or `pool` for none
    .venv/bin/python tools/cards/hq.py shelve ID                     a card in no starter out of the collection (into the reserve)
    .venv/bin/python tools/cards/hq.py collect ID                    a reserve card into the collection (the reverse of shelve)
    .venv/bin/python tools/cards/hq.py deck-name DECK NAME           a starter deck's name
    .venv/bin/python tools/cards/hq.py delete ID                     a card out of the game entirely
    .venv/bin/python tools/cards/hq.py rename OLD NEW                a new id everywhere (when its animal changes)
    .venv/bin/python tools/cards/hq.py crop ID [--crop x,y,d|reset] [--strip x,y,z|reset] [--full y|reset]   (all three reset: no painting)
    .venv/bin/python tools/cards/hq.py add NAME HABITAT [--species S]   a planned card: animal and habitat only
    .venv/bin/python tools/cards/hq.py token MAKER ID NAME STR [--tags T,U]   a token MAKER's effect places
    .venv/bin/python tools/cards/hq.py untoken MAKER ID              a token MAKER no longer makes (out of the game when nothing else makes it)
    .venv/bin/python tools/cards/hq.py link MAKER ID                 an existing card MAKER's effect brings in, shown beside it when read
    .venv/bin/python tools/cards/hq.py related MAKER ID,ID           the cards shown beside MAKER, set exactly (no repeats)
    .venv/bin/python tools/cards/hq.py stage MAKER ID TEXT            the next form MAKER evolves into (its rarity, name, strength, tags)

A planned card becomes a card (in the reserve) once it has a rarity and a strength. Every edit is checked against the
engine's card rules before it is written. This is the only way cards change: the workspace's hook
(hooks/cards-one-path.py, run before every tool call in Claude Code and in Codex) refuses direct edits of cards.json and
the crop tables in art.js.
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
sys.path.insert(0, str(ROOT))
from animal_kingdom.engine.cards import PLANNED, CardDataError, validate_card_record  # noqa: E402

CARDS = ROOT / "animal_kingdom" / "data" / "cards.json"
DECKLISTS = ROOT / "animal_kingdom" / "data" / "decklists.json"
ART_JS = ROOT / "animal_kingdom" / "web" / "static" / "art.js"
LEVELS = Path(__file__).parent / "levels.json"
PY = Path(sys.executable)   # the venv this runs in (bin/ on Unix, Scripts/ on Windows)

COLUMNS = ["habitat", "rarity", "animal", "tag", "strength", "effect", "art", "crop"]
VALUE_COLS = ["habitat", "rarity", "animal", "tag", "strength", "effect"]
LEVELS_ORDER = ["empty", "draft", "problem", "fine", "locked"]
HABITATS = ["Savanna", "Jungle", "Forest", "Meadow", "City", "Open Ocean",          # the launch six; the rest: docs/design/habitats.md
            "Deep Ocean", "Coral Reef", "Coast", "River and Lake", "Australia", "Islands", "Mountains", "Polar", "Desert",
            "Prehistoric", "Ice Age"]
RARITY = {"L": "legendary", "R": "rare", "C": "common"}
LETTER = {v: k for k, v in RARITY.items()}
COPIES = {"legendary": 1, "rare": 2, "common": 3}     # the 4-4-6 copy limits: a starter holds each card at its limit
POOL = "pool"                                         # the table's name for "in no starter deck"

# Printed keywords, as the first sentences of a card's text ("Flight. Roar: ...", "Titan. Hungry 4. ...").
KEYWORD = re.compile(r"(Flight|Armor|Stealth|Spikes|Poison|Roam|Reach|Apex Predator|Titan|Flee|Wild|Hungry (\d+))\.(?: |$)")
COSTS = re.compile(r"Costs (\d+) food")


class Refused(Exception):
    """An edit the rules don't allow (Claude on a locked value, or setting fine/locked)."""


def _read(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def _write(p: Path, data) -> None:
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1 if p == DECKLISTS else 2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(p)


def parse_text(text: str) -> dict:
    """The keywords a card's text opens with, Hungry's number, and a printed food cost."""
    out: dict = {"keywords": []}
    pos = 0
    while (m := KEYWORD.match(text, pos)):
        if m.group(2):
            out["keywords"].append("Hungry"); out["hungry"] = int(m.group(2))
        else:
            out["keywords"].append(m.group(1))
        pos = m.end()
    if (m := COSTS.search(text)):
        out["food_cost"] = int(m.group(1))
    return out


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

def _starters(decklists: dict) -> list[dict]:
    return [d for d in decklists["decks"] if d.get("starter")]


def load() -> dict:
    """Everything the page shows: the rows in table order, and the levels."""
    cards, decklists, art = _read(CARDS), _read(DECKLISTS), read_art()
    levels = _read(LEVELS) if LEVELS.exists() else {}
    starter_of = {cid: d["slug"] for d in _starters(decklists) for cid in d["cards"]}
    rows = []
    for c in cards["cards"]:
        token = c["status"] == "token"
        if c["status"] == "tutorial" or (c["status"] == "reserve" and not c.get("habitat")):
            continue
        rows.append({
            "id": c["id"], "deck": "token" if token else starter_of.get(c["id"], POOL), "status": c["status"],
            "editable": not token, "habitat": c.get("habitat", ""), "rarity": LETTER.get(c["rarity"], ""),
            "name": "" if c.get("unnamed") else c["name"], "species": c.get("species", ""),
            "tag": ", ".join(c.get("tags", [])), "str": "*" if c["base_strength"] == "dynamic" else c["base_strength"],
            "text": c.get("text", ""), "related": c.get("related", []), "evolves": bool(c.get("evolves")),
            "art": c["id"] in art["CROP"],
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
        return not v and r["deck"] != "token"   # a token may have no text
    return v is None or v is False or v == ""


def cell(levels: dict, r: dict, col: str) -> dict:
    e = dict(levels.get(r["id"], {}).get(col, {}))
    if _blank(r, col):
        e.setdefault("lv", "empty")
    e.setdefault("lv", "draft")
    return e


def stamp() -> float:
    return max(p.stat().st_mtime for p in (CARDS, DECKLISTS, ART_JS, LEVELS) if p.exists())


# ---------- edits ----------

def _levels() -> dict:
    return _read(LEVELS) if LEVELS.exists() else {}


def _row(card_id: str) -> dict:
    for r in load()["rows"]:
        if r["id"] == card_id:
            return r
    raise KeyError(f"no card {card_id!r}")


def _rec(cards: dict, card_id: str) -> dict:
    return next(c for c in cards["cards"] if c["id"] == card_id)


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


def _save_cards(cards: dict) -> None:
    """Check every card the edit touched against the engine's rules, then write cards.json and the deck docs' tables."""
    for c in cards["cards"]:
        if c["status"] != PLANNED:
            try:
                validate_card_record(c)
            except CardDataError as e:
                raise Refused(str(e)) from None
    _write(CARDS, cards)
    subprocess.run([str(PY), "-m", "animal_kingdom.render.deck_docs"], cwd=ROOT, capture_output=True)


def _apply_value(r: dict, col: str, value) -> None:
    cards = _read(CARDS)
    c = _rec(cards, r["id"])
    if col == "habitat":
        c["habitat"] = value
    elif col == "rarity":
        c["rarity"] = RARITY[value] if value else ""
        if c["rarity"]:
            decklists = _read(DECKLISTS)
            for d in _starters(decklists):
                if c["id"] in d["cards"]:    # capped at the new limit, never raised: the deck stays 30
                    d["cards"][c["id"]] = min(d["cards"][c["id"]], COPIES[c["rarity"]])
            _write(DECKLISTS, decklists)
    elif col == "animal":
        name, species = value.get("name", "").strip(), value.get("species", "").strip()
        if c["rarity"] != "legendary":
            name = name or species
            species = species or name
        c["species"] = species
        if name:
            c["name"] = name
            c.pop("unnamed", None)
        else:                                   # a legendary waiting for its name: plainly a placeholder
            c["name"], c["unnamed"] = f"[{species.upper()}]", True
    elif col == "tag":
        c["tags"] = [t.strip() for t in value.split(",") if t.strip()]
    elif col == "strength":
        if c["base_strength"] == "dynamic":
            raise Refused(f"{c['id']}'s strength is worked out by the engine ({c.get('dynamic_strength')})")
        c["base_strength"] = None if value in ("", None) else int(value)
    elif col == "effect":
        c["text"] = value.strip()
        for k in ("keywords", "hungry", "food_cost"):
            c.pop(k, None)
        c.update(parse_text(c["text"]))
    if c["status"] == PLANNED and c["rarity"] and c["base_strength"] is not None:
        c["status"] = "reserve"                 # designed enough to be a card; collect puts it in the collection
    _save_cards(cards)


TOKEN_COLS = ("strength", "effect", "rarity")   # what a token's card says, and its frame (a legendary's stages wear its gold); where it sits stays its maker's business


def set_value(card_id: str, col: str, value, by: str = "martin", note: str | None = None) -> str:
    r = _row(card_id)
    if col not in VALUE_COLS or not (r["editable"] or col in TOKEN_COLS):
        raise Refused(f"{r['id']} {col} isn't editable here")
    cur = _guard(r, col, by)
    prev = value_of(r, col)
    if col == "strength" and value not in ("", None):
        value = int(value)
    if value == prev:
        return ""
    _apply_value(r, col, value)
    levels = _levels()
    new_lv = None
    if cur["lv"] == "empty":
        new_lv = "draft"
    if by == "claude" and cur["lv"] == "fine":
        new_lv = "draft"
    _mark(levels, r, col, by, new_lv, note, prev, True)
    _write(LEVELS, levels)
    return f"{r['id']} {col}: {prev!r} -> {value!r}"


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
        write_art(r["id"], "CROP", None if crop == "reset" else crop)
    if strip is not None:
        write_art(r["id"], "STRIP", None if strip == "reset" else strip)
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
    e["lv"] = rv["prev_lv"]
    if rv.get("prev_note"):
        e["note"] = rv["prev_note"]
    else:
        e.pop("note", None)
    e["by"] = "martin"
    _write(LEVELS, levels)


def move(card_id: str, deck: str, by: str = "martin") -> str:
    """Put a card in a starter deck (decklists.json, at its rarity's copy limit; starters share no card, so it leaves any
    other), or with `pool` in none. A card in a starter is collectible. Claude can't move a card with a locked value;
    the move is noted on its animal for Martin's review."""
    r = _row(card_id)
    decklists = _read(DECKLISTS)
    starters = {d["slug"]: d for d in _starters(decklists)}
    if deck != POOL and deck not in starters:
        raise Refused(f"no starter deck {deck!r}: one of {sorted(starters)} or {POOL}")
    if r["deck"] == deck:
        return ""
    if by == "claude" and any(r["lv"][c]["lv"] == "locked" for c in VALUE_COLS):
        raise Refused(f"{r['id']} has a locked value; ask Martin")
    cards = _read(CARDS)
    c = _rec(cards, r["id"])
    if deck != POOL and not c["rarity"]:
        raise Refused(f"{r['id']} has no rarity yet")
    for d in starters.values():
        d["cards"].pop(c["id"], None)
    if deck != POOL:
        starters[deck]["cards"][c["id"]] = COPIES[c["rarity"]]
        if c["status"] != "collectible":
            c["status"] = "collectible"
            _save_cards(cards)
    _write(DECKLISTS, decklists)
    levels = _levels()
    _mark(levels, r, "animal", by, None, f"moved from {r['deck']} to {deck}")
    _write(LEVELS, levels)
    return f"{r['id']}: {r['deck']} -> {deck}"


def add(name: str, habitat: str, species: str = "") -> str:
    """A planned card: only its animal and habitat, everything else blank (the engine doesn't load it until it has a
    rarity and a strength). Returns its id."""
    cards = _read(CARDS)
    cid = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    if any(name.lower() in (c["name"].lower(), c.get("species", "").lower()) or c["id"] == cid for c in cards["cards"]):
        raise Refused(f"{name} already has a card")
    cards["cards"].append({"id": cid, "name": name, "status": PLANNED, "rarity": "", "tags": [], "base_strength": None,
                           "text": "", "keywords": [], "species": species or name, "habitat": habitat})
    _save_cards(cards)
    return cid


def add_token(maker: str, cid: str, name: str, strength: int, tags: list[str]) -> str:
    """A token the engine makes for `maker` (a youngling, an egg): strength and tags, no text; shown under its maker."""
    cards = _read(CARDS)
    if any(c["id"] == cid for c in cards["cards"]):
        raise Refused(f"{cid} already exists")
    m = _rec(cards, _row(maker)["id"])
    cards["cards"].append({"id": cid, "name": name, "status": "token", "rarity": "common", "tags": tags,
                           "base_strength": strength, "keywords": [], "text": ""})
    m["related"] = [*m.get("related", []), cid]
    _save_cards(cards)
    return f"{cid}: a token of {maker}"


def untoken(maker: str, cid: str, by: str = "martin") -> str:
    """A token its maker no longer makes (the Queen Bee's Young Bee after her text changed, Martin 2026-10-31): out of
    the maker's related cards, and out of the game when no other card makes it."""
    cards = _read(CARDS)
    m = _rec(cards, _row(maker)["id"])
    if cid not in m.get("related", []):
        raise Refused(f"{cid} is not a token of {maker}")
    m["related"] = [k for k in m["related"] if k != cid]
    _save_cards(cards)
    if any(cid in c.get("related", []) for c in cards["cards"]):
        return f"{cid}: no longer a token of {maker}"
    cards["cards"] = [c for c in cards["cards"] if c["id"] != cid]
    _save_cards(cards)
    levels = _levels()
    levels.pop(cid, None)
    _write(LEVELS, levels)
    return f"{cid}: no longer a token of {maker}; nothing else makes it, so it is out of the game"


def link(maker: str, cid: str) -> str:
    """An existing card MAKER's effect brings in (the Queen Bee's Worker, Soldier and Nurse Bees), shown beside it when read
    large, as a token is (Martin, 2026-10-31)."""
    cards = _read(CARDS)
    m = _rec(cards, _row(maker)["id"])
    if not any(c["id"] == cid for c in cards["cards"]):
        raise Refused(f"no card {cid}")
    if cid in m.get("related", []):
        return f"{cid} is already shown beside {maker}"
    m["related"] = [*m.get("related", []), cid]
    _save_cards(cards)
    return f"{cid}: shown beside {maker}"


def set_related(maker: str, ids: list[str]) -> str:
    """The cards shown beside MAKER when read large, set exactly (no repeats, every id a card): what its effect makes,
    brings or becomes (Martin, 2026-10-31: the Queen Ant showed her Young Ant twice)."""
    cards = _read(CARDS)
    m = _rec(cards, _row(maker)["id"])
    seen = []
    for cid in ids:
        if not any(c["id"] == cid for c in cards["cards"]):
            raise Refused(f"no card {cid}")
        if cid not in seen:
            seen.append(cid)
    m["related"] = seen
    if not seen:
        m.pop("related", None)
    _save_cards(cards)
    return f"{maker}: shown with {', '.join(seen) or 'nothing'}"


def add_stage(maker: str, cid: str, text: str) -> str:
    """The next form an evolving card becomes, shown after its earlier forms (the legendary Butterfly's stages): the
    maker's rarity, name, strength and tags, its own text."""
    cards = _read(CARDS)
    if any(c["id"] == cid for c in cards["cards"]):
        raise Refused(f"{cid} already exists")
    m = _rec(cards, _row(maker)["id"])
    rec = {"id": cid, "name": m["name"], "status": "token", "rarity": m["rarity"], "tags": list(m.get("tags", [])),
           "base_strength": m["base_strength"], "keywords": [], "text": text, "stage": len(m.get("related", [])) + 2}
    validate_card_record(rec)
    cards["cards"].append(rec)
    m["related"], m["evolves"] = [*m.get("related", []), cid], True
    _save_cards(cards)
    return f"{cid}: form {rec['stage']} of {maker}"


def deck_name(deck: str, name: str) -> str:
    """Rename a starter deck (the name players see). A player's saved copy keeps the name it was saved with."""
    decklists = _read(DECKLISTS)
    starters = {d["slug"]: d for d in _starters(decklists)}
    if deck not in starters:
        raise Refused(f"no starter deck {deck!r}: one of {sorted(starters)}")
    if starters[deck]["name"] == name:
        return ""
    starters[deck]["name"] = name
    _write(DECKLISTS, decklists)
    return f"{deck}: {name}"


def _set_status(card_id: str, frm: str, to: str, note: str, by: str) -> str:
    r = _row(card_id)
    cards = _read(CARDS)
    c = _rec(cards, r["id"])
    if c["status"] != frm:
        return ""
    c["status"] = to
    _save_cards(cards)
    levels = _levels()
    _mark(levels, r, "animal", by, None, note)
    _write(LEVELS, levels)
    return f"{r['id']}: {frm} -> {to}"


def shelve(card_id: str, by: str = "martin") -> str:
    """Take a card out of the collection, into the reserve (kept, not collectible); it leaves its starter deck too."""
    move(card_id, POOL, by)
    return _set_status(card_id, "collectible", "reserve", "out of the collection (in the reserve)", by)


def collect(card_id: str, by: str = "martin") -> str:
    """Put a reserve card into the collection. The reverse of shelve."""
    return _set_status(card_id, "reserve", "collectible", "into the collection", by)


# ---------- ids ----------

RENAMED = ROOT / "animal_kingdom" / "web" / "renamed.py"
CARDNUMS = ROOT / "animal_kingdom" / "web" / "static" / "cardnums.js"
DESIGN = ROOT.parent / "design"
# Records of what happened, kept as written: the human games, the players' news, the design repo's art rounds.
HISTORY = ("results/", "animal_kingdom/web/news/")
TEXT = (".py", ".js", ".mjs", ".json", ".jsonl", ".md", ".html", ".css", ".txt", ".toml", ".sh")


def _git_files(repo: Path) -> list[str]:
    return subprocess.run(["git", "-C", str(repo), "ls-files"], capture_output=True, text=True, check=True).stdout.split("\n")


def rename(old: str, new: str) -> str:
    """Give a card a new id everywhere the game knows it: the card data, the levels, the starter and bot decks, the crops,
    the code, tests and docs, its painting (here and the design repo's master); its deck-code number stays, and players'
    saved decks, old replays and saved matches follow it through the rename map (web/renamed.py, SUCCESSOR). Ids name the
    card's animal (AGENTS.md, Invariants), so a card changes id when its animal does, never when its name does."""
    ids = {c["id"] for c in _read(CARDS)["cards"]}
    if old not in ids:
        raise Refused(f"no card {old}")
    if new in ids or not re.fullmatch(r"[a-z][a-z0-9_]*", new):
        raise Refused(f"{new} is taken or not an id")
    # the id as a word, or leading a code name built on it (_goose_legend_roar, goose_legend_eggs), but never another card's id (eon_food_engine)
    word = re.compile(rf"(?<![A-Za-z0-9_])(_?){re.escape(old)}(?=(_[a-z0-9_]+)?(?![A-Za-z0-9_]))")
    # only where it's plainly an id: quoted ("rodent", `rodent`) or in a code name; a bare word is prose (a rodent), left alone
    def is_id(m: re.Match) -> bool:
        s, i, j = m.string, m.start(), m.end(2) if m.group(2) else m.end()
        return bool(m.group(1) or m.group(2)) or (i > 0 and j < len(s) and s[i - 1] in "\"'`" and s[j] in "\"'`")
    def sub(text: str) -> str:
        return word.sub(lambda m: m.group(0) if not is_id(m) or (m.group(2) and old + m.group(2) in ids)
                        else m.group(1) + new, text)
    changed = 0
    for f in _git_files(ROOT):
        p = ROOT / f
        if not f or f.startswith(HISTORY) or not f.endswith(TEXT) or not p.is_file():
            continue
        src = p.read_text(encoding="utf-8")
        out = sub(src)
        if out != src:
            p.write_text(out, encoding="utf-8"); changed += 1
    for f in _git_files(ROOT):    # its painting
        if Path(f).stem == old and Path(f).parent.name == "art":
            subprocess.run(["git", "-C", str(ROOT), "mv", f, str(Path(f).with_name(new + Path(f).suffix))], check=True)
    # the rename map: players' decks and old replays follow the card (its deck-code number already means it, kept in place)
    src = RENAMED.read_text(encoding="utf-8")
    RENAMED.write_text(src.replace("RENAMED_IDS = {", f'RENAMED_IDS = {{"{old}": "{new}", ', 1), encoding="utf-8")
    src = CARDNUMS.read_text(encoding="utf-8")
    CARDNUMS.write_text(src.replace("export const SUCCESSOR = { ", f"export const SUCCESSOR = {{ {old}: '{new}', ", 1), encoding="utf-8")
    if DESIGN.is_dir():   # the master painting, and the art rounds' manifest that installs and counts it
        for ext in (".png", ".jpg"):
            if (DESIGN / "cards" / (old + ext)).is_file():
                subprocess.run(["git", "-C", str(DESIGN), "mv", f"cards/{old}{ext}", f"cards/{new}{ext}"], check=True)
        man = DESIGN / "cards" / "bar" / "manifest.jsonl"
        if man.is_file():
            man.write_text(re.sub(rf'"card": "{re.escape(old)}"', f'"card": "{new}"', man.read_text(encoding="utf-8")), encoding="utf-8")
    subprocess.run([str(PY), "-m", "animal_kingdom.render.deck_docs"], cwd=ROOT, capture_output=True)
    return f"{old} -> {new} ({changed} files)"


def delete(card_id: str, by: str = "martin") -> str:
    """Remove a card from the game: out of cards.json and the starter decks, and its levels gone. Its number in
    static/cardnums.js stays, since deck codes depend on every number. Claude can't delete a card with a locked value."""
    cards = _read(CARDS)
    if any(c["id"] == card_id and c["status"] == "reserve" and not c.get("habitat") for c in cards["cards"]):
        r = {"id": card_id}                       # a sim fixture the table hides (no habitat): nothing of Martin's to lock
    else:
        r = _row(card_id)
        if by == "claude" and any(r["lv"][c]["lv"] == "locked" for c in VALUE_COLS):
            raise Refused(f"{r['id']} has a locked value; ask Martin")
    cards["cards"] = [c for c in cards["cards"] if c["id"] != r["id"]]
    _save_cards(cards)
    decklists = _read(DECKLISTS)
    for d in _starters(decklists):
        d["cards"].pop(r["id"], None)
    _write(DECKLISTS, decklists)
    levels = _levels()
    levels.pop(r["id"], None)
    _write(LEVELS, levels)
    return f"deleted {r['id']}"


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="The card table, for Claude: every edit is marked for Martin's review.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show"); s.add_argument("ids", nargs="*")
    s = sub.add_parser("set"); s.add_argument("id"); s.add_argument("col", choices=VALUE_COLS); s.add_argument("value"); s.add_argument("--note")
    s = sub.add_parser("level"); s.add_argument("id"); s.add_argument("col", choices=COLUMNS); s.add_argument("lv", choices=LEVELS_ORDER); s.add_argument("--note")
    s = sub.add_parser("note"); s.add_argument("id"); s.add_argument("col", choices=COLUMNS); s.add_argument("note")
    s = sub.add_parser("move"); s.add_argument("id"); s.add_argument("deck")
    s = sub.add_parser("shelve"); s.add_argument("id")
    s = sub.add_parser("collect"); s.add_argument("id")
    s = sub.add_parser("deck-name"); s.add_argument("deck"); s.add_argument("name")
    s = sub.add_parser("delete"); s.add_argument("id")
    s = sub.add_parser("rename"); s.add_argument("old"); s.add_argument("new")
    s = sub.add_parser("add"); s.add_argument("name"); s.add_argument("habitat", choices=HABITATS); s.add_argument("--species", default="")
    s = sub.add_parser("stage"); s.add_argument("maker"); s.add_argument("id"); s.add_argument("text")
    s = sub.add_parser("token"); s.add_argument("maker"); s.add_argument("id"); s.add_argument("name"); s.add_argument("strength", type=int); s.add_argument("--tags", default="")
    s = sub.add_parser("untoken"); s.add_argument("maker"); s.add_argument("id")
    s = sub.add_parser("link"); s.add_argument("maker"); s.add_argument("id")
    s = sub.add_parser("related"); s.add_argument("maker"); s.add_argument("ids", help="comma-separated card ids, in the order they come; empty for none")
    s = sub.add_parser("crop"); s.add_argument("id"); s.add_argument("--crop"); s.add_argument("--strip"); s.add_argument("--full")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "show":
            rows = load()["rows"]
            print(json.dumps([r for r in rows if not a.ids or r["id"] in a.ids], ensure_ascii=False, indent=1))
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
        elif a.cmd == "move":
            print(move(a.id, a.deck, "claude"))
        elif a.cmd == "shelve":
            print(shelve(a.id, "claude"))
        elif a.cmd == "collect":
            print(collect(a.id, "claude"))
        elif a.cmd == "deck-name":
            print(deck_name(a.deck, a.name))
        elif a.cmd == "delete":
            print(delete(a.id, "claude"))
        elif a.cmd == "rename":
            print(rename(a.old, a.new))
        elif a.cmd == "add":
            print(add(a.name, a.habitat, a.species))
        elif a.cmd == "stage":
            print(add_stage(a.maker, a.id, a.text))
        elif a.cmd == "token":
            print(add_token(a.maker, a.id, a.name, a.strength, [t for t in a.tags.split(",") if t]))
        elif a.cmd == "untoken":
            print(untoken(a.maker, a.id, "claude"))
        elif a.cmd == "link":
            print(link(a.maker, a.id))
        elif a.cmd == "related":
            print(set_related(a.maker, [x for x in a.ids.split(",") if x]))
        elif a.cmd == "crop":
            nums = lambda v: "reset" if v == "reset" else [float(x) for x in v.split(",")] if v else None
            full = None if a.full is None else "reset" if a.full == "reset" else float(a.full)
            set_crop(a.id, nums(a.crop), nums(a.strip), full, "claude")
    except (Refused, KeyError) as e:
        sys.exit(f"refused: {e}")


if __name__ == "__main__":
    main()
