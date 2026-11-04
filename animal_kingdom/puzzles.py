"""Puzzles: a fixed position, both hands face up, both decks empty, the solver (seat A) to move, and a den capture
forced within N of the solver's turns (N is 1 or 2).

Forced means every legal reply of the defender (seat B) still loses within N: a puzzle can never be solved by a
defender's mistake. There is no chance in a puzzle: no card whose text says "random", and the search refuses any
position where an effect draws on the game's random stream (`ChanceError`). The decks are empty, so a draw yields
nothing; the engine offers no draw from an empty deck, and ending the turn early (a pass, at any point of a turn) is
the same move, so both players may pass whenever nothing is resolving.

A puzzle file is `data/puzzles/<id>.json`:

    id, title, theme, to_move ("A"), turns (N),
    board: crossroad -> [{card, owner[, counter]}, ...] bottom to top (map_b),
    hands: {A: [card, ...], B: [card, ...]}, food: {A: n, B: n},
    solution: the solver's first turn, the engine's action dicts (choices included),
    main_line: the whole line the client plays when the solver follows the solution (the solver's turns and the
               defender's replies the search picks: [{"by": seat, ...action}, ...]),
    hint: one sentence a player may ask for, why: the idea in one sentence (for Martin only).

The solver is an exact AND/OR search over every decision point (every action, every choice, free placements and
passes included), with a transposition table and a node cap: past the cap it reports "unproven", never a guess.
`tools/puzzles/solve.py` is its command line (solve, check).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, replace
from typing import Optional

from .engine import rules
from .engine.actions import SKIP, Action, ChoiceAction, PassAction, PlaceAction, RoamAction, action_from_dict
from .engine.cards import load_cards
from .engine.config import Config
from .engine.maps import load_map
from .engine.state import GameState, Rng, UnitInstance

SOLVER, DEFENDER = "A", "B"
# AK_PUZZLE_DIR: another folder of puzzle files (a test server's fixtures)
PUZZLE_DIR = os.environ.get("AK_PUZZLE_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "puzzles")
FIRST_TURN = 2          # the position's turn_counter: past the first player's one-action first turn, A to move
_CARDS = None


def cards():
    global _CARDS
    if _CARDS is None:
        _CARDS = load_cards()
    return _CARDS


def config() -> Config:
    """No mulligan; everything else as in a real game."""
    return replace(Config.default(), mulligan=False)


# ---------------------------------------------------------------------------------------------- the format

def load(puzzle_id: str) -> dict:
    with open(os.path.join(PUZZLE_DIR, f"{puzzle_id}.json"), encoding="utf-8") as fh:
        return json.load(fh)


def all_ids() -> list[str]:
    if not os.path.isdir(PUZZLE_DIR):
        return []
    return sorted(f[:-5] for f in os.listdir(PUZZLE_DIR) if f.endswith(".json"))


def all_puzzles() -> list[dict]:
    """Every puzzle, in the order a player meets them: turns, then the file's `order`, then id."""
    ps = [load(i) for i in all_ids()]
    return sorted(ps, key=lambda p: (p.get("turns", 1), p.get("order", 99), p["id"]))


def build(puzzle: dict) -> GameState:
    """The puzzle's position as a game state: board bottom to top, hands as listed, decks empty, A to move."""
    reg = cards()
    state = GameState(load_map("map_b"), reg, config(), board={}, hands={"A": [], "B": []},
                      decks={"A": [], "B": []}, remove_pile=[], food={p: int(puzzle.get("food", {}).get(p, 0)) for p in "AB"},
                      current=SOLVER, first_player=SOLVER, turn_counter=FIRST_TURN, rng=Rng(0))
    for cr in sorted(puzzle.get("board", {})):
        for u in puzzle["board"][cr]:
            if u["card"] not in reg:
                raise ValueError(f"unknown card {u['card']!r} on {cr}")
            inst = UnitInstance(u["card"], u["owner"], state.new_iid(), placed_on_turn=0,
                                strength_counter=int(u.get("counter", 0)),
                                retaliation_used=bool(u.get("spent", False)))
            state.stamp_played(inst)
            state.board.setdefault(cr, []).append(inst)
    for p in "AB":
        for c in puzzle.get("hands", {}).get(p, []):
            cid, counter = (c, 0) if isinstance(c, str) else (c["card"], int(c.get("counter", 0)))
            if cid not in reg:
                raise ValueError(f"unknown card {cid!r} in {p}'s hand")
            state.hands[p].append(UnitInstance(cid, p, state.new_iid(), strength_counter=counter))
    for p in "AB":
        state.ensure_mates(p)
    state.events.clear()
    return state


def position_problems(puzzle: dict) -> list[str]:
    """What makes the position unfit for a puzzle: unknown cards, an illegal board, a card that brings chance."""
    out = []
    reg = cards()
    gm = load_map("map_b")
    if puzzle.get("to_move", "A") != "A":
        out.append("to_move must be A")
    if puzzle.get("turns") not in (1, 2):
        out.append("turns must be 1 or 2")
    used = []
    for cr, stack in puzzle.get("board", {}).items():
        if cr not in gm.crossroads:
            out.append(f"{cr} is not a crossroad of map_b")
        if not stack:
            out.append(f"{cr}: an empty stack")
        for u in stack:
            if u.get("owner") not in ("A", "B", "wild"):
                out.append(f"{cr}: owner {u.get('owner')!r}")
            used.append(u.get("card"))
    for p in "AB":
        hand = puzzle.get("hands", {}).get(p, [])
        if len(hand) > 10:
            out.append(f"{p}'s hand holds more than ten cards")
        used += [c if isinstance(c, str) else c["card"] for c in hand]
    for cid in used:
        card = reg.get(cid)
        if card is None:
            out.append(f"unknown card {cid!r}")
        elif "random" in card.text.lower():
            out.append(f"{card.name} ({cid}): its text says random")
        elif card.status not in ("collectible", "token"):
            out.append(f"{card.name} ({cid}) is {card.status}, not in the collection")
    try:
        s = build(puzzle)
    except Exception as e:  # noqa: BLE001
        return out + [f"cannot build: {e}"]
    if rules.is_terminal(s) is not None:
        out.append("the game is already over")
    for p in "AB":
        if s.food[p] >= s.game_map.win_food:
            out.append(f"{p} is already at the food win")
    return out


# ---------------------------------------------------------------------------------------------- the search

class Unproven(Exception):
    """The node cap was reached before the answer was known."""


class ChanceError(Exception):
    """An effect drew on the random stream: the position has chance in it."""


def moves(state: GameState) -> list[Action]:
    """Every decision open to the player to act: the legal actions, and ending the turn early when nothing resolves."""
    acts = list(rules.legal_actions(state))
    if rules.can_pass(state) and rules.is_terminal(state) is None:
        acts.append(PassAction())
    return acts


def step(state: GameState, action: Action) -> GameState:
    """`action` applied to a copy of `state`. Raises ChanceError if it drew on the random stream."""
    nxt = state.clone()
    rules.apply_action(nxt, action, validate=False)
    if nxt.rng._live:            # a clone's stream wakes only when something draws from it (state.Rng)
        # A draw that can't change anything (a pick among identical copies, a shuffle of one card) is no chance: the
        # same action under other streams must end on the same position.
        want = turn_key(nxt)
        for seed in (1, 2, 3, 4):
            alt = state.clone()
            alt.rng = Rng(seed)
            rules.apply_action(alt, action, validate=False)
            if turn_key(alt) != want:
                raise ChanceError(f"{action.to_dict()} has more than one outcome (the random stream decides)")
    return nxt


def _key(state: GameState) -> str:
    """The exact position (iids and play order included): a transposition table key."""
    d = state.to_dict()
    d.pop("rng", None)
    return json.dumps(d, sort_keys=True, separators=(",", ":"))


def turn_key(state: GameState) -> str:
    """The position a turn ends on, blind to the order it was reached in (iids and play order relabelled by place)."""
    label = {}
    for cr, st in state.board.items():
        for i, u in enumerate(st):
            label[u.iid] = f"{cr}#{i}"
    for p, h in state.hands.items():
        for u in h:
            label[u.iid] = f"hand{p}:{u.card_id}"

    def relabel(v, k=""):
        if isinstance(v, dict):
            return {kk: relabel(vv, kk) for kk, vv in v.items()}
        if isinstance(v, list):
            return [relabel(x, k) for x in v]
        if isinstance(v, int) and not isinstance(v, bool) and "iid" in k:
            return label.get(v, "gone")
        return v

    d = state.to_dict()
    for k in ("rng", "next_iid", "play_seq"):
        d.pop(k, None)
    d["board"] = {cr: [{kk: vv for kk, vv in u.items() if kk not in ("iid", "play_seq")} for u in st]
                  for cr, st in d["board"].items()}
    d["hands"] = {p: sorted(json.dumps({kk: vv for kk, vv in u.items() if kk != "iid"}, sort_keys=True) for u in h)
                  for p, h in d["hands"].items()}
    d["remove_pile"] = sorted(d["remove_pile"])
    d.pop("pile_owners", None)
    d["inked"] = sorted(label.get(i, "gone") for i in state.inked)
    d = relabel(d)
    return json.dumps(d, sort_keys=True, separators=(",", ":"))


def won_key(state: GameState) -> str:
    """A turn that took the den, by the board it leaves: the same win finished by a different spare card is one."""
    d = json.loads(turn_key(state))
    return json.dumps({"won": True, "board": d["board"]}, sort_keys=True)


def _order(state: GameState, acts: list, actor: str) -> list:
    """Den captures first, passes last: the search finds a win (or a refutation) sooner."""
    def rank(a):
        if isinstance(a, (PlaceAction, RoamAction)) and a.is_hq_capture:
            return 0
        if isinstance(a, PassAction):
            return 3
        if isinstance(a, ChoiceAction) and a.choice == SKIP:
            return 2
        return 1
    return sorted(acts, key=rank)


@dataclass
class Solver:
    """Proves or refutes a den capture for A within `turns` of A's turns, counted from turn `start` (A's first)."""

    turns: int
    start: int = FIRST_TURN
    node_cap: int = 2_000_000
    nodes: int = 0
    memo: dict = field(default_factory=dict)

    @property
    def last_turn(self) -> int:
        return self.start + 2 * (self.turns - 1)

    def _tick(self) -> None:
        self.nodes += 1
        if self.nodes > self.node_cap:
            raise Unproven(f"over {self.node_cap} nodes")

    def outcome(self, state: GameState) -> Optional[bool]:
        """True: A has taken the den; False: the game is over otherwise, or A's turns are spent; None: open."""
        r = rules.is_terminal(state)
        if r is not None:
            return r.winner == SOLVER and r.reason == "hq_capture"
        if state.turn_counter > self.last_turn:
            return False
        return None

    def wins(self, state: GameState) -> bool:
        """Whether A forces the den from `state` within the horizon (whoever is to act)."""
        done = self.outcome(state)
        if done is not None:
            return done
        key = _key(state)
        hit = self.memo.get(key)
        if hit is not None:
            return hit
        self._tick()
        actor = state.player_to_act()
        acts = _order(state, moves(state), actor)
        if actor == SOLVER:
            res = any(self.wins(step(state, a)) for a in acts)
        else:
            res = all(self.wins(step(state, a)) for a in acts)
        self.memo[key] = res
        return res

    # --- what the client and the reports need ---

    def winning_moves(self, state: GameState) -> list[Action]:
        """The solver's moves from `state` that keep the forced win."""
        return [a for a in moves(state) if self.wins(step(state, a))]

    def first_turns(self, state: GameState) -> dict:
        """Every way A's turn can end from `state`, grouped by the position it ends on (key -> {line, wins})."""
        out: dict = {}

        def walk(s: GameState, line: list) -> None:
            if self.outcome(s) is not None or s.player_to_act() != SOLVER or s.turn_counter != state.turn_counter:
                k = won_key(s) if self.outcome(s) else turn_key(s)
                if k not in out:
                    out[k] = {"line": line, "lines": 1, "state": s}
                else:
                    out[k]["lines"] += 1
                return
            self._tick()
            for a in _order(s, moves(s), SOLVER):
                walk(step(s, a), line + [a])

        walk(state, [])
        for v in out.values():
            v["wins"] = self.wins(v["state"])
        return out

    def resistance(self, state: GameState) -> int:
        """How hard the position is for A to finish (B has just replied): the number of A's first decisions that still
        win. Lower is a better defence."""
        if self.outcome(state) is not None:
            return 0
        return len(self.winning_moves(state)) if state.player_to_act() == SOLVER else 0

    def defence(self, state: GameState) -> list[Action]:
        """B's whole reply from `state` (B to act), played to the end of B's turn or to A's next decision: one that
        escapes if any does, else the one that leaves A the fewest winning first decisions; ties go to the earliest
        in the engine's order."""
        best: Optional[tuple] = None

        def walk(s: GameState, line: list) -> None:
            nonlocal best
            if self.outcome(s) is not None or s.player_to_act() != DEFENDER:
                w = self.wins(s)
                score = (0, 0) if not w else (1, self.resistance(s))
                if best is None or score < best[0]:
                    best = (score, line)
                return
            if best is not None and best[0] == (0, 0):
                return
            self._tick()
            for a in moves(s):
                walk(step(s, a), line + [a])

        walk(state, [])
        return best[1] if best else []


# ---------------------------------------------------------------------------------------------- reports

def actions_from(dicts: list[dict]) -> list[Action]:
    return [action_from_dict({k: v for k, v in d.items() if k not in ("by", "sub")}) for d in dicts]


def play_line(state: GameState, dicts: list[dict]) -> GameState:
    """Apply a list of action dicts (validated) to a copy of `state`."""
    s = state.clone()
    for a in actions_from(dicts):
        rules.apply_action(s, a)
    return s


def main_line(puzzle: dict, solver: Optional[Solver] = None, first: Optional[list[dict]] = None) -> list[dict]:
    """The whole line the client sees when the solver plays `first` (the puzzle's solution): each defender reply is the
    search's `defence`, each later solver turn the first winning line found."""
    state = build(puzzle)
    sv = solver or Solver(puzzle["turns"])
    out: list[dict] = []
    for a in actions_from(first if first is not None else puzzle["solution"]):
        out.append({"by": state.player_to_act(), **a.to_dict()})
        state = step(state, a)
    while sv.outcome(state) is None:
        if state.player_to_act() == DEFENDER:
            for a in sv.defence(state):
                out.append({"by": DEFENDER, **a.to_dict()})
                state = step(state, a)
        else:
            win = sv.winning_moves(state)
            if not win:
                break
            out.append({"by": SOLVER, **win[0].to_dict()})
            state = step(state, win[0])
    return out


def solve(puzzle: dict, node_cap: int = 2_000_000) -> dict:
    """The full report: forced or not, every distinct winning first turn with the defender's best reply."""
    state = build(puzzle)
    sv = Solver(puzzle["turns"], node_cap=node_cap)
    try:
        forced = sv.wins(state)
        turns = sv.first_turns(state)
    except Unproven as e:
        return {"status": "unproven", "reason": str(e), "nodes": sv.nodes}
    winners = []
    for v in turns.values():
        if not v["wins"]:
            continue
        s = v["state"]
        reply = [] if sv.outcome(s) is not None else sv.defence(s)
        winners.append({"line": [a.to_dict() for a in v["line"]], "orders": v["lines"],
                        "reply": [a.to_dict() for a in reply]})
    winners.sort(key=lambda w: len(w["line"]))
    return {"status": "forced" if forced else "not forced", "winning_first_turns": winners,
            "first_turns": len(turns), "nodes": sv.nodes}


def check(puzzle: dict, node_cap: int = 2_000_000) -> list[str]:
    """Every problem with a puzzle file (empty: it is fit to ship)."""
    out = []
    for k in ("id", "title", "theme", "to_move", "turns", "board", "hands", "food", "solution", "hint", "why"):
        if k not in puzzle:
            out.append(f"missing {k}")
    if out:
        return out
    out += position_problems(puzzle)
    if out:
        return out
    try:
        rep = solve(puzzle, node_cap)
    except ChanceError as e:
        return [f"chance: {e}"]
    if rep["status"] != "forced":
        return [f"the capture is {rep['status']}"]
    n = len(rep["winning_first_turns"])
    if n > 2:
        out.append(f"{n} winning first turns (one wanted, two at most)")
    sol = [d for d in puzzle["solution"]]
    try:
        end = play_line(build(puzzle), sol)
    except Exception as e:  # noqa: BLE001
        return out + [f"the solution is not legal: {e}"]
    sv = Solver(puzzle["turns"], node_cap=node_cap)
    if end.turn_counter == FIRST_TURN and sv.outcome(end) is None and end.player_to_act() == SOLVER:
        out.append("the solution stops before the solver's turn is over")
    elif not sv.wins(end):
        out.append("the solution does not force the capture")
    if "main_line" in puzzle:
        ml = main_line(puzzle, sv)
        if ml != puzzle["main_line"]:
            out.append("main_line is not the line the defender's search plays (rerun solve.py write)")
        else:
            fin = play_line(build(puzzle), ml)
            r = rules.is_terminal(fin)
            if not (r and r.winner == SOLVER and r.reason == "hq_capture"):
                out.append("main_line does not end on the den")
    else:
        out.append("missing main_line (solve.py write fills it)")
    return out
