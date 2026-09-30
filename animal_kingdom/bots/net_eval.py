"""NetEval: a small learned value network over `features.extract` - the nonlinear sibling of
`LinearEval`, used by the search through the same `evaluator=` seam.

`value(state, me) = scale * (w2 . relu(W1 . z + b1) + b2)` with `z` the standardized feature
vector. The inner expression is a win logit (trained on game outcomes, `learn/net.py`); `scale`
converts it to hand-eval points so the search's point-valued penalties (a wasted Roar) keep
their size. Terminal contract identical to `evaluate()`: +/-inf for a decisive result, 0.0 for
a draw.

Stdlib only (repo invariant: `bots/` stays stdlib-only; numpy lives in `learn/`). The forward
pass is a few hundred multiplications, cheap next to the feature extraction it sits on.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any, Mapping

from ..engine.state import GameState, other_player
from . import features


@dataclass(frozen=True)
class NetEval:
    feature_set: str
    mean: tuple[float, ...]
    std: tuple[float, ...]
    w1: tuple[tuple[float, ...], ...]     # hidden x inputs
    b1: tuple[float, ...]
    w2: tuple[float, ...]
    b2: float
    scale: float = 1.0
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def logit(self, state: GameState, me: str) -> float:
        phi = features.extract(state, me, self.feature_set)
        z = [(x - m) / s for x, m, s in zip(phi, self.mean, self.std)]
        out = self.b2
        for row, b, w in zip(self.w1, self.b1, self.w2):
            h = b + sum(a * x for a, x in zip(row, z))
            if h > 0:
                out += w * h
        return out

    def value(self, state: GameState, me: str) -> float:
        if state.result is not None:
            if state.result.winner == me:
                return math.inf
            if state.result.winner == other_player(me):
                return -math.inf
            return 0.0
        return self.scale * self.logit(state, me)

    def to_dict(self) -> dict:
        return {
            "kind": "mlp", "feature_set": self.feature_set,
            "feature_schema_hash": features.schema_hash(self.feature_set),
            "mean": list(self.mean), "std": list(self.std),
            "w1": [list(r) for r in self.w1], "b1": list(self.b1),
            "w2": list(self.w2), "b2": self.b2, "scale": self.scale,
            "provenance": dict(self.provenance),
        }

    @staticmethod
    def from_dict(d: dict) -> "NetEval":
        expected = features.schema_hash(d["feature_set"])
        if d.get("feature_schema_hash") != expected:
            raise ValueError(
                f"stale net artifact: feature_set {d['feature_set']!r} schema hash "
                f"{d.get('feature_schema_hash')!r} != current {expected!r} - retrain")
        return NetEval(
            feature_set=d["feature_set"], mean=tuple(d["mean"]), std=tuple(d["std"]),
            w1=tuple(tuple(r) for r in d["w1"]), b1=tuple(d["b1"]),
            w2=tuple(d["w2"]), b2=float(d["b2"]), scale=float(d.get("scale", 1.0)),
            provenance=dict(d.get("provenance", {})))

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f)
