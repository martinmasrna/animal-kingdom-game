"""The position analyser: an analysis board for any position of any logged or running game, with an engine beside it.

Localhost only (`./play` sets AK_ANALYSE=1; live and staging never register it). Martin opens /analyse and picks a game.
The board is the game's own client: he plays on from any move as in a game, for either side, both hands face up, and
steps back and forth through the line (a move played after stepping back starts a new line from there; "back to the
game" restores the game's). "Analyse" starts the engine on the position on the board: every whole turn the side to act
can play, ranked by the whole-turn search (bots/atomic_bot.py, Martin, 2026-10-31: a turn is atomic, so nothing is
scored in the middle of one):

    Board        the board when the turn ends, mean over the five imagined hands      (every turn)
    Best reply   after the opponent's best whole reply turn in each hand: the ranking (the best 60 by Board)
    Old reply    the old search's score, after its GreedyBot reply, for contrast      (the best 20 by Best reply)

The evaluation and the five imagined hands are the Expert's own. Last, the Expert's own search runs on the position,
and its pick is marked in the list, with every option it weighed at each decision of its turn.

Any turn can be opened hand by hand ("hands"): the five hands, each one's scores, and its line, played on the board.

Heavy work runs in child processes (`python -m animal_kingdom.web.analyse`), so the server's event loop and its bots never
wait on it; the engine streams its ranking as JSON lines and the page polls the latest.
"""
from __future__ import annotations

import asyncio
import json
import os
import secrets
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

from aiohttp import web

from ..engine import rules
from ..engine.actions import ChoiceAction, DrawAction, PlaceAction, action_from_dict
from ..engine.cards import load_cards
from ..engine.config import Config
from ..engine.state import GameState, new_game, other_player
from ..engine.strength import effective_strength, placement_strength

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "results" / "human_games" / "web"
MATCH_DIR = ROOT / "results" / "web_matches"
PAGE = Path(__file__).resolve().parent / "static" / "analyse.html"
CARDS = load_cards()
REPLY_K = 40         # turns re-scored after the opponent's reply
DEEP_K = 12          # turns re-scored one round deeper
TURN_CAP = 1500      # whole turns enumerated at most; past it a line's remaining choices are left to the search's policy


# ------------------------------------------------------------------------------------------------ naming moves

def _name(cid: str) -> str:
    c = CARDS.get(cid)
    return c.name if c else cid


def describe(a: dict) -> str:
    """One action without its position (a fallback for anything `named` can't place)."""
    k = a.get("kind")
    if k == "place":
        return f"{_name(a['card_id'])} → {'den' if a['target'][0] == 'hq' else a['target'][1]}"
    if k == "roam":
        return f"roam {a['from']} → {'den' if a['target'][0] == 'hq' else a['target'][1]}"
    if k == "draw":
        return "draw"
    if k == "pass":
        return "end turn"
    if k == "choice":
        c = a.get("choice")
        return f"  choose {c if isinstance(c, str) else json.dumps(c)}"
    return json.dumps(a)


def _where(s: GameState, cr: str, me: str) -> str:
    """An empty crossroad by where it lies for the side acting: how far from its own den, and which row."""
    gm = s.game_map
    cols = max(int(c.split(",")[0]) for c in gm.crossroads)
    rows = max(int(c.split(",")[1]) for c in gm.crossroads)
    c, r = map(int, cr.split(","))
    own = min(int(x.split(",")[0]) for x in gm.hq_front(me))
    far = abs(c - own)
    col = {0: "at own den", cols - 1: "at enemy den"}.get(far, "centre" if far == (cols - 1) / 2 else
                                                         "own half" if far < (cols - 1) / 2 else "enemy half")
    row = "top" if r == 1 else "bottom" if r == rows else "middle"
    return f"empty crossroad, {col}, {row} row"


def _unit(s: GameState, cr: str, me: str) -> str:
    u = s.top_unit(cr)
    if u is None:
        return _where(s, cr, me)
    return f"{'own' if u.owner == me else 'enemy'} {_name(u.card_id)} ({effective_strength(s, u)})"


def named(state: GameState, seq: list[dict]) -> tuple[list[str], list[list[str]]]:
    """`seq` played from `state`, each action named by what it touches rather than where ("[TIGER] onto enemy Peacock
    (6)", "Serval onto empty crossroad, centre, top row"), as the side acting sees it; and, for each action, the
    crossroads it touches (for the page to ring on the board)."""
    s, out, crs = state.clone(), [], []
    for d in seq:
        me, k, t, touched = s.player_to_act(), d.get("kind"), describe(d), []
        if k == "place":
            tg = d["target"]
            if tg[0] == "hq":
                t = f"{_name(d['card_id'])} into the enemy den"
            else:
                t = f"{_name(d['card_id'])} onto {_unit(s, tg[1], me)}"
                touched = [tg[1]]
        elif k == "roam":
            src = s.top_unit(d["from"])
            tg = d["target"]
            name = _name(src.card_id) if src else "an animal"
            t = f"{name} roams into the enemy den" if tg[0] == "hq" else f"{name} roams onto {_unit(s, tg[1], me)}"
            touched = [d["from"]] + ([tg[1]] if tg[0] != "hq" else [])
        elif k == "choice":
            c = d.get("choice")
            if isinstance(c, str) and c in s.game_map.crossroads:
                t, touched = f"  → {_unit(s, c, me)}", [c]
            elif isinstance(c, str) and c in CARDS:
                t = f"  → {_name(c)}"
            elif isinstance(c, int):
                u = next((u for p in "AB" for u in s.hands[p] if u.iid == c), None)
                t = f"  → {_name(u.card_id)}" if u else t
            elif c in ("den", "skip"):
                t = "  → the den" if c == "den" else "  → nothing"
        out.append(t)
        crs.append(touched)
        try:
            rules.apply_action(s, action_from_dict({k_: v for k_, v in d.items() if k_ != "by"}), validate=False)
        except Exception:
            break
    while len(out) < len(seq):
        out.append(describe(seq[len(out)]))
        crs.append([])
    return out, crs


def texts(state: GameState, seq: list[dict]) -> list[str]:
    return named(state, seq)[0]


# ------------------------------------------------------------------------------------------------ games

def games() -> list[dict]:
    """The games to pick from, newest first: running matches, then every logged game (a match file holds one line a game)."""
    out = []
    for f in sorted(MATCH_DIR.glob("*.json"), key=lambda p: -p.stat().st_mtime):
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        if d.get("phase") != "playing" or not d.get("state") or d.get("takeover"):
            continue
        seats = d["seats"]
        out.append({"src": "live", "id": d["id"], "n": 0, "when": f.stat().st_mtime, "running": True,
                    "seats": {p: seats[p].get("bot") or seats[p].get("name") for p in "AB"},
                    "game": len(d.get("results") or []) + 1, "moves": len(d.get("actions") or [])})
    for f in sorted(LOG_DIR.glob("*.jsonl"), key=lambda p: -p.stat().st_mtime)[:150]:
        lines = f.read_text().splitlines()
        for n in range(len(lines) - 1, -1, -1):
            try:
                g = json.loads(lines[n])
            except Exception:
                continue
            if not g.get("lists"):
                continue
            out.append({"src": "log", "id": f.stem, "n": n, "when": f.stat().st_mtime, "running": False,
                        "seats": dict(zip("AB", g.get("bots", ["?", "?"]))), "game": n + 1,
                        "winner": g.get("winner"), "reason": g.get("reason"), "moves": len(g.get("actions", []))})
    return out


def _source(src: str, gid: str, n: int):
    """(a fresh start of the game, its seed, its actions)."""
    if src == "log":
        g = json.loads((LOG_DIR / f"{Path(gid).name}.jsonl").read_text().splitlines()[n])
        def start():
            return new_game(list(g["lists"][0]), list(g["lists"][1]), g["seed"], map_id=g.get("map_id", "map_b"),
                            config=Config.default().for_log(g), first_player=g["first_player"])
        return start, g["seed"], g["actions"]
    from .match import MAP_ID, Match
    m = Match.from_dict(json.loads((MATCH_DIR / f"{Path(gid).name}.json").read_text()))
    decks = [list(m.state.starting_decks[p]) for p in "AB"]
    target = json.dumps(m.state.to_dict()["board"], sort_keys=True)
    for first in "AB":           # the match file keeps the seed and the actions, not who went first: the one that replays
        st = new_game(*decks, m.seed, map_id=MAP_ID, first_player=first)
        try:
            for a in m.actions:
                rules.apply_logged(st, a)
        except Exception:
            continue
        if json.dumps(st.to_dict()["board"], sort_keys=True) == target:
            return (lambda first=first: new_game(*decks, m.seed, map_id=MAP_ID, first_player=first)), m.seed, list(m.actions)
    raise ValueError("this match doesn't replay from its log")


def _actor(state: GameState, a: dict) -> str:
    return a.get("by") or state.player_to_act()


def seat_view(m, seat: str) -> dict:
    """The client's view from `seat`, the other hand face up (the game's revealed-hand slot)."""
    v = m.view(seat)
    st = m.state
    v["game"]["revealedHand"] = [{"iid": u.iid, "id": u.card_id, "str": placement_strength(st, u)}
                                 for u in st.hands[other_player(seat)]]
    return v


def view(state: GameState, me: str, label: str = "") -> dict:
    """A still view of `state` from `me`'s seat, the other hand face up (a frame of an imagined line)."""
    from .match import Match, Seat
    m = Match("ANALYSE", Seat("a", "Seat A", deck="canines"))
    m.join(Seat("b", "Seat B", deck="cats"))
    m.start_from(state.clone(), 0)
    v = seat_view(m, me)
    v["game"]["events"] = []
    v["label"] = label
    return v


# ------------------------------------------------------------------------------------------------ the analysis board

class Session:
    """One analysis board: a game's start, the line on the board (the game's moves, or a new line from where Martin
    stepped back and played), and how far along it the board stands. The board is a real match with both seats open."""

    def __init__(self, src: str, gid: str, n: int):
        self.start, self.seed, game = _source(src, gid, n)
        # A game from before a card changed stops replaying where a logged move became illegal: the board holds the
        # moves up to there, and says so (`stops`).
        st, ok = self.start(), 0
        for a in game:
            try:
                rules.apply_logged(st, a)
            except Exception:
                break
            ok += 1
        self.stops = ok if ok < len(game) else None
        self.game = [dict(a) for a in game[:ok]]
        self.line = [dict(a) for a in self.game]
        self.k = len(self.line)
        self.m = None
        self._build(self.k)

    def _build(self, k: int) -> None:
        from .match import Match, Seat
        m = Match("ANALYSE", Seat("a", "Seat A", deck="canines"))
        m.join(Seat("b", "Seat B", deck="cats"))
        m.start_from(self.start(), self.seed)
        for a in self.line[:k]:
            m.act(_actor(m.state, a), a)
        m.events = []           # stepping somewhere is not a move: nothing to animate
        self.m, self.k = m, k

    def goto(self, k: int) -> None:
        k = max(0, min(len(self.line), k))
        if k >= self.k:                  # forward: play the line on
            for a in self.line[self.k:k]:
                self.m.act(_actor(self.m.state, a), a)
            self.k = k
            self.m.events = []
        else:
            self._build(k)

    def play(self, action: dict) -> None:
        st = self.m.state
        seat = st.player_to_act()
        self.m.events = []      # the view animates this move's events only, never the moves before it
        self.m.act(seat, action)
        self.line = self.line[:self.k] + [action]
        self.k += 1

    def seat(self) -> str:
        st = self.m.state
        return st.player_to_act() if rules.is_terminal(st) is None else (st.result.winner or "A") if st.result else "A"

    def moves(self) -> list[dict]:
        st, out = self.start(), []
        for i, a in enumerate(self.line):
            txt, crs = named(st, [a])
            out.append({"k": i, "turn": st.turn_counter, "actor": _actor(st, a), "text": txt[0], "crs": crs[0],
                        "top": a.get("kind") != "choice", "game": i < len(self.game) and self.game[i] == a})
            rules.apply_logged(st, a)
        return out

    def payload(self, mover: Optional[str] = None) -> dict:
        st = self.m.state
        seat = self.seat()
        out = {"k": self.k, "n": len(self.line), "seat": seat, "view": seat_view(self.m, seat), "turn": st.turn_counter,
               "cols": max(int(c.split(",")[0]) for c in st.game_map.crossroads),
               "food": st.food, "over": rules.is_terminal(st) is not None,
               "off_game": self.line[:len(self.game)] != self.game[:len(self.line)] or len(self.line) > len(self.game),
               "stops": self.stops}
        if mover and mover != seat:     # the move animates from the mover's seat first, then the board turns
            out["mover_view"] = seat_view(self.m, mover)
        return out


SESSIONS: dict[str, Session] = {}


# ------------------------------------------------------------------------------------------------ scoring like the Expert

def _expert(seed: int):
    from ..sim.runner import make_bot
    from .match import EXPERT
    spec = EXPERT.replace("time_budget=8", "time_budget=0")   # the full search; live it is the same search, cut at 8 s
    bot = make_bot(spec, seed, python_only=True)
    bot.last_search_stats = {"reply_world_rollouts": 0}
    return bot


def _worlds(bot, state: GameState, me: str) -> list[GameState]:
    """The hands the Expert imagines for the opponent at this seed (the same its own search starts from)."""
    from ..bots.determinize import determinize
    return [determinize(state, me, bot.det_rng) for _ in range(bot.determinizations)]


def _finish(bot, s: GameState, turn: list[dict], me: str) -> float:
    """Play `turn` in `s`, then whatever of my turn it leaves open (a Roar's choice, the action after a draw) by the
    search's own policy. Returns the wasted-Roar penalty the search charges the line (a Roar that fired at nothing)."""
    from ..bots.turn_search import _roar_fizzled
    pen = 0.0
    for d in turn:
        a = action_from_dict(d)
        before = s.clone()
        rules.apply_action(s, a, validate=False)
        if isinstance(a, PlaceAction) and _roar_fizzled(before, s, me, a):
            pen += bot.weights.wasted_roar
    for _ in range(20):
        if rules.is_terminal(s) is not None or s.player_to_act() != me:
            break
        legal_ = rules.legal_actions(s)
        if not legal_:
            break
        a = bot._policy.choose(s.view_for(me), legal_, s)
        before = s.clone()
        rules.apply_action(s, a, validate=False)
        if isinstance(a, PlaceAction) and _roar_fizzled(before, s, me, a):
            pen += bot.weights.wasted_roar
    return pen


def turns(state: GameState, me: str, cap: int = TURN_CAP) -> list[list[dict]]:
    """Every whole turn `me` can play from here: each sequence of actions and choices until the turn passes. A draw ends
    the enumeration (what follows depends on the card drawn: the policy plays it), and so does the cap."""
    out: list[list[dict]] = []
    def walk(s: GameState, path: list[dict]):
        if rules.is_terminal(s) is not None or s.player_to_act() != me:
            out.append(path)
            return
        legal_ = rules.legal_actions(s)
        if not legal_ or len(out) >= cap:
            out.append(path)
            return
        for a in legal_:
            d = a.to_dict()
            if isinstance(a, DrawAction):
                out.append(path + [d])
                continue
            nxt = s.clone()
            rules.apply_action(nxt, a, validate=False)
            walk(nxt, path + [d])
    walk(state.clone(), [])
    return [t for t in out if t]


def _atomic(seed: int, rounds: int):
    """The whole-turn search on the Expert's evaluation and imagined hands: the Rust engine's when it is built."""
    from ..sim.runner import make_bot
    from .match import EXPERT
    spec = EXPERT.replace("referee_learned", "atomic_learned").replace("time_budget=8", "time_budget=0")
    return make_bot(f"{spec},rounds={rounds}", seed)


def _ranked(bot, state: GameState, real: bool) -> list[dict]:
    """The bot's ranking of `state` as plain rows {turn: [action dicts], open, board, levels, per_hand}."""
    if hasattr(bot, "ranking"):
        return bot.ranking(state, real)
    me = state.player_to_act()
    rows = bot.rank(state, me, [state.clone()] if real else None)
    return [{**r, "turn": [a.to_dict() for a in r["turn"]]} for r in rows]


def engine(state: GameState, seed: int, emit, depth: int = 1, real: bool = False) -> None:
    """Every whole turn for the side to act, ranked by the whole-turn search (bots/atomic_bot.py, in Rust when built):
    the board when it ends, for all of them; depth 1 (after the opponent's best reply) for the best 60; with `depth`
    2, depth 2 (my best next turn and their best reply to it) for the best 20 of those. `real`: scored against the
    true hidden cards and deck order instead of the imagined hands (a look back at the game, not the bot's view).
    `emit` gets the ranking after each depth, then with the old search's reply score and the Expert's own pick."""
    me = state.player_to_act()
    t0 = time.monotonic()
    old: dict = {}

    def rowdict(r):
        txt, crs = named(state, r["turn"])
        lv = r["levels"] + [None] * (2 - len(r["levels"]))
        ph = r["per_hand"] + [None] * (2 - len(r["per_hand"]))
        return {"turn": r["turn"], "text": txt + (["then the best for the cards it draws"] if r["open"] else []),
                "crs": crs, "board": round(r["board"], 1),
                "score": None if lv[0] is None else round(lv[0], 1), "score2": None if lv[1] is None else round(lv[1], 1),
                "per_hand": [round(v, 1) for v in (ph[0] or [])], "per_hand2": [round(v, 1) for v in (ph[1] or [])],
                "old": old.get(json.dumps(r["turn"]))}

    def send(rows, stage, extra=None):
        emit({"stage": stage, "done": 1, "total": 1, "turns": len(rows), "seconds": round(time.monotonic() - t0, 1),
              "me": me, "depth": depth, "real": real, "rows": [rowdict(r) for r in rows[:60]], **(extra or {})})

    rows = _ranked(_atomic(seed, 1), state, real)
    send(rows, 2)
    if depth >= 2:
        rows = _ranked(_atomic(seed, 2), state, real)
        send(rows, 3)
    if not real:                               # the old search's score of the best 20, after its GreedyBot reply
        base = _expert(seed)
        worlds = _worlds(base, state, me)
        for r in rows[:20]:
            if r["levels"][0] is None:
                continue
            branches = []
            for w in worlds:
                x = w.clone()
                branches.append((x, _finish(base, x, r["turn"], me)))
            base._move_started, base._deepening, base._search_nodes = time.monotonic(), False, 0
            sc = base._reply_scores(branches, me)
            old[json.dumps(r["turn"])] = round(sum(sc) / len(sc), 1)
    send(rows, 4)
    expert = search(state, seed)
    last = [rowdict(r) for r in rows[:60]]
    for r in last:
        r["expert"] = r["turn"] == expert["planned"]
    if not any(r["expert"] for r in last):
        txt, crs = named(state, expert["planned"])
        last.append({"turn": expert["planned"], "text": txt, "crs": crs, "board": None, "score": None, "score2": None,
                     "per_hand": [], "per_hand2": [], "old": None, "expert": True})
    emit({"stage": 5, "done": 1, "total": 1, "turns": len(rows), "seconds": round(time.monotonic() - t0, 1), "me": me,
          "depth": depth, "real": real, "rows": last, "expert": expert})


def search(state: GameState, seed: int) -> dict:
    """What the Expert's own search does here: its pick, the turn it planned with it, the first actions it scored with
    their scores, and every option it weighed at each decision of the planned turn."""
    me = state.player_to_act()
    bot = _expert(seed)
    seen: dict = {}
    stage = {"root": None, "deep": False}
    keep: dict = {}

    def observe(path, score, compare):
        if stage["root"] is not None and not stage["deep"]:
            seen.setdefault(stage["root"], {})[path] = (score, compare)

    begin = bot._begin_root_candidate
    def begin_root(a):
        stage["root"] = a
        begin(a)
    bot._begin_root_candidate = begin_root
    rescore = bot._rescore_roots
    def rescore_roots(worlds, root_scores, st, me_):
        keep["worlds"] = [w.clone() for w in worlds]
        keep["shallow"] = list(root_scores)
        stage["deep"] = True
        out = rescore(worlds, root_scores, st, me_)
        keep["deep"] = list(out)
        return out
    bot._rescore_roots = rescore_roots
    bot._observer = observe
    chosen = bot.choose(state.view_for(me), rules.legal_actions(state), state)
    deep = dict(keep.get("deep", []))
    worlds = keep.get("worlds") or [state]
    roots = []
    for a, shallow in keep.get("shallow", []):
        t = _turn_of(bot, worlds[0], a, me)
        txt, crs = named(state, t)
        roots.append({"turn": t, "text": txt, "crs": crs, "reply": round(shallow, 1),
                      "deep": round(deep[a], 1) if a in deep else None,
                      "decisions": _decisions(state, a, t, seen.get(a, {}))})
    planned = next((r["turn"] for r in roots if r["turn"][0] == chosen.to_dict()), [chosen.to_dict()])
    return {"chosen": texts(state, [chosen.to_dict()])[0], "planned": planned, "planned_text": texts(state, planned),
            "roots": roots}


def _turn_of(bot, world: GameState, first, me: str) -> list[dict]:
    """The rest of the turn the search planned after `first`, read off its plan for this root in one sampled world."""
    plan = bot._candidate_plans.get(first, {})
    s = world.clone()
    rules.apply_action(s, first, validate=False)
    seq = [first.to_dict()]
    for _ in range(12):
        if rules.is_terminal(s) is not None or s.player_to_act() != me:
            break
        a = plan.get(bot._observation_key(s, me))
        if a is None:
            break
        rules.apply_action(s, a, validate=False)
        seq.append(a.to_dict())
    return seq


def _decisions(st: GameState, first, turn: list[dict], seen: dict) -> list[dict]:
    """The planned turn's decisions after its first action, in order, each with every option the planner scored there:
    its score, whether that score is after the opponent's sampled reply (the turn's last action) or of the board when
    the turn ends (the choices before it), and whether the plan took it. Each option carries its whole turn (its best
    continuation below it), so any of them can be opened hand by hand."""
    def best_below(path):
        while True:
            kids = [p for p in seen if len(p) == len(path) + 1 and p[:len(path)] == path]
            if not kids:
                return path
            path = max(kids, key=lambda p: seen[p][0])
    out, prefix = [], ()
    planned = turn[1:]
    while True:
        kids = [p for p in seen if len(p) == len(prefix) + 1 and p[:len(prefix)] == prefix]
        if not kids:
            break
        nxt = planned[len(prefix)] if len(prefix) < len(planned) else None
        took = next((p for p in kids if p[-1].to_dict() == nxt), None) or max(kids, key=lambda p: seen[p][0])
        opts = []
        for p in sorted(kids, key=lambda p: -seen[p][0]):
            whole = best_below(p)
            opts.append({"text": texts(st, [first.to_dict()] + [x.to_dict() for x in p])[-1],
                         "score": round(seen[p][0], 1), "reply": seen[p][1], "took": p == took,
                         "turn": [first.to_dict()] + [x.to_dict() for x in whole]})
        out.append({"options": opts})
        prefix = took
    return out


def _recorded(s: GameState, run, me: str, label: str) -> list[dict]:
    """Run `run(s)` (which plays `s` forward) and return a frame after each top-level action it took, with its text."""
    frames = []
    real = rules.apply_action
    def spy(state, action, validate=True, _real=real):
        out = _real(state, action, validate=validate)
        if state is s and not isinstance(action, ChoiceAction):
            frames.append((s.clone(), describe(action.to_dict())))
        return out
    rules.apply_action = spy
    try:
        run(s)
    finally:
        rules.apply_action = real
    return [view(f, me, f"{label}: {text}") for f, text in frames]


def explain(state: GameState, seed: int, turn: list[dict]) -> dict:
    """One whole turn scored the way the Expert's search scores it, hand by hand: the five hands it imagines for the
    opponent, the board when the turn ends, the score after their reply, one round deeper, and each hand's line as board
    frames."""
    me = state.player_to_act()
    bot = _expert(seed)
    worlds = _worlds(bot, state, me)
    branches, pens = [], []
    for w in worlds:
        s = w.clone()
        pens.append(_finish(bot, s, turn, me))
        branches.append(s)
    out = {"me": me, "turn": texts(state, turn), "hands": []}
    out["board"] = [round(bot._clamped_eval(b, me) - p, 1) for b, p in zip(branches, pens)]
    bot._move_started, bot._deepening, bot._search_nodes = time.monotonic(), False, 0
    out["reply"] = [round(x, 1) for x in bot._reply_scores([(b.clone(), p) for b, p in zip(branches, pens)], me)]
    from ..bots.atomic_bot import AtomicBot
    atomic = AtomicBot(bot)
    for k, (w, b) in enumerate(zip(worlds, branches)):
        frames = [view(w, me, "The position, with the hand imagined for the opponent"), view(b, me, "After this turn")]
        value, reply = atomic.best_reply(b.clone(), me)
        r = b.clone()
        def run(s):
            for a in reply:
                rules.apply_action(s, a, validate=False)
        frames += _recorded(r, run, me, "Their best reply")
        result = rules.is_terminal(r)
        out["hands"].append({"hand": [_name(u.card_id) for u in w.hands[other_player(me)]],
                             "board": out["board"][k], "reply": out["reply"][k], "best": round(value, 1),
                             "reply_text": named(b, [a.to_dict() for a in reply])[0],
                             "ends": (("they win" if result.winner != me else "it wins") + f" ({result.reason})")
                             if result else "", "frames": frames})
    out["best"] = [h["best"] for h in out["hands"]]
    return out


# ------------------------------------------------------------------------------------------------ the server side

JOBS: dict[str, dict] = {}


def _state_file(state: GameState) -> str:
    fd, path = tempfile.mkstemp(prefix="ak_analyse_", suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(state.to_dict(), f)
    return path


async def _child(kind: str, state: GameState, args: dict, on_line=None) -> Optional[dict]:
    """Run one analysis in a child process (CPU-heavy: the server keeps serving). `on_line` gets each JSON line it
    prints; the last one is returned."""
    path = _state_file(state)
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-W", "ignore", "-m", "animal_kingdom.web.analyse", kind, path, json.dumps(args),
        cwd=str(ROOT), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, limit=1 << 26,
        env={k: v for k, v in os.environ.items() if k != "AK_PY_BOTS"})
    if on_line is not None:
        on_line(None, proc)
    last = None
    try:
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            last = json.loads(line)
            if on_line is not None:
                on_line(last, proc)
        err = await proc.stderr.read()
        await proc.wait()
        if proc.returncode not in (0, -9, -15) and last is None:
            raise web.HTTPInternalServerError(text=err.decode()[-2000:])
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    return last


def _session(sid: str) -> Session:
    s = SESSIONS.get(sid)
    if s is None:
        raise web.HTTPNotFound(text="This board has expired: reload the page")
    return s


async def page(_req):
    return web.FileResponse(PAGE)


async def api_games(_req):
    return web.json_response(games())


async def api_open(req):
    body = await req.json()
    s = Session(body["src"], body["id"], int(body.get("n", 0)))
    if body.get("k") is not None:
        s.goto(int(body["k"]))
    sid = secrets.token_urlsafe(8)
    SESSIONS[sid] = s
    while len(SESSIONS) > 20:
        SESSIONS.pop(next(iter(SESSIONS)))
    return web.json_response({"sid": sid, "moves": s.moves(), **s.payload()})


async def api_goto(req):
    body = await req.json()
    s = _session(body["sid"])
    if body.get("game"):
        s.line = [dict(a) for a in s.game]
        s._build(min(s.k, len(s.line)))
    s.goto(int(body["k"]))
    return web.json_response({"moves": s.moves(), **s.payload()})


async def api_play(req):
    body = await req.json()
    s = _session(body["sid"])
    mover = s.m.state.player_to_act()
    try:
        s.play(body["action"])
    except Exception as e:
        raise web.HTTPBadRequest(text=str(e))
    return web.json_response({"moves": s.moves(), **s.payload(mover)})


async def api_engine(req):
    """Start the engine on the board's position (stopping the one running for this board)."""
    body = await req.json()
    s = _session(body["sid"])
    old = JOBS.pop(body["sid"], None)
    if old and old.get("proc") and old["proc"].returncode is None:
        old["proc"].kill()
    state = s.m.state.clone()
    if rules.is_terminal(state) is not None:
        raise web.HTTPBadRequest(text="The game is over")
    job = {"k": s.k, "seed": int(body.get("seed", 0)), "depth": int(body.get("depth", 1)), "real": bool(body.get("real")),
           "latest": None, "proc": None, "done": False}
    JOBS[body["sid"]] = job

    def on_line(line, proc):
        job["proc"] = proc
        if line is not None:
            job["latest"] = line

    async def run():
        try:
            await _child("engine", state, {"seed": job["seed"], "depth": job["depth"], "real": job["real"]}, on_line)
        except Exception as e:
            job["error"] = str(e)[-500:]
        job["done"] = True
    asyncio.get_running_loop().create_task(run())
    return web.json_response({"ok": True})


async def api_engine_poll(req):
    job = JOBS.get(req.query["sid"])
    if job is None:
        return web.json_response({"none": True})
    return web.json_response({"k": job["k"], "seed": job["seed"], "done": job["done"], "error": job.get("error"),
                              "latest": job["latest"]})


async def api_engine_stop(req):
    body = await req.json()
    job = JOBS.get(body["sid"])
    if job and job.get("proc") and job["proc"].returncode is None:
        job["proc"].kill()
    return web.json_response({"ok": True})


async def api_explain(req):
    body = await req.json()
    s = _session(body["sid"])
    out = await _child("explain", s.m.state.clone(), {"seed": int(body.get("seed", 0)), "turn": body["turn"]})
    return web.json_response(out)


def register(app: web.Application) -> None:
    app.add_routes([
        web.get("/analyse", page),
        web.get("/api/analyse/games", api_games),
        web.post("/api/analyse/open", api_open),
        web.post("/api/analyse/goto", api_goto),
        web.post("/api/analyse/play", api_play),
        web.post("/api/analyse/engine", api_engine),
        web.get("/api/analyse/engine", api_engine_poll),
        web.post("/api/analyse/engine/stop", api_engine_stop),
        web.post("/api/analyse/explain", api_explain),
    ])


def main(argv: Optional[list] = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    kind, path, args = argv[0], argv[1], json.loads(argv[2])
    state = GameState.from_dict(json.loads(Path(path).read_text()))
    emit = lambda d: (sys.stdout.write(json.dumps(d) + "\n"), sys.stdout.flush())
    if kind == "engine":
        engine(state, int(args["seed"]), emit, int(args.get("depth", 1)), bool(args.get("real")))
    elif kind == "search":
        emit(search(state, int(args["seed"])))
    else:
        emit(explain(state, int(args["seed"]), args["turn"]))


if __name__ == "__main__":
    main()
