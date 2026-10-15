"""Opening-hand impact: how many points a card in the opening hand moves its deck's win rate.

Replays every logged sim game on today's deck lists (a log names its decks, not their lists, so a game that no longer
replays to its recorded winner is from an older list and is dropped) and keeps each side GreedyBot piloted: GreedyBot
never mulligans, so its opening hands are dealt at random and the difference between games with and without a card is
the card's effect, not a choice. Per deck, impact = win rate with at least one copy in the opening hand minus without;
a card in several decks gets the average, weighted by hands. Each estimate is shrunk toward 0 by its own noise
(prior spread PRIOR_SD points), so a card with little data barely moves the mulligan.

    .venv/bin/python -m animal_kingdom.sim.opening_hand            # rebuild data/learned/opening_hand.json
    .venv/bin/python -m animal_kingdom.sim.opening_hand --show     # and print the table per deck

The table measures what GreedyBot does with a card, not the card's worth to a strong player; it is the mulligan's prior.
"""

from __future__ import annotations

import argparse
import glob
import json
from collections import defaultdict
from multiprocessing import Pool

from ..bots.mulligan import TABLE
from ..decks import load_premade_deck
from ..engine import rules
from ..engine.config import Config
from ..engine.state import new_game

LOG_GLOBS = ("results/logs/**/*.jsonl", "results/bot_quality/**/*.jsonl")
PILOTS = {"greedy"}      # bots whose opening hands are dealt at random and kept
MIN_HANDS = 30           # hands with and without the card, per deck
PRIOR_SD = 5.0           # points: the spread of real impacts the shrinkage assumes

_DECKS: dict = {}


def _deck(slug):
    if slug not in _DECKS:
        try:
            _DECKS[slug] = load_premade_deck(slug)
        except Exception:
            _DECKS[slug] = None
    return _DECKS[slug]


def opening_hands(path: str) -> list[dict]:
    """Each GreedyBot side of each game in `path` that still replays on today's lists: deck, opening hand, won."""
    out = []
    for line in open(path):
        try:
            log = json.loads(line)
        except ValueError:
            continue
        bots = log.get("bots") or []
        if "actions" not in log or log.get("map_id", "map_b") != "map_b" or not any(b in PILOTS for b in bots):
            continue
        da, db = _deck(log.get("deck_a")), _deck(log.get("deck_b"))
        if da is None or db is None:
            continue
        try:
            st = new_game(da, db, log["seed"], map_id="map_b", config=Config.default().for_log(log),
                          first_player=log["first_player"])
            hands = {p: [u.card_id for u in st.hands[p]] for p in "AB"}
            for ad in log["actions"]:
                if ad["kind"] == "choice" and st.pending and st.pending.get("kind") == "mulligan" and ad["choice"] != "__skip__":
                    raise ValueError("a mulligan: the hand was chosen")
                rules.apply_logged(st, ad)
            if st.result is None or st.result.winner != log["winner"]:
                continue
        except Exception:
            continue
        for p, bot in zip("AB", bots):
            if bot in PILOTS:
                out.append({"deck": log["deck_" + p.lower()], "hand": hands[p], "won": log["winner"] == p})
    return out


def impact_table(rows: list[dict]) -> tuple[dict, dict]:
    """(card -> shrunk impact in points, deck -> card -> (raw impact, standard error, hands))."""
    by_deck = defaultdict(list)
    for r in rows:
        by_deck[r["deck"]].append(r)
    per_deck, pooled = {}, defaultdict(list)
    for deck, rs in by_deck.items():
        for card in {c for r in rs for c in r["hand"]}:
            w = [r["won"] for r in rs if card in r["hand"]]
            wo = [r["won"] for r in rs if card not in r["hand"]]
            if len(w) < MIN_HANDS or len(wo) < MIN_HANDS:
                continue
            p1, p0 = sum(w) / len(w), sum(wo) / len(wo)
            se = 100 * ((p1 * (1 - p1) / len(w) + p0 * (1 - p0) / len(wo)) ** 0.5)
            per_deck.setdefault(deck, {})[card] = (100 * (p1 - p0), se, len(w))
            pooled[card].append((100 * (p1 - p0), se, len(w)))
    table = {}
    for card, ests in pooled.items():
        n = sum(e[2] for e in ests)
        raw = sum(e[0] * e[2] for e in ests) / n
        se = (sum((e[1] * e[2]) ** 2 for e in ests)) ** 0.5 / n
        table[card] = round(raw * PRIOR_SD ** 2 / (PRIOR_SD ** 2 + se ** 2), 2)
    return dict(sorted(table.items())), per_deck


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--show", action="store_true", help="print the table per deck")
    args = ap.parse_args(argv)
    files = sorted({f for g in LOG_GLOBS for f in glob.glob(g, recursive=True)})
    rows = []
    with Pool(args.jobs) as pool:
        for rs in pool.imap_unordered(opening_hands, files):
            rows.extend(rs)
    table, per_deck = impact_table(rows)
    TABLE.write_text(json.dumps({"hands": len(rows), "impact": table}, indent=1) + "\n")
    print(f"{len(rows)} opening hands from {len(files)} logs -> {TABLE}")
    if args.show:
        for deck in sorted(per_deck):
            print(f"\n{deck}")
            for card, (raw, se, n) in sorted(per_deck[deck].items(), key=lambda kv: -kv[1][0]):
                print(f"  {card:22s} {raw:+6.1f} ±{1.96 * se:4.1f}  (in {n} hands)  -> {table[card]:+.1f}")


if __name__ == "__main__":
    main()
