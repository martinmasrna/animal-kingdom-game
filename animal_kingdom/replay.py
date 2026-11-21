"""Replay a logged game (one line of results/human_games/web/*.jsonl) through the engine, with no bot compute: the decks,
the seed and the actions rebuild it move by move.

    .venv/bin/python -m animal_kingdom.replay FILE [--index N]
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional, Sequence

from . import game as rules
from .game import GameState, new_game


def load_logs(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def replay(log: dict) -> tuple[list[dict], Optional[object], GameState]:
    """Re-run one logged game. Returns a step per action (who acted, the action, the food after), the result, and the
    final state."""
    deck_a, deck_b = log["lists"]
    state = new_game(list(deck_a), list(deck_b), log["seed"], first_player=log["first_player"], leaders=log.get("leaders"))
    steps = []
    for adict in log["actions"]:
        actor = adict.get("by") or state.player_to_act()
        rules.apply_logged(state, adict)
        steps.append({"turn": state.turn_counter, "actor": actor, "action": adict, "food": dict(state.food)})
    return steps, rules.is_terminal(state), state


def _desc(a: dict) -> str:
    if a["kind"] == "place":
        kind, where = a["target"]
        return f"RAID {where}'s den with {a['card_id']}" if kind == "hq" else f"place {a['card_id']} -> {where}"
    if a["kind"] == "choice":
        return f"choose {a['choice']}"
    return a["kind"]


def format_trace(log: dict, steps, result) -> str:
    lines = [f"seed={log['seed']}   first={log.get('first_player', '?')}   bots={'/'.join(log.get('bots', []))}",
             f"result: winner={log.get('winner')}  by {log.get('reason')}  in {log.get('turns')} turns", "-" * 78]
    lines += [f"T{s['turn']:>2} {s['actor']}: {_desc(s['action'])}   [food A{s['food']['A']} B{s['food']['B']}]" for s in steps]
    lines.append("-" * 78)
    if result is not None:
        lines.append(f"END: {result.winner} wins by {result.reason}")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> None:
    p = argparse.ArgumentParser(description="Replay and trace a game from a game log.")
    p.add_argument("logfile")
    p.add_argument("--index", type=int, default=0, help="which game in the file (one line each, rematches included)")
    args = p.parse_args(argv)
    log = load_logs(args.logfile)[args.index]
    steps, result, _ = replay(log)
    print(format_trace(log, steps, result))


if __name__ == "__main__":
    main(sys.argv[1:])
