"""Tests for the Referee v2 convergence and paired-strength harness."""

from __future__ import annotations

from animal_kingdom.sim import referee_comparison


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
