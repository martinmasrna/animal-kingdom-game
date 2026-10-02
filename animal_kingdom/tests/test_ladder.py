"""The ladder's Glicko-2 (web/ladder.py): Glickman's own worked example, and the behaviour the ladder relies on."""

import pytest

from animal_kingdom.web import ladder
from animal_kingdom.web.ladder import Rating


def test_glickmans_worked_example():
    # Glickman (2013): a 1500/200 player (volatility 0.06, tau 0.5) beats a 1400/30, loses to a 1550/100 and to a
    # 1700/300 in one rating period, ending at 1464.06 / 151.52 / 0.05999.
    a = Rating(1500, 200, 0.06)
    new = ladder._update(a, [(Rating(1400, 30), 1.0), (Rating(1550, 100), 0.0), (Rating(1700, 300), 0.0)])
    assert new.rating == pytest.approx(1464.06, abs=0.01)
    assert new.rd == pytest.approx(151.52, abs=0.01)
    assert new.vol == pytest.approx(0.05999, abs=1e-5)
    assert ladder.expected(a, Rating(1400, 30)) == pytest.approx(0.639, abs=1e-3)


def test_a_new_player_moves_fast_and_a_seeded_bot_slowly():
    new, bot = Rating(), ladder.bot_seed(1500)
    new2, bot2 = ladder.play(new, bot, True)
    assert new2.rating - new.rating > 100, "a new player's first win moves them a lot"
    assert 0 < bot.rating - bot2.rating < 10, "a seeded bot barely moves"


def test_beating_a_stronger_opponent_earns_more_than_a_weaker_one():
    me = Rating(1500, 80, 0.06, 30)
    up, _ = ladder.play(me, Rating(1800, 80, 0.06, 30), True)
    down, _ = ladder.play(me, Rating(1200, 80, 0.06, 30), True)
    assert up.rating - me.rating > down.rating - me.rating > 0


def test_the_question_mark_shows_for_the_first_ten_games():
    assert Rating(1512.4, games=3).shown() == "1512?"
    assert Rating(1512.6, games=10).shown() == "1513"
    assert not ladder.bot_seed(1700).provisional


def test_ranked_queue_gives_a_bot_after_the_wait_and_pairs_two_people(monkeypatch):
    import asyncio
    from aiohttp.test_utils import TestClient, TestServer
    from animal_kingdom.web import server
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")
    monkeypatch.setattr(server, "RANKED_WAIT", 0.3)

    async def run():
        async with TestClient(TestServer(server.make_app())) as c:
            a, b = [await (await c.post("/api/profile", json={})).json() for _ in range(2)]
            ha, hb = {"X-AK-Key": a["code"]}, {"X-AK-Key": b["code"]}
            # alone: a bot near your rating, on the ladder
            m = await (await c.post("/api/ranked", json={"deck": "cats_midrange"}, headers=ha)).json()
            match = server.hub.matches[m["id"]]
            bot = match.seats["B"]   # a seeded bot within reach of a new player's 1500 (nearest_bot: the nearest, or within 100 of it)
            assert bot.is_bot and bot.ladder.startswith("bot:") and abs(server.ladder.get(bot.ladder).rating - 1500) < 250
            assert match.seats["A"].ladder == a["profile"]["id"]
            # the match states both ratings as they stood going in, for the versus moment; an unrated match states none
            seats = match.view("A")["seats"]
            assert seats["A"]["rating"] == "1500?" and seats["B"]["rating"] == server.ladder.get(bot.ladder).shown()
            # two people at once: they meet each other
            ra, rb = await asyncio.gather(c.post("/api/ranked", json={"deck": "ramp"}, headers=ha),
                                          c.post("/api/ranked", json={"deck": "aggro_hq_rush"}, headers=hb))
            ma, mb = await ra.json(), await rb.json()
            assert ma["id"] == mb["id"] and {ma["seat"], mb["seat"]} == {"A", "B"}
            pair = server.hub.matches[ma["id"]]
            assert not any(s.is_bot for s in pair.seats.values())
            # a ranked result moves both ratings; the leaderboard shows the bots and the rated person
            pair.results = [{"winner": ma["seat"], "reason": "food", "turns": 9}]
            server.rate_match(pair)
            board = await (await c.get("/api/leaderboard", headers=ha)).json()
            assert not any(r["you"] for r in board["rows"]), "placing: not ranked yet"
            pl = board["placing"]
            assert pl["rating"].endswith("?") and int(pl["rating"][:-1]) > 1500 and (pl["games"], pl["of"]) == (1, 10)
            assert sum(r["bot"] for r in board["rows"]) == 21 and board["rows"][0]["name"].endswith("(Expert Bot)")
    asyncio.run(run())


def test_a_seed_file_sets_the_bots_once(tmp_path):
    import json, sqlite3
    L = ladder.Ladder(sqlite3.connect(":memory:"), ["cats_midrange", "ramp"])
    f = tmp_path / "seed.json"
    f.write_text(json.dumps({"version": "v1", "ratings": {"bot:expert:ramp": 1777.0, "bot:easy:cats_midrange": 1111.0}}))
    assert L.apply_seed(f) and round(L.get("bot:expert:ramp").rating) == 1777
    L.result("p1", "bot:expert:ramp")   # the bot moves after a game
    assert not L.apply_seed(f), "the same seed is applied once"
    assert round(L.get("bot:expert:ramp").rating) != 1777


def test_a_bot_that_fails_or_overthinks_still_moves(monkeypatch):
    """Never a frozen match (feedback 2026-10-01): a bot that raises, or thinks past BOT_THINK_MAX, plays the Easy bot's move."""
    import asyncio, time
    from aiohttp.test_utils import TestClient, TestServer
    from animal_kingdom.web import server
    from animal_kingdom.web.match import Match
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")
    monkeypatch.setattr(server, "RANKED_WAIT", 0.1)
    monkeypatch.setattr(server, "BOT_THINK_MAX", 0.3)
    monkeypatch.setattr(server, "BOT_PAUSE", {"choice": 0, "open": 0, "move": 0})
    for broken in (lambda self: 1 / 0, lambda self: time.sleep(2)):
        monkeypatch.setattr(Match, "bot_move", broken)

        async def run():
            async with TestClient(TestServer(server.make_app())) as c:
                a = await (await c.post("/api/profile", json={})).json()
                m = await (await c.post("/api/ranked", json={"deck": "cats_midrange"}, headers={"X-AK-Key": a["code"]})).json()
                match = server.hub.matches[m["id"]]
                match.ready("A") if match.phase != "playing" else None
                server.hub.kick_bot(match)
                for _ in range(40):   # the bot's mulligan, or its first moves, get played for it
                    await asyncio.sleep(0.1)
                    if any(p == "B" for p in (getattr(h, "seat", None) for h in match.history)) or len(match.actions) > 0:
                        break
                assert len(match.actions) > 0 or match.to_act() == "A", "the bot moved"
        asyncio.run(run())


def test_a_settled_player_still_moves_about_15_for_an_even_game():
    """People keep an uncertainty of at least PLAYER_RD_FLOOR (Martin, 2026-10-01): about +-15 an even game, however many
    games they've played; bots keep their own steady BOT_RD."""
    import sqlite3
    from animal_kingdom.web.ladder import Ladder, PLAYER_RD_FLOOR, BOT_RD, bot_id
    lad = Ladder(sqlite3.connect(":memory:"), ["cats_midrange"])
    bot = bot_id("normal", "cats_midrange")
    for _ in range(60):   # a long record: without the floor its uncertainty would shrink far below
        lad.result("me", bot); lad.result(bot, "me")
    me = lad.get("me")
    assert me.rd >= PLAYER_RD_FLOOR and lad.get(bot).rd <= BOT_RD + 5
    before = me.rating
    lad._put(bot, replace_rating(lad.get(bot), rating=before))
    w, _ = lad.result("me", bot)
    assert 13 <= w.rating - before <= 18


def replace_rating(r, **kw):
    from dataclasses import replace
    return replace(r, **kw)
