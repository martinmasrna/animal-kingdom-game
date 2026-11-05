"""Puzzle matches (web/match.py, server.py): a puzzle starts from its position with the defender's hand face up, the
defender is the solver's search, a wrong move fails it at once and a retry starts it over, the den solves it, and a
solved puzzle is remembered on the profile without ever reaching the match history or the game logs."""
from __future__ import annotations

import asyncio
import json

import pytest

from animal_kingdom import puzzles as P
from animal_kingdom.engine import rules
from animal_kingdom.web.match import PUZZLE_BOT, Match, Seat

LION = {"card": "lion", "owner": "A"}
ONE = {"id": "t_one", "title": "One", "theme": "test", "to_move": "A", "turns": 1,
       "board": {"1,2": [LION], "2,2": [LION], "3,2": [LION], "4,2": [LION], "5,2": [{"card": "hamster", "owner": "B"}]},
       "hands": {"A": ["lion", "lion"], "B": ["tortoise"]}, "food": {"A": 0, "B": 0},
       "hint": "Two Lions, two steps.", "why": "test",
       "solution": [{"kind": "place", "card_id": "lion", "target": ["cr", "5,2"]},
                    {"kind": "place", "card_id": "lion", "target": ["hq", "B"]}]}
TWO = {**ONE, "id": "t_two", "title": "Two", "turns": 2, "board": {"1,2": [LION], "2,2": [LION]},
       "hands": {"A": ["lion"] * 4, "B": ["pup", "pup"]},
       "solution": [{"kind": "place", "card_id": "lion", "target": ["cr", "3,2"]},
                    {"kind": "place", "card_id": "lion", "target": ["cr", "4,2"]}]}


@pytest.fixture
def puzzle_dir(tmp_path, monkeypatch):
    for pz in (ONE, TWO):
        (tmp_path / f"{pz['id']}.json").write_text(json.dumps(pz))
    monkeypatch.setattr(P, "PUZZLE_DIR", str(tmp_path))
    return tmp_path


def _puzzle(pid: str) -> Match:
    m = Match("T", Seat("ta", "You"))
    m.seats["B"] = Seat("tb", "Defender", bot=PUZZLE_BOT)
    m.start_puzzle(pid)
    return m


def _run_defender(m: Match) -> None:
    while m.phase == "playing" and m.to_act() == "B":
        m.act("B", m.bot_move())


def test_a_puzzle_opens_on_its_position_with_both_hands_face_up(puzzle_dir):
    m = _puzzle("t_two")
    v = m.view("A")
    g = v["game"]
    assert v["phase"] == "playing" and g["toAct"] == "A" and g["decision"] == "yours"
    assert [h["id"] for h in g["hand"]] == ["lion"] * 4
    assert [h["id"] for h in g["revealedHand"]] == ["pup", "pup"]       # the defender's hand, face up
    assert g["deckCount"] == {"A": 0, "B": 0} and not g["legal"]["draw"] and g["pending"] is None   # no deck, no mulligan
    assert sorted(g["board"]) == ["1,2", "2,2"]
    assert v["puzzle"] == {"id": "t_two", "title": "Two", "theme": "test", "turns": 2, "brief": "Take the den in 2 turns.",
                           "hint": "Two Lions, two steps.", "turnsLeft": 2, "status": "playing"}
    assert v["lists"] == {}                                              # no decks to show


def test_the_solution_solves_it_against_the_defenders_best_reply(puzzle_dir):
    m = _puzzle("t_two")
    for a in TWO["solution"]:
        m.act("A", a)
    assert m.view("A")["puzzle"]["turnsLeft"] == 1
    _run_defender(m)
    assert m.phase == "playing" and m.to_act() == "A"
    # the defender played the reply the search picks for the solver's own line
    assert m.actions[2:] == [{k: v for k, v in d.items() if k != "by"} for d in P.main_line(TWO)[2:] if d["by"] == "B"]
    for a in [d for d in P.main_line(TWO) if d["by"] == "A"][2:]:
        m.act("A", {k: v for k, v in a.items() if k != "by"})
    v = m.view("A")
    assert v["phase"] == "match_over" and v["game"]["result"] == {"winner": "A", "reason": "hq_capture"}
    assert v["puzzle"]["status"] == "solved"


def test_a_move_that_lets_the_den_go_fails_at_once_and_retry_starts_over(puzzle_dir):
    m = _puzzle("t_one")
    start = m.view("A")["game"]["board"]
    m.act("A", {"kind": "place", "card_id": "lion", "target": ["cr", "4,1"]})   # one action left: the den is out of reach
    v = m.view("A")
    assert v["phase"] == "match_over" and v["puzzle"]["status"] == "failed"
    assert v["game"]["result"] == {"winner": "B", "reason": "puzzle"}
    m.rematch()                                                          # retry: the same position from the start
    v = m.view("A")
    assert v["phase"] == "playing" and v["puzzle"]["status"] == "playing" and v["game"]["board"] == start
    assert [h["id"] for h in v["game"]["hand"]] == ["lion", "lion"]
    m.rematch()                                                          # and at any time, mid-puzzle too
    assert m.phase == "playing" and m.state.actions_taken_this_turn == 0


def test_the_defender_escapes_when_a_reply_does(puzzle_dir):
    # Its search is the verdict's: a defender's reply that escapes fails the puzzle where it stands.
    pz = {**TWO, "id": "t_esc", "hands": {"A": ["lion"] * 4, "B": ["grizzly_bear"]}}
    (puzzle_dir / "t_esc.json").write_text(json.dumps(pz))
    m = _puzzle("t_esc")
    m.act("A", TWO["solution"][0])
    assert m.phase == "match_over" and m.results[-1]["reason"] == "puzzle"
    # and the reply it would play is the Bear's block in front of the den
    s = P.play_line(P.build(pz), TWO["solution"])
    assert m.bots["B"].choose(None, rules.legal_actions(s), s).to_dict() == \
        {"kind": "place", "card_id": "grizzly_bear", "target": ["cr", "5,2"]}


def test_a_saved_puzzle_match_resumes_with_its_defender(puzzle_dir):
    m = _puzzle("t_two")
    m.act("A", TWO["solution"][0])
    back = Match.from_dict(json.loads(json.dumps(m.to_dict())))
    assert back.puzzle == "t_two" and back.view("A")["puzzle"]["status"] == "playing"
    back.act("A", TWO["solution"][1])
    _run_defender(back)
    assert back.to_act() == "A" and back.phase == "playing"


def test_the_server_remembers_a_solved_puzzle_and_keeps_nothing_else(puzzle_dir, monkeypatch, tmp_path):
    from aiohttp.test_utils import TestClient, TestServer
    from animal_kingdom.web import server
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")
    monkeypatch.setattr(server, "BOT_PAUSE", {"open": 0, "move": 0, "choice": 0})
    saved = []
    monkeypatch.setattr(server, "save_game", lambda *a: saved.append(a))

    async def run():
        async with TestClient(TestServer(server.make_app())) as c:
            me = await (await c.post("/api/profile", json={})).json()
            h = {"X-AK-Key": me["code"]}
            listed = await (await c.get("/api/puzzles", headers=h)).json()
            assert [(p["id"], p["turns"], p["solved"]) for p in listed] == [("t_one", 1, False), ("t_two", 2, False)]
            assert (await c.post("/api/match", json={"puzzle": "nope"}, headers=h)).status == 404
            m = await (await c.post("/api/match", json={"puzzle": "t_one"}, headers=h)).json()
            ws = await c.ws_connect(f"/ws/{m['id']}?token={m['token']}")
            for a in ONE["solution"]:
                await ws.send_json({"t": "act", "action": a})
            v = None
            while not v or v["phase"] != "match_over":
                msg = await ws.receive_json(timeout=5)
                v = msg["view"] if msg["t"] == "view" else v
            assert v["puzzle"]["status"] == "solved"
            await ws.close()
            listed = await (await c.get("/api/puzzles", headers=h)).json()
            assert [p["solved"] for p in listed] == [True, False]
            prof = await (await c.get("/api/me", headers=h)).json()
            assert not prof.get("history")                              # never in the match history
            current = await (await c.get("/api/current", headers=h)).json()
            assert current == {}                                         # nor a match to rejoin
    asyncio.run(run())
    assert saved == []                                                   # nor a game log


def test_on_the_main_line_neither_verdict_nor_defender_searches(monkeypatch):
    # The shipped line is proven by solve.py check; following it costs no search (a hard puzzle's proof takes seconds).
    pid = next(i for i in P.all_ids() if P.load(i)["turns"] == 2)
    line = P.load(pid)["main_line"]
    m = _puzzle(pid)
    monkeypatch.setattr(P.Solver, "wins", lambda *a, **k: (_ for _ in ()).throw(AssertionError("searched")))
    monkeypatch.setattr(P.Solver, "defence", lambda *a, **k: (_ for _ in ()).throw(AssertionError("searched")))
    for d in line:
        if d["by"] == "A":
            m.act("A", {k: v for k, v in d.items() if k != "by"})
        else:
            assert m.to_act() == "B"
            m.act("B", m.bot_move())
    assert m.view("A")["puzzle"]["status"] == "solved"
