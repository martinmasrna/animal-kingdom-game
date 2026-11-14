"""Ranked leagues: the climb a person sees on the one ladder (docs/ranked-leagues.md).

Ten leagues named by material, Wood to Diamond, and a top league above them. A league has three stages, a stage takes
five wins, and the stages count down as divisions 3, 2, 1: a win gains one, two from your third win in a row; a loss loses one, and with none left drops you a stage,
and from a league's first stage a league (never out of the bottom). You play opponents from your own league. Each league
is a band of bot ratings, so the climb stops where a player's skill is: the league says how good you are, not how much
you played. The top league has no stages: it shows the rating, and the rating picks its opponents.

The rating (web/ladder.py) keeps running for everyone. Below the top league it decides nothing a player sees; it gives
the number a player starts the top league with, and it places a bot in its league.

Players see the word "league". The code says `tier` because `web/league.py` is already the bot population (docs/league.md).
A standing keeps a league and the wins inside it (0 to 14, the code's `stars`); the stage and the wins in it are read off
that count (`stage_of`).

Pure and stdlib-only: the server (web/server.py) and the simulator (tools/ranked/simulate.py) both call `after_game`, so
the numbers in the design doc are the rules that ship.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace

STAGES = 3                         # stages inside a league
WINS = 5                           # wins a stage takes

# One row per league, bottom first: (name, par rating, placeholder colour). The last row is the top league: no stages.
# A league's bots are those rated from its par to the next league's par (league 1 also takes every bot under it, the
# top league every bot from its par up). The look is a placeholder (docs/ranked-leagues.md): a disc in the colour.
LEAGUES = (
    ("Wood", 1000, "#8a5a33"),
    ("Bone", 1100, "#e4d8bd"),
    ("Stone", 1200, "#8c8f93"),
    ("Copper", 1300, "#c56f3c"),
    ("Silver", 1400, "#c9d0d8"),
    ("Gold", 1500, "#e2b23a"),
    ("Jade", 1600, "#4fa878"),
    ("Sapphire", 1700, "#3566d6"),
    ("Ruby", 1800, "#c8324a"),
    ("Diamond", 1900, "#a8e3f5"),
    ("Legend", 2000, "#f4f1e8"),
)
TOP = len(LEAGUES)                 # leagues count from 1; the top league shows the rating
STREAK = 3                         # the third win in a row and every one after it gains two
PLACING = 10                       # a profile with fewer rated games than this migrates to league 1 (web/ladder.py PROVISIONAL)


def name(league: int) -> str:
    return LEAGUES[league - 1][0]


def colour(league: int) -> str:
    return LEAGUES[league - 1][2]


def stars_needed(league: int) -> int:
    """Wins to climb a whole league (none in the top league)."""
    return 0 if league == TOP else STAGES * WINS


def stage_of(stars: int) -> tuple[int, int]:
    """A league's win count as (stage 1 to 3, wins in that stage 0 to 4)."""
    return stars // WINS + 1, stars % WINS


def division(stars: int) -> int:
    """The number a stage shows: III is where a league starts and I is its last stage (Martin, 2026-11-13: "divison 3
    should be worst one and division 1 best one"), as in League of Legends."""
    return STAGES + 1 - stage_of(stars)[0]


def label(s: "Standing") -> str:
    """What a standing is called: "Gold 2"; the top league by its name alone."""
    return name(s.league) if s.league == TOP else f"{name(s.league)} {division(s.stars)}"


def par(league: int) -> float:
    return LEAGUES[league - 1][1]


def league_of(rating: float) -> int:
    """The league a rating stands for: the highest whose par is at or under it (league 1 under the lowest par)."""
    return max((i + 1 for i, (_, p, _) in enumerate(LEAGUES) if rating >= p), default=1)


def band(league: int) -> tuple[float, float]:
    """The bot ratings a league plays: from its par up to the next league's par; open below league 1 and above the top."""
    lo = float("-inf") if league == 1 else par(league)
    hi = float("inf") if league == TOP else par(league + 1)
    return lo, hi


@dataclass(frozen=True)
class Standing:
    league: int = 1
    stars: int = 0        # wins inside the league, 0 to STAGES * WINS - 1 (stage_of)
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
        """The words the end of a ranked match adds to the emblem and the pips, which the client draws: a move between
        divisions or leagues, or the streak bonus; otherwise nothing, since the emblem already says where you stand."""
        a, b = self.after, self.before
        if a.league == TOP and b.league == TOP:
            return f"{name(TOP)}: rating {rating}" if rating else name(TOP)
        if (a.league, stage_of(a.stars)[0]) > (b.league, stage_of(b.stars)[0]):
            return f"Up to {label(a)}"
        if (a.league, stage_of(a.stars)[0]) < (b.league, stage_of(b.stars)[0]):
            return f"Down to {label(a)}"
        return "Win streak: +2" if self.streak_bonus else ""


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
    league its rating stands for, at most the league under the top (the top is reached by a win), at its first stage. Opponents come from that
    league, so a profile placed a little wrong finds its level in a few games. A profile still placing (fewer than PLACING
    rated games) starts at the bottom."""
    if games < PLACING:
        return Standing()
    league = min(TOP - 1, league_of(rating))
    return Standing(league, 0, 0, league)


def view(s: Standing, rating_shown: str | None = None) -> dict:
    """The standing as the client shows it: the league's name and colour, the division (3 down to 1), its emblem, the wins in the
    stage (`stars` of `of`), the streak; the top league shows the rating instead."""
    v = {"league": s.league, "name": name(s.league), "label": label(s), "colour": colour(s.league),
         "top": s.league == TOP, "streak": s.streak, "best": name(s.best)}
    if s.league == TOP:
        v["rating"] = rating_shown
    else:
        v["division"], v["stars"], v["of"] = division(s.stars), stage_of(s.stars)[1], WINS
        v["emblem"] = f"{name(s.league).lower()}_{division(s.stars)}"   # static/kit2/league/<emblem>.webp
    return v


def sort_key(s: Standing, rating: float) -> float:
    """Where a person sits on the one leaderboard beside the bots, on the rating's scale: below the top their league's par
    plus their wins' share of the 100 points to the next league (league 8, 6 of 15 wins: 1740); in the top league their
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
            self._to_stages()
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
            self.db.execute("INSERT OR REPLACE INTO ladder_meta VALUES ('tiers_stages', '1')")
        return n

    def _to_stages(self) -> None:
        """Once, for standings kept under the first build (ten numbered leagues of 3 or 5 stars, the tenth the top):
        the same league number, the stars as the same share of the fifteen wins, and the old top league to the new
        one. A `tiers_stages` mark in ladder_meta keeps it from running again."""
        if self.db.execute("SELECT 1 FROM ladder_meta WHERE k = 'tiers_stages'").fetchone():
            return
        old_top, old_needed = 10, lambda lg: 3 if lg <= 3 else 5
        with self.db:
            for lid, lg, stars, best in self.db.execute("SELECT id, league, stars, best FROM tiers").fetchall():
                new_lg = TOP if lg >= old_top else lg
                new_stars = 0 if lg >= old_top else min(STAGES * WINS - 1, stars * STAGES * WINS // old_needed(lg))
                self.db.execute("UPDATE tiers SET league = ?, stars = ?, best = ? WHERE id = ?",
                                (new_lg, new_stars, TOP if best >= old_top else best, lid))
            self.db.execute("INSERT OR REPLACE INTO ladder_meta VALUES ('tiers_stages', '1')")
