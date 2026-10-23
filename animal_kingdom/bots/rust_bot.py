"""The bots on the Rust engine (engine_rs): the same search, the same evaluation, the same seeds and tie-breaks as the
Python bots (tools/engine_rs/bot_oracle.py holds them to the same move and the same root scores), twenty times
faster. `sim.runner.make_bot` builds one of these when AK_RUST_BOTS=1 and `ak_engine` is importable.

A RustBot mirrors the live Python GameState into the Rust engine on every decision (a dict round trip, under a
millisecond) and keeps its own search state across the game as the Python bot does (continuation plans, RNG streams).
"""
from __future__ import annotations

import dataclasses
import json
import os
from typing import Optional, Sequence

from ..engine.actions import Action, action_from_dict
from ..engine.resources import load_bundled_json
from ..engine.state import GameState, StateView
from .base import Bot

try:
    import ak_engine
except ImportError:  # pragma: no cover - the pure-Python tree
    ak_engine = None

_engines: dict = {}
_cards_json: Optional[str] = None
_maps_json: Optional[str] = None


def available() -> bool:
    return ak_engine is not None and os.environ.get("AK_RUST_BOTS") == "1" and os.environ.get("AK_PY_BOTS") != "1"


def engine_for(state: GameState):
    """The Rust engine for `state`'s config and map (built once per distinct config)."""
    global _cards_json, _maps_json
    key = (json.dumps(dataclasses.asdict(state.config), sort_keys=True), state.game_map.id)
    eng = _engines.get(key)
    if eng is None:
        if _cards_json is None:
            _cards_json = json.dumps(load_bundled_json("cards.json"))
            _maps_json = json.dumps(load_bundled_json("maps.json"))
        eng = ak_engine.Engine(_cards_json, _maps_json, key[0], key[1])
        _engines[key] = eng
    return eng


class RustBot(Bot):
    def __init__(self, spec: str, seed: int, evaluator_json: Optional[str] = None):
        self.spec = spec
        self.seed = seed
        self.bot = ak_engine.Bot(spec, seed, evaluator_json)
        self.last_search_stats: dict = {}

    def choose(self, view: StateView, legal: Sequence[Action], state: Optional[GameState] = None) -> Action:
        if state is None or len(legal) == 1:
            return legal[0]
        rs = engine_for(state).from_dict(state.to_dict())
        d = self.bot.choose(rs)
        self.last_search_stats = self.bot.stats() or {}
        self._last_roots = (rs, d)
        action = action_from_dict(d)
        if action not in legal:        # never happens when the two engines agree; the Python legality check is the guard
            raise RuntimeError(f"the Rust bot chose {d}, not a legal action here")
        return action

    def root_scores(self) -> list:
        """The last search's root candidates with their scores, as (action dict, score) pairs."""
        rs, _ = getattr(self, "_last_roots", (None, None))
        return self.bot.root_scores(rs) if rs is not None else []
