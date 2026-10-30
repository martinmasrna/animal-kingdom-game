"""The league's door into the ladder (web/league.py, docs/league.md): bot games rated like anyone's, new lists joining as
placing players, the key that guards both."""

import asyncio
import json

import pytest

from animal_kingdom.decks import load_premade_deck
from animal_kingdom.web import ladder as ranking


def _run(monkeypatch, tmp_path, body):
    from aiohttp.test_utils import TestClient, TestServer
    from animal_kingdom.web import custom_decks, league, server
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")
    monkeypatch.setenv("AK_LEAGUE_KEY", "k-test")
    monkeypatch.setattr(custom_decks, "DECKS_FILE", tmp_path / "web_decks.json")

    async def run():
        async with TestClient(TestServer(server.make_app())) as c:
            await body(c, server)
    asyncio.run(run())


def test_the_league_calls_need_the_key(monkeypatch, tmp_path):
    async def body(c, server):
        assert (await c.get("/api/league/pool")).status == 403
        assert (await c.get("/api/league/pool", headers={"X-AK-League-Key": "wrong"})).status == 403
        assert (await c.post("/api/league/games", json={"games": []}, headers={"X-AK-League-Key": "wrong"})).status == 403
        r = await c.get("/api/league/pool", headers={"X-AK-League-Key": "k-test"})
        assert r.status == 200
        j = await r.json()
        assert {d["slug"] for d in j["decks"]} == set(server.ladder.decks) and len(j["players"]) == 3 * len(j["decks"])
        assert set(j["pilots"]) == {"easy", "normal", "expert"} and all(d["list"] == load_premade_deck(d["slug"]) for d in j["decks"])
    _run(monkeypatch, tmp_path, body)


def test_a_posted_bot_game_moves_both_pairings_like_any_game(monkeypatch, tmp_path):
    async def body(c, server):
        h = {"X-AK-League-Key": "k-test"}
        a, b = ranking.bot_id("expert", "cats"), ranking.bot_id("expert", "fish")
        before = (server.ladder.get(a), server.ladder.get(b))
        r = await c.post("/api/league/games", json={"games": [
            {"a": a, "b": b, "winner": "A", "seed": 1, "turns": 9, "reason": "hq_capture"},
            {"a": a, "b": b, "winner": None, "seed": 2, "turns": 30, "reason": "turn_limit"},   # a draw rates nothing
            {"a": a, "b": "bot:expert:no_such_deck", "winner": "B", "seed": 3},                 # unknown pairing: dropped
            {"a": "9429ccf2c28900ca", "b": b, "winner": "A", "seed": 4}]}, headers=h)             # a person: never through here
        j = await r.json()
        assert j["rated"] == 2 and set(j["ratings"]) == {a, b}
        after = (server.ladder.get(a), server.ladder.get(b))
        assert after[0].rating > before[0].rating and after[1].rating < before[1].rating
        assert after[0].games == before[0].games + 1 and after[1].games == before[1].games + 1
        rows = [tuple(r) for r in server.profiles.db.execute("SELECT a, b, winner FROM league_games ORDER BY id").fetchall()]
        assert rows == [(a, b, "A"), (a, b, None)]
    _run(monkeypatch, tmp_path, body)


def test_a_new_list_joins_as_three_placing_players_kept_from_people(monkeypatch, tmp_path):
    from animal_kingdom.web import meta
    monkeypatch.setattr(meta, "ARCHETYPES", tmp_path / "none.json")   # no archetypes: the bot keeps its list's own name

    async def body(c, server):
        h = {"X-AK-League-Key": "k-test"}
        lst = load_premade_deck("cats")
        lst2 = [c_ if c_ != lst[0] else "lion" for c_ in lst]   # one card changed, still legal? the test picks a plain swap
        # a legal distinct list: swap one Cats card for a common that the deck does not hold twice already
        from animal_kingdom.decks import decklist_problems
        from animal_kingdom.engine.cards import load_cards
        cards = load_cards()
        pool_ids = [cid for cid, card in cards.items() if card.collectible and cid not in lst and card.rarity == "common"]
        child = sorted(lst[1:] + [pool_ids[0]])
        assert not decklist_problems(child)
        r = await c.post("/api/league/decks", json={"decks": [
            {"slug": "league_cats_1", "name": "Savanna Cats III", "list": child, "source": "tinker", "parent": "cats", "start": 2050},
            {"slug": "league_dup", "name": "Twin", "list": lst, "source": "test"},               # identical to Cats: refused
            {"slug": "bad slug!", "name": "X", "list": child[:29], "source": "test"}]}, headers=h)
        j = await r.json()
        assert j["added"] == ["league_cats_1"] and set(j["rejected"]) == {"league_dup", "bad slug!"}
        assert "an identical list is already a player" in j["rejected"]["league_dup"][0]
        # three placing players, loadable, named, listed, and never handed to a person until placed
        for level in ranking.LEVELS:   # born at its parent's rating, the best prior, with a newcomer's wide uncertainty
            rr = server.ladder.get(ranking.bot_id(level, "league_cats_1"))
            assert rr.provisional and rr.rating == 2050 and rr.rd == ranking.START_RD
        assert load_premade_deck("league_cats_1") == child and server.DECK_NAMES["league_cats_1"] == "Savanna Cats III"
        import random
        assert "league_cats_1" not in {ranking.parse_bot(server.ladder.nearest_bot(1500, random.Random(i)))[1] for i in range(60)}
        board = await (await c.get("/api/leaderboard")).json()
        row = next(x for x in board["rows"] if x["bot"] and x.get("deck") == "league_cats_1")
        assert row["rating"].endswith("?") and row["name"].startswith("Savanna Cats III")
        # placed after ten bot games, it is offered like any other bot
        a = ranking.bot_id("expert", "league_cats_1")
        games = [{"a": a, "b": ranking.bot_id("expert", "fish"), "winner": "A" if i % 2 else "B", "seed": 100 + i} for i in range(10)]
        assert (await (await c.post("/api/league/games", json={"games": games}, headers=h)).json())["rated"] == 10
        assert not server.ladder.get(a).provisional
        pool = await (await c.get("/api/league/pool", headers=h)).json()
        assert "league_cats_1" in {d["slug"] for d in pool["decks"]}
        # the pool survives a restart: the row is in the database
        assert tuple(server.profiles.db.execute("SELECT name, source, parent FROM pool_decks WHERE slug = 'league_cats_1'").fetchone()) == ("Savanna Cats III", "tinker", "cats")
    _run(monkeypatch, tmp_path, body)


def test_the_meta_report_is_posted_by_the_runner_and_served_with_the_people(monkeypatch, tmp_path):
    async def body(c, server):
        h = {"X-AK-League-Key": "k-test"}
        assert (await (await c.get("/api/league/report")).json()) == {"empty": True}
        assert (await c.post("/api/league/report", json={"report": {"generated": "x"}})).status == 403
        r = await c.post("/api/league/report", json={"report": {"generated": "2026-10-25 06:00", "top": [], "meta": {}}}, headers=h)
        assert r.status == 200
        server.ladder.result(server.ladder.get("someone") and "someone", ranking.bot_id("expert", "cats"))
        j = await (await c.get("/api/league/report")).json()
        assert j["generated"] == "2026-10-25 06:00" and j["people"] and j["people"][0]["games"] == 1
    _run(monkeypatch, tmp_path, body)


def test_a_retired_list_leaves_the_pool_and_stays_out_after_a_restart(monkeypatch, tmp_path):
    async def body(c, server):
        h = {"X-AK-League-Key": "k-test"}
        assert "fish" in server.ladder.decks
        j = await (await c.post("/api/league/retire", json={"slugs": ["fish", "no_such_deck"]}, headers=h)).json()
        assert j["retired"] == ["fish"] and "fish" not in server.ladder.decks
        pool = await (await c.get("/api/league/pool", headers=h)).json()
        assert "fish" not in {d["slug"] for d in pool["decks"]} and not any(p["id"].endswith(":fish") for p in pool["players"])
        assert server.league.retired() == {"fish"}
        assert (await c.post("/api/league/retire", json={"slugs": ["cats"]})).status == 403
    _run(monkeypatch, tmp_path, body)


def test_a_retired_lists_twin_comes_back_fresh_and_only_at_the_levels_asked(monkeypatch, tmp_path):   # a legal list: a design change can leave one illegal
    async def body(c, server):
        h = {"X-AK-League-Key": "k-test"}
        twin = {"slug": "cats_again", "name": "Cats", "list": load_premade_deck("cats"), "levels": ["expert"]}
        j = await (await c.post("/api/league/decks", json={"decks": [twin]}, headers=h)).json()
        assert j["added"] == [] and "cats_again" in j["rejected"]               # the original still plays: no twin
        await c.post("/api/league/retire", json={"slugs": ["cats"]}, headers=h)
        j = await (await c.post("/api/league/decks", json={"decks": [twin]}, headers=h)).json()
        assert j["added"] == ["cats_again"]
        pool = await (await c.get("/api/league/pool", headers=h)).json()
        assert [p["id"] for p in pool["players"] if p["id"].endswith(":cats_again")] == ["bot:expert:cats_again"]
    _run(monkeypatch, tmp_path, body)


def test_a_person_can_be_reset_but_not_a_bot(monkeypatch, tmp_path):
    async def body(c, server):
        h = {"X-AK-League-Key": "k-test"}
        server.ladder.result("p1", "bot:expert:cats"); bot = server.ladder.get("bot:expert:cats").games
        j = await (await c.post("/api/league/reset_people", json={"ids": ["p1", "bot:expert:cats"]}, headers=h)).json()
        assert j["reset"] == ["p1"] and server.ladder.get("p1").games == 0 and server.ladder.get("bot:expert:cats").games == bot
    _run(monkeypatch, tmp_path, body)


def test_the_meta_tab_survives_a_bad_range(monkeypatch, tmp_path):
    async def body(c, server):
        assert (await c.get("/api/meta?lo=NaN&hi=NaN&days=7")).status == 200
    _run(monkeypatch, tmp_path, body)


def test_a_list_kept_to_expert_loses_its_other_pilots_and_a_restart_keeps_it_so(monkeypatch, tmp_path):
    async def body(c, server):
        from animal_kingdom.web import ladder as ranking
        h = {"X-AK-League-Key": "k-test"}
        j = await (await c.post("/api/league/levels", json={"slugs": ["cats"], "levels": ["expert"]}, headers=h)).json()
        assert j["slugs"] == ["cats"]
        assert {lid for lid in server.ladder.bots() if lid.endswith(":cats")} == {"bot:expert:cats"}
        g = {"gid": "x-1", "a": "bot:easy:cats", "b": "bot:expert:fish", "winner": "A", "seed": 1, "turns": 9, "reason": "food"}
        j = await (await c.post("/api/league/games", json={"games": [g]}, headers=h)).json()
        assert j["rated"] == 0 and "bot:easy:cats" not in server.ladder.bots()   # a late result can't bring the pilot back
        again = ranking.Ladder(server.ladder.db, server.ladder.decks, server.league.levels())   # what a restart builds
        assert {lid for lid in again.bots() if lid.endswith(":cats")} == {"bot:expert:cats"}
    _run(monkeypatch, tmp_path, body)


def test_a_game_posted_twice_is_rated_once(monkeypatch, tmp_path):
    async def body(c, server):
        h = {"X-AK-League-Key": "k-test"}
        before = server.ladder.get("bot:expert:cats").games
        g = {"gid": "123-0", "a": "bot:expert:cats", "b": "bot:expert:fish", "winner": "A", "seed": 1, "turns": 9, "reason": "hq_capture"}
        j1 = await (await c.post("/api/league/games", json={"games": [g]}, headers=h)).json()
        j2 = await (await c.post("/api/league/games", json={"games": [g, {**g, "gid": "123-1"}]}, headers=h)).json()
        assert (j1["rated"], j1["seen"]) == (1, 0) and (j2["rated"], j2["seen"]) == (1, 1)
        assert server.ladder.get("bot:expert:cats").games == before + 2
    _run(monkeypatch, tmp_path, body)


def test_card_facts_feed_the_meta_tab_by_martins_archetypes(monkeypatch, tmp_path):
    from animal_kingdom.web import meta
    (tmp_path / "a.json").write_text(json.dumps({"archetypes": [{"name": "Cats", "lists": ["cats"]}, {"name": "Fish Token", "lists": ["fish"]}]}))
    monkeypatch.setattr(meta, "ARCHETYPES", tmp_path / "a.json")
    cats, fish = load_premade_deck("cats"), load_premade_deck("fish")
    side = lambda l: {"seen": l[:4], "back": [], "cards": [[l[0], 0, 1], [l[5], 2, None]]}
    g = {"a": "bot:expert:cats", "b": "bot:expert:fish", "winner": "A", "seed": 1, "turns": 9, "reason": "hq_capture"}

    async def body(c, server):
        h = {"X-AK-League-Key": "k-test"}
        assert (await c.post("/api/league/facts", json={"games": []})).status == 403
        await c.post("/api/league/games", json={"games": [{**g, "t": 1e9 * 1.8, "facts": {"ra": 1500, "rb": 1500, "A": side(cats), "B": side(fish)}}]}, headers=h)
        j = await (await c.post("/api/league/facts", json={"games": [{**g, "winner": "B", "ra": 1500, "rb": 1500, "A": side(cats), "B": side(fish)}]}, headers=h)).json()
        assert j["counted"] == 1
        o = await (await c.get("/api/meta?lo=1400&hi=1600")).json()
        assert o["games"] == 2 and {r["name"]: r["wins"] for r in o["archetypes"]} == {"Cats": 1, "Fish Token": 1}
        a = await (await c.get("/api/meta/archetype?id=cats&vs=fish_token")).json()
        assert a["name"] == "Cats" and a["vs_name"] == "Fish Token" and {x["card"]: x["p"]["yes"] for x in a["cards"]}[cats[0]] == [2, 1]
        assert (await c.get("/api/meta/archetype?id=nope")).status == 404
        assert server.ladder_name("bot:expert:fish").startswith("Fish Token (")   # the ladder names a bot by its archetype
    _run(monkeypatch, tmp_path, body)
