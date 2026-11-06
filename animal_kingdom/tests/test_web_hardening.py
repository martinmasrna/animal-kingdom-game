"""The server hardening Martin approved on 2026-11-05: old match files archived, a friend's rematch as an offer, the Expert
only for a profile and one bot search at a time per person, a stuck search abandoned for a fresh bot, the sign-in tied to
the browser that started it, and the small leaks (the Server header, the Host header, the league key's comparison)."""

import asyncio
import json
import os
import threading
import time

import pytest
from aiohttp.test_utils import TestClient, TestServer

from animal_kingdom.engine import rules
from animal_kingdom.engine.state import EngineError
from animal_kingdom.web import custom_decks, guard, league as league_mod, oauth, server
from animal_kingdom.web.match import Match, Seat


@pytest.fixture
def app(monkeypatch, tmp_path):
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")
    monkeypatch.delenv("FLY_APP_NAME", raising=False)
    monkeypatch.delenv("AK_BASE_URL", raising=False)
    monkeypatch.setattr(server, "BOT_PAUSE", {"choice": 0, "open": 0, "move": 0})
    monkeypatch.setattr(custom_decks, "DECKS_FILE", tmp_path / "web_decks.json")
    monkeypatch.setattr(guard, "limiter", guard.Limiter())
    monkeypatch.setattr(server, "hub", server.Hub())
    monkeypatch.setattr(server, "bot_pool", server.BotPool())
    return server.make_app


def run(app, body):
    async def go():
        async with TestClient(TestServer(app())) as c:
            return await body(c)
    return asyncio.run(go())


# ------------------------------------------------------------------ old match files
def test_a_match_file_untouched_for_a_week_is_archived_at_start_and_not_reloaded(monkeypatch, tmp_path):
    monkeypatch.delenv("AK_NO_GAME_LOGS", raising=False)
    monkeypatch.setattr(server, "MATCH_DIR", tmp_path)
    for mid in ("OLDONE", "NEWONE"):
        m = Match(mid, Seat("t" + mid, "You", deck="cats"))
        (tmp_path / f"{mid}.json").write_text(json.dumps(m.to_dict()))
    week = time.time() - 8 * 24 * 3600
    os.utime(tmp_path / "OLDONE.json", (week, week))
    hub = server.Hub()
    hub.load()
    assert set(hub.matches) == {"NEWONE"}
    assert (tmp_path / "archive" / "OLDONE.json").is_file() and not (tmp_path / "OLDONE.json").exists()
    assert hub.get("OLDONE") is None          # an archived match is gone for the server


# ------------------------------------------------------------------ rematch
def _over(friendly: bool) -> Match:
    m = Match("RMATCH", Seat("ta", "Ann", deck="cats", profile="pa"))
    m.join(Seat("tb", "Bob", deck="cats", profile="pb") if friendly else Seat("tb", "Bot", bot="easy", deck="cats"))
    m.results, m.phase = [{"winner": "A", "reason": "concede", "turns": 3, "first": "A"}], "match_over"
    return m


def test_a_friend_match_rematch_is_an_offer_the_other_player_accepts():
    m = _over(friendly=True)
    m.offer_rematch("A")
    assert m.phase == "match_over"
    assert m.view("B")["rematch"] == {"offer": "A", "declined": None}
    m.offer_rematch("A")                       # offering twice changes nothing
    assert m.phase == "match_over"
    m.offer_rematch("B")                       # the other's Rematch accepts
    assert m.phase == "playing" and "rematch" not in m.view("A")


def test_a_declined_rematch_stays_declined():
    m = _over(friendly=True)
    m.offer_rematch("A")
    with pytest.raises(EngineError):
        m.decline_rematch("A")                 # only the one offered to declines
    m.decline_rematch("B")
    assert m.view("A")["rematch"] == {"offer": None, "declined": "B"}
    with pytest.raises(EngineError):
        m.offer_rematch("A")
    assert Match.from_dict(json.loads(json.dumps(m.to_dict()))).rematch_declined == "B"   # a restart keeps it


def test_a_rematch_against_a_bot_starts_at_once():
    m = _over(friendly=False)
    m.offer_rematch("A")
    assert m.phase == "playing"


# ------------------------------------------------------------------ the Expert's compute
def test_the_expert_needs_a_profile(app):
    async def body(c):
        bot = {"deck": "cats", "bot": {"level": "expert", "deck": "cats"}}
        assert (await c.post("/api/match", json=bot)).status == 401
        gauntlet = {"deck": "cats", "gauntlet": {"level": "expert", "games": 1, "decks": ["bot_optimized"]}}
        assert (await c.post("/api/match", json=gauntlet)).status == 401
        p = await (await c.post("/api/profile", json={})).json()
        assert (await c.post("/api/match", json=bot, headers={"X-AK-Key": p["code"]})).status == 200
        assert (await c.post("/api/match", json={"deck": "cats", "bot": {"level": "easy", "deck": "cats"}})).status == 200
    run(app, body)


def test_one_bot_search_at_a_time_per_person_and_a_bounded_number_in_all():
    pool, live, peak, lock = server.BotPool(size=2, stuck_max=8), [0], {}, threading.Lock()

    def search(key):
        def fn():
            with lock:
                live[0] += 1
                peak["all"] = max(peak.get("all", 0), live[0])
            time.sleep(0.05)
            with lock:
                live[0] -= 1
            return key
        return fn

    async def go():
        return await asyncio.gather(*(pool.run(k, search(k), 5) for k in ["ann"] * 3 + ["bob", "cy", "dee"]))
    assert asyncio.run(go()) == ["ann"] * 3 + ["bob", "cy", "dee"]
    assert peak["all"] == 2                    # the pool's size
    assert pool.locks == {}                    # nothing left behind


def test_a_person_never_runs_two_searches_at_once():
    pool, running, seen = server.BotPool(size=4), set(), []

    def fn():
        seen.append(len(running))
        running.add(threading.get_ident())
        time.sleep(0.03)
        running.discard(threading.get_ident())

    async def go():
        await asyncio.gather(*(pool.run("ann", fn, 5) for _ in range(4)))
    asyncio.run(go())
    assert seen == [0, 0, 0, 0]


def test_a_stuck_search_is_abandoned_its_slot_freed_and_too_many_stop_new_searches():
    pool, release = server.BotPool(size=1, stuck_max=2), threading.Event()

    async def go():
        for _ in range(2):                      # two searches that never end on their own
            with pytest.raises(asyncio.TimeoutError):
                await pool.run("ann", release.wait, 0.05)
        assert pool.stuck_running() == 2
        with pytest.raises(server.PoolFull):    # the cap: no new search while they run
            await pool.run("bob", lambda: "bob", 1)
        release.set()
        for _ in range(100):
            if not pool.stuck_running():
                break
            await asyncio.sleep(0.01)
        return await pool.run("bob", lambda: "bob", 1)
    assert asyncio.run(go()) == "bob"


def test_a_bot_whose_search_was_abandoned_gets_a_fresh_bot(app, monkeypatch):
    monkeypatch.setattr(server, "BOT_THINK_MAX", 0.05)
    release = threading.Event()
    monkeypatch.setattr(Match, "bot_move", lambda self: release.wait(5))

    async def body(c):
        p = await (await c.post("/api/profile", json={})).json()
        m = await (await c.post("/api/match", json={"deck": "cats", "bot": {"level": "easy", "deck": "cats"}},
                                headers={"X-AK-Key": p["code"]})).json()
        match = server.hub.matches[m["id"]]
        if match.phase != "playing":
            match.ready("A")
        bots = [id(b) for b in match.bots.values()]
        server.hub.kick_bot(match)
        for _ in range(300):
            if [id(b) for b in match.bots.values()] != bots:
                break
            if match.to_act() == "A" or (match.state.pending is None and rules.early_mulligan(match.state, "A") is not None):
                match.act("A", rules.legal_actions(match.state)[0].to_dict())
                await server.hub.push(match)
            await asyncio.sleep(0.01)
        release.set()
        return [id(b) for b in match.bots.values()] != bots
    assert run(app, body)


# ------------------------------------------------------------------ sign-in
def test_a_sign_in_callback_must_come_back_to_the_browser_that_started_it(app, monkeypatch):
    monkeypatch.setattr(oauth, "_credentials", lambda provider: ("id", "secret"))
    signed = []

    async def identify(provider, code, redirect_uri):
        signed.append(code)
        return "subject-1", "ann@example.com"
    monkeypatch.setattr(oauth, "identify", identify)

    async def body(c):
        p = await (await c.post("/api/profile", json={})).json()
        r = await c.post("/api/auth/google", headers={"X-AK-Key": p["code"]})
        url = (await r.json())["url"]
        state = oauth.URL(url).query["state"]
        cookie = r.cookies[server.SIGNIN_COOKIE]
        assert cookie.value == state and cookie["httponly"] and cookie["samesite"] == "Lax"
        c.session.cookie_jar.clear()            # someone else's browser: the attacker's state, no cookie
        r = await c.get(f"/auth/google/callback?code=x&state={state}", allow_redirects=False)
        assert r.headers["Location"] == "/#/auth/failed" and signed == []
        c.session.cookie_jar.update_cookies({server.SIGNIN_COOKIE: state})   # the browser that started it
        r = await c.get(f"/auth/google/callback?code=x&state={state}", allow_redirects=False)
        assert r.headers["Location"].startswith("/#/auth/") and r.headers["Location"] != "/#/auth/failed"
        assert signed == ["x"]
    run(app, body)


# ------------------------------------------------------------------ small leaks
def test_the_server_header_names_no_versions(app):
    async def body(c):
        return (await c.get("/api/pool")).headers.get("Server")
    assert run(app, body) == "animal-kingdom"


def test_absolute_links_never_come_from_the_request_host(monkeypatch):
    class Req:
        headers, scheme, host = {}, "http", "evil.example"
    monkeypatch.delenv("AK_BASE_URL", raising=False)
    monkeypatch.setenv("FLY_APP_NAME", "animal-kingdom-staging")
    assert server.callback_url(Req(), "google") == "https://animal-kingdom-staging.fly.dev/auth/google/callback"
    monkeypatch.setenv("AK_BASE_URL", "https://example.org/")
    assert server.callback_url(Req(), "google") == "https://example.org/auth/google/callback"
    monkeypatch.delenv("AK_BASE_URL")
    monkeypatch.delenv("FLY_APP_NAME")
    assert server.callback_url(Req(), "google") == "http://evil.example/auth/google/callback"   # a local server only


def test_the_league_key_is_checked_in_constant_time(monkeypatch):
    from aiohttp import web
    monkeypatch.setattr(league_mod, "key", lambda: "right-key")
    calls = []
    real = server.secrets.compare_digest
    monkeypatch.setattr(server.secrets, "compare_digest", lambda a, b: calls.append(1) or real(a, b))

    class Req:
        def __init__(self, k):
            self.headers = {"X-AK-League-Key": k} if k is not None else {}
    server.league_auth(Req("right-key"))
    for wrong in ("wrong", None, "ríght"):
        with pytest.raises(web.HTTPForbidden):
            server.league_auth(Req(wrong))
    assert len(calls) == 4
