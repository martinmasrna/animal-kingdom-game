"""Replay and trace simulated games from a stored action log — with no bot compute.

Bot-vs-bot games are deterministic: `new_game(decks, seed, map, config)` plus the exact
sequence of actions the bots chose reproduces the game bit-for-bit, including seeded random
effects. So once a run is captured with `./report --log <file>` (one JSONL record per game,
see `write_game_logs`), any game can be replayed by applying its recorded actions straight
through the rules engine — the expensive bot search is bypassed entirely.

Usage:
  python -m animal_kingdom.sim.replay results/ref.jsonl                 # first game in the file
  python -m animal_kingdom.sim.replay results/ref.jsonl --index 3       # the 4th game
  python -m animal_kingdom.sim.replay results/ref.jsonl --deck colony --opponent ramp --seed 7
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Iterable, Optional, Sequence

from ..decks import load_premade_deck
from ..engine import rules
from ..engine.actions import action_from_dict
from ..engine.config import Config
from ..engine.state import GameState, new_game


# ------------------------------------------------------------------ log I/O

def game_log_record(rec, *, map_id: str, bots: tuple[str, str]) -> dict:
    """The JSONL log line for one finished game: metadata + the full action sequence."""
    return {
        "deck_a": rec.deck_a, "deck_b": rec.deck_b, "seed": rec.seed, "map_id": map_id,
        "bots": list(bots), "first_player": rec.first_player,
        "winner": rec.winner, "reason": rec.reason, "turns": rec.turns,
        "actions": list(rec.actions),
    }


def write_game_logs(records: Iterable, path: str, *, map_id: str, bots: tuple[str, str]) -> int:
    """Write one JSONL line per game. Returns the number of games written."""
    from ..recording.writer import JsonlGameWriter
    w = JsonlGameWriter(path)
    n = 0
    try:
        for rec in records:
            w.append(game_log_record(rec, map_id=map_id, bots=bots))
            n += 1
    finally:
        w.close()
    return n


def load_logs(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


# --------------------------------------------------------------- replay core

def regions_controlled(state: GameState) -> dict[str, list[str]]:
    """Which regions each player fully controls (tops every corner) in the current state."""
    out: dict[str, list[str]] = {"A": [], "B": []}
    for rid, region in state.game_map.regions.items():
        tops = [state.top_unit(c) for c in region.corners]
        if all(u is not None for u in tops):
            owners = {u.owner for u in tops}
            if len(owners) == 1:
                out[owners.pop()].append(rid)
    return out


def _board_owners(state: GameState) -> dict[str, str]:
    return {cr: st[-1].owner for cr, st in state.board.items() if st}


def replay(log: dict, *, config: Optional[Config] = None) -> list[dict]:
    """Re-run one logged game by applying its stored actions (no bots). Returns a step list,
    each step diffing state before/after the action (food, region control, board ownership)."""
    state = new_game(load_premade_deck(log["deck_a"]), load_premade_deck(log["deck_b"]),
                     log["seed"], map_id=log.get("map_id", "map_b"), config=config)
    steps: list[dict] = []
    for adict in log["actions"]:
        action = action_from_dict(adict)
        actor = state.player_to_act()
        food0, reg0, own0 = dict(state.food), regions_controlled(state), _board_owners(state)
        rules.apply_action(state, action)
        food1, reg1, own1 = dict(state.food), regions_controlled(state), _board_owners(state)
        changed = {cr: (own0.get(cr), own1.get(cr))
                   for cr in set(own0) | set(own1) if own0.get(cr) != own1.get(cr)}
        steps.append({
            "turn": state.turn_counter, "actor": actor, "action": adict,
            "food_delta": {p: food1[p] - food0[p] for p in ("A", "B") if food1[p] != food0[p]},
            "regions_gained": {p: sorted(set(reg1[p]) - set(reg0[p])) for p in ("A", "B")
                               if set(reg1[p]) - set(reg0[p])},
            "regions_lost": {p: sorted(set(reg0[p]) - set(reg1[p])) for p in ("A", "B")
                             if set(reg0[p]) - set(reg1[p])},
            "board_changes": changed,
        })
    result = rules.is_terminal(state)
    return steps, result, state


# ---------------------------------------------------------------- formatting

def _action_desc(a: dict) -> str:
    kind = a["kind"]
    if kind == "draw":
        return "draw"
    if kind == "place":
        tgt = a["target"]
        if tgt[0] == "hq":
            return f"PLACE {a['card_id']} -> ENEMY HQ ({tgt[1]})  *** CAPTURE ***"
        return f"place {a['card_id']} -> {tgt[1]}"
    if kind == "choice":
        return f"choose {a['choice']}"
    return str(a)


def format_trace(log: dict, steps, result, *, config: Optional[Config] = None) -> str:
    lines = [
        f"{log['deck_a']} (A) vs {log['deck_b']} (B)   seed={log['seed']}   "
        f"map={log.get('map_id','map_b')}   first={log.get('first_player','?')}   "
        f"bots={'/'.join(log.get('bots', []))}",
        f"result: winner={log.get('winner')}  by {log.get('reason')}  in {log.get('turns')} turns",
        "-" * 78,
    ]
    for s in steps:
        line = f"T{s['turn']:>2} {s['actor']}: {_action_desc(s['action'])}"
        ann = []
        if s["food_delta"]:
            ann.append("food " + " ".join(f"{p}{d:+d}" for p, d in s["food_delta"].items()))
        for cr, (o0, o1) in s["board_changes"].items():
            if o0 is None:
                ann.append(f"{cr}=+{o1}")
            elif o1 is None:
                ann.append(f"{cr}:{o0}->∅")
            else:
                ann.append(f"{cr}:{o0}->{o1}")
        for p, rs in s["regions_gained"].items():
            ann.append(f"{p} takes {','.join(rs)}")
        for p, rs in s["regions_lost"].items():
            ann.append(f"{p} loses {','.join(rs)}")
        if ann:
            line += "   [" + " | ".join(ann) + "]"
        lines.append(line)
    lines.append("-" * 78)
    if result is not None:
        lines.append(f"END: {result.winner} wins by {result.reason}")
    return "\n".join(lines)


# --------------------------------------------------------------------- CLI

def _select(logs: list[dict], args) -> list[dict]:
    if args.deck or args.opponent or args.seed is not None:
        hits = [g for g in logs
                if (args.deck is None or args.deck in g["deck_a"])
                and (args.opponent is None or args.opponent in g["deck_b"])
                and (args.seed is None or g["seed"] == args.seed)]
        return hits[: args.limit]
    return logs[args.index: args.index + args.limit]


def main(argv: Optional[Sequence[str]] = None) -> None:
    p = argparse.ArgumentParser(description="Replay/trace games from a --log JSONL file.")
    p.add_argument("logfile")
    p.add_argument("--index", type=int, default=0, help="which game (by position) to trace")
    p.add_argument("--limit", type=int, default=1, help="how many games to trace")
    p.add_argument("--deck", default=None, help="filter: substring of deck_a")
    p.add_argument("--opponent", default=None, help="filter: substring of deck_b")
    p.add_argument("--seed", type=int, default=None, help="filter: exact seed")
    args = p.parse_args(argv)

    logs = load_logs(args.logfile)
    selected = _select(logs, args)
    if not selected:
        raise SystemExit("no games matched the selection")
    for i, log in enumerate(selected):
        if i:
            print("\n" + "=" * 78 + "\n")
        steps, result, _ = replay(log)
        print(format_trace(log, steps, result))


if __name__ == "__main__":
    main(sys.argv[1:])
