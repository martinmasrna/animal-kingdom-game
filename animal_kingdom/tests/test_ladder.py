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
            m = await (await c.post("/api/ranked", json={"deck": "cats"}, headers=ha)).json()
            match = server.hub.matches[m["id"]]
            bot = match.seats["B"]   # a seeded bot within reach of a new player's 1500 (nearest_bot: among the five nearest decks)
            assert bot.is_bot and bot.ladder.startswith("bot:") and abs(server.ladder.get(bot.ladder).rating - 1500) < 250
            assert match.seats["A"].ladder == a["profile"]["id"]
            # the match states both ratings as they stood going in, for the versus moment; an unrated match states none.
            # A bot states the rating of the pairing that plays: its own leaderboard row
            seats = match.view("A")["seats"]
            rung = ladder.rung_of(server.ladder.get(bot.ladder).rating)   # a bot is named by its rung, not its level
            assert bot.name.endswith(f"({rung} Bot)")
            row = next(r for r in (await (await c.get("/api/leaderboard", headers=ha)).json())["rows"] if r["name"] == bot.name and r["deck"] == bot.deck)
            assert seats["A"]["rating"] == "1500?" and seats["B"]["rating"] == row["rating"] == server.ladder.get(bot.ladder).shown()
            # two people at once: they meet each other
            ra, rb = await asyncio.gather(c.post("/api/ranked", json={"deck": "giants"}, headers=ha),
                                          c.post("/api/ranked", json={"deck": "den_rush"}, headers=hb))
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
            bots = [r for r in board["rows"] if r["bot"]]   # one row per pilot-and-deck pairing, best first
            assert len(bots) == len(ladder.LEVELS) * len(server.ladder.decks) and all(r["name"].endswith(" Bot)") for r in bots)
            assert [int(r["rating"]) for r in bots] == sorted((int(r["rating"]) for r in bots), reverse=True)
            me = await (await c.get("/api/me", headers=ha)).json()   # home's name piece: placement progress, no rank yet
            assert me["placing"] == {"games": 1, "of": 10} and "rank" not in me
    asyncio.run(run())


def test_a_seed_file_sets_the_bots_once(tmp_path):
    import json, sqlite3
    L = ladder.Ladder(sqlite3.connect(":memory:"), ["cats", "giants"])
    f = tmp_path / "seed.json"
    f.write_text(json.dumps({"version": "v1", "ratings": {"bot:expert:ramp": 1777.0, "bot:easy:cats_midrange": 1111.0}}))
    assert L.apply_seed(f) and round(L.get("bot:expert:ramp").rating) == 1777
    L.result("p1", "bot:expert:ramp")   # the bot moves after a game
    assert not L.apply_seed(f), "the same seed is applied once"


def test_a_seed_can_reset_the_people_for_placement_games(tmp_path):
    import json, sqlite3
    db = sqlite3.connect(":memory:"); L = ladder.Ladder(db, ["ramp"])
    L.result("person-1", "bot:expert:ramp")
    assert L.get("person-1").games == 1
    f = tmp_path / "seed.json"
    f.write_text(json.dumps({"version": "v2", "reset_people": True, "ratings": {"bot:expert:ramp": 1900}}))
    assert L.apply_seed(f)
    assert L.get("person-1").games == 0 and L.get("person-1").rating == ladder.START, "everyone places again"
    assert round(L.get("bot:expert:ramp").rating) == 1900
    g = tmp_path / "seed2.json"
    g.write_text(json.dumps({"version": "v3", "ratings": {"bot:expert:ramp": 1950}}))
    L.result("person-1", "bot:expert:ramp")
    assert L.apply_seed(g) and L.get("person-1").games == 1, "a seed without the flag leaves people alone"
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
                m = await (await c.post("/api/ranked", json={"deck": "cats"}, headers={"X-AK-Key": a["code"]})).json()
                match = server.hub.matches[m["id"]]
                match.ready("A") if match.phase != "playing" else None
                server.hub.kick_bot(match)
                for _ in range(40):   # the bot's mulligan, or its first moves, get played for it
                    await asyncio.sleep(0.1)
                    if any(p == "B" for p in (getattr(h, "seat", None) for h in match.history)) or len(match.actions) > 0:
                        break
                assert len(match.actions) > 0 or match.to_act() == "A", "the bot moved"
        asyncio.run(run())


def test_a_bot_whose_move_is_refused_still_moves(monkeypatch):
    """The other way a match froze: the bot chose a move and the match refused it (verification 2026-10-17: the task died with
    the exception, and only conceding got the player out). Now it plays a fallback, and the task's death would be logged."""
    import asyncio
    from aiohttp.test_utils import TestClient, TestServer
    from animal_kingdom.web import server
    from animal_kingdom.web.match import Match
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")
    monkeypatch.setattr(server, "RANKED_WAIT", 0.1)
    monkeypatch.setattr(server, "BOT_PAUSE", {"choice": 0, "open": 0, "move": 0})
    real_act, refused = Match.act, []

    def act(self, s, action, auto=False):
        if self.seats[s].is_bot and not refused:   # the bot's first move is refused once
            refused.append(action)
            raise RuntimeError("refused")
        return real_act(self, s, action, auto)
    monkeypatch.setattr(Match, "act", act)

    async def run():
        async with TestClient(TestServer(server.make_app())) as c:
            a = await (await c.post("/api/profile", json={})).json()
            m = await (await c.post("/api/ranked", json={"deck": "cats"}, headers={"X-AK-Key": a["code"]})).json()
            match = server.hub.matches[m["id"]]
            real_act(match, "A", {"kind": "choice", "choice": "__skip__"})   # the person keeps their hand; the bot is to act
            server.hub.kick_bot(match)
            for _ in range(60):
                await asyncio.sleep(0.1)
                if refused and match.to_act() == "A":
                    break
            assert refused, "the first bot move was refused"
            assert match.to_act() == "A", "the bot still moved"
            task = server.hub.bot_tasks[match.id]
            assert not task.done() or task.exception() is None, "the bot task did not die"
    asyncio.run(run())


def test_a_settled_player_still_moves_about_15_for_an_even_game():
    """People keep an uncertainty of at least PLAYER_RD_FLOOR (Martin, 2026-10-01): about +-15 an even game, however many
    games they've played; bots keep their own steady BOT_RD."""
    import sqlite3
    from animal_kingdom.web.ladder import Ladder, PLAYER_RD_FLOOR, BOT_RD, bot_id
    lad = Ladder(sqlite3.connect(":memory:"), ["cats"])
    bot = bot_id("normal", "cats")
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


def test_a_player_at_the_top_meets_five_decks_and_never_the_same_one_twice_running():
    """The ladder's bots are rated per level and deck, and a bot plays some decks far better than others (Expert Egg rates
    under Easy Cats). A player far above them all still meets the five nearest decks, at random, never the deck of their
    last bot games (Martin, 2026-10-02: variety at the top)."""
    import random, sqlite3
    from animal_kingdom.web.ladder import Ladder, bot_id, parse_bot
    decks = ["cats", "den_rush", "food_otk", "canines", "giants", "colony", "egg_control"]
    lad = Ladder(sqlite3.connect(":memory:"), decks)
    seed = {("expert", "cats"): 1776, ("expert", "den_rush"): 1716, ("normal", "cats"): 1716, ("expert", "food_otk"): 1685,
            ("expert", "canines"): 1670, ("expert", "giants"): 1670, ("normal", "colony"): 1641, ("expert", "colony"): 1537,
            ("expert", "egg_control"): 1256}
    lad.seed_bots({bot_id(l, d): r for (l, d), r in seed.items()})
    rng = random.Random(7)
    met = {parse_bot(lad.nearest_bot(2200, rng))[1] for _ in range(300)}
    assert met == {"cats", "den_rush", "food_otk", "canines", "giants"}, met
    for _ in range(100):
        assert parse_bot(lad.nearest_bot(2200, rng, avoid={"cats", "giants"}))[1] not in {"cats", "giants"}
    picks = [lad.nearest_bot(2200, rng) for _ in range(200)]
    assert bot_id("normal", "cats") not in picks, "of one deck, only its nearest bot"


def test_home_shows_the_rank_your_leaderboard_row_has(monkeypatch):
    # home's name piece and the leaderboard count the same rows: ranked people and one row per bot pairing
    import asyncio
    from aiohttp.test_utils import TestClient, TestServer
    from animal_kingdom.web import server
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")

    async def run():
        async with TestClient(TestServer(server.make_app())) as c:
            a = await (await c.post("/api/profile", json={})).json()
            h = {"X-AK-Key": a["code"]}
            for rating in (900, 1500, 2600):   # below every bot level, among them, above them all
                server.ladder._put(a["profile"]["id"], Rating(rating, 60, 0.06, 20))
                rows = (await (await c.get("/api/leaderboard", headers=h)).json())["rows"]
                me = await (await c.get("/api/me", headers=h)).json()
                assert me["rank"] == next(i for i, r in enumerate(rows) if r["you"]) + 1, rating
    asyncio.run(run())


def test_cancelling_a_ranked_search_leaves_the_queue(monkeypatch):
    # the server never notices the browser dropping its request: Cancel says it, and nobody is paired with a player gone
    import asyncio
    from aiohttp.test_utils import TestClient, TestServer
    from animal_kingdom.web import server
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")
    monkeypatch.setattr(server, "RANKED_WAIT", 1.0)

    async def run():
        async with TestClient(TestServer(server.make_app())) as c:
            a, b = [await (await c.post("/api/profile", json={})).json() for _ in range(2)]
            ha, hb = {"X-AK-Key": a["code"]}, {"X-AK-Key": b["code"]}
            first = asyncio.ensure_future(c.post("/api/ranked", json={"deck": "giants"}, headers=ha))
            await asyncio.sleep(0.2)
            await c.delete("/api/ranked", headers=ha)
            assert (await (await first).json()) == {"cancelled": True}
            m = await (await c.post("/api/ranked", json={"deck": "giants"}, headers=hb)).json()
            assert server.hub.matches[m["id"]].seats["B"].is_bot, "paired with a person who had left"
    asyncio.run(run())


def test_a_retired_decks_bot_never_plays_and_tied_decks_take_turns():
    import random, sqlite3
    from animal_kingdom.web import ladder as L
    lad = L.Ladder(sqlite3.connect(":memory:"), [f"d{i}" for i in range(8)])
    lad.seed_bots({"bot:normal:retired": 1500.0})          # exactly a player's rating: nearest of all
    rng = random.Random(0)
    picks = {L.parse_bot(lad.nearest_bot(1500, rng))[1] for _ in range(200)}
    assert "retired" not in picks and len(picks) == 8        # eight decks tied at 1500, all of them met


def test_a_rating_sits_on_one_rung_and_a_bot_is_named_by_it():
    """The bots as five named opponents (Martin, 2026-10-20): five bands over the rating scale, a bot named by the band its
    own rating sits in, never by its pilot's level; since 2026-10-24 the leaderboard lists every pairing as its own row."""
    assert [ladder.rung_of(r) for r in (1000, 1299, 1300, 1699, 1700, 1899, 1900, 2200)] == \
        ["Beginner", "Beginner", "Intermediate", "Advanced", "Expert", "Expert", "Legendary", "Legendary"]
    assert [n for n, _ in ladder.RUNGS] == [ladder.rung_of(f) for _, f in ladder.RUNGS]


def test_practice_offers_the_ladders_five_bots_and_the_pilot_follows_the_band(monkeypatch, tmp_path):
    """One vocabulary (Martin, 2026-10-20): Practice's bot is one of the five bands. The server hands out the pilot whose
    rating with the chosen deck sits nearest the band, and names the seat by the band the bot's own rating sits in; the
    engine's pilot levels still work for callers that send them."""
    import asyncio
    from aiohttp.test_utils import TestClient, TestServer
    from animal_kingdom.web import custom_decks, server
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")
    monkeypatch.setattr(custom_decks, "DECKS_FILE", tmp_path / "web_decks.json")

    async def run():
        async with TestClient(TestServer(server.make_app())) as c:
            a = await (await c.post("/api/profile", json={})).json()
            h = {"X-AK-Key": a["code"]}
            rows = server.ladder.bots()
            for band in ladder.BANDS:
                m = await (await c.post("/api/match", json={"deck": "cats", "bot": {"level": band, "deck": "fish"}}, headers=h)).json()
                seat = server.hub.matches[m["id"]].seats["B"]
                assert seat.bot in ("easy", "normal", "expert") and seat.deck == "fish"
                centre = ladder.band_centre(band)
                nearest = min(("easy", "normal", "expert"), key=lambda l: abs(rows[ladder.bot_id(l, "fish")].rating - centre))
                assert seat.bot == nearest, band
                assert seat.name == f"{ladder.rung_of(rows[ladder.bot_id(seat.bot, 'fish')].rating)} Bot"
            m = await (await c.post("/api/match", json={"deck": "cats", "bot": {"level": "easy", "deck": "fish"}}, headers=h)).json()
            assert server.hub.matches[m["id"]].seats["B"].bot == "easy"            # a pilot level still works
            r = await c.post("/api/match", json={"deck": "cats", "bot": {"level": "Grandmaster", "deck": "fish"}}, headers=h)
            assert r.status == 400
    asyncio.run(run())
