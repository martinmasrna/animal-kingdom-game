"""How many of the mined den-capture positions the live Expert converts, and how long it thinks a move there.

Analysis only. For every position in a `mine.py` output (default `forced_captures-2026-11-05.jsonl`), the game is
replayed from its log up to that position (the same replay as `mine.py`), the live Expert (`web.match.EXPERT`, built by
`sim.runner.make_bot`, so it is the Rust bot when AK_RUST_BOTS=1 and the engine is built, the Python one otherwise)
plays the whole turn for the player to move, and the position counts as found when that turn ends in their den capture.
A choice the opponent makes inside the turn (rare) is taken by GreedyBot. The bot sees what it sees in a live game:
`choose(state.view_for(me), legal, state)`; it reads only its own seat (bots are honest, regression-tested).

Usage:
  .venv/bin/python tools/puzzles/expert_finds.py                          # all 154, 4 workers, seed 0
  .venv/bin/python tools/puzzles/expert_finds.py --workers 1 --out results/puzzles/expert_before.json
  .venv/bin/python tools/puzzles/expert_finds.py --spec "referee_learned:...,den_open=false" --seeds 0,1,2
  .venv/bin/python tools/puzzles/expert_finds.py --only OXHIXA,ZXMEHG      # positions whose path contains these

Each result also says whether the rebuilt position matches the recorded one (`same_position`: the board's top units
and the hand, as `mine.py` wrote them) and whether the recorded line still captures on the true state on today's
cards (`line_still_captures`, a check by the tool, never shown to the bot): the cards move, so a position mined on
older cards may hold no capture now.

Time per move is the wall time of each `choose` the Expert makes in the turn (turn actions and its own sub-choices
alike), averaged over every such call (`sec_per_move_mean`; `sec_first_move_mean` is the turn's first call, the
full search); it depends on the machine and its load, and the Expert's 8 s budget
(`time_budget`) cuts its deepening, so compare runs made on the same machine with the same `--workers`. The time budget
also means a position's result can change with the load. The output JSON keeps every position's result, moves and times.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import statistics
import sys
import time
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from animal_kingdom.decks import load_premade_deck  # noqa: E402
from animal_kingdom.engine import rules  # noqa: E402
from animal_kingdom.engine.actions import SKIP, ChoiceAction, action_from_dict  # noqa: E402
from animal_kingdom.engine.config import Config  # noqa: E402
from animal_kingdom.engine.state import GameState, new_game  # noqa: E402
from animal_kingdom.sim.runner import make_bot  # noqa: E402
from animal_kingdom.web.match import EXPERT  # noqa: E402
from animal_kingdom.web.renamed import renamed  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mine import _Sub, _follows, _snapshot  # noqa: E402  (the miner beside this file)

DEFAULT_IN = os.path.join(ROOT, "tools", "puzzles", "forced_captures-2026-11-05.jsonl")


def rebuild(path: str, line: int, action_index: int) -> GameState:
    """The game state of `path` line `line` just before its logged action `action_index` (mine.py's replay)."""
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        for i, raw in enumerate(fh):
            if i == line:
                log = json.loads(raw)
                break
        else:
            raise ValueError(f"{path} has no line {line}")
    log = renamed(log)
    deck_a, deck_b = log.get("lists") or (load_premade_deck(log["deck_a"]), load_premade_deck(log["deck_b"]))
    state = new_game(list(deck_a), list(deck_b), log["seed"], map_id=log.get("map_id", "map_b"),
                     config=Config.default().for_log(log), first_player=log["first_player"])
    for idx, adict in enumerate(log["actions"]):
        while state.pending is not None and state.effect_stack[-1].get("op") == "mulligan" \
                and adict["kind"] != "choice":
            rules.apply_action(state, ChoiceAction(SKIP))
        if idx == action_index:
            return state
        rules.apply_logged(state, adict)
    raise ValueError(f"{path} line {line} has no action {action_index}")


def play_turn(state: GameState, me: str, spec: str, seed: int) -> dict:
    """The Expert plays `me`'s whole turn from `state`; whether it captured, its moves and its time per call."""
    bot = make_bot(spec, seed)
    other = make_bot("greedy", seed + 1)
    turn = state.turn_counter
    moves, times = [], []
    guard = 0
    while rules.is_terminal(state) is None and state.turn_counter == turn and guard < 60:
        guard += 1
        actor = state.player_to_act()
        legal = rules.legal_actions(state)
        if actor == me:
            t0 = time.perf_counter()
            action = bot.choose(state.view_for(me), legal, state)
            times.append(time.perf_counter() - t0)
            moves.append(action.to_dict())
        else:
            action = other.choose(state.view_for(actor), legal, state)
        rules.apply_action(state, action)
    res = rules.is_terminal(state)
    return {"captured": bool(res is not None and res.winner == me and res.reason == "hq_capture"),
            "won": bool(res is not None and res.winner == me),
            "result": [res.winner, res.reason] if res is not None else None, "moves": moves, "times": times}


def _seed_for(rec: dict, seed: int) -> int:
    return zlib.crc32(f"{rec['path']}:{rec['line']}:{rec['action_index']}".encode()) % 100_000 + 1_000_003 * seed


def _run(task: tuple) -> dict:
    rec, spec, seed = task
    out = {k: rec[k] for k in ("path", "line", "action_index", "player")}
    out.update(seed=seed, human=rec.get("human"), was_captured=rec.get("captured"))
    try:
        state = rebuild(rec["path"], rec["line"], rec["action_index"])
        if state.current != rec["player"]:
            raise ValueError(f"replay reached {state.current} to move, the record says {rec['player']}")
        snap = _snapshot(state, rec["player"])
        out["same_position"] = snap["board"] == rec["position"]["board"] and snap["hand"] == rec["position"]["hand"]
        line = [_Sub(action_from_dict(a)) if a.get("sub") else action_from_dict(a) for a in rec["shortest_line"]]
        out["line_still_captures"] = _follows(state.clone(), rec["player"], line)   # on the true state: a check only
        out.update(play_turn(state, rec["player"], spec, _seed_for(rec, seed)))
        out["error"] = None
    except Exception as e:  # noqa: BLE001 - a log that no longer replays on these cards
        out.update(captured=False, won=False, result=None, moves=[], times=[], error=f"{type(e).__name__}: {e}"[:200])
    return out


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--positions", default=DEFAULT_IN)
    p.add_argument("--spec", default=EXPERT, help="bot spec (default: the live Expert, web.match.EXPERT)")
    p.add_argument("--seeds", default="0", help="comma-separated bot seeds; each position is played once per seed")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--only", default="", help="comma-separated substrings; keep positions whose path holds one")
    p.add_argument("--out", default=None, help="write every result as JSON here")
    args = p.parse_args(argv)

    with open(args.positions, encoding="utf-8") as fh:
        recs = [json.loads(l) for l in fh if l.strip()]
    if args.only:
        keys = args.only.split(",")
        recs = [r for r in recs if any(k in r["path"] for k in keys)]
    seeds = [int(s) for s in args.seeds.split(",")]
    tasks = [(r, args.spec, s) for s in seeds for r in recs]
    t0 = time.time()
    if args.workers > 1:
        with mp.Pool(args.workers) as pool:
            results = list(pool.imap(_run, tasks, chunksize=1))
    else:
        results = [_run(t) for t in tasks]
    times = [t for r in results for t in r["times"]]
    first = [r["times"][0] for r in results if r["times"]]
    summary = {
        "spec": args.spec, "seeds": seeds, "workers": args.workers, "positions": len(recs), "runs": len(results),
        "found": sum(r["captured"] for r in results),
        "won_that_turn": sum(r["won"] for r in results),
        "found_where_line_still_captures": sum(r["captured"] for r in results if r.get("line_still_captures")),
        "line_still_captures": sum(bool(r.get("line_still_captures")) for r in results),
        "same_position": sum(bool(r.get("same_position")) for r in results),
        "errors": sum(r["error"] is not None for r in results),
        "moves": len(times),
        "sec_per_move_mean": round(statistics.mean(times), 3) if times else None,
        "sec_per_move_median": round(statistics.median(times), 3) if times else None,
        "sec_per_move_max": round(max(times), 3) if times else None,
        "sec_first_move_mean": round(statistics.mean(first), 3) if first else None,
        "wall_seconds": round(time.time() - t0, 1),
        "missed": [f"{r['path'].rsplit('/', 1)[-1]} line {r['line']} action {r['action_index']} seed {r['seed']}"
                   for r in results if not r["captured"]],
    }
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump({"summary": summary, "results": results}, fh, indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
