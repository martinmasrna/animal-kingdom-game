"""Load test for the web server: N simulated players through the public API and the sockets, as a browser drives them.

Each player signs in as a guest, opens the collection (pool, profile), saves a deck, befriends the next player and chats
with them, then plays matches to the end with random legal moves, acknowledging each view as played (as the client does,
so a bot never waits out BOT_WAIT_MAX on a silent screen). The path picks the opponent:

  bot     practice matches against a bot (POST /api/match with `bot`), `--level` picks the pilot
  ranked  the ranked queue (POST /api/ranked): two players searching together meet, else a bot after RANKED_WAIT
  pvp     no bot: player 2k hosts a friend match, 2k+1 joins it by its id, both play random legal moves

Measured, per step of the ramp (`--players 4,8,16`):

  move     a move's ack: the player's act sent -> the first view carrying the events it caused (applied and pushed)
  bot      a bot's turn, end to end: the player's turn ended -> the player's decision again, less the server's own fixed
           pacing (server.BOT_PAUSE per bot action), so what is left is thinking and queueing
  errors   HTTP statuses >= 400 that were not asked for, socket errors, and the server's own logged tracebacks (--serve)

Run against a server started like production (the Dockerfile's command, AK_RUST_BOTS=1), from a copy of the package
in a temp directory so its results/ (profiles, matches, game logs) never land in this checkout. The server's rate limits
exempt its own machine when it is not on Fly, so one machine can play every simulated player:

  .venv/bin/python tools/loadtest.py --serve --path bot --level easy --players 4,8,16,32 --duration 60
  .venv/bin/python tools/loadtest.py --serve --path pvp --players 8,32,64,128 --duration 60
  .venv/bin/python tools/loadtest.py --url http://127.0.0.1:8080 --path ranked --players 16

Prints one table row per step, and `--json FILE` writes every sample. Needs aiohttp (the `web` extra).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import shutil
import socket
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import aiohttp

ROOT = Path(__file__).resolve().parents[1]
PAUSE = {"open": 0.6, "move": 0.4, "choice": 0.3}   # server.BOT_PAUSE: subtracted from a bot turn's wall time
SKIP = "__skip__"


# ----------------------------------------------------------------- the server, started like production
def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def serve(port: int, log_path: Path, cpus: str = "", code: Path = ROOT) -> tuple[subprocess.Popen, Path]:
    """The Dockerfile's command over a copy of `code`'s package (its results/ is the copy's own). Returns (process, tree)."""
    tree = Path(tempfile.mkdtemp(prefix="ak-load-"))
    shutil.copytree(Path(code) / "animal_kingdom", tree / "animal_kingdom",
                    ignore=shutil.ignore_patterns("tests", "node_modules", "__pycache__", "test", "shots"))
    env = {**os.environ, "PYTHONUNBUFFERED": "1", "AK_RUST_BOTS": "1"}
    env.pop("AK_NO_GAME_LOGS", None)
    env.pop("AK_BOT_PAUSE", None)
    pin = ["taskset", "-c", cpus] if cpus else []
    proc = subprocess.Popen(pin + [sys.executable, "-m", "animal_kingdom.web.server", "--host", "127.0.0.1", "--port", str(port), "--no-open"],
                            cwd=tree, env=env, stdout=open(log_path, "w"), stderr=subprocess.STDOUT)
    return proc, tree


async def wait_up(url: str, proc: subprocess.Popen | None, timeout: float = 120) -> None:
    t0 = time.time()
    async with aiohttp.ClientSession() as s:
        while time.time() - t0 < timeout:
            if proc is not None and proc.poll() is not None:
                raise SystemExit("the server exited at startup")
            try:
                async with s.get(url + "/api/pool") as r:
                    if r.status == 200:
                        return
            except aiohttp.ClientError:
                pass
            await asyncio.sleep(0.5)
    raise SystemExit("the server did not come up")


# ----------------------------------------------------------------- one simulated player
class Stats:
    def __init__(self):
        self.move: list[float] = []
        self.bot: list[float] = []
        self.bot_raw: list[float] = []
        self.http: list[float] = []
        self.errors: list[str] = []
        self.refused = 0            # moves the game refused (a random pick the rules don't allow): the player's, not the server's
        self.games = 0
        self.moves = 0

    def err(self, what: str) -> None:
        self.errors.append(what)


def position(v: dict) -> str:
    """What an action changes in a view (a clock's bump changes none of it): the ack of an action is a view where it moved."""
    g = v.get("game") or {}
    return json.dumps([v.get("phase"), g.get("round"), g.get("toAct"), g.get("decision"), g.get("actionsLeft"), g.get("pending"),
                       [u["iid"] for u in g.get("hand", [])], g.get("board"), g.get("food"), len(g.get("history") or [])], sort_keys=True)


class Player:
    def __init__(self, i: int, url: str, http: aiohttp.ClientSession, stats: Stats, args, pool: dict):
        self.i, self.url, self.http, self.stats, self.args, self.pool = i, url, http, stats, args, pool
        self.key = None
        self.pid = None
        self.rng = random.Random(args.seed * 1000 + i)

    async def call(self, method: str, path: str, ok=(200,), **kw):
        headers = {"X-AK-Key": self.key} if self.key else {}
        t0 = time.time()
        try:
            async with self.http.request(method, self.url + path, headers=headers, timeout=aiohttp.ClientTimeout(total=60), **kw) as r:
                body = await r.read()
                self.stats.http.append(time.time() - t0)
                if r.status not in ok:
                    self.stats.err(f"{method} {path.split('?')[0]} -> {r.status} {body[:80]!r}")
                    return None
                return json.loads(body) if body else {}
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            self.stats.err(f"{method} {path.split('?')[0]} -> {type(e).__name__}")
            return None

    def deck(self) -> str:
        return self.rng.choice(self.pool["bot_decks"])

    async def sign_in(self) -> bool:
        r = await self.call("POST", "/api/profile", json={"name": f"Load{self.i}"})
        if not r:
            return False
        self.key, self.pid = r["code"], r["profile"]["id"]
        return True

    async def collection(self) -> None:
        await self.call("GET", "/api/pool")
        me = await self.call("GET", "/api/me")
        lists = self.pool["lists"]
        slug = self.rng.choice(list(lists))
        cards: dict = {}
        for c in lists[slug]:
            cards[c] = cards.get(c, 0) + 1
        decks = (me or {}).get("decks", [])[:19] + [{"id": f"load{self.rng.randrange(10**6)}", "name": "Load deck", "cards": cards}]
        await self.call("PUT", "/api/me/decks", json=decks)

    async def befriend(self, other: "Player") -> None:
        r = await other.call("GET", "/api/friends")
        if r:
            await self.call("POST", "/api/friends", json={"code": r["code"]})

    async def chat(self, other: "Player") -> None:
        if other.pid:
            await self.call("POST", f"/api/chat/{other.pid}", json={"text": f"gg {self.rng.randrange(1000)}"})
            await self.call("GET", f"/api/chat/{other.pid}")

    # --------------------------------------------------------- playing
    def pick(self, g: dict) -> dict | None:
        legal, pending = g.get("legal"), g.get("pending")
        if pending and pending.get("mode") == "choice":
            opts = [o["v"] for o in pending.get("options", [])]
            if pending.get("optional") and (not opts or self.rng.random() < 0.3):
                return {"kind": "choice", "choice": SKIP}
            return {"kind": "choice", "choice": self.rng.choice(opts)} if opts else None
        if not legal:
            return None
        cands = []
        if pending and pending.get("optional"):     # a placement a card offers (mode "place"): its places, or decline
            cands.append({"kind": "choice", "choice": SKIP})
        if legal.get("draw"):
            cands.append({"kind": "draw"})
        for card, targets in legal.get("place", {}).items():
            for t in targets:
                cands.append({"kind": "place", "card_id": card, "target": t})
        for origin, targets in legal.get("roam", {}).items():
            for t in targets:
                cands.append({"kind": "roam", "from": origin, "target": t})
        if g.get("canPass") and (not cands or self.rng.random() < 0.05):
            return {"kind": "pass"}
        return self.rng.choice(cands) if cands else ({"kind": "pass"} if g.get("canPass") else None)

    async def play(self, mid: str, token: str, deadline: float) -> None:
        """One match to its end (or the step's deadline): random legal moves, every view acknowledged as played."""
        try:
            ws = await self.http.ws_connect(f"{self.url}/ws/{mid}?token={token}", heartbeat=20, timeout=30)
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            self.stats.err(f"ws connect -> {type(e).__name__}")
            return
        sent_at = None              # our action in flight: when it was sent (one at a time, as a person clicks)
        sent_seq, sent_pos = 0, None  # the last event we had seen when we sent it: its view brings newer ones
        seen_seq = 0
        their_since = None          # when the decision last left us (a bot's turn began)
        bot_actions = 0             # the bot's top-level moves and choices seen since then
        quiet_since = time.time()
        try:
            while time.time() < deadline + self.args.grace:
                try:
                    msg = await ws.receive(timeout=max(0.5, min(5.0, deadline + self.args.grace - time.time())))
                except asyncio.TimeoutError:
                    if time.time() - quiet_since > self.args.stall:
                        self.stats.err(f"ws: no view for {self.args.stall:.0f}s (a stalled match)")
                        return
                    continue
                quiet_since = time.time()
                if msg.type != aiohttp.WSMsgType.TEXT:
                    if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING, aiohttp.WSMsgType.ERROR):
                        self.stats.err(f"ws closed by the server ({msg.type.name})")
                        return
                    continue
                data = json.loads(msg.data)
                if data.get("t") == "error":
                    self.stats.refused += 1
                    sent_at = None          # refused: the view that follows is the same position, choose again
                    continue
                if data.get("t") != "view":
                    continue
                v = data["view"]
                now = time.time()
                g = v.get("game")
                seq = max((e.get("seq", 0) for e in g["events"]), default=0) if g and g.get("events") else 0
                if g is not None and seq < seen_seq:     # a new game (a rematch) numbers its events afresh
                    seen_seq = sent_seq = 0
                if sent_at is not None and (seq > sent_seq or position(v) != sent_pos):   # the view our action brought
                    self.stats.move.append(now - sent_at)
                    sent_at = None
                if seq > seen_seq:
                    seen_seq = seq
                    await ws.send_json({"t": "played", "seq": seq})
                if v["phase"] in ("match_over", "game_over") or (g and g.get("result")):
                    self.stats.games += 1
                    return
                if not g:
                    continue
                mine = g["decision"] in ("yours", "your_choice", "mulligan") and g["toAct"] == v["you"]
                if not mine:
                    if their_since is None:
                        their_since, bot_actions = now, 0
                    continue
                if their_since is not None and self.args.path != "pvp" and v["seats"].get("B" if v["you"] == "A" else "A", {}).get("bot"):
                    hist = [h for h in g.get("history", []) if h["seat"] != v["you"]]
                    last_round = g["round"] - (1 if g["first"] == v["you"] else 0)
                    bot_actions = max(1, sum(1 for h in hist if h["round"] == last_round))
                    raw = now - their_since
                    self.stats.bot_raw.append(raw)
                    self.stats.bot.append(max(0.0, raw - PAUSE["open"] - PAUSE["move"] * (bot_actions - 1)))
                their_since = None
                if sent_at is not None:     # our last action's view hasn't come yet: this one is a stale copy
                    continue
                await asyncio.sleep(self.rng.uniform(*self.args.think))
                action = self.pick(g)
                if action is None:
                    continue
                sent_seq, sent_pos = seen_seq, position(v)
                sent_at = time.time()
                self.stats.moves += 1
                await ws.send_json({"t": "act", "action": action})
        finally:
            await ws.close()

    async def practice(self, deadline: float) -> None:
        level = self.args.level if self.args.level != "mix" else self.rng.choice(["easy", "normal", "expert"])
        m = await self.call("POST", "/api/match", json={"deck": self.deck(), "bot": {"level": level, "deck": self.deck()}})
        if m:
            await self.play(m["id"], m["token"], deadline)

    async def ranked(self, deadline: float) -> None:
        m = await self.call("POST", "/api/ranked", json={"deck": self.deck()})
        if m and m.get("id"):
            await self.play(m["id"], m["token"], deadline)


async def run_step(url: str, n: int, args, pool: dict) -> Stats:
    stats = Stats()
    conn = aiohttp.TCPConnector(limit=0)
    async with aiohttp.ClientSession(connector=conn) as http:
        players = [Player(i, url, http, stats, args, pool) for i in range(n)]
        await asyncio.gather(*(p.sign_in() for p in players))
        players = [p for p in players if p.key]
        await asyncio.gather(*(p.collection() for p in players))
        for a, b in zip(players[::2], players[1::2]):
            await a.befriend(b)
        await asyncio.gather(*(a.chat(b) for a, b in zip(players[::2], players[1::2])))
        deadline = time.time() + args.duration

        async def loop_bot(p):
            while time.time() < deadline:
                await (p.ranked if args.path == "ranked" else p.practice)(deadline)

        async def loop_pvp(host, guest):
            while time.time() < deadline:
                m = await host.call("POST", "/api/match", json={"deck": host.deck()})
                if not m:
                    await asyncio.sleep(1); continue
                j = await guest.call("POST", f"/api/match/{m['id']}/join", json={"deck": guest.deck()})
                if not j:
                    await asyncio.sleep(1); continue
                await asyncio.gather(host.play(m["id"], m["token"], deadline), guest.play(j["id"], j["token"], deadline))
                await host.chat(guest)

        work = [loop_pvp(a, b) for a, b in zip(players[::2], players[1::2])] if args.path == "pvp" else [loop_bot(p) for p in players]
        try:   # a match that never ends (a stalled server) ends the step anyway, counted
            await asyncio.wait_for(asyncio.gather(*work), args.duration + args.grace + 30)
        except asyncio.TimeoutError:
            stats.err("step: a player still in a match past the grace (a stalled match)")
    return stats


def cpu_seconds(pid: int | None) -> float:
    """User plus system CPU seconds a process (and its threads) has used, from /proc; 0 where there is none."""
    try:
        f = open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()
        return (int(f[11]) + int(f[12])) / os.sysconf("SC_CLK_TCK")
    except (OSError, TypeError, IndexError, ValueError):
        return 0.0


def rss_mb(pid: int | None) -> float:
    try:
        for line in open(f"/proc/{pid}/status"):
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024
    except (OSError, TypeError):
        pass
    return 0.0


def pct(xs: list[float], q: float) -> float:
    if not xs:
        return float("nan")
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))]


def server_errors(log_path: Path, since: int) -> tuple[list[str], int]:
    """New tracebacks and error lines in the server's log since byte `since`."""
    if not log_path or not log_path.exists():
        return [], since
    with open(log_path, "rb") as fh:
        fh.seek(since)
        text = fh.read().decode("utf-8", "replace")
        end = fh.tell()
    lines = [l for l in text.splitlines() if "Traceback" in l or "Error handling request" in l or " ERROR " in l
             or "bot over" in l or "bot failed" in l or "bot task died" in l or "refused" in l]
    return lines, end


async def main_async(args) -> None:
    proc = tree = None
    log_path = None
    url = args.url
    if args.serve:
        port = free_port()
        log_path = Path(args.server_log or tempfile.mktemp(prefix="ak-load-", suffix=".log"))
        proc, tree = serve(port, log_path, args.cpus, Path(args.code))
        url = f"http://127.0.0.1:{port}"
        print(f"server: pid {proc.pid}, {url}, log {log_path}", flush=True)
    try:
        await wait_up(url, proc)
        async with aiohttp.ClientSession() as s:
            async with s.get(url + "/api/pool") as r:
                raw = await r.json()
        decks = [d for d in raw["bot_decks"] if d in {x["id"] for x in raw["bot_only"]} | {x["id"] for x in raw["decks"]}]
        lists = {x["id"]: x["list"] for x in raw["bot_only"] + raw["decks"]}
        pool = {"bot_decks": decks, "lists": lists}
        print(f"path {args.path}, level {args.level}, {args.duration}s a step, think {args.think[0]}-{args.think[1]}s, {os.cpu_count()} cores")
        print(f"{'players':>7} {'moves':>6} {'games':>5} {'move p50':>9} {'p95':>6} {'max':>6} {'bot p50':>8} {'p95':>6} {'max':>6} {'http p95':>8} {'errors':>6} {'server':>6} {'refused':>7} {'srv cpu':>7} {'cli cpu':>7} {'rss MB':>6}")
        since, samples = 0, []
        for n in args.players:
            t0, c0, k0 = time.time(), cpu_seconds(proc and proc.pid), cpu_seconds(os.getpid())
            stats = await run_step(url, n, args, pool)
            wall = time.time() - t0
            srv_cpu, cli_cpu = (cpu_seconds(proc and proc.pid) - c0) / wall, (cpu_seconds(os.getpid()) - k0) / wall   # in cores
            srv, since = server_errors(log_path, since)
            print(f"{n:>7} {stats.moves:>6} {stats.games:>5} {pct(stats.move, .5):>9.3f} {pct(stats.move, .95):>6.2f} "
                  f"{max(stats.move or [float('nan')]):>6.2f} {pct(stats.bot, .5):>8.2f} {pct(stats.bot, .95):>6.2f} "
                  f"{max(stats.bot or [float('nan')]):>6.2f} {pct(stats.http, .95):>8.3f} {len(stats.errors):>6} {len(srv):>6} {stats.refused:>7} {srv_cpu:>7.2f} {cli_cpu:>7.2f} {rss_mb(proc and proc.pid):>6.0f}", flush=True)
            for e in sorted(set(stats.errors))[:8]:
                print(f"        client: {e} (x{stats.errors.count(e)})")
            for e in sorted(set(srv))[:8]:
                print(f"        server: {e[:160]} (x{srv.count(e)})")
            samples.append({"players": n, "seconds": time.time() - t0, "move": stats.move, "bot": stats.bot, "bot_raw": stats.bot_raw,
                            "http": stats.http, "errors": stats.errors, "server": srv, "games": stats.games, "moves": stats.moves, "refused": stats.refused,
                            "server_cores": srv_cpu, "client_cores": cli_cpu, "server_rss_mb": rss_mb(proc and proc.pid)})
            if proc is not None and proc.poll() is not None:
                print("the server died"); break
            if args.stop_on and pct(stats.bot if args.path != "pvp" else stats.move, .5) > args.stop_on:
                print(f"median latency past {args.stop_on}s: stopping the ramp"); break
        if args.json:
            Path(args.json).write_text(json.dumps({"args": vars(args), "steps": samples}))
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(10)
            except subprocess.TimeoutExpired:
                proc.kill()
            shutil.rmtree(tree, ignore_errors=True)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--url", default="http://127.0.0.1:8080")
    p.add_argument("--serve", action="store_true", help="start a server like production (a temp copy of the package)")
    p.add_argument("--code", default=str(ROOT), help="--serve runs the package of this checkout (another branch's, to compare)")
    p.add_argument("--cpus", default="", help="--serve pins the server to these cores (taskset), e.g. 0 for one core as on Fly")
    p.add_argument("--server-log", help="where --serve writes the server's log")
    p.add_argument("--path", choices=["bot", "ranked", "pvp"], default="bot")
    p.add_argument("--level", default="easy", help="the practice bot: easy, normal, expert or mix")
    p.add_argument("--players", default="4,8,16", help="the ramp, comma-separated")
    p.add_argument("--duration", type=float, default=60, help="seconds each step plays (a match under way finishes in --grace)")
    p.add_argument("--grace", type=float, default=30)
    p.add_argument("--stall", type=float, default=60, help="seconds with no message on a match socket that count as a stalled match")
    p.add_argument("--think", default="0.3,1.0", help="a player's thinking time per move, min,max seconds")
    p.add_argument("--stop-on", type=float, default=0, help="stop the ramp once the median latency passes this")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--json", help="write every sample here")
    args = p.parse_args(argv)
    args.players = [int(x) for x in args.players.split(",")]
    args.think = tuple(float(x) for x in args.think.split(","))
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
