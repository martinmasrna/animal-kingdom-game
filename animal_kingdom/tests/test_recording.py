from __future__ import annotations

import json
from pathlib import Path

from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import action_from_dict
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.state import GameState
from animal_kingdom.recording.cohort import generate_manifest
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
    assert manifest["config"]["draw_action_count"] == 1
