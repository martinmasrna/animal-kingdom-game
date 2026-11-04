"""Puzzle mode: the solver on hand-built positions, and every shipped puzzle file (animal_kingdom/puzzles.py)."""
from __future__ import annotations

import pytest

from animal_kingdom import puzzles as P
from animal_kingdom.engine import rules

LIONS = {cr: [{"card": "lion", "owner": "A"}] for cr in ("1,2", "2,2", "3,2", "4,2")}


def _pz(board, hand_a, hand_b, turns, **kw):
    return {"id": "t", "title": "t", "theme": "t", "to_move": "A", "turns": turns, "board": board,
            "hands": {"A": hand_a, "B": hand_b}, "food": {"A": 0, "B": 0}, "solution": [], "hint": "", "why": "", **kw}


def test_forced_in_one_has_one_winning_turn():
    # Lions up the middle to 4,2; B's Hamster (3) on 5,2. Cover it, then take the den: the only way.
    pz = _pz({**LIONS, "5,2": [{"card": "hamster", "owner": "B"}]}, ["lion", "lion"], ["tortoise"], 1)
    rep = P.solve(pz)
    assert rep["status"] == "forced"
    lines = [w["line"] for w in rep["winning_first_turns"]]
    assert lines == [[{"kind": "place", "card_id": "lion", "target": ["cr", "5,2"]},
                      {"kind": "place", "card_id": "lion", "target": ["hq", "B"]}]]


def test_forced_in_two():
    # Lions to 2,2, three more in hand: four placements reach the den. B's Pups can't cover a 7, and nothing else stops it.
    board = {cr: v for cr, v in LIONS.items() if cr in ("1,2", "2,2")}
    pz = _pz(board, ["lion"] * 4, ["pup", "pup"], 2)
    assert P.solve(pz)["status"] == "forced"
    assert P.solve({**pz, "turns": 1})["status"] == "not forced"


def test_not_forced_when_one_reply_escapes():
    # The same race against a Grizzly Bear (8): wherever A's two Lions go, the Bear stands in front of the den where
    # they must pass, and two actions are no longer enough.
    board = {cr: v for cr, v in LIONS.items() if cr in ("1,2", "2,2")}
    pz = _pz(board, ["lion"] * 4, ["grizzly_bear"], 2)
    rep = P.solve(pz)
    assert rep["status"] == "not forced" and not rep["winning_first_turns"]
    # Against the natural first turn the defence finds the escape, and it is the Bear's block.
    sv = P.Solver(2)
    after = P.play_line(P.build(pz), [{"kind": "place", "card_id": "lion", "target": ["cr", "3,2"]},
                                      {"kind": "place", "card_id": "lion", "target": ["cr", "4,2"]}])
    reply = sv.defence(after)
    assert reply and reply[0].to_dict() == {"kind": "place", "card_id": "grizzly_bear", "target": ["cr", "5,2"]}
    end = after.clone()
    for a in reply:
        rules.apply_action(end, a)
    assert not sv.wins(end)


def test_node_cap_reports_unproven():
    board = {cr: v for cr, v in LIONS.items() if cr in ("1,2", "2,2")}
    rep = P.solve(_pz(board, ["lion"] * 4, ["grizzly_bear"], 2), node_cap=5)
    assert rep["status"] == "unproven"


def test_random_cards_are_refused():
    pz = _pz({**LIONS}, ["lion", "sunfish"], [], 1)
    assert any("random" in p for p in P.position_problems(pz))


def test_chance_from_the_stream_is_refused():
    # A City Spider's Dawn removes the weakest animal next to it; two Pups tie, so the stream would pick one.
    pz = _pz({"5,2": [{"card": "city_spider", "owner": "B"}], "4,2": [{"card": "pup", "owner": "A"}],
              "5,1": [{"card": "pup", "owner": "A"}], "1,2": [{"card": "pup", "owner": "A"}]}, ["pup"], [], 2)
    with pytest.raises(P.ChanceError):
        P.solve(pz)


@pytest.mark.parametrize("puzzle_id", P.all_ids())
def test_shipped_puzzle(puzzle_id):
    """Every file in data/puzzles: a legal, chance-free position whose solution forces the den, one or two winning
    first turns, and a main line the client can play to the den."""
    pz = P.load(puzzle_id)
    assert pz["id"] == puzzle_id
    assert P.check(pz) == []
