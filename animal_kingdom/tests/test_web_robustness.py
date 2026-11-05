"""The server keeps a match going through what goes wrong around it: a bot that always fails or always overthinks, a
screen that stops reading or drops mid-turn, and a server restart in the middle of a game."""

import asyncio
import json
import random
import time

import pytest
from aiohttp.test_utils import TestClient, TestServer

from animal_kingdom.engine import rules
from animal_kingdom.web import custom_decks, guard, server
from animal_kingdom.web.match import Match


@pytest.fixture
def quiet(monkeypatch, tmp_path):
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")
    monkeypatch.setattr(server, "BOT_PAUSE", {"choice": 0, "open": 0, "move": 0})
    monkeypatch.setattr(custom_decks, "DECKS_FILE", tmp_path / "web_decks.json")
    monkeypatch.setattr(guard, "limiter", guard.Limiter())
    monkeypatch.setattr(server, "hub", server.Hub())


async def _play_to_the_end(match: Match, seat: str, rng: random.Random, timeout: float) -> None:
    """The person in `seat` plays random legal moves; the bot plays through the server's bot task."""
    t0 = time.time()
    while match.phase == "playing":
        assert time.time() - t0 < timeout, f"the match stopped moving (round {match.state.turn_counter // 2 + 1})"
        if match.to_act() == seat or (match.state.pending is None and rules.early_mulligan(match.state, seat) is not None):
            match.act(seat, rng.choice(rules.legal_actions(match.state)).to_dict())
            await server.hub.push(match)
        await asyncio.sleep(0.01)


@pytest.mark.parametrize("broken", ["raises", "overthinks"])
def test_a_bot_that_always_fails_still_plays_the_match_to_its_end(quiet, monkeypatch, broken):
    """Every one of the bot's moves fails (an exception) or runs past BOT_THINK_MAX: each is played by the fallback, so the
    game reaches its end; the stuck searches never stall the event loop."""
    monkeypatch.setattr(server, "BOT_THINK_MAX", 0.05)
    monkeypatch.setattr(Match, "bot_move", (lambda self: 1 / 0) if broken == "raises" else (lambda self: time.sleep(0.5)))

    async def body():
        async with TestClient(TestServer(server.make_app())) as c:
            m = await (await c.post("/api/match", json={"deck": "cats", "bot": {"level": "expert", "deck": "cats"}})).json()
            match = server.hub.matches[m["id"]]
            server.hub.kick_bot(match)
            await _play_to_the_end(match, "A", random.Random(3), timeout=60)
            return match.phase
    assert asyncio.run(body()) == "match_over"


class _Stalled:
    """A socket whose peer stopped reading: a send never completes."""
    closed = False

    async def send_json(self, msg):
        await asyncio.sleep(3600)

    async def close(self):
        await asyncio.sleep(3600)


class _Dead:
    closed = True

    async def send_json(self, msg):
        raise ConnectionError("Connection lost")

    async def close(self):
        pass


class _Live:
    closed = False

    def __init__(self):
        self.got = []

    async def send_json(self, msg):
        self.got.append(msg)

    async def close(self):
        pass


def test_a_stalled_or_dead_screen_never_holds_up_the_match_or_the_other_player(quiet, monkeypatch):
    """A phone gone off the network without closing fills its socket until sends block; one that has gone raises. Either is
    dropped within SEND_TIMEOUT, and the other screens get their view (2026-11-05: the stalled send held the match until the
    heartbeat, then its ConnectionError killed the opponent's own socket handler)."""
    monkeypatch.setattr(server, "SEND_TIMEOUT", 0.2)
    m = Match("T", server.Seat("ta", "A", deck="cats"))
    m.join(server.Seat("tb", "B", deck="cats"))
    live, stalled, dead = _Live(), _Stalled(), _Dead()
    server.hub.sockets["T"] = {(live, "A"), (stalled, "B"), (dead, "B")}

    async def body():
        t0 = time.time()
        await server.hub.broadcast(m)
        return time.time() - t0
    took = asyncio.run(body())
    assert took < 1.0
    assert [x["t"] for x in live.got] == ["view"]
    assert server.hub.sockets["T"] == {(live, "A")}


def test_a_friend_notice_to_a_stalled_tab_never_holds_up_the_sender(quiet, monkeypatch):
    monkeypatch.setattr(server, "SEND_TIMEOUT", 0.2)
    live, stalled = _Live(), _Stalled()
    monkeypatch.setitem(server.presence, "p1", {live, stalled})

    async def body():
        t0 = time.time()
        await server._tell("p1", {"t": "msg"})
        return time.time() - t0
    assert asyncio.run(body()) < 1.0
    assert live.got == [{"t": "msg"}] and server.presence["p1"] == {live}


async def _view(ws):
    """The socket's next view, acknowledged as played out, as the client does (else the bot waits BOT_WAIT_MAX)."""
    while True:
        d = json.loads((await asyncio.wait_for(ws.receive(), 10)).data)
        if d["t"] == "view":
            g = d["view"]["game"]
            if g and g["events"]:
                await ws.send_json({"t": "played", "seq": g["events"][-1]["seq"]})
            return d["view"]


async def _act_until(ws, view, rng, done):
    """Play the socket's seat with random legal moves until done(view)."""
    from animal_kingdom.engine.actions import SKIP
    while not done(view):
        g = view["game"]
        if g and g["toAct"] == view["you"] and g["decision"] in ("yours", "your_choice", "mulligan"):
            if g["pending"] and g["pending"]["mode"] == "choice":
                opts = [o["v"] for o in g["pending"]["options"]]
                a = {"kind": "choice", "choice": SKIP if g["pending"]["optional"] or not opts else rng.choice(opts)}
            elif g["legal"]["place"]:
                card = rng.choice(sorted(g["legal"]["place"]))
                a = {"kind": "place", "card_id": card, "target": rng.choice(g["legal"]["place"][card])}
            else:
                a = {"kind": "draw"} if g["legal"]["draw"] else {"kind": "pass"}
            await ws.send_json({"t": "act", "action": a})
        view = await _view(ws)
    return view


def test_a_player_whose_socket_drops_mid_turn_comes_back_to_the_same_turn(quiet):
    """The socket closes after the first of the turn's two actions; a new socket on the same seat (the client's reconnect,
    or another tab through /api/current) gets the same position and can finish the turn."""
    async def body():
        async with TestClient(TestServer(server.make_app())) as c:
            p = await (await c.post("/api/profile", json={})).json()
            key = {"X-AK-Key": p["code"]}
            m = await (await c.post("/api/match", json={"deck": "cats", "bot": {"level": "easy", "deck": "cats"}}, headers=key)).json()
            ws = await c.ws_connect(f"/ws/{m['id']}?token={m['token']}")
            rng = random.Random(5)
            mid_turn = lambda v: (v["game"] and v["game"]["toAct"] == v["you"] and v["game"]["decision"] == "yours"
                                  and v["game"]["actionsLeft"] < v["game"]["actionsTotal"]) or v["phase"] != "playing"
            before = await _act_until(ws, await _view(ws), rng, mid_turn)
            assert before["phase"] == "playing", "the game ended before a mid-turn moment"
            await ws.close()
            await asyncio.sleep(0.3)                              # the bot must not move in the player's turn meanwhile
            back = await (await c.get("/api/current", headers=key)).json()
            ws2 = await c.ws_connect(f"/ws/{back['id']}?token={back['token']}")
            after = await _view(ws2)
            g0, g1 = before["game"], after["game"]
            assert (g1["round"], g1["actionsLeft"], g1["decision"], g1["hand"]) == (g0["round"], g0["actionsLeft"], "yours", g0["hand"])
            end = await _act_until(ws2, after, rng, lambda v: v["phase"] != "playing")
            await ws2.close()
            return end["phase"]
    assert asyncio.run(body()) == "match_over"


def test_a_restart_in_the_middle_of_a_game_keeps_the_match(monkeypatch, tmp_path):
    """Matches are saved after every change and reloaded at startup: a new server process (a deploy, a crash) picks the
    game up where it was, same seat tokens, same position, and it plays to its end."""
    monkeypatch.delenv("AK_NO_GAME_LOGS", raising=False)
    monkeypatch.setenv("AK_DB", str(tmp_path / "web.db"))
    monkeypatch.setattr(server, "BOT_PAUSE", {"choice": 0, "open": 0, "move": 0})
    for name in ("MATCH_DIR", "LOG_DIR", "REPLAY_DIR", "STUDY_DATA_DIR"):
        monkeypatch.setattr(server, name, tmp_path / name.lower())
    monkeypatch.setattr(custom_decks, "DECKS_FILE", tmp_path / "web_decks.json")
    monkeypatch.setattr(guard, "limiter", guard.Limiter())
    rng = random.Random(9)

    async def first():
        monkeypatch.setattr(server, "hub", server.Hub())
        async with TestClient(TestServer(server.make_app())) as c:
            p = await (await c.post("/api/profile", json={})).json()
            m = await (await c.post("/api/match", json={"deck": "cats", "bot": {"level": "easy", "deck": "canines"}},
                                    headers={"X-AK-Key": p["code"]})).json()
            ws = await c.ws_connect(f"/ws/{m['id']}?token={m['token']}")
            v = await _act_until(ws, await _view(ws), rng,
                                 lambda v: v["phase"] != "playing" or (v["game"]["round"] >= 3 and v["game"]["toAct"] == v["you"]
                                                                      and v["game"]["decision"] == "yours"))
            await ws.close()
            return m, v, server.hub.matches[m["id"]].state.to_dict()

    async def second(m):
        monkeypatch.setattr(server, "hub", server.Hub())          # a new process: nothing in memory
        async with TestClient(TestServer(server.make_app())) as c:
            assert m["id"] in server.hub.matches
            ws = await c.ws_connect(f"/ws/{m['id']}?token={m['token']}")
            v = await _view(ws)
            state = server.hub.matches[m["id"]].state.to_dict()
            end = await _act_until(ws, v, rng, lambda v: v["phase"] != "playing")
            await ws.close()
            return v, state, end["phase"]

    m, before, state_before = asyncio.run(first())
    assert before["phase"] == "playing", "the game ended before round 3"
    after, state_after, phase = asyncio.run(second(m))
    assert state_after == state_before
    assert (after["game"]["round"], after["game"]["hand"], after["game"]["board"]) == \
        (before["game"]["round"], before["game"]["hand"], before["game"]["board"])
    assert phase == "match_over"
