"""The server keeps a match going through what goes wrong around it: a bot that always fails or always overthinks, a
screen that stops reading or drops mid-turn, and a server restart in the middle of a game."""

import asyncio
import json
import random
import time
from animal_kingdom.tests._helpers import DECK, SLUG  # noqa: F401

import pytest
from aiohttp.test_utils import TestClient, TestServer

from animal_kingdom import game as rules
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
            p = await (await c.post("/api/profile", json={})).json()
            m = await (await c.post("/api/match", json={"deck": DECK, "bot": True},
                                    headers={"X-AK-Key": p["code"]})).json()
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
    m = Match("T", server.Seat("ta", "A", deck=SLUG))
    m.join(server.Seat("tb", "B", deck=SLUG))
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


def test_the_bots_mulligan_swaps_never_wait_on_a_screen_that_cannot_see_them(quiet, monkeypatch):
    """A seat's view carries none of the other seat's mulligan swaps, so its screen can never report them played out:
    the bot goes on at once after a swap, never after BOT_WAIT_MAX (six seconds a card it returned)."""
    swaps, bot_move = [], Match.bot_move

    def swapping(self):   # the bot returns two cards, then plays as it would
        if self.mulliganing() and len(swaps) < 2:
            swaps.append(next(a for a in rules.legal_actions(self.state) if getattr(a, "choice", rules.SKIP) != rules.SKIP))
            return swaps[-1]
        return bot_move(self)
    monkeypatch.setattr(Match, "bot_move", swapping)

    async def body():
        async with TestClient(TestServer(server.make_app())) as c:
            p = await (await c.post("/api/profile", json={})).json()
            m = await (await c.post("/api/match", json={"deck": DECK, "bot": True}, headers={"X-AK-Key": p["code"]})).json()
            ws = await c.ws_connect(f"/ws/{m['id']}?token={m['token']}")
            match, t0, kept = server.hub.matches[m["id"]], time.time(), False
            while match.phase != "playing" or match.mulliganing():
                view = await _view(ws)
                g = view["game"]
                if g and not kept and g["decision"] == "mulligan" and g["toAct"] == view["you"]:
                    await ws.send_json({"t": "act", "action": {"kind": "choice", "choice": rules.SKIP}})
                    kept = True
            return time.time() - t0
    assert asyncio.run(body()) < 3.0 and len(swaps) == 2


async def _act_until(ws, view, rng, done):
    """Play the socket's seat with random legal moves until done(view)."""
    from animal_kingdom.game import SKIP
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
                a = {"kind": "pass"}
            await ws.send_json({"t": "act", "action": a})
        view = await _view(ws)
    return view


def test_a_player_whose_socket_drops_mid_turn_comes_back_to_the_same_turn(quiet):
    """The socket closes after the turn's first play; a new socket on the same seat (the client's reconnect,
    or another tab through /api/current) gets the same position and can finish the turn."""
    async def body():
        async with TestClient(TestServer(server.make_app())) as c:
            p = await (await c.post("/api/profile", json={})).json()
            key = {"X-AK-Key": p["code"]}
            m = await (await c.post("/api/match", json={"deck": DECK, "bot": True}, headers=key)).json()
            ws = await c.ws_connect(f"/ws/{m['id']}?token={m['token']}")
            rng = random.Random(5)
            mid_turn = lambda v: (v["game"] and v["game"]["toAct"] == v["you"] and v["game"]["decision"] == "yours"
                                  and v["game"]["mana"][v["you"]]["left"] < v["game"]["mana"][v["you"]]["total"]) or v["phase"] != "playing"
            before = await _act_until(ws, await _view(ws), rng, mid_turn)
            assert before["phase"] == "playing", "the game ended before a mid-turn moment"
            await ws.close()
            await asyncio.sleep(0.3)                              # the bot must not move in the player's turn meanwhile
            back = await (await c.get("/api/current", headers=key)).json()
            ws2 = await c.ws_connect(f"/ws/{back['id']}?token={back['token']}")
            after = await _view(ws2)
            g0, g1 = before["game"], after["game"]
            assert (g1["round"], g1["mana"], g1["decision"], g1["hand"]) == (g0["round"], g0["mana"], "yours", g0["hand"])
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
    for name in ("MATCH_DIR", "LOG_DIR"):
        monkeypatch.setattr(server, name, tmp_path / name.lower())
    monkeypatch.setattr(custom_decks, "DECKS_FILE", tmp_path / "web_decks.json")
    monkeypatch.setattr(guard, "limiter", guard.Limiter())
    rng = random.Random(9)

    async def first():
        monkeypatch.setattr(server, "hub", server.Hub())
        async with TestClient(TestServer(server.make_app())) as c:
            p = await (await c.post("/api/profile", json={})).json()
            m = await (await c.post("/api/match", json={"deck": DECK, "bot": True},
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


def test_a_saved_match_with_a_card_that_left_the_game_is_skipped_at_startup(monkeypatch, tmp_path, caplog):
    """A match saved before a card was removed can't be read by today's engine: the server starts without it, on one
    log line, and every other saved match comes back."""
    from animal_kingdom.web.match import Match, Seat
    monkeypatch.delenv("AK_NO_GAME_LOGS", raising=False)
    monkeypatch.setattr(server, "MATCH_DIR", tmp_path)
    saved = {}
    for mid in ("good", "stale"):
        m = Match(mid, Seat("ta", "Ann", deck=SLUG))
        m.join(Seat("tb", "Bob", deck=SLUG))
        saved[mid] = m.to_dict()
    hand = saved["stale"]["state"]["hands"]["A"]
    hand[0]["card_id"] = "a_card_that_left"
    for mid, d in saved.items():
        (tmp_path / f"{mid}.json").write_text(json.dumps(d), encoding="utf-8")
    hub = server.Hub()
    with caplog.at_level("WARNING"):
        hub.load()
    assert set(hub.matches) == {"good"}
    skipped = [r for r in caplog.records if "stale.json" in r.getMessage()]
    assert len(skipped) == 1 and skipped[0].exc_info is None and "a_card_that_left" in skipped[0].getMessage()


def test_an_idle_match_leaves_memory_and_comes_back_from_its_file(monkeypatch, tmp_path):
    """A server keeping every match it ever made ran out of memory under load; forget() lets go of idle ones and get()
    reloads one from its file the moment someone asks for it (a socket, a join). One with a socket open stays."""
    monkeypatch.delenv("AK_NO_GAME_LOGS", raising=False)
    monkeypatch.setattr(server, "MATCH_DIR", tmp_path / "web_matches")
    hub = server.Hub()
    monkeypatch.setattr(server, "hub", hub)
    m = Match("IDLE01", server.Seat("ta", "A", deck=SLUG))
    m.join(server.Seat("tb", "B", deck=SLUG))
    w = Match("WATCH1", server.Seat("tc", "A", deck=SLUG))
    w.join(server.Seat("td", "B", deck=SLUG))
    for x in (m, w):
        hub.matches[x.id] = x
        hub.save(x)
    hub.sockets["WATCH1"] = {(object(), "A")}
    now = time.time()
    assert hub.forget(now + 60) == 0                           # an hour is the rejoin window: not yet
    assert hub.forget(now + server.FORGET_IDLE + 1) == 1
    assert "IDLE01" not in hub.matches and "WATCH1" in hub.matches
    async def get(mid):              # a reloaded match's clock and bot start again: that needs the event loop
        return hub.get(mid)
    back = asyncio.run(get("IDLE01"))
    assert back is not None and back.state.to_dict() == m.state.to_dict() and back.seat_of("tb") == "B"
    assert asyncio.run(get("../IDLE01")) is None and asyncio.run(get("NOSUCH")) is None
