"""Ranked leagues, simulated: where the rules in animal_kingdom/web/tiers.py settle players of a given strength
(docs/ranked-leagues.md, "The simulation").

    .venv/bin/python tools/ranked/simulate.py [--runs 300] [--games 400] [--seed 1]

A player has a fixed true strength, a rating. Each game's opponent is what the server picks: below the top league a bot
from the league's band of the seeded bot ratings (web/ladder_seed.json, tiers.band), in the top league a bot within the
matchmaking window of the player's rating. The result is drawn from the Glicko expectation of strength against the bot.
The player's rating runs beside the stars as on the server; it only matters once they reach the top league.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from animal_kingdom.web import ladder as L, tiers as T   # noqa: E402

SEED = ROOT / "animal_kingdom/web/ladder_seed.json"
STRENGTHS = (1100, 1300, 1500, 1700, 1900, 2100)


def opponent(rating: float, standing: T.Standing, bots: list[float], rng: random.Random) -> float:
    if standing.league == T.TOP:
        near = [b for b in bots if abs(b - rating) <= L.MATCH_WINDOW]
        return rng.choice(near) if near else min(bots, key=lambda b: abs(b - rating))
    lo, hi = T.band(standing.league)
    here = [b for b in bots if lo <= b < hi]
    return rng.choice(here) if here else min(bots, key=lambda b: abs(b - T.par(standing.league) - 50))


def climb(strength: float, games: int, bots: list[float], rng: random.Random) -> dict:
    s, rating, true = T.Standing(), L.Rating(), L.Rating(strength, L.BOT_RD)
    top_at, wins_last = None, []
    for g in range(1, games + 1):
        opp = L.bot_seed(opponent(rating.rating, s, bots, rng))
        won = rng.random() < L.expected(true, opp)
        s = T.after_game(s, won).after
        new, _ = L.play(rating, opp, won)
        rating = new if new.rd >= L.PLAYER_RD_FLOOR else replace(new, rd=L.PLAYER_RD_FLOOR)
        if s.league == T.TOP and top_at is None:
            top_at = g
        if g > games - 100:
            wins_last.append(won)
    return {"league": s.league, "top_at": top_at, "won_last": sum(wins_last) / len(wins_last)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--runs", type=int, default=300)
    ap.add_argument("--games", type=int, default=400)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    bots = sorted(json.loads(SEED.read_text())["ratings"].values())
    print(f"{a.runs} runs of {a.games} games each; opponents from the {len(bots)} seeded bots")
    print("strength  reached the top  median games to it  league after (median)  won of the last 100")
    for strength in STRENGTHS:
        rng = random.Random(a.seed)
        runs = [climb(strength, a.games, bots, rng) for _ in range(a.runs)]
        tops = [r["top_at"] for r in runs if r["top_at"]]
        print(f"{strength:8d}  {100 * len(tops) / len(runs):14.0f}%  {statistics.median(tops) if tops else '-':>18}"
              f"  {statistics.median(r['league'] for r in runs):>21g}  {statistics.mean(r['won_last'] for r in runs):18.0%}")


if __name__ == "__main__":
    main()
