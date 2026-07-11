"""Measure one deck's win rate vs a field under a chosen pilot - the balance-tuning workhorse.

Reused every crank-measure iteration: point it at a deck (premade slug or a registered synthetic
like `goodstuff`), a field of opponents, a pilot, and a `--config` override, and it prints the
per-matchup win rate + mean. For synergy-deck tuning use `--pilot turn` (or referee): GreedyBot
under-pilots synergy decks, so tuning against it over-buffs (the recurring caveat).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from ..engine.cards import DECK_SLUGS
from ..engine.config import load_config_overrides
from .deck_optimizer import register_synthetic, make_recipe
from .runner import run_pairs

GOODSTUFF_RECIPE = Path("results/deck_optimizer/finalist_recipe.json")


def main(argv: Sequence[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--deck", required=True, help="deck to measure (premade slug or 'goodstuff')")
    p.add_argument("--field", default="",
                   help="comma-separated opponent slugs (default: all premades except --deck)")
    p.add_argument("--with-goodstuff", action="store_true",
                   help="register the goodstuff pile and add it to the field")
    p.add_argument("--goodstuff", type=Path, default=GOODSTUFF_RECIPE)
    p.add_argument("--pilot", default="turn", help="bot kind for both seats (turn|referee|greedy)")
    p.add_argument("--games", type=int, default=50, help="games/opponent PER MOVER (2x = per matchup)")
    p.add_argument("--base-seed", type=int, default=414000)
    p.add_argument("--jobs", type=int, default=8)
    p.add_argument("--config", default=None)
    args = p.parse_args(argv)

    config = load_config_overrides(args.config)
    need_goodstuff = args.with_goodstuff or args.deck == "goodstuff" or "goodstuff" in args.field
    if need_goodstuff:
        data = json.loads(args.goodstuff.read_text())
        register_synthetic("goodstuff", make_recipe(**data).decklist())

    if args.field:
        field = [s.strip() for s in args.field.split(",")]
    else:
        field = [s for s in sorted(DECK_SLUGS) if s != args.deck]
        if args.with_goodstuff:
            field.append("goodstuff")

    print(f"{args.deck} vs {len(field)} decks | pilot {args.pilot} | "
          f"{2*args.games} games/matchup | config {args.config or 'default'}\n", file=sys.stderr)

    def _prog(a, b, done, total, recs):
        wr = sum(1.0 if r.winner == "A" else (0.5 if r.winner is None else 0.0)
                 for r in recs) / len(recs)
        print(f"  [{done}/{len(field)}] vs {b:<20} {wr:.1%}", file=sys.stderr)

    pairs = [(args.deck, f) for f in field]
    records = run_pairs(pairs, args.games, args.base_seed, bots=(args.pilot, args.pilot),
                        config=config, jobs=args.jobs, matchup_progress=_prog)

    per: dict[str, list[float]] = {f: [0.0, 0] for f in field}
    for rec in records:
        cell = per[rec.deck_b]
        cell[0] += 1.0 if rec.winner == "A" else (0.5 if rec.winner is None else 0.0)
        cell[1] += 1
    rates = {f: per[f][0] / per[f][1] for f in field}
    print(f"\n{args.deck} win rate vs field (pilot {args.pilot}):")
    for f, wr in sorted(rates.items(), key=lambda kv: kv[1]):
        print(f"  vs {f:<20} {wr:.1%}")
    print(f"  mean {sum(rates.values())/len(rates):.1%} | worst {min(rates.values()):.1%}")


if __name__ == "__main__":
    main(sys.argv[1:])
