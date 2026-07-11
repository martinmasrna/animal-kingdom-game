"""Run the card-power benchmark 'yardstick' rig vs the premade field and rank every card.

The rig is a 30-card, all-distinct 'singleton' deck of *basic* cards + minted calibration
bodies (vanilla ladder + free apex ladder + a bare draw-2). Every card is 1 copy, so all cards
share a draw rate and the per-card win-rate-when-drawn / impact form one unified ranking (no
within-rarity siloing needed). See docs/balance/benchmark-set-handoff.md.

Reading `impact`: win-rate-when-drawn minus the deck's overall win rate. A vanilla body sits at
the ~0 line; an effect well above it is carrying weight, one in the flat tail is 'just a body'.

Examples:
  # oracle read, dropping the two decks bots pilot worst, live progress:
  .venv/bin/python -m animal_kingdom.sim.benchmark_set --pilot referee --games 50
  # fast sanity pass over the full field:
  .venv/bin/python -m animal_kingdom.sim.benchmark_set --pilot turn --games 100 --exclude ""
  # save the final table:
  .venv/bin/python -m animal_kingdom.sim.benchmark_set --pilot referee --games 50 --out results/benchmark_set/referee.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Sequence

from ..engine.cards import DECK_SLUGS, load_cards
from .deck_optimizer import register_synthetic
from .runner import BOT_KINDS, run_pairs

# --- the yardstick rig: 30 distinct cards, 1 copy each (18 common / 8 rare / 4 legendary) ---
COMMONS = ["lion", "eagle", "bat", "squirrel", "mock_scout", "mock_saboteur",
           "african_wild_dog", "anaconda", "hedgehog", "elephant", "black_bear", "grizzly_bear",
           "mock_vanilla_5", "mock_vanilla_6", "mock_vanilla_8", "mock_vanilla_9",
           "mock_apex_5", "mock_apex_6"]
RARES = ["jerboa", "jaguar", "serval", "stoop", "porcupine", "polar_bear",
         "rhinoceros", "hippopotamus"]
LEGENDARIES = ["greywhisker", "mock_draw2", "borealis", "aquila"]
DECKLIST = COMMONS + RARES + LEGENDARIES
RARITY = {**{c: "C" for c in COMMONS}, **{c: "R" for c in RARES}, **{c: "L" for c in LEGENDARIES}}

# Calibration ladders (id lists, ascending strength) surfaced separately in the report.
VANILLA_LADDER = ["mock_vanilla_5", "mock_vanilla_6", "lion", "mock_vanilla_8", "mock_vanilla_9"]
APEX_FREE_LADDER = ["mock_apex_5", "mock_apex_6", "anaconda", "polar_bear"]
APEX_COST_LADDER = ["aquila", "borealis"]


def _kw(card) -> str:
    return (",".join(card.keywords)
            .replace("Apex Predator", "apex").replace("Immovable", "immov").replace("Flight", "fly"))


def main(argv: Sequence[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--pilot", default="referee", choices=BOT_KINDS,
                   help="bot kind for both seats (default: referee, the oracle)")
    p.add_argument("--games", type=int, default=50,
                   help="games/matchup PER MOVER (total per matchup = 2x this)")
    p.add_argument("--exclude", default="egg_control,colony_food_swarm",
                   help="comma-separated premade slugs to drop from the field (bots under-pilot "
                        "these two by default); pass '' to keep the full 7-deck field")
    p.add_argument("--field", default="",
                   help="explicit comma-separated field (overrides --exclude entirely)")
    p.add_argument("--base-seed", type=int, default=902000)
    p.add_argument("--jobs", type=int, default=8)
    p.add_argument("--out", type=Path, help="write the final per-card table as CSV")
    args = p.parse_args(argv)

    if args.field.strip():
        field = [s.strip() for s in args.field.split(",") if s.strip()]
    else:
        excluded = {s.strip() for s in args.exclude.split(",") if s.strip()}
        field = [s for s in sorted(DECK_SLUGS) if s not in excluded]
    bad = set(field) - DECK_SLUGS
    if bad:
        raise SystemExit(f"unknown field deck(s): {sorted(bad)}; valid: {sorted(DECK_SLUGS)}")

    register_synthetic("baseline", DECKLIST)
    cards = load_cards()
    total_games = 2 * args.games * len(field)
    print(f"benchmark rig (18C/8R/4L, all x1) vs {len(field)} decks: {', '.join(field)}", file=sys.stderr)
    print(f"pilot {args.pilot} | {2*args.games} games/matchup | {total_games} total"
          f"{' | referee is slow — start small and scale up' if args.pilot == 'referee' else ''}\n",
          file=sys.stderr)

    # --- live progress: a per-game counter within each matchup, a summary line per matchup ---
    def on_game(a, b, done, pair_games):
        print(f"\r  vs {b:<22} {done}/{pair_games} games", end="", file=sys.stderr, flush=True)

    def on_matchup(a, b, done, total, recs):
        wr = sum(1.0 if r.winner == "A" else (0.5 if r.winner is None else 0.0) for r in recs) / len(recs)
        print(f"\r  [{done}/{total}] vs {b:<22} {wr:6.1%}   ({len(recs)} games)", file=sys.stderr, flush=True)

    records = run_pairs([("baseline", f) for f in field], args.games, args.base_seed,
                        bots=(args.pilot, args.pilot), jobs=args.jobs,
                        game_progress=on_game, matchup_progress=on_matchup)

    # --- aggregate ---
    per = {f: [0.0, 0] for f in field}
    tot_c = tot_n = 0
    drawn = defaultdict(lambda: [0.0, 0])
    for r in records:
        cr = 1.0 if r.winner == "A" else (0.5 if r.winner is None else 0.0)
        c = per[r.deck_b]; c[0] += cr; c[1] += 1
        tot_c += cr; tot_n += 1
        for cid in r.cards_drawn_a:
            drawn[cid][0] += cr; drawn[cid][1] += 1
    deck_wr = tot_c / tot_n
    rates = {f: per[f][0] / per[f][1] for f in field}

    print(f"\nrig win rate vs field (pilot {args.pilot}):")
    for f, wr in sorted(rates.items(), key=lambda kv: kv[1]):
        print(f"  vs {f:<22} {wr:.1%}")
    print(f"  OVERALL {deck_wr:.1%} | worst {min(rates.values()):.1%} | best {max(rates.values()):.1%}")

    # --- unified per-card ranking ---
    table = []  # (rank fields) sorted by impact
    for cid in DECKLIST:
        w, n = drawn[cid]
        wwd = (w / n) if n else float("nan")
        table.append((cid, wwd, wwd - deck_wr, n))
    table.sort(key=lambda t: -t[1])

    print(f"\nUNIFIED per-card ranking (overall = {deck_wr:.1%}; all x1, equal draw rate):")
    print(f"  {'#':>2} {'card':<18}{'R':<2}{'STR':<4}{'kw':<12}{'impact':>8}{'wwd':>8}{'draw%':>7}")
    for i, (cid, wwd, impact, n) in enumerate(table, 1):
        c = cards[cid]
        print(f"  {i:>2} {c.name:<18}{RARITY[cid]:<2}{str(c.base_strength):<4}{_kw(c):<12}"
              f"{impact:+7.1%} {wwd:6.1%} {n/tot_n:6.0%}")

    imp = {cid: impact for cid, _, impact, _ in table}
    def ladder(label, ids):
        print(f"  {label:<16} " + "  ".join(f"STR{cards[i].base_strength}={imp[i]:+.1%}"
                                            for i in ids if i in imp))
    print("\nSTRENGTH LADDERS (impact by body size):")
    ladder("vanilla", VANILLA_LADDER)
    ladder("apex (free)", APEX_FREE_LADDER)
    ladder("apex (cost15)", APEX_COST_LADDER)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", newline="") as fh:
            wr = csv.writer(fh)
            wr.writerow(["rank", "card_id", "name", "rarity", "strength", "keywords",
                         "drawn_games", "draw_rate", "win_rate_when_drawn", "impact"])
            for i, (cid, wwd, impact, n) in enumerate(table, 1):
                c = cards[cid]
                wr.writerow([i, cid, c.name, RARITY[cid], c.base_strength, _kw(c),
                             n, round(n / tot_n, 4), round(wwd, 4), round(impact, 4)])
        print(f"\nwrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
