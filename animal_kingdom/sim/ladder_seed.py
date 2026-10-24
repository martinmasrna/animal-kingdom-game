"""Seed the ladder's bots (web/ladder.py): every level-and-deck bot (the levels times decks.BOT_DECKS) rated by Bradley-Terry
on the Elo scale from games against each other, the field centred at 1500.

    python -m animal_kingdom.sim.ladder_seed --games 3 --jobs 4 --out results/ladder/seed.json            # a round robin
    python -m animal_kingdom.sim.ladder_seed --rounds 12 --per-round 4 --jobs 7 --out results/ladder/seed.json   # matchmaking

A round robin meets every pair `games` times, seats alternating: exact, and quadratic in the field (45 bots: 3,000 games;
129: 25,000). With `--rounds`, the field is rated the way a ladder rates it (Martin, 2026-10-24): each round every bot
plays `--per-round` games, most against bots near its current rating and some against anyone, the ratings are refitted on
all games so far, and the next round's matchmaking uses them; a bot's start is its rating in `--anchor` when it has one,
else its level's default. Twelve rounds of four give every bot about a hundred games for a tenth of the round robin's cost.
Draws are left out, as on the ladder. The output holds the games and the fitted ratings by bot ladder id; the server reads
the ratings (ladder.Ladder.seed_bots). `--anchor` (an earlier seed file, usually the shipped one) shifts the new ratings so
the bots in both keep their mean: new decks join the scale people were already rated on instead of pushing the field
down. A rerun resumes from the games already played.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import random
from pathlib import Path

from ..decks import BOT_DECKS
from ..web.ladder import LEVELS, bot_id
from ..web.match import BOT_LEVELS
from .runner import MatchSpec, run_specs


def bots() -> list[tuple[str, str]]:
    return [(level, deck) for level in LEVELS for deck in sorted(BOT_DECKS)]   # the bot pool: what ranked offers


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
    ap.add_argument("--batch", type=int, default=32, help="games per batch written to disk")
    ap.add_argument("--out", default="results/ladder/seed.json")
    ap.add_argument("--expert", default=None, help="the Expert's bot kind, with options (e.g. 'referee:depth=1,den_sense=1'); default: the web's")
    ap.add_argument("--anchor", default=None, help="an earlier seed file: the ratings shift so the bots in both keep their mean")
    ap.add_argument("--rounds", type=int, default=0, help="matchmaking rounds instead of a round robin (0: round robin)")
    ap.add_argument("--per-round", type=int, default=4, help="games each bot starts per matchmaking round")
    ap.add_argument("--near", type=int, default=12, help="how many rating neighbours a matchmaking game is drawn from")
    args = ap.parse_args(argv)
    kinds = dict(BOT_LEVELS, expert=args.expert) if args.expert else BOT_LEVELS
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    log = out.with_suffix(".games.jsonl")   # every finished game, appended batch by batch: a rerun resumes where it stopped
    done = {json.loads(l)["seed"] for l in log.read_text().splitlines() if l.strip()} if log.exists() else set()
    field = bots()

    def play(todo):
        for i in range(0, len(todo), args.batch):
            chunk = todo[i:i + args.batch]
            records = run_specs([c[0] for c in chunk], jobs=args.jobs)
            with log.open("a") as fh:
                for (spec, a, b), r in zip(chunk, records):
                    fh.write(json.dumps({"seed": spec.seed, "a": a, "b": b, "winner": r.winner, "reason": r.reason, "turns": r.turns}) + "\n")
            print(f"{len(done) + i + len(chunk)} games written", flush=True)

    def refit():
        games = [json.loads(l) for l in log.read_text().splitlines() if l.strip()]
        rated = [(g["a"], g["b"]) if g["winner"] == "A" else (g["b"], g["a"]) for g in games if g["winner"]]
        return games, (fit(rated) if rated else {})

    if args.rounds:
        start = json.loads(Path(args.anchor).read_text())["ratings"] if args.anchor else {}
        level_start = {"easy": 1200.0, "normal": 1500.0, "expert": 1800.0}
        by_id = {bot_id(*b): b for b in field}
        for r in range(args.rounds):
            games, fitted = refit() if r else ([], {})
            current = {lid: fitted.get(lid, start.get(lid, level_start[b[0]])) for lid, b in by_id.items()}
            order = sorted(by_id, key=lambda lid: current[lid])
            rng, todo = random.Random(1_000_003 * r), []
            for i, lid in enumerate(order):
                pos = order.index(lid)
                near = [o for o in order[max(0, pos - args.near):pos + args.near + 1] if o != lid]
                for g in range(args.per_round):
                    seed = 10_000_000 * r + 1000 * i + g
                    if seed in done:
                        continue
                    opp = rng.choice(near) if rng.random() < 0.8 and near else rng.choice([o for o in order if o != lid])
                    x, y = (by_id[lid], by_id[opp]) if g % 2 == 0 else (by_id[opp], by_id[lid])
                    todo.append((MatchSpec(x[1], y[1], seed, bot_a=kinds[x[0]], bot_b=kinds[y[0]]), bot_id(*x), bot_id(*y)))
            print(f"round {r + 1}/{args.rounds}: {len(games)} games so far, {len(todo)} to play, {args.jobs} jobs", flush=True)
            play(todo)
            done |= {t[0].seed for t in todo}
    else:
        todo = []
        for k, (a, b) in enumerate(itertools.combinations(field, 2)):
            for g in range(args.games):
                x, y = (a, b) if g % 2 == 0 else (b, a)
                seed = 1000 * k + g
                if seed not in done:
                    todo.append((MatchSpec(x[1], y[1], seed, bot_a=kinds[x[0]], bot_b=kinds[y[0]]), bot_id(*x), bot_id(*y)))
        print(f"{len(done)} games done, {len(todo)} to play, {args.jobs} jobs", flush=True)
        play(todo)
    games, ratings = refit()
    shift = 0.0
    if args.anchor:
        old = json.loads(Path(args.anchor).read_text())["ratings"]; common = [lid for lid in ratings if lid in old]
        shift = sum(old[lid] - ratings[lid] for lid in common) / len(common)
        ratings = {lid: r + shift for lid, r in ratings.items()}
        print(f"anchored to {args.anchor}: {len(common)} bots in common, shifted {shift:+.0f}")
    out.write_text(json.dumps({"games": len(games), "anchor": args.anchor, "shift": shift, "ratings": ratings}, indent=1))
    for lid, r in sorted(ratings.items(), key=lambda kv: -kv[1]):
        print(f"{round(r):5d}  {lid}")


if __name__ == "__main__":
    main()
