"""The Python side of the wasm oracle (wasm_oracle.mjs): logged human games replayed through the Python engine, written
as JSON lines for the node script to replay through the browser build and compare. Per game a header line
{"game": {match_id, game_no, lists, seed, first_player, map_id, config}}, then one line per step
{"step": i, "label", "do": action dict | "skip" | null, "state", "legal", "views": {"A", "B"}}: the action applied
(a mulligan skip the log leaves out is "skip"; the setup has none), then the position, the legal actions and both
seats' game views (match.py `_game_view`, without the match's clock, history and events). Games with cards not in
today's set, or that the Python engine cannot replay, are left out (newest first; each with a {"skipped": ...} line).

    .venv/bin/python tools/engine_rs/wasm_trace.py --limit 100 > trace.jsonl
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))   # REPO_ROOT: this tree
import argparse, dataclasses, glob, json, warnings

warnings.filterwarnings("ignore")

from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import SKIP, ChoiceAction
from animal_kingdom.engine.cards import load_cards
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.state import new_game
from animal_kingdom.web.match import Match, Seat
from animal_kingdom.web.renamed import renamed

ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
MATCH_ONLY = ("clock", "history", "events")


def views(state) -> dict:
    m = Match("oracle", Seat("a", "A"))
    m.state = state
    out = {}
    for s, o in (("A", "B"), ("B", "A")):
        g = m._game_view(s, o)
        out[s] = {k: v for k, v in g.items() if k not in MATCH_ONLY}
    return out


def trace(g, emit) -> str:
    cards = load_cards()
    lists = g["lists"]
    if not all(c in cards for l in lists for c in l):
        return "cards not in today's set"
    config = Config.default().for_log(g)
    map_id = g.get("map_id", "map_b")
    # the replay first, so a game the Python engine cannot finish writes nothing
    py = new_game(list(lists[0]), list(lists[1]), g["seed"], map_id=map_id, config=config, first_player=g["first_player"])
    steps = [(None, "setup")]
    for i, adict in enumerate(g["actions"]):
        while py.pending is not None and py.effect_stack[-1].get("op") == "mulligan" and adict["kind"] != "choice":
            rules.apply_action(py, ChoiceAction(SKIP))
            steps.append(("skip", f"mulligan skip before {i}"))
        if rules.is_terminal(py) is not None:
            break
        try:
            rules.apply_logged(py, adict)
        except Exception as e:
            return f"python replay breaks at step {i}: {e}"
        steps.append((adict, f"step {i}"))
    py = new_game(list(lists[0]), list(lists[1]), g["seed"], map_id=map_id, config=config, first_player=g["first_player"])
    emit({"game": {"match_id": g.get("match_id"), "game_no": g.get("game_no", 1), "lists": lists, "seed": g["seed"],
                   "first_player": g["first_player"], "map_id": map_id, "config": dataclasses.asdict(config)}})
    for n, (do, label) in enumerate(steps):
        if do == "skip":
            rules.apply_action(py, ChoiceAction(SKIP))
        elif do is not None:
            rules.apply_logged(py, do)
        py.events = []
        emit({"step": n, "label": label, "do": do, "state": py.to_dict(),
              "legal": [a.to_dict() for a in rules.legal_actions(py)], "views": views(py)})
    return ""


def games():
    """The logged games, newest first: the ones most likely to replay on today's cards."""
    for f in sorted(glob.glob(ROOT + "/results/human_games/web/*.jsonl"), reverse=True):
        for line in open(f):
            if line.strip():
                g = renamed(json.loads(line))
                if g.get("lists"):
                    yield g


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=100, help="games written (skipped ones don't count)")
    a = ap.parse_args()
    out = _sys.stdout
    emit = lambda d: out.write(json.dumps(d) + "\n")
    written = 0
    for g in games():
        why = trace(g, emit)
        if why:
            emit({"skipped": g.get("match_id"), "why": why})
            continue
        written += 1
        if written >= a.limit:
            break
    out.flush()
