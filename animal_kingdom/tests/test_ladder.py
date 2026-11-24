"""The ladder (web/ladder.py): Glickman's own worked example, the behaviour the ladder relies on, and a ranked match
through the server."""

import asyncio
import random
import sqlite3
from dataclasses import replace

import pytest
from aiohttp.test_utils import TestClient, TestServer

from animal_kingdom.tests._helpers import DECK
from animal_kingdom.web import custom_decks, guard, ladder, server, tiers
from animal_kingdom.web.ladder import Ladder, Rating, bot_id, parse_bot


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


def test_an_opponent_whose_rating_is_less_sure_moves_you_less():
    """A bot whose deck was not measured with today's cards stands on its level's rating with a wider uncertainty
    (web/pool.py): a game against it counts for less."""
    me = Rating(1500, 80, 0.06, 30)
    sure, _ = ladder.play(me, ladder.bot_seed(1500), True)
    unsure, _ = ladder.play(me, ladder.bot_seed(1500, ladder.UNMEASURED_RD), True)
    assert 0 < unsure.rating - me.rating < sure.rating - me.rating


def test_the_question_mark_shows_for_the_first_ten_games():
    assert Rating(1512.4, games=3).shown() == "1512?"
    assert Rating(1512.6, games=10).shown() == "1513"
    assert not ladder.bot_seed(1700).provisional


def test_the_bots_are_rated_from_their_games_against_each_other():
    # b wins three in four against a and against c; a and c split theirs: b on top, the field centred at 1500
    games = [("b", "a")] * 30 + [("a", "b")] * 10 + [("b", "c")] * 30 + [("c", "b")] * 10 + [("a", "c")] * 20 + [("c", "a")] * 20
    r = ladder.fit(games)
    assert r["b"] > r["a"] == pytest.approx(r["c"], abs=1) and sum(r.values()) / 3 == pytest.approx(1500, abs=0.1)
    assert r["b"] - r["a"] == pytest.approx(190, abs=15), "three in four is about 190 points"
    assert max(ladder.fit([("x", "y")] * 20).values()) < 2500, "a bot that won everything still gets a number"


def test_a_bot_is_set_once_from_a_measurement_and_people_never():
    lad = Ladder(sqlite3.connect(":memory:"), ["control"])
    bot = bot_id("5", "control")
    assert lad.set_bots({bot: (1777.0, ladder.BOT_RD, "seed-1:abc")}) == [bot] and round(lad.get(bot).rating) == 1777
    lad.result("person", bot)   # the bot moves after a game
    moved = lad.get(bot).rating
    assert lad.set_bots({bot: (1777.0, ladder.BOT_RD, "seed-1:abc")}) == [] and lad.get(bot).rating == moved, "the same measurement is applied once"
    # another measurement (a new seed, or the deck's cards changed): the bot is set again, the person keeps their games
    assert lad.set_bots({bot: (1600.0, ladder.UNMEASURED_RD, "seed-1:level:xyz")}) == [bot]
    assert round(lad.get(bot).rating) == 1600 and lad.get(bot).rd == ladder.UNMEASURED_RD and not lad.get(bot).provisional
    assert lad.get("person").games == 1


def test_a_settled_player_still_moves_about_15_for_an_even_game():
    """People keep an uncertainty of at least PLAYER_RD_FLOOR (Martin, 2026-10-01): about +-15 an even game, however many
    games they've played; bots keep their own steady BOT_RD."""
    lad = Ladder(sqlite3.connect(":memory:"), ["cats"])
    bot = bot_id("4", "cats")
    for _ in range(60):   # a long record: without the floor its uncertainty would shrink far below
        lad.result("me", bot); lad.result(bot, "me")
    me = lad.get("me")
    assert me.rd >= ladder.PLAYER_RD_FLOOR and lad.get(bot).rd <= ladder.BOT_RD + 5
    before = me.rating
    lad._put(bot, replace(lad.get(bot), rating=before))
    w, _ = lad.result("me", bot)
    assert 13 <= w.rating - before <= 18


def _far(lad: Ladder) -> None:
    for lid in list(lad.bots()):
        lad._put(lid, Rating(3000, 60, 0.06, 20))   # every pairing far out of reach, until a test places some


def test_a_person_meets_the_bots_within_the_window_and_the_strongest_level_there():
    """Martin, 2026-10-24: the bots are always there, so the only question is who is close. Within 75 of the person every
    pairing is a candidate, the strongest level is preferred at similar rating, the last decks are skipped, and a bot
    still placing is never offered."""
    lad = Ladder(sqlite3.connect(":memory:"), ["cats", "fish", "giants", "colony", "token"])
    _far(lad)
    for (level, deck), r in {("5", "cats"): 1560, ("4", "fish"): 1510, ("1", "giants"): 1500, ("5", "colony"): 1440,
                             ("4", "token"): 1700, ("5", "token"): 1900}.items():
        lad._put(bot_id(level, deck), ladder.bot_seed(r))
    lad._put(bot_id("5", "fish"), Rating(1505, 350, 0.06, 3))   # placing: not yet
    rng = random.Random(3)
    picks = {lad.nearest_bot(1500, rng) for _ in range(200)}
    assert picks == {bot_id("5", "cats"), bot_id("5", "colony")}, picks   # the level 5s within 75; the others wait
    picks = {lad.nearest_bot(1500, rng, avoid={"cats", "colony"}) for _ in range(200)}
    assert picks == {bot_id("4", "fish")}, picks                          # the next level down
    picks = {lad.nearest_bot(1500, rng, avoid={"cats", "colony", "fish"}) for _ in range(50)}
    assert picks == {bot_id("1", "giants")}, picks
    assert {parse_bot(lad.nearest_bot(1620, rng))[1] for _ in range(100)} == {"cats"}   # within 75 of 1620: only level 5 Cats


def test_a_player_above_every_bot_meets_five_decks_and_never_the_one_just_met():
    """A player far above them all, nobody within the window, still meets the five nearest decks, at random, never the
    deck of their last bot games (Martin, 2026-10-02: variety at the top)."""
    decks = ["cats", "den_rush", "food_otk", "canines", "giants", "colony", "egg_control"]
    lad = Ladder(sqlite3.connect(":memory:"), decks)
    for lid in list(lad.bots()):
        lad._put(lid, Rating(100, 60, 0.06, 20))
    seed = {("5", "cats"): 1776, ("5", "den_rush"): 1716, ("4", "cats"): 1716, ("5", "food_otk"): 1685, ("5", "canines"): 1670,
            ("5", "giants"): 1670, ("4", "colony"): 1641, ("5", "colony"): 1537, ("5", "egg_control"): 1256}
    for (level, deck), r in seed.items():
        lad._put(bot_id(level, deck), ladder.bot_seed(r))
    rng = random.Random(7)
    met = {parse_bot(lad.nearest_bot(2200, rng))[1] for _ in range(300)}
    assert met == {"cats", "den_rush", "food_otk", "canines", "giants"}, met
    for _ in range(100):
        assert parse_bot(lad.nearest_bot(2200, rng, avoid={"cats", "giants"}))[1] not in {"cats", "giants"}
    picks = [lad.nearest_bot(2200, rng) for _ in range(200)]
    assert bot_id("4", "cats") not in picks, "of one deck, only its nearest bot"


def test_a_bot_whose_deck_left_the_pool_never_plays_or_shows_and_tied_decks_take_turns():
    """A deck a card change made illegal is out of the pool: its bots keep their rows and their games, and are neither
    met nor listed. The old game's bots, still in a database from before 2026-11-20, are the same."""
    lad = Ladder(sqlite3.connect(":memory:"), [f"d{i}" for i in range(8)])
    for lid in list(lad.bots()):
        lad._put(lid, ladder.bot_seed(1500 if parse_bot(lid)[0] == "3" else 900))
    for gone in ("bot:3:gone", "bot:expert:d0", "bot:normal:fish"):
        lad._put(gone, ladder.bot_seed(1500))          # exactly the player's rating: nearest of all, were they playing
    rng = random.Random(0)
    picks = {lad.nearest_bot(1500, rng) for _ in range(300)}
    assert picks == {bot_id("3", f"d{i}") for i in range(8)}, "eight decks tied at 1500, all of them met, nobody else"
    assert not {"bot:3:gone", "bot:expert:d0", "bot:normal:fish"} & ({lid for lid, _ in lad.table()} | set(lad.bots()))
    assert lad.get("bot:3:gone").rating == 1500, "the row is kept"


def test_a_rating_sits_on_one_rung_and_a_bot_is_named_by_it():
    """A bot is named by the band its own rating sits in, never by its level (Martin, 2026-10-20)."""
    assert [ladder.rung_of(r) for r in (1000, 1299, 1300, 1699, 1700, 1899, 1900, 2200)] == \
        ["Beginner", "Beginner", "Intermediate", "Advanced", "Expert", "Expert", "Legendary", "Legendary"]
    assert [n for n, _ in ladder.RUNGS] == [ladder.rung_of(f) for _, f in ladder.RUNGS]


# ----------------------------------------------------------------- a ranked match through the server
def _served(monkeypatch, tmp_path, body):
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")
    monkeypatch.setattr(server, "BOT_PAUSE", {"choice": 0, "open": 0, "move": 0})
    monkeypatch.setattr(custom_decks, "DECKS_FILE", tmp_path / "web_decks.json")
    monkeypatch.setattr(guard, "limiter", guard.Limiter())
    monkeypatch.setattr(server, "hub", server.Hub())

    async def run():
        async with TestClient(TestServer(server.make_app())) as c:
            a = await (await c.post("/api/profile", json={})).json()
            await body(c, a["profile"]["id"], {"X-AK-Key": a["code"]})
    asyncio.run(run())


def test_ranked_is_a_match_at_once_against_a_bot_from_your_league(monkeypatch, tmp_path):
    async def body(c, pid, h):
        me = await (await c.get("/api/me", headers=h)).json()
        assert me["league"]["label"] == "Wood 3" and "rank" not in me, "everyone starts at the bottom, unranked until a game"
        m = await (await c.post("/api/ranked", json={"deck": DECK}, headers=h)).json()
        match = server.hub.matches[m["id"]]
        you, bot = match.seats["A"], match.seats["B"]
        assert match.phase == "playing" and match.ranked() and you.ladder == pid
        # league 1 plays the bots rated under 1100; when none is, the bot nearest the league: the weakest level
        level, deck = parse_bot(bot.ladder)
        assert bot.is_bot and bot.level == level == "1" and bot.deck == deck and bot.spec == "greedy"
        # the view says the match is ranked; the bot is called by the band its rating sits in, never by its deck
        assert match.view("A")["ranked"] and bot.name == f"{ladder.rung_of(server.ladder.get(bot.ladder).rating)} Bot"
        # what the versus moment shows: each player's name, their deck's leader and their league (a bot's read off its rating)
        vs = m["versus"]
        assert vs["you"]["leader"] and vs["you"]["league"]["label"] == "Wood 3" and "#" not in vs["you"]["name"]
        assert vs["them"]["name"] == bot.name and vs["them"]["leader"] == server.DECK_LEADERS[deck]
        r = server.ladder.get(bot.ladder).rating
        assert vs["them"]["league"]["name"] == server.tiers_mod.name(server.tiers_mod.league_of(r)) and 1 <= vs["them"]["league"]["division"] <= 3
        with pytest.raises(Exception, match="no rematch"):
            match.phase = "match_over"; match.offer_rematch("A")
    _served(monkeypatch, tmp_path, body)


def test_a_ranked_result_moves_the_rating_the_league_and_the_leaderboard(monkeypatch, tmp_path):
    async def body(c, pid, h):
        m = await (await c.post("/api/ranked", json={"deck": DECK}, headers=h)).json()
        match = server.hub.matches[m["id"]]
        bot, before = match.seats["B"].ladder, server.ladder.get(match.seats["B"].ladder)
        match.concede("B")   # the bot's seat gives up: the person won
        v = match.view("A")
        assert v["rating"]["delta"] > 50 and v["rating"]["after"].endswith("?"), "a first win moves a new player a lot, even over a weak bot"
        assert v["league"]["label"] == "Wood 3" and v["league"]["stars"] == 1 and v["league"]["line"] == ""
        assert v["league"]["before"]["label"] == "Wood 3" and v["league"]["before"]["stars"] == 0, "the standing going in, for the match's last screen"
        assert server.ladder.get(pid).games == 1 and server.ladder.get(bot).rating < before.rating
        server.rate_match(match)
        assert server.ladder.get(pid).games == 1, "a match is rated once"
        # the leaderboard: the person from their first rated game, with their league and no number; the bots one row
        # per level and deck, best first, each with its deck's leader
        rows = (await (await c.get("/api/leaderboard", headers=h)).json())["rows"]
        mine = next(r for r in rows if r["you"])
        assert mine["league"]["label"] == "Wood 3" and mine["rating"] is None
        bots = [r for r in rows if r["bot"]]
        assert len(bots) == len(ladder.LEVELS) * len(server.ladder.decks) and all(r["name"].endswith(" Bot)") and r["leader"] for r in bots)
        assert [int(r["rating"]) for r in bots] == sorted((int(r["rating"]) for r in bots), reverse=True)
        # home shows the place that row has
        me = await (await c.get("/api/me", headers=h)).json()
        assert me["rank"] == rows.index(mine) + 1 and me["league"]["stars"] == 1
        # the next match is against another deck than the one just met, while the pool has two
        if len(server.ladder.decks) > 1:
            for _ in range(5):
                n = await (await c.post("/api/ranked", json={"deck": DECK}, headers=h)).json()
                assert server.hub.matches[n["id"]].seats["B"].deck != match.seats["B"].deck
    _served(monkeypatch, tmp_path, body)


def test_home_shows_the_rank_your_leaderboard_row_has(monkeypatch, tmp_path):
    async def body(c, pid, h):
        for rating in (900, 1500, 2600):   # below every bot, among them, above them all
            server.ladder._put(pid, Rating(rating, 60, 0.06, 20))
            server.tiers.put(pid, tiers.from_rating(rating, 20), 20)
            rows = (await (await c.get("/api/leaderboard", headers=h)).json())["rows"]
            me = await (await c.get("/api/me", headers=h)).json()
            assert me["rank"] == next(i for i, r in enumerate(rows) if r["you"]) + 1, rating
    _served(monkeypatch, tmp_path, body)


def test_a_ranked_match_survives_a_restart_with_its_bot_and_its_result(monkeypatch, tmp_path):
    from animal_kingdom.web.match import Match

    async def body(c, pid, h):
        m = await (await c.post("/api/ranked", json={"deck": DECK}, headers=h)).json()
        match = server.hub.matches[m["id"]]
        back = Match.from_dict(match.to_dict())
        assert back.ranked() and back.seats["B"].level == match.seats["B"].level and back.bots["B"].spec == match.seats["B"].spec
        match.concede("B")
        back = Match.from_dict(match.to_dict())
        assert back.view("A")["rating"] == match.view("A")["rating"] and back.view("A")["league"] == match.view("A")["league"]
    _served(monkeypatch, tmp_path, body)
