"""The server's guard against hostile clients (web/guard.py and its uses in server.py): a malformed request is a 400, never
a 500; a malformed socket message is answered, never a closed socket; a socket message that changes nothing writes
nothing; the routes a loop could abuse are rate limited; names can't fake another player's; no credential reaches the
access log."""

import asyncio
import json
import logging

import pytest
from aiohttp.test_utils import TestClient, TestServer

from animal_kingdom.web import custom_decks, guard, server


@pytest.fixture
def app(monkeypatch, tmp_path):
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")
    monkeypatch.setenv("AK_BOT_PAUSE", "0")
    monkeypatch.setattr(custom_decks, "DECKS_FILE", tmp_path / "web_decks.json")
    monkeypatch.setattr(guard, "limiter", guard.Limiter())
    return server.make_app


def run(app, body):
    async def go():
        async with TestClient(TestServer(app())) as c:
            return await body(c)
    return asyncio.run(go())


async def _profile(c):
    return await (await c.post("/api/profile", json={})).json()


BAD = [   # (method, path, request kwargs, needs a profile)
    ("POST", "/api/profile", {"data": "not json"}, False),
    ("POST", "/api/profile", {"json": [1, 2]}, False),
    ("POST", "/api/signin", {"json": []}, False),
    ("POST", "/api/auth/redeem", {"json": []}, False),
    ("POST", "/api/match", {"json": {"deck": "cats", "bot": "easy"}}, False),
    ("POST", "/api/match", {"json": {"deck": "cats", "bot": {"level": ["x"], "deck": "cats"}}}, False),
    ("POST", "/api/match", {"json": {"deck": "cats", "gauntlet": {"level": {"a": 1}}}}, False),
    ("POST", "/api/match", {"json": {"deck": "cats", "gauntlet": {"decks": [[1]]}}}, False),
    ("POST", "/api/match", {"json": {"deck": "cats", "gauntlet": {"games": "2"}}}, False),
    ("POST", "/api/match", {"json": {"tutorial": "abc"}}, False),
    ("POST", "/api/match", {"json": {"tutorial": [1]}}, False),
    ("POST", "/api/match", {"json": {"from": "x"}}, True),
    ("POST", "/api/challenge", {"json": {"friend": {"a": 1}}}, True),
    ("POST", "/api/feedback", {"json": {"text": ["hi"]}}, True),
    ("POST", "/api/news/seen", {"json": []}, True),
    ("PUT", "/api/me/decks", {"data": "{"}, True),
    ("PUT", "/api/me/decks", {"json": [{"id": "x", "name": "n", "cards": {"a" * 500: 1}}]}, True),
    ("PUT", "/api/me/decks", {"json": [{"id": "x", "name": "n", "cards": {"lion": True}}]}, True),
]


@pytest.mark.parametrize("method,path,kw,keyed", BAD, ids=[f"{m} {p} {list(k.values())[0]!r:.40}" for m, p, k, _ in BAD])
def test_a_malformed_request_is_a_client_error_never_a_server_error(app, method, path, kw, keyed):
    async def body(c):
        headers = {"X-AK-Key": (await _profile(c))["code"]} if keyed else {}
        r = await c.request(method, path, headers=headers, **kw)
        return r.status
    status = run(app, body)
    assert 400 <= status < 500


def test_a_lone_surrogate_in_a_name_feedback_or_chat_is_dropped_not_a_server_error(app):
    async def body(c):
        a, b = await _profile(c), await _profile(c)
        ha, hb = {"X-AK-Key": a["code"]}, {"X-AK-Key": b["code"]}
        code = (await (await c.get("/api/friends", headers=hb)).json())["code"]
        await c.post("/api/friends", json={"code": code}, headers=ha)
        chat = await c.post(f"/api/chat/{b['profile']['id']}", json={"text": "hi\ud800 there"}, headers=ha)
        fb = await c.post("/api/feedback", json={"text": "bug\ud800"}, headers=ha)
        named = await c.post("/api/profile", json={"name": "a\ud800b"})
        return chat.status, (await chat.json())["text"], fb.status, named.status, (await named.json())["profile"]["name"]
    assert run(app, body) == (200, "hi there", 200, 200, "ab")


def test_a_name_can_carry_no_tag_and_no_invisible_or_direction_changing_characters(app):
    async def body(c):
        p = await (await c.post("/api/profile", json={"name": "‮Mar​tin\x00"})).json()
        m = await (await c.post("/api/match", json={"deck": "cats", "name": "Laras#4821"})).json()
        long = await (await c.post("/api/match", json={"deck": "cats", "name": "N" * 100_000})).json()
        return p["profile"]["name"], server.hub.matches[m["id"]].seats["A"].name, server.hub.matches[long["id"]].seats["A"].name
    name, guest, long = run(app, body)
    assert name == "Martin"
    assert guest == "Laras"          # a tag is a profile's: a guest can't wear another player's name#tag
    assert len(long) <= 20


async def _bot_match(c):
    m = await (await c.post("/api/match", json={"deck": "cats", "bot": {"level": "easy", "deck": "cats"}})).json()
    ws = await c.ws_connect(f"/ws/{m['id']}?token={m['token']}")
    assert json.loads((await ws.receive()).data)["t"] == "build"
    view = json.loads((await ws.receive()).data)["view"]
    return m, ws, view


async def _until(ws, pred, timeout=5.0):
    while True:
        msg = await asyncio.wait_for(ws.receive(), timeout)
        assert msg.type.name == "TEXT", msg
        d = json.loads(msg.data)
        if pred(d):
            return d


MALFORMED = ["not json", "[1]", '{"t": "played", "seq": Infinity}', '{"t": "played", "seq": [1]}',
             json.dumps({"t": "act", "action": {"kind": "place", "card_id": "lion", "target": 5}}),
             json.dumps({"t": "act", "action": [1]}), json.dumps({"t": ["x"]})]


def test_a_malformed_socket_message_is_answered_and_the_socket_stays_open(app):
    async def body(c):
        m, ws, view = await _bot_match(c)
        answers = []
        for raw in MALFORMED:
            await ws.send_str(raw)
            answers.append((await _until(ws, lambda d: d["t"] in ("error", "view")))["t"])
            await _until(ws, lambda d: d["t"] == "view")     # the view again after the error
        await ws.send_json({"t": "concede"})             # and the socket still plays: a real message lands
        over = await _until(ws, lambda d: d["t"] == "view" and d["view"]["phase"] == "match_over")
        await ws.close()
        return answers, over["view"]["phase"]
    answers, phase = run(app, body)
    assert answers == ["error"] * len(MALFORMED)
    assert phase == "match_over"


def test_a_socket_message_that_changes_nothing_saves_and_pushes_nothing(app, monkeypatch):
    saves = []

    async def body(c):
        m, ws, view = await _bot_match(c)
        await asyncio.sleep(0.5)                     # the bot's own mulligan is done: the match waits on the player
        monkeypatch.setattr(server.hub, "save", lambda match: saves.append(match.id))
        for _ in range(40):
            await ws.send_json({"t": "ready"})      # a no-op once the match has started
        await ws.send_json({"t": "hold", "on": True})
        await asyncio.sleep(0.3)
        await ws.close()
    run(app, body)
    assert saves == []


def test_a_concede_is_pushed_to_the_socket(app):
    async def body(c):
        m, ws, view = await _bot_match(c)
        v0 = view["version"]
        await ws.send_json({"t": "concede"})
        d = await _until(ws, lambda d: d["t"] == "view" and d["view"]["phase"] == "match_over")
        await ws.close()
        return v0, d["view"]["version"]
    v0, v1 = run(app, body)
    assert v1 > v0


def test_a_socket_flooding_messages_is_closed(app, monkeypatch):
    monkeypatch.setattr(guard, "SOCKET_BURST", (10, 5.0))

    async def body(c):
        m, ws, view = await _bot_match(c)
        for _ in range(30):
            if ws.closed:
                break
            await ws.send_json({"t": "ready"})
        while True:
            msg = await asyncio.wait_for(ws.receive(), 5)
            if msg.type.name in ("CLOSE", "CLOSED", "CLOSING"):
                return True
    assert run(app, body)


def test_the_routes_a_loop_could_abuse_are_limited_per_address(app, monkeypatch):
    """On Fly the proxy's Fly-Client-IP is the address; a new address starts fresh."""
    monkeypatch.setenv("FLY_APP_NAME", "test")
    monkeypatch.setitem(guard.LIMITS, "profile", (3, 3600))
    monkeypatch.setitem(guard.LIMITS, "match", (2, 60))

    async def body(c):
        ip = {"Fly-Client-IP": "203.0.113.7"}
        made = [(await c.post("/api/profile", json={}, headers=ip)).status for _ in range(5)]
        other = (await c.post("/api/profile", json={}, headers={"Fly-Client-IP": "203.0.113.8"})).status
        matches = [(await c.post("/api/match", json={"deck": "cats"}, headers=ip)).status for _ in range(3)]
        return made, other, matches
    made, other, matches = run(app, body)
    assert made == [200, 200, 200, 429, 429] and other == 200
    assert matches == [200, 200, 429]


def test_a_local_server_never_limits_its_own_machine(app, monkeypatch):
    monkeypatch.delenv("FLY_APP_NAME", raising=False)
    monkeypatch.setitem(guard.LIMITS, "profile", (2, 3600))

    async def body(c):
        return [(await c.post("/api/profile", json={})).status for _ in range(4)]
    assert run(app, body) == [200] * 4


def test_feedback_mail_has_a_server_wide_cap_and_an_oversized_view_is_dropped(app, monkeypatch):
    mailed, kept = [], []
    monkeypatch.setitem(guard.LIMITS, "mail", (2, 3600))
    monkeypatch.setattr(server.feedback, "mail", lambda *a: mailed.append(a))
    monkeypatch.setattr(server.discord, "post", lambda *a: None)
    real_keep = server.feedback.keep
    monkeypatch.setattr(server.feedback, "keep", lambda db, pid, sender, text, ctx, view: kept.append(view) or real_keep(db, pid, sender, text, ctx, view))

    async def body(c):
        out = []
        for i in range(3):
            p = await _profile(c)   # three senders, so the per-sender hourly cap is not what stops the third
            view = {"blob": "x" * (server.feedback.VIEW_MAX + 10)} if i == 0 else {"ok": 1}
            out.append((await c.post("/api/feedback", json={"text": f"msg {i}", "view": view}, headers={"X-AK-Key": p["code"]})).status)
        await asyncio.sleep(0.2)
        return out
    assert run(app, body) == [200, 200, 200]
    assert len(kept) == 3 and len(mailed) == 2
    assert "dropped" in kept[0]


def test_the_access_log_never_writes_a_sign_in_key_or_a_seat_token(caplog):
    from unittest import mock
    from aiohttp.test_utils import make_mocked_request
    logger = logging.getLogger("test.access")
    al = guard.RedactingAccessLogger(logger, '%a "%r" %s')
    req = make_mocked_request("GET", "/ws/presence?key=ABCD-EFGH-JKLM-NPQR&x=1")
    with caplog.at_level(logging.INFO, logger="test.access"):
        al.log(req, mock.Mock(status=101, body_length=0), 0.1)
        al.log(make_mocked_request("GET", "/ws/ABC123?token=sEcReT"), mock.Mock(status=101, body_length=0), 0.1)
    text = caplog.text
    assert "ABCD" not in text and "sEcReT" not in text
    assert "/ws/presence?key=-&x=1" in text and "/ws/ABC123?token=-" in text
