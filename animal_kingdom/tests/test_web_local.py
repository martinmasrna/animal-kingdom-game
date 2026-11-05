"""A practice match played in the browser (web/local.py): its finished log is taken back only when the Python engine
replays it to the end, and is then saved as a match played on the server is."""

import json
import random

import pytest

from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import SKIP, ChoiceAction
from animal_kingdom.engine.state import EngineError
from animal_kingdom.web import local
from animal_kingdom.web.match import Match, Seat


def _seats():
    return Seat("ta", "You", deck="cats"), Seat("tb", "Easy Bot", bot="easy", deck="egg_control")


def _browser_game(seed=7, rng_seed=3, stop=None):
    """A game as the browser plays it (both seats moving at random, the host's mulligan beside the bot's): its log."""
    rng = random.Random(rng_seed)
    m = Match("B", Seat("ta", "You", deck="cats"))
    m.rng = local._Seed(seed)
    m.join(Seat("tb", "Easy Bot", deck="egg_control"))
    while m.phase == "playing" and (stop is None or len(m.actions) < stop):
        if rules.early_mulligan(m.state, "A") is not None:   # the host keeps their hand while the bot's mulligan is asked
            m.act("A", ChoiceAction(SKIP).to_dict())
            continue
        m.act(m.to_act(), rng.choice(rules.legal_actions(m.state)).to_dict())
    return {"seed": seed, "first": m.state.first_player, "actions": list(m.actions),
            "times": [float(i) for i in range(len(m.actions))]}, m


def test_a_finished_browser_game_is_saved_as_a_server_match_is():
    body, played = _browser_game()
    logs, ended = [], []
    host, bot = _seats()
    m = local.replay("L1", host, bot, body, lambda match, rec: logs.append(rec), ended.append)
    assert m.phase == "match_over" and ended == [m]
    assert len(logs) == 1
    rec = logs[0]
    assert rec["seed"] == body["seed"] and rec["first_player"] == body["first"]
    assert rec["actions"] == body["actions"] and rec["winner"] == played.results[-1]["winner"]
    assert rec["bots"] == ["human", "easy"] and rec["action_times"] == body["times"]
    assert any("by" in a for a in body["actions"])   # the host's mulligan beside the bot's was in it
    json.dumps(rec)


def test_a_log_the_engine_refuses_is_refused_whole():
    body, _ = _browser_game()
    i = next(i for i, a in enumerate(body["actions"]) if a["kind"] == "place")
    body["actions"][i] = {**body["actions"][i], "target": ["cr", "9,9"]}
    with pytest.raises(EngineError):
        local.replay("L2", *_seats(), body, lambda *a: None, lambda *a: None)


def test_an_unfinished_game_counts_only_when_conceded():
    body, _ = _browser_game(stop=12)
    with pytest.raises(EngineError):
        local.replay("L3", *_seats(), body, lambda *a: None, lambda *a: None)
    logs = []
    m = local.replay("L4", *_seats(), {**body, "concede": True}, lambda match, rec: logs.append(rec), lambda *a: None)
    assert m.results[-1] == {**m.results[-1], "winner": "B", "reason": "concede"} and len(logs) == 1


def test_the_seed_and_first_player_must_be_the_games():
    body, _ = _browser_game()
    with pytest.raises(EngineError):
        local.replay("L5", *_seats(), {**body, "first": "B" if body["first"] == "A" else "A"}, lambda *a: None, lambda *a: None)
    with pytest.raises(EngineError):
        local.replay("L6", *_seats(), {**body, "seed": -1}, lambda *a: None, lambda *a: None)


def test_the_browser_gets_the_engine_the_server_plays():
    doc = json.loads(local.engine_doc())
    assert doc["map_id"] == "map_b" and doc["cards"] and doc["maps"]["maps"] and doc["config"]["actions_per_turn"] == 2
    spec = local.bot_spec("expert")
    assert spec["spec"].startswith("referee_learned:") and "eval=" not in spec["spec"] and json.loads(spec["evaluator"])
    assert local.bot_spec("normal") == {"spec": "turn:w.hq_threat_reach=0.5", "evaluator": None}
