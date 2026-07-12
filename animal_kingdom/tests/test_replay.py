"""The action log round-trips: a logged game replays (bot-free) to the identical outcome."""
from __future__ import annotations

from animal_kingdom.bots.greedy_bot import GreedyBot
from animal_kingdom.sim.runner import play_game
from animal_kingdom.sim import replay


def _logged_game(deck_a="colony_food_swarm", deck_b="ramp", seed=0):
    rec = play_game(deck_a, deck_b, seed, bot_a=GreedyBot(), bot_b=GreedyBot(), log_actions=True)
    return rec, replay.game_log_record(rec, map_id="map_b", bots=("greedy", "greedy"))


def test_log_actions_captures_the_full_game():
    # Seed the bots so the logged and unlogged games are genuinely comparable: an unseeded
    # GreedyBot breaks ties from a fresh RNG, so two plays of the same game can diverge (that is
    # bot nondeterminism, not a logging side effect).
    rec = play_game("cats_midrange", "canine_buff_tempo", 1,
                    bot_a=GreedyBot(seed=0), bot_b=GreedyBot(seed=1), log_actions=True)
    assert rec.actions and all("kind" in a for a in rec.actions)
    # Off by default -> no overhead / empty log.
    quiet = play_game("cats_midrange", "canine_buff_tempo", 1,
                      bot_a=GreedyBot(seed=0), bot_b=GreedyBot(seed=1))
    assert quiet.actions == ()
    assert quiet.winner == rec.winner and quiet.reason == rec.reason  # logging changes nothing


def test_replay_reproduces_the_recorded_outcome():
    rec, log = _logged_game()
    steps, result, _ = replay.replay(log)
    assert result is not None
    assert result.winner == rec.winner
    assert result.reason == rec.reason
    assert len(steps) == len(rec.actions)


def test_replay_is_deterministic():
    _, log = _logged_game(seed=3)
    r1 = replay.replay(log)[1]
    r2 = replay.replay(log)[1]
    assert (r1.winner, r1.reason) == (r2.winner, r2.reason)


def test_replay_reproduces_a_forced_first_player():
    # run_pairs forces first_player independently of the seed's coin flip (see runner.py); the
    # logged record and replay must agree on which player actually moved first.
    rec = play_game("colony_food_swarm", "ramp", 0, bot_a=GreedyBot(), bot_b=GreedyBot(),
                    log_actions=True, first_player="B")
    assert rec.first_player == "B"
    log = replay.game_log_record(rec, map_id="map_b", bots=("greedy", "greedy"))

    _, result, state = replay.replay(log)
    assert state.first_player == "B"
    assert result.winner == rec.winner
    assert result.reason == rec.reason


def test_write_and_load_logs_round_trip(tmp_path):
    recs = [play_game("aggro_hq_rush", "egg_control", s,
                      bot_a=GreedyBot(), bot_b=GreedyBot(), log_actions=True) for s in range(3)]
    path = tmp_path / "games.jsonl"
    n = replay.write_game_logs(recs, str(path), map_id="map_b", bots=("greedy", "greedy"))
    assert n == 3
    loaded = replay.load_logs(str(path))
    assert len(loaded) == 3
    # A loaded log replays to the same winner the live game reported.
    steps, result, _ = replay.replay(loaded[0])
    assert result.winner == recs[0].winner
