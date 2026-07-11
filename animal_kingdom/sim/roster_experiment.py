"""Tier 1 conquest experiment: does a disjoint 3-deck roster + conquest punish concentration?

Sets up two rosters drawn from the same card pool:
  * CONCENTRATE = [goodstuff, leftover1, leftover2] - all the best cards jammed into one deck,
    the other two optimized from the *residual* pool (goodstuff's 14 cards removed), so the
    concentrator gets its fairest possible leftovers rather than a strawman.
  * SPREAD      = three chosen premades (mutually disjoint by construction).

It measures the real 3x3 deck-vs-deck win-rate matrix (GreedyBot) and solves the series two
ways (see conquest.py): last-hero (concentration is *supposed* to win) vs conquest (winner's
deck retired). The gap between them is the whole question: if concentrate wins last-hero but
loses conquest, the format works.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path
from typing import Optional, Sequence

from ..engine.config import Config, load_config_overrides
from .conquest import conquest_series, last_hero_series
from .deck_optimizer import (
    Recipe, draftable_by_rarity, hill_climb, make_recipe, random_recipe,
    register_synthetic, format_recipe,
)
from .runner import run_pairs

DEFAULT_GOODSTUFF = Path("results/deck_optimizer/finalist_recipe.json")


def load_recipe(path: Path) -> Recipe:
    data = json.loads(path.read_text())
    return make_recipe(data["legendary"], data["rare"], data["common"])


def build_leftover(
    opponents: Sequence[str], exclude: frozenset[str], *, rng: random.Random,
    search_games: int, steps: int, pilot: str, jobs: int, config: Optional[Config],
    label: str,
) -> Recipe:
    """Best deck vs `opponents`, hill-climbed from the pool minus `exclude` (disjointness)."""
    pools = draftable_by_rarity(exclude=exclude)
    start = random_recipe(rng, pools)
    result = hill_climb(
        start, opponents, n_games=search_games, base_seed=606000, pilot=pilot, jobs=jobs,
        config=config, max_steps=steps, neighbors=10, patience=5, objective="mean",
        rng=rng, pools=pools,
    )
    print(f"  {label}: mean {result.best_eval.mean:.1%} vs spread", file=sys.stderr)
    return result.best_recipe


def matchup_matrix(
    rows: Sequence[str], cols: Sequence[str], *, n_games: int, base_seed: int,
    pilot: str, jobs: int, config: Optional[Config],
) -> tuple[list[list[float]], list]:
    """M[i][j] = win rate of rows[i] (as deck_a/seat A) vs cols[j], both movers pooled.

    Also returns the raw GameRecords (each carries the row deck's drawn cards, for --card-winrates)."""
    pairs = [(r, c) for r in rows for c in cols]
    total_pairs = len(pairs)

    def _game_prog(a: str, b: str, done: int, pair_total: int) -> None:
        if done % 20 == 0 or done == pair_total:
            print(f"    {a} vs {b}: {done}/{pair_total} games", file=sys.stderr)

    def _matchup_prog(a: str, b: str, done: int, _total: int, recs: list) -> None:
        wr = sum(r.credit("A") for r in recs) / len(recs)
        print(f"  [{done}/{total_pairs}] {a} vs {b}: {a} wins {wr:.1%}", file=sys.stderr)

    records = run_pairs(pairs, n_games, base_seed, bots=(pilot, pilot),
                        config=config, jobs=jobs,
                        game_progress=_game_prog, matchup_progress=_matchup_prog)
    agg: dict[tuple[str, str], list[float]] = {(r, c): [0.0, 0] for r in rows for c in cols}
    for rec in records:
        cell = agg[(rec.deck_a, rec.deck_b)]
        cell[0] += rec.credit("A")
        cell[1] += 1
    matrix = [[agg[(r, c)][0] / agg[(r, c)][1] for c in cols] for r in rows]
    return matrix, records


def card_winrates(records, row_decks: Sequence[str]) -> dict[str, dict[str, tuple[float, int]]]:
    """Per row deck, each card's win-rate-when-drawn: card_id -> (win_rate, games_drawn).

    Presence-only (was the card in hand at any point). Read as a within-deck, same-rarity
    relative signal of which cards ride with wins - compare like copy-counts in one deck."""
    from collections import defaultdict
    stats: dict[str, dict[str, list[float]]] = {d: defaultdict(lambda: [0.0, 0]) for d in row_decks}
    for rec in records:
        if rec.deck_a not in stats:
            continue
        credit = rec.credit("A")
        for cid in rec.cards_drawn_a:
            entry = stats[rec.deck_a][cid]
            entry[0] += credit
            entry[1] += 1
    return {d: {cid: (w / n, n) for cid, (w, n) in cards.items()} for d, cards in stats.items()}


def main(argv: Sequence[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--goodstuff", type=Path, default=DEFAULT_GOODSTUFF)
    p.add_argument("--spread", default="cats_midrange,ramp,aggro_hq_rush",
                   help="three mutually-disjoint premade slugs for the SPREAD roster")
    p.add_argument("--pilot", default="greedy")
    p.add_argument("--matrix-games", type=int, default=150, help="games/pair per mover")
    p.add_argument("--leftover-games", type=int, default=25, help="search games/opp per mover")
    p.add_argument("--leftover-steps", type=int, default=20)
    p.add_argument("--rng-seed", type=int, default=3)
    p.add_argument("--jobs", type=int, default=os.cpu_count() or 1, help="worker processes")
    p.add_argument("--config", default=None)
    p.add_argument("--from-result", type=Path,
                   help="load the leftover decks from a prior run's JSON and just RE-MEASURE the "
                        "matrix (skip optimization) - e.g. to re-score under a different --pilot")
    p.add_argument("--card-winrates", action="store_true",
                   help="also print each non-premade deck's per-card win-rate-when-drawn "
                        "(presence-only; a within-deck, same-rarity relative signal)")
    p.add_argument("--out", type=Path)
    args = p.parse_args(argv)

    config = load_config_overrides(args.config)
    goodstuff = load_recipe(args.goodstuff)
    rng = random.Random(args.rng_seed)

    if args.from_result:
        prior = json.loads(args.from_result.read_text())
        spread = prior["spread"]
        l1 = make_recipe(**prior["leftover1"])
        l2 = make_recipe(**prior["leftover2"])
        print(f"Re-measuring saved decks from {args.from_result} under {args.pilot}", file=sys.stderr)
    else:
        spread = [s.strip() for s in args.spread.split(",")]
        print(f"Building concentrator leftovers vs spread {spread} ...", file=sys.stderr)
        l1 = build_leftover(spread, goodstuff.all_ids(), rng=rng, search_games=args.leftover_games,
                            steps=args.leftover_steps, pilot=args.pilot, jobs=args.jobs,
                            config=config, label="leftover1")
        l2 = build_leftover(spread, goodstuff.all_ids() | l1.all_ids(), rng=rng,
                            search_games=args.leftover_games, steps=args.leftover_steps,
                            pilot=args.pilot, jobs=args.jobs, config=config, label="leftover2")

    register_synthetic("goodstuff", goodstuff.decklist())
    register_synthetic("leftover1", l1.decklist())
    register_synthetic("leftover2", l2.decklist())
    concentrate = ["goodstuff", "leftover1", "leftover2"]

    print(f"\nMeasuring 3x3 matchup matrix ({2*args.matrix_games} games/pair)...", file=sys.stderr)
    matrix, records = matchup_matrix(concentrate, spread, n_games=args.matrix_games,
                                     base_seed=717000, pilot=args.pilot, jobs=args.jobs, config=config)

    print("\nCONCENTRATE roster:")
    print(f"  goodstuff:\n{format_recipe(goodstuff)}")
    print(f"  leftover1:\n{format_recipe(l1)}")
    print(f"  leftover2:\n{format_recipe(l2)}")
    print(f"\nSPREAD roster: {', '.join(spread)}")

    print("\nMatchup matrix (concentrate row vs spread col, row win rate):")
    print("                 " + "".join(f"{c[:10]:>12}" for c in spread))
    for name, row in zip(concentrate, matrix):
        print(f"  {name:<12} " + "".join(f"{v:>11.1%} " for v in row))
    conc_deck_wr = [sum(row) / len(row) for row in matrix]
    print("  mean per concentrate deck: "
          + ", ".join(f"{n}={w:.0%}" for n, w in zip(concentrate, conc_deck_wr)))

    conquest_p = conquest_series(matrix)
    lasthero_p = last_hero_series(matrix)
    print(f"\n--- series win probability for the CONCENTRATE roster ---")
    print(f"  last-hero (replay allowed):   {lasthero_p:.1%}")
    print(f"  conquest  (winner retired):   {conquest_p:.1%}")
    verdict = ("conquest PUNISHES concentration" if conquest_p < 0.5 <= lasthero_p
               else "conquest did NOT flip the result")
    print(f"\nVerdict: last-hero {lasthero_p:.0%} -> conquest {conquest_p:.0%}  =>  {verdict}")

    if args.card_winrates:
        from ..engine.cards import load_cards
        names = {cid: c.name for cid, c in load_cards().items()}
        deck_wr = dict(zip(concentrate, (sum(r) / len(r) for r in matrix)))
        per = card_winrates(records, concentrate)
        print("\n--- per-card win-rate-when-drawn (presence-only; within-deck relative) ---")
        for deck in concentrate:
            print(f"\n  {deck}  (deck overall {deck_wr[deck]:.0%} vs spread):")
            for cid, (wr, n) in sorted(per[deck].items(), key=lambda kv: -kv[1][0]):
                flag = "  <- below deck avg" if wr < deck_wr[deck] - 0.05 else ""
                print(f"    {names.get(cid, cid):<20} {wr:>6.1%}  (drawn {n}){flag}")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps({
            "spread": spread, "concentrate": concentrate,
            "leftover1": {"legendary": l1.legendary, "rare": l1.rare, "common": l1.common},
            "leftover2": {"legendary": l2.legendary, "rare": l2.rare, "common": l2.common},
            "matrix": matrix, "matrix_games_per_pair": 2 * args.matrix_games,
            "conquest_winrate": conquest_p, "lasthero_winrate": lasthero_p,
        }, indent=2) + "\n")
        print(f"\nWrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
