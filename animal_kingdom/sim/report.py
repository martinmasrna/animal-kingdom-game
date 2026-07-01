"""Per-card balance report: full 7x7 round-robin, printed as one impact table per deck.

Same simulation/metrics machinery as `python -m animal_kingdom.sim` (that module writes
the raw CSV/JSON bundle); this one prints human-readable per-deck card tables instead,
sorted by `impact` (win_rate_when_drawn minus the deck's own baseline win rate) so the
over/under-performing cards in each deck surface at the top/bottom.

Examples:
  python -m animal_kingdom.sim.report 500
  python -m animal_kingdom.sim.report 200 --bots random,random --jobs 4
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from collections import defaultdict
from typing import Sequence

from ..engine.cards import DECK_SLUGS, Card, load_cards
from . import metrics
from .runner import GameRecord, run_round_robin

RARITY_MARK = {"legendary": "\U0001F7E1", "rare": "\U0001F535", "common": "⚪"}  # yellow/blue/white


def _parse_bots(spec: str) -> tuple[str, str]:
    parts = spec.split(",")
    if len(parts) != 2 or any(p.strip().lower() not in ("greedy", "random") for p in parts):
        raise SystemExit("--bots expects two of greedy|random, e.g. greedy,greedy")
    return parts[0].strip().lower(), parts[1].strip().lower()


def _card_line(row: dict, card: Card) -> str:
    wwd = f"{row['win_rate_when_drawn']:.1%}" if row["win_rate_when_drawn"] is not None else "n/a"
    imp = f"{row['impact']:+.1%}" if row["impact"] is not None else "n/a"
    tag = "/".join(sorted(card.tags)) or "-"
    info = f"{tag} · STR {card.base_strength} · {card.text or '(vanilla)'}"
    mark = RARITY_MARK[card.rarity]
    return f"{mark}  {row['card_id']:<16}{wwd:>9}{imp:>8}   {info}"


def format_report(records: Sequence[GameRecord], cards: dict[str, Card]) -> str:
    """One impact-sorted card table per deck, as a single printable string."""
    by_deck: dict[str, list[dict]] = defaultdict(list)
    for row in metrics.per_card_stats(records):     # already sorted by impact desc, overall
        by_deck[row["deck"]].append(row)             # per-deck order is preserved (stable sort)

    sections = []
    for deck in sorted(by_deck):
        deck_rows = by_deck[deck]
        baseline = deck_rows[0]["deck_win_rate"]
        lines = [f"\n### {deck} (deck win rate {baseline:.1%})", "```",
                f"   {'card':<16}{'WR_drawn':>9}{'impact':>8}   tag / str / text"]
        lines += [_card_line(row, cards[row["card_id"]]) for row in deck_rows]
        lines.append("```")
        sections.append("\n".join(lines))
    return "\n".join(sections)


def main(argv: Sequence[str] | None = None) -> None:
    p = argparse.ArgumentParser(
        description="Full 7x7 round-robin, printed as one per-card impact table per deck.")
    p.add_argument("games", type=int, help="games per matchup (49 matchups in the 7x7 grid)")
    p.add_argument("--seed", type=int, default=0, help="base seed (games use seed, seed+1, ...)")
    p.add_argument("--bots", default="greedy,greedy", help="two of greedy|random")
    p.add_argument("--jobs", type=int, default=os.cpu_count() or 1, help="worker processes")
    p.add_argument("--map", dest="map_id", default="map_a")
    args = p.parse_args(argv)

    bots = _parse_bots(args.bots)
    slugs = sorted(DECK_SLUGS)
    total_matchups = len(slugs) ** 2
    total_games = total_matchups * args.games
    print(f"Running {len(slugs)}x{len(slugs)} round-robin, {args.games} games/matchup "
          f"({total_games} games total, bots={bots[0]},{bots[1]}, jobs={args.jobs})...", file=sys.stderr)

    start = time.monotonic()

    def _progress(a: str, b: str, done: int, matchup_total: int) -> None:
        elapsed = time.monotonic() - start
        games_done = done * args.games
        print(f"  [{done:>2}/{matchup_total}] {elapsed:6.1f}s  {a} vs {b}  "
              f"({games_done}/{total_games} games)", file=sys.stderr)

    records = run_round_robin(slugs, args.games, args.seed, bots=bots,
                              map_id=args.map_id, jobs=args.jobs, progress=_progress)
    print(f"Simulation done in {time.monotonic() - start:.1f}s.\n", file=sys.stderr)
    print(format_report(records, load_cards()))


if __name__ == "__main__":
    main(sys.argv[1:])
