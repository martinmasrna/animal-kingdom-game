"""Tests for the Referee v2 convergence and paired-strength harness."""

from __future__ import annotations

import pytest

from animal_kingdom.sim import referee_comparison


class _FakeRecord:
    def __init__(self, winner="A", turns=7):
        self.winner = winner
        self.turns = turns


def _capture_match_bots(monkeypatch, spec):
    """Run _run_referee_match with play_game stubbed; return the (bot_a, bot_b) built."""
    captured = {}

    def fake_play_game(deck_a, deck_b, seed, *, bot_a, bot_b, config, map_id):
        captured["a"], captured["b"] = bot_a, bot_b
        return _FakeRecord()

    monkeypatch.setattr(referee_comparison, "play_game", fake_play_game)
    outcome = referee_comparison._run_referee_match(spec, None)
    return captured, outcome


def test_parse_candidate_config_maps_keys_to_referee_kwargs():
    assert referee_comparison._parse_candidate_config(None) == ()
    assert referee_comparison._parse_candidate_config("") == ()
    parsed = dict(referee_comparison._parse_candidate_config(
        "det=3,root=5,reply=4,nodes=150,beam=8"))
    assert parsed == {
        "determinizations": 3,
        "root_width": 5,
        "reply_width": 4,
        "max_search_nodes": 150,
        "beam_width": 8,
    }


def test_parse_candidate_config_rejects_unknown_key():
    with pytest.raises(SystemExit):
        referee_comparison._parse_candidate_config("bogus=1")


def test_run_referee_match_applies_candidate_and_reference_kwargs(monkeypatch):
    spec = referee_comparison.RefereeMatchSpec(
        deck="ramp", seed=5, candidate_seat="A", map_id="map_b",
        candidate_kwargs=(("max_search_nodes", 150),),
        reference_kwargs=(("max_search_nodes", 1000),),
    )
    captured, (seed, seat, credit, turns) = _capture_match_bots(monkeypatch, spec)
    # candidate is seat A, reference ("legacy") is seat B.
    assert captured["a"].max_search_nodes == 150 and captured["a"].staged is True
    assert captured["b"].max_search_nodes == 1000
    assert (seed, seat, credit, turns) == (5, "A", 1.0, 7)  # winner A == candidate seat


def test_run_referee_match_default_reference_is_uncapped_legacy(monkeypatch):
    # No reference_kwargs => full legacy referee; candidate seat B => reference is seat A.
    spec = referee_comparison.RefereeMatchSpec(
        deck="ramp", seed=5, candidate_seat="B", map_id="map_b")
    captured, _ = _capture_match_bots(monkeypatch, spec)
    assert captured["a"].staged is False and captured["a"].max_search_nodes is None
    assert captured["b"].max_search_nodes == 1000  # candidate = production make_bot referee


def test_position_corpus_is_deterministic_and_covers_requested_decks():
    kwargs = {
        "decks": ["ramp", "egg_control"],
        "turns": [0],
        "base_seed": 12,
        "map_id": "map_b",
    }
    first = referee_comparison.collect_positions(**kwargs)
    second = referee_comparison.collect_positions(**kwargs)

    assert len(first) == 2
    assert [position.label for position in first] == [
        position.label for position in second
    ]
    assert [position.state.to_dict() for position in first] == [
        position.state.to_dict() for position in second
    ]


def test_mirror_comparison_pairs_seats_before_bootstrap(monkeypatch):
    credits = {
        (20, "A"): 1.0,
        (20, "B"): 0.0,
        (21, "A"): 1.0,
        (21, "B"): 1.0,
    }

    def fake_match(spec, config):
        return spec.seed, spec.candidate_seat, credits[(spec.seed, spec.candidate_seat)], 10

    monkeypatch.setattr(referee_comparison, "_run_referee_match", fake_match)
    result = referee_comparison.run_mirror_strength_comparison(
        "ramp",
        paired_seeds=2,
        base_seed=20,
        config=None,
        map_id="map_b",
        jobs=1,
        bootstrap_resamples=20,
    )

    assert result["games"] == 4
    assert result["candidate_win_rate"] == 0.75
    assert result["avg_turns"] == 10
    assert result["outcomes"] == [
        {
            "seed": 20,
            "candidate_seat": "A",
            "candidate_credit": 1.0,
            "turns": 10,
        },
        {
            "seed": 20,
            "candidate_seat": "B",
            "candidate_credit": 0.0,
            "turns": 10,
        },
        {
            "seed": 21,
            "candidate_seat": "A",
            "candidate_credit": 1.0,
            "turns": 10,
        },
        {
            "seed": 21,
            "candidate_seat": "B",
            "candidate_credit": 1.0,
            "turns": 10,
        },
    ]
