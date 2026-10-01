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
            await asyncio.sleep(0.05)
            assert (await (await c.get("/api/friends", headers=ha)).json())["friends"][0]["online"]
            ask = asyncio.ensure_future(c.post("/api/challenge", json={"friend": b["profile"]["id"], "deck": "ramp"}, headers=ha))
            msg = await ws.receive_json(timeout=2)
            assert msg["t"] == "challenge" and msg["from"] == peek["name"] and "deck" not in msg
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
            # removed: friends no more, both ways
            await c.delete(f"/api/friends/{a['profile']['id']}", headers=hb)
            assert (await (await c.get("/api/friends", headers=ha)).json())["friends"] == []
            await ws.close()
    asyncio.run(run())
