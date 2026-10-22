"""The replay oracle: every logged game replayed through the Python engine and the Rust engine side by side, the
serialised position and the legal actions compared after every action. The port is right when every game agrees.

    .venv/bin/python tools/engine_rs/oracle.py [--limit N] [--games ID,ID] [--verbose]
"""
import argparse, dataclasses, glob, json, sys, time

from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import SKIP, ChoiceAction
from animal_kingdom.engine.cards import load_cards
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.resources import load_bundled_json
from animal_kingdom.engine.state import new_game
from animal_kingdom.web.renamed import renamed
import ak_engine

ROOT = "/Users/martin/Work/fun/animal-kingdom/game"
CARDS_JSON = json.dumps(load_bundled_json("cards.json"))
MAPS_JSON = json.dumps(load_bundled_json("maps.json"))
_engines = {}


def engine_for(config, map_id):
    key = (json.dumps(dataclasses.asdict(config), sort_keys=True), map_id)
    if key not in _engines:
        _engines[key] = ak_engine.Engine(CARDS_JSON, MAPS_JSON, key[0], map_id)
    return _engines[key]


def canon(d):
    return json.dumps(d, sort_keys=True, default=list)


def diff_keys(a, b, path=""):
    """Where two JSON-shaped values differ, as a short list of paths with both sides."""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append((f"{path}.{k}", a.get(k, "<missing>"), b.get(k, "<missing>")))
            else:
                out.extend(diff_keys(a[k], b[k], f"{path}.{k}"))
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((f"{path}[len]", len(a), len(b)))
        for i, (x, y) in enumerate(zip(a, b)):
            out.extend(diff_keys(x, y, f"{path}[{i}]"))
    elif a != b:
        out.append((path, a, b))
    return out[:12]


def replay(g, verbose=False):
    cards = load_cards()
    lists = g["lists"]
    if not all(c in cards for l in lists for c in l):
        return "skip", "cards not in today's set"
    config = Config.default().for_log(g)
    map_id = g.get("map_id", "map_b")
    py = new_game(list(lists[0]), list(lists[1]), g["seed"], map_id=map_id, config=config, first_player=g["first_player"])
    eng = engine_for(config, map_id)
    rs = eng.new_game(list(lists[0]), list(lists[1]), g["seed"], g["first_player"], False)
    rs.set_record_events(False)

    def check(i, label):
        a, b = py.to_dict(), rs.to_dict()
        if canon(a) != canon(b):
            return f"state differs at step {i} ({label}): " + "; ".join(f"{p}: py={x!r} rs={y!r}" for p, x, y in diff_keys(a, b))
        la = [x.to_dict() for x in rules.legal_actions(py)]
        lb = rs.legal_actions()
        if [canon(x) for x in la] != [canon(x) for x in lb]:
            sa, sb = {canon(x) for x in la}, {canon(x) for x in lb}
            if sa == sb:
                return f"legal action ORDER differs at step {i} ({label}): py={la[:6]} rs={lb[:6]}"
            return f"legal actions differ at step {i} ({label}): only py={[json.loads(x) for x in sorted(sa - sb)][:5]} only rs={[json.loads(x) for x in sorted(sb - sa)][:5]}"
        return None

    bad = check(-1, "setup")
    if bad:
        return "fail", bad
    for i, adict in enumerate(g["actions"]):
        while py.pending is not None and py.effect_stack[-1].get("op") == "mulligan" and adict["kind"] != "choice":
            rules.apply_action(py, ChoiceAction(SKIP))
            try:
                rs.apply_action({"kind": "choice", "choice": SKIP})
            except Exception as e:
                return "fail", f"rust refused the mulligan skip at step {i}: {e}"
            bad = check(i, "mulligan skip")
            if bad:
                return "fail", bad
        if rules.is_terminal(py) is not None:
            break
        try:
            rules.apply_logged(py, adict)
        except Exception as e:
            return "skip", f"python replay breaks at step {i}: {e}"
        try:
            rs.apply_logged(adict)
        except Exception as e:
            return "fail", f"rust refused step {i} {adict}: {e}"
        bad = check(i, f"after {adict}")
        if bad:
            return "fail", bad
    return "ok", f"{len(g['actions'])} actions"


def games(limit=None, only=None):
    out = []
    for f in sorted(glob.glob(ROOT + "/results/human_games/web/*.jsonl")):
        for line in open(f):
            if not line.strip():
                continue
            g = renamed(json.loads(line))
            if not g.get("lists"):
                continue
            if only and g["match_id"] not in only:
                continue
            out.append(g)
    return out[:limit] if limit else out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--games", default=None)
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--stop", action="store_true", help="stop at the first failure")
    a = ap.parse_args()
    counts = {"ok": 0, "fail": 0, "skip": 0}
    t0 = time.time()
    for g in games(a.limit, set(a.games.split(",")) if a.games else None):
        try:
            status, msg = replay(g, a.verbose)
        except Exception as e:
            status, msg = "fail", f"exception: {type(e).__name__}: {e}"
        counts[status] += 1
        if status != "ok" or a.verbose:
            print(f"{status:4} {g['match_id']} game {g.get('game_no', 1)}: {msg}"[:700], flush=True)
        if status == "fail" and a.stop:
            break
    print(f"=== {counts} in {time.time() - t0:.0f}s", flush=True)
