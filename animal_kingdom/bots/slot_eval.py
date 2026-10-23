"""SlotEval: the slot network (learn/slotnet.py) as an evaluator, through the same `evaluator=` seam as NetEval.

Every crossroad slot of the board feature set goes through one shared encoder with a learned embedding for the slot's
place on the map, every hand slot through another; the slot encodings are pooled by sum and by max, the globals are
standardised, and a small trunk reads the lot. Stdlib only. The arithmetic here is written in the exact order the Rust
evaluator uses (zero inputs skipped, slots and hidden units in index order), so the two engines agree to the last bit.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any, Mapping

from ..engine.state import GameState, other_player
from . import features


@dataclass(frozen=True)
class SlotEval:
    feature_set: str
    globals_: tuple[int, ...]            # column indexes of the global inputs
    slot_offset: int
    slot_width: int
    n_slots: int
    hand_offset: int
    hand_width: int
    n_hands: int
    mean: tuple[float, ...]              # of the globals
    std: tuple[float, ...]
    embed: tuple[tuple[float, ...], ...]         # n_slots x EMBED
    we_s: tuple[tuple[float, ...], ...]          # (slot_width + EMBED) x SLOT_HIDDEN
    be_s: tuple[float, ...]
    we_h: tuple[tuple[float, ...], ...]          # hand_width x HAND_HIDDEN
    be_h: tuple[float, ...]
    w1: tuple[tuple[float, ...], ...]            # trunk_in x TRUNK_HIDDEN
    b1: tuple[float, ...]
    w2: tuple[float, ...]
    b2: float
    scale: float = 1.0
    provenance: Mapping[str, Any] = field(default_factory=dict)
    # the standardisation of the globals folded into the trunk's first rows, as NetEval does
    _w1g: tuple = field(init=False, repr=False, compare=False, default=())
    _b1f: tuple = field(init=False, repr=False, compare=False, default=())
    _slot_bias: tuple = field(init=False, repr=False, compare=False, default=())

    def __post_init__(self) -> None:
        ng, hidden = len(self.globals_), len(self.b1)
        inv = [1.0 / s for s in self.std]
        w1g = [tuple(self.w1[i][j] * inv[i] for j in range(hidden)) for i in range(ng)]
        b1f = []
        for j in range(hidden):
            acc = 0.0
            for i in range(ng):
                acc += (self.mean[i] * inv[i]) * self.w1[i][j]
            b1f.append(self.b1[j] - acc)
        # the embedding's share of each slot's pre-activation, fixed per slot
        sw = self.slot_width
        slot_bias = []
        for k in range(self.n_slots):
            row = []
            for j in range(len(self.be_s)):
                acc = self.be_s[j]
                for e in range(len(self.embed[k])):
                    acc += self.embed[k][e] * self.we_s[sw + e][j]
                row.append(acc)
            slot_bias.append(tuple(row))
        object.__setattr__(self, "_w1g", tuple(w1g))
        object.__setattr__(self, "_b1f", tuple(b1f))
        object.__setattr__(self, "_slot_bias", tuple(slot_bias))

    def logit_of(self, phi: list[float]) -> float:
        sh, hh, th = len(self.be_s), len(self.be_h), len(self.b1)
        sum_s = [0.0] * sh
        max_s = [-math.inf] * sh
        for k in range(self.n_slots):
            a = list(self._slot_bias[k])
            base = self.slot_offset + k * self.slot_width
            for i in range(self.slot_width):
                x = phi[base + i]
                if x != 0.0:
                    row = self.we_s[i]
                    for j in range(sh):
                        a[j] += x * row[j]
            for j in range(sh):
                h = a[j] if a[j] > 0.0 else 0.0
                sum_s[j] += h
                if h > max_s[j]:
                    max_s[j] = h
        sum_h = [0.0] * hh
        max_h = [-math.inf] * hh
        for k in range(self.n_hands):
            a = list(self.be_h)
            base = self.hand_offset + k * self.hand_width
            for i in range(self.hand_width):
                x = phi[base + i]
                if x != 0.0:
                    row = self.we_h[i]
                    for j in range(hh):
                        a[j] += x * row[j]
            for j in range(hh):
                h = a[j] if a[j] > 0.0 else 0.0
                sum_h[j] += h
                if h > max_h[j]:
                    max_h[j] = h
        t = list(self._b1f)
        for i, col in enumerate(self.globals_):
            x = phi[col]
            if x != 0.0:
                row = self._w1g[i]
                for j in range(th):
                    t[j] += x * row[j]
        ng = len(self.globals_)
        pooled = sum_s + max_s + sum_h + max_h
        for i, x in enumerate(pooled):
            if x != 0.0:
                row = self.w1[ng + i]
                for j in range(th):
                    t[j] += x * row[j]
        out = self.b2
        for j in range(th):
            if t[j] > 0.0:
                out += self.w2[j] * t[j]
        return out

    def logit(self, state: GameState, me: str) -> float:
        return self.logit_of(features.extract(state, me, self.feature_set))

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
            "kind": "slotnet", "feature_set": self.feature_set,
            "feature_schema_hash": features.schema_hash(self.feature_set),
            "globals": list(self.globals_), "slot_offset": self.slot_offset, "slot_width": self.slot_width, "n_slots": self.n_slots,
            "hand_offset": self.hand_offset, "hand_width": self.hand_width, "n_hands": self.n_hands,
            "mean": list(self.mean), "std": list(self.std), "embed": [list(r) for r in self.embed],
            "we_s": [list(r) for r in self.we_s], "be_s": list(self.be_s), "we_h": [list(r) for r in self.we_h], "be_h": list(self.be_h),
            "w1": [list(r) for r in self.w1], "b1": list(self.b1), "w2": list(self.w2), "b2": self.b2, "scale": self.scale,
            "provenance": dict(self.provenance),
        }

    @staticmethod
    def from_dict(d: dict) -> "SlotEval":
        expected = features.schema_hash(d["feature_set"])
        if d.get("feature_schema_hash") != expected:
            raise ValueError(f"stale slotnet artifact: feature_set {d['feature_set']!r} schema hash {d.get('feature_schema_hash')!r} != current {expected!r} - retrain")
        rows = lambda k: tuple(tuple(r) for r in d[k])
        return SlotEval(feature_set=d["feature_set"], globals_=tuple(d["globals"]), slot_offset=d["slot_offset"], slot_width=d["slot_width"],
                        n_slots=d["n_slots"], hand_offset=d["hand_offset"], hand_width=d["hand_width"], n_hands=d["n_hands"],
                        mean=tuple(d["mean"]), std=tuple(d["std"]), embed=rows("embed"), we_s=rows("we_s"), be_s=tuple(d["be_s"]),
                        we_h=rows("we_h"), be_h=tuple(d["be_h"]), w1=rows("w1"), b1=tuple(d["b1"]), w2=tuple(d["w2"]), b2=float(d["b2"]),
                        scale=float(d.get("scale", 1.0)), provenance=dict(d.get("provenance", {})))

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f)
