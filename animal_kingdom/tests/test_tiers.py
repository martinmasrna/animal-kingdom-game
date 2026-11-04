"""Ranked leagues (web/tiers.py): one test per rule of the table in docs/ranked-leagues.md."""

import sqlite3

import pytest

from animal_kingdom.web import ladder, tiers as T
from animal_kingdom.web.tiers import Standing, after_game



def at(league, stars=0, floor=None, streak=0):
    return Standing(league, stars, floor if floor is not None else T.floor_of(league), streak, league)


def par(league):   # a rating exactly at a league's par: no rating bonus, not over-ranked, the streak bonus allowed
    return T.par(league)


def test_the_table():
    assert T.TOP == 10 and [T.stars_needed(i) for i in range(1, 10)] == [3, 3, 3, 5, 5, 5, 5, 5, 5]
    assert [T.par(i) for i in range(1, 11)] == [1000 + 100 * i for i in range(10)]
    assert T.FLOORS == (1, 4, 7, 10) and T.par(T.TOP) == ladder.RUNGS[-1][1], "the top league is the Legendary band"


def test_rule_1_everyone_starts_in_league_1():
    assert Standing() == Standing(1, 0, 1, 0, 1)
    assert T.Tiers(sqlite3.connect(":memory:")).get("someone") == Standing()


def test_rule_2_a_win_gains_one_star():
    ch = after_game(at(5, 1), True, par(5))
    assert ch.after.stars == 2 and ch.gained == 1 and not (ch.streak_bonus or ch.rating_bonus)


def test_rule_2_the_third_win_in_a_row_gains_two():
    s = at(5, 0, streak=2)
    ch = after_game(s, True, par(5))
    assert ch.after.stars == 2 and ch.streak_bonus and ch.after.streak == 3
    assert after_game(ch.after, True, par(5)).gained == 2, "and every win after it"


def test_rule_2_no_streak_bonus_above_league_7():
    assert after_game(at(7, 0, streak=5), True, par(7)).gained == 2
    assert after_game(at(8, 0, streak=5), True, par(8)).gained == 1


def test_rule_2_no_streak_bonus_while_the_rating_is_under_the_league():
    assert after_game(at(5, 0, streak=5), True, par(5) - 1).gained == 1


def test_rule_2_the_rating_bonus():
    ch = after_game(at(5, 0), True, par(6))
    assert ch.gained == 2 and ch.rating_bonus and not ch.streak_bonus
    assert after_game(at(5, 0), True, par(6) - 1).gained == 1


def test_rule_2_never_more_than_two_stars():
    ch = after_game(at(5, 0, streak=5), True, 2500)
    assert ch.gained == 2 and ch.after.stars == 2


def test_rule_3_moving_up_with_a_spare_star():
    ch = after_game(at(2, 2), True, par(2))
    assert ch.promoted and (ch.after.league, ch.after.stars) == (3, 0)
    ch = after_game(at(2, 2), True, par(3))     # two stars into a league that needed one more: one carries over
    assert ch.promoted and (ch.after.league, ch.after.stars) == (3, 1)
    assert ch.after.best == 3


def test_rule_3_league_10_has_no_stars():
    ch = after_game(at(9, 4), True, 2500)
    assert ch.promoted and ch.after.league == T.TOP and ch.after.stars == 0
    ch2 = after_game(ch.after, True, 2500)
    assert ch2.after.league == T.TOP and ch2.after.stars == 0 and ch2.gained == 0


def test_rule_4_a_loss_costs_a_star():
    ch = after_game(at(5, 3, streak=4), False, par(5))
    assert ch.after.stars == 2 and ch.gained == 1 and ch.after.streak == 0


@pytest.mark.parametrize("league", [1, 2, 3])
def test_rule_4_no_losses_in_leagues_1_to_3(league):
    ch = after_game(at(league, 2), False, 500)
    assert ch.after.stars == 2 and ch.after.league == league and ch.saved == "low league"


def test_rule_4_over_ranked_a_loss_costs_two():
    assert after_game(at(6, 3), False, par(6) - 101).after.stars == 1
    assert after_game(at(6, 3), False, par(6) - 100).after.stars == 2, "100 under is not yet over-ranked"


def test_rule_5_moving_down():
    ch = after_game(at(6, 0, floor=4), False, par(6))
    assert ch.demoted and (ch.after.league, ch.after.stars) == (5, 4)
    ch = after_game(at(6, 1, floor=4), False, par(6) - 200)   # over-ranked, one star left: it pays one, the next league the other
    assert ch.demoted and (ch.after.league, ch.after.stars) == (5, 4)
    ch = after_game(at(6, 0, floor=4), False, par(6) - 200)
    assert ch.demoted and (ch.after.league, ch.after.stars) == (5, 3)


def test_rule_6_checkpoints_hold():
    for league in (4, 7):
        ch = after_game(at(league, 0), False, 0)
        assert (ch.after.league, ch.after.stars) == (league, 0) and ch.saved == "floor"
    ch = after_game(at(7, 1), False, 0)        # over-ranked at a checkpoint: down to 0, never below
    assert (ch.after.league, ch.after.stars) == (7, 0)
    assert after_game(at(5, 0, floor=4), False, par(5)).after.league == 4


def test_rule_6_reaching_a_checkpoint_keeps_it():
    ch = after_game(at(6, 4, floor=4), True, par(6))
    assert ch.after.league == 7 and ch.after.floor == 7
    down = after_game(after_game(ch.after, False, par(7)).after, False, 0)
    assert down.after.league == 7


def test_rule_7_the_top_league_is_never_left_and_shows_the_rating():
    top = at(T.TOP)
    ch = after_game(top, False, 0)
    assert ch.after.league == T.TOP and ch.saved == "top"
    v = T.view(top, "1987")
    assert v["top"] and v["rating"] == "1987" and "stars" not in v
    assert "stars" in T.view(at(5, 2), "1500") and "rating" not in T.view(at(5, 2), "1500")


def test_rule_8_the_bonuses_read_the_rating_going_in():
    db = sqlite3.connect(":memory:")
    t = T.Tiers(db)
    assert t.result("p", True, 1050).gained == 1            # 1050 < par(2): no bonus
    assert t.result("p", True, 1100).gained == 2            # at par(2): the rating bonus
    assert t.get("p") == Standing(2, 0, 1, 2, 2) and t.games("p") == 2


def test_rule_9_the_end_of_match_line():
    assert after_game(at(5, 0, streak=2), True, par(5)).line() == "+2 stars (win streak): League 5, 2 of 5 stars"
    assert after_game(at(5, 0), True, par(5)).line() == "+1 star: League 5, 1 of 5 stars"
    assert after_game(at(4, 0), False, par(4)).line() == "No star lost (League 4 is a checkpoint): League 4, 0 of 5 stars"
    assert after_game(at(2, 1), False, par(2)).line() == "No star lost (no stars lost in leagues 1 to 3): League 2, 1 of 3 stars"
    assert after_game(at(6, 4, floor=4), True, par(6)).line() == "Up to League 7, 0 stars"
    assert after_game(at(5, 0, floor=4), False, par(5)).line() == "Down to League 4, 4 stars"
    assert after_game(at(6, 3), False, 1300).line() == "-2 stars: League 6, 1 of 5 stars"
    assert after_game(at(9, 4), True, 2000).line("2004") == "Up to League 10"
    assert after_game(at(T.TOP), True, 2000).line("2011") == "League 10: rating 2011"


def test_the_leaderboard_key():
    assert T.sort_key(at(8, 2), 1500) == 1740
    assert T.sort_key(at(T.TOP), 2033.0) == 2033.0


def test_migration_from_the_rating():
    assert T.from_rating(1820, 50) == Standing(7, 0, 7, 0, 7)
    assert T.from_rating(1500, 50) == Standing(4, 0, 4, 0, 4)
    assert T.from_rating(1250, 50) == Standing(1, 0, 1, 0, 1)
    assert T.from_rating(2400, 50).league == 8, "two under the top at most: the top is earned"
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
