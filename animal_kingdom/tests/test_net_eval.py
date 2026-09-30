"""NetEval: the value network behind the evaluator seam - artifact round trip, load_eval
dispatch, the terminal contract, and a search decision driven by it."""

from __future__ import annotations

import json
import math
import random

from animal_kingdom.bots import features
from animal_kingdom.bots.learned_eval import load_eval
from animal_kingdom.bots.net_eval import NetEval
from animal_kingdom.bots.turn_bot import TurnBot
from animal_kingdom.engine import rules
from animal_kingdom.engine.state import Result

from ._helpers import make_state, put


def _net(hidden=4, seed=0) -> NetEval:
    n = len(features.feature_names("rung2"))
    rng = random.Random(seed)
    return NetEval(feature_set="rung2", mean=(0.0,) * n, std=(1.0,) * n,
                   w1=tuple(tuple(rng.uniform(-.1, .1) for _ in range(n)) for _ in range(hidden)),
                   b1=(0.1,) * hidden, w2=tuple(rng.uniform(-1, 1) for _ in range(hidden)),
                   b2=0.0, scale=40.0)


def _state():
    s = make_state(hands={"A": ["lion", "mouse"], "B": ["lion"]},
                   decks={"A": ["mouse"] * 4, "B": ["mouse"] * 4})
    put(s, "1,2", "lion", "A")
    return s


def test_round_trip_and_load_eval_dispatch(tmp_path):
    net = _net()
    path = tmp_path / "net.json"
    net.save(str(path))
    loaded = load_eval(str(path))
    assert isinstance(loaded, NetEval)
    assert loaded == NetEval.from_dict(json.loads(path.read_text()))
    assert loaded.value(_state(), "A") == net.value(_state(), "A")


def test_terminal_contract():
    s = _state()
    s.result = Result("A", "hq_capture")
    assert _net().value(s, "A") == math.inf
    assert _net().value(s, "B") == -math.inf


def test_search_runs_on_the_net():
    s = _state()
    action = TurnBot(seed=0, evaluator=_net()).choose(s.view_for("A"), rules.legal_actions(s), s)
    assert action in rules.legal_actions(s)
