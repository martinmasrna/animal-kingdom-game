"""Run the card-power benchmark 'yardstick' rig vs the premade field and rank every card.

The rig is a 30-card, all-distinct 'singleton' deck of *basic* cards + minted calibration
bodies (vanilla ladder + free apex ladder + a bare draw-2). Every card is 1 copy, so all cards
share a draw rate and the per-card win-rate-when-drawn / impact form one unified ranking (no
within-rarity siloing needed). See docs/balance/benchmark-set-handoff.md.

Reading `impact`: win-rate-when-drawn minus the deck's overall win rate. A vanilla body sits at
the ~0 line; an effect well above it is carrying weight, one in the flat tail is 'just a body'.

Every game scores BOTH seats: one pass yields the rig's own per-card ranking *and* each field
deck's per-card ranking vs the rig. The games are the expensive part (referee search); folding
the second seat is free, so `--report` only picks which tables get printed, never what gets run.

Crash-safe for long referee runs: after each matchup the accumulated tallies are written to a
checkpoint file; re-running the SAME command auto-resumes, skipping matchups already done.

Examples:
  # oracle read, dropping the two decks bots pilot worst, live progress + auto-resume:
  .venv/bin/python -m animal_kingdom.sim.benchmark_set --pilot referee --games 500 --out results/benchmark_set/referee.csv
  # fast sanity pass over the full field:
  .venv/bin/python -m animal_kingdom.sim.benchmark_set --pilot turn --games 100 --exclude ""
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Sequence

from ..engine.cards import DECK_SLUGS, load_cards
from ..engine.config import load_config_overrides
from .deck_optimizer import register_synthetic
from .runner import BOT_KINDS, run_pairs

# --- the yardstick rig: 30 distinct cards, 1 copy each (18 common / 8 rare / 4 legendary) ---
# Every card is self-sufficient: it functions with no synergy/tribal/food-state condition (cost-
# gated and delayed cards were cut). Legendaries are basic primitives at top dosage. See
# docs/balance/baseline-deck-arc.md.
COMMONS = ["lion", "eagle", "bat", "squirrel", "mock_scout", "mock_saboteur",
           "african_wild_dog", "anaconda", "gray_wolf", "mock_immovable_6", "black_bear",
           "grizzly_bear", "mock_vanilla_5", "mock_vanilla_6", "mock_vanilla_8", "mock_vanilla_9",
           "mock_apex_5", "mock_apex_6"]
RARES = ["jerboa", "jaguar", "serval", "stoop", "porcupine", "polar_bear",
         "rhinoceros", "mock_draw2"]
LEGENDARIES = ["greywhisker", "mock_removal", "mock_vanilla_10", "mock_flyer_7"]
DECKLIST = COMMONS + RARES + LEGENDARIES
RARITY = {**{c: "C" for c in COMMONS}, **{c: "R" for c in RARES}, **{c: "L" for c in LEGENDARIES}}

# Calibration ladders (id lists, ascending strength) surfaced separately in the report.
VANILLA_LADDER = ["mock_vanilla_5", "mock_vanilla_6", "lion", "mock_vanilla_8", "mock_vanilla_9",
                  "mock_vanilla_10"]
APEX_FREE_LADDER = ["mock_apex_5", "mock_apex_6", "anaconda", "polar_bear"]


# Checkpoint schema. v1 stored a single seat's tallies (whichever --measure picked) and is
# unreadable here: the other seat's games were never written down.
CKPT_VERSION = 2


def _kw(card) -> str:
    return (",".join(card.keywords)
            .replace("Apex Predator", "apex").replace("Immovable", "immov").replace("Flight", "fly"))


def _fold(records) -> dict:
    """Reduce one matchup's game records to the additive tallies the report needs, BOTH seats.

    In `run_pairs([("baseline", f)], ...)` the baseline is always seat A and the field deck always
    seat B (the mover split uses first_player, not a seat swap), so seat "A" reads the rig's own
    per-card impact and seat "B" reads the synergy deck's, off the very same games. Returns
    {"A": tallies, "B": tallies}; each seat's tallies are {n, credit, cards: cid -> [credit, n]}."""
    out = {}
    for seat, drawn_attr in (("A", "cards_drawn_a"), ("B", "cards_drawn_b")):
        n = 0
        credit = 0.0
        cards: dict[str, list] = defaultdict(lambda: [0.0, 0])  # cid -> [win-credit-when-drawn, drawn]
        for r in records:
            cr = r.credit(seat)
            n += 1
            credit += cr
            for cid in getattr(r, drawn_attr):
                cards[cid][0] += cr
                cards[cid][1] += 1
        out[seat] = {"n": n, "credit": credit, "cards": {k: v for k, v in cards.items()}}
    return out


def _write_json_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data))
    os.replace(tmp, path)  # atomic: a crash mid-write can't corrupt the checkpoint


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
    # Re-rolled 2026-07-15 for the fresh both-seats run (was 902000). Pass the old value
    # explicitly to reproduce any pre-2026-07-15 result.
    p.add_argument("--base-seed", type=int, default=715000)
    p.add_argument("--jobs", type=int, default=os.cpu_count() or 1, help="worker processes")
    p.add_argument("--out", type=Path, help="write the final per-card table as CSV")
    p.add_argument("--config", default=None,
                   help="JSON of Config overrides (e.g. a rules variant like draw_action_count=2)")
    p.add_argument("--checkpoint", type=Path,
                   help="checkpoint file for crash-safe resume "
                        "(default: results/benchmark_set/<pilot>_g<games>[_<config>].ckpt.json)")
    p.add_argument("--report", choices=("self", "opponent", "both"), default="both",
                   help="which per-card tables to PRINT (both are always measured): 'self' = the "
                        "baseline rig's own cards, 'opponent' = each field deck's cards vs the "
                        "baseline, 'both' (default). Never affects what gets simulated.")
    args = p.parse_args(argv)

    config = load_config_overrides(args.config)

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

    cfg_tag = f"_{Path(args.config).stem}" if args.config else ""
    ckpt_path = args.checkpoint or Path(
        f"results/benchmark_set/{args.pilot}_g{args.games}{cfg_tag}.ckpt.json")
    # This run's identity — a resumed checkpoint must match all of it, else the samples don't
    # compose. (`--report` is absent by design: it picks output, not what's simulated.)
    run_key = {"pilot": args.pilot, "games": args.games, "base_seed": args.base_seed,
               "field": sorted(field), "deck": DECKLIST, "config": str(args.config)}

    matchups: dict[str, dict] = {}
    if ckpt_path.exists():
        saved = json.loads(ckpt_path.read_text())
        if saved.get("version") != CKPT_VERSION:
            raise SystemExit(
                f"checkpoint {ckpt_path} is v{saved.get('version', 1)} (one seat only); this rig "
                f"writes v{CKPT_VERSION} (both seats). The unrecorded seat can't be recovered: "
                f"delete it or pass a fresh --checkpoint and re-run.")
        if saved.get("run_key") != run_key:
            raise SystemExit(
                f"checkpoint {ckpt_path} is from a different run (pilot/games/seed/field/deck).\n"
                f"Delete it or pass a fresh --checkpoint to start over.")
        matchups = saved.get("matchups", {})
        # normalize card lists back to [float, int]
        for m in matchups.values():
            for seat in ("A", "B"):
                m[seat]["cards"] = {k: [float(v[0]), int(v[1])] for k, v in m[seat]["cards"].items()}
        if matchups:
            print(f"resuming from {ckpt_path}: {len(matchups)}/{len(field)} matchups already done "
                  f"({', '.join(sorted(matchups))})", file=sys.stderr)

    todo = [f for f in field if f not in matchups]
    print(f"benchmark rig (18C/8R/4L, all x1) vs {len(field)} decks | pilot {args.pilot} | "
          f"{2*args.games} games/matchup | {len(todo)} matchups to run"
          f"{' | referee is slow' if args.pilot == 'referee' else ''}\n", file=sys.stderr)

    def on_game(a, b, done, pair_games):
        print(f"\r  vs {b:<22} {done}/{pair_games} games", end="", file=sys.stderr, flush=True)

    # Each matchup runs on its own stable seed (indexed off the full field) so a resumed matchup
    # reproduces exactly, and completes independently before we checkpoint it.
    for f in todo:
        seed = args.base_seed + sorted(field).index(f)
        recs = run_pairs([("baseline", f)], args.games, seed,
                         bots=(args.pilot, args.pilot), config=config, jobs=args.jobs,
                         game_progress=on_game)
        agg = _fold(recs)
        matchups[f] = agg
        _write_json_atomic(ckpt_path,
                           {"version": CKPT_VERSION, "run_key": run_key, "matchups": matchups})
        print(f"\r  [{len([x for x in field if x in matchups])}/{len(field)}] vs {f:<22} "
              f"{agg['A']['credit']/agg['A']['n']:6.1%}   ({agg['A']['n']} games) ✓ checkpointed",
              file=sys.stderr, flush=True)

    # --- aggregate across all matchups (both seats came out of the same games) ---
    # Seat A: the rig's cards, POOLED across the whole field — one unified ranking, 0 line = the
    # rig's overall win rate. Seat B: each field deck's own cards, per deck (their lists differ),
    # 0 line = that deck's win rate vs the rig.
    tot_c = sum(m["A"]["credit"] for m in matchups.values())
    tot_n = sum(m["A"]["n"] for m in matchups.values())
    deck_wr = tot_c / tot_n
    rates = {f: matchups[f]["A"]["credit"] / matchups[f]["A"]["n"] for f in field}
    drawn: dict[str, list] = defaultdict(lambda: [0.0, 0])
    for m in matchups.values():
        for cid, (w, n) in m["A"]["cards"].items():
            drawn[cid][0] += w
            drawn[cid][1] += n

    def _rank(tallies: dict, base_wr: float) -> list:
        """cid -> (win-rate-when-drawn, impact vs base_wr, games drawn), best-first."""
        rows = [(cid, (w / n if n else float("nan")), n) for cid, (w, n) in tallies.items()]
        return sorted(((cid, wwd, wwd - base_wr, n) for cid, wwd, n in rows), key=lambda t: -t[1])

    def _print_table(rows: list, total: int, rarity_of) -> None:
        print(f"  {'#':>2} {'card':<20}{'R':<2}{'STR':<4}{'kw':<12}{'impact':>8}{'wwd':>8}{'draw%':>7}")
        for i, (cid, wwd, impact, n) in enumerate(rows, 1):
            c = cards[cid]
            print(f"  {i:>2} {c.name:<20}{rarity_of(cid):<2}{str(c.base_strength):<4}{_kw(c):<12}"
                  f"{impact:+7.1%} {wwd:6.1%} {n/total:6.0%}")

    rmap = {"common": "C", "rare": "R", "legendary": "L"}
    csv_rows = []

    # --- seat A: the baseline rig ---
    base_tab = _rank({cid: drawn[cid] for cid in DECKLIST}, deck_wr)
    if args.report in ("self", "both"):
        print(f"\nrig win rate vs field (pilot {args.pilot}):")
        for f, wr in sorted(rates.items(), key=lambda kv: kv[1]):
            print(f"  vs {f:<22} {wr:.1%}")
        print(f"  OVERALL {deck_wr:.1%} | worst {min(rates.values()):.1%} | "
              f"best {max(rates.values()):.1%}")
        print(f"\nUNIFIED per-card ranking (overall = {deck_wr:.1%}; all x1, equal draw rate; "
              f"{tot_n} games):")
        _print_table(base_tab, tot_n, lambda cid: RARITY[cid])

        imp = {cid: impact for cid, _, impact, _ in base_tab}
        def ladder(label, ids):
            print(f"  {label:<16} " + "  ".join(f"STR{cards[i].base_strength}={imp[i]:+.1%}"
                                                for i in ids if i in imp))
        print("\nSTRENGTH LADDERS (impact by body size):")
        ladder("vanilla", VANILLA_LADDER)
        ladder("apex (free)", APEX_FREE_LADDER)
    for i, (cid, wwd, impact, n) in enumerate(base_tab, 1):
        c = cards[cid]
        csv_rows.append(["baseline", i, cid, c.name, RARITY[cid], c.base_strength, _kw(c),
                         n, round(n / tot_n, 4), round(wwd, 4), round(impact, 4)])

    # --- seat B: each field deck vs the baseline ---
    if args.report in ("opponent", "both"):
        print(f"\nfield-deck win rate vs the baseline (pilot {args.pilot}):")
        for f, wr in sorted(rates.items(), key=lambda kv: kv[1]):
            fwr = 1.0 - wr
            print(f"  {f:<22} {fwr:.1%}  ({'beats baseline' if fwr > 0.5 else 'loses'})")
    for f in sorted(field, key=lambda x: -rates[x]):
        fwr, fn = matchups[f]["B"]["credit"] / matchups[f]["B"]["n"], matchups[f]["B"]["n"]
        ftab = _rank(matchups[f]["B"]["cards"], fwr)
        if args.report in ("opponent", "both"):
            print(f"\n{f} vs baseline = {fwr:.1%}  ({fn} games) - per-card impact:")
            _print_table(ftab, fn, lambda cid: rmap.get(getattr(cards[cid], "rarity", ""), "?"))
        for i, (cid, wwd, impact, n) in enumerate(ftab, 1):
            c = cards[cid]
            csv_rows.append([f, i, cid, c.name, rmap.get(getattr(c, "rarity", ""), "?"),
                             c.base_strength, _kw(c), n, round(n / fn, 4), round(wwd, 4),
                             round(impact, 4)])

    # One CSV, every deck, every card: `deck` is "baseline" for the rig's own pooled ranking and
    # the field slug for each opponent's. Always both tables regardless of --report.
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["deck", "rank", "card_id", "name", "rarity", "strength", "keywords",
                        "drawn_games", "draw_rate", "win_rate_when_drawn", "impact"])
            w.writerows(csv_rows)
        print(f"\nwrote {args.out}", file=sys.stderr)
    print(f"(checkpoint: {ckpt_path})", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
