"""Ranked leagues: the climb a person sees on the one ladder (docs/ranked-leagues.md).

Three rules, all on the screen (Martin, 2026-11-05): a win gains a star, two from your third win in a row; a loss loses
a star, and at 0 stars drops you a league (never out of league 1); you play opponents from your own league. Each league
is a band of bot ratings, so the climb stops where a player's skill is: the league says how good you are, not how much
you played. The top league has no stars: it shows the rating, and the rating picks its opponents.

The rating (web/ladder.py) keeps running for everyone. Below the top league it decides nothing a player sees; it gives
the number a player starts the top league with, and it places a bot in its league.

Players see the word "league". The code says `tier` because `web/league.py` is already the bot population (docs/league.md).

Pure and stdlib-only: the server (web/server.py) and the simulator (tools/ranked/simulate.py) both call `after_game`, so
the numbers in the design doc are the rules that ship.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace

# One row per league, bottom first: (name, stars to move up, par rating). The top league has no stars.
# A league's bots are those rated from its par to the next league's par (league 1 also takes every bot under it, the
# top league every bot from its par up). The names are placeholders until Martin picks a set (docs/ranked-leagues.md).
LEAGUES = (
    ("League 1", 3, 1000),
    ("League 2", 3, 1100),
    ("League 3", 3, 1200),
    ("League 4", 5, 1300),
    ("League 5", 5, 1400),
    ("League 6", 5, 1500),
    ("League 7", 5, 1600),
    ("League 8", 5, 1700),
    ("League 9", 5, 1800),
    ("League 10", 0, 1900),
)
TOP = len(LEAGUES)                 # leagues count from 1; the top league shows the rating
STREAK = 3                         # the third win in a row and every one after it gains two stars
PLACING = 10                       # a profile with fewer rated games than this migrates to league 1 (web/ladder.py PROVISIONAL)


def name(league: int) -> str:
    return LEAGUES[league - 1][0]


def stars_needed(league: int) -> int:
    return LEAGUES[league - 1][1]


def par(league: int) -> float:
    return LEAGUES[league - 1][2]


def league_of(rating: float) -> int:
    """The league a rating stands for: the highest whose par is at or under it (league 1 under the lowest par)."""
    return max((i + 1 for i, (_, _, p) in enumerate(LEAGUES) if rating >= p), default=1)


def band(league: int) -> tuple[float, float]:
    """The bot ratings a league plays: from its par up to the next league's par; open below league 1 and above the top."""
    lo = float("-inf") if league == 1 else par(league)
    hi = float("inf") if league == TOP else par(league + 1)
    return lo, hi


@dataclass(frozen=True)
class Standing:
    league: int = 1
    stars: int = 0
    streak: int = 0       # wins in a row (0 after a loss)
    best: int = 1         # the highest league reached

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict | None) -> "Standing":
        return cls(**{k: int(v) for k, v in (d or {}).items() if k in cls.__dataclass_fields__})


@dataclass(frozen=True)
class Change:
    """What one game did, for the end-of-match line."""
    before: Standing
    after: Standing
    won: bool
    gained: int = 0        # stars gained on a win (1 or 2), or lost on a loss (0 or 1), as a count
    streak_bonus: bool = False
    promoted: bool = False
    demoted: bool = False

    def line(self, rating: str | None = None) -> str:
        """The one line the end of a ranked match says about the stars."""
        a = self.after
        if a.league == TOP and self.before.league == TOP:
            return f"{name(TOP)}: rating {rating}" if rating else name(TOP)
        if self.promoted:
            return f"Up to {name(a.league)}" + ("" if a.league == TOP else f", {_stars(a.stars)}")
        if self.demoted:
            return f"Down to {name(a.league)}, {_stars(a.stars)}"
        here = f"{name(a.league)}, {a.stars} of {stars_needed(a.league)} stars"
        if self.won:
            return f"+{self.gained} star{'s' if self.gained > 1 else ''}{' (win streak)' if self.streak_bonus else ''}: {here}"
        return f"-1 star: {here}" if self.gained else here


def _stars(n: int) -> str:
    return f"{n} star{'' if n == 1 else 's'}"


def after_game(s: Standing, won: bool) -> Change:
    """The standing after one rated game."""
    if won:
        streak = s.streak + 1
        if s.league == TOP:
            return Change(s, replace(s, streak=streak), True)
        gain = 2 if streak >= STREAK else 1
        league, stars, promoted = s.league, s.stars + gain, False
        while league < TOP and stars >= stars_needed(league):
            stars -= stars_needed(league); league += 1; promoted = True
        if league == TOP:
            stars = 0
        a = Standing(league, stars, streak, max(s.best, league))
        return Change(s, a, True, gain, gain > 1, promoted)
    # a loss
    if s.league == TOP:
        return Change(s, replace(s, streak=0), False)
    if s.stars:
        return Change(s, replace(s, stars=s.stars - 1, streak=0), False, 1)
    if s.league == 1:
        return Change(s, replace(s, streak=0), False)
    league = s.league - 1
    return Change(s, replace(s, league=league, stars=stars_needed(league) - 1, streak=0), False, 1, demoted=True)


def from_rating(rating: float, games: int) -> Standing:
    """A standing for a profile that played ranked before leagues existed (docs/ranked-leagues.md, "Migration"): the
    league its rating stands for, at most league 9 (the top is reached by a win), no stars. Opponents come from that
    league, so a profile placed a little wrong finds its level in a few games. A profile still placing (fewer than PLACING
    rated games) starts at the bottom."""
    if games < PLACING:
        return Standing()
    league = min(TOP - 1, league_of(rating))
    return Standing(league, 0, 0, league)


def view(s: Standing, rating_shown: str | None = None) -> dict:
    """The standing as the client shows it: the league's name, stars as a count, the streak; the top league shows the
    rating instead of stars."""
    v = {"league": s.league, "name": name(s.league), "top": s.league == TOP, "streak": s.streak, "best": name(s.best)}
    if s.league == TOP:
        v["rating"] = rating_shown
    else:
        v["stars"], v["of"] = s.stars, stars_needed(s.league)
    return v


def sort_key(s: Standing, rating: float) -> float:
    """Where a person sits on the one leaderboard beside the bots, on the rating's scale: below the top their league's par
    plus their stars' share of the 100 points to the next league (league 8, 2 of 5 stars: 1740); in the top league their
    rating."""
    return rating if s.league == TOP else par(s.league) + 100 * s.stars / stars_needed(s.league)


# --------------------------------------------------------------- the table (in the profiles database, beside `ladder`)
SCHEMA = """
CREATE TABLE IF NOT EXISTS tiers (
    id TEXT PRIMARY KEY, league INTEGER NOT NULL, stars INTEGER NOT NULL,
    streak INTEGER NOT NULL, best INTEGER NOT NULL, games INTEGER NOT NULL);
"""


class Tiers:
    """Each person's standing by ladder id (their profile id). Bots have none. A person with no row stands in league 1."""

    def __init__(self, db):
        self.db = db
        db.executescript(SCHEMA)

    def get(self, pid: str) -> Standing:
        row = self.db.execute("SELECT league, stars, streak, best FROM tiers WHERE id = ?", (pid,)).fetchone()
        return Standing(*row) if row else Standing()

    def games(self, pid: str) -> int:
        row = self.db.execute("SELECT games FROM tiers WHERE id = ?", (pid,)).fetchone()
        return row[0] if row else 0

    def put(self, pid: str, s: Standing, games: int) -> None:
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO tiers VALUES (?, ?, ?, ?, ?, ?)",
                            (pid, s.league, s.stars, s.streak, s.best, games))

    def result(self, pid: str, won: bool) -> Change:
        """One rated game for a person: their standing moved by the result."""
        ch = after_game(self.get(pid), won)
        self.put(pid, ch.after, self.games(pid) + 1)
        return ch

    def all(self) -> dict[str, Standing]:
        return {lid: Standing(*rest) for lid, *rest in self.db.execute("SELECT id, league, stars, streak, best FROM tiers")}

    def migrate(self, ratings: dict) -> int:
        """Once, when leagues arrive: every person already rated gets a standing from their rating (from_rating); a
        `tiers_migrated` mark in ladder_meta keeps it from running again, so a later newcomer starts in league 1.
        `ratings`: ladder id -> ladder.Rating for the people (not the bots). Returns how many were placed."""
        self.db.execute("CREATE TABLE IF NOT EXISTS ladder_meta (k TEXT PRIMARY KEY, v TEXT NOT NULL)")
        if self.db.execute("SELECT 1 FROM ladder_meta WHERE k = 'tiers_migrated'").fetchone():
            return 0
        n = 0
        with self.db:
            for lid, r in ratings.items():
                if lid.startswith("bot:") or r.games <= 0:
                    continue
                if not self.db.execute("SELECT 1 FROM tiers WHERE id = ?", (lid,)).fetchone():
                    s = from_rating(r.rating, r.games)
                    self.db.execute("INSERT INTO tiers VALUES (?, ?, ?, ?, ?, ?)", (lid, s.league, s.stars, 0, s.best, 0))
                    n += 1
            self.db.execute("INSERT OR REPLACE INTO ladder_meta VALUES ('tiers_migrated', '1')")
        return n
