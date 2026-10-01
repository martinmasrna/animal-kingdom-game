"""The ladder: Glicko-2 ratings for people and for the bots that fill it (docs/pre-launch.md, the road to an open alpha).

Every ranked game updates both sides at once (one game is one rating period, as Lichess does). A rating is a number,
its uncertainty (rd) and its volatility. New players start at 1500 with a wide uncertainty, so a few games place them;
the bots start where bot-vs-bot simulation puts them with a narrow one, so they move slowly and keep the scale steady.
Players see only the number, with a "?" after it for their first PROVISIONAL games (Martin, 2026-10-01). Draws don't count.

Glicko-2 as published: Glickman, "Example of the Glicko-2 system" (2013).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

SCALE = 173.7178        # Glicko-2's own scale: rating 1500 is mu 0
TAU = 0.5               # how much the volatility may change (Glickman suggests 0.3 to 1.2)
START = 1500.0
START_RD = 350.0
START_VOL = 0.06
BOT_RD = 60.0           # a seeded bot's uncertainty: it moves, slowly
PROVISIONAL = 10        # games before the "?" goes


@dataclass(frozen=True)
class Rating:
    rating: float = START
    rd: float = START_RD
    vol: float = START_VOL
    games: int = 0

    @property
    def provisional(self) -> bool:
        return self.games < PROVISIONAL

    def shown(self) -> str:
        return f"{round(self.rating)}{'?' if self.provisional else ''}"


def _g(phi: float) -> float:
    return 1 / math.sqrt(1 + 3 * phi * phi / (math.pi * math.pi))


def expected(a: Rating, b: Rating) -> float:
    """A's expected score against B."""
    mu, mu_b, phi_b = (a.rating - START) / SCALE, (b.rating - START) / SCALE, b.rd / SCALE
    return 1 / (1 + math.exp(-_g(phi_b) * (mu - mu_b)))


def _update(a: Rating, games: list[tuple[Rating, float]]) -> Rating:
    """A's new rating after a rating period of games: (opponent, score), score 1 a win, 0 a loss. The ladder's
    periods are single games; several are allowed so the worked example in the paper can be checked."""
    mu, phi, sigma = (a.rating - START) / SCALE, a.rd / SCALE, a.vol
    terms = []
    for b, score in games:
        g = _g(b.rd / SCALE)
        terms.append((g, 1 / (1 + math.exp(-g * (mu - (b.rating - START) / SCALE))), score))
    v = 1 / sum(g * g * e * (1 - e) for g, e, _ in terms)
    gain = sum(g * (s - e) for g, e, s in terms)
    delta = v * gain
    # the new volatility: the root of f by the Illinois algorithm (step 5 of the paper)
    a_ = math.log(sigma * sigma)
    f = lambda x: (math.exp(x) * (delta * delta - phi * phi - v - math.exp(x)) / (2 * (phi * phi + v + math.exp(x)) ** 2)
                   - (x - a_) / (TAU * TAU))
    lo = a_
    if delta * delta > phi * phi + v:
        hi = math.log(delta * delta - phi * phi - v)
    else:
        k = 1
        while f(a_ - k * TAU) < 0:
            k += 1
        hi = a_ - k * TAU
    f_lo, f_hi = f(lo), f(hi)
    while abs(hi - lo) > 1e-6:
        c = lo + (lo - hi) * f_lo / (f_hi - f_lo)
        f_c = f(c)
        if f_c * f_hi <= 0:
            lo, f_lo = hi, f_hi
        else:
            f_lo /= 2
        hi, f_hi = c, f_c
    sigma2 = math.exp(lo / 2)
    phi_star = math.sqrt(phi * phi + sigma2 * sigma2)
    phi2 = 1 / math.sqrt(1 / (phi_star * phi_star) + 1 / v)
    mu2 = mu + phi2 * phi2 * gain
    return Rating(START + SCALE * mu2, SCALE * phi2, sigma2, a.games + len(games))


def play(a: Rating, b: Rating, a_won: bool) -> tuple[Rating, Rating]:
    """Both sides' ratings after a game A won (a_won) or lost. A draw is not rated: don't call this for one."""
    return _update(a, [(b, 1.0 if a_won else 0.0)]), _update(b, [(a, 0.0 if a_won else 1.0)])


def bot_seed(rating: float) -> Rating:
    """A bot's starting rating: where simulation puts it, with a narrow uncertainty."""
    return replace(Rating(), rating=rating, rd=BOT_RD, games=PROVISIONAL)


# --------------------------------------------------------------- the ladder's players
LEVELS = ("easy", "normal", "expert")
LEVEL_START = {"easy": 1200.0, "normal": 1500.0, "expert": 1800.0}   # until simulation seeds them (seed_bots)
SCHEMA = """
CREATE TABLE IF NOT EXISTS ladder (
    id TEXT PRIMARY KEY, rating REAL NOT NULL, rd REAL NOT NULL, vol REAL NOT NULL, games INTEGER NOT NULL);
"""


def bot_id(level: str, deck: str) -> str:
    return f"bot:{level}:{deck}"


def parse_bot(lid: str) -> tuple[str, str] | None:
    """(level, deck) for a bot's ladder id, else None."""
    parts = lid.split(":")
    return (parts[1], parts[2]) if len(parts) == 3 and parts[0] == "bot" else None


class Ladder:
    """Ratings by ladder id: a person's profile id, or a bot's bot_id(level, deck). Kept in the profiles database."""

    def __init__(self, db, decks: list[str]):
        self.db, self.decks = db, decks
        db.executescript(SCHEMA)
        with db:
            for level in LEVELS:
                for deck in decks:
                    r = bot_seed(LEVEL_START[level])
                    db.execute("INSERT OR IGNORE INTO ladder VALUES (?, ?, ?, ?, ?)", (bot_id(level, deck), r.rating, r.rd, r.vol, r.games))

    def get(self, lid: str) -> Rating:
        row = self.db.execute("SELECT rating, rd, vol, games FROM ladder WHERE id = ?", (lid,)).fetchone()
        return Rating(*row) if row else Rating()

    def _put(self, lid: str, r: Rating) -> None:
        self.db.execute("INSERT OR REPLACE INTO ladder VALUES (?, ?, ?, ?, ?)", (lid, r.rating, r.rd, r.vol, r.games))

    def result(self, winner: str, loser: str) -> tuple[Rating, Rating]:
        """Rate one finished game; returns both new ratings."""
        w, l = play(self.get(winner), self.get(loser), True)
        with self.db:
            self._put(winner, w); self._put(loser, l)
        return w, l

    def seed_bots(self, ratings: dict[str, float]) -> None:
        """Set the bots' ratings from simulation (bot ladder id -> rating), with a seeded bot's narrow uncertainty."""
        with self.db:
            for lid, rating in ratings.items():
                self._put(lid, bot_seed(rating))

    def bots(self) -> dict[str, Rating]:
        return {lid: Rating(*rest) for lid, *rest in self.db.execute("SELECT id, rating, rd, vol, games FROM ladder WHERE id LIKE 'bot:%'")}

    def nearest_bot(self, rating: float, rng) -> str:
        """A bot near `rating`: one of those within 100 of the nearest, at random (so a player meets several decks)."""
        bots = sorted(self.bots().items(), key=lambda kv: abs(kv[1].rating - rating))
        near = [lid for lid, r in bots if abs(r.rating - rating) <= abs(bots[0][1].rating - rating) + 100]
        return rng.choice(near)

    def table(self) -> list[tuple[str, Rating]]:
        """Everyone who has a rating, people with at least one game, best first."""
        rows = self.db.execute("SELECT id, rating, rd, vol, games FROM ladder ORDER BY rating DESC").fetchall()
        return [(lid, Rating(*rest)) for lid, *rest in rows if lid.startswith("bot:") or rest[3] > 0]
