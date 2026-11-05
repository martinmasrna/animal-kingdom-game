"""One arm of a paired benchmark: one pilot spec on every listed deck against one opponent spec, on a fixed seed
schedule, so two arms run apart are paired game for game. The baseline arm is played once and every candidate arm
is read against it (`pair.py`), which halves the cost of a series of one-dial comparisons.

Schedule: for every (deck, opponent deck) in decks x opponents, `--games` seeds with the pilot moving first and the
same seeds with the opponent moving first (the mirror too), the pilot always in seat A. Seeds are
`--seed + block * 1000 + i`, the block being the pair's index, so a pair's games keep their seeds when the deck lists
change. Bots are seeded as `sim.runner` seeds them (game seed * 2 + 1 and + 2). The Rust bots play
(AK_RUST_BOTS=1 is set here); a spec the port lacks would fall back to Python and take hours.

Output: `<out>.jsonl`, one line per game: deck, opponent, seed, first player, winner, reason, turns, the pilot's
moves (`choose` calls with more than one legal option, sub-choices included), each one's wall seconds, their sum
and the slowest. Lines already in the file are skipped, so a killed run resumes. `<out>.logs.jsonl` holds the game logs
(`sim.replay` format).

    .venv/bin/python tools/bot_bench/arm.py --spec SPEC --opponent SPEC --decks a,b,... --games 10 --jobs 4 --out FILE
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault("AK_RUST_BOTS", "1")

BASE_SEED = 683470156   # sim.bot_comparison.ACCEPTANCE_SEED


def _game(task: tuple) -> dict:
    import warnings
    warnings.filterwarnings("ignore")
    from animal_kingdom.sim.runner import make_bot, parse_bot_spec, play_game
    deck, opp, seed, first, spec, opp_spec, log = task
    kind_a, kw_a = parse_bot_spec(spec, "--spec")
    kind_b, kw_b = parse_bot_spec(opp_spec, "--opponent")
    bot_a = make_bot(kind_a, seed=seed * 2 + 1, extra=dict(kw_a))
    bot_b = make_bot(kind_b, seed=seed * 2 + 2, extra=dict(kw_b))
    times: list[float] = []
    choose = bot_a.choose

    def timed(view, legal, state=None):
        t0 = time.perf_counter()
        action = choose(view, legal, state)
        if len(legal) > 1:
            times.append(time.perf_counter() - t0)
        return action

    bot_a.choose = timed
    r = play_game(deck, opp, seed, bot_a=bot_a, bot_b=bot_b, log_actions=log, first_player=first)
    out = {"deck": deck, "opp": opp, "seed": seed, "first": first, "winner": r.winner, "reason": r.reason,
           "turns": r.turns, "moves": len(times), "move_s": round(sum(times), 3),
           "max_move_s": round(max(times), 3) if times else 0.0,
           "times": [round(t, 3) for t in times]}
    return out, (r if log else None)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--spec", required=True)
    p.add_argument("--opponent", required=True)
    p.add_argument("--decks", required=True, help="comma-separated deck slugs (the opponents too, unless --opponents)")
    p.add_argument("--opponents", default=None)
    p.add_argument("--games", type=int, default=10, help="seeds per (deck, opponent), each played with both movers")
    p.add_argument("--seed", type=int, default=BASE_SEED)
    p.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    p.add_argument("--out", required=True)
    p.add_argument("--no-logs", action="store_true")
    a = p.parse_args(argv)
    decks = a.decks.split(",")
    opps = a.opponents.split(",") if a.opponents else decks
    done = set()
    if os.path.exists(a.out):
        with open(a.out) as fh:
            done = {(g["deck"], g["opp"], g["seed"], g["first"]) for g in map(json.loads, fh) if g.get("deck")}
    tasks = []
    for di, deck in enumerate(decks):
        for oi, opp in enumerate(opps):
            block = di * len(opps) + oi
            for first in ("A", "B"):
                for i in range(a.games):
                    seed = a.seed + block * 1000 + i
                    if (deck, opp, seed, first) not in done:
                        tasks.append((deck, opp, seed, first, a.spec, a.opponent, not a.no_logs))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    meta = a.out + ".meta.json"
    if not os.path.exists(meta):
        with open(meta, "w") as fh:
            json.dump({"spec": a.spec, "opponent": a.opponent, "decks": decks, "opponents": opps, "games": a.games,
                       "seed": a.seed, "started": time.strftime("%Y-%m-%d %H:%M")}, fh, indent=1)
    print(f"{len(tasks)} games to play ({len(done)} already done)", flush=True)
    t0 = time.time()
    from animal_kingdom.sim.replay import write_game_logs
    with ProcessPoolExecutor(max_workers=a.jobs) as ex, open(a.out, "a") as fh:
        futures = [ex.submit(_game, t) for t in tasks]
        for n, fut in enumerate(as_completed(futures), 1):
            row, rec = fut.result()
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            if rec is not None:
                write_game_logs([rec], a.out + ".logs.jsonl", map_id="map_b", bots=(a.spec, a.opponent))
            if n % 50 == 0 or n == len(tasks):
                print(f"  {n}/{len(tasks)} {time.time() - t0:.0f}s", flush=True)
    print("=== done", flush=True)


if __name__ == "__main__":
    main()
