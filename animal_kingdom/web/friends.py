"""Friends (docs/pre-launch.md, the road to an open alpha): a friend link, opened and confirmed once, makes two players
friends both ways; either can remove the other. Each player has one friend code for their link. When a player was last
online is kept for the friends list ("2 days ago"); who is online now is the server's presence (server.py), not stored.

Kept in the profiles database.
"""

from __future__ import annotations

import secrets
import time
from typing import Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS friends (a TEXT NOT NULL, b TEXT NOT NULL, created REAL NOT NULL, PRIMARY KEY (a, b));
CREATE TABLE IF NOT EXISTS friend_codes (profile TEXT PRIMARY KEY, code TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS last_seen (profile TEXT PRIMARY KEY, at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS friend_requests (frm TEXT NOT NULL, dest TEXT NOT NULL, created REAL NOT NULL, PRIMARY KEY (frm, dest));
"""
ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


class FriendError(ValueError):
    pass


class Friends:
    def __init__(self, db):
        self.db = db
        db.executescript(SCHEMA)

    def code_for(self, pid: str) -> str:
        """The player's friend code (made on first ask, then kept)."""
        row = self.db.execute("SELECT code FROM friend_codes WHERE profile = ?", (pid,)).fetchone()
        if row:
            return row[0]
        code = "".join(secrets.choice(ALPHABET) for _ in range(10))
        with self.db:
            self.db.execute("INSERT INTO friend_codes VALUES (?, ?)", (pid, code))
        return code

    def owner(self, code: str) -> Optional[str]:
        row = self.db.execute("SELECT profile FROM friend_codes WHERE code = ?", (str(code or "").strip().lower(),)).fetchone()
        return row[0] if row else None

    def add(self, pid: str, code: str) -> str:
        """Befriend the owner of `code`; returns their profile id."""
        other = self.owner(code)
        if other is None:
            raise FriendError("that friend link no longer works")
        if other == pid:
            raise FriendError("that's your own friend link")
        now = time.time()
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO friends VALUES (?, ?, ?)", (pid, other, now))
            self.db.execute("INSERT OR IGNORE INTO friends VALUES (?, ?, ?)", (other, pid, now))
        return other

    def befriend(self, a: str, b: str) -> None:
        now = time.time()
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO friends VALUES (?, ?, ?)", (a, b, now))
            self.db.execute("INSERT OR IGNORE INTO friends VALUES (?, ?, ?)", (b, a, now))
            self.db.execute("DELETE FROM friend_requests WHERE (frm = ? AND dest = ?) OR (frm = ? AND dest = ?)", (a, b, b, a))

    def request(self, pid: str, other: str) -> bool:
        """Ask `other` to be friends (from the leaderboard); True when that made you friends (they had asked you)."""
        if other == pid:
            raise FriendError("that's you")
        if self.are(pid, other):
            return True
        if self.db.execute("SELECT 1 FROM friend_requests WHERE frm = ? AND dest = ?", (other, pid)).fetchone():
            self.befriend(pid, other)
            return True
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO friend_requests VALUES (?, ?, ?)", (pid, other, time.time()))
        return False

    def requests_to(self, pid: str) -> list[str]:
        return [r[0] for r in self.db.execute("SELECT frm FROM friend_requests WHERE dest = ? ORDER BY created", (pid,))]

    def asked(self, pid: str) -> set[str]:
        return {r[0] for r in self.db.execute("SELECT dest FROM friend_requests WHERE frm = ?", (pid,))}

    def answer(self, pid: str, frm: str, accept: bool) -> None:
        if accept and self.db.execute("SELECT 1 FROM friend_requests WHERE frm = ? AND dest = ?", (frm, pid)).fetchone():
            self.befriend(pid, frm)
        else:
            with self.db:
                self.db.execute("DELETE FROM friend_requests WHERE frm = ? AND dest = ?", (frm, pid))

    def remove(self, pid: str, other: str) -> None:
        with self.db:
            self.db.execute("DELETE FROM friends WHERE (a = ? AND b = ?) OR (a = ? AND b = ?)", (pid, other, other, pid))

    def of(self, pid: str) -> list[str]:
        return [r[0] for r in self.db.execute("SELECT b FROM friends WHERE a = ? ORDER BY created", (pid,))]

    def are(self, a: str, b: str) -> bool:
        return self.db.execute("SELECT 1 FROM friends WHERE a = ? AND b = ?", (a, b)).fetchone() is not None

    def seen(self, pid: str, at: Optional[float] = None) -> None:
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO last_seen VALUES (?, ?)", (pid, at or time.time()))

    def last_seen(self, pid: str) -> Optional[float]:
        row = self.db.execute("SELECT at FROM last_seen WHERE profile = ?", (pid,)).fetchone()
        return row[0] if row else None
