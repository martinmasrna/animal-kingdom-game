"""Fit the value network on self-play rounds and write a NetEval artifact.

Supervised on game outcomes: every recorded position is labelled with whether its side went
on to win. One hidden ReLU layer, logistic loss, weight decay, Adam, early stopping on a slice
of the training games; the test games are held out entirely (split by game, never by
position). A logistic regression on the same inputs is fit alongside as the yardstick.

The output logit is scaled into hand-eval points (`POINTS_PER_LOGIT`, the calibrated slope of
the hand eval against outcomes) so the search's point-valued penalties keep their size.

    python -m animal_kingdom.learn.net OUT.json ROUND.npz [ROUND.npz ...] [--hidden 32]
"""

from __future__ import annotations

import argparse
import sys
import time

POINTS_PER_LOGIT = 47.0
STD_FLOOR = 1e-3


def _np():
    import numpy as np
    return np


def load_rounds(paths):
    np = _np()
    ds = [np.load(p) for p in paths]
    names = [str(n) for n in ds[0]["features"]]
    for d in ds[1:]:
        if [str(n) for n in d["features"]] != names:
            raise ValueError("rounds were recorded with different feature sets")
    cat = lambda k: np.concatenate([d[k] for d in ds])
    # games are identified by seed; rounds use disjoint seed ranges
    return names, cat("x").astype(np.float64), cat("y"), cat("turn"), cat("game"), cat("deck")


def logloss(p, t):
    np = _np()
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-np.mean(t * np.log(p) + (1 - t) * np.log(1 - p)))


def fit_mlp(X, y, Xv, yv, hidden, l2, seed=0, epochs=40, batch=512, lr=1e-3):
    np = _np()
    rng = np.random.default_rng(seed)
    n = X.shape[1]
    P = [rng.normal(0, np.sqrt(2 / n), (n, hidden)), np.zeros(hidden),
         rng.normal(0, np.sqrt(1 / hidden), hidden), np.zeros(1)]

    def fwd(P, A):
        h = np.maximum(0, A @ P[0] + P[1])
        return h, 1 / (1 + np.exp(-np.clip(h @ P[2] + P[3][0], -30, 30)))

    m = [np.zeros_like(p) for p in P]
    v = [np.zeros_like(p) for p in P]
    best, best_P, step, stale = np.inf, [p.copy() for p in P], 0, 0
    for _ in range(epochs):
        idx = rng.permutation(len(y))
        for i in range(0, len(y), batch):
            b = idx[i:i + batch]
            h, p = fwd(P, X[b])
            e = (p - y[b]) / len(b)
            d = np.outer(e, P[2]) * (h > 0)
            grads = [X[b].T @ d + l2 * P[0], d.sum(0), h.T @ e + l2 * P[2], np.array([e.sum()])]
            step += 1
            for j, g in enumerate(grads):
                m[j] = 0.9 * m[j] + 0.1 * g
                v[j] = 0.999 * v[j] + 0.001 * g * g
                P[j] -= lr * (m[j] / (1 - 0.9 ** step)) / (np.sqrt(v[j] / (1 - 0.999 ** step)) + 1e-8)
        loss = logloss(fwd(P, Xv)[1], yv)
        if loss < best - 1e-5:
            best, best_P, stale = loss, [p.copy() for p in P], 0
        else:
            stale += 1
            if stale >= 4:
                break
    return best_P, lambda A: fwd(best_P, A)[1]


def fit_linear(X, y, l2=1e-3):
    np = _np()
    from scipy.optimize import minimize

    def f(w):
        z = X @ w[:-1] + w[-1]
        p = 1 / (1 + np.exp(-np.clip(z, -30, 30)))
        g = np.append(X.T @ (p - y), (p - y).sum()) / len(y)
        g[:-1] += l2 * w[:-1]
        return float(np.mean(np.logaddexp(0, z) - y * z) + 0.5 * l2 * w[:-1] @ w[:-1]), g

    w = minimize(f, np.zeros(X.shape[1] + 1), jac=True, method="L-BFGS-B").x
    return lambda A: 1 / (1 + np.exp(-np.clip(A @ w[:-1] + w[-1], -30, 30)))


def train(out, paths, hidden=32, l2=1e-4, feature_set="rung2"):
    np = _np()
    from ..bots.net_eval import NetEval

    names, X, y, turn, game, deck = load_rounds(paths)
    bucket = (game.astype(np.int64) * 2654435761 % 2**32) % 100    # seeds are not uniform mod k
    test = bucket < 20
    val = (bucket >= 20) & (bucket < 30)
    fit = ~test & ~val
    mean = X[fit].mean(0)
    std = np.maximum(X[fit].std(0), STD_FLOOR)
    Z = (X - mean) / std
    t0 = time.time()
    P, net = fit_mlp(Z[fit], y[fit], Z[val], y[val], hidden, l2)
    lin = fit_linear(Z[~test], y[~test])
    base = np.full(test.sum(), y[~test].mean())
    report = {"positions": int(len(y)), "games": int(len(np.unique(game))),
              "test_positions": int(test.sum()), "fit_seconds": round(time.time() - t0, 1)}
    for label, p in (("base_rate", base), ("linear", lin(Z[test])), ("net", net(Z[test]))):
        row = {"all": logloss(p, y[test])}
        for bn, mk in (("t1_4", turn[test] <= 4), ("t5_9", (turn[test] >= 5) & (turn[test] <= 9)),
                       ("t10p", turn[test] >= 10)):
            row[bn] = logloss(p[mk], y[test][mk])
        report[label] = row
    NetEval(feature_set=feature_set, mean=tuple(mean), std=tuple(std),
            w1=tuple(tuple(col) for col in P[0].T), b1=tuple(P[1]), w2=tuple(P[2]),
            b2=float(P[3][0]), scale=POINTS_PER_LOGIT,
            provenance={"rounds": list(paths), "hidden": hidden, "l2": l2,
                        "report": report}).save(out)
    return report


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("out")
    p.add_argument("rounds", nargs="+")
    p.add_argument("--hidden", type=int, default=32)
    p.add_argument("--l2", type=float, default=1e-4)
    a = p.parse_args(argv)
    rep = train(a.out, a.rounds, a.hidden, a.l2)
    for k, v in rep.items():
        print(f"{k:15s} {v}")


if __name__ == "__main__":
    main(sys.argv[1:])
