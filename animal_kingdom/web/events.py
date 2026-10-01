"""What players do, kept as plain facts for reading play back (web/playtest.py): one row per event, never shown to them.

The server records what it knows for certain (a profile made, each game's start and end, tutorials included, a
concede, a player's connection dropping mid-game); the client records what only it sees (the screens visited, each
tutorial step reached, feedback opened, decks saved), through POST /api/events. Kept in the profiles database (table
`events`); `deploy/deploy.sh players` pulls it with the profiles and histories.
"""

from __future__ import annotations

import json
import re
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (t REAL NOT NULL, profile TEXT NOT NULL, kind TEXT NOT NULL, data TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS events_profile ON events (profile, t);
"""
KIND = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
DATA_MAX = 2000         # characters of one event's data
BATCH_MAX = 50          # events in one client request
PER_HOUR = 2000         # client events one profile may send an hour (a runaway page can't fill the disk)


def record(db, profile: str, kind: str, data: dict | None = None) -> None:
    """One event the server knows for certain."""
    db.executescript(SCHEMA)
    with db:
        db.execute("INSERT INTO events VALUES (?, ?, ?, ?)", (time.time(), profile or "", kind, json.dumps(data or {})))


def record_client(db, profile: str, items) -> int:
    """A client's batch: well-formed events only, within the hourly cap. Returns how many were kept."""
    if not isinstance(items, list):
        return 0
    db.executescript(SCHEMA)
    room = PER_HOUR - db.execute("SELECT COUNT(*) FROM events WHERE profile = ? AND t > ?",
                                 (profile, time.time() - 3600)).fetchone()[0]
    rows = []
    for e in items[:BATCH_MAX]:
        if len(rows) >= room or not isinstance(e, dict) or not KIND.match(str(e.get("kind", ""))):
            continue
        data = json.dumps(e.get("data") if isinstance(e.get("data"), dict) else {})
        if len(data) > DATA_MAX:
            continue
        rows.append((time.time(), profile, "c_" + e["kind"], data))   # c_: the client said so
    with db:
        db.executemany("INSERT INTO events VALUES (?, ?, ?, ?)", rows)
    return len(rows)
