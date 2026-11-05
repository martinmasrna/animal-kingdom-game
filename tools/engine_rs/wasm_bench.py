"""The bots' time per move on the server's engine (the Rust module the server's bots run on), for the browser numbers in
knowledge/wasm/STATUS.md; wasm_bench.mjs times the same positions in the browser.

Positions: every `--every`th decision with more than one legal action in the newest logged human games that replay on
today's cards (wasm_trace.py), written to `--out` as JSON. Each position is chosen by a fresh bot of the level (as the
server's first move of a game), one core.

    .venv/bin/python tools/engine_rs/wasm_bench.py --out positions.json --games 10 --every 6 [--levels normal,expert,expert_fixed]
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))   # REPO_ROOT: this tree
import argparse, json, statistics, time, warnings

warnings.filterwarnings("ignore")

import ak_engine
from animal_kingdom.engine.resources import load_bundled_json
from animal_kingdom.web.local import bot_spec, engine_doc
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import wasm_trace   # noqa: E402 (beside this file)


def positions(games: int, every: int) -> list:
    out, n = [], 0
    lines = []
    for g in wasm_trace.games():
        if wasm_trace.trace(g, lines.append) == "":
            n += 1
        if n >= games:
            break
    k = 0
    for d in lines:
        if "step" in d and len(d["legal"]) > 1 and d["state"].get("result") is None:
            k += 1
            if k % every == 0:
                out.append(d["state"])
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--games", type=int, default=10)
    ap.add_argument("--every", type=int, default=6)
    ap.add_argument("--levels", default="normal,expert,expert_fixed")
    a = ap.parse_args()
    states = positions(a.games, a.every)
    doc = json.loads(engine_doc())
    eng = ak_engine.Engine(json.dumps(doc["cards"]), json.dumps(doc["maps"]), json.dumps(doc["config"]), doc["map_id"])
    report = {"positions": len(states), "levels": {}}
    for level in a.levels.split(","):
        # expert_fixed: the Expert without its 8 s deepening budget, the same work on both engines whatever their speed
        spec = bot_spec(level.replace("_fixed", ""))
        if level.endswith("_fixed"):
            spec = {**spec, "spec": spec["spec"].replace("time_budget=8", "time_budget=0")}
        ms, moves = [], []
        for i, s in enumerate(states):
            bot = ak_engine.Bot(spec["spec"], 1000 + i, spec["evaluator"])
            st = eng.from_dict(s)
            t0 = time.perf_counter()
            moves.append(bot.choose(st))
            ms.append((time.perf_counter() - t0) * 1000)
        report["levels"][level] = {"spec": spec["spec"], "evaluator": spec["evaluator"], "ms": ms, "moves": moves,
                                   "median_ms": statistics.median(ms), "mean_ms": statistics.mean(ms), "max_ms": max(ms)}
        print(f"{level}: {len(ms)} moves, median {statistics.median(ms):.0f} ms, mean {statistics.mean(ms):.0f} ms, max {max(ms):.0f} ms", flush=True)
    json.dump({"states": states, "native": report}, open(a.out, "w"))
