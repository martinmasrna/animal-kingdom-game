"""Daily matches (docs/async-play.md): a friend match that waits for days. The clock gives whoever must act DAILY_DAYS
from the moment the decision came to them and the match is lost when it runs out; a challenge waits on the friend's home,
online or not, and lapses; home lists the matches where it is your turn; everything survives a restart."""

import asyncio
import json

from aiohttp.test_utils import TestClient, TestServer

from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import SKIP, ChoiceAction, PassAction
from animal_kingdom.web import server
from animal_kingdom.web.match import DAY, Match, Seat


import pytest


@pytest.fixture(autouse=True)
def _own_hub(monkeypatch):
    """A hub of this test's own: a sweep looks at every daily match the server holds, an earlier test's too."""
    monkeypatch.setattr(server, "hub", server.Hub())


def _daily(days=2, t0=1000.0, monkeypatch=None) -> Match:
    if monkeypatch:
        monkeypatch.setattr("animal_kingdom.web.match.time.time", lambda: t0)
    m = Match("D1", Seat("ta", "Ann", deck="cats", profile="pa"))
    m.daily = {"days": days}
    m.join(Seat("tb", "Bob", deck="giants", profile="pb"))
    return m


def _keep_hands(m: Match) -> None:
    while m.mulliganing():
        for p in "AB":
            if m.mulliganing() and m.yours(p):
                m.act(p, ChoiceAction(SKIP))


def _end_turn(m: Match) -> None:
    """The player to act ends their turn, answering whatever it still asks (a discard over the hand limit)."""
    s = m.to_act()
    while m.to_act() == s and m.phase == "playing":
        m.act(s, PassAction() if not m.state.pending else rules.legal_actions(m.state)[0])


def _clock(monkeypatch, t):
    monkeypatch.setattr("animal_kingdom.web.match.time.time", lambda: t)


def test_a_daily_match_has_no_live_clock_and_gives_each_decision_days(monkeypatch):
    m = _daily(monkeypatch=monkeypatch)
    assert m.phase == "playing" and m.clock is None
    assert m.yours("A") and m.yours("B"), "the opening mulligans are both players' at once"
    assert m.daily_deadline() == 1000.0 + 2 * DAY
    _clock(monkeypatch, 5000.0)
    _keep_hands(m)
    first = m.to_act()
    assert m.yours(first) and not m.yours("B" if first == "A" else "A")
    assert m.daily_deadline() == 5000.0 + 2 * DAY, "the first turn starts its own window"
    _clock(monkeypatch, 12000.0)
    _end_turn(m)                        # the first turn (one action for the first player) passes to the other
    second = m.to_act()
    assert second != first and m.yours(second) and not m.yours(first)
    assert m.daily_deadline() == 12000.0 + 2 * DAY, "the turn passing starts the other player's window"
    _clock(monkeypatch, 15000.0)
    m.act(second, {"kind": "draw"})
    assert m.to_act() == second and m.daily_deadline() == 12000.0 + 2 * DAY, "a second action in the same turn keeps it"
    v = m.view(second)
    assert v["daily"]["yours"] and v["daily"]["deadline"] == m.daily_deadline() and v["game"]["clock"] == {"on": False}
    assert not m.view(first)["daily"]["yours"]


def test_running_out_of_time_loses_the_match(monkeypatch):
    m = _daily(monkeypatch=monkeypatch)
    _keep_hands(m)
    late = m.to_act()
    assert not m.daily_time_out(m.daily_deadline() - 1)
    assert m.daily_time_out(m.daily_deadline())
    assert m.phase == "match_over" and m.results[-1]["winner"] != late and m.results[-1]["reason"] == "timeout"
    assert m.daily_deadline() is None and not m.daily_time_out(10 ** 12)


def test_nobody_mulliganed_in_time_is_a_draw(monkeypatch):
    m = _daily(monkeypatch=monkeypatch)
    assert m.daily_time_out(m.daily_deadline() + 1)
    assert m.results[-1]["winner"] is None and m.results[-1]["reason"] == "timeout"


def test_a_saved_daily_match_keeps_its_deadline_across_a_restart(monkeypatch):
    m = _daily(monkeypatch=monkeypatch)
    _keep_hands(m)
    deadline, who = m.daily_deadline(), m.to_act()
    _clock(monkeypatch, 1000.0 + DAY)
    back = Match.from_dict(json.loads(json.dumps(m.to_dict())))
    assert back.daily_deadline() == deadline and back.to_act() == who and back.clock is None
    assert back.yours(who) and back.view(who)["daily"]["deadline"] == deadline


def test_a_live_friend_match_is_untouched():
    m = Match("L1", Seat("ta", "Ann", deck="cats", profile="pa"))
    m.join(Seat("tb", "Bob", deck="giants", profile="pb"))
    assert m.daily is None and m.clock is not None and "daily" not in m.view("A")


async def _two_friends(c):
    a, b = [await (await c.post("/api/profile", json={})).json() for _ in range(2)]
    ha, hb = {"X-AK-Key": a["code"]}, {"X-AK-Key": b["code"]}
    code = (await (await c.get("/api/friends", headers=ha)).json())["code"]
    await c.post("/api/friends", json={"code": code}, headers=hb)
    return a, b, ha, hb


def test_a_daily_challenge_waits_for_an_offline_friend_who_accepts_and_home_lists_whose_turn_it_is(monkeypatch):
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")

    async def run():
        async with TestClient(TestServer(server.make_app())) as c:
            a, b, ha, hb = await _two_friends(c)
            bid = b["profile"]["id"]
            r = await c.post("/api/daily", json={"friend": bid, "deck": "cats"}, headers=ha)   # Bob is offline
            assert r.status == 200
            ch = await r.json()
            mine, his = [await (await c.get("/api/daily", headers=h)).json() for h in (ha, hb)]
            assert [s["id"] for s in mine["sent"]] == [ch["id"]] and mine["turn"] == [] and mine["challenges"] == []
            assert [x["id"] for x in his["challenges"]] == [ch["id"]] and his["challenges"][0]["from"] == a["profile"]["name"]
            assert his["challenges"][0]["until"] - mine["now"] > 6.9 * DAY
            # nobody else gets in by its code, and the challenger is not sent into it on opening the game
            assert (await c.post(f"/api/match/{ch['id']}/join", json={"deck": "giants"})).status == 409
            assert await (await c.get("/api/current", headers=ha)).json() == {}
            acc = await (await c.post(f"/api/daily/{ch['id']}/answer", json={"accept": True, "deck": "giants"}, headers=hb)).json()
            assert acc["seat"] == "B"
            match = server.hub.matches[ch["id"]]
            assert match.phase == "playing" and match.clock is None and match.seats["B"].deck == "giants"
            mine, his = [await (await c.get("/api/daily", headers=h)).json() for h in (ha, hb)]
            assert [x["id"] for x in mine["turn"]] == [ch["id"]] == [x["id"] for x in his["turn"]], "both mulligan"
            assert mine["turn"][0]["token"] == ch["token"] and his["turn"][0]["token"] == acc["token"]
            assert mine["sent"] == [] and his["challenges"] == []
            _keep_hands(match)
            first = match.to_act()
            hf, ho = (ha, hb) if first == "A" else (hb, ha)
            turn, wait = (await (await c.get("/api/daily", headers=hf)).json()), (await (await c.get("/api/daily", headers=ho)).json())
            assert [x["id"] for x in turn["turn"]] == [ch["id"]] and turn["waiting"] == []
            assert [x["id"] for x in wait["waiting"]] == [ch["id"]] and wait["turn"] == []
            assert turn["turn"][0]["deadline"] == match.daily_deadline()
            assert await (await c.get("/api/current", headers=hf)).json() == {}, "a daily match never takes over home"
    asyncio.run(run())


def test_a_turn_not_taken_in_time_loses_and_the_result_waits_on_home_until_opened(monkeypatch):
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")
    recorded = []

    async def run():
        async with TestClient(TestServer(server.make_app())) as c:
            a, b, ha, hb = await _two_friends(c)
            monkeypatch.setattr(server.profiles, "record", lambda pid, key, **k: recorded.append((pid, k)))
            ch = await (await c.post("/api/daily", json={"friend": b["profile"]["id"], "deck": "cats"}, headers=ha)).json()
            acc = await (await c.post(f"/api/daily/{ch['id']}/answer", json={"accept": True, "deck": "giants"}, headers=hb)).json()
            match = server.hub.matches[ch["id"]]
            _keep_hands(match)
            late = match.to_act()
            await server.hub.sweep_daily(match.daily_deadline() - 60)
            assert match.phase == "playing"
            await server.hub.sweep_daily(match.daily_deadline() + 1)
            assert match.phase == "match_over" and match.results[-1]["reason"] == "timeout"
            assert match.results[-1]["winner"] != late
            assert {k["mode"] for _, k in recorded} == {"daily"} and len(recorded) == 2, "both histories, as daily"
            hl, tl = (ha, ch["token"]) if late == "A" else (hb, acc["token"])
            res = (await (await c.get("/api/daily", headers=hl)).json())["results"]
            assert len(res) == 1 and not res[0]["won"] and res[0]["reason"] == "timeout"
            ws = await c.ws_connect(f"/ws/{ch['id']}?token={tl}")      # opening it once: seen
            while (await ws.receive_json(timeout=2))["t"] != "view":
                pass
            await ws.close()
            assert (await (await c.get("/api/daily", headers=hl)).json())["results"] == []
            other = hb if late == "A" else ha
            won = (await (await c.get("/api/daily", headers=other)).json())["results"]
            assert len(won) == 1 and won[0]["won"], "the winner's line stays until they open it"
    asyncio.run(run())


def test_a_daily_challenge_can_be_declined_withdrawn_or_left_to_lapse(monkeypatch):
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")

    async def run():
        async with TestClient(TestServer(server.make_app())) as c:
            a, b, ha, hb = await _two_friends(c)
            bid = b["profile"]["id"]
            new = lambda: c.post("/api/daily", json={"friend": bid, "deck": "cats"}, headers=ha)
            one = await (await new()).json()
            assert (await c.post(f"/api/daily/{one['id']}/answer", json={"accept": False}, headers=hb)).status == 200
            assert one["id"] not in server.hub.matches
            assert (await c.post(f"/api/daily/{one['id']}/answer", json={"accept": True, "deck": "giants"}, headers=hb)).status == 410
            two = await (await new()).json()
            assert (await c.delete(f"/api/daily/{two['id']}", headers=hb)).status == 410, "only its sender takes it back"
            assert (await c.delete(f"/api/daily/{two['id']}", headers=ha)).status == 200 and two["id"] not in server.hub.matches
            three = await (await new()).json()
            until = server.hub.matches[three["id"]].daily["until"]
            await server.hub.sweep_daily(until - 1)
            assert three["id"] in server.hub.matches
            await server.hub.sweep_daily(until)
            assert three["id"] not in server.hub.matches
            assert (await (await c.get("/api/daily", headers=hb)).json())["challenges"] == []
            # a stranger can't be challenged
            d = await (await c.post("/api/profile", json={})).json()
            assert (await c.post("/api/daily", json={"friend": d["profile"]["id"], "deck": "cats"}, headers=ha)).status == 400
    asyncio.run(run())


def test_at_most_daily_max_open_matches(monkeypatch):
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")
    monkeypatch.setattr(server, "DAILY_MAX", 2)

    async def run():
        async with TestClient(TestServer(server.make_app())) as c:
            a, b, ha, hb = await _two_friends(c)
            body = {"friend": b["profile"]["id"], "deck": "cats"}
            assert (await c.post("/api/daily", json=body, headers=ha)).status == 200
            assert (await c.post("/api/daily", json=body, headers=ha)).status == 200
            r = await c.post("/api/daily", json=body, headers=ha)
            assert r.status == 409 and "2 daily matches" in await r.text()
    asyncio.run(run())


def test_the_friend_hears_a_challenge_and_a_turn_on_their_open_tab(monkeypatch):
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")

    async def run():
        async with TestClient(TestServer(server.make_app())) as c:
            a, b, ha, hb = await _two_friends(c)
            ws = await c.ws_connect(f"/ws/presence?key={b['code']}")
            ch = await (await c.post("/api/daily", json={"friend": b["profile"]["id"], "deck": "cats"}, headers=ha)).json()
            msg = None
            while not msg or msg["t"] != "daily":
                msg = await ws.receive_json(timeout=2)
            assert msg["id"] == ch["id"]
            await ws.close()
    asyncio.run(run())


def test_a_daily_match_on_disk_is_reloaded_however_old(monkeypatch, tmp_path):
    monkeypatch.delenv("AK_NO_GAME_LOGS", raising=False)
    monkeypatch.setattr(server, "MATCH_DIR", tmp_path)
    m = _daily(monkeypatch=monkeypatch)
    _keep_hands(m)
    hub = server.Hub()
    hub.save(m)
    old = tmp_path / f"{m.id}.json"
    import os
    os.utime(old, (1, 1))                      # written long ago
    fresh = server.Hub()
    fresh.load()
    assert fresh.matches[m.id].daily_deadline() == m.daily_deadline()
    fresh.drop(fresh.matches[m.id])
    assert not old.exists()


def test_the_daily_ranked_queue_pairs_the_next_person_and_rates_the_result(monkeypatch):
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")

    async def run():
        async with TestClient(TestServer(server.make_app())) as c:
            a, b = [await (await c.post("/api/profile", json={})).json() for _ in range(2)]   # strangers: no friendship needed
            ha, hb = {"X-AK-Key": a["code"]}, {"X-AK-Key": b["code"]}
            one = await (await c.post("/api/daily/ranked", json={"deck": "cats"}, headers=ha)).json()
            assert not one["paired"]
            assert (await c.post("/api/daily/ranked", json={"deck": "cats"}, headers=ha)).status == 409, "one place in the queue"
            q = (await (await c.get("/api/daily", headers=ha)).json())["queue"]
            assert [x["id"] for x in q] == [one["id"]] and q[0]["until"] - time_now() > 0.9 * DAY
            two = await (await c.post("/api/daily/ranked", json={"deck": "giants"}, headers=hb)).json()
            assert two["paired"] and two["id"] == one["id"] and two["seat"] == "B"
            match = server.hub.matches[one["id"]]
            assert match.phase == "playing" and match.daily["ranked"] and match.clock is None
            assert match.seats["A"].ladder == a["profile"]["id"] and match.seats["B"].ladder == b["profile"]["id"]
            assert match.view("A")["ranked"] and match.seats["A"].rating
            rows = (await (await c.get("/api/daily", headers=hb)).json())["turn"]
            assert [r["id"] for r in rows] == [one["id"]] and rows[0]["ranked"]
            before = {p: server.ladder.get(match.seats[p].ladder).rating for p in "AB"}
            _keep_hands(match)
            late = match.to_act()
            await server.hub.sweep_daily(match.daily_deadline() + 1)
            after = {p: server.ladder.get(match.seats[p].ladder).rating for p in "AB"}
            assert after[late] < before[late] and after["B" if late == "A" else "A"] > before["B" if late == "A" else "A"], "rated"
            hist = server.profiles.history(a["profile"]["id"])
            assert hist[0]["mode"] == "ranked"
    asyncio.run(run())


def time_now():
    import time
    return time.time()


def test_nobody_in_the_daily_queue_for_a_day_gives_a_bot_at_your_rating_that_answers_at_once(monkeypatch):
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")
    monkeypatch.setenv("AK_BOT_PAUSE", "0")
    monkeypatch.setattr(server, "BOT_PAUSE", {"open": 0, "move": 0, "choice": 0})

    async def run():
        async with TestClient(TestServer(server.make_app())) as c:
            a = await (await c.post("/api/profile", json={})).json()
            ha = {"X-AK-Key": a["code"]}
            one = await (await c.post("/api/daily/ranked", json={"deck": "cats"}, headers=ha)).json()
            match = server.hub.matches[one["id"]]
            await server.hub.sweep_daily(match.daily["until"] - 1)
            assert match.phase == "lobby"
            await server.hub.sweep_daily(match.daily["until"] + 1)
            assert match.phase == "playing" and match.seats["B"].is_bot and match.seats["B"].ladder.startswith("bot:")
            assert match.daily["ranked"] and match.daily["bot"]
            assert match.yours("A")
            from animal_kingdom.web.match import bot_for
            match.bots["B"] = bot_for("easy", 1)        # a quick pilot: the test is about who waits, not how well it plays
            match.act("A", ChoiceAction(SKIP))         # you keep your hand; the bot then mulligans and plays at once
            server.hub.kick_bot(match)
            for _ in range(600):
                if not match.mulliganing() and match.yours("A"):
                    break
                await asyncio.sleep(0.05)
            assert not match.mulliganing() and match.yours("A") and not match.yours("B"), "the bot never keeps you waiting"
    asyncio.run(run())


def test_at_most_a_few_daily_ranked_matches(monkeypatch):
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")
    monkeypatch.setattr(server, "DAILY_RANKED_MAX", 1)

    async def run():
        async with TestClient(TestServer(server.make_app())) as c:
            a, b = [await (await c.post("/api/profile", json={})).json() for _ in range(2)]
            ha, hb = {"X-AK-Key": a["code"]}, {"X-AK-Key": b["code"]}
            await c.post("/api/daily/ranked", json={"deck": "cats"}, headers=ha)
            await c.post("/api/daily/ranked", json={"deck": "cats"}, headers=hb)
            r = await c.post("/api/daily/ranked", json={"deck": "cats"}, headers=ha)
            assert r.status == 409 and "1 daily ranked" in await r.text()
            # the queue can be left
            d = await (await c.post("/api/profile", json={})).json()
            hd = {"X-AK-Key": d["code"]}
            w = await (await c.post("/api/daily/ranked", json={"deck": "cats"}, headers=hd)).json()
            assert (await c.delete(f"/api/daily/{w['id']}", headers=hd)).status == 200 and w["id"] not in server.hub.matches
    asyncio.run(run())
