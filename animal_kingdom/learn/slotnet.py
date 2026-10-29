"""Fit the slot network on self-play rounds recorded with the board feature set, and write a SlotEval artifact.

The board set lays a position out as sixteen crossroad slots and eight hand slots, each a property vector, plus the
global columns. A plain network over those columns gives every slot its own weights and learns what the pool's decks
do at crossroad 7 (2026-10-23: worse than the hand formula on Martin's games while fine inside the pool). This one
reads every slot with the same small encoder, so what it learns about an animal at one crossroad holds at every
other, and keeps the geometry through a learned embedding per slot. Pooling by sum and max over the slots makes the
board summary permutation-symmetric; the hand slots the same without an embedding.

    logit = w2 . relu(W1 . [z_global, sum_k s_k, max_k s_k, sum_k h_k, max_k h_k] + b1) + b2
    s_k = relu(We_s . [slot_k, E_k] + be_s)        h_k = relu(We_h . hand_k + be_h)

Supervised on game outcomes like `learn.net`: logistic loss, Adam, weight decay, early stopping on a slice of the
training games, the test games held out by game. The forward pass is written out by hand in numpy, and so is the
backward pass; `check_gradients` compares it with finite differences.

    python -m animal_kingdom.learn.slotnet OUT.json ROUND.npz [ROUND.npz ...] [--test HUMAN.npz]
"""

from __future__ import annotations

import argparse
import sys
import time

from .net import POINTS_PER_LOGIT, logloss, load_rounds, STD_FLOOR
from ..bots import features

EMBED = 8          # the learned geometry of a slot
SLOT_HIDDEN = 24
HAND_HIDDEN = 12
TRUNK_HIDDEN = 48


def _np():
    import numpy as np
    return np


def layout(names):
    """Column indexes of the board set: the global columns, the slot block and the hand block."""
    n_slots, n_hands = features.BOARD_SLOTS, features.HAND_SLOTS
    sw, hw = sum(n.startswith("cr0_") for n in names), sum(n.startswith("hand0_") for n in names)
    first_slot = next(i for i, n in enumerate(names) if n.startswith("cr0_"))
    first_hand = next(i for i, n in enumerate(names) if n.startswith("hand0_"))
    assert names[first_slot + n_slots * sw - 1].startswith(f"cr{n_slots - 1}_") and names[first_hand + n_hands * hw - 1].startswith(f"hand{n_hands - 1}_")
    globals_ = [i for i in range(len(names)) if not (first_slot <= i < first_slot + n_slots * sw or first_hand <= i < first_hand + n_hands * hw)]
    return {"globals": globals_, "slot_offset": first_slot, "slot_width": sw, "n_slots": n_slots,
            "hand_offset": first_hand, "hand_width": hw, "n_hands": n_hands}


def split(X, lay):
    np = _np()
    G = X[:, lay["globals"]]
    S = X[:, lay["slot_offset"]:lay["slot_offset"] + lay["n_slots"] * lay["slot_width"]].reshape(len(X), lay["n_slots"], lay["slot_width"])
    H = X[:, lay["hand_offset"]:lay["hand_offset"] + lay["n_hands"] * lay["hand_width"]].reshape(len(X), lay["n_hands"], lay["hand_width"])
    return G, S, H


def init(lay, seed=0):
    np = _np()
    rng = np.random.default_rng(seed)
    sw, hw, ng = lay["slot_width"], lay["hand_width"], len(lay["globals"])
    trunk_in = ng + 2 * SLOT_HIDDEN + 2 * HAND_HIDDEN
    return {
        "E": rng.normal(0, 0.1, (lay["n_slots"], EMBED)),
        "We_s": rng.normal(0, (2 / (sw + EMBED)) ** 0.5, (sw + EMBED, SLOT_HIDDEN)), "be_s": np.zeros(SLOT_HIDDEN),
        "We_h": rng.normal(0, (2 / hw) ** 0.5, (hw, HAND_HIDDEN)), "be_h": np.zeros(HAND_HIDDEN),
        "W1": rng.normal(0, (2 / trunk_in) ** 0.5, (trunk_in, TRUNK_HIDDEN)), "b1": np.zeros(TRUNK_HIDDEN),
        "w2": rng.normal(0, (1 / TRUNK_HIDDEN) ** 0.5, TRUNK_HIDDEN), "b2": np.zeros(1),
    }


def forward(P, Gz, S, H):
    """Returns the probability and the cache the backward pass needs."""
    np = _np()
    B = len(Gz)
    Sc = np.concatenate([S, np.broadcast_to(P["E"], (B,) + P["E"].shape)], axis=2)      # (B, 16, sw+EMBED)
    As = Sc @ P["We_s"] + P["be_s"]
    Hs = np.maximum(0, As)                                                               # (B, 16, SLOT_HIDDEN)
    Ah = H @ P["We_h"] + P["be_h"]
    Hh = np.maximum(0, Ah)                                                               # (B, 8, HAND_HIDDEN)
    X = np.concatenate([Gz, Hs.sum(1), Hs.max(1), Hh.sum(1), Hh.max(1)], axis=1)
    A1 = X @ P["W1"] + P["b1"]
    H1 = np.maximum(0, A1)
    logit = H1 @ P["w2"] + P["b2"][0]
    p = 1 / (1 + np.exp(-np.clip(logit, -30, 30)))
    return p, (Sc, Hs, Hh, X, H1, logit)


def backward(P, cache, dlogit, S, H):
    """Gradients of sum(dlogit * logit) with respect to every parameter."""
    np = _np()
    Sc, Hs, Hh, X, H1, _ = cache
    g = {}
    g["w2"] = H1.T @ dlogit
    g["b2"] = np.array([dlogit.sum()])
    dH1 = np.outer(dlogit, P["w2"]) * (H1 > 0)
    g["W1"] = X.T @ dH1
    g["b1"] = dH1.sum(0)
    dX = dH1 @ P["W1"].T
    ng = X.shape[1] - 2 * SLOT_HIDDEN - 2 * HAND_HIDDEN
    d_sum_s = dX[:, ng:ng + SLOT_HIDDEN]
    d_max_s = dX[:, ng + SLOT_HIDDEN:ng + 2 * SLOT_HIDDEN]
    d_sum_h = dX[:, ng + 2 * SLOT_HIDDEN:ng + 2 * SLOT_HIDDEN + HAND_HIDDEN]
    d_max_h = dX[:, ng + 2 * SLOT_HIDDEN + HAND_HIDDEN:]
    # sum pool broadcasts; max pool routes to the first slot holding the maximum (numpy's argmax, as the forward's max)
    dHs = np.repeat(d_sum_s[:, None, :], Hs.shape[1], axis=1)
    arg = Hs.argmax(1)                                                                  # (B, SLOT_HIDDEN)
    np.put_along_axis(dHs, arg[:, None, :], np.take_along_axis(dHs, arg[:, None, :], axis=1) + d_max_s[:, None, :], axis=1)
    dHs = dHs * (Hs > 0)
    dHh = np.repeat(d_sum_h[:, None, :], Hh.shape[1], axis=1)
    argh = Hh.argmax(1)
    np.put_along_axis(dHh, argh[:, None, :], np.take_along_axis(dHh, argh[:, None, :], axis=1) + d_max_h[:, None, :], axis=1)
    dHh = dHh * (Hh > 0)
    g["We_s"] = np.einsum("bki,bkj->ij", Sc, dHs)
    g["be_s"] = dHs.sum((0, 1))
    dSc = dHs @ P["We_s"].T
    g["E"] = dSc[:, :, S.shape[2]:].sum(0)
    g["We_h"] = np.einsum("bki,bkj->ij", H, dHh)
    g["be_h"] = dHh.sum((0, 1))
    return g


def check_gradients(seed=0, eps=1e-6):
    """Finite differences against `backward` on a random batch; the largest relative error."""
    np = _np()
    names = features.feature_names("board")
    lay = layout(names)
    rng = np.random.default_rng(seed)
    B = 5
    Gz = rng.normal(size=(B, len(lay["globals"])))
    S = rng.normal(size=(B, lay["n_slots"], lay["slot_width"])) * (rng.random((B, lay["n_slots"], 1)) < 0.5)
    H = rng.normal(size=(B, lay["n_hands"], lay["hand_width"])) * (rng.random((B, lay["n_hands"], 1)) < 0.5)
    P = init(lay, seed)
    dlogit = rng.normal(size=B)
    _, cache = forward(P, Gz, S, H)
    g = backward(P, cache, dlogit, S, H)

    def f():
        _, c = forward(P, Gz, S, H)
        return float((dlogit * c[5]).sum())

    worst = {}
    for k, arr in P.items():
        flat = arr.reshape(-1)
        for idx in rng.choice(flat.size, size=min(8, flat.size), replace=False):
            old = flat[idx]
            flat[idx] = old + eps; up = f()
            flat[idx] = old - eps; down = f()
            flat[idx] = old
            num = (up - down) / (2 * eps)
            ana = g[k].reshape(-1)[idx]
            worst[k] = max(worst.get(k, 0.0), abs(num - ana) / max(1e-6, abs(num), abs(ana)))
    return worst


def fit(P, Gz, S, H, y, val, l2=1e-4, epochs=30, batch=512, lr=1e-3, seed=0):
    np = _np()
    rng = np.random.default_rng(seed)
    m = {k: np.zeros_like(v) for k, v in P.items()}
    v = {k: np.zeros_like(a) for k, a in P.items()}
    Gv, Sv, Hv, yv = Gz[val], S[val], H[val], y[val]
    fit_idx = np.flatnonzero(~val)
    best, best_P, step, stale = np.inf, {k: a.copy() for k, a in P.items()}, 0, 0
    for epoch in range(epochs):
        rng.shuffle(fit_idx)
        for s0 in range(0, len(fit_idx), batch):
            idx = fit_idx[s0:s0 + batch]
            p, cache = forward(P, Gz[idx], S[idx], H[idx])
            dlogit = (p - y[idx]) / len(idx)
            g = backward(P, cache, dlogit, S[idx], H[idx])
            step += 1
            for k in P:
                gk = g[k] + l2 * P[k]
                m[k] = 0.9 * m[k] + 0.1 * gk
                v[k] = 0.999 * v[k] + 0.001 * gk * gk
                mh = m[k] / (1 - 0.9 ** step)
                vh = v[k] / (1 - 0.999 ** step)
                P[k] -= lr * mh / (np.sqrt(vh) + 1e-8)
        pv, _ = forward(P, Gv, Sv, Hv)
        loss = logloss(pv, yv)
        if loss < best - 1e-5:
            best, best_P, stale = loss, {k: a.copy() for k, a in P.items()}, 0
        else:
            stale += 1
            if stale >= 4:
                break
    return best_P


def to_live(names, X):
    """Rows of the "board" set as `board_live` reads them: a crossroad's Roar has fired, so its roar column is 0 and a
    Roar animal's ability column 0 too. Exact but for the few Roar animals with a lasting ability (Meerkat, the
    Caterpillar's line, the Dung Beetle's forms, the Hungry Rhinos), which the rows cannot tell apart."""
    for k in range(features.BOARD_SLOTS):
        r, a = names.index(f"cr{k}_roar"), names.index(f"cr{k}_ability")
        roar = X[:, r] != 0
        X[roar, a] = 0.0
        X[:, r] = 0.0
    return X


def train(out, paths, l2=1e-4, test_path=None, epochs=30, live=False):
    np = _np()
    from ..bots.slot_eval import SlotEval

    if live:     # board rounds read as board_live, beside rounds recorded with board_live itself
        np_ = _np()
        parts = [load_rounds([p]) for p in paths]
        if any(part[6] not in ("board", "board_live") for part in parts):
            raise ValueError("the slot network reads the board feature sets")
        names = parts[0][0]
        X = np_.concatenate([to_live(names, part[1]) if part[6] == "board" else part[1] for part in parts])
        y, turn, game, deck = (np_.concatenate([part[k] for part in parts]) for k in (2, 3, 4, 5))
        feature_set = "board_live"
    else:
        names, X, y, turn, game, deck, feature_set = load_rounds(paths)
    if feature_set not in features.BOARD_SETS:
        raise ValueError(f"the slot network reads the board feature set, not {feature_set!r}")
    lay = layout(names)
    bucket = (game.astype(np.int64) * 2654435761 % 2**32) % 100
    test = bucket < 20
    val = (bucket >= 20) & (bucket < 30)
    fit_mask = ~test & ~val
    G, S, H = split(X, lay)
    raw_std = G[fit_mask].std(0)
    dead = raw_std < 1e-9
    mean = np.where(dead, 0.0, G[fit_mask].mean(0))
    std = np.where(dead, 1.0, np.maximum(raw_std, STD_FLOOR))
    Gz = (G - mean) / std
    t0 = time.time()
    P = init(lay)
    P = fit(P, Gz[~test], S[~test], H[~test], y[~test], val[~test], l2=l2, epochs=epochs)
    P["W1"][:len(lay["globals"])][dead, :] = 0.0
    report = {"positions": int(len(y)), "games": int(len(np.unique(game))), "test_positions": int(test.sum()),
              "fit_seconds": round(time.time() - t0, 1)}
    p_test, _ = forward(P, Gz[test], S[test], H[test])
    base = np.full(test.sum(), y[~test].mean())
    for label, p in (("base_rate", base), ("slotnet", p_test)):
        row = {"all": logloss(p, y[test])}
        for bn, mk in (("t1_4", turn[test] <= 4), ("t5_9", (turn[test] >= 5) & (turn[test] <= 9)), ("t10p", turn[test] >= 10)):
            row[bn] = logloss(p[mk], y[test][mk])
        report[label] = row
    ev = SlotEval(feature_set=feature_set, globals_=tuple(lay["globals"]), slot_offset=lay["slot_offset"], slot_width=lay["slot_width"],
                  n_slots=lay["n_slots"], hand_offset=lay["hand_offset"], hand_width=lay["hand_width"], n_hands=lay["n_hands"],
                  mean=tuple(mean), std=tuple(std), embed=tuple(tuple(r) for r in P["E"]),
                  we_s=tuple(tuple(r) for r in P["We_s"]), be_s=tuple(P["be_s"]), we_h=tuple(tuple(r) for r in P["We_h"]), be_h=tuple(P["be_h"]),
                  w1=tuple(tuple(r) for r in P["W1"]), b1=tuple(P["b1"]), w2=tuple(P["w2"]), b2=float(P["b2"][0]), scale=POINTS_PER_LOGIT,
                  provenance={"rounds": list(paths), "l2": l2, "live": live, "report": report})
    if test_path:
        t = np.load(test_path)
        if [str(n) for n in t["features"]] != names:
            raise ValueError("the test set was recorded with a different feature set")
        Xt = t["x"].astype(np.float64)
        Gt, St, Ht = split(to_live(names, Xt) if live else Xt, lay)
        yt, tt = t["y"], t["turn"]
        pt, _ = forward(P, (Gt - mean) / std, St, Ht)
        outside = {"positions": int(len(yt)), "games": int(len(np.unique(t["game"])))}
        scorers = [("slotnet", pt)]
        if "hand" in t:
            scorers.append(("hand", 1 / (1 + np.exp(-np.clip(t["hand"] / POINTS_PER_LOGIT, -30, 30)))))
        for label, p in scorers:
            row = {"all": logloss(p, yt)}
            for bn, mk in (("t1_4", tt <= 4), ("t5_9", (tt >= 5) & (tt <= 9)), ("t10p", tt >= 10)):
                row[bn] = logloss(p[mk], yt[mk]) if mk.any() else None
            agree = (p > 0.5) == (yt > 0.5)
            row["sign"] = round(float(agree.mean()), 4)
            mid = (tt >= 5) & (tt <= 9)
            row["sign_t5_9"] = round(float(agree[mid].mean()), 4) if mid.any() else None
            outside[label] = row
        report["outside_test"] = outside
    ev.save(out)
    return report


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("out")
    p.add_argument("rounds", nargs="+")
    p.add_argument("--l2", type=float, default=1e-4)
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--test", default=None, help="an outside test set (.npz with x, y, turn, game, features[, hand])")
    p.add_argument("--live", action="store_true", help="fit the board_live set: the board's fired Roars read as spent")
    p.add_argument("--check", action="store_true", help="only check the gradients against finite differences")
    a = p.parse_args(argv)
    if a.check:
        print("largest relative gradient error by parameter:", {k: f"{v:.1e}" for k, v in check_gradients().items()})
        return
    rep = train(a.out, a.rounds, a.l2, test_path=a.test, epochs=a.epochs, live=a.live)
    for k, v in rep.items():
        print(f"{k:15s} {v}")


if __name__ == "__main__":
    main(sys.argv[1:])
