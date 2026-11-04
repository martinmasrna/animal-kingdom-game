"""Train the raw-position network and compare it offline with a network on today's descriptions and with the live
evaluation function, on the same positions.

    python -m animal_kingdom.learn.rawnet OUT.pt TRAIN.npz [TRAIN.npz ...] [--test HUMAN.npz] [--dim 32] [--epochs 40]

Inputs are the arrays `tools/policy/raw_extract.py` writes. Every card id is one learned vector (`--dim` numbers) shared
across the board, the hand, the deck, the pool and the piles. The 15 crossroads go through one small encoder each
(top piece, card beneath, slot position) and are pooled by sum and max; each bag is the weighted sum of its cards'
vectors; the globals go in as they are. Two outputs: this seat wins the game; this seat loses its den within three
turns. The description network has the same trunk and outputs over the 908 board_live inputs, so the only difference
measured is what the network is shown. Games held out by game (every fifth game); Martin's games as a second test set.
"""

from __future__ import annotations

import argparse
import sys
import time

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as Fn

from ..bots import raw_position as R

N_OWNER = 4
SLOT_HIDDEN = 48
SLOT_OUT = 32
TRUNK = (192, 64)
DROPOUT = 0.0


def load(paths):
    ds = [np.load(p, allow_pickle=False) for p in paths]
    out = {"source": np.concatenate([np.full(len(d["y_win"]), i, dtype=np.int16) for i, d in enumerate(ds)]), "paths": list(paths)}
    keys = [k for k in ds[0].files if all(k in d.files for d in ds)]
    # a relabelled file carries the outcome beside the (soft) training label; a plain file's outcome is its label
    out["y_outcome"] = np.concatenate([d["y_outcome"] if "y_outcome" in d.files else d["y_win"] for d in ds])
    for k in keys:
        if k.endswith("_names") or k in ("bags", "desc_names", "cards"):
            out[k] = ds[0][k]
        elif k == "game":
            base, parts = 0, []
            for d in ds:
                parts.append(d[k] + base); base += int(d[k].max()) + 1 if len(d[k]) else 0
            out[k] = np.concatenate(parts)
        elif k.endswith("_off"):
            base, parts = 0, [np.array([0], dtype=np.int64)]
            for d in ds:
                parts.append(d[k][1:] + base); base += int(d[k][-1])
            out[k] = np.concatenate(parts)
        else:
            out[k] = np.concatenate([d[k] for d in ds])
    return out


class Batch:
    """Index a dataset by rows; bags are re-packed per batch (indices, weights, offsets)."""

    def __init__(self, d, device):
        self.d, self.device = d, device
        self.n = len(d["y_win"])
        self.bags = [str(b) for b in d["bags"]]

    def take(self, rows):
        d, dev = self.d, self.device
        rows = np.asarray(rows)
        out = {
            "cr_card": torch.as_tensor(d["cr_card"][rows].astype(np.int64), device=dev),
            "cr_owner": torch.as_tensor(d["cr_owner"][rows].astype(np.int64), device=dev),
            "top_num": torch.as_tensor(d["top_num"][rows].astype(np.float32), device=dev),
            "under_num": torch.as_tensor(d["under_num"][rows].astype(np.float32), device=dev),
            "globals": torch.as_tensor(d["globals"][rows].astype(np.float32), device=dev),
            "desc": torch.as_tensor(d["desc"][rows].astype(np.float32), device=dev),
            "y": torch.as_tensor(np.stack([d["y_win"][rows], d["y_den3"][rows]], 1).astype(np.float32), device=dev),
            "w": torch.as_tensor(d["row_w"][rows].astype(np.float32), device=dev) if "row_w" in d else None,
        }
        bags = {}
        for b in self.bags:
            off, idx, w = d[f"bag_{b}_off"], d[f"bag_{b}_idx"], d[f"bag_{b}_w"]
            starts, ends = off[rows], off[rows + 1]
            lens = ends - starts
            sel = np.concatenate([np.arange(s, e) for s, e in zip(starts, ends)]) if lens.sum() else np.zeros(0, dtype=np.int64)
            boffs = np.concatenate([[0], np.cumsum(lens)[:-1]])
            bags[b] = (torch.as_tensor(idx[sel].astype(np.int64), device=dev), torch.as_tensor(w[sel].astype(np.float32), device=dev),
                       torch.as_tensor(boffs, device=dev))
        out["bags"] = bags
        return out


def trunk(n_in):
    return nn.Sequential(nn.Dropout(DROPOUT), nn.Linear(n_in, TRUNK[0]), nn.ReLU(), nn.Dropout(DROPOUT),
                         nn.Linear(TRUNK[0], TRUNK[1]), nn.ReLU(), nn.Dropout(DROPOUT), nn.Linear(TRUNK[1], 2))


class RawNet(nn.Module):
    def __init__(self, n_cards, dim, bags, n_top, n_under, n_glob):
        super().__init__()
        self.n_cards, self.dim, self.bags = n_cards, dim, bags
        self.card = nn.Embedding(n_cards + 1, dim, padding_idx=n_cards)
        self.slot_pos = nn.Embedding(R.N_CROSSROADS, 8)
        slot_in = 2 * (dim + N_OWNER) + n_top + n_under + 8
        self.slot = nn.Sequential(nn.Linear(slot_in, SLOT_HIDDEN), nn.ReLU(), nn.Linear(SLOT_HIDDEN, SLOT_OUT), nn.ReLU())
        trunk_in = n_glob + 2 * SLOT_OUT + len(bags) * dim
        self.trunk = trunk(trunk_in)

    def forward(self, x):
        B = x["globals"].shape[0]
        cards = x["cr_card"].clone(); cards[cards < 0] = self.n_cards
        e = self.card(cards)                                                   # (B, 15, 2, dim)
        own = Fn.one_hot(x["cr_owner"], N_OWNER).float()                      # (B, 15, 2, 4)
        pos = self.slot_pos.weight.unsqueeze(0).expand(B, -1, -1)              # (B, 15, 8)
        slot_in = torch.cat([e[:, :, 0], own[:, :, 0], x["top_num"], e[:, :, 1], own[:, :, 1], x["under_num"], pos], dim=2)
        s = self.slot(slot_in)                                                 # (B, 15, SLOT_OUT)
        pooled = torch.cat([s.sum(1), s.max(1).values], dim=1)
        bag_vecs = []
        for b in self.bags:
            idx, w, off = x["bags"][b]
            if len(idx):
                v = Fn.embedding_bag(idx, self.card.weight, off, per_sample_weights=w, mode="sum")
            else:
                v = torch.zeros(B, self.dim, device=self.card.weight.device)
            bag_vecs.append(v)
        return self.trunk(torch.cat([x["globals"], pooled, *bag_vecs], dim=1))


class DescNet(nn.Module):
    def __init__(self, n_in):
        super().__init__()
        self.trunk = trunk(n_in)
        self.register_buffer("mu", torch.zeros(n_in)); self.register_buffer("sd", torch.ones(n_in))

    def standardise(self, X):
        self.mu.copy_(X.mean(0)); self.sd.copy_(X.std(0) + 1e-3)

    def forward(self, x):
        return self.trunk((x["desc"] - self.mu) / self.sd)


def auc(p, y):
    order = np.argsort(p); r = np.empty(len(p)); r[order] = np.arange(1, len(p) + 1); n1 = y.sum()
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(y) - n1))) if 0 < n1 < len(y) else float("nan")


def score(logits, y):
    p = 1 / (1 + np.exp(-logits)); p = np.clip(p, 1e-6, 1 - 1e-6)
    ll = float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
    return ll, auc(p, y), float(np.mean((p > 0.5) == (y > 0.5)))


def predict(model, batch, rows, bs=4096):
    model.eval(); outs = []
    with torch.no_grad():
        for i in range(0, len(rows), bs):
            outs.append(model(batch.take(rows[i:i + bs])).cpu().numpy())
    model.train()
    return np.concatenate(outs) if outs else np.zeros((0, 2))


def train(model, batch, tr, va, epochs, lr, wd, bs, log, name):
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=wd)
    best, best_state, bad = float("inf"), None, 0
    rng = np.random.default_rng(0)
    for ep in range(epochs):
        t0 = time.time(); perm = rng.permutation(tr); tot = 0.0
        for i in range(0, len(perm), bs):
            x = batch.take(perm[i:i + bs])
            if x["w"] is None:
                loss = Fn.binary_cross_entropy_with_logits(model(x), x["y"])
            else:   # a row's weight: who played it (--weight, one per training file)
                loss = (Fn.binary_cross_entropy_with_logits(model(x), x["y"], reduction="none") * x["w"][:, None]).sum() / (2 * x["w"].sum())
            opt.zero_grad(); loss.backward(); opt.step(); tot += float(loss.detach()) * len(x["y"])
        pv = predict(model, batch, va)
        vl = np.mean([score(pv[:, k], np.stack([batch.d["y_win"][va], batch.d["y_den3"][va]], 1)[:, k])[0] for k in range(2)])
        log(f"  {name} epoch {ep + 1:2d} train {tot / len(perm):.4f} val {vl:.4f} ({time.time() - t0:.0f}s)")
        if vl < best - 1e-4:
            best, bad = vl, 0; best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= 4:
                break
    model.load_state_dict(best_state)
    return model


def report(log, name, logits, d, rows, head):
    y = (d.get("y_outcome", d["y_win"]) if head == 0 else d["y_den3"])[rows]
    ll, a, acc = score(logits[:, head] if logits.ndim == 2 else logits, y)
    log(f"{name:52s} log-loss {ll:.4f}  AUC {a:.3f}  accuracy {acc:.3f}  (base rate {y.mean():.3f}, {len(y)} rows)")


def export(model: "RawNet", cards: list[str], out: str, provenance: dict, scale: float) -> None:
    """The artifact both engines read (`bots/raw_eval.py`, `engine_rs/src/bots/raw.rs`): weights as [in][out] rows."""
    import json
    sd = {k: v.detach().cpu().numpy().astype(np.float64) for k, v in model.state_dict().items()}
    t = lambda k: sd[k].T.tolist()
    lin = [k for k in sd if k.startswith("trunk.") and k.endswith(".weight")]
    lin.sort(key=lambda k: int(k.split(".")[1]))
    assert len(lin) == 3, lin
    (w1, w2, w3) = lin
    b = lambda k: sd[k.replace("weight", "bias")].tolist()
    slot = sorted((k for k in sd if k.startswith("slot.") and k.endswith(".weight")), key=lambda k: int(k.split(".")[1]))
    d = {"kind": "rawnet", "feature_set": "raw", "dim": model.dim, "cards": cards,
         "card_table": sd["card.weight"][: len(cards)].tolist(), "slot_pos": sd["slot_pos.weight"].tolist(),
         "slot_w1": t(slot[0]), "slot_b1": b(slot[0]), "slot_w2": t(slot[1]), "slot_b2": b(slot[1]),
         "trunk_w1": t(w1), "trunk_b1": b(w1), "trunk_w2": t(w2), "trunk_b2": b(w2), "out_w": t(w3), "out_b": b(w3),
         "scale": scale, "bags": list(model.bags), "globals": list(R.GLOBALS), "top_num": list(R.TOP_NUM),
         "under_num": list(R.UNDER_NUM), "provenance": provenance}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(d, f)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("train", nargs="+"); ap.add_argument("--test", nargs="*", default=[])
    ap.add_argument("--dim", type=int, default=32); ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--lr", type=float, default=1e-3); ap.add_argument("--wd", type=float, default=1e-5)
    ap.add_argument("--batch", type=int, default=512); ap.add_argument("--live", default="wave2_slot_r4_10_live")
    ap.add_argument("--cpu", action="store_true"); ap.add_argument("--dropout", type=float, default=0.0)
    ap.add_argument("--trunk", default="192,64"); ap.add_argument("--only", choices=["raw", "desc"], default=None)
    ap.add_argument("--export", default=None, help="write the trained raw network as a rawnet JSON artifact")
    ap.add_argument("--scale", type=float, default=47.0, help="points per logit in the artifact (net.POINTS_PER_LOGIT)")
    ap.add_argument("--weight", default=None, help="row weights, one per training file (e.g. 1,1,2,20): who played the position")
    ap.add_argument("--init", default=None, help="start the raw network from this checkpoint (fine-tuning)")
    ap.add_argument("--game-offset", type=int, default=0, help="shift game ids before the held-out split, to keep a fine-tune's held-out games the same as the checkpoint's")
    a = ap.parse_args(argv)
    global DROPOUT, TRUNK
    DROPOUT = a.dropout; TRUNK = tuple(int(v) for v in a.trunk.split(","))
    log = lambda s: print(s, flush=True)
    dev = torch.device("cpu" if a.cpu or not torch.backends.mps.is_available() else "mps")
    d = load(a.train)
    n_cards = int(max(d[f"bag_{b}_idx"].max() if len(d[f"bag_{b}_idx"]) else 0 for b in [str(x) for x in d["bags"]]) + 1)
    n_cards = max(n_cards, int(d["cr_card"].max()) + 1)
    if a.weight:
        ws = [float(v) for v in a.weight.split(",")]; assert len(ws) == len(a.train), (ws, a.train)
        d["row_w"] = np.array(ws, dtype=np.float32)[d["source"]]
    batch = Batch(d, dev)
    games = d["game"] + a.game_offset; held = (games % 5) == 0; val = (games % 5) == 1
    tr = np.where(~held & ~val)[0]; va = np.where(val)[0]; te = np.where(held)[0]
    log(f"rows {batch.n} train {len(tr)} val {len(va)} held-out {len(te)}; cards {n_cards}; device {dev}")
    tests = [("held-out games", d, batch, te)] if len(a.train) == 1 else \
        [(f"held-out games of {p}", d, batch, te[d["source"][te] == i]) for i, p in enumerate(a.train)]
    for p in a.test:
        dt = load([p]); tests.append((f"Martin's games ({p})", dt, Batch(dt, dev), np.arange(len(dt["y_win"]))))
    # the live evaluation function on the same rows, for reference
    try:
        if a.only:
            raise RuntimeError("skipped (--only)")
        from ..bots.learned_eval import load_eval
        live = load_eval(a.live)
        for name, dt, bt, rows in tests:
            lg = np.array([live.logit_of([float(v) for v in row]) for row in dt["desc"][rows].astype(np.float64)])
            for head in (0, 1):
                report(log, f"live evaluation function, {'winner' if head == 0 else 'den lost in 3'}: {name}", (lg if head == 0 else -lg), dt, rows, head)
    except Exception as e:  # noqa: BLE001
        log(f"live evaluation function not scored: {e}")
    models = []
    if a.only != "raw":
        desc = DescNet(d["desc"].shape[1]).to(dev)
        desc.standardise(torch.as_tensor(d["desc"][tr].astype(np.float32), device=dev))
        models.append(("descriptions network (908 inputs)", train(desc, batch, tr, va, a.epochs, a.lr, a.wd, a.batch, log, "descriptions")))
    if a.only != "desc":
        raw = RawNet(n_cards, a.dim, batch.bags, d["top_num"].shape[2], d["under_num"].shape[2], d["globals"].shape[1]).to(dev)
        if a.init:
            ck = torch.load(a.init, map_location=dev)
            assert ck["dim"] == a.dim and ck["n_cards"] == n_cards and list(ck["bags"]) == list(batch.bags), "checkpoint does not match the data"
            raw.load_state_dict(ck["state"]); log(f"raw network initialised from {a.init}")
        models.append((f"raw position network (dim {a.dim})", train(raw, batch, tr, va, a.epochs, a.lr, a.wd, a.batch, log, "raw")))
        torch.save({"state": raw.state_dict(), "dim": a.dim, "n_cards": n_cards, "bags": batch.bags, "trunk": TRUNK}, a.out)
        if a.export:
            cards = [str(c) for c in d["cards"]] if "cards" in d else None
            if cards is None:
                from ..engine.cards import load_cards
                cards = sorted(load_cards())
            assert len(cards) == n_cards, (len(cards), n_cards)
            export(raw, cards, a.export, {"train": list(a.train), "dim": a.dim, "dropout": DROPOUT, "trunk": list(TRUNK),
                                           "wd": a.wd, "lr": a.lr, "rows": int(batch.n)}, a.scale)
            log(f"exported {a.export}")
    for name, dt, bt, rows in tests:
        for head in (0, 1):
            h = "winner" if head == 0 else "den lost in 3"
            for mname, m in models:
                report(log, f"{mname}, {h}: {name}", predict(m, bt, rows), dt, rows, head)
    log(f"saved {a.out}")


if __name__ == "__main__":
    main()
