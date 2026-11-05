"""Ranked leagues (web/tiers.py): one test per rule of docs/ranked-leagues.md (Martin, 2026-11-05)."""

import random
import sqlite3

from animal_kingdom.web import ladder, tiers as T
from animal_kingdom.web.tiers import Standing, after_game


def at(league, stars=0, streak=0):
    return Standing(league, stars, streak, league)


def test_the_table():
    assert T.TOP == 10 and [T.stars_needed(i) for i in range(1, 10)] == [3, 3, 3, 5, 5, 5, 5, 5, 5]
    assert [T.par(i) for i in range(1, 11)] == [1000 + 100 * i for i in range(10)]
    assert T.par(T.TOP) == ladder.RUNGS[-1][1], "the top league is the Legendary band"


def test_everyone_starts_in_league_1():
    assert Standing() == Standing(1, 0, 0, 1)
    assert T.Tiers(sqlite3.connect(":memory:")).get("someone") == Standing()


def test_a_win_gains_a_star_and_two_from_the_third_in_a_row():
    assert after_game(at(5, 1), True).after == Standing(5, 2, 1, 5)
    ch = after_game(at(5, 0, streak=2), True)
    assert ch.gained == 2 and ch.streak_bonus and ch.after.stars == 2
    assert after_game(ch.after, True).gained == 2, "and every win after it"
    assert after_game(at(9, 0, streak=5), True).gained == 2, "in every league below the top"


def test_moving_up_carries_a_spare_star():
    ch = after_game(at(2, 2), True)
    assert ch.promoted and ch.after.league == 3 and ch.after.stars == 0
    ch = after_game(at(2, 2, streak=2), True)
    assert ch.after.league == 3 and ch.after.stars == 1
    ch = after_game(at(9, 4), True)
    assert ch.after.league == T.TOP and ch.after.stars == 0


def test_a_loss_loses_a_star_and_ends_the_streak():
    ch = after_game(at(5, 3, streak=4), False)
    assert ch.after == Standing(5, 2, 0, 5) and ch.gained == 1
    for league in (2, 3):
        assert after_game(at(league, 2), False).after.stars == 1, "losses cost a star in the low leagues too"


def test_a_loss_at_0_stars_drops_a_league_but_never_out_of_league_1():
    ch = after_game(at(7, 0), False)
    assert ch.demoted and ch.after.league == 6 and ch.after.stars == 4
    ch = after_game(at(4, 0), False)
    assert ch.after.league == 3 and ch.after.stars == 2
    ch = after_game(at(1, 0), False)
    assert ch.after.league == 1 and ch.after.stars == 0 and not ch.demoted


def test_the_top_league_is_kept_and_shows_the_rating():
    ch = after_game(at(T.TOP), False)
    assert ch.after.league == T.TOP
    v = T.view(at(T.TOP), "1987")
    assert v["top"] and v["rating"] == "1987" and "stars" not in v
    assert "stars" in T.view(at(5, 2), "1500") and "rating" not in T.view(at(5, 2), "1500")


def test_each_league_plays_a_band_of_bot_ratings():
    assert T.band(1) == (float("-inf"), 1100) and T.band(5) == (1400, 1500) and T.band(T.TOP) == (1900, float("inf"))
    assert [T.league_of(r) for r in (900, 1000, 1099, 1100, 1550, 1899, 1900, 2400)] == [1, 1, 1, 2, 6, 9, 10, 10]


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
    assert after_game(at(5, 0, streak=2), True).line() == "+2 stars (win streak): League 5, 2 of 5 stars"
    assert after_game(at(5, 0), True).line() == "+1 star: League 5, 1 of 5 stars"
    assert after_game(at(5, 2), False).line() == "-1 star: League 5, 1 of 5 stars"
    assert after_game(at(1, 0), False).line() == "League 1, 0 of 3 stars"
    assert after_game(at(6, 4), True).line() == "Up to League 7, 0 stars"
    assert after_game(at(5, 0), False).line() == "Down to League 4, 4 stars"
    assert after_game(at(9, 4), True).line("2004") == "Up to League 10"
    assert after_game(at(T.TOP), True).line("2011") == "League 10: rating 2011"


def test_the_leaderboard_key():
    assert T.sort_key(at(8, 2), 1500) == 1740
    assert T.sort_key(at(T.TOP), 2033.0) == 2033.0


def test_migration_from_the_rating():
    assert T.from_rating(1820, 50) == Standing(9, 0, 0, 9)
    assert T.from_rating(1500, 50) == Standing(6, 0, 0, 6)
    assert T.from_rating(950, 50) == Standing()
    assert T.from_rating(2400, 50).league == 9, "the top is reached by a win"
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
