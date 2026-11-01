"""The candidate network: a score per legal action from the position and the action's own features, trained on which
action the search took (cross-entropy over the legal actions of each decision).

Usage: train.py OUT.pt --train A.npz [B.npz ...] --test C.npz [...] [--epochs N] [--hidden H]
Reports, on every test set, how often the taken action is the net's first pick, and inside its top 3, 5, 8, next to
chance (8 of the legal actions at random).
"""
import argparse, sys, time
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as Fn


def load(files):
    pos, act, offs, chosen, game = [], [], [0], [], []
    base_game, base_act = 0, 0
    for f in files:
        d = np.load(f)
        pos.append(d["pos"]); act.append(d["act"]); chosen.append(d["chosen"])
        offs.extend((d["offs"][1:] + base_act).tolist())
        game.append(d["meta"][:, 0] + base_game)
        base_game += int(d["meta"][:, 0].max()) + 1 if len(d["meta"]) else 0
        base_act += len(d["act"])
    return (np.concatenate(pos), np.concatenate(act), np.array(offs, dtype=np.int64), np.concatenate(chosen),
            np.concatenate(game))


class Net(nn.Module):
    """`head="mlp"`: a small network over (position, action, their product). `head="dot"`: the score is the dot product
    of the position's and the action's embeddings plus a bias, so scoring an action costs one small layer and a dot
    product: the shape the engine can afford at every decision of a search."""
    def __init__(self, pos_n, act_n, hidden=128, head="mlp"):
        super().__init__()
        self.kind = head
        self.pos = nn.Sequential(nn.Linear(pos_n, hidden), nn.ReLU(), nn.Linear(hidden, hidden), nn.ReLU())
        self.act = nn.Sequential(nn.Linear(act_n, hidden), nn.ReLU())
        if head == "mlp":
            self.head = nn.Sequential(nn.Linear(3 * hidden, hidden), nn.ReLU(), nn.Linear(hidden, 1))
        else:
            self.bias = nn.Linear(act_n, 1)

    def forward(self, pos, act, owner):
        """pos (N,P), act (M,A), owner (M,) the decision index of each action -> a score per action (M,)."""
        p = self.pos(pos)[owner]
        a = self.act(act)
        if self.kind == "mlp":
            return self.head(torch.cat([p, a, p * a], dim=1)).squeeze(1)
        return (p * a).sum(1) + self.bias(act).squeeze(1)


def batches(idx, offs, bs):
    for i in range(0, len(idx), bs):
        yield idx[i:i + bs]


def scores_of(net, pos, act, offs, dec, dev):
    """Scores for the decisions `dec` (indices): returns (scores (M,), owner (M,), starts)."""
    pos_t = torch.tensor(pos[dec], device=dev)
    pieces, owner = [], []
    for j, d in enumerate(dec):
        pieces.append(act[offs[d]:offs[d + 1]]); owner.extend([j] * (offs[d + 1] - offs[d]))
    act_t = torch.tensor(np.concatenate(pieces), device=dev)
    owner_t = torch.tensor(owner, device=dev)
    return net(pos_t, act_t, owner_t), owner_t


def loss_of(scores, owner, chosen_local, n_dec):
    """Softmax over each decision's actions; cross-entropy on the taken one."""
    # log-sum-exp per decision
    mx = torch.full((n_dec,), -1e9, device=scores.device).scatter_reduce(0, owner, scores, reduce="amax")
    ex = torch.exp(scores - mx[owner])
    z = torch.zeros(n_dec, device=scores.device).scatter_add(0, owner, ex)
    logp = scores - mx[owner] - torch.log(z)[owner]
    return -logp[chosen_local].mean()


def evaluate(net, data, dev):
    return evaluate_subset(net, data, np.arange(len(data[3])), dev)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--train", nargs="+", required=True)
    ap.add_argument("--test", nargs="+", default=[])
    ap.add_argument("--epochs", type=int, default=6)
    ap.add_argument("--hidden", type=int, default=128)
    ap.add_argument("--head", default="mlp", choices=("mlp", "dot"))
    ap.add_argument("--bs", type=int, default=256)
    ap.add_argument("--lr", type=float, default=1e-3)
    args = ap.parse_args()
    dev = "cpu"                                    # small nets: the CPU beats the MPS launch cost
    pos, act, offs, chosen, game = load(args.train)
    # held-out by game: every tenth game
    hold = (game % 10) == 0
    tr = np.where(~hold)[0]; va = np.where(hold)[0]
    print(f"train decisions {len(tr)}, held-out {len(va)}, actions {len(act)}, games {game.max() + 1}", flush=True)
    net = Net(pos.shape[1], act.shape[1], args.hidden, args.head).to(dev)
    opt = torch.optim.Adam(net.parameters(), lr=args.lr)
    tests = {f: load([f]) for f in args.test}

    best = {"top8": -1.0}

    def report(tag):
        out = {"held-out": evaluate_subset(net, (pos, act, offs, chosen, game), va, dev)}
        for f, d in tests.items():
            out[f.split("/")[-1]] = evaluate(net, d, dev)
        for k, v in out.items():
            print(f"  {tag} {k}: " + " ".join(f"{a}={b:.3f}" if isinstance(b, float) else f"{a}={b}" for a, b in v.items()), flush=True)
        if out["held-out"]["top8"] > best["top8"]:          # the saved net is the best epoch by held-out top 8
            best["top8"] = out["held-out"]["top8"]
            torch.save({"state": net.state_dict(), "pos_n": pos.shape[1], "act_n": act.shape[1], "hidden": args.hidden,
                        "head": args.head, "tag": tag, "held_out": out["held-out"]}, args.out)
            print(f"  saved {args.out} ({tag})", flush=True)

    report("start")
    for ep in range(args.epochs):
        t0 = time.time(); tot = 0.0; cnt = 0
        rng = np.random.default_rng(ep)
        order = rng.permutation(tr)
        for dec in batches(order, offs, args.bs):
            s, owner = scores_of(net, pos, act, offs, dec, dev)
            starts = np.cumsum([0] + [offs[d + 1] - offs[d] for d in dec[:-1]])
            chosen_local = torch.tensor(starts + chosen[dec], device=dev)
            loss = loss_of(s, owner, chosen_local, len(dec))
            opt.zero_grad(); loss.backward(); opt.step()
            tot += float(loss) * len(dec); cnt += len(dec)
        print(f"epoch {ep + 1}: loss {tot / cnt:.3f} ({time.time() - t0:.0f} s)", flush=True)
        report(f"epoch {ep + 1}")
    print("done; best held-out top8", round(best["top8"], 3), "in", args.out)


def evaluate_subset(net, data, dec_idx, dev, ks=(1, 3, 5, 8), bs=512):
    pos, act, offs, chosen, _ = data
    net.eval()
    hits = {k: 0 for k in ks}; chance = 0.0; n = 0; nll = 0.0
    wide = {"top8": 0, "chance8": 0.0, "n": 0}                   # the decisions with 12 or more legal actions
    with torch.no_grad():
        for dec in batches(dec_idx, offs, bs):
            s, owner = scores_of(net, pos, act, offs, dec, dev)
            s = s.cpu().numpy()
            start = 0
            for d in dec:
                m = offs[d + 1] - offs[d]
                sc = s[start:start + m]; start += m
                order = np.argsort(-sc)
                rank = int(np.where(order == chosen[d])[0][0])
                for k in ks:
                    hits[k] += rank < k
                chance += min(1.0, 8.0 / m)
                if m >= 12:
                    wide["top8"] += rank < 8; wide["chance8"] += 8.0 / m; wide["n"] += 1
                p = np.exp(sc - sc.max()); p /= p.sum(); nll += -np.log(max(p[chosen[d]], 1e-9))
                n += 1
    net.train()
    w = max(wide["n"], 1)
    return ({f"top{k}": hits[k] / n for k in ks} | {"chance8": chance / n, "nll": nll / n, "n": n,
            "wide_top8": wide["top8"] / w, "wide_chance8": wide["chance8"] / w, "wide_n": wide["n"]})


if __name__ == "__main__":
    main()
