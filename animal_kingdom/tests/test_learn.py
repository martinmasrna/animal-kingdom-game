"""Tests for animal_kingdom/learn/: episode generation, TD(lambda) update math, and the
train.py checkpoint/resume CLI plumbing.

Kept fast: no test here runs a real multi-thousand-game training loop (that's the step-4/5
mini-run and rung-0 run, done by hand outside the suite) - these exercise the *machinery*
(determinism, closed-form math, resume identity, a toy convergence sanity check) at a scale
of single-digit-to-low-hundreds of games.
"""

from __future__ import annotations

import math
import os

import pytest

from animal_kingdom.bots import features
from animal_kingdom.decks import PREMADE_DECKS
from animal_kingdom.learn import train as learn_train
from animal_kingdom.learn.episodes import (
    EpisodeSpec,
    Trajectory,
    all_deck_pairs,
    deck_pool,
    ensure_baseline_registered,
    play_episode,
)
from animal_kingdom.learn.td import TDTrainer, TrainConfig
from animal_kingdom.sim import deck_optimizer

N_RUNG0 = len(features.RUNG0_FEATURES)   # 11
FOOD_IDX = features.RUNG0_FEATURES.index("food_progress")


@pytest.fixture(autouse=True)
def restore_deck_registry():
    """Every test here (directly or via play_episode) registers the synthetic 'baseline'
    rig into process-global state (PREMADE_DECKS + $AK_EXTRA_DECKS). Undo it, or
    test_pool.py's PREMADE_DECKS == DECK_SLUGS invariant fails depending on test order (see
    the identical fixture in test_benchmark_set.py)."""
    decks = dict(PREMADE_DECKS)
    synth = dict(deck_optimizer._SYNTHETIC_DECKS)
    env = os.environ.get("AK_EXTRA_DECKS")
    yield
    PREMADE_DECKS.clear()
    PREMADE_DECKS.update(decks)
    deck_optimizer._SYNTHETIC_DECKS.clear()
    deck_optimizer._SYNTHETIC_DECKS.update(synth)
    if env is None:
        os.environ.pop("AK_EXTRA_DECKS", None)
    else:
        os.environ["AK_EXTRA_DECKS"] = env


# --------------------------------------------------------------------- deck pool / pairs

def test_deck_pool_is_seven_premades_plus_baseline():
    pool = deck_pool()
    assert len(pool) == 8
    assert "baseline" in pool


def test_all_deck_pairs_is_36_unordered_pairs_including_mirrors():
    pool = deck_pool()
    index = {d: i for i, d in enumerate(pool)}
    pairs = all_deck_pairs()
    assert len(pairs) == 36
    assert len(set(pairs)) == 36               # no duplicates
    assert all(index[a] <= index[b] for a, b in pairs)   # canonical (unordered) form
    assert sum(1 for a, b in pairs if a == b) == 8   # every deck mirrors itself once


def test_ensure_baseline_registered_makes_baseline_loadable():
    from animal_kingdom.decks import load_premade_deck
    ensure_baseline_registered()
    deck = load_premade_deck("baseline")
    assert len(deck) == 30


# --------------------------------------------------------------------- episode determinism

def _toy_spec(seed=0, anchor_seat=None) -> EpisodeSpec:
    return EpisodeSpec(
        deck_a="cats_midrange", deck_b="ramp", seed=seed, feature_set="rung0",
        weights=tuple(0.0 for _ in range(N_RUNG0)), bias=0.0, epsilon=0.05,
        anchor_seat=anchor_seat,
    )


def test_play_episode_is_deterministic():
    spec = _toy_spec(seed=7)
    a = play_episode(spec)
    b = play_episode(spec)
    assert a == b


def test_play_episode_20_games_deterministic_batch():
    cfg = TrainConfig(feature_set="rung0", batch_size=20, run_seed=123)
    specs_a = learn_train._make_batch_specs(cfg, [0.0] * (N_RUNG0 + 1), iteration=0)
    specs_b = learn_train._make_batch_specs(cfg, [0.0] * (N_RUNG0 + 1), iteration=0)
    assert specs_a == specs_b
    results_a = [play_episode(s) for s in specs_a]
    results_b = [play_episode(s) for s in specs_b]
    assert results_a == results_b


def test_anchor_seat_only_yields_the_other_seats_trajectory():
    spec = _toy_spec(seed=3, anchor_seat="A")
    trajectories = play_episode(spec)
    assert {t.seat for t in trajectories} == {"B"}


def test_no_anchor_yields_both_seats_trajectories():
    spec = _toy_spec(seed=3, anchor_seat=None)
    trajectories = play_episode(spec)
    assert {t.seat for t in trajectories} == {"A", "B"}


def test_trajectory_phis_have_the_right_width_and_outcomes_are_valid():
    spec = _toy_spec(seed=5)
    for traj in play_episode(spec):
        assert traj.outcome in (0.0, 0.5, 1.0)
        for phi in traj.phis:
            assert len(phi) == N_RUNG0


def test_paired_seat_outcomes_are_complementary():
    spec = _toy_spec(seed=9)
    trajectories = {t.seat: t for t in play_episode(spec)}
    if "A" in trajectories and "B" in trajectories:
        assert trajectories["A"].outcome == pytest.approx(1.0 - trajectories["B"].outcome)


# ------------------------------------------------------------------- closed-form TD math

def _sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))


def test_td_update_matches_hand_derived_closed_form_one_step():
    # A single-step trajectory in weight space: phi has 1.0 in the food_progress slot, 0
    # elsewhere; outcome z=1.0. With w0 = 0, P0 = sigmoid(0) = 0.5 exactly, so every quantity
    # in the update is hand-computable without any floating-point surprises.
    cfg = TrainConfig(feature_set="rung0", lam=0.8, alpha=0.1, grad_clip=1e9)
    trainer = TDTrainer(cfg)
    phi = [0.0] * N_RUNG0
    phi[FOOD_IDX] = 1.0
    traj = Trajectory(seat="A", deck="x", opponent_deck="y", seed=0, phis=[phi], outcome=1.0)

    trainer.update([traj])

    p0 = 0.5
    delta0 = 1.0 - p0
    grad_food = p0 * (1 - p0) * 1.0
    grad_bias = p0 * (1 - p0) * 1.0
    expected_food = cfg.alpha * delta0 * grad_food
    expected_bias = cfg.alpha * delta0 * grad_bias

    w = list(trainer.weights)
    assert w[FOOD_IDX] == pytest.approx(expected_food, abs=1e-12)
    assert w[-1] == pytest.approx(expected_bias, abs=1e-12)
    for i, wi in enumerate(w[:-1]):
        if i != FOOD_IDX:
            assert wi == pytest.approx(0.0, abs=1e-12)


def _reference_td_update(w0, traj, lam, alpha, grad_clip):
    """An independent, pure-Python re-derivation of td.py's closed-form update (no numpy),
    used to cross-check TDTrainer.update()'s vectorized implementation."""
    w = list(w0)
    n = len(w)
    preds = [_sigmoid(sum(wi * xi for wi, xi in zip(w, phi + [1.0])))
            for phi in traj.phis]
    targets = preds[1:] + [traj.outcome]
    trace = [0.0] * n
    dw = [0.0] * n
    for t, phi in enumerate(traj.phis):
        x = phi + [1.0]
        grad = [preds[t] * (1 - preds[t]) * xi for xi in x]
        trace = [lam * e + g for e, g in zip(trace, grad)]
        delta = targets[t] - preds[t]
        dw = [d + delta * e for d, e in zip(dw, trace)]
    dw = [d * alpha for d in dw]
    norm = math.sqrt(sum(d * d for d in dw))
    if grad_clip and norm > grad_clip:
        dw = [d * grad_clip / norm for d in dw]
    return [wi + d for wi, d in zip(w, dw)]


@pytest.mark.parametrize("outcome", [0.0, 0.5, 1.0])
@pytest.mark.parametrize("n_steps", [1, 2, 4])
def test_td_update_matches_independent_reference_implementation(outcome, n_steps):
    import random
    rng = random.Random(f"{outcome}-{n_steps}")
    phis = [[rng.uniform(-2, 2) for _ in range(N_RUNG0)] for _ in range(n_steps)]
    w0 = [rng.uniform(-0.5, 0.5) for _ in range(N_RUNG0 + 1)]
    traj = Trajectory(seat="A", deck="x", opponent_deck="y", seed=0, phis=phis, outcome=outcome)

    cfg = TrainConfig(feature_set="rung0", lam=0.8, alpha=0.05, grad_clip=1e9)
    trainer = TDTrainer(cfg)
    trainer.set_weights(w0)
    trainer.update([traj])

    expected = _reference_td_update(w0, traj, cfg.lam, cfg.alpha, cfg.grad_clip)
    for got, exp in zip(trainer.weights, expected):
        assert got == pytest.approx(exp, abs=1e-9)


def test_grad_clip_bounds_the_weight_step_norm():
    cfg = TrainConfig(feature_set="rung0", lam=0.8, alpha=1000.0, grad_clip=0.01)
    trainer = TDTrainer(cfg)
    phi = [1.0] * N_RUNG0
    traj = Trajectory(seat="A", deck="x", opponent_deck="y", seed=0, phis=[phi], outcome=1.0)
    trainer.update([traj])
    norm = math.sqrt(sum(w * w for w in trainer.weights))
    assert norm <= cfg.grad_clip + 1e-9


def test_empty_trajectory_is_skipped_without_error():
    cfg = TrainConfig(feature_set="rung0")
    trainer = TDTrainer(cfg)
    empty = Trajectory(seat="A", deck="x", opponent_deck="y", seed=0, phis=[], outcome=1.0)
    stats = trainer.update([empty])
    assert stats["n_trajectories_used"] == 0
    assert all(w == 0.0 for w in trainer.weights)


# --------------------------------------------------------- toy convergence: learns the sign

def test_learns_food_sign_toy():
    # A supervised-flavoured toy, bypassing real self-play: outcome is a deterministic
    # function of the food_progress feature alone (positive food -> win, negative -> loss);
    # every other feature is pure noise uncorrelated with the outcome. After a modest number
    # of TD passes the food_progress weight must have moved clearly positive while the noise
    # feature weights stay small - i.e. TD actually learns which feature carries the signal.
    import random
    rng = random.Random(0)
    cfg = TrainConfig(feature_set="rung0", lam=0.8, alpha=0.05, grad_clip=5.0)
    trainer = TDTrainer(cfg)

    def toy_trajectory(win: bool):
        food_val = rng.uniform(0.5, 2.0) if win else rng.uniform(-2.0, -0.5)
        phi = [rng.uniform(-0.1, 0.1) for _ in range(N_RUNG0)]
        phi[FOOD_IDX] = food_val
        return Trajectory(seat="A", deck="x", opponent_deck="y", seed=0,
                          phis=[phi], outcome=1.0 if win else 0.0)

    for _ in range(300):
        batch = [toy_trajectory(rng.random() < 0.5) for _ in range(10)]
        trainer.update(batch)

    w = list(trainer.weights)
    assert w[FOOD_IDX] > 0.5, f"expected a clearly positive food_progress weight, got {w[FOOD_IDX]}"
    noise_weights = [abs(w[i]) for i in range(N_RUNG0) if i != FOOD_IDX]
    assert max(noise_weights) < w[FOOD_IDX], "noise features must not outweigh the real signal"


# ------------------------------------------------------------------------ train.py CLI

def test_run_training_2_iterations_completes_and_writes_artifacts(tmp_path):
    cfg = TrainConfig(feature_set="rung0", batch_size=3, total_episodes=6, jobs=1,
                      run_seed=42, arena_every=1000)   # arena_every huge: skip the arena probe here
    out = tmp_path / "run1"
    trainer = learn_train.run_training(cfg, out)
    assert (out / "checkpoint.json").exists()
    assert (out / "curve.csv").exists()
    assert (out / "manifest.json").exists()
    assert len(trainer.weights) == N_RUNG0 + 1


def test_training_moves_weights_away_from_zero_init(tmp_path):
    # A real (small) self-play run through the actual train.py machinery: starting from an
    # all-zero scorecard, weights must move meaningfully - i.e. TD is actually learning
    # something from the games, not silently a no-op. (The stronger "curve trends down"
    # claim is verified on the real 2k-game/jobs=12 mini-run outside the test suite, where
    # sample size is large enough for the trend to be statistically clear rather than noisy.)
    cfg = TrainConfig(feature_set="rung0", batch_size=20, total_episodes=200, jobs=1,
                      run_seed=1, alpha=0.02, arena_every=1000)
    out = tmp_path / "trend"
    trainer = learn_train.run_training(cfg, out)
    norm = float((trainer.weights ** 2).sum() ** 0.5)
    assert norm > 0.05
    import csv as csv_mod
    with (out / "curve.csv").open() as f:
        rows = list(csv_mod.DictReader(f))
    assert len(rows) == 10   # 200 episodes / batch_size 20
    assert all(float(r["mean_abs_delta"]) >= 0.0 for r in rows)


def test_kill_and_resume_is_byte_identical(tmp_path):
    cfg = TrainConfig(feature_set="rung0", batch_size=3, total_episodes=9, jobs=1, run_seed=5,
                      arena_every=1000)

    straight_dir = tmp_path / "straight"
    straight = learn_train.run_training(cfg, straight_dir)

    resumed_dir = tmp_path / "resumed"
    partial_cfg = TrainConfig(**{**cfg.__dict__, "total_episodes": 3})   # 1 of 3 iterations
    learn_train.run_training(partial_cfg, resumed_dir)
    resumed = learn_train.run_training(cfg, resumed_dir)   # "kill" then resume to the full run

    assert list(straight.weights) == pytest.approx(list(resumed.weights), abs=0.0)
    import json as json_mod
    straight_ckpt = json_mod.loads((straight_dir / "checkpoint.json").read_text())
    resumed_ckpt = json_mod.loads((resumed_dir / "checkpoint.json").read_text())
    assert straight_ckpt["weights"] == resumed_ckpt["weights"]
    assert straight_ckpt["iteration"] == resumed_ckpt["iteration"]


def test_resume_rejects_a_mismatched_config(tmp_path):
    cfg = TrainConfig(feature_set="rung0", batch_size=3, total_episodes=3, jobs=1, run_seed=5)
    out = tmp_path / "run"
    learn_train.run_training(cfg, out)

    mismatched = TrainConfig(**{**cfg.__dict__, "alpha": 0.5})
    with pytest.raises(SystemExit):
        learn_train.run_training(mismatched, out)
