"""Mine the recorded human games for positions where a den capture was available within one turn.

The raw material for a daily puzzle. Analysis only: it replays logs through the rules engine and changes nothing.

Usage:
  .venv/bin/python tools/puzzles/mine.py                                  # every game under results/human_games/
  .venv/bin/python tools/puzzles/mine.py --out tools/puzzles/forced_captures-2026-11-05.jsonl --workers 4
  .venv/bin/python tools/puzzles/mine.py --limit 50 --worlds 4            # a quick sample
  .venv/bin/python tools/puzzles/mine.py --sample 0.5 --sample-seed 1     # a random half of the games

For every replayable game (old card ids are first read as their successors with the web replayer's
`web/renamed.py`; a log whose cards have changed since may still fail to replay: EngineError, KeyError or ValueError,
counted and skipped) and every position where a player is about to take the first action of their turn
(nothing resolving, no action yet taken this turn), it searches for a line of at most two turn actions (draw, place,
roam), with every sub-choice the engine asks for along the way expanded, that ends in that player capturing the
opponent's den (`rules.is_terminal` → reason hq_capture, winner the actor).

Honesty (the actor's own seat only): the search never touches the true state's hidden information. It runs on a
world re-sampled from the actor's view (`bots.determinize`: the actor's deck reshuffled, the opponent's hand and deck
re-dealt from the pool), and every line it finds is then replayed on `--worlds` more independently sampled worlds; a
line counts only if it is legal and captures in all of them. So a line that needs a particular draw or a particular
card in the opponent's hand survives only if every sampled outcome works (a sample, not a proof over all draws). A
sub-choice the opponent makes in the middle of the line (rare) is treated as adversarial: every option must still
lead to the capture with the same continuation.

Search bounds: both turn actions are enumerated in full, with every sub-choice (`--fast` restricts the second
action to den captures, a placement or roam onto the enemy den, and the choices they open). Only turn actions count
toward the two (draw, place, roam); sub-choices, and placements an effect grants while it resolves, are free and are
marked "sub" in the output lines. A per-position node cap (`--node-cap`) stops pathological
expansions: such a position is searched again with the second action restricted to den captures, and counted.

Output: one JSONL line per position with a capture (`captured`: the player took the den that turn; `turn_result`:
how that turn ended the game, if it did, e.g. a food win instead; `turn_unfinished`: the log stops during that
turn, a concession or an abandoned game; `game_result`: the log's own result), plus a `<out>.summary.json` with the counts.
"""
from __future__ import annotations

import argparse
import glob
import json
import multiprocessing as mp
import os
import random
import sys
import time
from typing import Optional

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from animal_kingdom.bots.determinize import determinize  # noqa: E402
from animal_kingdom.decks import load_premade_deck  # noqa: E402
from animal_kingdom.engine import rules  # noqa: E402
from animal_kingdom.engine.actions import SKIP, ChoiceAction, PlaceAction, RoamAction  # noqa: E402
from animal_kingdom.engine.config import Config  # noqa: E402
from animal_kingdom.engine.state import EngineError, GameState, new_game, other_player  # noqa: E402
from animal_kingdom.engine.strength import effective_strength  # noqa: E402
from animal_kingdom.web.renamed import renamed  # noqa: E402  (old card ids read as their successors)

OPP = {"kind": "opp_choice"}   # marker in a line: the opponent picks here, every option must still work


FULL = [True]   # enumerate the second action in full (False: den captures only, --fast)


class _Sub:
    """An action taken inside an effect's resolution (a sub-choice, or a free placement a Roar grants): no turn action."""
    __slots__ = ("a",)

    def __init__(self, a):
        self.a = a


class _Cap(Exception):
    pass


def _is_capture_for(state: GameState, me: str) -> Optional[bool]:
    """True: me captured the den; False: the game ended otherwise; None: still going."""
    r = rules.is_terminal(state)
    if r is None:
        return None
    return r.winner == me and r.reason == "hq_capture"


def _key(a) -> str:
    return json.dumps(a.to_dict(), sort_keys=True)


def _search(s: GameState, me: str, moves: int, ctr: list, cap: int) -> list[list]:
    """Every capturing line from `s` (lists of Action / OPP), `moves` turn actions already used."""
    done = _is_capture_for(s, me)
    if done is not None:
        return [[]] if done else []
    if s.current != me:
        return []
    legal = rules.legal_actions(s)
    out: list[list] = []
    if s.pending is not None:
        actor = s.player_to_act()
        if actor != me:                                   # an opponent's sub-choice: all of them must still work
            first = None
            for a in legal:
                ctr[0] += 1
                if ctr[0] > cap:
                    raise _Cap
                nxt = s.clone()
                rules.apply_action(nxt, a, validate=False)
                sub = _search(nxt, me, moves, ctr, cap)
                if not sub:
                    return []
                if first is None:
                    first = sub
            return [[OPP] + l for l in (first or [])]
        for a in legal:
            ctr[0] += 1
            if ctr[0] > cap:
                raise _Cap
            nxt = s.clone()
            rules.apply_action(nxt, a, validate=False)
            out.extend([_Sub(a)] + l for l in _search(nxt, me, moves, ctr, cap))
        return out
    if moves >= 2:
        return []
    if moves == 1 and not FULL[0]:
        legal = [a for a in legal if isinstance(a, (PlaceAction, RoamAction)) and a.is_hq_capture]
    for a in legal:
        ctr[0] += 1
        if ctr[0] > cap:
            raise _Cap
        nxt = s.clone()
        rules.apply_action(nxt, a, validate=False)
        out.extend([a] + l for l in _search(nxt, me, moves + 1, ctr, cap))
    return out


def _follows(s: GameState, me: str, line: list) -> bool:
    """Whether `line` is legal and captures in world `s` (validated; opponent choices all tried)."""
    for i, a in enumerate(line):
        if _is_capture_for(s, me) is not None or s.current != me:
            return False
        if a is OPP:
            if s.pending is None or s.player_to_act() == me:
                return False
            for o in rules.legal_actions(s):
                nxt = s.clone()
                rules.apply_action(nxt, o, validate=False)
                if not _follows(nxt, me, line[i + 1:]):
                    return False
            return True
        if s.pending is not None and s.player_to_act() != me:
            return False
        if isinstance(a, _Sub) != (s.pending is not None):
            return False
        if isinstance(a, _Sub):
            a = a.a
        try:
            rules.apply_action(s, a)
        except EngineError:
            return False
    return _is_capture_for(s, me) is True


def _turn_moves(line: list) -> int:
    return sum(1 for a in line if a is not OPP and not isinstance(a, _Sub))


def _placements(line: list) -> int:
    return sum(1 for a in line if isinstance(a.a if isinstance(a, _Sub) else a, (PlaceAction, RoamAction)))


def _line_dicts(line: list) -> list[dict]:
    """The line as action dicts; one taken inside an effect's resolution is marked "sub" (it costs no action)."""
    return [dict(OPP) if a is OPP else dict(a.a.to_dict(), sub=True) if isinstance(a, _Sub) else a.to_dict()
            for a in line]


def _snapshot(state: GameState, me: str) -> dict:
    """The position in public terms plus the actor's hand: enough to write the puzzle up."""
    board = {}
    for cr, st in sorted(state.board.items()):
        if st:
            u = st[-1]
            board[cr] = {"card": u.card_id, "owner": u.owner, "str": effective_strength(state, u),
                         "stack": len(st)}
    gm = state.game_map
    return {
        "turn": state.turn_counter,
        "hand": [u.card_id for u in state.hands[me]],
        "opp_hand_size": len(state.hands[other_player(me)]),
        "deck_sizes": {p: len(state.decks[p]) for p in ("A", "B")},
        "food": dict(state.food),
        "board": board,
        "den_front": {p: sorted(gm.hq_front(p)) for p in ("A", "B")},
    }


def mine_game(task: tuple) -> dict:
    path, lineno, log, worlds_n, node_cap, full = task
    FULL[0] = full
    out = {"path": path, "line": lineno, "replayed": False, "error": None, "positions": 0,
           "truncated": 0, "search_errors": [], "found": []}
    log = renamed(log)
    try:
        deck_a, deck_b = log.get("lists") or (load_premade_deck(log["deck_a"]), load_premade_deck(log["deck_b"]))
        state = new_game(list(deck_a), list(deck_b), log["seed"], map_id=log.get("map_id", "map_b"),
                         config=Config.default().for_log(log), first_player=log["first_player"])
    except Exception as e:  # noqa: BLE001 - a log whose cards have changed
        out["error"] = f"setup {type(e).__name__}: {e}"[:200]
        return out
    bots = list(log.get("bots") or [])
    seat_kind = {p: (bots[i] if i < len(bots) else "unknown") for i, p in enumerate(("A", "B"))}
    actions = log["actions"]
    seen_turns: set = set()
    open_pos: list[dict] = []            # found positions whose turn has not finished yet in the real game
    rng = random.Random(f"{path}:{lineno}")
    try:
        for idx, adict in enumerate(actions):
            while state.pending is not None and state.effect_stack[-1].get("op") == "mulligan" \
                    and adict["kind"] != "choice":
                rules.apply_action(state, ChoiceAction(SKIP))
            if (state.pending is None and not state.effect_stack and state.actions_taken_this_turn == 0
                    and rules.is_terminal(state) is None and state.turn_counter not in seen_turns
                    and adict["kind"] != "choice"):
                seen_turns.add(state.turn_counter)
                me = state.current
                out["positions"] += 1
                try:
                    rec = _mine_position(state, me, worlds_n, node_cap, rng)
                except Exception as e:  # noqa: BLE001 - an engine error inside the search, not the replay
                    out["search_errors"].append(f"{idx} {type(e).__name__}: {e}"[:160])
                    rec = None
                if isinstance(rec, dict) and rec.pop("truncated", False):
                    out["truncated"] += 1
                if isinstance(rec, dict) and rec.get("_none"):
                    rec = None
                if rec is not None:
                    rec["search_complete"] = rec.get("search_complete", True)
                    rec.update(path=path, line=lineno, action_index=idx, player=me, seat=seat_kind[me],
                               human=seat_kind[me] == "human", deck=log["deck_a"] if me == "A" else log["deck_b"],
                               opp_deck=log["deck_b"] if me == "A" else log["deck_a"],
                               map_id=log.get("map_id", "map_b"), turn_counter=state.turn_counter,
                               actual_first_action=adict, _turn=state.turn_counter)
                    open_pos.append(rec)
            rules.apply_logged(state, adict)
            # close positions whose turn is over
            res = rules.is_terminal(state)
            for rec in list(open_pos):
                if res is not None or state.turn_counter != rec["_turn"]:
                    ended = res is not None and state.turn_counter == rec["_turn"]
                    rec["captured"] = bool(ended and res.winner == rec["player"] and res.reason == "hq_capture")
                    rec["turn_result"] = [res.winner, res.reason] if ended else None
                    rec["turn_unfinished"] = False
                    open_pos.remove(rec)
                    out["found"].append(rec)
        for rec in open_pos:             # game log ended mid-turn (resigned, abandoned)
            res = rules.is_terminal(state)
            rec["captured"] = bool(res is not None and res.winner == rec["player"] and res.reason == "hq_capture")
            rec["turn_result"] = [res.winner, res.reason] if res is not None else None
            rec["turn_unfinished"] = res is None    # the log stops mid-turn: a concession, or an abandoned game
            out["found"].append(rec)
    except (EngineError, KeyError, ValueError) as e:
        out["error"] = f"replay {type(e).__name__}: {e}"[:200]
        out["found"] = []
        return out
    for rec in out["found"]:
        rec.pop("_turn", None)
        rec["game_result"] = [log.get("winner"), log.get("reason")]
    out["replayed"] = True
    return out


def _mine_position(state: GameState, me: str, worlds_n: int, node_cap: int, rng: random.Random):
    w0 = determinize(state, me, rng)
    ctr = [0]
    truncated = False
    try:
        lines = _search(w0, me, 0, ctr, node_cap)
    except _Cap:                         # too wide: fall back to den captures as the second action
        truncated, full = True, FULL[0]
        FULL[0] = False
        try:
            ctr[0] = 0
            lines = _search(w0, me, 0, ctr, node_cap * 5)
        except _Cap:
            lines = []
        finally:
            FULL[0] = full
    if not lines:
        return {"truncated": True, "_none": True} if truncated else None
    uniq: dict[str, list] = {}
    for l in lines:
        uniq.setdefault(json.dumps(_line_dicts(l), sort_keys=True), l)
    others = [determinize(state, me, rng) for _ in range(worlds_n)]
    good = [l for l in uniq.values() if all(_follows(w.clone(), me, l) for w in others)]
    if not good:
        return {"truncated": True, "_none": True} if truncated else None
    good.sort(key=lambda l: (_turn_moves(l), len(l)))
    shortest = _turn_moves(good[0])
    return {
        "shortest_actions": shortest,
        "shortest_line": _line_dicts(good[0]),
        "shortest_placements": _placements(good[0]),
        "n_lines": len(good),
        "n_lines_shortest": sum(1 for l in good if _turn_moves(l) == shortest),
        "n_lines_unverified": len(uniq) - len(good),
        "truncated": truncated, "search_complete": not truncated,
        "position": _snapshot(state, me),
    }


def _tasks(root: str, limit: Optional[int], sample: float, sample_seed: int, worlds_n: int, node_cap: int,
           full: bool = True):
    files = sorted(glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True))
    tasks = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            for i, line in enumerate(fh):
                if line.strip():
                    tasks.append((os.path.relpath(f, ROOT), i, json.loads(line), worlds_n, node_cap, full))
    if sample < 1.0:
        tasks = random.Random(sample_seed).sample(tasks, int(len(tasks) * sample))
    if limit:
        tasks = tasks[:limit]
    return files, tasks


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--root", default=os.path.join(ROOT, "results", "human_games"))
    p.add_argument("--out", default=os.path.join(ROOT, "tools", "puzzles", "forced_captures.jsonl"))
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--worlds", type=int, default=4, help="extra sampled worlds each line must also capture in")
    p.add_argument("--node-cap", type=int, default=20000, help="search nodes per position before giving up")
    p.add_argument("--fast", action="store_true", help="second action: den captures only (see Search bounds)")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--sample", type=float, default=1.0, help="fraction of games to mine")
    p.add_argument("--sample-seed", type=int, default=0)
    args = p.parse_args(argv)

    files, tasks = _tasks(args.root, args.limit, args.sample, args.sample_seed, args.worlds, args.node_cap,
                          not args.fast)
    t0 = time.time()
    summary = {"files": len(files), "games": len(tasks), "replayed": 0, "skipped": 0, "skip_reasons": {},
               "positions": 0, "truncated": 0, "search_errors": 0, "found": 0, "worlds": args.worlds, "node_cap": args.node_cap,
               "sample": args.sample, "full_second_action": not args.fast}
    found: list[dict] = []
    with mp.Pool(args.workers) as pool:
        for n, r in enumerate(pool.imap_unordered(mine_game, tasks, chunksize=2), 1):
            if r["replayed"]:
                summary["replayed"] += 1
                summary["positions"] += r["positions"]
                summary["truncated"] += r["truncated"]
                summary["search_errors"] += len(r["search_errors"])
                found.extend(r["found"])
            else:
                summary["skipped"] += 1
                k = r["error"].split(":")[0]
                summary["skip_reasons"][k] = summary["skip_reasons"].get(k, 0) + 1
            if n % 100 == 0:
                print(f"{n}/{len(tasks)} games, {len(found)} positions found, {time.time() - t0:.0f}s",
                      file=sys.stderr, flush=True)
    found.sort(key=lambda r: (r["path"], r["line"], r["action_index"]))
    summary["found"] = len(found)
    summary["seconds"] = round(time.time() - t0, 1)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        for r in found:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    with open(os.path.splitext(args.out)[0] + ".summary.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1, sort_keys=True)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
