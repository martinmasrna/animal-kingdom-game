"""Record the bots' play on a fixed schedule, move for move, with timings: the acceptance set for engine speedups.
Byte-identical play before and after a change is the test (the Expert runs without its time budget here, so the
machine's load cannot change its moves).   .venv/bin/python tools/engine_speed/record.py results/engine_speed/<name>.json [-j1]
The games run in parallel, one per core; `-j1` plays them one at a time, for timings that compare across runs."""
import json, os, sys, time
from concurrent.futures import ProcessPoolExecutor
from animal_kingdom.sim.runner import make_bot, play_game
from animal_kingdom.web.match import EXPERT

EXPERT_UNTIMED = EXPERT.replace("time_budget=8", "time_budget=0")
SCHEDULE = [  # (bot kind, deck_a, deck_b, seed)
    *[("easy", a, b, s) for (a, b) in (("cats", "fish"), ("colony", "den_rush"), ("optimizer_4", "hoofed")) for s in (1, 2)],
    *[("turn", a, b, s) for (a, b) in (("cats", "fish"), ("colony", "den_rush"), ("handlock", "food_aggro"), ("removal", "giants")) for s in (1, 2)],
    *[(EXPERT_UNTIMED, a, b, s) for (a, b) in (("cats", "fish"), ("colony", "den_rush"), ("bot_optimized", "canines"), ("token", "tempo")) for s in (1, 2)],
]

def play(entry):
    kind, a, b, seed = entry
    t = time.perf_counter()
    r = play_game(a, b, seed, bot_a=make_bot(kind, seed * 2 + 1), bot_b=make_bot(kind, seed * 2 + 2), log_actions=True)
    return {"kind": kind, "a": a, "b": b, "seed": seed, "winner": r.winner, "turns": r.turns,
            "seconds": round(time.perf_counter() - t, 2), "actions": r.actions}

def main(out, jobs):
    order = sorted(SCHEDULE, key=lambda e: e[0] != EXPERT_UNTIMED)   # the long Expert games start first
    with ProcessPoolExecutor(jobs) as pool:
        done = dict(zip(order, pool.map(play, order)))
    games = [done[e] for e in SCHEDULE]
    for g in games:
        print(f"{g['kind'].split(':')[0]:8} {g['a']:>14} v {g['b']:<14} seed {g['seed']}: {g['winner']} in {g['turns']} turns, {len(g['actions'])} actions, {g['seconds']:.1f}s")
    json.dump(games, open(out, "w"))
    print("total", round(sum(g["seconds"] for g in games), 1), "s")

if __name__ == "__main__":
    main(sys.argv[1], 1 if "-j1" in sys.argv[2:] else os.cpu_count())
