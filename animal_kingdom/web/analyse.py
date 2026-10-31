"""The position analyser: any position of any logged or running game, and what the Expert's search makes of it.

Localhost only (`./play` sets AK_ANALYSE=1; live and staging never register it). Martin opens /analyse, picks a game and
a move, and sees the board from the seat to act with the other hand face up, the turns the Expert considered with the
scores its search gave them, and, for any turn (one it considered or one he puts together), the five hands it imagined
for the opponent, what each scored and the line it played out to get there, on the real board.

The numbers are the Expert's own: the Python search (bit for bit the Rust one the server plays) run on the shipped spec
without its time budget, watched through `TurnSearcher._observer`. The search itself runs in a child process
(`python -m animal_kingdom.web.analyse`) so the server's event loop and its bots never wait on it; results are cached.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

from aiohttp import web

from ..engine import rules
from ..engine.actions import ChoiceAction, DrawAction, PlaceAction, RoamAction, action_from_dict
from ..engine.cards import load_cards
from ..engine.config import Config
from ..engine.state import GameState, new_game, other_player
from ..engine.strength import effective_strength, placement_strength

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "results" / "human_games" / "web"
MATCH_DIR = ROOT / "results" / "web_matches"
CACHE = ROOT / "results" / "analysis"
PAGE = Path(__file__).resolve().parent / "static" / "analyse.html"
CARDS = load_cards()


# ------------------------------------------------------------------------------------------------ games and positions

def _name(cid: str) -> str:
    c = CARDS.get(cid)
    return c.name if c else cid


def describe(a: dict) -> str:
    """One action as a line of the move list."""
    k = a.get("kind")
    if k == "place":
        t = a["target"]
        return f"{_name(a['card_id'])} → {'den' if t[0] == 'hq' else t[1]}"
    if k == "roam":
        t = a["target"]
        return f"roam {a['from']} → {'den' if t[0] == 'hq' else t[1]}"
    if k == "draw":
        return "draw"
    if k == "choice":
        c = a.get("choice")
        return f"  choose {c if isinstance(c, str) else json.dumps(c)}"
    return json.dumps(a)


def texts(state: GameState, seq: list[dict]) -> list[str]:
    """`seq` played from `state`, each action described with what it touches: a choice names the animal on the
    crossroad it picks (or the card it picks), as the seat acting sees it ("own" or "enemy")."""
    s, out = state.clone(), []
    for d in seq:
        t = describe(d)
        if d.get("kind") == "choice":
            c, me = d.get("choice"), s.player_to_act()
            if isinstance(c, str) and s.top_unit(c) is not None:
                u = s.top_unit(c)
                t = f"  on {c}: {'own' if u.owner == me else 'enemy'} {_name(u.card_id)} ({effective_strength(s, u)})"
            elif isinstance(c, str) and c in CARDS:
                t = f"  pick {_name(c)}"
            elif isinstance(c, int):
                u = next((u for p in "AB" for u in s.hands[p] if u.iid == c), None)
                t = f"  pick {_name(u.card_id)}" if u else t
        out.append(t)
        try:
            rules.apply_action(s, action_from_dict(d), validate=False)
        except Exception:
            break
    return out


def games() -> list[dict]:
    """The games to pick from, newest first: running matches, then every logged game (a match file holds one line a game)."""
    out = []
    for f in sorted(MATCH_DIR.glob("*.json"), key=lambda p: -p.stat().st_mtime):
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        if d.get("phase") != "playing" or not d.get("state"):
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
    """(a fresh start of the game, its actions)."""
    if src == "log":
        g = json.loads((LOG_DIR / f"{Path(gid).name}.jsonl").read_text().splitlines()[n])
        def start():
            return new_game(list(g["lists"][0]), list(g["lists"][1]), g["seed"], map_id=g.get("map_id", "map_b"),
                            config=Config.default().for_log(g), first_player=g["first_player"])
        return start, g["actions"]
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
            return (lambda first=first: new_game(*decks, m.seed, map_id=MAP_ID, first_player=first)), list(m.actions)
    raise ValueError("this match doesn't replay from its log")


def position(src: str, gid: str, n: int, ply: int) -> GameState:
    """The game right before its action number `ply` (0: the start)."""
    start, actions = _source(src, gid, n)
    st = start()
    for a in actions[:ply]:
        rules.apply_logged(st, a)
    return st


def moves(src: str, gid: str, n: int) -> list[dict]:
    """The move list: each action with who took it and the turn it was in."""
    start, actions = _source(src, gid, n)
    st, out = start(), []
    for i, a in enumerate(actions):
        out.append({"ply": i, "turn": st.turn_counter, "actor": st.player_to_act(), "text": texts(st, [a])[0],
                    "top": a.get("kind") != "choice"})
        rules.apply_logged(st, a)
    return out


def view(state: GameState, me: str, label: str = "") -> dict:
    """The client's view of `state` from `me`'s seat, the other hand face up (the game's revealed-hand slot)."""
    from .match import Match, Seat
    opp = other_player(me)
    m = Match("ANALYSE", Seat("a", "You", deck="canines"))
    m.join(Seat("b", "Opponent", deck="cats"))
    m.start_from(state.clone(), 0)
    v = m.view(me)
    v["game"]["events"] = []
    v["game"]["revealedHand"] = [{"iid": u.iid, "id": u.card_id, "str": placement_strength(state, u)}
                                 for u in state.hands[opp]]
    v["label"] = label
    return v


def legal(state: GameState, after: list[dict]) -> list[dict]:
    """The legal actions once `after` has been played from `state` (the next action of a turn being put together)."""
    st = state.clone()
    for a in after:
        rules.apply_action(st, action_from_dict(a))
    if rules.is_terminal(st) is not None:
        return []
    return [{"action": a.to_dict(), "text": texts(st, [a.to_dict()])[0], "actor": st.player_to_act()}
            for a in rules.legal_actions(st)]


# ------------------------------------------------------------------------------------------------ the Expert's search

def _expert(seed: int):
    from ..sim.runner import make_bot
    from .match import EXPERT
    spec = EXPERT.replace("time_budget=8", "time_budget=0")   # the full search; live it is the same search, cut at 8 s
    bot = make_bot(spec, seed, python_only=True)
    bot.last_search_stats = {"reply_world_rollouts": 0}
    return bot


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
    """The turn's decisions after its first action, in order, each with every option the planner scored there: its
    score, whether that score is after the opponent's sampled reply (the turn's last action) or of the board when the
    turn ends (the choices before it), and whether it is the one the plan took. Each option carries its own whole turn
    (its best continuation below it), so any of them can be explained."""
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
            opts.append({"text": texts(st, [first.to_dict()] + [x.to_dict() for x in p])[-1], "score": round(seen[p][0], 1), "reply": seen[p][1],
                         "took": p == took, "turn": [first.to_dict()] + [x.to_dict() for x in whole]})
        out.append({"options": opts})
        prefix = took
    return out


def search(src: str, gid: str, n: int, ply: int, seed: int) -> dict:
    """What the Expert's search does at this position: every first action it scored, the rest of the turn it planned for
    each, the other continuations it weighed with their scores, and the move it picks."""
    st = position(src, gid, n, ply)
    me = st.player_to_act()
    bot = _expert(seed)
    seen: dict = {}
    stage = {"root": None, "deep": False}
    keep: dict = {}

    def observe(path, score, compare):
        if stage["root"] is None or stage["deep"]:
            return
        seen.setdefault(stage["root"], {})[path] = (score, compare)

    begin = bot._begin_root_candidate
    def begin_root(a):
        stage["root"] = a
        begin(a)
    bot._begin_root_candidate = begin_root
    rescore = bot._rescore_roots
    def rescore_roots(worlds, root_scores, state, me_):
        keep["worlds"] = [w.clone() for w in worlds]
        keep["shallow"] = list(root_scores)
        stage["deep"] = True
        out = rescore(worlds, root_scores, state, me_)
        keep["deep"] = list(out)
        return out
    bot._rescore_roots = rescore_roots
    bot._observer = observe
    t0 = time.monotonic()
    chosen = bot.choose(st.view_for(me), rules.legal_actions(st), st)
    took = time.monotonic() - t0
    deep = dict(keep.get("deep", []))
    worlds = keep.get("worlds") or []
    roots = []
    for a, shallow in keep.get("shallow", []):
        turn = _turn_of(bot, worlds[0], a, me) if worlds else [a.to_dict()]
        roots.append({"first": a.to_dict(), "turn": turn, "text": texts(st, turn),
                      "shallow": round(shallow, 1), "deep": round(deep[a], 1) if a in deep else None,
                      "decisions": _decisions(st, a, turn, seen.get(a, {}))})
    roots.sort(key=lambda r: -(r["deep"] if r["deep"] is not None else r["shallow"] - 1e7))
    stats = {k: v for k, v in bot.last_search_stats.items() if isinstance(v, (int, float))}
    return {"me": me, "chosen": chosen.to_dict(), "chosen_text": describe(chosen.to_dict()), "roots": roots,
            "legal": len(rules.legal_actions(st)), "seconds": round(took, 1), "stats": stats,
            "outs": "outs_roots" in stats}


# ------------------------------------------------------------------------------------------------ one turn, explained

def _finish(bot, s: GameState, turn: list[dict], me: str) -> float:
    """Play `turn` in `s`; a choice it leaves open is made by the search's own policy. Returns the wasted-Roar penalty
    the search charges the line (a Roar that fired at nothing)."""
    from ..bots.turn_search import _roar_fizzled
    pen = 0.0
    for d in turn:
        a = action_from_dict(d)
        before = s.clone()
        rules.apply_action(s, a, validate=False)
        if isinstance(a, PlaceAction) and _roar_fizzled(before, s, me, a):
            pen += bot.weights.wasted_roar
    for _ in range(12):
        if rules.is_terminal(s) is not None or s.pending is None or s.player_to_act() != me:
            break
        legal_ = rules.legal_actions(s)
        a = bot._policy.choose(s.view_for(me), legal_, s)
        rules.apply_action(s, a, validate=False)
    return pen


def _recorded(bot, s: GameState, run, me: str, label: str) -> list[dict]:
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


def explain(src: str, gid: str, n: int, ply: int, seed: int, turn: list[dict]) -> dict:
    """One whole turn scored the way the Expert's search scores it, hand by hand: the five hands it imagines for the
    opponent (the same five its search at this seed used), the score after the opponent's reply, the score one round
    deeper, and the line behind each, as board frames."""
    st = position(src, gid, n, ply)
    me = st.player_to_act()
    bot = _expert(seed)
    from ..bots.determinize import determinize
    worlds = [determinize(st, me, bot.det_rng) for _ in range(bot.determinizations)]
    branches, pens = [], []
    for w in worlds:
        s = w.clone()
        pens.append(_finish(bot, s, turn, me))
        branches.append(s)
    out = {"me": me, "turn": texts(st, turn), "hands": []}
    for deep in (False, True):
        bot._move_started, bot._deepening, bot._search_nodes = time.monotonic(), deep, 0
        scores = bot._reply_scores([(b.clone(), p) for b, p in zip(branches, pens)], me)
        out["deep" if deep else "shallow"] = [round(x, 1) for x in scores]
    bot._deepening = False
    out["board"] = round(bot._clamped_eval(branches[0], me), 1)
    for k, (w, b) in enumerate(zip(worlds, branches)):
        frames = [view(w, me, "The position, with the hand imagined for the opponent"),
                  view(b, me, "After this turn")]
        r = b.clone()
        frames += _recorded(bot, r, lambda s: bot._advance(s, me), me, "Their imagined reply")
        reply_end = r.clone()
        if r.result is None and r.player_to_act() == me and r.pending is None:
            # one round deeper, as the search looks: the best of my next turns (its few best first moves, the rest by the
            # fast policy) against their reply after it
            best, best_frames = None, []
            for a in bot._greedy_topn(r, rules.legal_actions(r), me, bot.next_width):
                x = r.clone()
                def run(s, a=a):
                    rules.apply_action(s, a, validate=False)
                    bot._play_turn(s, me)
                    bot._deepening = True
                    try:
                        bot._advance(s, me)
                    finally:
                        bot._deepening = False
                fr = _recorded(bot, x, run, me, "One round deeper")
                value = bot._clamped_eval(x, me)
                if best is None or value > best:
                    best, best_frames = value, fr
            frames += best_frames
        result = reply_end.result
        out["hands"].append({"hand": [_name(u.card_id) for u in w.hands[other_player(me)]],
                             "shallow": out["shallow"][k], "deep": out["deep"][k], "penalty": pens[k],
                             "after_reply": str(result.reason) + (" — they win" if result.winner != me else " — you win")
                             if result else "", "frames": frames})
    return out


# ------------------------------------------------------------------------------------------------ the server side

def _key(kind: str, body: dict) -> str:
    return kind + "_" + hashlib.sha1(json.dumps(body, sort_keys=True).encode()).hexdigest()[:16]


async def _run(kind: str, body: dict) -> dict:
    """Run one analysis in a child process (CPU-heavy, the server keeps serving), cached by its inputs and the code."""
    stamp = max(p.stat().st_mtime for p in (Path(__file__), ROOT / "animal_kingdom" / "bots" / "referee_bot.py",
                                             ROOT / "animal_kingdom" / "bots" / "turn_search.py"))
    if body.get("src") == "live":
        stamp = max(stamp, (MATCH_DIR / f"{Path(body['id']).name}.json").stat().st_mtime)
    path = CACHE / f"{_key(kind, {**body, 'stamp': stamp})}.json"
    if path.exists():
        return json.loads(path.read_text())
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-W", "ignore", "-m", "animal_kingdom.web.analyse", kind, json.dumps(body),
        cwd=str(ROOT), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        env={**os.environ, "AK_PY_BOTS": "1"})
    out, err = await proc.communicate()
    if proc.returncode != 0:
        raise web.HTTPInternalServerError(text=err.decode()[-2000:])
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_bytes(out)
    return json.loads(out)


def _pos(q) -> tuple:
    return q["src"], q["id"], int(q.get("n", 0)), int(q["ply"])


async def page(_req):
    return web.FileResponse(PAGE)


async def api_games(_req):
    return web.json_response(games())


async def api_moves(req):
    q = req.query
    return web.json_response(moves(q["src"], q["id"], int(q.get("n", 0))))


async def api_position(req):
    src, gid, n, ply = _pos(req.query)
    st = position(src, gid, n, ply)
    me = st.player_to_act()
    return web.json_response({"view": view(st, me), "me": me, "food": st.food, "turn": st.turn_counter,
                              "over": rules.is_terminal(st) is not None})


async def api_legal(req):
    body = await req.json()
    st = position(body["src"], body["id"], int(body.get("n", 0)), int(body["ply"]))
    return web.json_response(legal(st, body.get("after", [])))


async def api_search(req):
    body = await req.json()
    return web.json_response(await _run("search", {k: body[k] for k in ("src", "id", "n", "ply", "seed")}))


async def api_explain(req):
    body = await req.json()
    return web.json_response(await _run("explain", {k: body[k] for k in ("src", "id", "n", "ply", "seed", "turn")}))


def register(app: web.Application) -> None:
    app.add_routes([
        web.get("/analyse", page),
        web.get("/api/analyse/games", api_games),
        web.get("/api/analyse/moves", api_moves),
        web.get("/api/analyse/position", api_position),
        web.post("/api/analyse/legal", api_legal),
        web.post("/api/analyse/search", api_search),
        web.post("/api/analyse/explain", api_explain),
    ])


def main(argv: Optional[list] = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    kind, body = argv[0], json.loads(argv[1])
    if kind == "search":
        out = search(body["src"], body["id"], int(body.get("n", 0)), int(body["ply"]), int(body["seed"]))
    else:
        out = explain(body["src"], body["id"], int(body.get("n", 0)), int(body["ply"]), int(body["seed"]), body["turn"])
    sys.stdout.write(json.dumps(out))


if __name__ == "__main__":
    main()
