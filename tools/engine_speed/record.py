"""Record the bots' play on a fixed schedule, move for move, with timings: the acceptance set for engine speedups.
Byte-identical play before and after a change is the test (the Expert runs without its time budget here, so the
machine's load cannot change its moves).   .venv/bin/python tools/engine_speed/record.py results/engine_speed/<name>.json
The committed baseline, tools/engine_speed/baseline.json, is what the Docker build's compile gate compares against (deploy/Dockerfile):
the compiled engine must play all 22 games move for move the same. Record it again whenever the play legitimately changes: a bot
change, a card change, a new Expert spec (web.match.EXPERT, which this reads). Record it with the plain engine from the tree:
    .venv/bin/python tools/engine_speed/record.py tools/engine_speed/baseline.json"""
import json, sys, time
from animal_kingdom.sim.runner import make_bot, play_game
from animal_kingdom.web.match import EXPERT

EXPERT_UNTIMED = EXPERT.replace("time_budget=8", "time_budget=0")
SCHEDULE = [  # (bot kind, deck_a, deck_b, seed)
    *[("easy", a, b, s) for (a, b) in (("cats", "fish"), ("colony", "den_rush"), ("optimizer_4", "hoofed")) for s in (1, 2)],
    *[("turn", a, b, s) for (a, b) in (("cats", "fish"), ("colony", "den_rush"), ("handlock", "food_aggro"), ("removal", "giants")) for s in (1, 2)],
    *[(EXPERT_UNTIMED, a, b, s) for (a, b) in (("cats", "fish"), ("colony", "den_rush"), ("bot_optimized", "canines"), ("token", "tempo")) for s in (1, 2)],
]

def main(out):
    games = []
    for kind, a, b, seed in SCHEDULE:
        t = time.perf_counter()
        r = play_game(a, b, seed, bot_a=make_bot(kind, seed * 2 + 1), bot_b=make_bot(kind, seed * 2 + 2), log_actions=True)
        dt = time.perf_counter() - t
        games.append({"kind": kind, "a": a, "b": b, "seed": seed, "winner": r.winner, "turns": r.turns, "seconds": round(dt, 2), "actions": r.actions})
        print(f"{kind.split(':')[0]:8} {a:>14} v {b:<14} seed {seed}: {r.winner} in {r.turns} turns, {len(r.actions)} actions, {dt:.1f}s", flush=True)
        json.dump(games, open(out, "w"))
    print("total", round(sum(g["seconds"] for g in games), 1), "s")

if __name__ == "__main__":
    main(sys.argv[1])
