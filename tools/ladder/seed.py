"""Measure the ranked bots: every bot of the pool (each level with each legal premade deck) rated from games against each
other, and written to the seed the server reads (animal_kingdom/web/ladder_seed.json; web/pool.py says how it is used).

    .venv/bin/python tools/ladder/seed.py                 # about two minutes with two decks, ten with five
    .venv/bin/python tools/ladder/seed.py --games 40      # twice the games a pair, half the noise

Run it after a change to the cards or to a premade deck, as the race evaluation is refitted (tools/bot_bench/README.md):
until then the bots that change reached stand on their level's rating. It plays on the map the server ships with
(`--map`, staging's map_sq16 unless said), every pair of bots `--games` times, each deal twice with the seats swapped, so
neither the shuffle nor going first favours one. The ratings are Bradley-Terry on the Elo scale, the field centred at
1500; a draw is left out, as on the ladder. Every bot is seeded from the deal, so a run with the same arguments on the
same commit plays the same games.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import ak_engine  # noqa: E402

from animal_kingdom import game  # noqa: E402
from animal_kingdom.web import ladder, pool  # noqa: E402
from animal_kingdom.web.match import BOT_LEVELS  # noqa: E402

ACTIONS_MAX = 5000   # a game still going after this many actions is left out (none has come near)


def play(engine, a: tuple, b: tuple, seed: int):
    """One game, bot `a` in seat A: the winning seat, or None."""
    (la, da), (lb, db) = a, b
    rs = engine.new_game(da["cards"], db["cards"], seed, None, {"A": da["leader"], "B": db["leader"]})
    bots = {"A": ak_engine.Bot(BOT_LEVELS[la], seed), "B": ak_engine.Bot(BOT_LEVELS[lb], seed + 1)}
    for _ in range(ACTIONS_MAX):
        result = rs.is_terminal()
        if result is not None:
            return result["winner"]
        rs.apply_action(bots[rs.player_to_act()].choose(rs), False)
    return None


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--games", type=int, default=20, help="games per pair of bots (an even number: each deal is played from both seats)")
    ap.add_argument("--map", default="map_sq16")
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    ap.add_argument("--out", default=str(pool.SEED_FILE))
    args = ap.parse_args(argv)
    decks = pool.legal()
    out_of = [d["name"] for d in pool.premade() if d not in decks]
    field = [(level, d) for d in decks for level in ladder.LEVELS]
    lid = lambda bot: ladder.bot_id(bot[0], bot[1]["slug"])
    engine = game._engine_for(None, None, args.map)
    jobs = []
    for k, (a, b) in enumerate(itertools.combinations(field, 2)):
        for g in range(args.games // 2):
            seed = 1000 * k + g
            jobs += [(a, b, seed), (b, a, seed)]
    print(f"{len(decks)} decks ({', '.join(d['name'] for d in decks)}), {len(field)} bots, {len(jobs)} games on {args.map}, {args.jobs} at a time"
          + (f"; not legal today, so out: {', '.join(out_of)}" if out_of else ""), flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(args.jobs) as ex:   # a bot thinks with the interpreter released
        winners = list(ex.map(lambda j: play(engine, *j), jobs))
    rated = [(lid(a), lid(b)) if w == "A" else (lid(b), lid(a)) for (a, b, _), w in zip(jobs, winners) if w]
    ratings = ladder.fit(rated)
    levels = {level: {"bot": BOT_LEVELS[level], "rating": round(sum(ratings[lid((level, d))] for d in decks) / len(decks), 1)} for level in ladder.LEVELS}
    rows = {lid(bot): {"rating": round(ratings[lid(bot)], 1), "with": pool.measured_with(bot[0], bot[1], args.map)} for bot in field}
    # the version names this measurement: the server sets a bot from a seed once, and again when the version moves
    version = f"{time.strftime('%Y-%m-%d')} {hashlib.sha1(json.dumps(rows, sort_keys=True).encode()).hexdigest()[:8]}"
    seed = {"version": version, "map": args.map, "games": len(rated), "levels": levels, "ratings": rows}
    Path(args.out).write_text(json.dumps(seed, indent=1) + "\n", encoding="utf-8")
    print(f"{len(rated)} games rated ({len(jobs) - len(rated)} without a winner) in {time.time() - t0:.0f} s; written to {args.out}")
    for level in reversed(ladder.LEVELS):
        row = "  ".join(f"{d['name']} {round(ratings[lid((level, d))])}" for d in decks)
        print(f"level {level}  {levels[level]['rating']:6.0f}   {row}   {BOT_LEVELS[level]}")
    top = max(ratings.values()); low = min(ratings.values())
    print(f"spread: {round(low)} to {round(top)} ({round(top - low)} points)")


if __name__ == "__main__":
    main()
