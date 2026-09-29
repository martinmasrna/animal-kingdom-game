"""Player profiles: a name with a #tag, the decks you built, and your finished matches.

There are no passwords. A first visit creates a guest profile and hands the browser its sign-in
code, which the browser then sends with every request (header `X-AK-Key`). Typing the same code on
another device signs that device in to the same profile. Only a hash of the code is stored.

One SQLite file (`results/web.db`, or `$AK_DB`); in memory when `AK_NO_GAME_LOGS` is set, so test
servers never touch real profiles.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Optional

DB_FILE = Path(__file__).resolve().parents[2] / "results" / "web.db"
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"     # no 0/O, 1/I: codes get typed by hand
NAME_MAX = 20
DECKS_MAX = 100
HISTORY_SHOWN = 100

SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, tag TEXT NOT NULL, key_hash TEXT NOT NULL UNIQUE,
    created REAL NOT NULL, UNIQUE (name COLLATE NOCASE, tag));
CREATE TABLE IF NOT EXISTS decks (
    profile TEXT NOT NULL, id TEXT NOT NULL, name TEXT NOT NULL, cards TEXT NOT NULL, pos INTEGER NOT NULL,
    PRIMARY KEY (profile, id));
CREATE TABLE IF NOT EXISTS history (
    profile TEXT NOT NULL, match TEXT NOT NULL, ended REAL NOT NULL, kind TEXT NOT NULL,
    my_deck TEXT NOT NULL, opp TEXT NOT NULL, opp_deck TEXT NOT NULL, won INTEGER NOT NULL, lost INTEGER NOT NULL,
    PRIMARY KEY (profile, match));
"""


class ProfileError(ValueError):
    pass


def _hash(code: str) -> str:
    return hashlib.sha256(normalize_code(code).encode()).hexdigest()


def normalize_code(code: str) -> str:
    return "".join(ch for ch in str(code).upper() if ch in CODE_ALPHABET)


def _new_code() -> str:
    raw = "".join(secrets.choice(CODE_ALPHABET) for _ in range(16))
    return "-".join(raw[i:i + 4] for i in range(0, 16, 4))


def clean_name(name) -> str:
    name = " ".join(str(name or "").split())[:NAME_MAX]
    if not name:
        raise ProfileError("a name can't be empty")
    return name


class Profiles:
    def __init__(self, path: Optional[str] = None):
        if path is None:
            path = os.environ.get("AK_DB") or (":memory:" if os.environ.get("AK_NO_GAME_LOGS") else str(DB_FILE))
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    # ------------------------------------------------------------- identity
    def _free_tag(self, name: str) -> str:
        taken = {r["tag"] for r in self.db.execute(
            "SELECT tag FROM profiles WHERE name = ? COLLATE NOCASE", (name,))}
        if len(taken) >= 9000:
            raise ProfileError("that name is full, pick another")
        while True:
            tag = str(secrets.randbelow(9000) + 1000)
            if tag not in taken:
                return tag

    def create(self, name: str = "Player") -> tuple[str, dict]:
        """A new guest profile. Returns (sign-in code, profile)."""
        name = clean_name(name)
        code, pid = _new_code(), secrets.token_hex(8)
        with self.db:
            self.db.execute("INSERT INTO profiles VALUES (?, ?, ?, ?, ?)",
                            (pid, name, self._free_tag(name), _hash(code), time.time()))
        return code, self.get(pid)

    def by_code(self, code: str) -> Optional[dict]:
        row = self.db.execute("SELECT id FROM profiles WHERE key_hash = ?", (_hash(code),)).fetchone()
        return self.get(row["id"]) if row else None

    def get(self, pid: str) -> Optional[dict]:
        row = self.db.execute("SELECT id, name, tag FROM profiles WHERE id = ?", (pid,)).fetchone()
        return dict(row) if row else None

    def rename(self, pid: str, name: str) -> dict:
        """A new name keeps the tag unless someone already has that name#tag."""
        name, me = clean_name(name), self.get(pid)
        clash = self.db.execute("SELECT 1 FROM profiles WHERE name = ? COLLATE NOCASE AND tag = ? AND id != ?",
                                (name, me["tag"], pid)).fetchone()
        tag = self._free_tag(name) if clash else me["tag"]
        with self.db:
            self.db.execute("UPDATE profiles SET name = ?, tag = ? WHERE id = ?", (name, tag, pid))
        return self.get(pid)

    # ------------------------------------------------------------- decks
    def decks(self, pid: str) -> list[dict]:
        return [{"id": r["id"], "name": r["name"], "cards": json.loads(r["cards"])} for r in self.db.execute(
            "SELECT id, name, cards FROM decks WHERE profile = ? ORDER BY pos", (pid,))]

    def save_decks(self, pid: str, decks: list) -> list[dict]:
        """Replace the profile's decks with `decks` ([{id, name, cards: {card id: copies}}]). Drafts
        are allowed, so this checks shape only; the deck rules are checked when a deck is played."""
        if not isinstance(decks, list) or len(decks) > DECKS_MAX:
            raise ProfileError("bad deck list")
        rows = []
        for pos, d in enumerate(decks):
            cards = d.get("cards") if isinstance(d, dict) else None
            if not isinstance(cards, dict) or not all(isinstance(n, int) and 0 < n <= 3 for n in cards.values()) \
                    or sum(cards.values()) > 30:
                raise ProfileError("bad deck")
            rows.append((pid, str(d.get("id") or pos)[:40], (str(d.get("name") or "").strip() or "New deck")[:40],
                         json.dumps({str(k): n for k, n in cards.items()}), pos))
        with self.db:
            self.db.execute("DELETE FROM decks WHERE profile = ?", (pid,))
            self.db.executemany("INSERT OR REPLACE INTO decks VALUES (?, ?, ?, ?, ?)", rows)
        return self.decks(pid)

    # ------------------------------------------------------------- history
    def record(self, pid: str, match: str, *, kind: str, my_deck: str, opp: str, opp_deck: str,
               won: int, lost: int) -> None:
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO history VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (pid, match, time.time(), kind, my_deck, opp, opp_deck, won, lost))

    def history(self, pid: str) -> list[dict]:
        return [dict(r) for r in self.db.execute(
            "SELECT match, ended, kind, my_deck, opp, opp_deck, won, lost FROM history WHERE profile = ? "
            "ORDER BY ended DESC LIMIT ?", (pid, HISTORY_SHOWN))]
