"""Friends and challenges (web/friends.py, server.py): a friend link makes two players friends, an online friend can be
challenged and accept into one match, a declined challenge answers 409, removal ends the friendship."""

import asyncio

from aiohttp.test_utils import TestClient, TestServer

from animal_kingdom.web import server


def test_friends_by_link_challenge_accept_decline_and_remove(monkeypatch):
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")

    async def run():
        async with TestClient(TestServer(server.make_app())) as c:
            a, b = [await (await c.post("/api/profile", json={})).json() for _ in range(2)]
            ha, hb = {"X-AK-Key": a["code"]}, {"X-AK-Key": b["code"]}
            code = (await (await c.get("/api/friends", headers=ha)).json())["code"]
            peek = await (await c.get(f"/api/friends/link/{code}", headers=hb)).json()
            assert peek["name"].startswith("Player#") and not peek["self"] and not peek["already"]
            assert (await c.post("/api/friends", json={"code": code}, headers=hb)).status == 200
            mine = (await (await c.get("/api/friends", headers=ha)).json())["friends"]
            assert [f["id"] for f in mine] == [b["profile"]["id"]] and not mine[0]["online"]
            # offline: no challenge
            r = await c.post("/api/challenge", json={"friend": b["profile"]["id"], "deck": "ramp"}, headers=ha)
            assert r.status == 409
            # B comes online; A challenges; B is told and accepts with its deck: one match, both seats
            ws = await c.ws_connect(f"/ws/presence?key={b['code']}")
            assert (await ws.receive_json(timeout=2))["t"] == "build"   # the server's client build, for a stale tab to reload
            await asyncio.sleep(0.05)
            assert (await (await c.get("/api/friends", headers=ha)).json())["friends"][0]["online"]
            ask = asyncio.ensure_future(c.post("/api/challenge", json={"friend": b["profile"]["id"], "deck": "ramp"}, headers=ha))
            msg = await ws.receive_json(timeout=2)
            assert msg["t"] == "challenge" and msg["from"] == peek["name"].split("#")[0] and "deck" not in msg   # the only friend so named: no tag
            mb = await (await c.post(f"/api/challenge/{msg['id']}/answer", json={"accept": True, "deck": "cats_midrange"}, headers=hb)).json()
            ma = await (await ask).json()
            assert ma["id"] == mb["id"] and (ma["seat"], mb["seat"]) == ("A", "B")
            assert server.hub.matches[ma["id"]].seats["B"].deck == "cats_midrange"
            # a declined challenge answers 409
            ask = asyncio.ensure_future(c.post("/api/challenge", json={"friend": b["profile"]["id"], "deck": "ramp"}, headers=ha))
            msg = None
            while not msg or msg["t"] != "challenge":
                msg = await ws.receive_json(timeout=2)
            await c.post(f"/api/challenge/{msg['id']}/answer", json={"accept": False}, headers=hb)
            assert (await ask).status == 409
            # withdrawn: the friend's piece goes, and a late accept finds it gone
            ask = asyncio.ensure_future(c.post("/api/challenge", json={"friend": b["profile"]["id"], "deck": "ramp"}, headers=ha))
            msg = None
            while not msg or msg["t"] != "challenge":
                msg = await ws.receive_json(timeout=2)
            await c.delete("/api/challenge", headers=ha)
            gone = await ws.receive_json(timeout=2)
            assert gone == {"t": "challenge_gone", "id": msg["id"]} and (await ask).status == 409
            assert (await c.post(f"/api/challenge/{msg['id']}/answer", json={"accept": True, "deck": "ramp"}, headers=hb)).status == 410
            # removed: friends no more, both ways
            await c.delete(f"/api/friends/{a['profile']['id']}", headers=hb)
            assert (await (await c.get("/api/friends", headers=ha)).json())["friends"] == []
            await ws.close()
    asyncio.run(run())


def test_friend_request_from_the_leaderboard(monkeypatch):
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")

    async def run():
        async with TestClient(TestServer(server.make_app())) as c:
            a, b, d = [await (await c.post("/api/profile", json={})).json() for _ in range(3)]
            ha, hb, hd = ({"X-AK-Key": x["code"]} for x in (a, b, d))
            bid, aid = b["profile"]["id"], a["profile"]["id"]
            # B online: the request reaches B at once; declining leaves no friends
            ws = await c.ws_connect(f"/ws/presence?key={b['code']}")
            assert (await ws.receive_json(timeout=2))["t"] == "build"   # the server's client build, for a stale tab to reload
            await asyncio.sleep(0.05)
            assert (await (await c.post("/api/friends/request", json={"to": bid}, headers=ha)).json()) == {"friends": False}
            msg = await ws.receive_json(timeout=2)
            assert msg["t"] == "friendreq" and msg["from"] == aid
            await c.post(f"/api/friends/request/{aid}/answer", json={"accept": False}, headers=hb)
            assert (await (await c.get("/api/friends", headers=ha)).json())["friends"] == []
            await ws.close()
            # B offline: the request waits and arrives when B comes; accepting makes them friends both ways
            await c.post("/api/friends/request", json={"to": bid}, headers=ha)
            ws = await c.ws_connect(f"/ws/presence?key={b['code']}")
            msg = await ws.receive_json(timeout=2)
            assert msg["t"] == "friendreq" and msg["from"] == aid
            assert (await ws.receive_json(timeout=2))["t"] == "build"   # after what was waiting
            await c.post(f"/api/friends/request/{aid}/answer", json={"accept": True}, headers=hb)
            assert [f["id"] for f in (await (await c.get("/api/friends", headers=ha)).json())["friends"]] == [bid]
            assert [f["id"] for f in (await (await c.get("/api/friends", headers=hb)).json())["friends"]] == [aid]
            await ws.close()
            # asking someone who asked you makes you friends at once; you can't ask yourself
            await c.post("/api/friends/request", json={"to": aid}, headers=hd)
            assert (await (await c.post("/api/friends/request", json={"to": d["profile"]["id"]}, headers=ha)).json()) == {"friends": True}
            assert (await c.post("/api/friends/request", json={"to": aid}, headers=ha)).status == 400
    asyncio.run(run())


def test_the_match_you_are_playing_can_be_rejoined_from_anywhere(monkeypatch):
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")

    async def run():
        async with TestClient(TestServer(server.make_app())) as c:
            a = await (await c.post("/api/profile", json={})).json()
            ha = {"X-AK-Key": a["code"]}
            assert await (await c.get("/api/current", headers=ha)).json() == {}
            await c.post("/api/match", json={"tutorial": 1}, headers=ha)   # a lesson is never brought back
            assert await (await c.get("/api/current", headers=ha)).json() == {}
            m = await (await c.post("/api/match", json={"deck": "cats_midrange", "bot": {"level": "easy", "deck": "ramp"}}, headers=ha)).json()
            match = server.hub.matches[m["id"]]
            if match.phase != "playing":
                match.ready("A")
            assert await (await c.get("/api/current", headers=ha)).json() == {}, "a bot match left before your first move is left"
            from animal_kingdom.web.match import Move
            match.history.append(Move(round=1, seat="A", kind="draw", pre={}))   # you made a move: now it's yours to return to
            cur = await (await c.get("/api/current", headers=ha)).json()
            assert cur["id"] == m["id"] and match.seat_of(cur["token"]) == "A"
            assert await (await c.get("/api/current")).json() == {}   # no profile, no match
            match.started_at -= server.REJOIN_WITHIN + 60; match.action_times = []   # an abandoned match is left alone
            assert await (await c.get("/api/current", headers=ha)).json() == {}
    asyncio.run(run())
