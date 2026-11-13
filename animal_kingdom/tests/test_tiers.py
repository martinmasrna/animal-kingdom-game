"""Ranked leagues (web/tiers.py): one test per rule of docs/ranked-leagues.md (Martin, 2026-11-05)."""

import random
import sqlite3

from animal_kingdom.web import ladder, tiers as T
from animal_kingdom.web.tiers import Standing, after_game


def at(league, stars=0, streak=0):
    return Standing(league, stars, streak, league)


def test_the_table():
    assert T.TOP == 11 and [T.name(i) for i in range(1, 12)] == [
        "Wood", "Bone", "Stone", "Copper", "Silver", "Gold", "Jade", "Sapphire", "Ruby", "Diamond", "Legend"]
    assert [T.stars_needed(i) for i in range(1, 11)] == [15] * 10 and T.stars_needed(T.TOP) == 0
    assert [T.par(i) for i in range(1, 12)] == [1000 + 100 * i for i in range(11)]


def test_three_stages_of_five_wins():
    assert [T.stage_of(n) for n in (0, 4, 5, 9, 10, 14)] == [(1, 0), (1, 4), (2, 0), (2, 4), (3, 0), (3, 4)]
    assert T.label(at(6, 7)) == "Gold 2" and T.label(at(T.TOP)) == "Legend"


def test_everyone_starts_in_league_1():
    assert Standing() == Standing(1, 0, 0, 1)
    assert T.Tiers(sqlite3.connect(":memory:")).get("someone") == Standing()


def test_a_win_gains_one_and_two_from_the_third_in_a_row():
    assert after_game(at(5, 1), True).after == Standing(5, 2, 1, 5)
    ch = after_game(at(5, 0, streak=2), True)
    assert ch.gained == 2 and ch.streak_bonus and ch.after.stars == 2
    assert after_game(ch.after, True).gained == 2, "and every win after it"
    assert after_game(at(10, 0, streak=5), True).gained == 2, "in every league below the top"


def test_moving_up_carries_a_spare_win():
    ch = after_game(at(2, 14), True)
    assert ch.promoted and ch.after.league == 3 and ch.after.stars == 0
    ch = after_game(at(2, 14, streak=2), True)
    assert ch.after.league == 3 and ch.after.stars == 1
    ch = after_game(at(10, 14), True)
    assert ch.after.league == T.TOP and ch.after.stars == 0


def test_a_loss_loses_one_and_ends_the_streak():
    ch = after_game(at(5, 3, streak=4), False)
    assert ch.after == Standing(5, 2, 0, 5) and ch.gained == 1
    assert after_game(at(5, 5), False).after.stars == 4, "down a stage inside the league"


def test_a_loss_with_none_left_drops_a_league_but_never_out_of_league_1():
    ch = after_game(at(7, 0), False)
    assert ch.demoted and ch.after.league == 6 and ch.after.stars == 14
    ch = after_game(at(1, 0), False)
    assert ch.after.league == 1 and ch.after.stars == 0 and not ch.demoted


def test_the_top_league_is_kept_and_shows_the_rating():
    ch = after_game(at(T.TOP), False)
    assert ch.after.league == T.TOP
    v = T.view(at(T.TOP), "2087")
    assert v["top"] and v["rating"] == "2087" and "stars" not in v
    v = T.view(at(6, 7), "1500")
    assert (v["label"], v["stage"], v["stars"], v["of"], v["stages"]) == ("Gold 2", 2, 2, 5, 3) and "rating" not in v


def test_each_league_plays_a_band_of_bot_ratings():
    assert T.band(1) == (float("-inf"), 1100) and T.band(5) == (1400, 1500) and T.band(T.TOP) == (2000, float("inf"))
    assert [T.league_of(r) for r in (900, 1000, 1099, 1100, 1550, 1899, 1900, 2000, 2400)] == [1, 1, 1, 2, 6, 9, 10, 11, 11]


def test_a_ranked_bot_comes_from_the_league_band():
    db = sqlite3.connect(":memory:")
    L = ladder.Ladder(db, ["cats", "fish", "canines"])
    for lid, r in (("bot:expert:cats", 1450), ("bot:normal:fish", 1420), ("bot:expert:canines", 1720)):
        L._put(lid, ladder.bot_seed(r))
    rng = random.Random(1)
    assert {L.bot_in(*T.band(5), rng) for _ in range(20)} == {"bot:expert:cats"}, "the strongest pilot in the band"
    assert L.bot_in(*T.band(5), rng, avoid={"cats"}) == "bot:normal:fish", "a recent deck is skipped"
    assert L.bot_in(5000, 6000, rng) is None, "an empty band: the caller falls back to the nearest bot"


def test_the_end_of_match_line():
    assert after_game(at(5, 0, streak=2), True).line() == "Silver 1, win streak: +2"
    assert after_game(at(5, 0), True).line() == "Silver 1"
    assert after_game(at(5, 2), False).line() == "Silver 1"
    assert after_game(at(5, 4), True).line() == "Up to Silver 2"
    assert after_game(at(5, 5), False).line() == "Down to Silver 1"
    assert after_game(at(6, 14), True).line() == "Up to Jade 1"
    assert after_game(at(5, 0), False).line() == "Down to Copper 3"
    assert after_game(at(10, 14), True).line("2004") == "Up to Legend"
    assert after_game(at(T.TOP), True).line("2011") == "Legend: rating 2011"


def test_the_leaderboard_key():
    assert T.sort_key(at(8, 6), 1500) == 1740
    assert T.sort_key(at(T.TOP), 2033.0) == 2033.0


def test_migration_from_the_rating():
    assert T.from_rating(1820, 50) == Standing(9, 0, 0, 9)
    assert T.from_rating(1500, 50) == Standing(6, 0, 0, 6)
    assert T.from_rating(950, 50) == Standing()
    assert T.from_rating(2400, 50).league == 10, "the top is reached by a win"
    assert T.from_rating(1700, 9) == Standing(), "still placing: league 1"


def test_migration_runs_once_and_skips_bots():
    db = sqlite3.connect(":memory:")
    L = ladder.Ladder(db, ["cats"])
    for _ in range(12):
        L.result("veteran", "bot:easy:cats")
    t = T.Tiers(db)
    people = {lid: r for lid, r in L.table() if not lid.startswith("bot:")}
    assert t.migrate(people) == 1 and t.get("veteran") == T.from_rating(L.get("veteran").rating, 12)
    assert not any(lid.startswith("bot:") for lid in t.all())
    t.put("veteran", Standing(), 0)
    assert t.migrate(people) == 0 and t.get("veteran") == Standing(), "once only"


def test_standings_from_the_first_build_are_converted_once():
    db = sqlite3.connect(":memory:")
    t = T.Tiers(db)
    db.execute("CREATE TABLE IF NOT EXISTS ladder_meta (k TEXT PRIMARY KEY, v TEXT NOT NULL)")
    db.execute("INSERT INTO ladder_meta VALUES ('tiers_migrated', '1')")   # a database that already had leagues
    for pid, lg, stars, best in (("low", 2, 2, 2), ("mid", 6, 3, 7), ("top", 10, 0, 10)):
        db.execute("INSERT INTO tiers VALUES (?, ?, ?, 0, ?, 5)", (pid, lg, stars, best))
    assert t.migrate({}) == 0
    assert t.get("low") == Standing(2, 10, 0, 2), "2 of 3 stars: the same share of fifteen"
    assert t.get("mid") == Standing(6, 9, 0, 7), "3 of 5 stars"
    assert t.get("top") == Standing(T.TOP, 0, 0, T.TOP), "the old top league is the new one"
    t.migrate({})
    assert t.get("mid") == Standing(6, 9, 0, 7), "once only"
