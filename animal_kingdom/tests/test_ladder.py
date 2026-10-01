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
            assert match.seats["B"].is_bot and match.seats["B"].ladder.startswith("bot:normal:")
            assert match.seats["A"].ladder == a["profile"]["id"]
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
            table = await (await c.get("/api/leaderboard", headers=ha)).json()
            mine = next(r for r in table if r["you"])
            assert mine["rating"].endswith("?") and int(mine["rating"][:-1]) > 1500
            assert sum(r["bot"] for r in table) == 21 and table[0]["name"].startswith("Expert Bot")
    asyncio.run(run())
