"""Unified balance simulation CLI: human-readable reports and machine-readable artifacts.

The default prints human-readable per-deck card tables sorted by `impact`
(win_rate_when_drawn minus the deck's own baseline win rate). ``--format files`` writes
the raw CSV/JSON metrics bundle instead; ``--format both`` does both from the same run.

Examples:
  ./report 500
  ./report 200 --bots random,random --jobs 4
  ./report 500 --format both --out results/baseline
  ./report 500 --deck aggro
  ./report 500 --deck egg --opponent cat
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
from .runner import BOT_KINDS, GameRecord, parse_bot_pair, run_pairs

RARITY_MARK = {"legendary": "\U0001F7E1", "rare": "\U0001F535", "common": "⚪"}  # yellow/blue/white


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

    Rows/columns are ordered by each deck's combined (both-seats) win rate, strongest first,
    so the table itself reads as a ranking. Columns are keyed by a 4-letter abbreviation
    (unique across the current deck slugs) so the table fits a terminal width. Trailing "TotA"
    column = that row-deck's average win rate playing as seat A across its non-mirror matchups;
    trailing "TotB" row = that column-deck's average win rate playing as seat B; "Both" column
    = the same deck's combined (both-seats) average win rate, i.e. (TotA + TotB) / 2 for that
    deck. The mirror matchup is still shown on the diagonal but excluded from these three
    aggregates - same convention as `metrics._deck_win_rates` (a deck can't be more or less
    powerful than itself, so folding the mirror in just dilutes the "vs the field" read toward
    50%), which keeps these numbers consistent with each per-deck section's "deck win rate".
    """
    m = metrics.matchup_matrix(records)
    all_decks = m["decks"]
    col_w = 7

    def _avg(vals: list[float]) -> Optional[float]:
        return sum(vals) / len(vals) if vals else None

    as_a = {a: _avg([m["win_rate"][a][b] for b in all_decks
                    if b != a and m["win_rate"][a][b] is not None])
            for a in all_decks}
    as_b = {b: _avg([1.0 - m["win_rate"][a][b] for a in all_decks
                    if a != b and m["win_rate"][a][b] is not None])
            for b in all_decks}
    combined = {d: _avg([v for v in (as_a[d], as_b[d]) if v is not None]) for d in all_decks}

    decks = sorted(all_decks, key=lambda d: (combined[d] is None, -(combined[d] or 0.0)))
    abbrevs = [d[:4] for d in decks]
    name_w = max(len(d) for d in decks)

    def _cell(rate: Optional[float]) -> str:
        return f"{rate:>{col_w - 1}.0%} " if rate is not None else f"{'n/a':>{col_w - 1}} "

    header = (" " * (name_w + 1) + "".join(f"{ab:>{col_w}}" for ab in abbrevs)
              + f"{'TotA':>{col_w}}{'Both':>{col_w}}")
    lines = ["\n### Matchup matrix (row = A, column = B, cell = A's win rate)", "```", header]
    for a in decks:
        cells = [_cell(m["win_rate"][a][b]) for b in decks]
        cells.append(_cell(as_a[a]))
        cells.append(_cell(combined[a]))
        lines.append(f"{a:<{name_w}} " + "".join(cells))
    tot_b_cells = [_cell(as_b[b]) for b in decks] + [_cell(None), _cell(None)]
    lines.append(f"{'TotB':<{name_w}} " + "".join(tot_b_cells))
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
    the matchup matrix (or a trimmed one-deck view of it), as a single string. Deck sections
    are ordered by that deck's own win rate, strongest first."""
    by_deck: dict[str, list[dict]] = defaultdict(list)
    for row in metrics.per_card_stats(records):     # already sorted by impact desc, overall
        by_deck[row["deck"]].append(row)             # per-deck order is preserved (stable sort)

    if focus_deck is not None:
        sections = [format_focused_matrix(records, focus_deck)]
        decks_to_print = [focus_deck] if focus_deck in by_deck else []
    else:
        sections = [format_matrix(records)]
        decks_to_print = sorted(by_deck, key=lambda d: -by_deck[d][0]["deck_win_rate"])

    for deck in decks_to_print:
        deck_rows = by_deck[deck]
        baseline = deck_rows[0]["deck_win_rate"]
        lines = [f"\n### {deck} (deck win rate {baseline:.1%})", "```",
                f"   {'card':<16}{'WR_drawn':>9}{'impact':>8}   tag / str / text"]
        lines += [_card_line(row, cards[row["card_id"]]) for row in deck_rows]
        lines.append("```")
        sections.append("\n".join(lines))
    return "\n".join(sections)


def _print_metrics_summary(summary: dict, out_dir: str, *, file) -> None:
    print(f"\nWrote {summary['games']} games to {out_dir}/ "
          "(matchup_matrix.csv, per_card_stats.csv, summary.json)", file=file)
    split = summary["win_condition_split"]["percent"]
    print("Win conditions: "
          + ", ".join(f"{key}={value:.1%}" for key, value in sorted(split.items())),
          file=file)
    first_player = summary["first_player_win_rate"]["rate"]
    print(f"First-player win rate: {first_player:.1%}" if first_player is not None
          else "First-player win rate: n/a", file=file)
    print(f"Avg game length: {summary['avg_game_length']['overall']:.1f} turns", file=file)
    print(f"\nCaveat: {summary['caveat']}", file=file)


def _crossed_progress_decile(done: int, total: int) -> bool:
    """Return whether completing game ``done`` crossed the next 10% matchup milestone."""
    return total > 0 and (done * 10) // total > ((done - 1) * 10) // total


def main(
    argv: Sequence[str] | None = None,
    *,
    default_format: str = "report",
) -> None:
    p = argparse.ArgumentParser(
        description="Run balance simulations and print a report, write metrics files, or both.")
    p.add_argument("games", nargs="?", type=int,
                   help="games per matchup (e.g. './report 200')")
    p.add_argument("--games", dest="games_option", type=int,
                   help="games per matchup (compatibility form)")
    p.add_argument("--seed", type=int, default=0, help="base seed (games use seed, seed+1, ...)")
    p.add_argument("--bots", default="greedy,greedy",
                   help=f"two of {'|'.join(BOT_KINDS)} (referee is ~50-100x slower than "
                        "greedy: pair it with a low games count, e.g. 50)")
    p.add_argument("--jobs", type=int, default=os.cpu_count() or 1, help="worker processes")
    p.add_argument("--map", dest="map_id", default="map_b")
    p.add_argument("--config", default=None,
                   help="JSON file of Config field overrides (rule/balance dials); "
                        "'none' clears a wrapper-injected preset")
    p.add_argument("--deck", default=None,
                   help="only simulate/report this deck's matchups (abbreviation OK, e.g. "
                        "--deck aggro matches aggro_hq_rush) instead of the full round-robin")
    p.add_argument("--opponent", default=None,
                   help="pair with --deck to simulate/report only that single matchup "
                        "(abbreviation OK, both seats; same deck = mirror only)")
    p.add_argument("--decks", default=None,
                   help="compatibility form: 'all' or one ordered comma-separated pair")
    p.add_argument("--format", dest="output_format",
                   choices=("report", "files", "both"), default=default_format,
                   help=f"output mode (default: {default_format})")
    p.add_argument("--out", default="results",
                   help="metrics output directory for --format files/both")
    p.add_argument("--log", default=None,
                   help="also write a per-game action log (JSONL) to this path, for later "
                        "move-by-move replay via `python -m animal_kingdom.sim.replay`")
    args = p.parse_args(argv)

    if args.games is not None and args.games_option is not None:
        p.error("pass games either positionally or with --games, not both")
    games = args.games if args.games is not None else args.games_option
    if games is None:
        p.error("games per matchup is required (e.g. './report 200')")
    if games <= 0:
        p.error("games per matchup must be positive")
    args.games = games

    bots = parse_bot_pair(args.bots)
    config = load_config_overrides(args.config)
    slugs = sorted(DECK_SLUGS)

    if args.decks is not None and (args.deck is not None or args.opponent is not None):
        p.error("--decks cannot be combined with --deck or --opponent")
    if args.opponent is not None and args.deck is None:
        p.error("--opponent requires --deck (it narrows that deck's matchups to one)")

    target = _resolve_deck(args.deck, slugs) if args.deck is not None else None
    opponent = _resolve_deck(args.opponent, slugs) if args.opponent is not None else None
    if args.decks is not None and args.decks.strip() != "all":
        pair = [part.strip() for part in args.decks.split(",")]
        if len(pair) != 2:
            p.error("--decks expects 'all' or two comma-separated deck names")
        a, b = (_resolve_deck(part, slugs) for part in pair)
        pairs = [(a, b)]
        label = f"{a} vs {b} (ordered seats)"
    elif opponent is not None:
        pairs = [(target, opponent)] if target == opponent else [(target, opponent), (opponent, target)]
        label = f"{target} vs {opponent} ({len(pairs)} seat{'' if len(pairs) == 1 else 's'})"
    elif target is not None:
        pairs = [(target, b) for b in slugs] + [(a, target) for a in slugs if a != target]
        label = f"{target}'s matchups ({len(pairs)})"
    else:
        pairs = [(a, b) for a in slugs for b in slugs]
        label = f"{len(slugs)}x{len(slugs)} round-robin"

    total_matchups = len(pairs)
    total_games = total_matchups * args.games
    print(f"Running {label}, {args.games} games/matchup "
          f"({total_games} games total, bots={bots[0]},{bots[1]}, jobs={args.jobs})...",
          file=sys.stderr, flush=True)

    start = time.monotonic()

    matchups_done = 0

    def _matchup_progress(
        a: str,
        b: str,
        done: int,
        matchup_total: int,
        batch: list[GameRecord],
    ) -> None:
        nonlocal matchups_done
        matchups_done = done
        elapsed = time.monotonic() - start
        games_done = done * args.games
        total = len(batch)
        draws = sum(record.winner is None for record in batch)
        draw_rate = draws / total if total else 0.0
        a_rate = (
            (sum(record.winner == "A" for record in batch) + draws / 2) / total
            if total else 0.0
        )
        b_rate = 1.0 - a_rate if total else 0.0
        print(f"\n  === MATCHUP {done}/{matchup_total} COMPLETE === {a} vs {b} | "
              f"WR A={a_rate:.1%}, B={b_rate:.1%}, draws={draw_rate:.1%} | "
              f"{games_done}/{total_games} total games | {elapsed:.1f}s\n",
              file=sys.stderr, flush=True)

    def _game_progress(a: str, b: str, done: int, matchup_games: int) -> None:
        if not _crossed_progress_decile(done, matchup_games):
            return
        elapsed = time.monotonic() - start
        games_done = matchups_done * args.games + done
        matchup_percent = done / matchup_games
        print(f"      [{matchup_percent:>4.0%}] {a} vs {b} | "
              f"{done}/{matchup_games} games | {games_done}/{total_games} total | "
              f"{elapsed:.1f}s",
              file=sys.stderr, flush=True)

    records = run_pairs(pairs, args.games, args.seed, bots=bots, config=config,
                        map_id=args.map_id, jobs=args.jobs, log_actions=bool(args.log),
                        game_progress=_game_progress,
                        matchup_progress=_matchup_progress)
    print(f"Simulation done in {time.monotonic() - start:.1f}s.\n",
          file=sys.stderr, flush=True)

    if args.log:
        from .replay import write_game_logs
        n = write_game_logs(records, args.log, map_id=args.map_id, bots=bots)
        print(f"Wrote {n} game action-logs to {args.log}", file=sys.stderr, flush=True)

    if args.output_format in ("files", "both"):
        summary = metrics.write_all(records, args.out)
        summary_stream = sys.stdout if args.output_format == "files" else sys.stderr
        _print_metrics_summary(summary, args.out, file=summary_stream)
    if args.output_format in ("report", "both"):
        print(format_report(records, load_cards(), focus_deck=target))


if __name__ == "__main__":
    main(sys.argv[1:])
