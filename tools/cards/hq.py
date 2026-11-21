"""The card table's data: every card's values, read from and written to the game's own files, and how settled each one is.

The values live where the game keeps them, one place each: animal_kingdom/data/cards.json (rarity, name, strength, mana
cost, text, and the status: collectible, reserve, planned; the keywords are read from the text as it is written) and
animal_kingdom/web/static/art.js (the crops).

How settled each value is lives in tools/cards/levels.json, one entry per card id and column:
    {"lv": "empty|draft|problem|fine|locked", "note": "...", "by": "martin|claude", "review": {"prev": ..., "prev_lv": ...}}
A missing entry is draft when the value exists, else empty. `review` marks a change Claude made that Martin hasn't
seen; he accepts it (the mark goes) or reverts it (the old value and level come back).

The rule for Claude (by="claude"): a locked value is never changed; changing a fine one drops it to draft; Claude never
sets fine or locked. Martin's edits have no limits.

As a command, for Claude:
    .venv/bin/python tools/cards/hq.py show [ID...]                  the rows, as JSON
    .venv/bin/python tools/cards/hq.py set ID COLUMN VALUE [--note N] a value (cost: the mana cost, 0 or more)
    .venv/bin/python tools/cards/hq.py level ID COLUMN LEVEL [--note N]
    .venv/bin/python tools/cards/hq.py shelve ID                     a card out of the collection (into the reserve)
    .venv/bin/python tools/cards/hq.py collect ID                    a reserve card into the collection
    .venv/bin/python tools/cards/hq.py add ID NAME STRENGTH COST [--dynamic RULE] [--legendary]   a new collectible card
    .venv/bin/python tools/cards/hq.py delete ID                     a card out of the game entirely
    .venv/bin/python tools/cards/hq.py dynamic ID RULE               what a variable strength counts (a Shade's: engine/cards.py DYNAMIC_STRENGTHS)
    .venv/bin/python tools/cards/hq.py rename OLD NEW                a new id everywhere
    .venv/bin/python tools/cards/hq.py crop ID [--crop x,y,d|reset] [--strip x,y,z|reset] [--full y|reset]

Every edit is checked against the engine's card rules before it is written. This is the only way cards change: the
workspace's hook (hooks/cards-one-path.py, run before every tool call in Claude Code and in Codex) refuses direct edits
of cards.json and the crop tables in art.js.
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
from animal_kingdom.game import PLANNED, CardDataError, validate_card_record  # noqa: E402

CARDS = ROOT / "animal_kingdom" / "data" / "cards.json"
ART_JS = ROOT / "animal_kingdom" / "web" / "static" / "art.js"
LEVELS = Path(__file__).parent / "levels.json"
PY = Path(sys.executable)   # the venv this runs in (bin/ on Unix, Scripts/ on Windows)

COLUMNS = ["rarity", "animal", "strength", "cost", "effect", "art", "crop"]
VALUE_COLS = ["rarity", "animal", "strength", "cost", "effect"]
LEVELS_ORDER = ["empty", "draft", "problem", "fine", "locked"]
RARITY = {"L": "legendary", "C": "common"}
LETTER = {v: k for k, v in RARITY.items()}

# Printed keywords, as the first sentences of a card's text ("Flight. Roar: ...").
KEYWORD = re.compile(r"(Flight|Armor|Stealth|Spikes|Poison|Hungry)\.(?: |$)")


class Refused(Exception):
    """An edit the rules don't allow (Claude on a locked value, or setting fine/locked)."""


def _read(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def _write(p: Path, data) -> None:
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(p)


def parse_text(text: str) -> dict:
    """The keywords a card's text opens with."""
    out: dict = {"keywords": []}
    pos = 0
    while (m := KEYWORD.match(text, pos)):
        out["keywords"].append(m.group(1))
        pos = m.end()
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

def load() -> dict:
    """Everything the page shows: the rows in table order, and the levels."""
    cards, art = _read(CARDS), read_art()
    levels = _read(LEVELS) if LEVELS.exists() else {}
    rows = []
    for c in cards["cards"]:
        rows.append({
            "id": c["id"], "status": c["status"], "rarity": LETTER.get(c["rarity"], ""), "name": c["name"],
            "str": "*" if c["base_strength"] == "dynamic" else c["base_strength"], "cost": c.get("cost"),
            "text": c.get("text", ""), "art": c["id"] in art["CROP"],
        })
    for r in rows:
        r["lv"] = {col: cell(levels, r, col) for col in COLUMNS}
    return {"rows": rows, "crops": {t: art[t] for t in TABLES}, "stamp": stamp()}


def value_of(r: dict, col: str):
    return {"rarity": r["rarity"], "animal": r["name"], "strength": r["str"], "cost": r["cost"], "effect": r["text"],
            "art": r["art"], "crop": r["art"]}[col]


def _blank(r: dict, col: str) -> bool:
    v = value_of(r, col)
    if col == "effect":
        return False                # a vanilla card has no text
    return v is None or v is False or v == ""


def cell(levels: dict, r: dict, col: str) -> dict:
    e = dict(levels.get(r["id"], {}).get(col, {}))
    if _blank(r, col):
        e.setdefault("lv", "empty")
    e.setdefault("lv", "draft")
    return e


def stamp() -> float:
    return max(p.stat().st_mtime for p in (CARDS, ART_JS, LEVELS) if p.exists())


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
    """Check every card the edit touched against the engine's rules, then write cards.json."""
    for c in cards["cards"]:
        if c["status"] != PLANNED:
            try:
                validate_card_record(c)
            except CardDataError as e:
                raise Refused(str(e)) from None
    _write(CARDS, cards)


def _apply_value(r: dict, col: str, value) -> None:
    cards = _read(CARDS)
    c = _rec(cards, r["id"])
    if col == "rarity":
        c["rarity"] = RARITY[value] if value else ""
    elif col == "animal":
        c["name"] = str(value).strip()
    elif col == "strength":
        if c["base_strength"] == "dynamic":
            raise Refused(f"{c['id']}'s strength is worked out by the engine ({c.get('dynamic_strength')})")
        c["base_strength"] = None if value in ("", None) else int(value)
    elif col == "cost":
        c["cost"] = value
    elif col == "effect":
        c["text"] = value.strip()
        c.pop("keywords", None)
        c.update(parse_text(c["text"]))
    if c["status"] == PLANNED and c["rarity"] and c["base_strength"] is not None:
        c["status"] = "reserve"                 # designed enough to be a card; collect puts it in the collection
    _save_cards(cards)


def set_value(card_id: str, col: str, value, by: str = "martin", note: str | None = None) -> str:
    r = _row(card_id)
    if col not in VALUE_COLS:
        raise Refused(f"{r['id']} {col} isn't editable here")
    cur = _guard(r, col, by)
    prev = value_of(r, col)
    if col in ("strength", "cost") and value not in ("", None):
        try:
            value = int(value)
        except ValueError:
            raise Refused(f"{r['id']} {col}: {value!r} is not a whole number") from None
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


def add(cid: str, name: str, strength: int, cost: int, dynamic: str = "", legendary: bool = False) -> str:
    """A new collectible card, vanilla until its text is written. Its number for deck codes is appended."""
    cards = _read(CARDS)
    if any(c["id"] == cid for c in cards["cards"]):
        raise Refused(f"{cid} already exists")
    rec = {"id": cid, "name": name, "status": "collectible", "rarity": "legendary" if legendary else "common",
           "base_strength": strength, "keywords": [], "text": "", "cost": cost}
    if dynamic:   # a strength that is a count (engine_rs/src/data.rs DYNAMIC_STRENGTHS): the Shades
        rec["base_strength"], rec["dynamic_strength"] = "dynamic", dynamic
    validate_card_record(rec)
    cards["cards"].append(rec)
    _save_cards(cards)
    src = CARDNUMS.read_text(encoding="utf-8")
    if f'"{cid}"' not in src:
        CARDNUMS.write_text(src.replace("\n];", f'\n  "{cid}",\n];', 1), encoding="utf-8")
    return f"{cid}: {name}, {cost} mana, strength {strength}"


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
    """Take a card out of the collection, into the reserve (kept, not collectible)."""
    return _set_status(card_id, "collectible", "reserve", "out of the collection (in the reserve)", by)


def collect(card_id: str, by: str = "martin") -> str:
    """Put a reserve card into the collection. The reverse of shelve."""
    return _set_status(card_id, "reserve", "collectible", "into the collection", by)


# ---------- ids ----------

RENAMED = ROOT / "animal_kingdom" / "web" / "renamed.py"
CARDNUMS = ROOT / "animal_kingdom" / "web" / "static" / "cardnums.js"
# Records of what happened, kept as written: the human games.
HISTORY = ("results/",)
TEXT = (".py", ".js", ".mjs", ".json", ".jsonl", ".md", ".html", ".css", ".txt", ".toml", ".sh")


def _git_files(repo: Path) -> list[str]:
    return subprocess.run(["git", "-C", str(repo), "ls-files"], capture_output=True, text=True, check=True).stdout.split("\n")


def rename(old: str, new: str) -> str:
    """Give a card a new id everywhere the game knows it: the card data, the levels, the crops,
    the code, tests and docs, its painting; its deck-code number stays, and players'
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
    CARDNUMS.write_text(src.replace("export const SUCCESSOR = {", f"export const SUCCESSOR = {{ {old}: '{new}', ", 1), encoding="utf-8")
    return f"{old} -> {new} ({changed} files)"


def set_dynamic(card_id: str, rule: str, by: str = "martin") -> str:
    """What a card with a variable strength counts (a Shade's "+1 for each ..."). Claude can't change a locked strength."""
    r = _row(card_id)
    _guard(r, "strength", by)
    cards = _read(CARDS)
    c = _rec(cards, r["id"])
    if c["base_strength"] != "dynamic":
        raise Refused(f"{c['id']}'s strength is a number, not a count")
    prev = c.get("dynamic_strength")
    c["dynamic_strength"] = rule
    _save_cards(cards)
    levels = _levels()
    _mark(levels, r, "strength", by, None, None, prev_value=prev, changed_value=True)
    _write(LEVELS, levels)
    return f"{c['id']} counts: {prev} -> {rule}"


def delete(card_id: str, by: str = "martin") -> str:
    """Remove a card from the game: out of cards.json, and its levels gone. Its number in static/cardnums.js stays, since
    deck codes depend on every number. Claude can't delete a card with a locked value."""
    r = _row(card_id)
    if by == "claude" and any(r["lv"][c]["lv"] == "locked" for c in VALUE_COLS):
        raise Refused(f"{r['id']} has a locked value; ask Martin")
    cards = _read(CARDS)
    cards["cards"] = [c for c in cards["cards"] if c["id"] != r["id"]]
    _save_cards(cards)
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
    s = sub.add_parser("shelve"); s.add_argument("id")
    s = sub.add_parser("collect"); s.add_argument("id")
    s = sub.add_parser("add"); s.add_argument("id"); s.add_argument("name"); s.add_argument("strength", type=int); s.add_argument("cost", type=int); s.add_argument("--dynamic", default=""); s.add_argument("--legendary", action="store_true")
    s = sub.add_parser("delete"); s.add_argument("id")
    s = sub.add_parser("dynamic"); s.add_argument("id"); s.add_argument("rule")
    s = sub.add_parser("rename"); s.add_argument("old"); s.add_argument("new")
    s = sub.add_parser("crop"); s.add_argument("id"); s.add_argument("--crop"); s.add_argument("--strip"); s.add_argument("--full")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "show":
            rows = load()["rows"]
            print(json.dumps([r for r in rows if not a.ids or r["id"] in a.ids], ensure_ascii=False, indent=1))
        elif a.cmd == "set":
            print(set_value(a.id, a.col, a.value, "claude", a.note))
        elif a.cmd == "level":
            set_level(a.id, a.col, a.lv, "claude", a.note)
        elif a.cmd == "note":
            set_note(a.id, a.col, a.note, "claude")
        elif a.cmd == "shelve":
            print(shelve(a.id, "claude"))
        elif a.cmd == "collect":
            print(collect(a.id, "claude"))
        elif a.cmd == "add":
            print(add(a.id, a.name, a.strength, a.cost, a.dynamic, a.legendary))
        elif a.cmd == "delete":
            print(delete(a.id, "claude"))
        elif a.cmd == "dynamic":
            print(set_dynamic(a.id, a.rule, "claude"))
        elif a.cmd == "rename":
            print(rename(a.old, a.new))
        elif a.cmd == "crop":
            nums = lambda v: "reset" if v == "reset" else [float(x) for x in v.split(",")] if v else None
            full = None if a.full is None else "reset" if a.full == "reset" else float(a.full)
            set_crop(a.id, nums(a.crop), nums(a.strip), full, "claude")
    except (Refused, KeyError) as e:
        sys.exit(f"refused: {e}")


if __name__ == "__main__":
    main()
