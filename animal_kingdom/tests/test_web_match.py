"""The web client's match model: series flow, seat checks, and what each seat's view may show."""

import json
import random

import pytest

from animal_kingdom.engine import rules
from animal_kingdom.engine.state import EngineError
from animal_kingdom.web.match import Match, Seat


def _match(bots=("easy", "easy"), decks=("cats_midrange", "egg_control")) -> Match:
    m = Match("T", Seat("ta", "A", bot=bots[0], deck=decks[0]))
    m.join(Seat("tb", "B", bot=bots[1], deck=decks[1]))
    return m


def _play_out_game(m: Match, rng: random.Random) -> None:
    while m.phase == "playing":
        s = m.to_act()
        m.act(s, rng.choice(rules.legal_actions(m.state)).to_dict())


def test_humans_start_only_when_both_ready():
    m = Match("T", Seat("ta", "A", deck="ramp"))
    assert m.phase == "lobby"
    m.join(Seat("tb", "B", deck="ramp"))
    assert m.phase == "prematch"
    m.ready("A")
    assert m.phase == "prematch"
    m.ready("B")
    assert m.phase == "playing"


def test_series_ends_at_two_wins_and_loser_goes_first():
    rng = random.Random(3)
    m = _match()
    while m.phase != "match_over":
        _play_out_game(m, rng)
        last = m.results[-1]
        if m.phase == "game_over":
            m.next_game()
            if last["winner"]:
                assert m.state.first_player != last["winner"]
    score = m.score()
    assert max(score.values()) == 2 or len(m.results) == 3


def test_rejects_the_wrong_seat_and_illegal_moves():
    m = _match()
    s = m.to_act()
    other = "B" if s == "A" else "A"
    with pytest.raises(EngineError):
        m.act(other, {"kind": "draw"})
    with pytest.raises(EngineError):
        m.act(s, {"kind": "place", "card_id": "lion", "target": ["hq", other]})


def test_view_hides_the_opponents_hand_and_deck_order():
    rng = random.Random(7)
    m = _match()
    for _ in range(12):
        m.act(m.to_act(), rng.choice(rules.legal_actions(m.state)).to_dict())
    view = m.view("A")
    game = view["game"]
    assert [h["iid"] for h in game["hand"]] == [u.iid for u in m.state.hands["A"]]
    b_hand_iids = {u.iid for u in m.state.hands["B"]}
    assert not b_hand_iids & {h["iid"] for h in game["hand"]}
    assert "decks" not in game and "hands" not in json.dumps(game)
    # The opponent's unseen cards are a multiset, which open decklists make public anyway.
    assert sum(game["unseen"].values()) == len(m.state.decks["B"]) + len(m.state.hands["B"])


def test_every_view_is_json_and_offers_legal_choices():
    rng = random.Random(11)
    m = _match(decks=("egg_control", "food_otk"))
    while m.phase == "playing":
        s = m.to_act()
        game = json.loads(json.dumps(m.view(s)))["game"]
        legal = rules.legal_actions(m.state)
        if game["pending"] and game["pending"]["mode"] == "choice":
            offered = {json.dumps(o["v"]) for o in game["pending"]["options"]}
            assert offered == {json.dumps(a.choice) for a in legal if a.kind == "choice" and a.choice != "__skip__"}
        m.act(s, rng.choice(legal).to_dict())


def test_game_log_replays_to_the_same_result():
    from animal_kingdom.sim.replay import replay
    rng = random.Random(5)
    logs = []
    m = _match(decks=("food_otk", "aggro_hq_rush"))
    m.on_game_end = lambda match, rec: logs.append(json.loads(json.dumps(rec)))
    _play_out_game(m, rng)
    _, result, _ = replay(logs[0])
    assert (result.winner, result.reason) == (logs[0]["winner"], logs[0]["reason"])


def test_notes_are_pinned_to_the_point_of_the_game():
    rng = random.Random(9)
    logs = []
    m = _match()
    m.on_game_end = lambda match, rec: logs.append(rec)
    m.act(m.to_act(), rng.choice(rules.legal_actions(m.state)).to_dict())
    m.add_note("A", "  going wide here  ")
    m.add_note("A", "   ")
    _play_out_game(m, rng)
    notes = logs[0]["notes"]
    assert [(n["at"], n["seat"], n["round"], n["text"]) for n in notes] == [(1, "A", 1, "going wide here")]
    assert len(logs[0]["action_times"]) == len(logs[0]["actions"])
