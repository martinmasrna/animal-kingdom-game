"""The league's door into the ladder (docs/league.md): bot games played elsewhere are rated here, and new lists join the pool here.

The web ladder is the only rating store. A runner (league/runner.py) plays bot-versus-bot games by matchmaking on another
machine and posts every result to `/api/league/games`; the server rates both pairings with the same Glicko-2 update a
person's game gets. New lists (Martin's, a tinkered child, a netdeck) arrive at `/api/league/decks` and join the pool at
once, as players: three pairings at 1500 with the wide uncertainty everyone starts with, not offered to people until they
have placed. `/api/league/pool` hands the runner the pool and every bot's rating. The three calls need the league key:
`AK_LEAGUE_KEY` in the environment (on Fly: `fly secrets set`) or in the untracked results/oauth.json, like the sign-in
credentials; without a key the calls answer 403 and the league is simply absent.
"""

from __future__ import annotations

import json
import os
import time
from typing import Optional

from ..decks import PREMADE_DECKS, decklist_problems, register_deck
from .oauth import LOCAL_CREDENTIALS

SCHEMA = """
CREATE TABLE IF NOT EXISTS pool_decks (
    slug TEXT PRIMARY KEY, name TEXT NOT NULL, list TEXT NOT NULL, source TEXT NOT NULL, parent TEXT, born REAL NOT NULL);
CREATE TABLE IF NOT EXISTS league_games (
    id INTEGER PRIMARY KEY, t REAL NOT NULL, a TEXT NOT NULL, b TEXT NOT NULL, winner TEXT, seed INTEGER, turns INTEGER, reason TEXT);
CREATE TABLE IF NOT EXISTS league_report (k TEXT PRIMARY KEY, v TEXT NOT NULL, t REAL NOT NULL);
CREATE TABLE IF NOT EXISTS pool_retired (slug TEXT PRIMARY KEY, t REAL NOT NULL);
"""


def key() -> Optional[str]:
    env = dict(os.environ)
    if LOCAL_CREDENTIALS.is_file():
        env = {**json.loads(LOCAL_CREDENTIALS.read_text()), **env}
    return env.get("AK_LEAGUE_KEY") or None


class Pool:
    """The lists the league added to the bot pool, kept in the profiles database and registered as loadable decks."""

    def __init__(self, db, names: dict[str, str]):
        self.db, self.names = db, names
        db.executescript(SCHEMA)
        self.rows: dict[str, dict] = {}
        for slug, name, lst, source, parent, born in db.execute("SELECT slug, name, list, source, parent, born FROM pool_decks ORDER BY born"):
            self._register(slug, name, json.loads(lst), source, parent, born)

    def _register(self, slug, name, lst, source, parent, born) -> None:
        if slug not in PREMADE_DECKS:
            register_deck(slug, lst)
        self.names.setdefault(slug, name)
        self.rows[slug] = {"slug": slug, "name": name, "list": lst, "source": source, "parent": parent, "born": born}

    def slugs(self) -> list[str]:
        return list(self.rows)

    def add(self, slug: str, name: str, lst: list[str], source: str, parent: Optional[str], known: set[str]) -> list[str]:
        """Add a list to the pool; the problems that stop it, else empty. `known` holds every pool slug outside this table."""
        problems = decklist_problems(lst)
        if not slug or not slug.replace("_", "").isalnum() or slug in known or slug in self.rows:
            problems.append(f"slug {slug!r} is taken or malformed")
        key_ = tuple(sorted(lst))
        if any(tuple(sorted(r["list"])) == key_ for r in self.rows.values()) or \
                any(tuple(sorted(PREMADE_DECKS[s])) == key_ for s in known if s in PREMADE_DECKS):
            problems.append("an identical list is already a player")
        if problems:
            return problems
        born = time.time()
        with self.db:
            self.db.execute("INSERT INTO pool_decks VALUES (?, ?, ?, ?, ?, ?)", (slug, name, json.dumps(lst), source, parent, born))
        self._register(slug, name, list(lst), source, parent, born)
        return []

    def retired(self) -> set[str]:
        """Lists Martin took out of the league (2026-10-25: stale and pointless ones); their games and rows stay, they play no more."""
        return {r[0] for r in self.db.execute("SELECT slug FROM pool_retired")}

    def retire(self, slugs: list[str]) -> None:
        with self.db:
            self.db.executemany("INSERT OR IGNORE INTO pool_retired VALUES (?, ?)", [(s, time.time()) for s in slugs])

    def put_report(self, rep: dict) -> None:
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO league_report VALUES ('latest', ?, ?)", (json.dumps(rep), time.time()))

    def report(self) -> Optional[dict]:
        row = self.db.execute("SELECT v FROM league_report WHERE k = 'latest'").fetchone()
        return json.loads(row[0]) if row else None

    def record(self, games: list[dict]) -> None:
        with self.db:
            self.db.executemany("INSERT INTO league_games (t, a, b, winner, seed, turns, reason) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                [(time.time(), g["a"], g["b"], g.get("winner"), g.get("seed"), g.get("turns"), g.get("reason")) for g in games])
