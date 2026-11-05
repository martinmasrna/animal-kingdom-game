"""Read a candidate arm against a baseline arm (`arm.py` outputs on the same schedule): wins, the paired difference
with its 95% interval (the paired bootstrap of `sim.bot_comparison`, same seed), per deck and pooled; den captures
made and suffered, all and by turn 5; the pilot's seconds per move (mean, median, 95th and 99th
percentiles, slowest, how many over 8 s and over 30 s).

    .venv/bin/python tools/bot_bench/pair.py BASELINE.jsonl CANDIDATE.jsonl [--md]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from animal_kingdom.sim.bot_comparison import DEFAULT_BOOTSTRAP_SEED, paired_bootstrap_ci  # noqa: E402


def load(path: str) -> dict:
    with open(path) as fh:
        return {(g["deck"], g["opp"], g["seed"], g["first"]): g for g in map(json.loads, fh) if g.get("deck")}


def credit(g: dict) -> float:
    return 0.5 if g["winner"] is None else float(g["winner"] == "A")


def summary(games: list[dict]) -> dict:
    n = len(games)
    caps = [g for g in games if g["reason"] == "hq_capture"]
    return {
        "games": n,
        "win": sum(map(credit, games)) / n,
        "den_won": sum(g["winner"] == "A" for g in caps), "den_lost": sum(g["winner"] == "B" for g in caps),
        # turns counts both players' turns: the game's fifth turn is turn 5
        "den_lost_t5": sum(g["winner"] == "B" and g["turns"] <= 5 for g in caps),
        "moves": sum(g["moves"] for g in games), "move_s": sum(g["move_s"] for g in games),
        "max_move_s": max(g["max_move_s"] for g in games),
        "times": sorted(t for g in games for t in g.get("times", [])),
    }


def pct(xs: list, q: float) -> float:
    return xs[min(len(xs) - 1, int(q * len(xs)))] if xs else 0.0


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("baseline")
    p.add_argument("candidate")
    p.add_argument("--md", action="store_true", help="a markdown table")
    a = p.parse_args(argv)
    base, cand = load(a.baseline), load(a.candidate)
    keys = sorted(set(base) & set(cand))
    decks = list(dict.fromkeys(k[0] for k in keys))
    rows = []
    for deck in decks + ["(all)"]:
        ks = [k for k in keys if deck == "(all)" or k[0] == deck]
        deltas = [credit(cand[k]) - credit(base[k]) for k in ks]
        lo, hi = paired_bootstrap_ci(deltas, resamples=10_000, seed=(DEFAULT_BOOTSTRAP_SEED, deck, "arm"))
        rows.append((deck, summary([base[k] for k in ks]), summary([cand[k] for k in ks]),
                     sum(deltas) / len(deltas), lo, hi))
    if a.md:
        print("| deck | games | baseline wins | candidate wins | difference | 95% interval | dens taken b/c | "
              "dens lost b/c | lost by turn 5 b/c | s a move b/c |")
        print("|---|---|---|---|---|---|---|---|---|---|")
    for deck, b, c, d, lo, hi in rows:
        bs = b["move_s"] / max(b["moves"], 1)
        cs = c["move_s"] / max(c["moves"], 1)
        cells = [deck, str(c["games"]), f"{100 * b['win']:.1f}%", f"{100 * c['win']:.1f}%", f"{100 * d:+.1f}",
                 f"{100 * lo:+.1f} to {100 * hi:+.1f}", f"{b['den_won']}/{c['den_won']}",
                 f"{b['den_lost']}/{c['den_lost']}", f"{b['den_lost_t5']}/{c['den_lost_t5']}", f"{bs:.3f}/{cs:.3f}"]
        print(("| " + " | ".join(cells) + " |") if a.md else "  ".join(f"{x:>14}" for x in cells))
    print(f"\npaired games {len(keys)} (baseline {len(base)}, candidate {len(cand)})")
    for name, s in (("baseline", rows[-1][1]), ("candidate", rows[-1][2])):
        t = s["times"]
        print(f"  {name}: {len(t)} moves, median {pct(t, 0.5):.3f}s, 95th {pct(t, 0.95):.2f}s, 99th {pct(t, 0.99):.2f}s, "
              f"slowest {s['max_move_s']:.2f}s, over 8 s {sum(x > 8 for x in t)}, over 30 s {sum(x > 30 for x in t)}")


if __name__ == "__main__":
    main()
