"""A round robin of decks played by one bot, and what each card did for its deck.

    .venv/bin/python tools/cardstats/roundrobin.py run --profile 73fc9b588392c875 --games 200 --name 2026-11-24
    .venv/bin/python tools/cardstats/roundrobin.py report results/cardstats/2026-11-24

`run` plays every pair of the decks (no mirrors) `--games` times, half with each deck going first, both seats the same
bot (Practice's unless `--bot`), each game seeded from its number, so a run with the same arguments on the same commit
plays the same games. The decks are a profile's in the local database (results/web.db), or a deck file (`--decks`,
{"decks": [{"name", "leader", "cards"}]}). It writes results/cardstats/NAME/: run.json (the commit, the bot, the decks)
and games.jsonl, one line a game as it finishes, so a run stopped halfway is read as far as it got. A game records
for each seat its deck, the cards it held after the mulligan, every card of its deck it ever held (opening hand or
drawn, Scout included; a card an effect made, such as a hatched Flight 1, is not its deck's) with the turn it first
did, and the cards it played from hand.

`report` reads a run: each deck's win rate, overall, by matchup and going first or second; and for each card of each
deck, its improvement when drawn early: among the games that reached game turn `--by` (8: each player's fourth turn),
the win rate of those in which a copy was in hand by then, less the win rate of those in which none was, with a 95%
interval; and the win rate of the games it was in the opening hand. Not "held at any point" (17lands' IWD): a deck
sees nearly all its 25 cards in a long game, so a card never held marks a short game, and that score measured game
length (the 2026-11-24 run: every Sage card +28 to +46). An early IWD ranks cards within their deck.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import sqlite3
import subprocess
import sys
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import ak_engine  # noqa: E402

from animal_kingdom import game  # noqa: E402
from animal_kingdom.web.match import PRACTICE_BOT  # noqa: E402

ACTIONS_MAX = 5000


def profile_decks(profile: str) -> list[dict]:
    db = sqlite3.connect(ROOT / "results" / "web.db")
    out = []
    for name, leader, cards in db.execute("SELECT name, leader, cards FROM decks WHERE profile = ? ORDER BY pos", (profile,)):
        c = json.loads(cards)
        out.append({"name": name, "leader": leader, "cards": c if isinstance(c, list) else [k for k, n in c.items() for _ in range(n)]})
    return out


def hand_of(d: dict, p: str) -> dict:
    """iid -> (card, made) of seat `p`'s hand."""
    return {u["iid"]: (u["card_id"], u.get("made", False)) for u in d["hands"][p]}


def play(engine, bot: str, da: dict, db: dict, first: str, seed: int) -> dict:
    """One game, deck `da` in seat A and `db` in seat B, `first` going first."""
    rs = engine.new_game(da["cards"], db["cards"], seed, first, {"A": da["leader"], "B": db["leader"]})
    bots = {"A": ak_engine.Bot(bot, seed), "B": ak_engine.Bot(bot, seed + 1)}
    seen = {"A": {}, "B": {}}          # card -> the turn it was first held
    opening = {"A": None, "B": None}
    played = {"A": [], "B": []}
    d = rs.to_dict()

    mulliganing = lambda d, p: bool(d["pending"]) and d["pending"].get("kind") == "mulligan" and d["pending"].get("chooser") == p

    def look(d):
        # from its kept hand on: a card sent back in the mulligan was never held
        for p in "AB":
            if opening[p] is None:
                continue
            for card, made in hand_of(d, p).values():
                if not made and card not in seen[p]:
                    seen[p][card] = d["turn_counter"]
    result = None
    for _ in range(ACTIONS_MAX):
        result = rs.is_terminal()
        if result is not None:
            break
        p = rs.player_to_act()
        before = hand_of(d, p)
        was = mulliganing(d, p)
        action = bots[p].choose(rs)
        rs.apply_action(action, False)
        d = rs.to_dict()
        if was and not mulliganing(d, p):   # the opening hand: what its seat kept
            opening[p] = sorted(c for c, made in hand_of(d, p).values() if not made)
            for c in opening[p]:
                seen[p].setdefault(c, d["turn_counter"])
        if action.get("kind") == "place":
            after = hand_of(d, p)
            played[p] += [card for iid, (card, made) in before.items() if iid not in after and not made]
        look(d)
    seat = lambda p, dk: {"deck": dk["name"], "opening": opening[p] or [], "seen": seen[p], "played": played[p]}
    return {"seed": seed, "first": first, "winner": result and result.get("winner"), "reason": result and result.get("reason"),
            "turns": d["turn_counter"], "A": seat("A", da), "B": seat("B", db)}


def run(args) -> None:
    decks = json.loads(Path(args.decks).read_text())["decks"] if args.decks else profile_decks(args.profile)
    for dk in decks:
        problems = game.deck_problems(dk["cards"], dk["leader"])
        if problems:
            sys.exit(f"{dk['name']}: {'; '.join(problems)}")
    out = ROOT / "results" / "cardstats" / args.name
    out.mkdir(parents=True, exist_ok=True)
    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    (out / "run.json").write_text(json.dumps({"commit": commit, "bot": args.bot, "map": args.map, "games": args.games, "decks": decks}, indent=1) + "\n")
    engine = game._engine_for(None, None, args.map)
    jobs = []
    for k, (a, b) in enumerate(itertools.combinations(range(len(decks)), 2)):
        for g in range(args.games):
            jobs.append((decks[a], decks[b], "A" if g % 2 == 0 else "B", 100_000 * (k + 1) + g))
    print(f"{len(decks)} decks ({', '.join(d['name'] for d in decks)}), {len(jobs)} games, {args.bot}, {args.jobs} at a time", flush=True)
    lock, done, t0 = threading.Lock(), [0], time.time()
    with open(out / "games.jsonl", "w") as f:
        def one(job):
            rec = play(engine, args.bot, *job)
            with lock:
                f.write(json.dumps(rec) + "\n"); f.flush()
                done[0] += 1
                if done[0] % 50 == 0 or done[0] == len(jobs):
                    el = time.time() - t0
                    print(f"{done[0]}/{len(jobs)} games, {el / 60:.1f} min, about {el / done[0] * (len(jobs) - done[0]) / 60:.0f} min to go", flush=True)
        with ThreadPoolExecutor(args.jobs) as ex:   # a bot thinks with the interpreter released
            list(ex.map(one, jobs))
    print(f"done in {(time.time() - t0) / 60:.1f} min: {out}")


def interval(w: int, n: int) -> float:
    """The half-width of a 95% interval on a win rate of w in n."""
    if n == 0:
        return float("nan")
    p = w / n
    return 1.96 * math.sqrt(max(p * (1 - p), 1e-9) / n)


def report(args) -> None:
    path = Path(args.path)
    games = [json.loads(line) for line in (path / "games.jsonl").read_text().splitlines() if line.strip()]
    decks = {d["name"]: d for d in json.loads((path / "run.json").read_text())["decks"]}
    rows = []   # (deck, seat record, won)
    for g in games:
        if g["winner"] is None:
            continue
        for p in "AB":
            rows.append((g[p]["deck"], g[p], g["winner"] == p, g["first"] == p, g["B" if p == "A" else "A"]["deck"], g["turns"]))
    print(f"{len(games)} games ({sum(g['winner'] is None for g in games)} without a winner), {path.name}\n")
    pct = lambda w, n: f"{100 * w / n:5.1f}%" if n else "    - "
    print("Decks: win rate overall, going first, going second, and against each deck")
    names = list(decks)
    for dk in names:
        mine = [r for r in rows if r[0] == dk]
        w, n = sum(r[2] for r in mine), len(mine)
        f1 = [r for r in mine if r[3]]; f2 = [r for r in mine if not r[3]]
        vs = "  ".join(f"{o} {pct(sum(r[2] for r in mine if r[4] == o), sum(1 for r in mine if r[4] == o)).strip()}" for o in names if o != dk)
        print(f"  {dk:10} {pct(w, n)} ±{100 * interval(w, n):4.1f}   first {pct(sum(r[2] for r in f1), len(f1))}  second {pct(sum(r[2] for r in f2), len(f2))}   {vs}")
    T = args.by
    print(f"\nCards, by deck: early IWD (of the games that reached turn {T}: win rate when a copy was in hand by then, less when")
    print("none was), with its 95% interval; held: the share of those games a copy was; opening: the win rate when a copy was in the opening hand")
    for dk in names:
        mine = [r for r in rows if r[0] == dk]
        base = sum(r[2] for r in mine) / max(1, len(mine))
        print(f"\n  {dk} ({len(mine)} games, {100 * base:.1f}% won)")
        out = []
        for card in sorted(set(decks[dk]["cards"])):
            reached = [r for r in mine if r[5] >= T]
            held = [r for r in reached if r[1]["seen"].get(card, T) < T]; not_held = [r for r in reached if r[1]["seen"].get(card, T) >= T]
            op = [r for r in mine if card in r[1]["opening"]]
            wh, nh, wn, nn = sum(r[2] for r in held), len(held), sum(r[2] for r in not_held), len(not_held)
            iwd = (wh / nh - wn / nn) if nh and nn else float("nan")
            half = 1.96 * math.sqrt((wh / nh) * (1 - wh / nh) / nh + (wn / nn) * (1 - wn / nn) / nn) if nh and nn else float("nan")
            out.append((iwd, card, nh, len(reached), half, sum(r[2] for r in op), len(op)))
        for iwd, card, nh, n, half, wo, no in sorted(out, key=lambda x: -x[0] if x[0] == x[0] else 1e9):
            name = game.CARDS[card].name if card in game.CARDS else card
            print(f"    {name:22} early IWD {100 * iwd:+6.1f} ±{100 * half:4.1f}   held {100 * nh / n:3.0f}%   opening {pct(wo, no)} (in {no})")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--profile", help="a profile id in results/web.db: its decks")
    r.add_argument("--decks", help="a deck file instead")
    r.add_argument("--games", type=int, default=200, help="games a pair of decks plays, half with each going first")
    r.add_argument("--bot", default=PRACTICE_BOT)
    r.add_argument("--map", default="map_sq16")
    r.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    r.add_argument("--name", default=time.strftime("%Y-%m-%d-%H%M"))
    p = sub.add_parser("report")
    p.add_argument("path")
    p.add_argument("--by", type=int, default=8, help="the game turn a card counts as drawn early by (8: each player's fourth turn)")
    args = ap.parse_args(argv)
    if args.cmd == "run":
        if not (args.profile or args.decks):
            sys.exit("run: --profile or --decks")
        run(args)
    else:
        report(args)


if __name__ == "__main__":
    main()
