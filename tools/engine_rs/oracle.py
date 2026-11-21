"""The replay oracle: every logged game that still replays on today's Python engine, replayed through the Rust engine
side by side, everything compared after every action (common.compare).

    .venv/bin/python tools/engine_rs/oracle.py [--dir results/human_games/web] [--verbose]

A game from before a rule or card change stops replaying (a card it holds is gone, or an action it took is no longer
legal); those are counted and left out.
"""
import argparse, glob, json, os, sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import compare, engines

from animal_kingdom.engine import rules
from animal_kingdom.engine.state import new_game
from animal_kingdom.replay import replay

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def replays_today(log, cards):
    """Whether the Python engine still plays this log through: its cards exist and every action it took is still legal
    (the result may differ from the one recorded, when a card's numbers changed since)."""
    try:
        if not all(c in cards for deck in log["lists"] for c in deck):
            return False
        replay(log)
    except Exception:
        return False
    return True


def side_by_side(log, cards, config, eng):
    deck_a, deck_b = log["lists"]
    leaders = log.get("leaders") or {}
    py = new_game(list(deck_a), list(deck_b), log["seed"], cards=cards, config=config, first_player=log["first_player"], leaders=leaders)
    rs = eng.new_game(list(deck_a), list(deck_b), log["seed"], log["first_player"], leaders)
    rs.record_events(True)
    bad = compare(py, rs, "setup")
    for i, adict in enumerate(log["actions"]):
        if bad:
            break
        rules.apply_logged(py, adict)
        try:
            rs.apply_logged(adict)
        except Exception as e:
            return f"rust refused action {i} {adict}: {e}", i
        bad = compare(py, rs, f"action {i} {adict}")
    return bad, len(log["actions"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(ROOT, "results", "human_games", "web"))
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    cards, config, eng = engines()
    games = stale = agree = actions = 0
    for path in sorted(glob.glob(os.path.join(a.dir, "*.jsonl"))):
        with open(path, encoding="utf-8") as fh:
            logs = [json.loads(line) for line in fh if line.strip()]
        for n, log in enumerate(logs):
            games += 1
            name = f"{os.path.basename(path)}#{n}"
            if not replays_today(log, cards):
                stale += 1
                if a.verbose:
                    print(f"  stale  {name}")
                continue
            bad, steps = side_by_side(log, cards, config, eng)
            actions += steps
            if bad:
                print(f"FAIL {name}: {bad}"[:1500], flush=True)
            else:
                agree += 1
                if a.verbose:
                    print(f"  agree  {name} ({steps} actions)")
    replayable = games - stale
    print(f"=== {games} logged games: {stale} no longer replay on today's Python engine; of the {replayable} that do, {agree} agree in Rust ({actions} actions compared)")
    sys.exit(0 if agree == replayable else 1)
