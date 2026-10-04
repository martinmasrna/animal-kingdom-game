"""Chat between friends (design sandbox ladder/chat/greybox.html, approved by Martin 2026-10-04): one conversation per pair
of friends, kept, so a message to a friend who is away waits for them. Only friends may write to each other (server.py
checks); a conversation keeps its last KEEP messages. What each player has read is kept as the last message id they saw.

Kept in the profiles database.
"""

from __future__ import annotations

import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS chat (id INTEGER PRIMARY KEY AUTOINCREMENT, frm TEXT NOT NULL, dest TEXT NOT NULL, text TEXT NOT NULL, at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS chat_pair ON chat (frm, dest, id);
CREATE INDEX IF NOT EXISTS chat_dest ON chat (dest, id);
CREATE TABLE IF NOT EXISTS chat_read (profile TEXT NOT NULL, other TEXT NOT NULL, upto INTEGER NOT NULL, PRIMARY KEY (profile, other));
"""
KEEP = 200          # messages kept per conversation
MAX_LEN = 500       # characters in one message
PER_MINUTE = 30     # messages one player may send a minute


class ChatError(ValueError):
    pass


class Chat:
    def __init__(self, db):
        self.db = db
        db.executescript(SCHEMA)
        self._sent: dict[str, list[float]] = {}   # sender -> the times of their messages in the last minute

    def send(self, frm: str, dest: str, text: str, now: float | None = None) -> dict:
        text = " ".join(str(text or "").split())   # one line: the box sends on Enter
        if not text:
            raise ChatError("an empty message")
        if len(text) > MAX_LEN:
            raise ChatError(f"a message is at most {MAX_LEN} characters")
        now = now or time.time()
        recent = [t for t in self._sent.get(frm, []) if now - t < 60]
        if len(recent) >= PER_MINUTE:
            raise ChatError("slow down a little")
        self._sent[frm] = recent + [now]
        with self.db:
            mid = self.db.execute("INSERT INTO chat (frm, dest, text, at) VALUES (?, ?, ?, ?)", (frm, dest, text, now)).lastrowid
            self.db.execute("""DELETE FROM chat WHERE ((frm = ? AND dest = ?) OR (frm = ? AND dest = ?)) AND id NOT IN (
                SELECT id FROM chat WHERE (frm = ? AND dest = ?) OR (frm = ? AND dest = ?) ORDER BY id DESC LIMIT ?)""",
                            (frm, dest, dest, frm) * 2 + (KEEP,))
            self._mark(frm, dest, mid)   # your own message is read
        return {"id": mid, "from": frm, "to": dest, "text": text, "at": now}

    def history(self, a: str, b: str) -> list[dict]:
        """The conversation between a and b, oldest first."""
        rows = self.db.execute("SELECT id, frm, dest, text, at FROM chat WHERE (frm = ? AND dest = ?) OR (frm = ? AND dest = ?) ORDER BY id",
                               (a, b, b, a))
        return [{"id": i, "from": f, "to": d, "text": t, "at": at} for i, f, d, t, at in rows]

    def read(self, pid: str, other: str) -> None:
        """pid has seen everything other sent them."""
        row = self.db.execute("SELECT MAX(id) FROM chat WHERE frm = ? AND dest = ?", (other, pid)).fetchone()
        if row and row[0]:
            with self.db:
                self._mark(pid, other, row[0])

    def _mark(self, pid: str, other: str, upto: int) -> None:
        self.db.execute("INSERT INTO chat_read VALUES (?, ?, ?) ON CONFLICT (profile, other) DO UPDATE SET upto = MAX(upto, excluded.upto)",
                        (pid, other, upto))

    def unread(self, pid: str) -> dict[str, int]:
        """Unread messages to pid, by sender."""
        rows = self.db.execute("""SELECT c.frm, COUNT(*) FROM chat c LEFT JOIN chat_read r ON r.profile = c.dest AND r.other = c.frm
            WHERE c.dest = ? AND c.id > COALESCE(r.upto, 0) GROUP BY c.frm""", (pid,))
        return {f: n for f, n in rows}

    def last(self, pid: str) -> dict[str, dict]:
        """The last message between pid and each person they have talked to."""
        rows = self.db.execute("""SELECT frm, dest, text, at FROM chat WHERE id IN (
            SELECT MAX(id) FROM chat WHERE frm = ? OR dest = ? GROUP BY CASE WHEN frm = ? THEN dest ELSE frm END)""", (pid, pid, pid))
        return {(d if f == pid else f): {"text": t, "at": at, "mine": f == pid} for f, d, t, at in rows}
