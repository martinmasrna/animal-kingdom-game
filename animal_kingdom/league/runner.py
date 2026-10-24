"""The league runner: the ladder's bots play each other here, by matchmaking, and every result is rated on the web ladder.

    .venv/bin/python -m animal_kingdom.league.runner --server https://animal-kingdom.fly.dev [--jobs 7] [--batch 64] [--pace 1200] [--once]

Each pass asks the server for the pool (`/api/league/pool`: every bot deck's list, every pairing's rating and uncertainty,
the pilots' specs), picks the games a ladder would pick, plays them on the Rust engine (AK_RUST_BOTS=1, the pilots
untimed), posts the results to `/api/league/games`, and appends them to results/league/games.jsonl. Who plays: pairings
still placing first (two games each), then the pairings whose rating is least certain, each against an opponent near its
rating (within the matching window, widened when nobody is there), a fifth of the time against anyone, never itself.
`--pace` caps games an hour so the machine stays usable; the runner sleeps when the pool needs nothing. The league key
comes from AK_LEAGUE_KEY, results/oauth.json (as the server reads it) or --key-file.
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

from ..decks import PREMADE_DECKS, register_deck
from ..sim.runner import MatchSpec, run_specs
from ..web.league import key as league_key
from ..web.ladder import PROVISIONAL, parse_bot

WINDOW = 150          # rating distance a matchmaking opponent is drawn from, doubled until someone is there
ANYONE = 0.2          # share of games against anyone at all, as a ladder's queue mixes
PLACING_GAMES = 2     # games a placing pairing gets each pass


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


def play(games: list[tuple[str, str]], pilots: dict[str, str], jobs: int, seed0: int) -> list[dict]:
    specs = []
    for i, (a, b) in enumerate(games):
        la, da = parse_bot(a); lb, db = parse_bot(b)
        x, y = ((la, da), (lb, db)) if i % 2 == 0 else ((lb, db), (la, da))   # seats alternate
        specs.append((MatchSpec(x[1], y[1], seed0 + i, bot_a=pilots[x[0]], bot_b=pilots[y[0]]), f"bot:{x[0]}:{x[1]}", f"bot:{y[0]}:{y[1]}"))
    records = run_specs([s[0] for s in specs], jobs=jobs)
    return [{"a": a, "b": b, "winner": r.winner, "seed": s.seed, "turns": r.turns, "reason": r.reason}
            for (s, a, b), r in zip(specs, records)]


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--server", default="https://animal-kingdom.fly.dev")
    ap.add_argument("--key-file", default=None)
    ap.add_argument("--jobs", type=int, default=7)
    ap.add_argument("--batch", type=int, default=64, help="games a pass")
    ap.add_argument("--pace", type=int, default=1200, help="games an hour at most")
    ap.add_argument("--once", action="store_true", help="one pass, then stop")
    ap.add_argument("--log", default="results/league/games.jsonl")
    args = ap.parse_args(argv)
    key = (Path(args.key_file).read_text().strip() if args.key_file else None) or league_key()
    if not key:
        sys.exit("no league key (AK_LEAGUE_KEY, results/oauth.json or --key-file)")
    os.environ.setdefault("AK_RUST_BOTS", "1")
    log = Path(args.log); log.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random()
    while True:
        started = time.time()
        try:
            pool = api(args.server, "/api/league/pool", key)
        except (urllib.error.URLError, OSError) as e:
            print(f"pool: {e}; retrying in 60 s", flush=True); time.sleep(60); continue
        for d in pool["decks"]:
            if d["slug"] not in PREMADE_DECKS:
                register_deck(d["slug"], d["list"])
        pilots = {level: spec.replace("time_budget=8", "time_budget=0") for level, spec in pool["pilots"].items()}
        games = pick(pool["players"], args.batch, rng)
        if not games:
            print("nothing to play", flush=True)
            if args.once:
                return
            time.sleep(300); continue
        results = play(games, pilots, args.jobs, int(started * 1000) % 10_000_000_000)
        with log.open("a") as fh:
            for g in results:
                fh.write(json.dumps({"t": started, **g}) + "\n")
        try:
            ack = api(args.server, "/api/league/games", key, {"games": results})
        except (urllib.error.URLError, OSError) as e:
            print(f"games not posted: {e} (kept in {log})", flush=True); ack = {"rated": 0}
        placing = sum(1 for p in pool["players"] if p["games"] < PROVISIONAL)
        print(f"{time.strftime('%H:%M')} {len(results)} games in {time.time() - started:.0f} s, {ack.get('rated')} rated; "
              f"{len(pool['players'])} pairings, {placing} placing", flush=True)
        if args.once:
            return
        time.sleep(max(0.0, len(results) * 3600 / args.pace - (time.time() - started)))


if __name__ == "__main__":
    main()
