"""Run a simulation and write the §10 balance metrics.

Examples:
  python -m animal_kingdom.sim --decks all --games 200 --seed 0 --jobs 4 --out results/
  python -m animal_kingdom.sim --decks ramp,aggro_hq_rush --games 100 --bots greedy,random

A single matchup with two slugs, or the full round-robin with `--decks all`.
"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from ..engine.cards import DECK_SLUGS
from . import metrics
from .runner import run_matchup, run_round_robin


def _parse_bots(spec: str) -> tuple[str, str]:
    parts = spec.split(",")
    if len(parts) != 2 or any(p.strip().lower() not in ("greedy", "random") for p in parts):
        raise SystemExit("--bots expects two of greedy|random, e.g. greedy,greedy")
    return parts[0].strip().lower(), parts[1].strip().lower()


def main(argv: Sequence[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Run Animal Kingdom balance simulations.")
    p.add_argument("--decks", default="all",
                   help="'all' for the full round-robin, or two slugs (e.g. ramp,egg_control)")
    p.add_argument("--games", type=int, default=100, help="games per matchup")
    p.add_argument("--seed", type=int, default=0, help="base seed (games use seed, seed+1, ...)")
    p.add_argument("--bots", default="greedy,greedy", help="two of greedy|random")
    p.add_argument("--jobs", type=int, default=1, help="worker processes (round-robin only)")
    p.add_argument("--map", dest="map_id", default="map_a")
    p.add_argument("--out", default="results", help="output directory for the metrics bundle")
    args = p.parse_args(argv)

    bots = _parse_bots(args.bots)
    spec = args.decks.strip()
    if spec == "all":
        slugs = sorted(DECK_SLUGS)
        print(f"Round-robin: {len(slugs)} decks x {len(slugs)} = {len(slugs) ** 2} matchups, "
              f"{args.games} games each, {len(slugs) ** 2 * args.games} total "
              f"(bots={bots[0]},{bots[1]}, jobs={args.jobs})...")
        records = run_round_robin(slugs, args.games, args.seed, bots=bots,
                                  map_id=args.map_id, jobs=args.jobs)
    else:
        pair = spec.split(",")
        if len(pair) != 2:
            raise SystemExit("--decks expects 'all' or two comma-separated slugs")
        a, b = pair[0].strip(), pair[1].strip()
        print(f"Matchup: {a} vs {b}, {args.games} games (bots={bots[0]},{bots[1]})...")
        records = run_matchup(a, b, args.games, args.seed, bots=bots, map_id=args.map_id)

    summary = metrics.write_all(records, args.out)

    print(f"\nWrote {summary['games']} games to {args.out}/ "
          "(matchup_matrix.csv, per_card_winrate.csv, summary.json)")
    split = summary["win_condition_split"]["percent"]
    print("Win conditions: " + ", ".join(f"{k}={v:.1%}" for k, v in sorted(split.items())))
    fp = summary["first_player_win_rate"]["rate"]
    print(f"First-player win rate: {fp:.1%}" if fp is not None else "First-player win rate: n/a")
    print(f"Avg game length: {summary['avg_game_length']['overall']:.1f} turns")
    print(f"\nCaveat: {summary['caveat']}")


if __name__ == "__main__":
    main(sys.argv[1:])
