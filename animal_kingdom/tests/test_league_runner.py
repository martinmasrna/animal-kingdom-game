"""The league runner's matchmaking (league/runner.py): placing pairings first, the least certain next, opponents near."""

import random

from animal_kingdom.league.runner import PLACING_GAMES, WINDOW, pick


def _players():
    ps = [{"id": f"bot:expert:d{i}", "rating": 1500 + 40 * i, "rd": 60, "games": 50} for i in range(20)]
    ps.append({"id": "bot:expert:new", "rating": 1500, "rd": 350, "games": 0})          # placing
    ps.append({"id": "bot:easy:stale", "rating": 1300, "rd": 140, "games": 30})          # least certain of the settled
    return ps


def test_placing_pairings_play_first_and_stale_ones_next():
    games = pick(_players(), 6, random.Random(1))
    assert [a for a, _ in games[:PLACING_GAMES]] == ["bot:expert:new"] * PLACING_GAMES
    assert games[PLACING_GAMES][0] == "bot:easy:stale"
    assert all(a != b for a, b in games) and len(games) == 6


def test_opponents_come_from_near_the_rating_mostly():
    rng = random.Random(2)
    games = pick(_players(), 400, rng)
    ratings = {p["id"]: p["rating"] for p in _players()}
    near = sum(1 for a, b in games if abs(ratings[a] - ratings[b]) <= WINDOW)
    assert near >= 0.6 * len(games), near   # a fifth are against anyone, the window widens when nobody is near


def test_the_night_window_wraps_midnight():
    from animal_kingdom.league.runner import is_night
    assert [is_night("23-8", h) for h in (22, 23, 0, 7, 8, 12)] == [False, True, True, True, False, False]
    assert [is_night("1-5", h) for h in (0, 1, 4, 5)] == [False, True, True, False] and not is_night("", 3)
