"""The league runner: the ladder's bots play each other here, by matchmaking, and every result is rated on the web ladder.

    .venv/bin/python -m animal_kingdom.league.runner --server https://animal-kingdom.fly.dev [--jobs 7] [--batch 64] [--pace 1200] [--once]

Offline first (Martin, 2026-10-27: the games never wait on the internet): the pool and its ratings are kept on disk
(results/league/state.json) and a pass plays from the last copy when the server can't be reached, nudging its own copy's
ratings with each result so matchmaking stays sensible; every game goes to an outbox (results/league/outbox.jsonl) and each
pass sends the outbox, oldest first, until the server acknowledges it. Each game has an id, and the server skips one it has
seen, so a post that arrived but whose answer was lost is never rated twice. The server stays the one rating store.

Each pass asks the server for the pool (`/api/league/pool`: every bot deck's list, every pairing's rating and uncertainty,
the pilots' specs), picks the games a ladder would pick, plays them on the Rust engine (AK_RUST_BOTS=1, the pilots
untimed), posts the results to `/api/league/games`, and appends them to results/league/games.jsonl. Who plays: pairings
still placing first (two games each), then the pairings whose rating is least certain, each against an opponent near its
rating (within the matching window, widened when nobody is there), a fifth of the time against anyone, never itself.
`--pace` caps games an hour so the machine stays usable by day; in the night window (`--night 0-8`) every core plays
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
from concurrent.futures import ProcessPoolExecutor

from ..sim.runner import MatchSpec, _run_spec
from ..web.league import key as league_key
from ..web.ladder import PROVISIONAL, parse_bot
from . import report, tinker
from .facts import game_facts

WINDOW = 150          # rating distance a matchmaking opponent is drawn from, doubled until someone is there
ANYONE = 0.2          # share of games against anyone at all, as a ladder's queue mixes
PLACING_GAMES = 2     # games a placing pairing gets each pass


OUTBOX_CHUNK = 300   # games a post carries
LOCAL_K = 16         # how far a result moves the local copy's ratings while offline (the server's Glicko replaces them)


def load_pool(server: str, key: str, state: Path) -> dict | None:
    """The server's pool, saved to `state`; offline, the last saved copy (None before the first contact)."""
    try:
        pool = api(server, "/api/league/pool", key, timeout=20)
        state.write_text(json.dumps(pool))
        return pool
    except (urllib.error.URLError, OSError, ValueError) as e:
        if state.is_file():
            print(f"pool: {e}; playing from the saved copy", flush=True)
            return json.loads(state.read_text())
        return None


def nudge(pool: dict, results: list[dict], state: Path) -> None:
    """The local copy learns from the pass while the server can't be asked: an Elo step and a game counted per result."""
    players = {p["id"]: p for p in pool["players"]}
    for g in results:
        a, b = players.get(g["a"]), players.get(g["b"])
        if not a or not b or g.get("winner") not in ("A", "B"):
            continue
        e = 1 / (1 + 10 ** ((b["rating"] - a["rating"]) / 400))
        s = 1.0 if g["winner"] == "A" else 0.0
        a["rating"] += LOCAL_K * (s - e); b["rating"] -= LOCAL_K * (s - e)
        a["games"] += 1; b["games"] += 1
    state.write_text(json.dumps(pool))


def send_outbox(server: str, key: str, outbox: Path) -> tuple[int, int]:
    """Post the outbox oldest first, dropping each chunk the server acknowledges; stop at the first failure. (rated, left)."""
    if not outbox.is_file():
        return 0, 0
    lines = [l for l in outbox.read_text().splitlines() if l.strip()]
    rated = 0
    while lines:
        chunk = lines[:OUTBOX_CHUNK]
        try:
            ack = api(server, "/api/league/games", key, {"games": [json.loads(l) for l in chunk]})
        except (urllib.error.URLError, OSError, ValueError) as e:
            print(f"outbox: {e}; {len(lines)} games wait for the connection", flush=True)
            break
        rated += ack.get("rated", 0)
        lines = lines[OUTBOX_CHUNK:]
        outbox.write_text("".join(l + "\n" for l in lines))
    return rated, len(lines)


def is_night(window: str, hour: int) -> bool:
    """Whether `hour` lies in the 'from-to' window (wrapping midnight: '22-6' is 22:00 to 05:59)."""
    if not window:
        return False
    a, b = (int(x) for x in window.split("-"))
    return a <= hour < b if a < b else hour >= a or hour < b


def api(server: str, path: str, key: str, body=None, timeout: int = 60) -> dict:
    req = urllib.request.Request(server.rstrip("/") + path, headers={"X-AK-League-Key": key, "Content-Type": "application/json"},
                                 data=json.dumps(body).encode() if body is not None else None, method="POST" if body is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
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


def round_robin(players: list[dict], rng: random.Random) -> list[tuple[str, str]]:
    """Every pairing of two different decks at the same pilot level, twice (play() alternates the seats), in a shuffled order:
    all the matchups evenly, whatever the ratings (Martin, 2026-10-27: the night's league covers every matchup)."""
    ids = [p["id"] for p in players]
    pairs = [(a, b) for i, a in enumerate(ids) for b in ids[i + 1:] if parse_bot(a)[0] == parse_bot(b)[0] and parse_bot(a)[1] != parse_bot(b)[1]]
    rng.shuffle(pairs)
    return [g for a, b in pairs for g in ((a, b), (a, b))]


def pair_key(a: str, b: str) -> str:
    return "|".join(sorted((parse_bot(a)[1], parse_bot(b)[1])))


def round_robin_until(players: list[dict], target: int, counts: dict, rng: random.Random) -> list[tuple[str, str]]:
    """The round robin, only for the matchups still under `target` games (counts: pair_key -> games played); empty once every
    matchup has them, and the ladder's matchmaking takes over (Martin, 2026-10-27: 50 games a matchup first, then the ladder;
    the games are rated as any other, only the pairing is forced)."""
    return [g for g in round_robin(players, rng) if counts.get(pair_key(*g), 0) < target]


def _safe_run(spec: MatchSpec):
    """One game, or None when the engine raises: a broken game is logged and skipped, never the end of the runner."""
    try:
        return _run_spec(spec)
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException as e:   # a Rust panic is a BaseException, and one escaping the worker killed the whole runner (2026-10-27)
        print(f"game failed: {spec.deck_a} v {spec.deck_b} seed {spec.seed}: {e!r}", flush=True)
        return None


def play(games: list[tuple[str, str]], pilots: dict[str, str], jobs: int, seed0: int, ratings: dict[str, float]) -> list[dict]:
    """The games played, each with its card facts (league/facts.py) and both players' ratings as the game began."""
    specs = []
    for i, (a, b) in enumerate(games):
        la, da = parse_bot(a); lb, db = parse_bot(b)
        x, y = ((la, da), (lb, db)) if i % 2 == 0 else ((lb, db), (la, da))   # seats alternate
        specs.append((MatchSpec(x[1], y[1], seed0 + i, bot_a=pilots[x[0]], bot_b=pilots[y[0]], log_actions=True),
                      f"bot:{x[0]}:{x[1]}", f"bot:{y[0]}:{y[1]}"))
    if jobs <= 1:
        records = [_safe_run(s[0]) for s in specs]
    else:
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            records = list(ex.map(_safe_run, [s[0] for s in specs]))
    out = []
    for (s, a, b), r in zip(specs, records):
        if r is None:
            continue
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
    ap.add_argument("--round-robin", action="store_true", help="every pass plays every same-level pairing twice instead of matchmaking")
    ap.add_argument("--round-robin-games", type=int, default=0, help="round robin until every matchup has this many games, then matchmaking")
    ap.add_argument("--births", type=int, default=3, help="tinkered children a day at most (0: no tinkering)")
    ap.add_argument("--night", default="0-8", help="hours (local) when every core plays uncapped, 'from-to'; '' for never")
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
    state, outbox = log.with_name("state.json"), log.with_name("outbox.jsonl")
    rr_file = log.with_name("rr.json")   # games per matchup, for --round-robin-games
    last_tinker, reported_day = 0.0, ""
    while True:
        started = time.time()
        pool = load_pool(args.server, key, state)
        if pool is None:
            print("pool: no server and no saved copy yet; retrying in 60 s", flush=True); time.sleep(60); continue
        retired_file = log.with_name("retired.json")   # lists Martin retired, kept out here even before the server knows
        if retired_file.is_file():
            out = set(json.loads(retired_file.read_text()))
            if out & {d["slug"] for d in pool["decks"]}:   # the server still offers some: tell it (a server without the call answers 404)
                try:
                    api(args.server, "/api/league/retire", key, {"slugs": sorted(out)})
                except (urllib.error.URLError, OSError):
                    pass
            pool["decks"] = [d for d in pool["decks"] if d["slug"] not in out]
            pool["players"] = [p for p in pool["players"] if parse_bot(p["id"])[1] not in out]
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
        rr = json.loads(rr_file.read_text()) if rr_file.is_file() else {}
        games = (round_robin(pool["players"], rng) if args.round_robin else
                 round_robin_until(pool["players"], args.round_robin_games, rr, rng) if args.round_robin_games else [])
        games = games or pick(pool["players"], args.batch, rng)
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
        with outbox.open("a") as fh:   # every game waits here until the server has it
            for i, g in enumerate(results):
                fh.write(json.dumps({**{k: v for k, v in g.items() if not k.startswith("drawn_")}, "t": started,
                                     "gid": f"{int(started * 1000)}-{i}"}, separators=(",", ":")) + "\n")
        nudge(pool, results, state)
        for g in results:
            rr[pair_key(g["a"], g["b"])] = rr.get(pair_key(g["a"], g["b"]), 0) + 1
        rr_file.write_text(json.dumps(rr, indent=0))
        rated, left = send_outbox(args.server, key, outbox)
        ack = {"rated": rated if not left else f"{rated} ({left} waiting)"}
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
