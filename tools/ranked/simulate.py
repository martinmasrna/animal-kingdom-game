"""Ranked leagues, replayed: how the rules in animal_kingdom/web/tiers.py would have treated the people who played, and
how they treat synthetic players (docs/ranked-leagues.md, "The simulation").

    .venv/bin/python tools/ranked/simulate.py                    # people from the logs, then synthetic players
    .venv/bin/python tools/ranked/simulate.py --players results/players.json   # exact names and modes (deploy/deploy.sh players)
    .venv/bin/python tools/ranked/simulate.py --people-only | --synthetic-only

People. The game logs (results/human_games/web/*.jsonl) carry the seats (`bots`: who sat where), the decks, the winner
and the match id, and the file name the date; they carry neither the person nor whether the game was ranked. With
`--players` (the server's profiles and histories) each game gets its person and its mode, and only ranked games count.
Without it every human-against-bot game from 2026-10-01 (the ladder's first day) counts, and the person is read off the
deck (`attribute`): Kalista's mono Cats, Laras's lists built on Black Bear, Owl and Raven until her sixth day, Martin
for the rest. That is an inference from docs/playtests/2026-10-02.md and docs/wave-2.md, good for the shape of a climb,
not for anyone's exact record.

The rating the rules read (the rating bonus) is replayed with the ladder's own Glicko-2 (web/ladder.py), each bot at its
seeded rating (web/ladder_seed.json; a deck the seed doesn't have gets its pilot's median), the person from 1500.

Synthetic players: (1) a fixed win rate, as asked: 40%, 50%, 60% in every game, the rating moved by those results
against opponents at the player's own rating; (2) a fixed skill: the player's true strength is a rating, the opponent is
a bot within the matchmaking window of the player's current rating (ladder.MATCH_WINDOW), and the result is drawn from
the Glicko expectation. (2) is the honest model of this ladder: matchmaking by rating pulls every placed person's win
rate towards 50%, so a fixed 60% only exists while a rating is still catching up.
"""

from __future__ import annotations

import argparse
import collections
import datetime
import json
import random
import statistics
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from animal_kingdom.web import ladder as L          # noqa: E402
from animal_kingdom.web import tiers as T           # noqa: E402

GAMES = ROOT / "results" / "human_games" / "web"
SEED = ROOT / "animal_kingdom" / "web" / "ladder_seed.json"
CARDS = ROOT / "animal_kingdom" / "data" / "cards.json"
LADDER_START = "2026-10-01"
LARAS_LAST = "2026-10-06"        # "Laras ... stopped after six days" (docs/wave-2.md), from 1 October


# ----------------------------------------------------------------- reading the logs
def cat_share(cards: list[str], tags: dict) -> float:
    known = [c for c in cards if c in tags]      # a card renamed since has no tags here; it is left out of the share
    return sum("Cat" in (tags[c] or ()) for c in known) / max(1, len(known))


def attribute(cards: list[str], day: str, tags: dict) -> str:
    """Who played a list, read off the list itself (no profile in the logs)."""
    s = set(cards)
    if day <= LARAS_LAST and {"black_bear", "owl", "raven"} <= s:
        return "Laras"
    if day < "2026-10-17" and cat_share(cards, tags) >= 0.9:
        return "Kalista"
    return "Martin"


def read_games(players: Path | None) -> list[dict]:
    tags = {c["id"]: c.get("tags", []) for c in json.loads(CARDS.read_text())["cards"]}
    who = {}
    if players and players.is_file():
        d = json.loads(players.read_text())
        names = {p["id"]: p["name"] for p in d["profiles"]}
        who = {(h["match"], h.get("seat") or ""): (names.get(h["profile"], "?"), h.get("mode", "")) for h in d["history"]}
    out = []
    for f in sorted(GAMES.glob("*.jsonl")):
        stamp = f.name.split("_")[1]
        t = datetime.datetime.strptime(stamp[:15], "%Y%m%dT%H%M%S")
        day = t.date().isoformat()
        if day < LADDER_START:
            continue
        for line in f.read_text().splitlines():
            g = json.loads(line)
            humans = [i for i, b in enumerate(g["bots"]) if b == "human"]
            if len(humans) != 1:      # a game between two people: both sides unknown here, left out
                continue
            i = humans[0]; seat = "AB"[i]; opp = 1 - i
            cards = (g.get("lists") or [[], []])[i]
            if who:
                person, mode = who.get((f"{g['match_id']}-{g.get('series', 0)}", seat), ("?", ""))
                if mode != "ranked":
                    continue
            else:
                person = attribute(cards, day, tags)
            out.append({"t": t, "day": day, "person": person, "won": g["winner"] == seat,
                        "bot": L.bot_id(g["bots"][opp], g["deck_b" if i == 0 else "deck_a"])})
    out.sort(key=lambda g: g["t"])
    return out


def bot_ratings() -> tuple[dict, dict]:
    r = json.loads(SEED.read_text())["ratings"]
    med = {lv: statistics.median(v for k, v in r.items() if k.startswith(f"bot:{lv}:")) for lv in L.LEVELS}
    return r, med


# ----------------------------------------------------------------- one person's climb
class Climber:
    def __init__(self):
        self.rating, self.standing, self.games = L.Rating(), T.Standing(), 0
        self.reached: dict[int, int] = {1: 0}      # league -> games it took to first reach it

    def play(self, won: bool, opp: L.Rating) -> T.Change:
        ch = T.after_game(self.standing, won, self.rating.rating)
        new, _ = L.play(self.rating, opp, won)
        self.rating = new if new.rd >= L.PLAYER_RD_FLOOR else replace(new, rd=L.PLAYER_RD_FLOOR)
        self.standing, self.games = ch.after, self.games + 1
        self.reached.setdefault(ch.after.league, self.games)
        return ch


def short(s: T.Standing, rating: float) -> str:
    return f"L{s.league} top {round(rating)}" if s.league == T.TOP else f"L{s.league} {s.stars}/{T.stars_needed(s.league)}"


def people(games: list[dict]) -> None:
    seed, med = bot_ratings()
    by = collections.defaultdict(list)
    for g in games:
        by[g["person"]].append(g)
    print("PEOPLE (league at the end of each day played; L = league, stars/needed)")
    for person, gs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        c, days = Climber(), collections.OrderedDict()
        for g in gs:
            lv = L.parse_bot(g["bot"])[0]
            c.play(g["won"], L.bot_seed(seed.get(g["bot"], med.get(lv, 1500))))
            days[g["day"]] = (c.games, short(c.standing, c.rating.rating), round(c.rating.rating))
        w = sum(g["won"] for g in gs)
        print(f"\n{person}: {len(gs)} games, {w}-{len(gs) - w} ({100 * w / len(gs):.0f}%), {len(days)} days")
        print("  day         games  league        rating")
        for day, (n, lg, rt) in days.items():
            print(f"  {day}  {n:5d}  {lg:12s}  {rt}")
        print("  first reached: " + ", ".join(f"L{lg} after {n}" for lg, n in sorted(c.reached.items())))


# ----------------------------------------------------------------- synthetic players
def run_fixed(p: float, n: int, rng: random.Random) -> Climber:
    c = Climber()
    for _ in range(n):
        c.play(rng.random() < p, L.bot_seed(c.rating.rating))
    return c


def run_skill(skill: float, n: int, rng: random.Random) -> Climber:
    c = Climber()
    true = L.Rating(skill, L.BOT_RD)
    for _ in range(n):
        opp = L.bot_seed(min(2250.0, max(900.0, c.rating.rating + rng.uniform(-L.MATCH_WINDOW, L.MATCH_WINDOW))))
        c.play(rng.random() < L.expected(true, opp), opp)
    return c


def table(label: str, runs: list[Climber], checkpoints=(25, 50, 100, 200, 400)) -> None:
    def pct(xs, q):
        xs = sorted(xs); return xs[min(len(xs) - 1, int(q * len(xs)))]
    reach = []
    for lg in range(2, T.TOP + 1):
        got = [c.reached[lg] for c in runs if lg in c.reached]
        reach.append(f"L{lg} {pct(got, 0.5) if len(got) * 2 >= len(runs) else '-':>4}")
    print(f"  {label:14s} games to reach (median): " + " ".join(reach))


def synthetic(n_runs: int, games: int, seed: int) -> None:
    print(f"\nSYNTHETIC ({n_runs} runs each, {games} games; '-' = fewer than half the runs get there)")
    print(" fixed win rate:")
    for p in (0.4, 0.5, 0.6):
        rng = random.Random(seed)
        table(f"{int(p * 100)}%", [run_fixed(p, games, rng) for _ in range(n_runs)])
    print(" fixed skill (opponents within the matchmaking window of the current rating):")
    for skill in (1200, 1400, 1600, 1800, 2000, 2200):
        rng = random.Random(seed)
        table(f"skill {skill}", [run_skill(skill, games, rng) for _ in range(n_runs)])
    print(" league after N games (median), fixed skill:")
    for skill in (1200, 1400, 1600, 1800, 2000, 2200):
        rng = random.Random(seed)
        runs = []
        for _ in range(n_runs):
            c, at = Climber(), {}
            true = L.Rating(skill, L.BOT_RD)
            for k in range(1, games + 1):
                opp = L.bot_seed(min(2250.0, max(900.0, c.rating.rating + rng.uniform(-L.MATCH_WINDOW, L.MATCH_WINDOW))))
                c.play(rng.random() < L.expected(true, opp), opp)
                if k in (10, 25, 50, 100, 200, 400):
                    at[k] = c.standing.league
            runs.append(at)
        print(f"  skill {skill}: " + "  ".join(f"{k}g L{statistics.median(r[k] for r in runs):g}" for k in sorted(runs[0])))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--players", type=Path, help="results/players.json from deploy/deploy.sh players: exact people and modes")
    ap.add_argument("--people-only", action="store_true")
    ap.add_argument("--synthetic-only", action="store_true")
    ap.add_argument("--runs", type=int, default=300)
    ap.add_argument("--games", type=int, default=400)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    if not a.synthetic_only:
        people(read_games(a.players))
    if not a.people_only:
        synthetic(a.runs, a.games, a.seed)


if __name__ == "__main__":
    main()
