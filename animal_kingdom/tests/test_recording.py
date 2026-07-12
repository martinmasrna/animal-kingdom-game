from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import action_from_dict
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.state import GameState
from animal_kingdom.recording.cohort import config_drift, generate_manifest
from animal_kingdom.recording.session import GameSetup, RecorderSession
from animal_kingdom.recording.schedule import main as schedule_main
from animal_kingdom.recording.writer import (
    JsonlGameWriter,
    completed_game_ids,
    recover_records,
)


def test_schedule_is_deterministic_paired_and_unique():
    kwargs = dict(
        cohort_id="human-v1",
        human_decks=("ramp", "egg_control"),
        opponent_decks=("cats_midrange",),
        opponent_kinds=("random", "greedy"),
        repetitions=2,
        seats=("A", "B"),
        base_seed=100,
        schedule_seed=7,
        map_id="map_b",
        config=Config(),
    )
    left = generate_manifest(**kwargs)
    right = generate_manifest(**kwargs)
    assert left.to_dict() == right.to_dict()
    assert len(left.games) == 16
    assert len({game.game_id for game in left.games}) == len(left.games)
    paired = {}
    for game in left.games:
        key = (game.human_deck, game.opponent_deck, game.opponent_kind, game.seed)
        paired.setdefault(key, set()).add(game.human_seat)
    assert all(seats == {"A", "B"} for seats in paired.values())


def test_exclude_mirrors_drops_deck_vs_itself():
    kwargs = dict(
        cohort_id="human-v1",
        human_decks=("ramp", "egg_control", "cats_midrange"),
        opponent_decks=("ramp", "egg_control", "cats_midrange"),
        opponent_kinds=("greedy",),
        repetitions=1,
        seats=("A", "B"),
        base_seed=0,
        schedule_seed=0,
        map_id="map_b",
        config=Config(),
    )
    full = generate_manifest(**kwargs)
    trimmed = generate_manifest(**kwargs, exclude_mirrors=True)
    # 3x3 pairs x 2 seats = 18; excluding 3 mirrors x 2 seats = 12.
    assert len(full.games) == 18
    assert len(trimmed.games) == 12
    assert all(g.human_deck != g.opponent_deck for g in trimmed.games)
    assert trimmed.generation["exclude_mirrors"] is True


def test_writer_recovers_truncated_tail_and_tracks_latest_validity(tmp_path):
    path = tmp_path / "game.jsonl"
    with JsonlGameWriter(path) as writer:
        writer.append({"type": "meta", "scheduled_game_id": "g1"})
        writer.append({"type": "result", "game_valid": True})
        writer.append({"type": "annotation", "annotation": "game_validity", "valid": False})
    with open(path, "ab") as handle:
        handle.write(b'{"type":"partial"')

    records = recover_records(path)
    assert len(records) == 3
    assert completed_game_ids([path]) == set()

    with JsonlGameWriter(path) as writer:
        writer.append({"type": "annotation", "annotation": "game_validity", "valid": True})
    assert completed_game_ids([path]) == {"g1"}


def test_generate_manifest_grouped_keeps_matchups_consecutive():
    from animal_kingdom.recording.cohort import generate_manifest
    from animal_kingdom.engine.config import Config

    m = generate_manifest(
        cohort_id="c", human_decks=["food_otk"],
        opponent_decks=["ramp", "cats_midrange"], opponent_kinds=["greedy"],
        repetitions=3, seats=("A", "B"), base_seed=0, schedule_seed=0,
        map_id="map_b", config=Config.default(), shuffle=False)
    # 3 reps x 2 seats = 6 games per opponent, all of one matchup before the next.
    assert [g.opponent_deck for g in m.games] == ["ramp"] * 6 + ["cats_midrange"] * 6


def test_summarize_cohort_tallies_human_record(tmp_path):
    from animal_kingdom.recording.writer import summarize_cohort

    def game(name, sid, human_seat, opp_deck, winner, valid=True):
        opp_seat = "B" if human_seat == "A" else "A"
        with JsonlGameWriter(tmp_path / name) as w:
            w.append({"type": "meta", "scheduled_game_id": sid, "human_seat": human_seat,
                      "decks": {human_seat: "food_otk", opp_seat: opp_deck}})
            w.append({"type": "result", "winner": winner, "game_valid": valid})

    game("g1.jsonl", "g1", "A", "ramp", "A")                       # human (A) wins
    game("g2.jsonl", "g2", "B", "ramp", "A")                       # human (B) loses
    game("g3.jsonl", "g3", "A", "cats_midrange", None)             # draw
    game("g4.jsonl", "g4", "A", "ramp", "B", valid=False)         # excluded -> ignored

    prog = summarize_cohort(sorted(tmp_path.glob("*.jsonl")))
    assert (prog.win, prog.loss, prog.draw) == (1, 1, 1)
    assert prog.completed_ids == {"g1", "g2", "g3"}
    assert prog.per_opponent["ramp"] == [1, 1, 0]
    assert prog.per_opponent["cats_midrange"] == [0, 0, 1]
    assert prog.win_pct == 50.0                                    # 1 win / 2 decided


def test_session_records_replayable_decisions_and_hidden_view(tmp_path):
    config = Config().sweep(max_turns=20)
    setup = GameSetup(
        "ramp",
        "egg_control",
        human_seat="A",
        opponent_kind="random",
        seed=5,
        map_id="map_a",
        config=config,
        cohort_id="test",
        scheduled_game_id="game-1",
    )
    session = RecorderSession(setup, output_root=tmp_path)
    while session.result is None:
        if session.human_turn:
            session.submit_human_action(session.legal_actions[0])
        else:
            action, elapsed = session.choose_bot_action()
            session.submit_bot_action(action, elapsed)
    final = session.state.to_dict()
    session.toggle_latest_human_decision()
    session.close()

    records = recover_records(session.path)
    meta = records[0]
    decisions = [row for row in records if row["type"] == "decision"]
    assert meta["type"] == "meta"
    assert {row["controller"] for row in decisions} == {"human", "random"}
    assert all("opponent_hand_count" in row["view"] for row in decisions)
    assert all("opponent_hand" not in row["view"] for row in decisions)
    assert all("board_units" in row["view"] for row in decisions)
    assert all("own_hand_units" in row["view"] for row in decisions)
    assert all(
        unit["owner"] == row["actor"]
        for row in decisions
        for unit in row["view"]["own_hand_units"]
    )
    assert any(row["type"] == "result" for row in records)
    assert any(
        row.get("annotation") == "decision_validity" and not row["valid"]
        for row in records
    )

    replay = GameState.from_dict(meta["initial_state"], config=config)
    for row in decisions:
        assert action_from_dict(row["action"]) in rules.legal_actions(replay)
        rules.apply_action(replay, action_from_dict(row["action"]))
    rules.is_terminal(replay)
    assert replay.to_dict() == final


def test_state_view_to_dict_is_json_safe(tmp_path):
    setup = GameSetup("ramp", "egg_control", opponent_kind="random", seed=1, map_id="map_a")
    session = RecorderSession(setup, output_root=tmp_path)
    payload = session.state.view_for(setup.human_seat).to_dict()
    json.dumps(payload)
    assert "own_hand" in payload
    assert "opponent_hand_count" in payload
    assert "decks" not in payload
    session.close()


def test_schedule_cli_uses_shipped_config_without_retired_preset(tmp_path):
    output = tmp_path / "cohort.json"
    schedule_main([
        "--id", "default-config",
        "--out", str(output),
        "--human-decks", "ramp",
        "--opponent-decks", "egg_control",
        "--bots", "random",
        "--seats", "A",
    ])
    manifest = json.loads(output.read_text())
    assert manifest["config"]["actions_per_turn"] == 2
    assert manifest["config"]["draw_action_count"] == 2


def test_config_drift_flags_stale_pinned_constants():
    """A schedule pins config at generation; if a balance constant later changes in code, the
    drift check must surface exactly the stale keys (guards the flying_squirrel 8-vs-10 incident)."""
    # A schedule generated from the current defaults has no drift.
    assert config_drift(Config.default()) == []

    # Pin two constants at stale values; only those should be reported, with (name, pinned, current).
    default = Config.default()
    stale = dataclasses.replace(
        default,
        flying_squirrel_food=default.flying_squirrel_food - 2,
        groundhog_food=default.groundhog_food - 3,
    )
    drift = dict((name, (pinned, current)) for name, pinned, current in config_drift(stale))
    assert drift == {
        "flying_squirrel_food": (default.flying_squirrel_food - 2, default.flying_squirrel_food),
        "groundhog_food": (default.groundhog_food - 3, default.groundhog_food),
    }
