"""The engine crash fuzzer (tools/engine_fuzz.py) and the positions it found.

The 2026-11-05 run (knowledge/audit/engine-fuzz-2026-11-05.md) found no exception and no refused action in 5,000
games (nor in 115,000 more); its only group is games that run past 300 actions, every one a lone roaming unit after both
decks ran out, ended by the turn cap. These tests keep that true and keep the tool able to see a failure.
"""
from __future__ import annotations

import importlib.util
import pathlib

import pytest

from animal_kingdom.engine import rules
from animal_kingdom.engine.state import EngineError

_PATH = pathlib.Path(__file__).resolve().parents[2] / "tools" / "engine_fuzz.py"
_spec = importlib.util.spec_from_file_location("engine_fuzz", _PATH)
fuzz = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fuzz)


@pytest.mark.parametrize("seed", range(40))
def test_random_games_raise_nothing(seed):
    rec, _, state = fuzz.play(seed)
    assert rec is None, f"{rec['kind']} at index {rec['index']}: {rec['error']}\n{rec['traceback']}"
    assert rules.is_terminal(state) is not None


def test_long_game_ends_at_the_turn_cap():
    """Seed 2800 (the 5,000-game run's one long game): both decks and hands run dry, A's units roam back and forth, B has
    nothing and passes. A roam is acting, so the two-idle-turns end never fires; the turn cap ends it, at action 369."""
    rec, n, state = fuzz.play(2800, max_actions=100_000)
    assert rec is None
    result = rules.is_terminal(state)
    assert result is not None and result.reason == "max_turns"
    assert state.turn_counter == state.config.max_turns
    assert not any(state.decks[p] or state.hands[p] for p in "AB")


def test_the_fuzzer_sees_a_crash(monkeypatch):
    real = rules.apply_action
    calls = {"n": 0}

    def flaky(state, action, **kw):
        calls["n"] += 1
        if calls["n"] == 5:
            raise KeyError("planted")
        return real(state, action, **kw)

    monkeypatch.setattr(fuzz.rules, "apply_action", flaky)
    rec, n, _ = fuzz.play(0)
    assert rec["kind"] == "crash" and rec["call"] == "apply_action" and "planted" in rec["error"]
    assert rec["seed"] == 0 and rec["deck_a"] and rec["action"] is not None


def test_the_fuzzer_sees_a_refusal(monkeypatch):
    real = rules.apply_action

    def refuse_roams(state, action, **kw):
        if getattr(action, "kind", None) == "roam":
            raise EngineError("planted refusal")
        return real(state, action, **kw)

    monkeypatch.setattr(fuzz.rules, "apply_action", refuse_roams)
    rec = next(r for r in (fuzz.play(s)[0] for s in range(50)) if r)
    assert rec["kind"] == "refused" and rec["action"]["kind"] == "roam"


def test_a_reproduction_rebuilds_its_position():
    """play(seed, stop_at=i) stops before action i: the position a failing test rebuilds."""
    _, n, end = fuzz.play(7)
    _, k, mid = fuzz.play(7, stop_at=n // 2)
    assert k == n // 2 and rules.is_terminal(mid) is None
    for a in rules.legal_actions(mid)[:1]:
        rules.apply_action(mid, a)
