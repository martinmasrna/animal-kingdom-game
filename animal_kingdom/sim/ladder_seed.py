"""Seed the ladder's bots (web/ladder.py): a round robin of every level-and-deck bot against every other, then each
bot's rating fitted to the results (Bradley-Terry on the Elo scale, the field centred at 1500).

    python -m animal_kingdom.sim.ladder_seed --games 3 --jobs 4 --out results/ladder/seed.json

Each pair meets `games` times, seats alternating. Draws are left out, as on the ladder. The output holds the games and
the fitted ratings by bot ladder id; the server reads the ratings (ladder.Ladder.seed_bots).
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path

from ..decks import PREMADE_DECKS
from ..web.ladder import LEVELS, bot_id
from ..web.match import BOT_LEVELS
from .runner import MatchSpec, run_specs


def bots() -> list[tuple[str, str]]:
    return [(level, deck) for level in LEVELS for deck in sorted(PREMADE_DECKS) if deck != "goodstuff"]


def fit(results: list[tuple[str, str]], iters: int = 2000) -> dict[str, float]:
    """Ratings (Elo scale, mean 1500) from (winner, loser) pairs, by the minorise-maximise iteration for Bradley-Terry.
    A bot that won or lost everything has no finite rating: one half win against every opponent is added as a prior."""
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


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--games", type=int, default=3, help="games per pair of bots")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--out", default="results/ladder/seed.json")
    args = ap.parse_args(argv)
    field, specs, who = bots(), [], []
    for k, (a, b) in enumerate(itertools.combinations(field, 2)):
        for g in range(args.games):
            x, y = (a, b) if g % 2 == 0 else (b, a)
            specs.append(MatchSpec(x[1], y[1], 1000 * k + g, bot_a=BOT_LEVELS[x[0]], bot_b=BOT_LEVELS[y[0]]))
            who.append((bot_id(*x), bot_id(*y)))
    print(f"{len(specs)} games, {args.jobs} jobs", flush=True)
    records = run_specs(specs, jobs=args.jobs)
    games = [{"a": a, "b": b, "winner": r.winner, "reason": r.reason, "turns": r.turns} for (a, b), r in zip(who, records)]
    rated = [(g["a"], g["b"]) if g["winner"] == "A" else (g["b"], g["a"]) for g in games if g["winner"]]
    ratings = fit(rated)
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"games": games, "ratings": ratings}, indent=1))
    for lid, r in sorted(ratings.items(), key=lambda kv: -kv[1]):
        print(f"{round(r):5d}  {lid}")


if __name__ == "__main__":
    main()
