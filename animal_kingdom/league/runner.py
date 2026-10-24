"""The league runner: the ladder's bots play each other here, by matchmaking, and every result is rated on the web ladder.

    .venv/bin/python -m animal_kingdom.league.runner --server https://animal-kingdom.fly.dev [--jobs 7] [--batch 64] [--pace 1200] [--once]

Each pass asks the server for the pool (`/api/league/pool`: every bot deck's list, every pairing's rating and uncertainty,
the pilots' specs), picks the games a ladder would pick, plays them on the Rust engine (AK_RUST_BOTS=1, the pilots
untimed), posts the results to `/api/league/games`, and appends them to results/league/games.jsonl. Who plays: pairings
still placing first (two games each), then the pairings whose rating is least certain, each against an opponent near its
rating (within the matching window, widened when nobody is there), a fifth of the time against anyone, never itself.
`--pace` caps games an hour so the machine stays usable by day; in the night window (`--night 23-8`) every core plays
and nothing is capped (Martin, 2026-10-24: all in while he is not working). The runner sleeps when the pool needs nothing. The league key
comes from AK_LEAGUE_KEY, results/oauth.json (as the server reads it) or --key-file. The log keeps the cards each side
drew, results/league/facts/<day>.jsonl each game's card facts for the Meta tab (league/facts.py: the mulligan, every card's
draw and play turn, both ratings as it began), and once an hour a tinker pass (league/tinker.py) reads it and posts at most `--births` children a day.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from ..decks import PREMADE_DECKS, load_premade_deck, register_deck
from ..sim.runner import MatchSpec, run_specs
from ..web.league import key as league_key
from ..web.ladder import PROVISIONAL, parse_bot
from . import report, tinker
from .facts import game_facts

WINDOW = 150          # rating distance a matchmaking opponent is drawn from, doubled until someone is there
ANYONE = 0.2          # share of games against anyone at all, as a ladder's queue mixes
PLACING_GAMES = 2     # games a placing pairing gets each pass


def is_night(window: str, hour: int) -> bool:
    """Whether `hour` lies in the 'from-to' window (wrapping midnight: '23-8' is 23:00 to 07:59)."""
    if not window:
        return False
    a, b = (int(x) for x in window.split("-"))
    return a <= hour < b if a < b else hour >= a or hour < b


def api(server: str, path: str, key: str, body=None) -> dict:
    req = urllib.request.Request(server.rstrip("/") + path, headers={"X-AK-League-Key": key, "Content-Type": "application/json"},
                                 data=json.dumps(body).encode() if body is not None else None, method="POST" if body is not None else "GET")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def pick(players: list[dict], batch: int, rng: random.Random) -> list[tuple[str, str]]:
    """The games this pass: (a, b) pairs of bot ladder ids, placing pairings first, then the least certain, opponents near."""
    by_rating = sorted(players, key=lambda p: p["rating"])
    ratings = {p["id"]: p["rating"] for p in players}
    ids = [p["id"] for p in by_rating]

    def opponent(lid: str) -> str:
        if rng.random() < ANYONE:
            return rng.choice([o for o in ids if o != lid])
        window = WINDOW
        while True:
            near = [o for o in ids if o != lid and abs(ratings[o] - ratings[lid]) <= window]
            if near:
                return rng.choice(near)
            window *= 2

    games: list[tuple[str, str]] = []
    placing = [p["id"] for p in players if p["games"] < PROVISIONAL]
    rng.shuffle(placing)
    for lid in placing:
        for _ in range(PLACING_GAMES):
            if len(games) >= batch:
                break
            games.append((lid, opponent(lid)))
    uncertain = sorted((p for p in players if p["games"] >= PROVISIONAL), key=lambda p: (-p["rd"], rng.random()))
    for p in uncertain:
        if len(games) >= batch:
            break
        games.append((p["id"], opponent(p["id"])))
    return games


def play(games: list[tuple[str, str]], pilots: dict[str, str], jobs: int, seed0: int, ratings: dict[str, float]) -> list[dict]:
    """The games played, each with its card facts (league/facts.py) and both players' ratings as the game began."""
    specs = []
    for i, (a, b) in enumerate(games):
        la, da = parse_bot(a); lb, db = parse_bot(b)
        x, y = ((la, da), (lb, db)) if i % 2 == 0 else ((lb, db), (la, da))   # seats alternate
        specs.append((MatchSpec(x[1], y[1], seed0 + i, bot_a=pilots[x[0]], bot_b=pilots[y[0]], log_actions=True),
                      f"bot:{x[0]}:{x[1]}", f"bot:{y[0]}:{y[1]}"))
    records = run_specs([s[0] for s in specs], jobs=jobs)
    out = []
    for (s, a, b), r in zip(specs, records):
        g = {"a": a, "b": b, "winner": r.winner, "seed": s.seed, "turns": r.turns, "reason": r.reason,
             "drawn_a": sorted(r.cards_drawn_a), "drawn_b": sorted(r.cards_drawn_b)}
        try:
            f = game_facts(load_premade_deck(s.deck_a), load_premade_deck(s.deck_b), s.seed, r.first_player, r.actions)
            g["facts"] = {"first": r.first_player, "ra": round(ratings.get(a, 0)), "rb": round(ratings.get(b, 0)), **f}
        except Exception as e:   # a replay that fails never costs the game its rating
            print(f"facts failed for {a} v {b} seed {s.seed}: {e!r}", flush=True)
        out.append(g)
    return out


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--server", default="https://animal-kingdom.fly.dev")
    ap.add_argument("--key-file", default=None)
    ap.add_argument("--jobs", type=int, default=7)
    ap.add_argument("--batch", type=int, default=64, help="games a pass")
    ap.add_argument("--pace", type=int, default=1200, help="games an hour at most")
    ap.add_argument("--once", action="store_true", help="one pass, then stop")
    ap.add_argument("--log", default="results/league/games.jsonl")
    ap.add_argument("--births", type=int, default=3, help="tinkered children a day at most (0: no tinkering)")
    ap.add_argument("--night", default="23-8", help="hours (local) when every core plays uncapped, 'from-to'; '' for never")
    ap.add_argument("--night-jobs", type=int, default=os.cpu_count() or 8)
    ap.add_argument("--report-hour", type=int, default=6, help="the hour the meta report is built and posted (-1: never)")
    ap.add_argument("--report-now", action="store_true", help="build and post the report on the first pass too")
    args = ap.parse_args(argv)
    key = (Path(args.key_file).read_text().strip() if args.key_file else None) or league_key()
    if not key:
        sys.exit("no league key (AK_LEAGUE_KEY, results/oauth.json or --key-file)")
    os.environ.setdefault("AK_RUST_BOTS", "1")
    log = Path(args.log); log.parent.mkdir(parents=True, exist_ok=True)
    births_log = log.with_name("births.jsonl")
    facts_dir = log.with_name("facts")
    rng = random.Random()
    last_tinker, reported_day = 0.0, ""
    while True:
        started = time.time()
        try:
            pool = api(args.server, "/api/league/pool", key)
        except (urllib.error.URLError, OSError) as e:
            print(f"pool: {e}; retrying in 60 s", flush=True); time.sleep(60); continue
        for d in pool["decks"]:
            if d["slug"] not in PREMADE_DECKS:
                register_deck(d["slug"], d["list"])
        today = time.strftime("%Y-%m-%d", time.localtime(started))
        report.snapshot(pool, log.with_name("snapshots"), today)
        if (args.report_now and not reported_day) or (args.report_hour >= 0 and time.localtime(started).tm_hour == args.report_hour and reported_day != today):
            reported_day = today
            try:
                births = [json.loads(l) for l in births_log.read_text().splitlines() if l.strip()] if births_log.is_file() else []
                rep = report.build(pool, log.with_name("snapshots"), births, tinker.read_log(log), started)
                log.with_name("report.md").write_text(report.to_markdown(rep))
                api(args.server, "/api/league/report", key, {"report": rep})
                print(f"report posted ({rep['games_logged']} games, {len(rep['births'])} births)", flush=True)
            except Exception as e:   # a report never stops the games
                print(f"report failed: {e!r}", flush=True)
        pilots = {level: spec.replace("time_budget=8", "time_budget=0") for level, spec in pool["pilots"].items()}
        games = pick(pool["players"], args.batch, rng)
        if not games:
            print("nothing to play", flush=True)
            if args.once:
                return
            time.sleep(300); continue
        night = is_night(args.night, time.localtime(started).tm_hour)
        results = play(games, pilots, args.night_jobs if night else args.jobs, int(started * 1000) % 10_000_000_000,
                       {p["id"]: p["rating"] for p in pool["players"]})
        with log.open("a") as fh:
            for g in results:
                fh.write(json.dumps({"t": started, **{k: v for k, v in g.items() if k != "facts"}}) + "\n")
        facts_dir.mkdir(exist_ok=True)
        with (facts_dir / f"{today}.jsonl").open("a") as fh:   # the Meta tab's games, one file a day
            for g in results:
                if "facts" in g:
                    fh.write(json.dumps({"t": started, "a": g["a"], "b": g["b"], "winner": g["winner"], "turns": g["turns"],
                                         "reason": g["reason"], **g["facts"]}, separators=(",", ":")) + "\n")
        try:
            ack = api(args.server, "/api/league/games", key, {"games": [{k: v for k, v in g.items() if not k.startswith("drawn_") and k != "facts"} for g in results]})
        except (urllib.error.URLError, OSError) as e:
            print(f"games not posted: {e} (kept in {log})", flush=True); ack = {"rated": 0}
        if args.births and started - last_tinker > 3600:
            last_tinker = started
            try:
                born = [json.loads(l) for l in births_log.read_text().splitlines() if l.strip()] if births_log.is_file() else []
                today = sum(1 for b in born if started - b["t"] < 86400)
                children = tinker.propose(tinker.read_log(log), pool, today, args.births, log=lambda m: print(f"tinker: {m}", flush=True))
                if children:
                    ack2 = api(args.server, "/api/league/decks", key, {"decks": [{k: v for k, v in c.items() if k != "why"} for c in children]})
                    with births_log.open("a") as fh:
                        for c in children:
                            fh.write(json.dumps({"t": started, **c, "added": c["slug"] in ack2.get("added", [])}) + "\n")
                    print(f"tinker: born {ack2.get('added')}, refused {ack2.get('rejected')}", flush=True)
            except Exception as e:   # a tinker pass never stops the games
                print(f"tinker pass failed: {e!r}", flush=True)
        placing = sum(1 for p in pool["players"] if p["games"] < PROVISIONAL)
        print(f"{time.strftime('%H:%M')}{' night' if night else ''} {len(results)} games in {time.time() - started:.0f} s, {ack.get('rated')} rated; "
              f"{len(pool['players'])} pairings, {placing} placing", flush=True)
        if args.once:
            return
        if not night:
            time.sleep(max(0.0, len(results) * 3600 / args.pace - (time.time() - started)))


if __name__ == "__main__":
    main()
