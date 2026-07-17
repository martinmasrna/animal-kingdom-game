"""python -m animal_kingdom.learn.train: batched-synchronous self-play TD(lambda) training.

Deterministic: the whole run is a pure function of `TrainConfig` (git rev and
feature_schema_hash ride along in the run-key/manifest for provenance only - neither affects
the computation). Crash-safe: an atomic checkpoint under `--out` lets a killed run resume
exactly where it left off (mirrors `sim/benchmark_set.py`'s run-key checkpoint/resume - a
resumed run whose config/git/schema don't match the checkpoint refuses to continue rather
than silently composing incompatible samples).

Windows: `play_episode` is a module-level function taking a picklable dataclass (see
episodes.py), and this file is `__main__`-guarded, so `ProcessPoolExecutor` is spawn-safe here.

Usage:
    python -m animal_kingdom.learn.train --total-episodes 30000 --jobs 12 \\
        --out results/learn/rung0_v1
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Optional, Sequence

from ..bots import features
from ..bots.greedy_bot import GreedyBot
from ..decks import load_premade_deck
from ..engine import rules
from ..engine.state import new_game
from . import artifacts
from .episodes import EpisodeSpec, all_deck_pairs, ensure_baseline_registered, play_episode
from .td import TDTrainer, TrainConfig

CKPT_VERSION = 1
CURVE_FIELDS_BASE = ("iteration", "episodes", "n_trajectories", "n_trajectories_used",
                    "n_steps", "mean_abs_delta", "logloss", "weight_norm")


# Fields that determine the deterministic weight trajectory a checkpoint encodes. A resumed
# run must match on these, or the accumulated weights don't mean what the new invocation
# thinks they mean. Deliberately EXCLUDED: `total_episodes` (extending how far a run goes is
# a legitimate continue-training operation, not a different run), `jobs` (doesn't affect the
# result - `ex.map` is order-preserving regardless of worker count), and the `arena_*` fields
# (reporting/probe cadence only, never touch `trainer.weights`).
_IDENTITY_FIELDS = ("feature_set", "lam", "alpha", "epsilon", "grad_clip", "run_seed",
                    "batch_size", "anchor_fraction", "map_id", "init_weights")


def _run_key(cfg: TrainConfig) -> dict:
    return {
        "config": {k: getattr(cfg, k) for k in _IDENTITY_FIELDS},
        "git_rev": artifacts.git_rev(),
        "feature_schema_hash": features.schema_hash(cfg.feature_set),
    }


def _write_json_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(tmp, path)   # atomic: a crash mid-write can't corrupt the checkpoint


def _make_batch_specs(cfg: TrainConfig, weights: Sequence[float], iteration: int) -> list[EpisodeSpec]:
    """The deterministic recipe for iteration `iteration`'s batch - a pure function of
    `(cfg, weights, iteration)`, so a resumed run reproduces every later batch exactly."""
    rng = random.Random(cfg.run_seed + iteration)
    pairs = all_deck_pairs()
    weights = list(weights)
    w_features, bias = tuple(weights[:-1]), float(weights[-1])
    specs = []
    for i in range(cfg.batch_size):
        seed = cfg.run_seed + iteration * cfg.batch_size + i
        deck_a, deck_b = rng.choice(pairs)
        anchor_seat = None
        global_index = iteration * cfg.batch_size + i
        if rng.random() < cfg.anchor_fraction:
            anchor_seat = "A" if global_index % 2 == 0 else "B"
        specs.append(EpisodeSpec(
            deck_a=deck_a, deck_b=deck_b, seed=seed, feature_set=cfg.feature_set,
            weights=w_features, bias=bias, map_id=cfg.map_id, epsilon=cfg.epsilon,
            anchor_seat=anchor_seat,
        ))
    return specs


def arena_probe(
    evaluator,
    decks: Sequence[str],
    games_per_deck: int,
    base_seed: int,
) -> dict[str, float]:
    """Learner-piloted GreedyBot vs plain hand-eval GreedyBot, mirror matchup per deck
    (games_per_deck alternates which seat the learner plays). Returns {deck: learner win
    rate}. Deliberately small/serial (this is a training-loop health probe, not a balance
    claim - see docs/balance-eval for the >=200-games standard that applies to real claims)."""
    results: dict[str, float] = {}
    for d_index, deck in enumerate(decks):
        credit = 0.0
        for g in range(games_per_deck):
            seed = base_seed * 1000 + d_index * 1000 + g
            learner_seat, hand_seat = ("A", "B") if g % 2 == 0 else ("B", "A")
            state = new_game(load_premade_deck(deck), load_premade_deck(deck), seed)
            bots = {
                learner_seat: GreedyBot(seed=seed * 2 + 1, evaluator=evaluator),
                hand_seat: GreedyBot(seed=seed * 2 + 2),
            }
            result = rules.is_terminal(state)
            while result is None:
                actor = state.player_to_act()
                legal = rules.legal_actions(state)
                action = bots[actor].choose(state.view_for(actor), legal, state)
                rules.apply_action(state, action)
                result = rules.is_terminal(state)
            if result.winner is None:
                credit += 0.5
            elif result.winner == learner_seat:
                credit += 1.0
        results[deck] = credit / games_per_deck
    return results


def _arena_flat(history: list[dict], decks: Sequence[str], tolerance: float) -> bool:
    """True if the last 3 arena probes' overall mean win rate stayed within `tolerance` of
    each other (the plan's early-stop signal: 'flat arena +/-1.5pt over 3 probes')."""
    if len(history) < 3:
        return False
    means = [sum(h[d] for d in decks) / len(decks) for h in history[-3:]]
    return (max(means) - min(means)) <= tolerance


def run_training(
    cfg: TrainConfig,
    out_dir: Path,
    *,
    progress=None,
) -> TDTrainer:
    ensure_baseline_registered()
    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = out_dir / "checkpoint.json"
    curve_path = out_dir / "curve.csv"
    manifest_path = out_dir / "manifest.json"
    run_key = _run_key(cfg)

    trainer = TDTrainer(cfg)
    start_iteration = 0
    arena_history: list[dict] = []

    if ckpt_path.exists():
        saved = json.loads(ckpt_path.read_text())
        if saved.get("version") != CKPT_VERSION:
            raise SystemExit(
                f"checkpoint {ckpt_path} is version {saved.get('version')!r}, "
                f"this trainer writes v{CKPT_VERSION} - delete it or use a fresh --out"
            )
        if saved.get("run_key") != run_key:
            raise SystemExit(
                f"checkpoint {ckpt_path} is from a different run (config/git_rev/schema_hash "
                "differ from this invocation) - delete it or point --out at a fresh directory"
            )
        trainer.set_weights(saved["weights"])
        start_iteration = saved["iteration"]
        arena_history = saved.get("arena_history", [])
        print(f"resuming {out_dir}: iteration {start_iteration} already done", file=sys.stderr)
    else:
        _write_json_atomic(manifest_path, {"run_key": run_key, "started_unix": time.time()})
        with curve_path.open("w", newline="") as f:
            csv.writer(f).writerow(CURVE_FIELDS_BASE + tuple(f"arena_{d}" for d in cfg.arena_decks))

    n_iterations = math.ceil(cfg.total_episodes / cfg.batch_size)

    def _one_iteration(ex: Optional[ProcessPoolExecutor], iteration: int) -> bool:
        """Runs iteration `iteration`; returns True if the early-stop condition fired."""
        specs = _make_batch_specs(cfg, trainer.weights, iteration)
        batches = (list(ex.map(play_episode, specs)) if ex is not None
                  else [play_episode(s) for s in specs])          # order-preserving either way
        trajectories = [t for batch in batches for t in batch]
        stats = trainer.update(trajectories)                      # sequential updates, in order

        row = {
            "iteration": iteration + 1,
            "episodes": (iteration + 1) * cfg.batch_size,
            **stats,
        }
        arena_row = None
        if (iteration + 1) % cfg.arena_every == 0:
            arena_row = arena_probe(trainer.linear_eval, cfg.arena_decks,
                                    cfg.arena_games_per_deck, cfg.run_seed + iteration)
            arena_history.append(arena_row)
        with curve_path.open("a", newline="") as f:
            csv.writer(f).writerow(
                [row.get(k, "") for k in CURVE_FIELDS_BASE]
                + [f"{arena_row[d]:.4f}" if arena_row else "" for d in cfg.arena_decks]
            )
        _write_json_atomic(ckpt_path, {
            "version": CKPT_VERSION, "run_key": run_key,
            "iteration": iteration + 1,
            "weights": [float(x) for x in trainer.weights],
            "arena_history": arena_history,
        })
        if progress is not None:
            progress(iteration + 1, n_iterations, stats, arena_row)
        if arena_row is not None and _arena_flat(arena_history, cfg.arena_decks, 0.015):
            print(f"early stop at iteration {iteration + 1}: arena flat +/-1.5pt over "
                  "the last 3 probes", file=sys.stderr)
            return True
        return False

    # jobs<=1 skips the pool entirely (mirrors sim/runner.py's run_specs/run_pairs) - faster
    # for small/dev/test runs and avoids Windows process-spawn overhead when it buys nothing.
    if cfg.jobs <= 1:
        for iteration in range(start_iteration, n_iterations):
            if _one_iteration(None, iteration):
                break
    else:
        with ProcessPoolExecutor(max_workers=cfg.jobs) as ex:
            for iteration in range(start_iteration, n_iterations):
                if _one_iteration(ex, iteration):
                    break

    return trainer


def main(argv: Optional[Sequence[str]] = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--feature-set", default="rung0", choices=("rung0", "rung1"))
    p.add_argument("--total-episodes", type=int, default=2_000)
    p.add_argument("--batch-size", type=int, default=500)
    p.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    p.add_argument("--lam", type=float, default=0.8)
    p.add_argument("--alpha", type=float, default=0.01)
    p.add_argument("--epsilon", type=float, default=0.05)
    p.add_argument("--grad-clip", type=float, default=5.0)
    p.add_argument("--anchor-fraction", type=float, default=0.20)
    p.add_argument("--run-seed", type=int, default=0)
    p.add_argument("--map", dest="map_id", default="map_b")
    p.add_argument("--arena-every", type=int, default=10)
    p.add_argument("--arena-games-per-deck", type=int, default=20)
    p.add_argument("--out", type=Path, required=True,
                   help="output directory for checkpoint.json/curve.csv/manifest.json")
    args = p.parse_args(argv)

    cfg = TrainConfig(
        feature_set=args.feature_set, lam=args.lam, alpha=args.alpha, epsilon=args.epsilon,
        grad_clip=args.grad_clip, run_seed=args.run_seed, batch_size=args.batch_size,
        anchor_fraction=args.anchor_fraction, total_episodes=args.total_episodes,
        jobs=args.jobs, map_id=args.map_id, arena_every=args.arena_every,
        arena_games_per_deck=args.arena_games_per_deck,
    )

    start = time.monotonic()

    def _progress(iteration, total, stats, arena_row):
        elapsed = time.monotonic() - start
        msg = (f"\r  [{iteration}/{total}] {elapsed:7.1f}s  "
              f"mean|d|={stats['mean_abs_delta']:.4f}  logloss={stats['logloss']:.4f}  "
              f"||w||={stats['weight_norm']:.3f}")
        if arena_row is not None:
            arena_str = "  ".join(f"{d}={wr:.1%}" for d, wr in arena_row.items())
            msg += f"  arena[{arena_str}]"
        print(msg, file=sys.stderr)

    trainer = run_training(cfg, args.out, progress=_progress)
    print(f"\ndone in {time.monotonic() - start:.1f}s. "
          f"final ||w||={float((trainer.weights ** 2).sum() ** 0.5):.4f}", file=sys.stderr)
    print(f"artifacts: {args.out}/checkpoint.json, curve.csv, manifest.json", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
