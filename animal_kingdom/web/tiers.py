"""Ranked leagues: the climb a person sees on top of the one ladder (docs/ranked-leagues.md).

The rating (web/ladder.py) keeps running for everyone, bots included, and still picks every ranked opponent. A league and
its stars are only the person's view of their progress: a win gains a star, a loss loses one, a run of wins and a rating
above the league gain an extra star, a few stars move you up, checkpoint leagues are floors you never fall below, and the
top league shows the rating itself instead of stars.

Players see the word "league". The code says `tier` because `web/league.py` is already the bot population (docs/league.md).

Pure and stdlib-only: the server (web/server.py), the profiles table (web/profiles.py) and the simulator
(tools/ranked/simulate.py) all call `after_game`, so the numbers in the design doc are the rules that ship.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace

# One row per league, bottom first: (name, stars to move up, par rating). The top league has no stars.
# Par is the rating a league stands for: a person whose rating is at or above the next league's par gets the rating bonus.
# The names are placeholders until Martin picks a set (docs/ranked-leagues.md, "Names").
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
FLOORS = (1, 4, 7, 10)             # checkpoints: once reached, never fallen below
NO_LOSS_UNTIL = 3                  # a loss costs no star in leagues 1 to 3
STREAK = 3                         # the third win in a row and every one after it gains an extra star...
STREAK_UNTIL = 7                   # ...in leagues 1 to 7
PLACING = 10                       # a profile with fewer rated games than this migrates to league 1 (web/ladder.py PROVISIONAL)
MAX_GAIN = 2                       # one star a win, two at most: the streak and the rating bonus don't add up
STREAK_NEEDS_PAR = True            # the streak bonus only while the rating is at least the league's par
OVERRANKED = 100                   # a loss costs two stars while the rating sits more than this under the league's par


def name(league: int) -> str:
    return LEAGUES[league - 1][0]


def stars_needed(league: int) -> int:
    return LEAGUES[league - 1][1]


def par(league: int) -> float:
    return LEAGUES[league - 1][2]


def floor_of(league: int) -> int:
    """The checkpoint a league sits on or above."""
    return max(f for f in FLOORS if f <= league)


@dataclass(frozen=True)
class Standing:
    league: int = 1
    stars: int = 0
    floor: int = 1        # the highest checkpoint reached: the league never falls below it
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
    gained: int = 0        # stars gained on a win (1 or 2), or lost on a loss (0 to 2), as a count
    streak_bonus: bool = False
    rating_bonus: bool = False
    promoted: bool = False
    demoted: bool = False
    saved: str = ""        # why a loss cost nothing: "low league", "floor", "top", ""

    def line(self, rating: str | None = None) -> str:
        """The one line the end of a ranked match says about the stars."""
        a = self.after
        if a.league == TOP and self.before.league == TOP:
            return f"{name(TOP)}: rating {rating}" if rating else name(TOP)
        if self.promoted:
            return f"Up to {name(a.league)}" + ("" if a.league == TOP else f", {_stars(a.stars)}")
        if self.demoted:
            return f"Down to {name(a.league)}, {_stars(a.stars)}"
        if self.won:
            why = " (win streak)" if self.streak_bonus else " (rating bonus)" if self.rating_bonus else ""
            return f"+{self.gained} star{'s' if self.gained > 1 else ''}{why}: {name(a.league)}, {_stars(a.stars)} of {stars_needed(a.league)}"
        if self.gained:
            return f"-{self.gained} star{'s' if self.gained > 1 else ''}: {name(a.league)}, {_stars(a.stars)} of {stars_needed(a.league)}"
        why = {"low league": f"no stars lost in leagues 1 to {NO_LOSS_UNTIL}", "floor": f"{name(a.league)} is a checkpoint"}.get(self.saved, "")
        return f"No star lost ({why}): {name(a.league)}, {_stars(a.stars)} of {stars_needed(a.league)}" if why else \
            f"{name(a.league)}, {_stars(a.stars)} of {stars_needed(a.league)}"


def _stars(n: int) -> str:
    return f"{n} star{'' if n == 1 else 's'}"


def after_game(s: Standing, won: bool, rating: float) -> Change:
    """The standing after one rated game. `rating` is the person's ladder rating going into the game (the number the
    rating bonus reads; the ladder itself is updated separately, web/ladder.py)."""
    if won:
        streak = s.streak + 1
        if s.league == TOP:
            a = replace(s, streak=streak)
            return Change(s, a, True)
        streak_bonus = streak >= STREAK and s.league <= STREAK_UNTIL and (not STREAK_NEEDS_PAR or rating >= par(s.league))
        rating_bonus = rating >= par(s.league + 1)
        gain = min(MAX_GAIN, 1 + (streak_bonus or rating_bonus))
        league, stars = s.league, s.stars + gain
        promoted = False
        while league < TOP and stars >= stars_needed(league):
            stars -= stars_needed(league); league += 1; promoted = True
        if league == TOP:
            stars = 0
        floor = max(s.floor, floor_of(league))
        a = Standing(league, stars, floor, streak, max(s.best, league))
        return Change(s, a, True, gain, streak_bonus and gain > 1, rating_bonus and not streak_bonus and gain > 1, promoted)
    # a loss
    if s.league == TOP:
        return Change(s, replace(s, streak=0), False, saved="top")
    if s.league <= NO_LOSS_UNTIL:
        return Change(s, replace(s, streak=0), False, saved="low league")
    loss = 2 if OVERRANKED is not None and rating < par(s.league) - OVERRANKED else 1
    if s.stars >= loss:
        return Change(s, replace(s, stars=s.stars - loss, streak=0), False, loss)
    if s.league <= s.floor:
        return Change(s, replace(s, stars=0, streak=0), False, s.stars, saved="floor" if not s.stars else "")
    league = s.league - 1
    a = replace(s, league=league, stars=stars_needed(league) - (loss - s.stars), streak=0)
    return Change(s, a, False, loss, demoted=True)


def from_rating(rating: float, games: int) -> Standing:
    """A standing for a profile that played ranked before leagues existed (docs/ranked-leagues.md, "Migration").
    Two leagues under the league its rating stands for, at that league's checkpoint, no stars: the rating bonus carries a
    player whose rating is ahead of their league back up in a few wins, so the climb is felt, not skipped. A profile still
    placing (fewer than PLACING rated games) starts at the bottom."""
    if games < PLACING:
        return Standing()
    at = max((i + 1 for i, (_, _, p) in enumerate(LEAGUES) if rating >= p), default=1)
    league = max(1, min(TOP - 1, at - 2))
    return Standing(league, 0, floor_of(league), 0, league)


def view(s: Standing, rating_shown: str | None = None) -> dict:
    """The standing as the client shows it: the league's name, stars as a count, the checkpoint, the streak; the top
    league shows the rating instead of stars."""
    v = {"league": s.league, "name": name(s.league), "top": s.league == TOP, "floor": name(s.floor),
         "streak": s.streak, "best": name(s.best)}
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
    id TEXT PRIMARY KEY, league INTEGER NOT NULL, stars INTEGER NOT NULL, floor INTEGER NOT NULL,
    streak INTEGER NOT NULL, best INTEGER NOT NULL, games INTEGER NOT NULL);
"""


class Tiers:
    """Each person's standing by ladder id (their profile id). Bots have none. A person with no row stands in league 1."""

    def __init__(self, db):
        self.db = db
        db.executescript(SCHEMA)

    def get(self, pid: str) -> Standing:
        row = self.db.execute("SELECT league, stars, floor, streak, best FROM tiers WHERE id = ?", (pid,)).fetchone()
        return Standing(*row) if row else Standing()

    def games(self, pid: str) -> int:
        row = self.db.execute("SELECT games FROM tiers WHERE id = ?", (pid,)).fetchone()
        return row[0] if row else 0

    def put(self, pid: str, s: Standing, games: int) -> None:
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO tiers VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (pid, s.league, s.stars, s.floor, s.streak, s.best, games))

    def result(self, pid: str, won: bool, rating: float) -> Change:
        """One rated game for a person: their standing moved by the result, `rating` their rating going in."""
        ch = after_game(self.get(pid), won, rating)
        self.put(pid, ch.after, self.games(pid) + 1)
        return ch

    def all(self) -> dict[str, Standing]:
        return {lid: Standing(*rest) for lid, *rest in self.db.execute("SELECT id, league, stars, floor, streak, best FROM tiers")}

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
                    self.db.execute("INSERT INTO tiers VALUES (?, ?, ?, ?, ?, ?, ?)", (lid, s.league, s.stars, s.floor, 0, s.best, 0))
                    n += 1
            self.db.execute("INSERT OR REPLACE INTO ladder_meta VALUES ('tiers_migrated', '1')")
        return n
