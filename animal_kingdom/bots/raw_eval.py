"""The raw-position network as an evaluator (`kind: "rawnet"`): one learned vector per card, a shared crossroad encoder
pooled by sum and max, the bags as weighted sums of card vectors, a two-layer trunk, two outputs (this seat wins the
game; this seat loses its den within three turns). Trained by `learn/rawnet.py`, exported with `--export`; the Rust
engine runs the same artifact (`engine_rs/src/bots/raw.rs`), and `test_raw_position.py` holds the two to the same
numbers. The forward pass is plain Python over lists, exact to the artifact's floats, so a bot without numpy can run it.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any

from ..engine.state import GameState, other_player
from . import raw_position as R


def _relu(v: list[float]) -> list[float]:
    return [x if x > 0.0 else 0.0 for x in v]


def _linear(x: list[float], w: list[list[float]], b: list[float]) -> list[float]:
    h = list(b)
    for i, xi in enumerate(x):
        if xi != 0.0:
            row = w[i]
            for j in range(len(h)):
                h[j] += xi * row[j]
    return h


@dataclass(frozen=True)
class RawEval:
    dim: int
    cards: tuple[str, ...]                 # the artifact's card names, row by row of the table
    card_table: tuple[tuple[float, ...], ...]
    slot_pos: tuple[tuple[float, ...], ...]
    slot_w1: tuple[tuple[float, ...], ...]
    slot_b1: tuple[float, ...]
    slot_w2: tuple[tuple[float, ...], ...]
    slot_b2: tuple[float, ...]
    trunk_w1: tuple[tuple[float, ...], ...]
    trunk_b1: tuple[float, ...]
    trunk_w2: tuple[tuple[float, ...], ...]
    trunk_b2: tuple[float, ...]
    out_w: tuple[tuple[float, ...], ...]
    out_b: tuple[float, ...]
    scale: float = 1.0
    provenance: dict = field(default_factory=dict)
    feature_set: str = "raw"

    @staticmethod
    def from_dict(d: dict) -> "RawEval":
        rows = lambda k: tuple(tuple(float(x) for x in r) for r in d[k])
        vec = lambda k: tuple(float(x) for x in d[k])
        if list(d["bags"]) != list(R.BAGS):
            raise ValueError("rawnet artifact's bags differ from the extractor's")
        return RawEval(dim=int(d["dim"]), cards=tuple(d["cards"]), card_table=rows("card_table"), slot_pos=rows("slot_pos"),
                       slot_w1=rows("slot_w1"), slot_b1=vec("slot_b1"), slot_w2=rows("slot_w2"), slot_b2=vec("slot_b2"),
                       trunk_w1=rows("trunk_w1"), trunk_b1=vec("trunk_b1"), trunk_w2=rows("trunk_w2"), trunk_b2=vec("trunk_b2"),
                       out_w=rows("out_w"), out_b=vec("out_b"), scale=float(d.get("scale", 1.0)), provenance=dict(d.get("provenance", {})))

    @staticmethod
    def from_file(path: str) -> "RawEval":
        with open(path, encoding="utf-8") as f:
            return RawEval.from_dict(json.load(f))

    def to_dict(self) -> dict:
        return {"kind": "rawnet", "feature_set": self.feature_set, "dim": self.dim, "cards": list(self.cards),
                "card_table": [list(r) for r in self.card_table], "slot_pos": [list(r) for r in self.slot_pos],
                "slot_w1": [list(r) for r in self.slot_w1], "slot_b1": list(self.slot_b1),
                "slot_w2": [list(r) for r in self.slot_w2], "slot_b2": list(self.slot_b2),
                "trunk_w1": [list(r) for r in self.trunk_w1], "trunk_b1": list(self.trunk_b1),
                "trunk_w2": [list(r) for r in self.trunk_w2], "trunk_b2": list(self.trunk_b2),
                "out_w": [list(r) for r in self.out_w], "out_b": list(self.out_b), "scale": self.scale,
                "bags": list(R.BAGS), "globals": list(R.GLOBALS), "top_num": list(R.TOP_NUM), "under_num": list(R.UNDER_NUM),
                "provenance": self.provenance}

    def table_for(self, state: GameState) -> list[tuple[float, ...]]:
        """The card table in the extractor's index order (the registry's sorted ids); an id the artifact lacks is zeros."""
        by_name = dict(zip(self.cards, self.card_table))
        zero = tuple([0.0] * self.dim)
        return [by_name.get(cid, zero) for cid in sorted(state.cards)]

    def heads_of(self, raw: dict, table: list[tuple[float, ...]]) -> list[float]:
        zero = [0.0] * self.dim
        n_out = len(self.slot_b2)
        sum_s = [0.0] * n_out
        max_s = [-math.inf] * n_out
        for k in range(R.N_CROSSROADS):
            x: list[float] = []
            for layer in (0, 1):
                c = raw["cr_card"][k][layer]
                x.extend(table[c] if c >= 0 else zero)
                own = [0.0] * 4
                own[raw["cr_owner"][k][layer]] = 1.0
                x.extend(own)
                x.extend(raw["top_num"][k] if layer == 0 else raw["under_num"][k])
            x.extend(self.slot_pos[k])
            s = _relu(_linear(_relu(_linear(x, self.slot_w1, self.slot_b1)), self.slot_w2, self.slot_b2))
            for j in range(n_out):
                sum_s[j] += s[j]
                if s[j] > max_s[j]:
                    max_s[j] = s[j]
        t: list[float] = list(raw["globals"]) + sum_s + max_s
        for b in R.BAGS:
            v = [0.0] * self.dim
            for c, w in raw["bags"][b]:
                e = table[c]
                for j in range(self.dim):
                    v[j] += w * e[j]
            t.extend(v)
        h = _relu(_linear(_relu(_linear(t, self.trunk_w1, self.trunk_b1)), self.trunk_w2, self.trunk_b2))
        return _linear(h, self.out_w, self.out_b)

    def heads(self, state: GameState, me: str) -> list[float]:
        return self.heads_of(R.extract(state, me), self.table_for(state))

    def logit(self, state: GameState, me: str) -> float:
        return self.heads(state, me)[0]

    def value(self, state: GameState, me: str) -> float:
        if state.result is not None:
            if state.result.winner == me:
                return math.inf
            if state.result.winner == other_player(me):
                return -math.inf
            return 0.0
        return self.scale * self.logit(state, me)

    def explain(self, state: GameState, me: str) -> dict[str, Any]:
        w, d = self.heads(state, me)
        return {"winner_logit": w, "den_lost_in_3_logit": d}
