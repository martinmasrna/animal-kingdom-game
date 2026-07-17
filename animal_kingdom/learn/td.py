"""Gradient-descent TD(lambda) (TD-Gammon lineage) fit of a LinearEval's weights from
recorded self-play Trajectories.

Model: `P(s) = sigmoid(w . phi(s))` (bias folded in as a trailing always-1 feature), gamma=1
(undiscounted - `TrainConfig` has no gamma field). For a trajectory of non-terminal
afterstates `s_0 .. s_{T-1}` ending in outcome `z`, the *targets* are the next prediction in
the sequence (bootstrapped) with `z` closing it out: `target_t = P(s_{t+1})` for `t < T-1`,
`target_{T-1} = z`. The backward-view eligibility-trace update (mirrors TD-Gammon's original
gradient-descent form, not the "plain phi" trace some other TD(lambda) write-ups use):

    e_{-1} = 0
    for t in 0..T-1:
        e_t     = lambda * e_{t-1} + grad_w P(s_t)      # grad_w P = P(1-P) * phi(s_t) (sigmoid)
        delta_t = target_t - P(s_t)
        w      += alpha * delta_t * e_t

`grad_clip` bounds the L2 norm of one trajectory's total weight step (not each per-step
term) - a single pathological trajectory can't blow up the run.

Numpy-lazy (mirrors `sim/ratings.py`'s `_analysis_imports`): `bots/`/`engine/` stay
stdlib-only; this is the one place in the repo allowed to import numpy, and only inside
function/method bodies, so a core-only install never pays for it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from ..bots import features
from ..bots.learned_eval import LinearEval
from .episodes import Trajectory

_NP_MODULE = None


def _np():
    global _NP_MODULE
    if _NP_MODULE is not None:
        return _NP_MODULE
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover - exercised only in a core-only install
        raise RuntimeError(
            "learned-pilot TD training needs numpy; install with "
            "`python -m pip install -e '.[dev]'` (or `[analysis]`)"
        ) from exc
    _NP_MODULE = np
    return np


@dataclass(frozen=True)
class TrainConfig:
    """Everything the training run's outcome is a pure function of (plus the git rev and
    feature_schema_hash, recorded for provenance only - see learn/train.py's run_key)."""

    feature_set: str = "rung0"
    lam: float = 0.8
    alpha: float = 0.01
    epsilon: float = 0.05
    grad_clip: float = 5.0
    run_seed: int = 0
    batch_size: int = 500
    anchor_fraction: float = 0.20
    total_episodes: int = 2_000
    jobs: int = 12
    map_id: str = "map_b"
    # None -> start from all-zero weights (a completely untrained scorecard, argmax-ties
    # everywhere at iteration 0 - deliberate: rung 0 relearns the hand terms' weights *from
    # experience*, not by warm-starting on the hand-tuned values it's supposed to validate).
    init_weights: Optional[tuple[float, ...]] = None
    arena_every: int = 10
    arena_decks: tuple[str, ...] = ("egg_control", "cats_midrange", "ramp")
    arena_games_per_deck: int = 20


def _param_size(feature_set: str) -> int:
    return len(features.feature_names(feature_set)) + 1   # +1: trailing bias term


class TDTrainer:
    """Owns the live weight vector (numpy, length = features + 1 bias) and applies batches
    of Trajectories to it with gradient-descent TD(lambda)."""

    def __init__(self, config: TrainConfig):
        np = _np()
        self.config = config
        n = _param_size(config.feature_set)
        if config.init_weights is not None:
            init = list(config.init_weights)
            if len(init) != n:
                raise ValueError(
                    f"init_weights must have length {n} (feature_names + bias), got {len(init)}"
                )
            self.weights = np.array(init, dtype=float)
        else:
            self.weights = np.zeros(n, dtype=float)

    @property
    def linear_eval(self) -> LinearEval:
        """A `LinearEval` snapshot of the current weights (safe to hand to a bot/episode -
        it's a plain immutable dataclass, not a view onto `self.weights`)."""
        w = [float(x) for x in self.weights]
        return LinearEval(feature_set=self.config.feature_set, weights=tuple(w[:-1]), bias=w[-1])

    def set_weights(self, values: Sequence[float]) -> None:
        np = _np()
        n = _param_size(self.config.feature_set)
        values = list(values)
        if len(values) != n:
            raise ValueError(f"expected {n} weight values, got {len(values)}")
        self.weights = np.array(values, dtype=float)

    def update(self, trajectories: Sequence[Trajectory]) -> dict:
        """One sequential TD(lambda) pass over a batch of trajectories - mutates
        `self.weights` in place, once per trajectory, in list order. Returns batch
        diagnostics computed from each trajectory's PRE-update predictions (so `logloss`
        measures the snapshot the episodes were actually generated with, not a value already
        nudged by this same batch)."""
        np = _np()
        cfg = self.config
        w = self.weights
        total_abs_delta = 0.0
        total_logloss = 0.0
        n_steps = 0
        n_trajectories_used = 0

        for traj in trajectories:
            if not traj.phis:
                continue
            n_trajectories_used += 1
            x = np.array([[*phi, 1.0] for phi in traj.phis], dtype=float)   # (T, D+1)
            preds = _sigmoid(x @ w, np)                                     # (T,)
            targets = np.concatenate([preds[1:], np.array([traj.outcome])])
            deltas = targets - preds
            grads = (preds * (1.0 - preds))[:, None] * x                    # (T, D+1)

            trace = np.zeros_like(w)
            dw = np.zeros_like(w)
            for t in range(len(preds)):
                trace = cfg.lam * trace + grads[t]
                dw += deltas[t] * trace
            dw *= cfg.alpha
            norm = float(np.linalg.norm(dw))
            if cfg.grad_clip and norm > cfg.grad_clip:
                dw *= cfg.grad_clip / norm
            w += dw

            total_abs_delta += float(np.abs(deltas).sum())
            n_steps += len(preds)
            eps = 1e-9
            clipped = np.clip(preds, eps, 1.0 - eps)
            z = traj.outcome
            total_logloss += float(
                -(z * np.log(clipped) + (1.0 - z) * np.log(1.0 - clipped)).sum()
            )

        return {
            "n_trajectories": len(trajectories),
            "n_trajectories_used": n_trajectories_used,
            "n_steps": n_steps,
            "mean_abs_delta": total_abs_delta / n_steps if n_steps else 0.0,
            "logloss": total_logloss / n_steps if n_steps else 0.0,
            "weight_norm": float(np.linalg.norm(w)),
        }


def _sigmoid(z, np):
    # Numerically stable logistic: avoids overflow in exp(-z) for very negative z and in
    # exp(z) for very positive z (both branches only ever exponentiate a <=0 argument).
    out = np.empty_like(z, dtype=float)
    pos = z >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    neg = ~pos
    ez = np.exp(z[neg])
    out[neg] = ez / (1.0 + ez)
    return out
