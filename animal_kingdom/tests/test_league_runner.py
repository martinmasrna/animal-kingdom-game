"""The league runner's matchmaking (league/runner.py): placing pairings first, the least certain next, opponents near."""

import random

from animal_kingdom.league.runner import PLACING_GAMES, WINDOW, pick, round_robin


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


def test_a_game_the_engine_breaks_is_skipped_not_the_end_of_the_runner(monkeypatch):
    from animal_kingdom.league import runner

    real = runner._run_spec

    def run(spec):
        if spec.seed == 11:
            raise ValueError("list.remove(x): x not in list")
        return real(spec)
    monkeypatch.setattr(runner, "_run_spec", run)
    pilots = {"easy": "greedy"}
    out = runner.play([("bot:easy:cats", "bot:easy:fish")] * 3, pilots, 1, 10, {})
    assert [g["seed"] for g in out] == [10, 12]


def test_round_robin_plays_every_same_level_pairing_twice_and_no_mirror():
    ps = [{"id": f"bot:expert:d{i}", "rating": 1500, "rd": 50, "games": 9} for i in range(4)] + [{"id": "bot:easy:d0", "rating": 1500, "rd": 50, "games": 9}]
    g = round_robin(ps, random.Random(1))
    assert len(g) == 12 and all(a.split(":")[1] == b.split(":")[1] and a != b for a, b in g)
    assert {frozenset(x) for x in g} == {frozenset((f"bot:expert:d{i}", f"bot:expert:d{j}")) for i in range(4) for j in range(i + 1, 4)}


def test_offline_the_games_wait_in_the_outbox_and_go_once_the_server_answers(monkeypatch, tmp_path):
    import json, urllib.error
    from animal_kingdom.league import runner
    out, state = tmp_path / "outbox.jsonl", tmp_path / "state.json"
    out.write_text("".join(json.dumps({"gid": f"g{i}", "a": "x", "b": "y"}) + "\n" for i in range(700)))
    def down(*a, **k): raise urllib.error.URLError("no network")
    monkeypatch.setattr(runner, "api", down)
    assert runner.send_outbox("s", "k", out) == (0, 700) and len(out.read_text().splitlines()) == 700
    assert runner.load_pool("s", "k", state) is None                                   # offline and nothing saved yet
    state.write_text(json.dumps({"players": [{"id": "x", "rating": 1500, "games": 0}, {"id": "y", "rating": 1500, "games": 0}]}))
    pool = runner.load_pool("s", "k", state)
    runner.nudge(pool, [{"a": "x", "b": "y", "winner": "A"}], state)
    assert pool["players"][0]["rating"] > 1500 > pool["players"][1]["rating"] and pool["players"][0]["games"] == 1
    sent = []
    monkeypatch.setattr(runner, "api", lambda s, p, k, body=None, timeout=60: sent.append(len(body["games"])) or {"rated": len(body["games"])})
    assert runner.send_outbox("s", "k", out) == (700, 0) and sent == [300, 300, 100] and out.read_text() == ""


def test_the_round_robin_plays_only_matchups_under_the_target_then_hands_over():
    import random
    from animal_kingdom.league import runner
    players = [{"id": f"bot:expert:{s}", "rating": 1500, "games": 0} for s in ("a", "b", "c")]
    rng = random.Random(1)
    assert len(runner.round_robin_until(players, 50, {}, rng)) == 6
    counts = {"a|b": 50, "a|c": 49}
    assert sorted({runner.pair_key(*g) for g in runner.round_robin_until(players, 50, counts, rng)}) == ["a|c", "b|c"]
    assert runner.round_robin_until(players, 50, {"a|b": 50, "a|c": 50, "b|c": 52}, rng) == []
