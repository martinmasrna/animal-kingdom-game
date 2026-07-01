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

DRAWN_CAVEAT = (
    "\"Drawn\" is presence-only (was the card in hand at any point), not exact copy counts. "
    "A card returned to hand by an effect (e.g. a bounce) counts as drawn again, which can "
    "inflate draw_rate/impact slightly for bounce-heavy decks."
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


def _deck_win_rates(records: Iterable[GameRecord]) -> dict[str, float]:
    """Each deck's win fraction across its non-mirror games, regardless of seat.

    Mirror (deck vs itself) games are excluded: a deck can't be more or less powerful than
    itself, so by construction they center on ~50% regardless of true field strength. Folding
    them in just dilutes this baseline (and per_card_stats' `impact`, which subtracts it)
    toward 50% for every deck. `matchup_matrix` still includes mirrors - they're cheap and are
    the cleanest read on pure first-player/turn-order advantage - this exclusion is only for
    the "how strong is this deck against the field" baseline.
    """
    wins: dict[str, float] = defaultdict(float)
    games: dict[str, int] = defaultdict(int)
    for r in records:
        if r.deck_a == r.deck_b:
            continue
        for seat, slug in (("A", r.deck_a), ("B", r.deck_b)):
            res = _winner_seat(r, seat)
            games[slug] += 1
            wins[slug] += 0.5 if res is None else (1.0 if res else 0.0)
    return {slug: wins[slug] / games[slug] for slug in games}


def per_card_stats(records: Iterable[GameRecord]) -> list[dict]:
    """Real per-card signal: how often a card was drawn, and how games went when it was.

    `draw_rate` = fraction of the card's deck's games in which it was drawn at least once
    (presence-only, see DRAWN_CAVEAT). `win_rate_when_drawn` is the win rate restricted to
    those games (`None` if the card was never drawn in the sample). `impact` is
    `win_rate_when_drawn` minus the deck's overall `deck_win_rate` - positive means the deck
    does better than its average when this card shows up. Sorted by impact, best first,
    with never-drawn cards (impact `None`) last.

    Mirror (deck vs itself) games are excluded throughout, matching `_deck_win_rates` - see
    its docstring. A card's `impact` is only meaningful relative to a field baseline.
    """
    records = list(records)
    deck_win_rate = _deck_win_rates(records)

    games_with_card: dict[str, int] = defaultdict(int)
    draws: dict[str, int] = defaultdict(int)
    wins_when_drawn: dict[str, float] = defaultdict(float)
    card_deck: dict[str, str] = {}

    for r in records:
        if r.deck_a == r.deck_b:
            continue
        for seat, slug, seat_drawn in (("A", r.deck_a, r.cards_drawn_a),
                                       ("B", r.deck_b, r.cards_drawn_b)):
            res = _winner_seat(r, seat)
            credit = 0.5 if res is None else (1.0 if res else 0.0)
            for card_id in _deck_card_set(slug):
                games_with_card[card_id] += 1
                card_deck[card_id] = slug
            for card_id in seat_drawn:
                draws[card_id] += 1
                wins_when_drawn[card_id] += credit

    rows = []
    for card_id in sorted(games_with_card):
        n = games_with_card[card_id]
        d = draws[card_id]
        wwd = (wins_when_drawn[card_id] / d) if d else None
        dwr = deck_win_rate.get(card_deck[card_id])
        impact = wwd - dwr if (wwd is not None and dwr is not None) else None
        rows.append({
            "card_id": card_id,
            "deck": card_deck[card_id],
            "games": n,
            "draw_rate": round(d / n, 4) if n else 0.0,
            "win_rate_when_drawn": round(wwd, 4) if wwd is not None else None,
            "deck_win_rate": round(dwr, 4) if dwr is not None else None,
            "impact": round(impact, 4) if impact is not None else None,
        })
    rows.sort(key=lambda r: (r["impact"] is None, -(r["impact"] or 0.0)))
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


_PER_CARD_FIELDS = ["card_id", "deck", "games", "draw_rate", "win_rate_when_drawn",
                    "deck_win_rate", "impact"]


def _write_per_card_csv(path: str, rows: list[dict]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_PER_CARD_FIELDS)
        w.writeheader()
        for row in rows:
            w.writerow({k: ("" if v is None else v) for k, v in row.items()})


def write_all(records: Iterable[GameRecord], out_dir: str) -> dict:
    """Compute every metric and write the results bundle to `out_dir`. Returns the summary."""
    records = list(records)
    os.makedirs(out_dir, exist_ok=True)

    matrix = matchup_matrix(records)
    per_card = per_card_stats(records)
    summary = {
        "games": len(records),
        "win_condition_split": win_condition_split(records),
        "first_player_win_rate": first_player_win_rate(records),
        "avg_game_length": avg_game_length(records),
        "matchup_decks": matrix["decks"],
        "caveat": GREEDY_CAVEAT + "\n\n" + DRAWN_CAVEAT,
    }

    _write_matchup_csv(os.path.join(out_dir, "matchup_matrix.csv"), matrix)
    _write_per_card_csv(os.path.join(out_dir, "per_card_stats.csv"), per_card)
    with open(os.path.join(out_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    return summary
