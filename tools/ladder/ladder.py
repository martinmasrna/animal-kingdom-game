"""One ladder for everyone who has played: people and bots on the same Elo scale.

A bot is a player like any other (docs/bots.md; Martin, 2026-10-17 and 2026-10-24). Every logged game is a rated game:
a person against the live Expert on the web, two Experts against each other in a benchmark, two people in a friend match.
A bot's identity is its spec and its deck (the pairing), a person's identity is their profile. The ratings are a
Bradley-Terry fit over all games at once (a logistic model of who beats whom, with a weak prior so a pairing with few
games sits near the field rather than at infinity), reported in Elo units: 400 points of difference is 10:1 odds.

    .venv/bin/python tools/ladder/ladder.py [--results results] [--anchor 1900]

Sources: results/human_games/web/*.jsonl (the web server's games; the people behind them from results/players.json,
`deploy/deploy.sh players`), results/bot_quality/*/logs/*.jsonl (every benchmark game; the specs from run.json or
run.sh). The Expert a web game met is the spec live at that time (EXPERT_HISTORY, from the commits of web/match.py).
The anchor: the hand-formula Expert of 22 October, averaged over the bot pool, is 1900; everything else is relative.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import math
import os
import re
import sys

import numpy as np

ELO_PER_NAT = 400 / math.log(10)   # Elo points per unit of log-odds

# The Expert the web served, by the time its spec was committed plus the deploy that followed (about forty minutes).
HAND = ("referee:depth=1,den_sense=true,reply_turns=3,w.pending_target=1.5,w.buried_presence=0.25,w.food_progress=0,"
        "w.food_curve=3,w.food_proximity=60,w.food_race=true")
EXPERT_HISTORY = [
    ("2026-10-23T17:30", "referee_learned:eval=slot_r456,depth=1,den_sense=true,reply_turns=3,w.pending_target=1.5,"
                         "w.buried_presence=0.25,w.food_progress=0,w.food_curve=3,w.food_proximity=60,w.food_race=true,"
                         "quiesce=true,mulligan=true"),
    ("2026-10-23T11:30", "referee_learned:eval=wave2_net_r2,depth=1,den_sense=true,reply_turns=3,w.pending_target=1.5,"
                         "w.buried_presence=0.25,w.food_progress=0,w.food_curve=3,w.food_proximity=60,w.food_race=true,"
                         "quiesce=true,mulligan=true"),
    ("2026-10-22T10:15", HAND + ",quiesce=true,mulligan=true"),
    ("2026-10-21T23:45", HAND + ",quiesce=true"),
    ("2026-10-21T10:00", HAND),
    ("2026-10-20T12:30", "referee:depth=1,den_sense=true,reply_turns=3,w.pending_target=1.5,w.buried_presence=0.25"),
    ("2000-01-01T00:00", "referee"),   # the plain referee, before the wave-2 dials shipped on 20 Oct
]
LABELS = {
    EXPERT_HISTORY[0][1]: "Expert, slot network (live since 23 Oct pm)",
    EXPERT_HISTORY[1][1]: "Expert, round-2 network (23 Oct am)",
    EXPERT_HISTORY[2][1]: "Expert, hand formula + mulligan (22 Oct)",
    EXPERT_HISTORY[3][1]: "Expert, hand formula + quiesce (21 Oct pm)",
    EXPERT_HISTORY[4][1]: "Expert, hand formula, food race (21 Oct)",
    EXPERT_HISTORY[5][1]: "Expert, den sense (20 Oct)",
    EXPERT_HISTORY[6][1]: "Expert before 20 Oct (plain referee)",
    "normal": "Normal", "easy": "Easy",
}
ANCHOR_SPEC = EXPERT_HISTORY[2][1]
EVAL_ALIASES = {"wave2_slot_r456": "slot_r456"}


def canonical(spec: str) -> str:
    """A bot spec with the time budget dropped, the evaluator by its bare name, the dials in a fixed order."""
    kind, _, rest = spec.partition(":")
    kw = {}
    for part in filter(None, rest.split(",")):
        k, _, v = part.partition("=")
        if k == "time_budget":
            continue
        if k == "eval":
            v = os.path.basename(v)
            v = v[:-5] if v.endswith(".json") else v
            v = EVAL_ALIASES.get(v, v)
        kw[k] = v
    order = ["eval", "depth", "den_sense", "reply_turns"]
    keys = [k for k in order if k in kw] + sorted(k for k in kw if k not in order)
    return kind + (":" + ",".join(f"{k}={kw[k]}" for k in keys) if keys else "")


def label(spec: str) -> str:
    c = canonical(spec)
    for k, v in LABELS.items():
        if canonical(k) == c:
            return v
    mine = set(c.partition(":")[2].split(","))
    ref = set(canonical(ANCHOR_SPEC).partition(":")[2].split(","))
    added = sorted(d for d in mine - ref if not d.startswith("eval="))
    missing = sorted(d for d in ref - mine if not d.startswith("eval="))
    kw = dict(part.partition("=")[::2] for part in mine if part)
    parts = ([kw["eval"]] if "eval" in kw else []) + [f"+{d}" for d in added] + [f"-{d}" for d in missing]
    return "candidate, " + " ".join(parts) if parts else c


def expert_at(stamp: str) -> str:
    for since, spec in EXPERT_HISTORY:
        if stamp >= since:
            return spec
    return EXPERT_HISTORY[-1][1]


def load_people(results: str):
    """match key -> {seat: profile name}; seat from the history row, the key as the web logs form it."""
    path = os.path.join(results, "players.json")
    if not os.path.exists(path):
        return {}, {}
    d = json.load(open(path))
    names = {p["id"]: f'{p["name"]}#{p["tag"]}' for p in d["profiles"]}
    by_match: dict[str, dict[str, str]] = collections.defaultdict(dict)
    for h in d["history"]:
        by_match[h["match"]][h.get("seat") or "?"] = names.get(h["profile"], h["profile"])
    return by_match, names


def web_games(results: str, people):
    games, skipped = [], collections.Counter()
    for f in sorted(glob.glob(os.path.join(results, "human_games", "web", "*.jsonl"))):
        m = re.search(r"_(\d{8}T\d{6})_", os.path.basename(f))
        stamp = f"{m[1][:4]}-{m[1][4:6]}-{m[1][6:8]}T{m[1][9:11]}:{m[1][11:13]}" if m else "2000-01-01T00:00"
        for line in open(f):
            try:
                g = json.loads(line)
            except Exception:
                skipped["unreadable"] += 1
                continue
            bots = g.get("bots") or []
            if len(bots) != 2 or g.get("winner") not in ("A", "B"):
                skipped["no result"] += 1
                continue
            key = f"{g.get('match_id')}-{g.get('series') or 0}"
            seats = people.get(key, {})
            ids = []
            for seat, kind, deck in zip("AB", bots, (g.get("deck_a"), g.get("deck_b"))):
                if kind == "human":
                    ids.append(("person", seats.get(seat, "person without a profile")))
                elif kind == "expert":
                    ids.append(("bot", canonical(expert_at(stamp)), deck))
                elif kind in ("normal", "easy"):
                    ids.append(("bot", kind, deck))
                else:
                    ids.append(("bot", canonical(kind), deck))
            games.append((ids[0], ids[1], g["winner"], "web"))
    return games, skipped


def run_specs(out: str):
    """(candidate, baseline, opponent) specs of a benchmark folder, from run.json or the run script."""
    rj = os.path.join(out, "run.json")
    if os.path.exists(rj):
        d = json.load(open(rj))
        return d["candidate"], d["baseline"], d["baseline"]
    sh = os.path.join(out, "run.sh")
    if not os.path.exists(sh):
        return None
    text = open(sh).read()
    env = dict(re.findall(r'^([A-Z_]+)="([^"]*)"', text, re.M))

    def arg(name):
        m = re.search(rf"--{name} +(\"[^\"]*\"|'[^']*'|\S+)", text)
        if not m:
            return None
        v = m[1].strip("\"'")
        return re.sub(r"\$(\w+)", lambda mm: env.get(mm[1], mm[0]), v)
    c, b, o = arg("candidate-kind"), arg("baseline-kind"), arg("opponent-kind")
    return (c, b, o or b) if c and b else None


def bench_games(results: str):
    games, runs = [], 0
    for out in sorted(glob.glob(os.path.join(results, "bot_quality", "*"))):
        logs = glob.glob(os.path.join(out, "logs", "*.jsonl"))
        specs = run_specs(out) if logs else None
        if not specs:
            continue
        cand, base, opp = (canonical(s) for s in specs)
        runs += 1
        for f in logs:
            name = os.path.basename(f)[:-6]
            deck, _, side = name.rpartition("-")
            if side not in ("candidate", "baseline"):
                continue
            a_spec = cand if side == "candidate" else base
            for line in open(f):
                try:
                    g = json.loads(line)
                except Exception:
                    continue
                if g.get("winner") not in ("A", "B"):
                    continue
                games.append((("bot", a_spec, g.get("deck_a")), ("bot", opp, g.get("deck_b")), g["winner"], "bench"))
    return games, runs


def fit(games, prior_sd=2.0):
    ids = sorted({g[0] for g in games} | {g[1] for g in games}, key=str)
    index = {i: k for k, i in enumerate(ids)}
    n = len(ids)
    a = np.array([index[g[0]] for g in games]); b = np.array([index[g[1]] for g in games])
    y = np.array([1.0 if g[2] == "A" else 0.0 for g in games])
    theta = np.zeros(n)
    for _ in range(60):
        p = 1 / (1 + np.exp(-(theta[a] - theta[b])))
        grad = np.zeros(n)
        np.add.at(grad, a, y - p); np.add.at(grad, b, p - y)
        grad -= theta / prior_sd ** 2
        w = p * (1 - p)
        H = np.zeros((n, n))
        np.add.at(H, (a, a), w); np.add.at(H, (b, b), w)
        np.add.at(H, (a, b), -w); np.add.at(H, (b, a), -w)
        H += np.eye(n) / prior_sd ** 2
        step = np.linalg.solve(H, grad)
        theta += step
        if np.abs(step).max() < 1e-8:
            break
    cov = np.linalg.inv(H)
    counts = collections.Counter()
    for g in games:
        counts[g[0]] += 1; counts[g[1]] += 1
    return ids, index, theta, cov, counts


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--results", default=os.path.join(here, "..", "..", "results"))
    ap.add_argument("--anchor", type=float, default=1900.0, help="rating of the anchor Expert averaged over the pool")
    ap.add_argument("--min-games", type=int, default=10)
    args = ap.parse_args()
    results = os.path.abspath(args.results)

    people, names = load_people(results)
    web, skipped = web_games(results, people)
    bench, runs = bench_games(results)
    games = web + bench
    print(f"{len(web)} web games, {len(bench)} benchmark games from {runs} runs"
          + (f"; skipped {dict(skipped)}" if skipped else ""))
    ids, index, theta, cov, counts = fit(games)

    pool = sorted({i[2] for i in ids if i[0] == "bot" and i[1] == canonical(ANCHOR_SPEC)})
    anchor_ids = [("bot", canonical(ANCHOR_SPEC), d) for d in pool]
    anchor = np.mean([theta[index[i]] for i in anchor_ids])
    elo = lambda i: args.anchor + ELO_PER_NAT * (theta[index[i]] - anchor)
    se = lambda i: ELO_PER_NAT * math.sqrt(cov[index[i], index[i]])

    def group(spec):
        members = [i for i in ids if i[0] == "bot" and i[1] == spec]
        ks = [index[i] for i in members]
        m = np.mean(theta[ks])
        v = cov[np.ix_(ks, ks)].sum() / len(ks) ** 2
        best = max(members, key=elo); worst = min(members, key=elo)
        return (args.anchor + ELO_PER_NAT * (m - anchor), ELO_PER_NAT * math.sqrt(v),
                sum(counts[i] for i in members), best, worst, len(members))

    win = lambda d: 100 / (1 + 10 ** (-d / 400))
    print("\nPeople (rating, 95% range, games):")
    persons = [i for i in sorted((i for i in ids if i[0] == "person"), key=lambda i: -elo(i)) if counts[i] >= args.min_games]
    for i in persons:
        print(f"  {i[1]:<34}{elo(i):7.0f}  ±{2*se(i):4.0f}  {counts[i]:6d}")

    print("\nBots, averaged over the decks they played (rating, 95% range, games; best and worst pairing):")
    specs = sorted({i[1] for i in ids if i[0] == "bot"}, key=lambda s: -group(s)[0])
    for s in specs:
        r, sd, n, best, worst, k = group(s)
        if n < args.min_games:
            continue
        print(f"  {label(s):<52}{r:7.0f}  ±{2*sd:4.0f}  {n:6d}   {k:2d} decks   best {best[2]} {elo(best):.0f}, worst {worst[2]} {elo(worst):.0f}")

    live = canonical(EXPERT_HISTORY[0][1])
    r, sd, n, best, worst, k = group(live)
    print(f"\nAgainst the live Expert, expected win rate (average pairing / its best pairing, {best[2]}):")
    for i in persons:
        print(f"  {i[1]:<34}{win(elo(i) - r):5.0f}% / {win(elo(i) - elo(best)):3.0f}%")

    print(f"\nAnchor: {label(ANCHOR_SPEC)} over {len(pool)} pool decks = {args.anchor:.0f}. "
          "Elo: 100 points = 64% for the stronger side, 200 = 76%, 400 = 91%.")


if __name__ == "__main__":
    main()
