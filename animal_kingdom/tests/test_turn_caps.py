"""The turn's two caps (Config.max_actions_per_turn, max_effect_steps_per_turn): a looping combination of cards ends
the turn instead of running for ever, and every cap that fires is flagged (the `turn_capped` event and `state.caps`),
the same in both engines (Martin, 2026-11-18)."""

from __future__ import annotations

import dataclasses
import json

import pytest

from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import ChoiceAction, PlaceAction
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.resources import load_bundled_json

from ._helpers import make_state, put


def vole_pair():
    """A Vole on the board and one in hand: placing it beside the first makes two replay each other."""
    s = make_state(hands={"A": ["vole"]}, decks={"A": ["lion"] * 5, "B": ["lion"] * 5})
    put(s, "1,2", "vole", "A")
    return s


def looping_stack(cap=50):
    """A position with `cap + 30` effect steps waiting that need no input (a loop of cards, stood in for)."""
    s = make_state(hands={"A": ["lion"]}, decks={"A": ["lion"] * 5, "B": ["lion"] * 5},
                   config=dataclasses.replace(Config.default(), max_effect_steps_per_turn=cap))
    s.effect_stack.extend({"op": "gain_food", "player": "A", "amount": 1, "by_card": "squirrel"} for _ in range(cap + 30))
    return s


def test_two_voles_ask_a_choice_each_round_so_the_action_cap_ends_them_and_flags_it():
    s = vole_pair()
    rules.apply_action(s, PlaceAction("vole", ("cr", "1,1")))
    n = 1
    while s.current == "A":
        assert s.pending["options"] == ["1,2"] or s.pending["options"] == ["1,1"]       # always the other Vole
        rules.apply_action(s, ChoiceAction(s.pending["options"][0]))
        n += 1
    assert n == s.config.max_actions_per_turn and s.pending is None and not s.effect_stack
    assert [(c["cap"], c["player"], c["cards"]) for c in s.caps] == [("actions", "A", ["vole"])]
    assert [e for e in s.events if e["e"] == "turn_capped"] == [{"e": "turn_capped", **s.caps[0]}]


def test_effect_steps_that_need_no_input_end_the_turn_at_the_effect_cap_and_flag_it():
    s = looping_stack()
    rules.apply_action(s, PlaceAction("lion", ("cr", "1,1")))
    assert s.current == "B" and not s.effect_stack and s.pending is None and s.effect_steps_this_turn == 0
    assert s.food["A"] == 50                      # exactly the cap's worth resolved
    assert [(c["cap"], c["player"], c["cards"]) for c in s.caps] == [("effect_steps", "A", ["squirrel"])]
    assert sum(e["e"] == "turn_capped" for e in s.events) == 1


def test_a_turn_under_both_caps_flags_nothing():
    s = make_state(hands={"A": ["lion"]}, decks={"A": ["lion"] * 5, "B": ["lion"] * 5})
    rules.apply_action(s, PlaceAction("lion", ("cr", "1,1")))
    assert s.caps == [] and not any(e["e"] == "turn_capped" for e in s.events)


# ------------------------------------------------------------------------------------------------ both engines

ak_engine = pytest.importorskip("ak_engine")


def _canon(d):
    return json.dumps(d, sort_keys=True, default=list)


def _rust_twin(s):
    eng = ak_engine.Engine(json.dumps(load_bundled_json("cards.json")), json.dumps(load_bundled_json("maps.json")),
                           json.dumps(dataclasses.asdict(s.config)), "map_a")
    rs = eng.from_dict(json.loads(_canon(s.to_dict())))
    assert _canon(rs.to_dict()) == _canon(s.to_dict())
    return rs


def _both(s, rs, action):
    rules.apply_action(s, action)
    rs.apply_action(action.to_dict())
    assert _canon(rs.to_dict()) == _canon(s.to_dict()), action


def test_both_engines_cap_the_two_voles_at_the_same_action():
    s = vole_pair()
    rs = _rust_twin(s)
    _both(s, rs, PlaceAction("vole", ("cr", "1,1")))
    n = 1
    while s.current == "A":
        _both(s, rs, ChoiceAction(s.pending["options"][0]))
        n += 1
    assert n == s.config.max_actions_per_turn
    assert rs.to_dict()["caps"] == s.to_dict()["caps"] and len(s.caps) == 1


def test_both_engines_cap_a_stack_of_steps_at_the_same_step():
    s = looping_stack()
    rs = _rust_twin(s)
    _both(s, rs, PlaceAction("lion", ("cr", "1,1")))
    assert s.food["A"] == rs.to_dict()["food"]["A"] == 50
    assert rs.to_dict()["caps"] == s.to_dict()["caps"] and len(s.caps) == 1
