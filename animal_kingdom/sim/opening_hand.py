"""Opening-hand impact: how many points a card in the opening hand moves its deck's win rate, as ExpertBot plays it.

A log names its decks, not their lists, and the seed deals from the list: so each logged game is rebuilt with the deck
lists of its day (the git history of cards.json, nearest the log's time first), and a list is accepted when both
players' first turns replay with it (every card placed was in the hand it deals). Only sides piloted by bots that kept
their hand count, and only games where nobody mulliganed: the hands are dealt at random, so the difference between
games with and without a card is the card's effect, not a choice. Per deck, impact = win rate with at least one copy in
the opening hand minus without, over the cards in today's list; a card in several decks gets the average, weighted by
hands. Each estimate is shrunk toward 0 by its own noise (prior spread PRIOR_SD points).

    .venv/bin/python -m animal_kingdom.sim.opening_hand            # rebuild data/learned/opening_hand.json
    .venv/bin/python -m animal_kingdom.sim.opening_hand --show     # and print the table per deck

The table is pilot-specific: GreedyBot's and ExpertBot's correlate about 0.2 card by card. It feeds the bots' mulligan
(bots/mulligan.py, off by default) and reads as a card signal: which cards a strong pilot wants to start with.
Two copies of one card (Prince Leo and Princess Lea) differ by up to ~7 points by noise alone at ~3,000 hands a deck.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

from ..bots.mulligan import TABLE
from ..decks import PREMADE_DECKS
from ..engine import rules
from ..engine.cards import COPY_LIMITS, NON_DECK_SLUGS
from ..engine.config import Config
from ..engine.state import new_game

LOG_GLOBS = ("results/logs/**/*.jsonl", "results/bot_quality/**/*.jsonl")
PILOTS = {"referee", "turn"}      # ExpertBot and TurnBot, which kept their hands in these logs
MIN_HANDS = 30                    # hands with and without the card, per deck
PRIOR_SD = 5.0                    # points: the spread of real impacts the shrinkage assumes
REPO = Path(__file__).resolve().parents[2]
CARDS = "animal_kingdom/data/cards.json"

_VERSIONS: list = []


def _lists(cards_json: dict) -> dict[str, list[str]]:
    """Deck slug -> 30 card ids, in the order decks.py builds them (the order the seed shuffles)."""
    decks: dict[str, list[str]] = {}
    for rec in cards_json.get("cards", []):
        if rec.get("deck") and rec["deck"] not in NON_DECK_SLUGS:
            decks.setdefault(rec["deck"], []).extend([rec["id"]] * (rec.get("copies") or COPY_LIMITS.get(rec.get("rarity"), 0)))
    return decks


def _load_versions() -> None:
    """Every committed cards.json's deck lists with its commit time, and today's."""
    out = []
    log = subprocess.run(["git", "-C", str(REPO), "log", "--format=%H %ct", "--", CARDS], capture_output=True, text=True).stdout
    for line in log.split("\n"):
        if line.strip():
            h, t = line.split()
            try:
                show = subprocess.run(["git", "-C", str(REPO), "show", f"{h}:{CARDS}"], capture_output=True, text=True).stdout
                out.append((int(t), _lists(json.loads(show))))
            except ValueError:
                pass
    out.append((10 ** 12, {k: list(v) for k, v in PREMADE_DECKS.items()}))
    _VERSIONS[:] = sorted(out, key=lambda v: v[0])


def _candidates(slug: str, t: float) -> list[list[str]]:
    """Distinct lists `slug` had, the ones in force before time `t` nearest first, then a few after."""
    if slug == "lions30":
        return [["lion"] * 30]
    before = [d for tv, d in reversed(_VERSIONS) if tv <= t][:15]
    after = [d for tv, d in _VERSIONS if tv > t][:3]
    seen, out = set(), []
    for decks in before + after:
        lst = decks.get(slug)
        if lst and tuple(lst) not in seen:
            seen.add(tuple(lst))
            out.append(lst)
    return out[:6]


def _first_turns(log: dict, da: list[str], db: list[str]):
    """Both opening hands if the game's first turns replay with these lists and nobody mulliganed, else None."""
    try:
        st = new_game(da, db, log["seed"], map_id="map_b", config=Config.default().for_log(log), first_player=log["first_player"])
        hands = {p: [u.card_id for u in st.hands[p]] for p in "AB"}
        for ad in log["actions"]:
            if st.turn_counter > 2 or st.result is not None:
                break
            if ad["kind"] == "choice" and st.pending and st.pending.get("kind") == "mulligan" and ad["choice"] != "__skip__":
                return None
            rules.apply_logged(st, ad)
        return hands if st.turn_counter > 2 or st.result is not None else None
    except Exception:
        return None


def opening_hands(path: str) -> list[dict]:
    """Each kept-hand side of each game in `path` whose deck exists today: deck, opening hand (today's cards), won."""
    t = os.path.getmtime(path)
    out = []
    for line in open(path):
        try:
            log = json.loads(line)
        except ValueError:
            continue
        bots = log.get("bots") or []
        slugs = (log.get("deck_a"), log.get("deck_b"))
        if "actions" not in log or log.get("map_id", "map_b") != "map_b" or not any(
                b in PILOTS and s in PREMADE_DECKS for b, s in zip(bots, slugs)):
            continue
        found = None
        for da in _candidates(slugs[0], t):
            for db in _candidates(slugs[1], t):
                if (hands := _first_turns(log, da, db)) is not None:
                    found = (hands, (da, db))
                    break
            if found:
                break
        if not found:
            continue
        hands, lists = found
        for p, bot, slug, lst in zip("AB", bots, slugs, lists):
            if bot in PILOTS and slug in PREMADE_DECKS:
                today = set(PREMADE_DECKS[slug])
                if slug == "aristocrats" and lst != PREMADE_DECKS[slug]:
                    continue        # the old Aristocrats was another deck under this slug
                out.append({"deck": slug, "hand": [c for c in hands[p] if c in today], "won": log["winner"] == p})
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
    # A mulligan test's candidate side is a mulliganing bot, whose kept hands were chosen.
    files = sorted({f for g in LOG_GLOBS for f in glob.glob(g, recursive=True)
                    if not ("mulligan" in f and "candidate" in os.path.basename(f))})
    rows = []
    with Pool(args.jobs, initializer=_load_versions) as pool:
        for rs in pool.imap_unordered(opening_hands, files):
            rows.extend(rs)
    table, per_deck = impact_table(rows)
    TABLE.write_text(json.dumps({"hands": len(rows), "impact": table}, indent=1) + "\n")
    print(f"{len(rows)} opening hands from {len(files)} logs -> {TABLE}")
    if args.show:
        for deck in sorted(per_deck):
            print(f"\n{deck} ({sum(r['deck'] == deck for r in rows)} hands)")
            for card, (raw, se, n) in sorted(per_deck[deck].items(), key=lambda kv: -kv[1][0]):
                print(f"  {card:22s} {raw:+6.1f} ±{1.96 * se:4.1f}  (in {n} hands)  -> {table[card]:+.1f}")


if __name__ == "__main__":
    main()
