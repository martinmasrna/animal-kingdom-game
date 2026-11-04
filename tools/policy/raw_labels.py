"""Relabel raw-position rows with the search's own verdict, where a self-play round recorded one.

Usage: raw_labels.py IN.npz OUT.npz --search ROUND_search.npz [...] --logs ROUND.jsonl [...] [--mix 1.0]

IN.npz is what `raw_extract.py` wrote from the same logs, in the same order; its `game` column is the running index of
games with a winner, which the logs turn back into seeds. A round's `*_search.npz` (tools/policy/selfplay_rs.py) holds,
per (seed, turn), the whole-turn search's score of the mover's position turned into a win chance. A mover row at that
(seed, turn) gets that chance, the other seat's row at the same position gets one minus it, and the label becomes
    y = (1 - mix) * outcome + mix * search
Rows without a search label keep the outcome. `has_search` marks which rows were relabelled.
"""
import argparse, json
import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp"); ap.add_argument("out")
    ap.add_argument("--search", nargs="+", required=True); ap.add_argument("--logs", nargs="+", required=True)
    ap.add_argument("--mix", type=float, default=1.0)
    a = ap.parse_args()
    seeds = []
    for path in a.logs:
        for line in open(path):
            if not line.strip():
                continue
            g = json.loads(line)
            if g.get("winner") is not None:
                seeds.append(int(g["seed"]))
    search = {}
    for p in a.search:
        d = np.load(p)
        for s, t, y in zip(d["game"].tolist(), d["turn"].tolist(), d["y"].tolist()):
            search[(int(s), int(t))] = float(y)
    d = dict(np.load(a.inp))
    game, turn, mover, y = d["game"], d["turn"], d["mover"], d["y_win"].astype(np.float32)
    assert game.max() < len(seeds), (game.max(), len(seeds))
    has = np.zeros(len(y), dtype=bool)
    new = y.copy()
    for i in range(len(y)):
        v = search.get((seeds[game[i]], int(turn[i])))
        if v is None:
            continue
        p = v if mover[i] else 1.0 - v
        new[i] = (1.0 - a.mix) * y[i] + a.mix * p
        has[i] = True
    d["y_outcome"] = y
    d["y_win"] = new
    d["has_search"] = has
    np.savez_compressed(a.out, **d)
    print(f"{len(y)} rows, {has.sum()} relabelled ({has.mean():.1%}), mix {a.mix}; search label mean {new[has].mean():.3f} "
          f"vs outcome mean {y[has].mean():.3f} on those rows -> {a.out}")


if __name__ == "__main__":
    main()
