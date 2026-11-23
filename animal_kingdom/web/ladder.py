"""The ladder: Glicko-2 ratings for people and for the bots that fill it.

Every ranked game updates both sides at once (one game is one rating period, as Lichess does). A rating is a number,
its uncertainty (rd) and its volatility. New players start at 1500 with a wide uncertainty, so a few games place them;
the bots start where bot-vs-bot games put them (tools/ladder/seed.py, web/pool.py) with a narrow one, so they move slowly
and keep the scale steady. A rating is shown as the number alone, with a "?" after it for the first PROVISIONAL games
(Martin, 2026-10-01); a person sees their own only in the top league, their league below it (web/tiers.py). Draws
don't count.

Glicko-2 as published: Glickman, "Example of the Glicko-2 system" (2013).
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, replace

SCALE = 173.7178        # Glicko-2's own scale: rating 1500 is mu 0
TAU = 0.5               # how much the volatility may change (Glickman suggests 0.3 to 1.2)
START = 1500.0
START_RD = 350.0
START_VOL = 0.06
BOT_RD = 60.0           # a seeded bot's uncertainty: it moves, slowly
UNMEASURED_RD = 110.0   # a bot on its level's rating, its deck not measured with today's cards (web/pool.py): it counts for less and moves faster
PROVISIONAL = 10        # games before the "?" goes
MATCH_WINDOW = 75.0     # how far from a rating a bot opponent is drawn (nearest_bot)
RECENT_DECKS = 4        # the decks of a person's last bot games are not offered again (variety)
# A bot is named by the band its own rating sits in, never by its level ("Control (Expert Bot)"; Martin, 2026-10-20), and
# the leaderboard lists the bots one row per level and deck. A person is never given a band word.
RUNGS = (("Beginner", 0), ("Intermediate", 1300), ("Advanced", 1500), ("Expert", 1700), ("Legendary", 1900))   # name, floor


def rung_of(rating: float) -> str:
    """The rung a rating sits on: the highest floor at or under it."""
    return next(name for name, floor in reversed(RUNGS) if rating >= floor)
PLAYER_RD_FLOOR = 75.0  # a person's uncertainty never settles below this: an even game stays worth about +-15 (Martin,
                        # 2026-10-01: a rating that keeps up with a player still learning beats a precise one; bots keep BOT_RD)


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


def bot_seed(rating: float, rd: float = BOT_RD) -> Rating:
    """A bot's starting rating: where its games against the other bots put it, with a narrow uncertainty."""
    return replace(Rating(), rating=rating, rd=rd, games=PROVISIONAL)


def fit(results: list[tuple[str, str]], iters: int = 2000) -> dict[str, float]:
    """Ratings (Elo scale, mean 1500) from (winner, loser) pairs, by the minorise-maximise iteration for Bradley-Terry:
    how the bots are seeded from their games against each other (tools/ladder/seed.py). A bot that won or lost
    everything has no finite rating: one half win against every opponent is added as a prior."""
    ids = sorted({x for pair in results for x in pair})
    wins = {i: 0.0 for i in ids}
    n = {}
    for w, l in results:
        wins[w] += 1
        n[(w, l)] = n.get((w, l), 0) + 1; n[(l, w)] = n.get((l, w), 0) + 1
    for a, b in itertools.permutations(ids, 2):   # the prior: a half win each way between every pair
        wins[a] += 0.5 / (len(ids) - 1); n[(a, b)] = n.get((a, b), 0) + 1 / (len(ids) - 1)
    p = {i: 1.0 for i in ids}
    for _ in range(iters):
        p = {i: wins[i] / sum(n.get((i, j), 0) / (p[i] + p[j]) for j in ids if j != i) for i in ids}
        g = math.exp(sum(math.log(v) for v in p.values()) / len(p)); p = {i: v / g for i, v in p.items()}
    return {i: 1500 + 400 * math.log10(v) for i, v in p.items()}


# --------------------------------------------------------------- the ladder's players
# The bots' levels, weakest first: one bot at five strengths (their specs and what each is: web/match.py BOT_LEVELS). Each
# level with each deck of the pool is a player of its own on the ladder (Martin, 2026-10-24).
LEVELS = ("1", "2", "3", "4", "5")
LEVEL_START = {"1": 1270.0, "2": 1375.0, "3": 1505.0, "4": 1615.0, "5": 1730.0}   # where a level sits with no seed at all (measured 2026-11-23)
SCHEMA = """
CREATE TABLE IF NOT EXISTS ladder (
    id TEXT PRIMARY KEY, rating REAL NOT NULL, rd REAL NOT NULL, vol REAL NOT NULL, games INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS ladder_source (id TEXT PRIMARY KEY, source TEXT NOT NULL);
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
            for deck in decks:
                for level in LEVELS:
                    r = bot_seed(LEVEL_START[level])
                    db.execute("INSERT OR IGNORE INTO ladder VALUES (?, ?, ?, ?, ?)", (bot_id(level, deck), r.rating, r.rd, r.vol, r.games))

    def set_bots(self, rows: dict[str, tuple[float, float, str]]) -> list[str]:
        """Give the bots their measured ratings: bot ladder id -> (rating, uncertainty, source), the source naming the
        measurement the number comes from (web/pool.py: the seed and what the bot plays with). A bot is set when its
        source is not the one its row was last set from: a new seed, a deck whose cards changed since, a new pairing.
        Until then it keeps the rating its games have moved it to. People's ratings are never touched. Returns the ids set."""
        was = dict(self.db.execute("SELECT id, source FROM ladder_source"))
        new = [lid for lid, (_, _, source) in rows.items() if was.get(lid) != source]
        with self.db:
            for lid in new:
                rating, rd, source = rows[lid]
                self._put(lid, bot_seed(rating, rd))
                self.db.execute("INSERT OR REPLACE INTO ladder_source VALUES (?, ?)", (lid, source))
        return new

    def get(self, lid: str) -> Rating:
        row = self.db.execute("SELECT rating, rd, vol, games FROM ladder WHERE id = ?", (lid,)).fetchone()
        return Rating(*row) if row else Rating()

    def _put(self, lid: str, r: Rating) -> None:
        self.db.execute("INSERT OR REPLACE INTO ladder VALUES (?, ?, ?, ?, ?)", (lid, r.rating, r.rd, r.vol, r.games))

    def result(self, winner: str, loser: str) -> tuple[Rating, Rating]:
        """Rate one finished game; returns both new ratings."""
        w, l = play(self.get(winner), self.get(loser), True)
        floor = lambda lid, r: r if lid.startswith("bot:") or r.rd >= PLAYER_RD_FLOOR else replace(r, rd=PLAYER_RD_FLOOR)
        w, l = floor(winner, w), floor(loser, l)
        with self.db:
            self._put(winner, w); self._put(loser, l)
        return w, l

    def bots(self) -> dict[str, Rating]:
        """The bots that play: every level with every deck of the pool. A row of a deck that left the pool (a card
        change made it illegal), or of the old game's bots, keeps its games and never plays or shows."""
        return {lid: Rating(*rest) for lid, *rest in self.db.execute("SELECT id, rating, rd, vol, games FROM ladder WHERE id LIKE 'bot:%'")
                if (b := parse_bot(lid)) and b[0] in LEVELS and b[1] in self.decks}

    def nearest_bot(self, rating: float, rng, avoid=(), window: float = MATCH_WINDOW) -> str:
        """A bot for a player at `rating` (Martin, 2026-10-24: the bots are always there, so a person waits for nobody and
        the only question is who is close). The pairings within `window` of the player, minus `avoid` (the decks of the
        player's last bot games); among them the strongest level there (the stronger player teaches more), one at
        random. Nobody within the window, as at the very top: the nearest of each deck, the five nearest decks, one at
        random (Martin, 2026-10-02: variety)."""
        rows = [(lid, r) for lid, r in self.bots().items() if not r.provisional]
        near = [(lid, r) for lid, r in rows if abs(r.rating - rating) <= window and parse_bot(lid)[1] not in avoid]
        if near:
            for level in reversed(LEVELS):
                here = [lid for lid, _ in near if parse_bot(lid)[0] == level]
                if here:
                    return rng.choice(here)
        nearest: dict[str, tuple[float, str]] = {}
        for lid, r in rows:
            deck = parse_bot(lid)[1]
            if deck not in nearest or abs(r.rating - rating) < nearest[deck][0]:
                nearest[deck] = (abs(r.rating - rating), lid)
        ranked = list(nearest.items())
        rng.shuffle(ranked)                    # decks at the same distance (new bots share a start) take turns
        five = [(lid, deck) for deck, (_, lid) in sorted(ranked, key=lambda kv: kv[1][0])][:5]
        fresh = [lid for lid, deck in five if deck not in avoid]
        return rng.choice(fresh or [lid for lid, _ in five])

    def bot_in(self, lo: float, hi: float, rng, avoid=()) -> str | None:
        """A bot for a ranked player whose league plays bots rated from `lo` up to `hi` (web/tiers.py band; Martin,
        2026-11-05: you play opponents from your own league). As nearest_bot, minus `avoid` (the decks of the player's last
        bot games) and the strongest level there first; None when the band holds no bot, and the caller falls back to
        nearest_bot."""
        rows = [(lid, r) for lid, r in self.bots().items() if not r.provisional and lo <= r.rating < hi]
        here = [(lid, r) for lid, r in rows if parse_bot(lid)[1] not in avoid] or rows
        for level in reversed(LEVELS):
            pick = [lid for lid, _ in here if parse_bot(lid)[0] == level]
            if pick:
                return rng.choice(pick)
        return None

    def table(self) -> list[tuple[str, Rating]]:
        """Everyone on the ladder, best first: the bots that play, and the people with at least one game."""
        bots = self.bots()
        rows = self.db.execute("SELECT id, rating, rd, vol, games FROM ladder ORDER BY rating DESC").fetchall()
        return [(lid, Rating(*rest)) for lid, *rest in rows if lid in bots or (not lid.startswith("bot:") and rest[3] > 0)]
