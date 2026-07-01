"""Aggregate `GameRecord`s into the handoff §10 balance metrics.

Pure standard library (csv / json) - producing the metrics needs no third-party deps. The
`pandas` extra is for *downstream* analysis of these CSV/JSON files, not for emitting them
(handoff §5). `write_all` drops a directory of machine-readable outputs plus a human summary.
"""

from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from functools import lru_cache
from typing import Iterable, Optional

from ..decks import load_premade_deck
from .runner import GameRecord

# Honest health warning carried into every results bundle (handoff §10).
GREEDY_CAVEAT = (
    "Balance conclusions are only as good as the bots. A 1-ply greedy bot underplays Combo "
    "(multi-turn payoffs) and sequencing chains (e.g. Wild Dogs / Domestic Cat). Treat these "
    "numbers as bot-limited; do not read them as final balance truth."
)


@lru_cache(maxsize=None)
def _deck_card_set(slug: str) -> frozenset[str]:
    return frozenset(load_premade_deck(slug))


def _winner_seat(rec: GameRecord, seat: str) -> Optional[bool]:
    """True if `seat` won, False if it lost, None on a draw (no result for that seat)."""
    if rec.winner is None:
        return None
    return rec.winner == seat


# --------------------------------------------------------------------- metrics

def matchup_matrix(records: Iterable[GameRecord]) -> dict:
    """Win rate from seat A's perspective for each (deck_a, deck_b) pairing.

    Returns {"decks": [...sorted slugs...], "win_rate": {a: {b: rate|None}}, "games": {...}}.
    A draw counts as half a win to each side so a mirror matchup centres on 0.5.
    """
    wins: dict[tuple[str, str], float] = defaultdict(float)
    games: dict[tuple[str, str], int] = defaultdict(int)
    decks: set[str] = set()
    for r in records:
        decks.add(r.deck_a)
        decks.add(r.deck_b)
        games[(r.deck_a, r.deck_b)] += 1
        if r.winner == "A":
            wins[(r.deck_a, r.deck_b)] += 1.0
        elif r.winner is None:
            wins[(r.deck_a, r.deck_b)] += 0.5

    order = sorted(decks)
    win_rate = {a: {b: (wins[(a, b)] / games[(a, b)] if games[(a, b)] else None)
                    for b in order} for a in order}
    game_counts = {a: {b: games[(a, b)] for b in order} for a in order}
    return {"decks": order, "win_rate": win_rate, "games": game_counts}


def win_condition_split(records: Iterable[GameRecord]) -> dict:
    """Counts and percentages of how games ended (hq_capture / food / exhaustion / max_turns)."""
    counts: dict[str, int] = defaultdict(int)
    total = 0
    for r in records:
        counts[r.reason] += 1
        total += 1
    pct = {k: (v / total if total else 0.0) for k, v in counts.items()}
    return {"total": total, "counts": dict(counts), "percent": pct}


def first_player_win_rate(records: Iterable[GameRecord]) -> dict:
    """Fraction of decided games won by the first player (target ~0.50, maps.md §5)."""
    decided = first_wins = 0
    for r in records:
        if r.winner is None:
            continue
        decided += 1
        if r.winner == r.first_player:
            first_wins += 1
    return {"decided_games": decided,
            "first_player_wins": first_wins,
            "rate": (first_wins / decided if decided else None)}


def avg_game_length(records: Iterable[GameRecord]) -> dict:
    """Mean game length in turns, overall and per ordered matchup."""
    records = list(records)
    by_pair_total: dict[tuple[str, str], int] = defaultdict(int)
    by_pair_n: dict[tuple[str, str], int] = defaultdict(int)
    total = 0
    for r in records:
        total += r.turns
        by_pair_total[(r.deck_a, r.deck_b)] += r.turns
        by_pair_n[(r.deck_a, r.deck_b)] += 1
    per_matchup = {f"{a}_vs_{b}": by_pair_total[(a, b)] / by_pair_n[(a, b)]
                   for (a, b) in by_pair_total}
    return {"overall": (total / len(records) if records else None),
            "per_matchup": per_matchup}


def per_card_winrate_delta(records: Iterable[GameRecord]) -> list[dict]:
    """For each card, its win rate across the games whose seat-deck contained it.

    `delta` = win_rate - 0.5 (presence-in-wins vs losses against an even baseline). Sorted
    most-winning first. Draws count as half a win on each side they appear.
    """
    wins: dict[str, float] = defaultdict(float)
    appearances: dict[str, int] = defaultdict(int)
    for r in records:
        for seat, slug in (("A", r.deck_a), ("B", r.deck_b)):
            res = _winner_seat(r, seat)
            credit = 0.5 if res is None else (1.0 if res else 0.0)
            for card_id in _deck_card_set(slug):
                appearances[card_id] += 1
                wins[card_id] += credit

    rows = []
    for card_id in sorted(appearances):
        n = appearances[card_id]
        rate = wins[card_id] / n
        rows.append({"card_id": card_id, "games": n,
                     "win_rate": round(rate, 4), "delta": round(rate - 0.5, 4)})
    rows.sort(key=lambda d: d["win_rate"], reverse=True)
    return rows


# ---------------------------------------------------------------------- output

def _write_matchup_csv(path: str, matrix: dict) -> None:
    decks = matrix["decks"]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["deck_a \\ deck_b", *decks])
        for a in decks:
            row = [a]
            for b in decks:
                rate = matrix["win_rate"][a][b]
                row.append("" if rate is None else f"{rate:.4f}")
            w.writerow(row)


def _write_per_card_csv(path: str, rows: list[dict]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["card_id", "games", "win_rate", "delta"])
        w.writeheader()
        w.writerows(rows)


def write_all(records: Iterable[GameRecord], out_dir: str) -> dict:
    """Compute every metric and write the results bundle to `out_dir`. Returns the summary."""
    records = list(records)
    os.makedirs(out_dir, exist_ok=True)

    matrix = matchup_matrix(records)
    per_card = per_card_winrate_delta(records)
    summary = {
        "games": len(records),
        "win_condition_split": win_condition_split(records),
        "first_player_win_rate": first_player_win_rate(records),
        "avg_game_length": avg_game_length(records),
        "matchup_decks": matrix["decks"],
        "caveat": GREEDY_CAVEAT,
    }

    _write_matchup_csv(os.path.join(out_dir, "matchup_matrix.csv"), matrix)
    _write_per_card_csv(os.path.join(out_dir, "per_card_winrate.csv"), per_card)
    with open(os.path.join(out_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    return summary
