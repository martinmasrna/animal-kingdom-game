"""Synthetic tests for the metagame replicator-mutator dynamics simulation."""

from __future__ import annotations

import csv
import json
import time

import pytest

from animal_kingdom.sim.metagame_evolution import (
    build_summary,
    detect_cycle,
    load_matrix,
    main,
    run_simulation,
    step,
)


def _write_matrix_csv(path, decks, cells):
    """cells[a][b] is deck a's win rate vs deck b (a str, blank allowed on the diagonal)."""
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["deck_a \\ deck_b", *decks])
        for a in decks:
            w.writerow([a, *(cells[a][b] for b in decks)])


# --------------------------------------------------------------------------- load_matrix

def test_load_matrix_fills_diagonal_and_parses(tmp_path):
    path = tmp_path / "m.csv"
    _write_matrix_csv(
        path, ["a", "b", "c"],
        {
            "a": {"a": "", "b": "0.6000", "c": "0.7000"},
            "b": {"a": "0.4000", "b": "", "c": "0.5500"},
            "c": {"a": "0.3000", "b": "0.4500", "c": ""},
        },
    )
    decks, matrix = load_matrix(str(path))
    assert decks == ["a", "b", "c"]
    assert matrix[0][0] == matrix[1][1] == matrix[2][2] == 0.5
    assert matrix[0][1] == pytest.approx(0.6)
    assert matrix[1][0] == pytest.approx(0.4)


def test_load_matrix_rejects_broken_complement(tmp_path):
    path = tmp_path / "m.csv"
    _write_matrix_csv(
        path, ["a", "b"],
        {"a": {"a": "", "b": "0.6000"}, "b": {"a": "0.6000", "b": ""}},  # doesn't sum to 1.0
    )
    with pytest.raises(ValueError, match="expected 1.0"):
        load_matrix(str(path))


def test_load_matrix_rejects_non_square(tmp_path):
    path = tmp_path / "m.csv"
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["deck_a \\ deck_b", "a", "b"])
        w.writerow(["a", "", "0.5"])
    with pytest.raises(ValueError, match="not square"):
        load_matrix(str(path))


# --------------------------------------------------------------------------- step / run_simulation

def test_already_at_equilibrium_converges_immediately():
    matrix = [[0.5, 0.5], [0.5, 0.5]]
    result = run_simulation(matrix, mutation_rate=0.0, max_generations=200, debounce=5)
    assert result.stop_reason == "converged"
    assert result.trace[-1] == pytest.approx([0.5, 0.5], abs=1e-9)


def test_strict_dominance_fixates_without_mutation():
    # deck 0 beats deck 1 90% of the time - classic replicator-dynamics fixation of the fitter type.
    matrix = [[0.5, 0.9], [0.1, 0.5]]
    result = run_simulation(matrix, mutation_rate=0.0, max_generations=500)
    shares_a = [row[0] for row in result.trace]
    assert shares_a[-1] > 0.99
    # monotone increase (allow float-level noise)
    assert all(b >= a - 1e-12 for a, b in zip(shares_a, shares_a[1:]))


def test_strict_dominance_bounded_by_mutation_floor():
    matrix = [[0.5, 0.9], [0.1, 0.5]]
    mu = 0.05
    result = run_simulation(matrix, mutation_rate=mu, max_generations=500)
    share_a_final = result.trace[-1][0]
    assert share_a_final < 1.0
    # deck 1's share settles above the raw floor (mu/n) since it still gets a (small) fitness term
    assert result.trace[-1][1] > mu / 2


def test_step_conserves_total_share():
    matrix = [[0.5, 0.6, 0.3], [0.4, 0.5, 0.7], [0.7, 0.3, 0.5]]
    shares = [0.5, 0.3, 0.2]
    updated = step(shares, matrix, mutation_rate=0.01)
    assert sum(updated) == pytest.approx(1.0)


# --------------------------------------------------------------------------- detect_cycle

def test_detect_cycle_finds_the_minimal_period():
    # every snapshot listed here is exactly in-phase with generation 110 (all g % 10 == 0);
    # detect_cycle should report the *smallest* qualifying age (10, from g=100), not a larger
    # multiple of it (e.g. 40, from g=70).
    def state(g):
        phase = g % 10
        return [0.5 + 0.05 * phase, 0.5 - 0.05 * phase]

    snapshots = [(g, state(g)) for g in (70, 80, 90, 100)]
    found = detect_cycle(
        snapshots, generation=110, state=state(110),
        tolerance=1e-9, min_period=5,
    )
    assert found == 10


def test_detect_cycle_returns_none_when_monotone():
    snapshots = [(g, [0.5 + 0.01 * g, 0.5 - 0.01 * g]) for g in range(0, 50, 5)]
    found = detect_cycle(
        snapshots, generation=60, state=[1.0, 0.0],
        tolerance=1e-6, min_period=5,
    )
    assert found is None


# --------------------------------------------------------------------------- invariants / smoke

def test_rps_invariants_and_speed():
    # rock-paper-scissors: 0 beats 1, 1 beats 2, 2 beats 0, each 90/10.
    matrix = [
        [0.5, 0.9, 0.1],
        [0.1, 0.5, 0.9],
        [0.9, 0.1, 0.5],
    ]
    mu = 0.01
    n = len(matrix)
    start = time.monotonic()
    result = run_simulation(matrix, mutation_rate=mu, max_generations=2000)
    elapsed = time.monotonic() - start

    assert elapsed < 1.0
    assert result.stop_reason in {"converged", "cyclic", "budget_exhausted"}
    for shares in result.trace:
        assert sum(shares) == pytest.approx(1.0, abs=1e-6)
        assert all(s >= mu / n - 1e-6 for s in shares)


def test_build_summary_schema():
    matrix = [[0.5, 0.9], [0.1, 0.5]]
    result = run_simulation(matrix, mutation_rate=0.0, max_generations=500)
    summary = build_summary(
        ["a", "b"], matrix, result,
        {"matrix_path": "x.csv", "mutation_rate": 0.0, "max_generations": 500},
    )
    assert summary["decks"] == ["a", "b"]
    assert summary["stop_reason"] == result.stop_reason
    assert set(summary["final_shares"]) == {"a", "b"}
    assert summary["final_shares"]["a"] == pytest.approx(result.trace[-1][0])


# --------------------------------------------------------------------------- CLI

def test_cli_writes_consistent_artifacts(tmp_path):
    matrix_path = tmp_path / "matrix.csv"
    _write_matrix_csv(
        matrix_path, ["a", "b"],
        {"a": {"a": "", "b": "0.6000"}, "b": {"a": "0.4000", "b": ""}},
    )
    out_dir = tmp_path / "out"
    main([
        "--matrix", str(matrix_path),
        "--out", str(out_dir),
        "--max-generations", "50",
    ])

    assert (out_dir / "trace.csv").exists()
    assert (out_dir / "summary.json").exists()

    with open(out_dir / "summary.json") as f:
        summary = json.load(f)
    with open(out_dir / "trace.csv", newline="") as f:
        rows = list(csv.reader(f))

    assert rows[0][1:] == summary["decks"]
    last_row = rows[-1]
    assert float(last_row[1]) == pytest.approx(summary["final_shares"][summary["decks"][0]], abs=1e-5)
    assert float(last_row[2]) == pytest.approx(summary["final_shares"][summary["decks"][1]], abs=1e-5)
