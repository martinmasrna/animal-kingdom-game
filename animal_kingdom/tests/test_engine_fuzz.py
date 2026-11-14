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
if not _PATH.exists():   # the live image ships the package and its tests, not tools/ (deploy/Dockerfile)
    pytest.skip("tools/engine_fuzz.py is not in this tree", allow_module_level=True)
_spec = importlib.util.spec_from_file_location("engine_fuzz", _PATH)
fuzz = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fuzz)


@pytest.mark.parametrize("seed", range(40))
def test_random_games_raise_nothing(seed):
    rec, _, state = fuzz.play(seed)
    assert rec is None, f"{rec['kind']} at index {rec['index']}: {rec['error']}\n{rec['traceback']}"
    assert rules.is_terminal(state) is not None


def test_long_game_ends_at_the_turn_cap():
    """A random game in which both decks and hands run dry and roaming keeps a player acting, so the two-idle-turns end
    never fires; the turn cap ends it. Seed 2077 on the 2026-11-12 card pool (a card change can move it: find the first
    seed whose game ends at the cap with both decks and hands empty)."""
    rec, n, state = fuzz.play(385, max_actions=100_000)   # 385 on the actions branch (its eight cards moved it)
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


# --- group: crash | engine/state.py ensure_mates | KeyError (the human-game probe, 2026-11-05) ---------------------------
# results/human_games/web/web_20261010T161459_LBFBOA.jsonl line 7: deck A still lists four old design ids
# (fish_legend_jellyfish, ...) that web/renamed.py does not map. new_game took them, and the logged game happened never
# to look one up; skipping the mulligan at action index 1 instead ends it, and ensure_mates raised KeyError on the
# unknown id in hand. A deck with a card the registry doesn't hold is now refused at setup, as the Rust engine does.

def _mixed_deck():
    return ["sardine"] * 3 + ["fish_legend_jellyfish"] + ["cod"] * 3 + ["mouse"] * 3


def test_unknown_card_id_is_refused_at_setup():
    from animal_kingdom.engine.state import new_game
    with pytest.raises(EngineError, match="fish_legend_jellyfish"):
        new_game(_mixed_deck(), ["sardine"] * 10, 22811793, first_player="B")


def test_the_logged_position_no_longer_crashes():
    """The probe's reproduction: the log either refuses at setup or every action at every position applies."""
    import json
    path = pathlib.Path(__file__).resolve().parents[2] / "results/human_games/web/web_20261010T161459_LBFBOA.jsonl"
    if not path.exists():
        pytest.skip("human game log not present")
    from animal_kingdom.web.renamed import renamed
    log = renamed(json.loads(path.read_text().splitlines()[7]))
    try:
        state, _, _ = fuzz._log_state(log)
    except EngineError as e:
        assert "unknown card" in str(e)
        return
    for index, adict in enumerate(log["actions"]):
        fuzz._skip_unlogged_mulligans(state, adict)
        assert fuzz.probe_position(state, {"log": "x", "index": index}) == []
        rules.apply_logged(state, adict)
