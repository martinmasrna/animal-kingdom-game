"""Per-card balance report: full 7x7 round-robin, printed as one impact table per deck.

Same simulation/metrics machinery as `python -m animal_kingdom.sim` (that module writes
the raw CSV/JSON bundle); this one prints human-readable per-deck card tables instead,
sorted by `impact` (win_rate_when_drawn minus the deck's own baseline win rate) so the
over/under-performing cards in each deck surface at the top/bottom.

Examples:
  python -m animal_kingdom.sim.report 500
  python -m animal_kingdom.sim.report 200 --bots random,random --jobs 4
  python -m animal_kingdom.sim.report 500 --deck aggro   # only aggro_hq_rush's matchups/tables
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from collections import defaultdict
from typing import Optional, Sequence

from ..engine.cards import DECK_SLUGS, Card, load_cards
from ..engine.config import load_config_overrides
from . import metrics
from .runner import BOT_KINDS, GameRecord, run_pairs

RARITY_MARK = {"legendary": "\U0001F7E1", "rare": "\U0001F535", "common": "⚪"}  # yellow/blue/white


def _parse_bots(spec: str) -> tuple[str, str]:
    parts = spec.split(",")
    if len(parts) != 2 or any(p.strip().lower() not in BOT_KINDS for p in parts):
        raise SystemExit(f"--bots expects two of {'|'.join(BOT_KINDS)}, e.g. greedy,greedy")
    return parts[0].strip().lower(), parts[1].strip().lower()


def _resolve_deck(query: str, slugs: list[str]) -> str:
    """Resolve a (possibly abbreviated) --deck query to exactly one slug, e.g. "aggro" ->
    "aggro_hq_rush". Exact match wins outright; otherwise any slug containing the query."""
    query = query.strip().lower()
    if query in slugs:
        return query
    matches = sorted(s for s in slugs if query in s)
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise SystemExit(f"--deck {query!r} doesn't match any of: {', '.join(slugs)}")
    raise SystemExit(f"--deck {query!r} is ambiguous: matches {', '.join(matches)}")


def _card_line(row: dict, card: Card) -> str:
    wwd = f"{row['win_rate_when_drawn']:.1%}" if row["win_rate_when_drawn"] is not None else "n/a"
    imp = f"{row['impact']:+.1%}" if row["impact"] is not None else "n/a"
    tag = "/".join(sorted(card.tags)) or "-"
    info = f"{tag} · STR {card.base_strength} · {card.text or '(vanilla)'}"
    mark = RARITY_MARK[card.rarity]
    return f"{mark}  {row['card_id']:<16}{wwd:>9}{imp:>8}   {info}"


def format_matrix(records: Sequence[GameRecord]) -> str:
    """Deck-vs-deck win-rate matrix: row = deck_a, column = deck_b, cell = A's win rate.

    Columns are keyed by a 4-letter abbreviation (unique across the current deck slugs) so
    the table fits a terminal width; the legend below spells each one out.
    """
    m = metrics.matchup_matrix(records)
    decks = m["decks"]
    abbrevs = [d[:4] for d in decks]
    name_w = max(len(d) for d in decks)
    col_w = 7

    header = " " * (name_w + 1) + "".join(f"{ab:>{col_w}}" for ab in abbrevs)
    lines = ["\n### Matchup matrix (row = A, column = B, cell = A's win rate)", "```", header]
    for a in decks:
        cells = []
        for b in decks:
            rate = m["win_rate"][a][b]
            cells.append(f"{rate:>{col_w - 1}.0%} " if rate is not None else f"{'n/a':>{col_w - 1}} ")
        lines.append(f"{a:<{name_w}} " + "".join(cells))
    lines.append("")
    lines += [f"{ab} = {d}" for ab, d in zip(abbrevs, decks)]
    lines.append("```")
    return "\n".join(lines)


def format_focused_matrix(records: Sequence[GameRecord], deck: str) -> str:
    """`deck`'s win rate against every opponent (mirror included), split by which seat it
    played — a trimmed one-deck view instead of the full square grid."""
    m = metrics.matchup_matrix(records)
    opponents = [d for d in m["decks"] if d != deck]
    name_w = max((len(d) for d in opponents), default=len(deck)) + 9  # +len(" (mirror)")

    def _fmt(rate: Optional[float]) -> str:
        return f"{rate:>6.0%}" if rate is not None else f"{'n/a':>6}"

    lines = [f"\n### {deck} matchups (cell = {deck}'s win rate)", "```",
             f"{'opponent':<{name_w}} {'as A':>6} {'as B':>6}"]
    mirror = m["win_rate"][deck][deck]
    lines.append(f"{deck + ' (mirror)':<{name_w}} {_fmt(mirror)} {'':>6}")
    for opp in opponents:
        as_a = m["win_rate"][deck][opp]                                   # deck seat A, opp seat B
        opp_as_a = m["win_rate"][opp][deck]                                # opp seat A, deck seat B
        as_b = (1.0 - opp_as_a) if opp_as_a is not None else None
        lines.append(f"{opp:<{name_w}} {_fmt(as_a)} {_fmt(as_b)}")
    lines.append("```")
    return "\n".join(lines)


def format_report(records: Sequence[GameRecord], cards: dict[str, Card],
                  focus_deck: Optional[str] = None) -> str:
    """One impact-sorted card table per deck (or just `focus_deck`, if given), preceded by
    the matchup matrix (or a trimmed one-deck view of it), as a single string."""
    by_deck: dict[str, list[dict]] = defaultdict(list)
    for row in metrics.per_card_stats(records):     # already sorted by impact desc, overall
        by_deck[row["deck"]].append(row)             # per-deck order is preserved (stable sort)

    if focus_deck is not None:
        sections = [format_focused_matrix(records, focus_deck)]
        decks_to_print = [focus_deck] if focus_deck in by_deck else []
    else:
        sections = [format_matrix(records)]
        decks_to_print = sorted(by_deck)

    for deck in decks_to_print:
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
    p.add_argument("--bots", default="greedy,greedy",
                   help=f"two of {'|'.join(BOT_KINDS)} (referee is ~50-100x slower than "
                        "greedy: pair it with a low games count, e.g. 50)")
    p.add_argument("--jobs", type=int, default=os.cpu_count() or 1, help="worker processes")
    p.add_argument("--map", dest="map_id", default="map_a")
    p.add_argument("--config", default=None,
                   help="JSON file of Config field overrides (rule/balance dials); "
                        "'none' clears a wrapper-injected preset")
    p.add_argument("--deck", default=None,
                   help="only simulate/report this deck's matchups (abbreviation OK, e.g. "
                        "--deck aggro matches aggro_hq_rush) instead of the full round-robin")
    args = p.parse_args(argv)

    bots = _parse_bots(args.bots)
    config = load_config_overrides(args.config)
    slugs = sorted(DECK_SLUGS)

    target = _resolve_deck(args.deck, slugs) if args.deck is not None else None
    if target is not None:
        pairs = [(target, b) for b in slugs] + [(a, target) for a in slugs if a != target]
        label = f"{target}'s matchups ({len(pairs)})"
    else:
        pairs = [(a, b) for a in slugs for b in slugs]
        label = f"{len(slugs)}x{len(slugs)} round-robin"

    total_matchups = len(pairs)
    total_games = total_matchups * args.games
    print(f"Running {label}, {args.games} games/matchup "
          f"({total_games} games total, bots={bots[0]},{bots[1]}, jobs={args.jobs})...", file=sys.stderr)

    start = time.monotonic()

    def _progress(a: str, b: str, done: int, matchup_total: int) -> None:
        elapsed = time.monotonic() - start
        games_done = done * args.games
        print(f"  [{done:>2}/{matchup_total}] {elapsed:6.1f}s  {a} vs {b}  "
              f"({games_done}/{total_games} games)", file=sys.stderr)

    records = run_pairs(pairs, args.games, args.seed, bots=bots, config=config,
                        map_id=args.map_id, jobs=args.jobs, progress=_progress)
    print(f"Simulation done in {time.monotonic() - start:.1f}s.\n", file=sys.stderr)
    print(format_report(records, load_cards(), focus_deck=target))


if __name__ == "__main__":
    main(sys.argv[1:])
