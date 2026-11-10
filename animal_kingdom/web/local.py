"""A practice match played in the browser (the default for a practice match against a bot; `?local=0` opts out; static/local/): the engine and the bot run there as WebAssembly
(engine_rs/wasm.sh), the server sees the match only when it ends. Here: what the browser needs to start one (the cards,
maps and Config the server plays with, the decks, the bot's spec), and the finished match taken back in.

The finished match is replayed through a real `Match`, seed and first player as the browser had them and every action
validated by the Python engine, so it is saved exactly as a match played on the server is: the game log, the players'
history and the replay (the callbacks the server gives every match). A log the engine refuses is refused whole.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import time
from pathlib import Path
from typing import Callable, Optional

from ..engine.config import Config
from ..engine.resources import load_bundled_json
from ..engine.state import EngineError
from ..sim.runner import rust_spec
from .match import BOT_LEVELS, DECK_NAMES, MAP_ID, Match, Seat

try:
    import ak_engine
except ImportError:  # pragma: no cover - a server without the Rust engine plays every match itself
    ak_engine = None

MAX_ACTIONS = 5000     # a game's actions (the engine ends a game long before: max_turns)
_engine_doc: Optional[str] = None


def source_hash() -> Optional[str]:
    """The Rust engine's source hash (engine_rs/build.rs), or None without it: the browser plays locally only on a match."""
    f = getattr(ak_engine, "source_hash", None)
    return f() if f else None


def engine_doc() -> str:
    """What the browser's engine is built from, as JSON text (built once: the cards and the Config load at startup)."""
    global _engine_doc
    if _engine_doc is None:
        _engine_doc = json.dumps({"source_hash": source_hash(), "map_id": MAP_ID,
                                  "cards": load_bundled_json("cards.json"), "maps": load_bundled_json("maps.json"),
                                  "config": dataclasses.asdict(Config.default())})
    return _engine_doc


def bot_spec(level: str) -> dict:
    """The bot of a level as the browser builds it: the Rust spec and, for a learned evaluator, its artifact."""
    spec, evaluator = rust_spec(BOT_LEVELS[level])
    return {"spec": spec, "evaluator": evaluator, "cand": cand_url(spec)}


_cands: dict[str, tuple[str, str]] = {}     # a candidate network's path -> (its address, its text)


def _cand(path: str) -> tuple[str, str]:
    if path not in _cands:
        text = (Path(__file__).resolve().parents[2] / path).read_text()
        _cands[path] = (f"/api/local/cand/{hashlib.sha1(text.encode()).hexdigest()[:16]}", text)
    return _cands[path]


def cand_url(spec: str) -> Optional[str]:
    """Where the browser fetches the candidate network a spec's `cand=` names (the whole-turn search), None without one.
    The address carries the artifact's hash, so a browser keeps it until the network changes."""
    path = next((kv[5:] for kv in spec.replace(":", ",").split(",") if kv.startswith("cand=")), None)
    return _cand(path)[0] if path else None


def cand_text(url: str) -> Optional[str]:
    """The artifact at an address `cand_url` gave, None for any other."""
    return next((text for u, text in _cands.values() if u == url), None)


def seats_view(host: Seat, bot: Seat) -> dict:
    """The view's `seats`, as Match.view gives them to the host."""
    return {p: {"name": s.name, "bot": s.bot, "ready": True, "deck": s.deck, "deckName": DECK_NAMES.get(s.deck, s.deck)}
            for p, s in (("A", host), ("B", bot))}


class _Seed:
    """Stands in for Match.rng: the game's seed is the one the browser played."""
    def __init__(self, seed: int):
        self.seed = seed

    def randrange(self, _n: int) -> int:
        return self.seed


def replay(match_id: str, host: Seat, bot: Seat, body: dict, on_game_end: Callable, on_match_end: Callable) -> Match:
    """The browser's finished match as a Match, its game ended and saved through the two callbacks. `body`: seed, first
    (who went first, as the browser's game had it), actions (as Match.actions keeps them, a mulligan made beside the
    other's carrying "by"), times (seconds since the start, one per action), and concede (the host gave up at the end)."""
    seed, first, actions = body.get("seed"), body.get("first"), body.get("actions")
    times = body.get("times") or []
    if not isinstance(seed, int) or not 0 <= seed < 1 << 30 or first not in ("A", "B"):
        raise EngineError("bad seed or first player")
    if not isinstance(actions, list) or len(actions) > MAX_ACTIONS or not all(isinstance(a, dict) for a in actions):
        raise EngineError("bad actions")
    m = Match(match_id, host)
    m.rng = _Seed(seed)
    m.last_game = {"winner": None, "first": first}    # _start_game: a drawn last game keeps its first player
    m.on_game_end, m.on_match_end = on_game_end, on_match_end
    m.join(bot)
    if m.state.first_player != first:
        raise EngineError("first player does not match")
    m.last_game = None
    for i, a in enumerate(actions):
        if m.phase != "playing":
            raise EngineError(f"action {i} after the game ended")
        if i == len(actions) - 1 and len(times) == len(actions):   # the last action lands at the browser's time
            m.started_at = time.time() - float(times[-1])
        by = a.get("by")
        m.act(by if by in ("A", "B") else m.to_act(), a)
        if len(times) == len(actions):
            m.action_times[-1] = round(float(times[i]), 1)
    if m.phase == "playing" and body.get("concede"):
        m.concede("A")
    if m.phase != "match_over":
        raise EngineError("the game is not over")
    return m
