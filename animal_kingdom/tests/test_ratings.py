"""Synthetic and design tests for the anchored pilot-strength model."""

from __future__ import annotations

import math
from collections import Counter

import pytest

from animal_kingdom.sim import ratings as ratings_module
from animal_kingdom.sim.ratings import (
    IdentifiabilityError,
    RatingGame,
    build_provenance,
    build_paired_schedule,
    fit_ratings,
    generate_rating_dataset,
    load_dataset,
    run_checkpointed_rating_dataset,
)

PILOT_TRUTH = {
    "random": 0.0,
    "greedy": 0.45,
    "turn": 0.90,
    "referee": 1.10,
}
DECK_TRUTH = {"d0": -0.30, "d1": 0.10, "d2": 0.20}
INTERACTION_TRUTH = {
    "random": {"d0": 0.12, "d1": -0.04, "d2": -0.08},
    "greedy": {"d0": -0.08, "d1": 0.06, "d2": 0.02},
    "turn": {"d0": 0.02, "d1": 0.08, "d2": -0.10},
    "referee": {"d0": -0.06, "d1": -0.10, "d2": 0.16},
}
SEAT_TRUTH = 0.15


def _logistic(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def _synthetic_games(repetitions: int = 80) -> list[RatingGame]:
    """Deterministic stratified outcomes from a known factored model."""
    assert repetitions % 2 == 0
    games = []
    block = 0
    pilots = list(PILOT_TRUTH)
    decks = list(DECK_TRUTH)
    for left_index, pilot_a in enumerate(pilots):
        for pilot_b in pilots[left_index + 1:]:
            for deck_a in decks:
                for deck_b in decks:
                    for repetition in range(repetitions):
                        first_player = "A" if repetition % 2 == 0 else "B"
                        seat = SEAT_TRUTH if first_player == "A" else -SEAT_TRUTH
                        pair_id = f"{block}:{repetition}"
                        # Within each first-player stratum, evenly-spaced quantiles provide
                        # nearly exact binomial proportions without a flaky random fixture.
                        quantile = (
                            (repetition // 2) + 0.5
                        ) / (repetitions // 2)

                        log_odds_a = (
                            PILOT_TRUTH[pilot_a] - PILOT_TRUTH[pilot_b]
                            + DECK_TRUTH[deck_a] - DECK_TRUTH[deck_b]
                            + INTERACTION_TRUTH[pilot_a][deck_a]
                            - INTERACTION_TRUTH[pilot_b][deck_b]
                            + seat
                        )
                        winner_a = "A" if quantile < _logistic(log_odds_a) else "B"
                        games.append(RatingGame(
                            pilot_a, deck_a, pilot_b, deck_b, repetition,
                            first_player, winner_a, pair_id,
                        ))

                        log_odds_b = (
                            PILOT_TRUTH[pilot_b] - PILOT_TRUTH[pilot_a]
                            + DECK_TRUTH[deck_b] - DECK_TRUTH[deck_a]
                            + INTERACTION_TRUTH[pilot_b][deck_b]
                            - INTERACTION_TRUTH[pilot_a][deck_a]
                            + seat
                        )
                        # Rotate the quantile stream for the paired reverse seat so the
                        # fixture is deterministic without making outcomes exact complements.
                        reverse_index = (
                            (repetition // 2) * 17
                        ) % (repetitions // 2)
                        reverse_quantile = (
                            reverse_index + 0.5
                        ) / (repetitions // 2)
                        winner_b = "A" if reverse_quantile < _logistic(log_odds_b) else "B"
                        games.append(RatingGame(
                            pilot_b, deck_b, pilot_a, deck_a, repetition,
                            first_player, winner_b, pair_id,
                        ))
                    block += 1
    return games


@pytest.fixture(scope="module")
def recovered():
    return fit_ratings(
        _synthetic_games(),
        ridge=0.01,
        bootstrap_resamples=30,
        bootstrap_seed=1234,
    )


def test_synthetic_fit_recovers_factored_parameters(recovered):
    for pilot, truth in PILOT_TRUTH.items():
        assert recovered.pilots[pilot].rating == pytest.approx(truth, abs=0.10)
    for deck, truth in DECK_TRUTH.items():
        assert recovered.decks[deck].rating == pytest.approx(truth, abs=0.10)
    for pilot, cells in INTERACTION_TRUTH.items():
        for deck, truth in cells.items():
            assert recovered.interactions[pilot][deck].rating == pytest.approx(
                truth, abs=0.12
            )
    assert recovered.seat_advantage.rating == pytest.approx(SEAT_TRUTH, abs=0.08)


def test_random_anchor_is_exact_and_every_rating_has_an_interval(recovered):
    assert recovered.pilots["random"].rating == 0.0
    assert recovered.pilots["random"].ci_low == 0.0
    assert recovered.pilots["random"].ci_high == 0.0

    estimates = [
        *recovered.pilots.values(),
        *recovered.decks.values(),
        *(
            estimate
            for cells in recovered.interactions.values()
            for estimate in cells.values()
        ),
        recovered.seat_advantage,
    ]
    assert all(math.isfinite(value) for estimate in estimates
               for value in (estimate.rating, estimate.ci_low, estimate.ci_high))
    assert all(estimate.ci_low <= estimate.ci_high for estimate in estimates)


def test_rating_fit_and_paired_bootstrap_are_seed_deterministic():
    games = _synthetic_games(repetitions=20)
    first = fit_ratings(games, ridge=0.01, bootstrap_resamples=10, bootstrap_seed=77)
    second = fit_ratings(games, ridge=0.01, bootstrap_resamples=10, bootstrap_seed=77)
    assert first == second


def test_generated_dataset_is_seed_deterministic_across_job_counts():
    serial = generate_rating_dataset(
        ["random", "greedy"], ["ramp", "egg_control"], 1, 314, jobs=1
    )
    parallel = generate_rating_dataset(
        ["random", "greedy"], ["ramp", "egg_control"], 1, 314, jobs=2
    )
    assert serial == parallel


def test_design_rejects_a_missing_pilot_deck_cell_as_unidentifiable():
    incomplete = [
        game for game in _synthetic_games(repetitions=10)
        if not (
            (game.pilot_a == "turn" and game.deck_a == "d2")
            or (game.pilot_b == "turn" and game.deck_b == "d2")
        )
    ]
    with pytest.raises(IdentifiabilityError, match="matrix rank"):
        fit_ratings(incomplete, bootstrap_resamples=0)


def test_recovered_ladder_has_the_expected_loose_sanity_order(recovered):
    ratings = recovered.pilots
    assert ratings["random"].rating < ratings["greedy"].rating
    assert ratings["greedy"].rating < ratings["turn"].rating
    assert ratings["turn"].rating <= ratings["referee"].rating


def test_schedule_pairs_every_seed_with_complete_competitor_seat_swap():
    specs, metadata = build_paired_schedule(
        ["random", "greedy"],
        ["ramp", "egg_control"],
        games_per_config=3,
        base_seed=100,
    )
    assert len(specs) == 2 * 1 * 2 * 2 * 3
    assert set(Counter(meta[4] for meta in metadata).values()) == {2}
    for index in range(0, len(specs), 2):
        left, right = specs[index:index + 2]
        left_meta, right_meta = metadata[index:index + 2]
        assert left.seed == right.seed
        assert (left.bot_a, left.deck_a, left.bot_b, left.deck_b) == (
            right.bot_b, right.deck_b, right.bot_a, right.deck_a
        )
        assert left_meta[4] == right_meta[4]


def _checkpoint_provenance(games_per_config: int, seed: int) -> dict:
    return build_provenance(
        pilots=["random", "greedy"],
        decks=["ramp", "egg_control"],
        games_per_config=games_per_config,
        base_seed=seed,
        map_id="map_b",
        config=None,
        config_id="none",
    )


def test_interrupted_checkpoint_resumes_to_identical_dataset_and_fit(
    tmp_path, monkeypatch,
):
    path = tmp_path / "dataset.jsonl"
    seed = 901
    games_per_config = 3
    provenance = _checkpoint_provenance(games_per_config, seed)
    real_run_pair = ratings_module.run_spec_pair
    calls = 0

    def interrupt_after_first_checkpoint(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise KeyboardInterrupt
        return real_run_pair(*args, **kwargs)

    monkeypatch.setattr(
        ratings_module, "run_spec_pair", interrupt_after_first_checkpoint
    )
    with pytest.raises(KeyboardInterrupt):
        run_checkpointed_rating_dataset(
            ["random", "greedy"],
            ["ramp", "egg_control"],
            games_per_config,
            seed,
            dataset_path=path,
            provenance=provenance,
            checkpoint_blocks=2,
        )
    saved, saved_provenance = load_dataset(path)
    assert len(saved) == 4
    assert saved_provenance == provenance

    monkeypatch.setattr(ratings_module, "run_spec_pair", real_run_pair)
    resumed = run_checkpointed_rating_dataset(
        ["random", "greedy"],
        ["ramp", "egg_control"],
        games_per_config,
        seed,
        dataset_path=path,
        provenance=provenance,
        checkpoint_blocks=2,
    )
    uninterrupted = generate_rating_dataset(
        ["random", "greedy"],
        ["ramp", "egg_control"],
        games_per_config,
        seed,
    )
    assert resumed == uninterrupted
    assert fit_ratings(
        resumed, bootstrap_resamples=5, bootstrap_seed=10
    ) == fit_ratings(
        uninterrupted, bootstrap_resamples=5, bootstrap_seed=10
    )


def test_resume_rejects_provenance_mismatch_before_running(tmp_path, monkeypatch):
    path = tmp_path / "dataset.jsonl"
    provenance = _checkpoint_provenance(1, 44)
    run_checkpointed_rating_dataset(
        ["random", "greedy"],
        ["ramp", "egg_control"],
        1,
        44,
        dataset_path=path,
        provenance=provenance,
        checkpoint_blocks=2,
    )
    mismatched = dict(provenance)
    mismatched["map"] = "map_a"

    def must_not_run(*args, **kwargs):
        raise AssertionError("simulation ran before provenance validation")

    monkeypatch.setattr(ratings_module, "run_spec_pair", must_not_run)
    with pytest.raises(ValueError, match=r"provenance.*different: map"):
        run_checkpointed_rating_dataset(
            ["random", "greedy"],
            ["ramp", "egg_control"],
            1,
            44,
            dataset_path=path,
            provenance=mismatched,
            checkpoint_blocks=2,
        )


def test_resume_discards_only_a_truncated_final_checkpoint_line(
    tmp_path, monkeypatch,
):
    path = tmp_path / "dataset.jsonl"
    provenance = _checkpoint_provenance(1, 55)
    expected = run_checkpointed_rating_dataset(
        ["random", "greedy"],
        ["ramp", "egg_control"],
        1,
        55,
        dataset_path=path,
        provenance=provenance,
        checkpoint_blocks=2,
    )
    with open(path, "ab") as handle:
        handle.write(b'{"type":"pair","games":[')

    def must_not_run(*args, **kwargs):
        raise AssertionError("completed checkpoint unexpectedly reran games")

    monkeypatch.setattr(ratings_module, "run_spec_pair", must_not_run)
    resumed = run_checkpointed_rating_dataset(
        ["random", "greedy"],
        ["ramp", "egg_control"],
        1,
        55,
        dataset_path=path,
        provenance=provenance,
        checkpoint_blocks=2,
    )
    assert resumed == expected
    assert path.read_bytes().endswith(b"\n")


def test_streaming_parallel_checkpoint_matches_serial(tmp_path):
    provenance = _checkpoint_provenance(1, 66)
    serial = run_checkpointed_rating_dataset(
        ["random", "greedy"],
        ["ramp", "egg_control"],
        1,
        66,
        dataset_path=tmp_path / "serial.jsonl",
        provenance=provenance,
        jobs=1,
        checkpoint_blocks=2,
    )
    parallel = run_checkpointed_rating_dataset(
        ["random", "greedy"],
        ["ramp", "egg_control"],
        1,
        66,
        dataset_path=tmp_path / "parallel.jsonl",
        provenance=provenance,
        jobs=2,
        checkpoint_blocks=2,
    )
    assert parallel == serial


def test_keyboard_interrupt_terminates_worker_pool_immediately(
    tmp_path, monkeypatch,
):
    lifecycle = []

    class InterruptedResults:
        def next(self, timeout):
            raise KeyboardInterrupt

    class FakePool:
        def imap_unordered(self, function, payloads, chunksize):
            return InterruptedResults()

        def terminate(self):
            lifecycle.append("terminate")

        def join(self):
            lifecycle.append("join")

        def close(self):
            lifecycle.append("close")

    class FakeContext:
        def Pool(self, **kwargs):
            return FakePool()

    monkeypatch.setattr(ratings_module, "get_context", lambda: FakeContext())
    provenance = _checkpoint_provenance(1, 77)
    with pytest.raises(KeyboardInterrupt):
        run_checkpointed_rating_dataset(
            ["random", "greedy"],
            ["ramp", "egg_control"],
            1,
            77,
            dataset_path=tmp_path / "interrupted.jsonl",
            provenance=provenance,
            jobs=2,
            checkpoint_blocks=1,
        )
    assert lifecycle == ["terminate", "join"]
