"""Prove or refute a puzzle's forced den capture, and check puzzle files (the search: `animal_kingdom/puzzles.py`).

Usage:
  .venv/bin/python tools/puzzles/solve.py solve FILE [--cap N]       # forced or not, every winning first turn and the reply
  .venv/bin/python tools/puzzles/solve.py check [FILE ...]           # every file in data/puzzles when none is named
  .venv/bin/python tools/puzzles/solve.py write FILE [--first K]     # fill solution (winning first turn K, default 0)
                                                                      # and main_line from the search
  .venv/bin/python tools/puzzles/solve.py from-log LOG LINE INDEX --id ID [--turns N] [--out FILE]
        # a recorded position (game log file, its line, the action index before which the actor is to move) as a
        # puzzle: the actor becomes A, the decks are emptied, the hands kept, stacks in full
  .venv/bin/python tools/puzzles/solve.py show FILE                  # the board as text (A's den at the bottom)

Exact search over the solver's whole turn (every action and every choice, free placements and passes included), every
whole-turn defender reply, and the solver's second turn; past the node cap it says "unproven" instead of guessing.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from animal_kingdom import puzzles as P  # noqa: E402
from animal_kingdom.engine.strength import effective_strength  # noqa: E402


def _load(path: str) -> dict:
    if not os.path.exists(path) and os.path.exists(os.path.join(P.PUZZLE_DIR, path + ".json")):
        path = os.path.join(P.PUZZLE_DIR, path + ".json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _path(path: str) -> str:
    if not os.path.exists(path) and os.path.exists(os.path.join(P.PUZZLE_DIR, path + ".json")):
        return os.path.join(P.PUZZLE_DIR, path + ".json")
    return path


def describe(a: dict, state=None) -> str:
    """One action in words."""
    k = a["kind"]
    if k == "place":
        t = "B's den" if a["target"][0] == "hq" else a["target"][1]
        return f"{'(free) ' if a.get('sub') else ''}{a['card_id']} -> {t}"
    if k == "roam":
        t = "B's den" if a["target"][0] == "hq" else a["target"][1]
        return f"roam {a['from']} -> {t}"
    if k == "choice":
        c = a["choice"]
        if state is not None and isinstance(c, int):
            for cr, st in state.board.items():
                for u in st:
                    if u.iid == c:
                        return f"choose {u.card_id} ({u.owner}) on {cr}"
            for p, h in state.hands.items():
                for u in h:
                    if u.iid == c:
                        return f"choose {u.card_id} in {p}'s hand"
        return f"choose {c}"
    return k


def board_text(puzzle: dict) -> str:
    """The board as text: B's den on top, A's at the bottom; + A's animal, - B's, strength after the name."""
    state = P.build(puzzle)
    names = {cid: c.name for cid, c in state.cards.items()}
    rows = ["            [B's den]"]
    for rank in range(5, 0, -1):
        cells = []
        for lane in (1, 2, 3):
            st = state.board.get(f"{rank},{lane}")
            if not st:
                cells.append(".")
                continue
            parts = []
            for u in st:
                sign = "+" if u.owner == "A" else "-" if u.owner == "B" else "~"
                parts.append(f"{sign}{names[u.card_id]} {effective_strength(state, u)}")
            cells.append(" / ".join(parts))
        rows.append(f"{rank}  " + " | ".join(f"{c:<22}" for c in cells))
    rows.append("            [A's den]")
    rows.append("   lanes: 1 (left) | 2 | 3 (right); a stack reads bottom / ... / top")
    hand = lambda p: ", ".join(f"{names[u.card_id]} {effective_strength(state, u)}" for u in state.hands[p]) or "(empty)"
    rows.append(f"A's hand: {hand('A')}")
    rows.append(f"B's hand: {hand('B')}")
    rows.append(f"Food: A {state.food['A']}, B {state.food['B']}")
    return "\n".join(rows)


def cmd_solve(args) -> int:
    pz = _load(args.file)
    t0 = time.time()
    rep = P.solve(pz, args.cap)
    state = P.build(pz)
    print(f"{pz.get('id')}: {rep['status']} in {pz['turns']} ({rep.get('nodes')} nodes, {time.time() - t0:.1f}s,"
          f" {rep.get('first_turns', '?')} distinct first turns)")
    for i, w in enumerate(rep.get("winning_first_turns", [])):
        print(f"  [{i}] " + "; ".join(describe(a, state) for a in w["line"]) + f"   ({w['orders']} orders)")
        if w["reply"]:
            after = P.play_line(state, w["line"])
            print("      best reply: " + "; ".join(describe(a, after) for a in w["reply"]))
    return 0 if rep["status"] == "forced" else 1


def cmd_check(args) -> int:
    files = args.files or [os.path.join(P.PUZZLE_DIR, f"{i}.json") for i in P.all_ids()]
    bad = 0
    for f in files:
        pz = _load(f)
        t0 = time.time()
        probs = P.check(pz, args.cap)
        rep = None if probs else P.solve(pz, args.cap)
        n = len(rep["winning_first_turns"]) if rep else "?"
        print(f"{'ok ' if not probs else 'BAD'} {pz.get('id', f)}: {n} winning first turn(s), {time.time() - t0:.1f}s")
        for p in probs:
            print(f"    {p}")
        bad += bool(probs)
    return 1 if bad else 0


def cmd_write(args) -> int:
    path = _path(args.file)
    pz = _load(path)
    rep = P.solve(pz, args.cap)
    if rep["status"] != "forced":
        print(f"not written: {rep['status']}")
        return 1
    w = rep["winning_first_turns"][args.first]
    pz["solution"] = w["line"]
    pz["main_line"] = P.main_line(pz)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(dumps(pz))
    print(f"wrote {path}: {len(rep['winning_first_turns'])} winning first turn(s)")
    return 0


def dumps(pz: dict) -> str:
    """A puzzle file, one board crossroad and one action a line, the way a person reads it."""
    order = ["id", "title", "theme", "to_move", "turns", "order", "board", "hands", "food", "hint", "why", "source",
             "solution", "main_line"]
    keys = [k for k in order if k in pz] + [k for k in pz if k not in order]
    lines = ["{"]
    for i, k in enumerate(keys):
        v = pz[k]
        end = "," if i < len(keys) - 1 else ""
        if k == "board":
            inner = [f'    {json.dumps(cr)}: {json.dumps(v[cr])}' for cr in sorted(v)]
            lines.append(f'  "board": {{\n' + ",\n".join(inner) + f"\n  }}{end}")
        elif k in ("solution", "main_line") and v:
            inner = [f"    {json.dumps(a)}" for a in v]
            lines.append(f'  {json.dumps(k)}: [\n' + ",\n".join(inner) + f"\n  ]{end}")
        else:
            lines.append(f"  {json.dumps(k)}: {json.dumps(v)}{end}")
    lines.append("}")
    return "\n".join(lines) + "\n"


def cmd_from_log(args) -> int:
    from animal_kingdom.decks import load_premade_deck
    from animal_kingdom.engine import rules
    from animal_kingdom.engine.actions import SKIP, ChoiceAction
    from animal_kingdom.engine.config import Config
    from animal_kingdom.engine.state import new_game
    from animal_kingdom.web.renamed import renamed
    with open(args.log, encoding="utf-8") as fh:
        log = renamed(json.loads(fh.readlines()[args.line]))
    deck_a, deck_b = log.get("lists") or (load_premade_deck(log["deck_a"]), load_premade_deck(log["deck_b"]))
    state = new_game(list(deck_a), list(deck_b), log["seed"], map_id=log.get("map_id", "map_b"),
                     config=Config.default().for_log(log), first_player=log["first_player"])
    for idx, adict in enumerate(log["actions"]):
        while state.pending is not None and state.effect_stack[-1].get("op") == "mulligan" and adict["kind"] != "choice":
            rules.apply_action(state, ChoiceAction(SKIP))
        if idx == args.index:
            break
        rules.apply_logged(state, adict)
    me = state.current
    flip = me == "B"
    seat = (lambda o: o if o not in ("A", "B") else ({"A": "B", "B": "A"}[o] if flip else o))
    cr_of = (lambda cr: f"{6 - int(cr.split(',')[0])},{cr.split(',')[1]}" if flip else cr)
    board = {}
    for cr, st in state.board.items():
        if st:
            board[cr_of(cr)] = [{"card": u.card_id, "owner": seat(u.owner),
                                 **({"counter": u.strength_counter} if u.strength_counter else {})} for u in st]
    hands = {seat(p): [u.card_id if not u.strength_counter else {"card": u.card_id, "counter": u.strength_counter}
                       for u in state.hands[p]] for p in ("A", "B")}
    pz = {"id": args.id, "title": args.id, "theme": "", "to_move": "A", "turns": args.turns, "board": board,
          "hands": hands, "food": {seat(p): state.food[p] for p in ("A", "B")}, "hint": "", "why": "",
          "source": f"{os.path.relpath(args.log, ROOT)} line {args.line}, action {args.index}"
                    + (" (seats swapped)" if flip else ""),
          "solution": []}
    if state.scheduled:
        print(f"warning: {len(state.scheduled)} timed effect(s) on the board are dropped", file=sys.stderr)
    text = dumps(pz)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    print(text)
    return 0


def cmd_show(args) -> int:
    print(board_text(_load(args.file)))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("solve"); s.add_argument("file"); s.add_argument("--cap", type=int, default=2_000_000)
    s.set_defaults(fn=cmd_solve)
    c = sub.add_parser("check"); c.add_argument("files", nargs="*"); c.add_argument("--cap", type=int, default=2_000_000)
    c.set_defaults(fn=cmd_check)
    w = sub.add_parser("write"); w.add_argument("file"); w.add_argument("--first", type=int, default=0)
    w.add_argument("--cap", type=int, default=2_000_000); w.set_defaults(fn=cmd_write)
    f = sub.add_parser("from-log"); f.add_argument("log"); f.add_argument("line", type=int); f.add_argument("index", type=int)
    f.add_argument("--id", required=True); f.add_argument("--turns", type=int, default=1); f.add_argument("--out")
    f.set_defaults(fn=cmd_from_log)
    sh = sub.add_parser("show"); sh.add_argument("file"); sh.set_defaults(fn=cmd_show)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
