"""Hill-climb a legal deck list for the Expert to win with against a field of decks, Expert against Expert.

Analysis only: writes JSON, ships nothing. A list is card id -> copies, legal by `decks.decklist_problems` (30 cards,
the copy limits, at most 8 rares and 4 legendaries, collectible cards only). A neighbour swaps every copy of one card
for the same number of copies of an unused collectible card of the same rarity, so the shape of the list (how many
legendaries, rares, commons) stays the seed's. Fitness is the mean win rate against the field on a fixed seed set
(`--games` seeds per field deck, each played with both first movers, the candidate in seat A), so two lists are
compared game for game. Each step tries `--neighbors` neighbours and takes the best strict improvement; the climb
stops after `--patience` steps without one, or `--steps`. The search seeds are not the check's: `--check N` plays the
seed list and the finalist on N other seeds a field deck (both movers) and prints the paired difference.

    .venv/bin/python tools/bot_bench/deck_climb.py --seed-deck den_rush --field a,b,... --spec SPEC --out FILE.json
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault("AK_RUST_BOTS", "1")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import warnings  # noqa: E402
warnings.filterwarnings("ignore")
from arm import _game  # noqa: E402
from animal_kingdom.decks import PREMADE_DECKS, decklist_problems  # noqa: E402
from animal_kingdom.engine.cards import load_cards  # noqa: E402
from animal_kingdom.sim.bot_comparison import DEFAULT_BOOTSTRAP_SEED, paired_bootstrap_ci  # noqa: E402

SLUG = "climb_candidate"
SEARCH_SEED = 20261105
CHECK_SEED = 990000000


def expand(counts: dict) -> list[str]:
    return [cid for cid, n in sorted(counts.items()) for _ in range(n)]


def play(counts: dict, field: list[str], games: int, base: int, spec: str, jobs: int) -> list[dict]:
    """Every game of `counts` (seat A) against the field: `games` seeds a field deck, both first movers."""
    from animal_kingdom import decks
    decks.EXTRA_DECKS[SLUG] = expand(counts)
    os.environ["AK_EXTRA_DECKS"] = json.dumps({s: d for s, d in decks.EXTRA_DECKS.items() if s != "baseline"})
    tasks = [(SLUG, opp, base + fi * 1000 + i, first, spec, spec, False)
             for fi, opp in enumerate(field) for first in ("A", "B") for i in range(games)]
    with ProcessPoolExecutor(max_workers=jobs) as ex:   # a fresh pool: the workers read the list from the environment
        return [row for row, _ in ex.map(_game, tasks)]


def credit(g: dict) -> float:
    return 0.5 if g["winner"] is None else float(g["winner"] == "A")


def fitness(rows: list[dict]) -> float:
    return sum(map(credit, rows)) / len(rows)


def neighbour(counts: dict, pools: dict, cards: dict, rng: random.Random) -> dict:
    out_id = rng.choice(sorted(counts))
    rarity = cards[out_id].rarity
    choices = [c for c in pools[rarity] if c not in counts]
    new = dict(counts)
    n = new.pop(out_id)
    new[rng.choice(choices)] = n
    return new


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--seed-deck", required=True, help="a shipped deck slug to start from")
    p.add_argument("--field", required=True)
    p.add_argument("--spec", required=True, help="the pilot of both seats")
    p.add_argument("--games", type=int, default=2, help="search seeds per field deck per mover")
    p.add_argument("--neighbors", type=int, default=6)
    p.add_argument("--steps", type=int, default=10)
    p.add_argument("--patience", type=int, default=3)
    p.add_argument("--rng-seed", type=int, default=0)
    p.add_argument("--check", type=int, default=10, help="check seeds per field deck per mover (0: none)")
    p.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    cards = load_cards()
    pools: dict[str, list[str]] = {}
    for c in cards.values():
        if c.collectible:
            pools.setdefault(c.rarity, []).append(c.id)
    for r in pools:
        pools[r].sort()
    field = a.field.split(",")
    seed_counts: dict[str, int] = {}
    for cid in PREMADE_DECKS[a.seed_deck]:
        seed_counts[cid] = seed_counts.get(cid, 0) + 1
    assert not decklist_problems(expand(seed_counts)), decklist_problems(expand(seed_counts))
    rng = random.Random(a.rng_seed)
    t0 = time.time()
    best = seed_counts
    best_f = seed_f = fitness(play(best, field, a.games, SEARCH_SEED, a.spec, a.jobs))
    history = [{"step": 0, "fitness": best_f, "deck": best}]
    print(f"seed {a.seed_deck}: {100 * best_f:.1f}% ({time.time() - t0:.0f}s)", flush=True)
    barren = 0
    for step in range(1, a.steps + 1):
        tried = []
        seen = set()
        while len(tried) < a.neighbors:
            nb = neighbour(best, pools, cards, rng)
            key = tuple(sorted(nb.items()))
            if key in seen or decklist_problems(expand(nb)):
                continue
            seen.add(key)
            tried.append((fitness(play(nb, field, a.games, SEARCH_SEED, a.spec, a.jobs)), nb))
        f, nb = max(tried, key=lambda t: t[0])
        swap = (sorted(set(best) - set(nb)), sorted(set(nb) - set(best)))
        improved = f > best_f + 1e-9
        if improved:
            best, best_f, barren = nb, f, 0
        else:
            barren += 1
        history.append({"step": step, "fitness": best_f, "tried_best": f, "swap": swap, "accepted": improved,
                        "tried": [t[0] for t in tried], "deck": best})
        print(f"step {step}: tried best {100 * f:.1f}% {swap[0]} -> {swap[1]} {'ACCEPT' if improved else '--'}; "
              f"best {100 * best_f:.1f}% ({time.time() - t0:.0f}s)", flush=True)
        with open(a.out, "w") as fh:
            json.dump({"args": vars(a), "seed_fitness": seed_f, "history": history, "best": best}, fh, indent=1)
        if barren >= a.patience:
            break
    out = {"args": vars(a), "seed_fitness": seed_f, "history": history, "best": best, "best_fitness": best_f}
    if a.check:
        base_rows = play(seed_counts, field, a.check, CHECK_SEED, a.spec, a.jobs)
        best_rows = play(best, field, a.check, CHECK_SEED, a.spec, a.jobs)
        deltas = [credit(b) - credit(s) for s, b in zip(base_rows, best_rows)]
        lo, hi = paired_bootstrap_ci(deltas, resamples=10_000, seed=(DEFAULT_BOOTSTRAP_SEED, a.seed_deck, "climb"))
        per_opp = {}
        for s, b in zip(base_rows, best_rows):
            d = per_opp.setdefault(s["opp"], [0, 0, 0])
            d[0] += credit(s)
            d[1] += credit(b)
            d[2] += 1
        out["check"] = {"games": len(deltas), "seed_win": fitness(base_rows), "best_win": fitness(best_rows),
                        "delta": sum(deltas) / len(deltas), "ci95": [lo, hi],
                        "per_opponent": {o: {"seed": v[0] / v[2], "best": v[1] / v[2], "games": v[2]}
                                         for o, v in per_opp.items()},
                        "seed_rows": base_rows, "best_rows": best_rows}
        print(f"check, {len(deltas)} games: seed {100 * fitness(base_rows):.1f}%, finalist "
              f"{100 * fitness(best_rows):.1f}%, difference {100 * out['check']['delta']:+.1f} "
              f"({100 * lo:+.1f} to {100 * hi:+.1f})", flush=True)
    with open(a.out, "w") as fh:
        json.dump(out, fh, indent=1)
    names = {c.id: c.name for c in cards.values()}
    print("finalist:", ", ".join(f"{n}x {names.get(c, c)}" for c, n in sorted(best.items())), flush=True)


if __name__ == "__main__":
    main()
