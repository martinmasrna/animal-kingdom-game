"""News: what changed in the game, release by release (web/news/*.md, written as its README says).

The News screen lists every release, newest first; a profile keeps the newest release it has opened (the corner piece's
dot) and the newest one whose "Since you last played" it has seen. That piece shows a returning player, once, the
changes of the releases since they last saw it that are rules or touch a card in one of their decks; a release from
before the profile existed never shows there (a first visit has nothing that changed under it).
"""

from __future__ import annotations

import datetime
import json
import re
from pathlib import Path

from ..engine.cards import load_cards

NEWS_DIR = Path(__file__).resolve().parent / "news"
GROUPS = ("Rules", "Cards", "New", "Fixed")
SCHEMA = """
CREATE TABLE IF NOT EXISTS news_seen (profile TEXT PRIMARY KEY, opened TEXT NOT NULL DEFAULT '', shown TEXT NOT NULL DEFAULT '');
"""


class NewsError(ValueError):
    pass


def parse(path: Path, cards: dict) -> dict:
    """One release file: its date and groups of changes, each with its why, the cards it touches and how they were."""
    by_name = {c.name.lower(): cid for cid, c in cards.items()}
    rid = path.stem
    try:
        day = datetime.date.fromisoformat(rid)
    except ValueError as e:
        raise NewsError(f"{path.name}: the file is named for its day, YYYY-MM-DD.md") from e
    groups, group, item = [], None, None
    for n, line in enumerate(path.read_text().splitlines(), 1):
        where = f"{path.name}:{n}"
        if not line.strip() or line.startswith("# "):
            continue
        if line.startswith("## "):
            name = line[3:].strip()
            if name not in GROUPS:
                raise NewsError(f"{where}: a group is one of {', '.join(GROUPS)}")
            group = {"name": name, "items": []}
            groups.append(group)
        elif line.startswith("- "):
            if group is None:
                raise NewsError(f"{where}: a change under no group")
            item = {"text": line[2:].strip(), "why": "", "cards": [], "was": {}}
            group["items"].append(item)
        elif m := re.match(r"\s+(Why|Cards|Was):\s*(.*)$", line):
            if item is None:
                raise NewsError(f"{where}: {m[1]} under no change")
            if m[1] == "Why":
                item["why"] = m[2].strip()
            elif m[1] == "Cards":
                for name in (x.strip() for x in m[2].split(",") if x.strip()):
                    if name.lower() not in by_name:
                        raise NewsError(f"{where}: no card named {name!r}")
                    item["cards"].append(by_name[name.lower()])
            else:
                item["was"] = json.loads(m[2])
        else:
            raise NewsError(f"{where}: not a line a release has ({line.strip()[:40]!r})")
    order = {g: i for i, g in enumerate(GROUPS)}
    if [order[g["name"]] for g in groups] != sorted(order[g["name"]] for g in groups):
        raise NewsError(f"{path.name}: the groups go {', '.join(GROUPS)}")
    return {"id": rid, "date": f"{day.day} {day:%B %Y}", "groups": groups}


def releases(news_dir: Path = NEWS_DIR) -> list[dict]:
    """Every release, newest first."""
    cards = load_cards()
    return [parse(p, cards) for p in sorted(news_dir.glob("[0-9]*.md"), reverse=True)]


def state(db, profile: dict, decks: list, rels: list) -> dict:
    """What this profile hasn't read (the dot) and what "Since you last played" shows it now (possibly nothing)."""
    db.executescript(SCHEMA)
    row = db.execute("SELECT opened, shown FROM news_seen WHERE profile = ?", (profile["id"],)).fetchone()
    opened, shown = row if row else ("", "")
    newest = rels[0]["id"] if rels else ""
    joined = datetime.date.fromtimestamp(profile.get("created") or 0).isoformat()
    mine = {c for d in decks for c in (d.get("cards") or {})}
    since = []
    for r in rels:
        if r["id"] <= shown or r["id"] < joined:   # seen there already, or from before the day this player came
            continue
        for g in r["groups"]:
            for it in g["items"]:
                if g["name"] == "Rules" or set(it["cards"]) & mine:
                    since.append({"release": r["id"], "group": g["name"], "text": it["text"],
                                  "cards": [c for c in it["cards"] if c in mine] or it["cards"],
                                  "decks": [d["name"] for d in decks if set(d.get("cards") or {}) & set(it["cards"])]})
    return {"unread": newest > opened, "newest": newest, "since": since}


def mark(db, profile_id: str, *, opened: str = "", shown: str = "") -> None:
    """The newest release opened on the News screen, or seen in "Since you last played"."""
    db.executescript(SCHEMA)
    with db:
        db.execute("INSERT OR IGNORE INTO news_seen (profile) VALUES (?)", (profile_id,))
        if opened:
            db.execute("UPDATE news_seen SET opened = MAX(opened, ?) WHERE profile = ?", (opened, profile_id))
        if shown:
            db.execute("UPDATE news_seen SET shown = MAX(shown, ?) WHERE profile = ?", (shown, profile_id))
