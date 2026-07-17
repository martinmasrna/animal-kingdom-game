"""LinearEval: the rung-0/rung-1 learned evaluator - `value()`, `win_prob()`, artifact I/O.

Architecture: `value(state, me) = bias + weights . features.extract(state, me, feature_set)`
- the "raw logit" the design calls for (argmax-invariant magnitude). The terminal contract is
exactly `evaluate()`'s: +/-inf for a decisive win/loss, 0.0 for a draw - so the search's
`_DECISIVE` clamping and determinized-worlds averaging (turn_search.py) keep working
unchanged whether the eval is hand-written or learned. `win_prob()` applies the logistic link
only for training/reporting; action selection always compares raw `value()`s.

Weight artifacts are tracked JSON, conventionally under `data/learned/<name>.json`:
`{feature_set, feature_schema_hash, weights, bias, provenance}`. `feature_schema_hash` is
validated against `features.schema_hash(feature_set)` on load - a stale artifact (trained
against a `features.py` that has since changed meaning) fails loudly instead of silently
scoring with the wrong feature semantics.

Stdlib only (repo invariant: `bots/` stays stdlib-only; training's numpy lives behind the
lazy-import seam in `animal_kingdom/learn/`, never here).
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Mapping, Optional

from ..engine.resources import load_bundled_json
from ..engine.state import GameState, other_player
from . import features


@dataclass(frozen=True)
class LinearEval:
    """A linear scorecard over `features.extract(state, me, feature_set)`."""

    feature_set: str
    weights: tuple[float, ...]
    bias: float = 0.0
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        expected = len(features.feature_names(self.feature_set))
        if len(self.weights) != expected:
            raise ValueError(
                f"LinearEval(feature_set={self.feature_set!r}) expects {expected} weights "
                f"(one per feature_names()), got {len(self.weights)}"
            )

    # ------------------------------------------------------------------- scoring
    def value(self, state: GameState, me: str) -> float:
        """Raw logit from `me`'s perspective. Terminal contract identical to `evaluate()`:
        +inf (me wins) / -inf (me loses) / 0.0 (draw) - never runs `features.extract` on a
        terminal state (which forbids it)."""
        opp = other_player(me)
        if state.result is not None:
            if state.result.winner == me:
                return math.inf
            if state.result.winner == opp:
                return -math.inf
            return 0.0
        phi = features.extract(state, me, self.feature_set)
        return self.bias + sum(w * x for w, x in zip(self.weights, phi))

    def win_prob(self, state: GameState, me: str) -> float:
        """Sigmoid(value) - training/reporting only, never used for action selection.
        Terminal states map to the literal outcome (1.0 / 0.0 / 0.5), sidestepping inf math."""
        if state.result is not None:
            opp = other_player(me)
            if state.result.winner == me:
                return 1.0
            if state.result.winner == opp:
                return 0.0
            return 0.5
        v = self.value(state, me)
        return 1.0 / (1.0 + math.exp(-v))

    # ---------------------------------------------------------------- artifact I/O
    def to_dict(self) -> dict:
        return {
            "feature_set": self.feature_set,
            "feature_schema_hash": features.schema_hash(self.feature_set),
            "weights": list(self.weights),
            "bias": self.bias,
            "provenance": dict(self.provenance),
        }

    @staticmethod
    def from_dict(d: dict) -> "LinearEval":
        feature_set = d["feature_set"]
        expected_hash = features.schema_hash(feature_set)
        got_hash = d.get("feature_schema_hash")
        if got_hash != expected_hash:
            raise ValueError(
                f"stale weight artifact: feature_set {feature_set!r} schema hash "
                f"{got_hash!r} does not match the current schema_hash() "
                f"{expected_hash!r} - features.py has changed since this artifact was "
                "trained (retrain, or pin the features.py revision it was trained against)"
            )
        return LinearEval(
            feature_set=feature_set,
            weights=tuple(float(w) for w in d["weights"]),
            bias=float(d.get("bias", 0.0)),
            provenance=dict(d.get("provenance", {})),
        )

    @staticmethod
    def from_file(path: str) -> "LinearEval":
        with open(path, "r", encoding="utf-8") as f:
            return LinearEval.from_dict(json.load(f))

    def save(self, path: str) -> None:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    # -------------------------------------------------------------- hand-mimic construction
    @staticmethod
    def hand_mimic(weights: Optional[Any] = None) -> "LinearEval":
        """A rung-0 LinearEval whose weights are read straight off `GreedyWeights`, so its
        `value()` reproduces `evaluate()` to numerical precision (the equivalence test this
        session's step 2 gates on). `weights` defaults to `GreedyWeights()`; the feature order
        must match `features.RUNG0_FEATURES` exactly.
        """
        from .greedy_bot import GreedyWeights  # local: avoid a bots-module import cycle

        w = weights or GreedyWeights()
        ordered = (
            w.food_progress, w.food_proximity, w.board_presence, w.connection,
            w.region_control, w.enemy_hq_threat, w.own_hq_threat, w.coverage_exposure,
            w.card_economy, w.effect_readiness, w.pending_payoff,
        )
        assert len(ordered) == len(features.RUNG0_FEATURES)
        return LinearEval(feature_set="rung0", weights=ordered, bias=0.0,
                          provenance={"kind": "hand_mimic"})


@lru_cache(maxsize=None)
def load_eval(name_or_path: str) -> LinearEval:
    """Resolve `name_or_path` to a `LinearEval`.

    A string containing a path separator, or one that names an existing file, is a literal
    filesystem path. Otherwise it's a bare name resolved against the bundled
    `data/learned/<name>.json` package data (see `pyproject.toml`'s package-data entry).
    Cached: sim workers passing the same `eval=` name only parse/validate the JSON once per
    process (each ProcessPoolExecutor worker gets its own cache - ok, this is a read-only
    lookup, not shared mutable state).
    """
    if os.sep in name_or_path or "/" in name_or_path or os.path.isfile(name_or_path):
        return LinearEval.from_file(name_or_path)
    raw = load_bundled_json(f"learned/{name_or_path}.json")
    return LinearEval.from_dict(raw)
