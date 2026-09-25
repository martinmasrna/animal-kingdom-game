"""Metagame evolution over a fixed deck-vs-deck matchup matrix (replicator-mutator dynamics).

Pure standard library (csv / json) for the simulation itself — a 7-deck matrix-vector product run
for a couple thousand generations is a few hundred thousand multiply-adds, well below where numpy's
vectorization overhead would pay off. `matplotlib` (analysis extra) is imported lazily, only by
`plot_trace`, so running the simulation never requires it.

Treats each deck as a population share (not a discrete player pool): since matchup outcomes are
fixed expected values rather than simulated win/loss draws, every individual piloting the same deck
is exactly tied with every other individual of that deck, so a "population of players" is fully
described by one share per deck. Fitness of a deck is its expected score against the current
population (mirror matches included, scored 0.5); shares evolve each generation in proportion to
relative fitness (the discrete-time replicator equation), blended with a small uniform mutation
floor so no deck is ever driven to a literal, permanent zero — that floor is what makes "would this
deck reinvade" a well-posed question rather than a foregone conclusion.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

DEFAULT_MATRIX = "results/matrix_referee_round5/matchup_matrix.csv"
DEFAULT_OUT = "results/metagame_evolution"
DEFAULT_MAX_GENERATIONS = 2000
DEFAULT_MUTATION_RATE = 0.002
DEFAULT_EPSILON = 1e-9
DEFAULT_DEBOUNCE = 20
DEFAULT_CYCLE_CHECK_INTERVAL = 1
DEFAULT_CYCLE_BUFFER_SIZE = 200
DEFAULT_CYCLE_TOLERANCE = 1e-3
DEFAULT_CYCLE_MIN_PERIOD = 20

_MEAN_FITNESS_FLOOR = 1e-15

Matrix = list[list[float]]


# --------------------------------------------------------------------------- data loading

def load_matrix(path: str) -> tuple[list[str], Matrix]:
    """Parse a `matchup_matrix.csv` (the format `sim/metrics.py` writes) into a dense matrix.

    The diagonal (mirror matchup) is blank in the CSV and filled to 0.5. Validates the matrix is
    square, every off-diagonal cell parses as a float, and `matrix[i][j] + matrix[j][i] == 1.0`
    (within a small tolerance) for every off-diagonal pair.
    """
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        raise ValueError(f"{path}: empty file")

    header, *body = rows
    decks = header[1:]
    if len(body) != len(decks):
        raise ValueError(
            f"{path}: {len(decks)} deck columns but {len(body)} data rows (not square)"
        )

    n = len(decks)
    matrix: Matrix = [[0.0] * n for _ in range(n)]
    for i, row in enumerate(body):
        if row[0] != decks[i]:
            raise ValueError(
                f"{path}: row {i} label {row[0]!r} does not match column order {decks[i]!r}"
            )
        cells = row[1:]
        if len(cells) != n:
            raise ValueError(f"{path}: row {row[0]!r} has {len(cells)} cells, expected {n}")
        for j, cell in enumerate(cells):
            if i == j:
                matrix[i][j] = 0.5
                continue
            if not cell:
                raise ValueError(f"{path}: missing off-diagonal cell [{decks[i]}][{decks[j]}]")
            matrix[i][j] = float(cell)

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            total = matrix[i][j] + matrix[j][i]
            if abs(total - 1.0) > 1e-6:
                raise ValueError(
                    f"{path}: [{decks[i]}][{decks[j]}] + [{decks[j]}][{decks[i]}] "
                    f"= {total!r}, expected 1.0 (not a valid complementary win-rate matrix)"
                )

    return decks, matrix


# --------------------------------------------------------------------------- dynamics

def step(shares: Sequence[float], matrix: Matrix, mutation_rate: float) -> list[float]:
    """One discrete replicator-mutator generation update.

    fitness_i = sum_j shares[j] * matrix[i][j] (an individual of type i facing an opponent sampled
    proportional to current population shares, mirror matches included). Shares scale by relative
    fitness (the replicator step), then blend toward the uniform distribution by `mutation_rate` -
    the reintroduction floor that keeps every deck's share bounded away from exactly zero. Result
    is renormalized to sum to 1 as a defense against float drift over many generations.
    """
    n = len(shares)
    fitness = [sum(shares[j] * matrix[i][j] for j in range(n)) for i in range(n)]
    mean_fitness = sum(shares[i] * fitness[i] for i in range(n))
    mean_fitness = max(mean_fitness, _MEAN_FITNESS_FLOOR)

    uniform = 1.0 / n
    updated = [
        (1.0 - mutation_rate) * (shares[i] * fitness[i] / mean_fitness) + mutation_rate * uniform
        for i in range(n)
    ]
    total = sum(updated)
    return [x / total for x in updated]


def detect_cycle(
    snapshots: Sequence[tuple[int, Sequence[float]]],
    generation: int,
    state: Sequence[float],
    *,
    tolerance: float,
    min_period: int,
) -> Optional[int]:
    """Scan `snapshots` (older (generation, state) pairs) for one that `state` has returned close
    to. Searches most-recent-first so the *smallest* qualifying age is returned - the minimal
    period consistent with the data, not just some larger multiple of it. Returns the estimated
    period (generation - snapshot_generation), or None if no snapshot within `tolerance` is at
    least `min_period` generations old.
    """
    for snap_generation, snap_state in reversed(snapshots):
        age = generation - snap_generation
        if age < min_period:
            continue
        max_delta = max(abs(a - b) for a, b in zip(state, snap_state))
        if max_delta <= tolerance:
            return age
    return None


@dataclass
class SimulationResult:
    trace: list[list[float]] = field(repr=False)
    stop_reason: str
    generations_run: int
    stop_detail: dict


def run_simulation(
    matrix: Matrix,
    *,
    mutation_rate: float = DEFAULT_MUTATION_RATE,
    max_generations: int = DEFAULT_MAX_GENERATIONS,
    epsilon: float = DEFAULT_EPSILON,
    debounce: int = DEFAULT_DEBOUNCE,
    cycle_check_interval: int = DEFAULT_CYCLE_CHECK_INTERVAL,
    cycle_buffer_size: int = DEFAULT_CYCLE_BUFFER_SIZE,
    cycle_tolerance: float = DEFAULT_CYCLE_TOLERANCE,
    cycle_min_period: int = DEFAULT_CYCLE_MIN_PERIOD,
) -> SimulationResult:
    n = len(matrix)
    shares = [1.0 / n] * n
    trace: list[list[float]] = [list(shares)]
    snapshots: deque[tuple[int, list[float]]] = deque(maxlen=cycle_buffer_size)

    stable_run = 0
    for generation in range(1, max_generations + 1):
        new_shares = step(shares, matrix, mutation_rate)
        max_delta = max(abs(a - b) for a, b in zip(new_shares, shares))
        shares = new_shares
        trace.append(list(shares))

        if max_delta < epsilon:
            stable_run += 1
            if stable_run >= debounce:
                return SimulationResult(
                    trace=trace, stop_reason="converged",
                    generations_run=generation,
                    stop_detail={
                        "stable_since_generation": generation - debounce + 1,
                        "debounce_window": debounce,
                        "max_delta": max_delta,
                    },
                )
        else:
            stable_run = 0

        if generation % cycle_check_interval == 0:
            period = detect_cycle(
                snapshots, generation, shares,
                tolerance=cycle_tolerance, min_period=cycle_min_period,
            )
            if period is not None:
                return SimulationResult(
                    trace=trace, stop_reason="cyclic",
                    generations_run=generation,
                    stop_detail={
                        "estimated_period": period,
                        "reference_generation": generation - period,
                        "cycle_tolerance": cycle_tolerance,
                    },
                )
            snapshots.append((generation, list(shares)))

    return SimulationResult(
        trace=trace, stop_reason="budget_exhausted",
        generations_run=max_generations, stop_detail={},
    )


# --------------------------------------------------------------------------- output

def write_trace_csv(path: Path, decks: Sequence[str], trace: Sequence[Sequence[float]]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["generation", *decks])
        for generation, shares in enumerate(trace):
            w.writerow([generation, *(f"{s:.6f}" for s in shares)])


def build_summary(
    decks: Sequence[str],
    matrix: Matrix,
    result: SimulationResult,
    params: dict,
) -> dict:
    initial = result.trace[0]
    final = result.trace[-1]
    n = len(decks)
    final_fitness = [sum(final[j] * matrix[i][j] for j in range(n)) for i in range(n)]
    return {
        "schema_version": 1,
        "decks": list(decks),
        "matrix_path": params["matrix_path"],
        "matrix": matrix,
        "parameters": {k: v for k, v in params.items() if k != "matrix_path"},
        "initial_shares": dict(zip(decks, initial)),
        "final_shares": dict(zip(decks, final)),
        "fitness_at_final": dict(zip(decks, final_fitness)),
        "generations_run": result.generations_run,
        "stop_reason": result.stop_reason,
        "stop_detail": result.stop_detail,
    }


def plot_trace(decks: Sequence[str], trace: Sequence[Sequence[float]], path: Path) -> None:
    """Line chart of population share per deck over generations. Lazy matplotlib import so the
    simulation itself never requires the `analysis` extra."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    generations = list(range(len(trace)))
    fig, ax = plt.subplots(figsize=(10, 6))
    for i, deck in enumerate(decks):
        ax.plot(generations, [row[i] for row in trace], label=deck, linewidth=1.5)
    ax.set_xlabel("Generation")
    ax.set_ylabel("Population share")
    ax.set_ylim(0, 1)
    ax.set_title("Metagame evolution (replicator-mutator dynamics)")
    ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0), fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# --------------------------------------------------------------------------- CLI

def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Simulate metagame evolution over a deck matchup matrix via replicator-"
                    "mutator dynamics (no game re-simulation - pure math over the matrix)."
    )
    parser.add_argument("--matrix", default=DEFAULT_MATRIX, help="matchup_matrix.csv path")
    parser.add_argument("--out", default=DEFAULT_OUT, help="artifact directory")
    parser.add_argument("--max-generations", type=int, default=DEFAULT_MAX_GENERATIONS)
    parser.add_argument("--mutation-rate", type=float, default=DEFAULT_MUTATION_RATE)
    parser.add_argument("--epsilon", type=float, default=DEFAULT_EPSILON)
    parser.add_argument("--debounce", type=int, default=DEFAULT_DEBOUNCE)
    parser.add_argument("--cycle-check-interval", type=int, default=DEFAULT_CYCLE_CHECK_INTERVAL)
    parser.add_argument("--cycle-buffer-size", type=int, default=DEFAULT_CYCLE_BUFFER_SIZE)
    parser.add_argument("--cycle-tolerance", type=float, default=DEFAULT_CYCLE_TOLERANCE)
    parser.add_argument("--cycle-min-period", type=int, default=DEFAULT_CYCLE_MIN_PERIOD)
    parser.add_argument("--plot", action="store_true",
                        help="also render trace.png (requires the analysis extra)")
    args = parser.parse_args(argv)

    start = time.monotonic()
    decks, matrix = load_matrix(args.matrix)
    print(
        f"Loaded {len(decks)}-deck matrix from {args.matrix}. "
        f"Running replicator dynamics: mu={args.mutation_rate}, "
        f"max_generations={args.max_generations}...",
        file=sys.stderr,
    )

    result = run_simulation(
        matrix,
        mutation_rate=args.mutation_rate,
        max_generations=args.max_generations,
        epsilon=args.epsilon,
        debounce=args.debounce,
        cycle_check_interval=args.cycle_check_interval,
        cycle_buffer_size=args.cycle_buffer_size,
        cycle_tolerance=args.cycle_tolerance,
        cycle_min_period=args.cycle_min_period,
    )

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_trace_csv(out_dir / "trace.csv", decks, result.trace)

    params = {
        "matrix_path": args.matrix,
        "mutation_rate": args.mutation_rate,
        "max_generations": args.max_generations,
        "epsilon": args.epsilon,
        "debounce": args.debounce,
        "cycle_check_interval": args.cycle_check_interval,
        "cycle_buffer_size": args.cycle_buffer_size,
        "cycle_tolerance": args.cycle_tolerance,
        "cycle_min_period": args.cycle_min_period,
    }
    summary = build_summary(decks, matrix, result, params)
    with open(out_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)

    if args.plot:
        plot_trace(decks, result.trace, out_dir / "trace.png")

    print(
        f"Stopped after {result.generations_run} generations: {result.stop_reason}.",
        file=sys.stderr,
    )
    print(
        f"Artifacts written to {out_dir}/ in {time.monotonic() - start:.2f}s.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main(sys.argv[1:])
