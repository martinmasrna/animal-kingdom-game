"""The web server: static client, a small JSON API to create and join matches, and one
WebSocket per player that pushes that seat's view after every change.

Run: `./play` (or `python -m animal_kingdom.web.server --port 8000`). Every match is saved to
`results/web_matches/` after each change and reloaded on start, so a restart doesn't end it.
"""

from __future__ import annotations

import argparse
import asyncio
import gzip
import json
import logging
import os
import random
import secrets
import subprocess
import threading
import time
import webbrowser
from collections import Counter
from pathlib import Path

from aiohttp import WSMsgType, web

from ..decks import BOT_DECKS, PREMADE_DECKS, TEST_BOT_DECKS, load_premade_deck
from ..engine import rules
from ..engine.state import EngineError
from ..engine.cards import COPY_LIMITS, DECK_SLUGS, STARTER_DECKS, load_cards
from . import custom_decks
from .renamed import RENAMED_IDS, renamed as _renamed
from . import events, feedback, guard, news
from .chat import Chat, ChatError
from .friends import FriendError, Friends
from . import ladder as ranking
from . import tiers as tiers_mod
from . import league as league_mod
from . import meta as meta_mod
from . import oauth
from .profiles import ProfileError, Profiles, clean_name
from . import local
from . import replay
from . import tutorial
from .match import BOT_LEVELS, DECK_NAMES, MAP_ID, STARTER_COVERS, Match, Seat, card_pool, map_info
from . import discord

CARDS = load_cards()

STATIC = Path(__file__).parent / "static"
# The client this server serves, as one fingerprint: its files and the card data. A tab left open across a deploy keeps
# running the old client (the page never reloads by itself), so the sockets tell every tab, and one on another build
# reloads (Martin, 2026-10-02: the Spikes badge never showed in a tab opened before it shipped).
def _build_id() -> str:
    import hashlib
    h = hashlib.sha1()
    for f in sorted(STATIC.rglob("*")) + [Path(__file__).resolve().parents[1] / "data" / "cards.json"]:
        if f.is_file() and f.suffix in (".js", ".css", ".html", ".json"):
            h.update(f.name.encode()); h.update(f.read_bytes())
    return h.hexdigest()[:12]
BUILD = _build_id()
# Human games are the best design signal there is: every game with a human seat is kept,
# one JSONL file per match, replayable with `python -m animal_kingdom.sim.replay FILE --index N`.
LOG_DIR = Path(__file__).resolve().parents[2] / "results" / "human_games" / "web"
REPLAY_DIR = Path(__file__).resolve().parents[2] / "results" / "replays"
MATCH_DIR = Path(__file__).resolve().parents[2] / "results" / "web_matches"
KEEP_FINISHED = 24 * 3600    # seconds a finished match is still reloaded after a restart
FORGET_FINISHED = 600        # seconds a finished match, untouched and unwatched, stays in memory (its file stays; Hub.get reloads it)
ARCHIVE_AFTER = 7 * 24 * 3600   # seconds untouched after which a match file moves to MATCH_DIR/archive at start, never reloaded (Martin, 2026-11-05)
FORGET_IDLE = 3600           # the same for an unfinished one: REJOIN_WITHIN, after which nobody is taken back to it
BOT_PAUSE = {"open": 0.6, "move": 0.4, "choice": 0.3}   # seconds: the bot's thinking beat, once the players have watched its last move
BOT_WAIT_MAX = 6.0          # seconds a bot waits for a player's screen to play its last move out (a stalled client never stalls it)
if os.environ.get("AK_BOT_PAUSE") is not None:   # the test harness sets 0: tests wait on nothing a player needs to follow
    BOT_PAUSE = {k: v * float(os.environ["AK_BOT_PAUSE"]) for k, v in BOT_PAUSE.items()}
log = logging.getLogger("animal_kingdom.web")


def _commit() -> str:
    """The commit the server runs, for the game logs: a log replays only under the rules it was played with, and a day of
    card and rule changes left 32 of 140 games of 2026-10-30 unreplayable at the next day's HEAD. Empty where there is no git
    (the deployed image)."""
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=Path(__file__).resolve().parent, capture_output=True,
                              text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


COMMIT = _commit()


def save_game(match: Match, record: dict) -> None:
    if os.environ.get("AK_NO_GAME_LOGS") or all(seat.is_bot for seat in match.seats.values()):
        return
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        stamp = match.created.strftime("%Y%m%dT%H%M%S")
        with open(LOG_DIR / f"web_{stamp}_{match.id}.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps({**record, **({"commit": COMMIT} if COMMIT else {})}) + "\n")
    except OSError:
        log.exception("could not save the game log for match %s", match.id)


SEND_TIMEOUT = 5.0          # seconds a socket may take to accept one message before it is dropped (Hub._send)
BOT_THINK_MAX = 45          # seconds one bot search may take before the Easy bot's move is played for it (the Expert's whole turn has 30 s, match.py)


BOT_THREADS = 4             # bot searches running at once, server-wide (the Expert takes a core each; the live machine has one)
BOT_STUCK_MAX = 8           # searches abandoned past BOT_THINK_MAX and still running; beyond it a bot plays the fallback until some end


class PoolFull(Exception):
    """Too many abandoned searches still running: the move is the fallback's."""


class BotPool:
    """Bot searches off the event loop: at most `size` at once, and one at a time per person (the profile facing the bot),
    so one person opening many Expert matches shares one search with nobody else's. Each runs in a daemon thread of its
    own. A search past its timeout is abandoned: its slot and the person's turn go to the next, and the thread runs out
    on its own (Python can't stop it); with `stuck_max` of those still running, no new search starts."""

    def __init__(self, size: int = BOT_THREADS, stuck_max: int = BOT_STUCK_MAX):
        self.size, self.stuck_max = size, stuck_max
        self.sem: asyncio.Semaphore | None = None
        self.locks: dict[str, asyncio.Lock] = {}
        self.stuck: set[threading.Thread] = set()

    def stuck_running(self) -> int:
        self.stuck = {t for t in self.stuck if t.is_alive()}
        return len(self.stuck)

    async def run(self, key: str, fn, timeout: float):
        if self.sem is None:
            self.sem = asyncio.Semaphore(self.size)
        lock = self.locks.setdefault(key, asyncio.Lock())
        try:
            async with lock, self.sem:
                if self.stuck_running() >= self.stuck_max:
                    raise PoolFull()
                loop, fut = asyncio.get_running_loop(), None
                fut = loop.create_future()

                def done(result, error):
                    if not fut.done():
                        fut.set_exception(error) if error is not None else fut.set_result(result)

                def work():
                    try:
                        result, error = fn(), None
                    except BaseException as e:   # noqa: BLE001 — handed to the awaiting coroutine
                        result, error = None, e
                    try:
                        loop.call_soon_threadsafe(done, result, error)
                    except RuntimeError:          # the loop is gone (the server stopped)
                        pass

                t = threading.Thread(target=work, daemon=True, name=f"bot {key}")
                t.start()
                try:
                    return await asyncio.wait_for(asyncio.shield(fut), timeout)
                except asyncio.TimeoutError:
                    self.stuck.add(t)
                    raise
        finally:
            if not lock.locked() and not lock._waiters:   # noqa: SLF001 — drop idle locks so the table doesn't grow
                self.locks.pop(key, None)


bot_pool = BotPool()


class Hub:
    def __init__(self):
        self.matches: dict[str, Match] = {}
        self.sockets: dict[str, set] = {}        # match id -> {(ws, seat)}
        self.bot_tasks: dict[str, asyncio.Task] = {}
        self.noted: dict[str, tuple] = {}        # match id -> (phase, games ended) as last recorded (note)
        self.clock_tasks: dict[str, asyncio.Task] = {}
        self.touched: dict[str, float] = {}      # match id -> when it last changed (saved)

    def new_id(self) -> str:
        while True:
            mid = secrets.token_urlsafe(4).replace("-", "x").replace("_", "y")[:6].upper()
            if mid not in self.matches:
                return mid

    def save(self, match: Match) -> None:
        """Write the match to disk (atomically), so a server restart can resume it."""
        if os.environ.get("AK_NO_GAME_LOGS"):
            return
        try:
            MATCH_DIR.mkdir(parents=True, exist_ok=True)
            tmp = MATCH_DIR / f".{match.id}.json.tmp"
            tmp.write_text(json.dumps(match.to_dict()), encoding="utf-8")
            tmp.replace(MATCH_DIR / f"{match.id}.json")
            self.touched[match.id] = time.time()
        except Exception:
            log.exception("could not save match %s", match.id)

    def _reload(self, path: Path) -> Match | None:
        """A saved match back in memory: any unfinished one, a finished one from the last day."""
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
            if d["phase"] == "match_over" and time.time() - path.stat().st_mtime > KEEP_FINISHED:
                return None
            match = Match.from_dict(_renamed(d))
        except Exception:
            log.exception("could not reload %s", path.name)
            return None
        if not match.takeover:
            match.on_game_end = save_game
            match.on_match_end = record_match
        self.matches[match.id] = match
        self.touched[match.id] = time.time()
        return match

    def load(self, now: float | None = None) -> None:
        """Reload saved matches: every unfinished one, and finished ones from the last day. A file untouched for
        ARCHIVE_AFTER (an abandoned lobby or bot game: nobody is taken back to one after the hour) moves to the archive
        folder instead, so the folder and the start stop growing with every match ever made."""
        if not MATCH_DIR.is_dir():
            return
        now = time.time() if now is None else now
        archived = 0
        for path in MATCH_DIR.glob("*.json"):
            try:
                if now - path.stat().st_mtime > ARCHIVE_AFTER:
                    (MATCH_DIR / "archive").mkdir(exist_ok=True)
                    path.replace(MATCH_DIR / "archive" / path.name)
                    archived += 1
                    continue
            except OSError:
                log.exception("could not archive %s", path.name)
            self._reload(path)
        log.info("reloaded %d saved matches, archived %d", len(self.matches), archived)

    def get(self, mid: str) -> Match | None:
        """The match with this id: in memory, or reloaded from its file when forget() let it go."""
        match = self.matches.get(mid)
        if match is None and mid.isalnum() and not os.environ.get("AK_NO_GAME_LOGS") and (MATCH_DIR / f"{mid}.json").is_file():
            match = self._reload(MATCH_DIR / f"{mid}.json")
            if match is not None:
                self.kick_bot(match)
        return match

    def forget(self, now: float | None = None) -> int:
        """Let go of the matches nobody is in: finished ones after FORGET_FINISHED, unfinished after FORGET_IDLE, never
        one with a socket open or a bot or clock task running. Each is on disk (saved on every change), so get() brings
        it back; a server keeping no files (AK_NO_GAME_LOGS) keeps everything. A finished match holds about half a MB, and
        nothing else ever freed one (2026-11-05: 1.7 GB after an 8-minute load test, on a 2 GB machine)."""
        if os.environ.get("AK_NO_GAME_LOGS"):
            return 0
        now = time.time() if now is None else now
        busy = lambda tasks, mid: (t := tasks.get(mid)) is not None and not t.done()
        gone = [mid for mid, m in self.matches.items()
                if not self.sockets.get(mid) and not busy(self.bot_tasks, mid) and not busy(self.clock_tasks, mid)
                and now - self.touched.get(mid, now) > (FORGET_FINISHED if m.phase == "match_over" else FORGET_IDLE)]
        for mid in gone:
            for table in (self.matches, self.sockets, self.bot_tasks, self.clock_tasks, self.touched):
                table.pop(mid, None)
        return len(gone)

    async def broadcast(self, match: Match) -> None:
        self.save(match)
        try:
            self.note(match)
        except Exception:
            log.exception("could not note match %s", match.id)
        conns = list(self.sockets.get(match.id, ()))
        views = [{"t": "view", "view": match.view(seat)} for _, seat in conns]   # all from the same position
        await asyncio.gather(*(self._send(match.id, ws, seat, v) for (ws, seat), v in zip(conns, views)))

    async def _send(self, mid: str, ws, seat: str, msg: dict) -> None:
        """One view to one socket, within SEND_TIMEOUT: a screen that stopped reading (a phone gone off the network without
        closing, a stalled tab) is dropped, so it never holds up the match, its opponent's socket or the bot."""
        try:
            await asyncio.wait_for(ws.send_json(msg), SEND_TIMEOUT)
        except Exception as e:
            log.info("dropping a socket of match %s seat %s: %r", mid, seat, e)
            self.sockets.get(mid, set()).discard((ws, seat))
            asyncio.ensure_future(_close_quietly(ws))

    def note(self, match: Match) -> None:
        """Every game's start and end, for each person in it (web/events.py). Every change passes through broadcast,
        so a game ended by a bot or the clock is seen too."""
        now = (match.phase, len(match.results))
        was = self.noted.get(match.id)
        self.noted[match.id] = now
        if now == was:
            return
        people = [(p, s) for p, s in match.seats.items() if not s.is_bot and s.profile]
        lesson = match.lesson() if match.tutorial else 0
        if match.phase == "playing" and (was is None or was[0] != "playing"):
            for p, s in people:
                opp = match.seats.get("B" if p == "A" else "A")
                events.record(profiles.db, s.profile, "game_start", {
                    "match": match.id, "game": len(match.results) + 1, "lesson": lesson, "deck": s.deck,
                    "opp": opp and (f"bot:{opp.bot}" if opp.is_bot else "person"), "opp_deck": opp and opp.deck,
                    "ranked": bool(s.ladder)})
        if len(match.results) > (was[1] if was else 0):
            r = match.results[-1]
            for p, s in people:
                events.record(profiles.db, s.profile, "game_end", {
                    "match": match.id, "game": len(match.results), "lesson": lesson, "won": r["winner"] == p,
                    "reason": r["reason"], "rounds": r["turns"]})
                if r["winner"] == p:   # a line for the Discord channel, when it is one worth a line (web/discord.py)
                    opp = match.seats.get("B" if p == "A" else "A")
                    deck = lambda q: DECK_NAMES.get(q.deck, "their own deck") if q else ""
                    text = discord.result_text(s.name, opp.name if opp else "", deck(s), deck(opp), opp.bot if opp and opp.is_bot else None, lesson)
                    if text:
                        asyncio.get_running_loop().run_in_executor(None, discord.post, "events", text)

    async def push(self, match: Match) -> None:
        await self.broadcast(match)
        self.kick_bot(match)

    def kick_clock(self, match: Match) -> None:
        """Keep a timer running while a clocked game is on; it acts for a player out of time."""
        task = self.clock_tasks.get(match.id)
        if match.clock_deadline() is not None and (task is None or task.done()):
            self.clock_tasks[match.id] = asyncio.create_task(self._run_clock(match))

    async def _run_clock(self, match: Match) -> None:
        while (deadline := match.clock_deadline()) is not None:
            await asyncio.sleep(min(1.0, max(0.05, deadline - time.time())))
            try:
                if match.time_out():
                    await self.broadcast(match)
            except EngineError:
                log.exception("clock failed in match %s", match.id)
                return

    def kick_bot(self, match: Match) -> None:
        self.kick_clock(match)
        s = match.to_act()
        if s is None or not match.seats[s].is_bot:
            return
        task = self.bot_tasks.get(match.id)
        if task is None or task.done():
            self.bot_tasks[match.id] = task = asyncio.create_task(self._run_bot(match))
            task.add_done_callback(lambda t: t.cancelled() or t.exception() is None or log.error("bot task died in match %s: %r", match.id, t.exception()))

    async def _watched(self, match: Match) -> None:
        """Until every person watching has played the match's events out on screen (their client says so, 'played'), at
        most BOT_WAIT_MAX: the bot moves as fast as they can follow, never on a guessed pause."""
        t0 = time.time()
        while time.time() - t0 < BOT_WAIT_MAX:
            watchers = {seat for _, seat in self.sockets.get(match.id, ()) if not match.seats[seat].is_bot}
            if all(match.played.get(w, 0) >= match.seq for w in watchers):
                return
            await asyncio.sleep(0.05)

    async def _run_bot(self, match: Match) -> None:
        failures = 0
        while (s := match.to_act()) is not None and match.seats[s].is_bot:
            opening = not match.state.pending and match.state.actions_taken_this_turn == 0
            await self._watched(match)
            await asyncio.sleep(BOT_PAUSE["choice" if match.state.pending else "open" if opening else "move"])
            while match.hold:                 # the tutorial's coach is talking: the opponent waits for its Next (the client
                await asyncio.sleep(0.1)      # lets go only once what Next set off has played)
            version = match.version
            person = next((x.profile for x in match.seats.values() if not x.is_bot and x.profile), None)
            try:
                action = await bot_pool.run(person or f"match {match.id}", match.bot_move, BOT_THINK_MAX)
            except asyncio.TimeoutError:   # never a hanging opponent (feedback 2026-10-01: an Expert move took 4 minutes on a throttled CPU)
                log.warning("bot over %ss in match %s; playing a fallback move, and a fresh bot from here", BOT_THINK_MAX, match.id)
                match.fresh_bot(s)         # the abandoned search still holds the old one
                action = match.fallback_move()
            except PoolFull:
                log.error("%d abandoned bot searches still running; match %s plays a fallback move", bot_pool.stuck_running(), match.id)
                action = match.fallback_move()
            except Exception:   # nor a frozen match when a bot fails: a plain legal move instead
                log.exception("bot failed in match %s; playing a fallback move", match.id)
                action = match.fallback_move()
            if match.version != version:     # the position moved under the bot (rematch etc.)
                continue
            try:
                match.act(s, action)
            except Exception:   # the move was refused (feedback 2026-10-01: a bot that never moved, only conceding got out): the
                log.exception("bot move refused in match %s; playing a fallback move", match.id)   # plain move, then the first legal one
                failures += 1
                if match.version == version and match.to_act() == s:
                    try:
                        match.act(s, match.fallback_move() if failures == 1 else rules.legal_actions(match.state)[0])
                    except Exception:
                        log.exception("fallback refused too in match %s", match.id)
                        if failures >= 3:    # the position itself is broken: say so loudly and stop hammering it
                            log.error("bot gives up in match %s after %d refused moves", match.id, failures)
                            return
                        await asyncio.sleep(1)
                        continue
            failures = 0
            await self.broadcast(match)


_background: set = set()      # tasks the server keeps running (a reference, so none is collected)


async def _close_quietly(ws) -> None:
    try:
        await asyncio.wait_for(ws.close(), SEND_TIMEOUT)
    except Exception:
        pass


hub = Hub()
profiles: Profiles = None         # opened at startup (make_app), so importing the module touches no files


# ----------------------------------------------------------------- profiles
def profile_of(req) -> dict | None:
    code = req.headers.get("X-AK-Key")
    return profiles.by_code(code) if code else None


def me(req) -> dict:
    p = profile_of(req)
    if p is None:
        raise web.HTTPUnauthorized(text="unknown sign-in code")
    return p


def display(p: dict) -> str:
    return f"{p['name']}#{p['tag']}"


# A profile starts with the starter decks as its own (their covers, as on the play screen, from decklists.json).
def starter_decks() -> list[dict]:
    return [{"id": d["slug"], "name": d["name"], "cards": dict(d["cards"]), "cover": d.get("cover", "")} for d in STARTER_DECKS]


def starter_cards() -> dict[str, dict]:
    """Every starter's id -> its current {card id: copies}, for resolving a profile's unedited copies."""
    return {d["id"]: d["cards"] for d in starter_decks()}





COPY_LIMIT = {cid: COPY_LIMITS[c.rarity] for cid, c in CARDS.items()}   # any deck may hold the rarity's full count (decks.py)
# The cards a player's deck can hold: the starter decks' and the bench's (not the reserve's, the tutorial's or tokens).
COLLECTIBLE = {cid for cid, c in CARDS.items() if c.collectible}


def profile_view(p: dict) -> dict:
    starters = starter_decks()
    profiles.seed_decks(p["id"], starters, COLLECTIBLE, RENAMED_IDS, COPY_LIMIT)
    return {**p, "decks": profiles.decks(p["id"], {d["id"]: d["cards"] for d in starters}),
            "history": [{**h, **{k: _renamed(h[k]) for k in ("my_cover", "opp_cover") if h.get(k)}} for h in profiles.history(p["id"])],
            "records": profiles.records(p["id"]),
            "logins": profiles.identities(p["id"]), "providers": oauth.available(),
            "rating": ladder.get(p["id"]).shown() if ladder else None, **standing(p["id"])}


def league_of(pid: str) -> dict | None:
    """A person's league as the client shows it (web/tiers.py): its name, the stars as a count, the checkpoint, the
    streak; in the top league the rating instead of stars (docs/ranked-leagues.md)."""
    if not tiers:
        return None
    return tiers_mod.view(tiers.get(pid), ladder.get(pid).shown())


def person_key(lid: str, r: ranking.Rating) -> float:
    """Where a person sorts among the bots on the one leaderboard: by league and stars below the top, by rating in it."""
    return tiers_mod.sort_key(tiers.get(lid), r.rating) if tiers else r.rating


def pilot_for(band: str, deck: str) -> str:
    """Practice's bot (Martin, 2026-10-20): the player picks one of the five bots (ranking.BANDS) and a deck; the pilot is the
    one whose ladder rating with that deck sits nearest the band's middle. A deck without ladder rows gets the pilot by name."""
    rows = ladder.bots() if ladder else {}
    ids = {level: ranking.bot_id(level, deck) for level in ranking.LEVELS}
    if all(lid in rows for lid in ids.values()):
        centre = ranking.band_centre(band)
        return min(ranking.LEVELS, key=lambda level: abs(rows[ids[level]].rating - centre))
    return next(level for level, b in ranking.PILOT_BAND.items() if b == band) if band in ranking.PILOT_BAND.values() \
        else ("easy" if ranking.BANDS.index(band) < 2 else "expert")


def bot_seat_name(level: str, deck: str) -> str:
    """What a practice bot is called: its band ("Expert Bot"), by its rating with the deck when the ladder has it."""
    lid = ranking.bot_id(level, deck)
    band = ranking.rung_of(ladder.bots()[lid].rating) if ladder and lid in ladder.bots() else ranking.PILOT_BAND[level]
    return f"{band} Bot"


def bot_band(seat) -> str:
    """The band a bot seat was shown under ("Beginner Bot", "Fish (Expert Bot)"), for the match history: the player picked
    a band, never saw the engine's pilot ("Easy"). A seat named otherwise falls back to its pilot's band."""
    words = seat.name.rstrip(")").split()
    return words[-2] if len(words) >= 2 and words[-1] == "Bot" and words[-2] in ranking.BANDS else ranking.PILOT_BAND.get(seat.bot, seat.bot.capitalize())


def bot_rows(table) -> list[tuple[str, ranking.Rating]]:
    """The bots the leaderboard lists: one row per pilot-and-deck pairing on a deck still in the pool (Martin, 2026-10-24:
    every pairing is a player of its own on the ladder; a retired deck's rows keep their games but are not listed). A
    league newcomer still placing is listed with its '?', as a person placing is not: people see what they may meet."""
    pool_ = set(ladder.decks) if ladder else set(BOT_DECKS)
    return [(lid, r) for lid, r in table if (b := ranking.parse_bot(lid)) and b[1] in pool_]


def standing(pid: str) -> dict:
    """Where you stand, for home's name piece: your league (docs/ranked-leagues.md), and once you have played a rated game
    your place on the leaderboard (people and bots, sorted as the leaderboard sorts them)."""
    if not ladder:
        return {}
    r = ladder.get(pid)
    out = {"league": league_of(pid)} if tiers else {}
    if r.games <= 0:
        return out
    table = ladder.table()
    me_ = person_key(pid, r)
    above = sum(1 for lid, x in table if not lid.startswith("bot:") and lid != pid and person_key(lid, x) > me_)
    return {**out, "rank": 1 + above + sum(1 for _, x in bot_rows(table) if x.rating > me_)}


# ----------------------------------------------------------------- sign in with Google / Discord
flow = oauth.Flow()


def base_url(req) -> str:
    """The site's own address for absolute links: AK_BASE_URL, else on Fly the app's own name, never the request's Host
    (a client sets that); only a local server takes it from the request."""
    if os.environ.get("AK_BASE_URL"):
        return os.environ["AK_BASE_URL"].rstrip("/")
    if guard.on_fly():
        return f"https://{os.environ['FLY_APP_NAME']}.fly.dev"
    return f"{req.headers.get('X-Forwarded-Proto', req.scheme)}://{req.host}"


def callback_url(req, provider: str) -> str:
    base = base_url(req)
    return f"{base}/auth/{provider}/callback"


SIGNIN_COOKIE = "ak_signin"   # the sign-in's `state`, in the browser that started it: the callback must come back with it


async def auth_start(req):
    provider, player = req.match_info["provider"], profile_of(req)
    try:
        url = flow.start(provider, player and player["id"], callback_url(req, provider))
    except oauth.OAuthError as e:
        raise web.HTTPBadRequest(text=str(e))
    resp = web.json_response({"url": url})
    # Tied to this browser, so nobody can start a sign-in from their own guest and have someone else finish it (their
    # Google account would land on the attacker's guest). Lax: sent on the provider's top-level redirect back.
    resp.set_cookie(SIGNIN_COOKIE, oauth.URL(url).query.get("state", ""), max_age=int(oauth.PENDING_TTL), path="/auth/",
                    httponly=True, samesite="Lax", secure=req.headers.get("X-Forwarded-Proto", req.scheme) == "https")
    return resp


async def auth_callback(req):
    provider = req.match_info["provider"]
    try:
        if "code" not in req.query:
            raise oauth.OAuthError(req.query.get("error", "sign-in cancelled"))
        state = req.query.get("state", "")
        if not state or not secrets.compare_digest(state.encode(), req.cookies.get(SIGNIN_COOKIE, "").encode()):
            raise oauth.OAuthError("the sign-in wasn't started in this browser")
        guest = flow.claim(provider, state)
        subject, label = await oauth.identify(provider, req.query["code"], callback_url(req, provider))
        p = profiles.sign_in(provider, subject, label, guest)
        redirect = web.HTTPFound(f"/#/auth/{flow.hand_off(profiles.new_session(p['id']))}")
    except oauth.OAuthError as e:
        log.info("sign-in with %s failed: %s", provider, e)
        redirect = web.HTTPFound("/#/auth/failed")
    redirect.del_cookie(SIGNIN_COOKIE, path="/auth/")
    raise redirect


async def auth_redeem(req):
    guard.limit_ip(req, "signin")
    key = flow.redeem(str((await guard.body(req)).get("code") or ""))
    p = profiles.by_code(key) if key else None
    if p is None:
        raise web.HTTPNotFound(text="that sign-in expired, try again")
    return web.json_response({"key": key, "profile": profile_view(p)})


async def sign_out(req):
    code = req.headers.get("X-AK-Key")
    if code:
        profiles.end_session(code)
    return web.json_response({})


async def create_profile(req):
    guard.limit_ip(req, "profile")
    body = await guard.body(req)
    try:
        code, p = profiles.create(body.get("name") or "Player")
        events.record(profiles.db, p["id"], "profile_created", {"agent": req.headers.get("User-Agent", "")[:200]})
        if body.get("decks"):
            profiles.save_decks(p["id"], body["decks"], starter_cards())
    except ProfileError as e:
        raise web.HTTPBadRequest(text=str(e))
    return web.json_response({"code": code, "profile": profile_view(p)})


async def get_me(req):
    return web.json_response(profile_view(me(req)))


async def patch_me(req):
    body = await guard.body(req)
    try:
        p = profiles.rename(me(req)["id"], body.get("name"))
    except ProfileError as e:
        raise web.HTTPBadRequest(text=str(e))
    return web.json_response(profile_view(p))


async def put_decks(req):
    try:
        decks = profiles.save_decks(me(req)["id"], await guard.body(req, list), starter_cards())
    except ProfileError as e:
        raise web.HTTPBadRequest(text=str(e))
    return web.json_response(decks)


async def sign_in(req):
    guard.limit_ip(req, "signin")
    body = await guard.body(req)
    p = profiles.by_code(str(body.get("code") or ""))
    if p is None:
        raise web.HTTPNotFound(text="no profile has that sign-in code")
    return web.json_response(profile_view(p))


def deck_cover(seat: Seat) -> str:
    """The card a seat's deck shows as its face: a starter's cover, the cover its owner chose, else its first legendary."""
    if seat.deck in STARTER_COVERS:
        return STARTER_COVERS[seat.deck]
    cards = Counter(load_premade_deck(seat.deck))
    if seat.profile:
        for d in profiles.decks(seat.profile, starter_cards()):
            if d.get("cover") and Counter(d["cards"]) == cards:
                return d["cover"]
    return next((c for c in cards if CARDS[c].rarity == "legendary"), next(iter(cards), ""))


def record_match(match: Match) -> None:
    """Add a finished match to each human player's history (the gauntlet, a developer's tool, stays out of it), and
    rate it when it was ranked."""
    if match.schedule:
        return
    try:
        rate_match(match)
    except Exception:
        log.exception("could not rate match %s", match.id)
    kind = "gauntlet" if match.schedule else "bot" if any(s.is_bot for s in match.seats.values()) else "friend"
    mode = "ranked" if all(s.ladder for s in match.seats.values()) else "practice" if kind == "bot" else "friendly"
    rotating = match.schedule[0].get("seat", "B") if match.schedule else None
    score = match.score()
    for p, seat in match.seats.items():
        if not seat.profile or seat.is_bot:
            continue
        o = "B" if p == "A" else "A"
        other = match.seats[o]
        deck = lambda q: "Starter decks" if q == rotating else DECK_NAMES.get(match.seats[q].deck, match.seats[q].deck)
        try:
            profiles.record(seat.profile, f"{match.id}-{match.rematches}", kind=kind, my_deck=deck(p),
                            opp=f"Bot ({bot_band(other)})" if other.is_bot else other.name,
                            opp_deck=deck(o) if other.is_bot else "", won=score[p], lost=score[o], seat=p,   # a person's deck name is theirs
                            my_cover="" if p == rotating else deck_cover(seat), opp_cover="" if o == rotating else deck_cover(other), mode=mode)
        except Exception:
            log.exception("could not record match %s in a history", match.id)
            continue
        if os.environ.get("AK_NO_GAME_LOGS"):
            continue
        try:
            names = {p: display(profiles.get(seat.profile)), o: other.name}
            replay.save(REPLAY_DIR, f"{match.id}-{match.rematches}", p, replay.game_views(match.last_log, p, names))
        except Exception:
            log.exception("could not save the replay of match %s", match.id)


async def get_replay(req):
    """Every view you saw in one of your finished matches (key: the history's match), as saved when it ended: a JSON list.
    The key can instead be a share token (`share_replay`): that replay, read-only, to anyone, with no profile needed."""
    key = req.match_info["match"]
    shared = profiles.shared(key)
    row = shared or profiles.match(me(req)["id"], key)
    saved = row and row["seat"] and replay.load(REPLAY_DIR, row["match"], row["seat"])
    if not saved:
        raise web.HTTPNotFound(text="This match can't be replayed")
    return web.Response(body=saved, content_type="application/json",
                        headers={"Content-Encoding": "gzip", "X-AK-Shared": "1" if shared else "0"})


async def share_replay(req):
    """A link to one of your finished matches' replays, for anyone (docs/share-links.md): {token}, opened at #/replay/<token>."""
    p = me(req)
    key = req.match_info["match"]
    row = profiles.match(p["id"], key)
    if not (row and row["seat"] and replay.load(REPLAY_DIR, key, row["seat"])):
        raise web.HTTPNotFound(text="This match can't be replayed")
    return web.json_response({"token": profiles.share(p["id"], key, row["seat"])})


async def replay_lists(req):
    """Both decklists of one of your finished matches, as played ({mine, theirs}: card id -> copies), for the match history
    to show without loading the whole replay. Decklists are open in this game, the opponent's too."""
    p = me(req)
    key = req.match_info["match"]
    row = profiles.match(p["id"], key)
    saved = row and row["seat"] and replay.load(REPLAY_DIR, key, row["seat"])
    if not saved:
        raise web.HTTPNotFound(text="This match's decklists weren't kept")
    lists = json.loads(gzip.decompress(saved))[0].get("lists")   # replays saved before lists were kept have none
    if not lists:
        raise web.HTTPNotFound(text="This match's decklists weren't kept")
    return web.json_response({"mine": lists[row["seat"]], "theirs": lists["B" if row["seat"] == "A" else "A"]})


async def get_news(req):
    """Every release, and what this player hasn't read (web/news.py)."""
    p = profile_of(req)
    rels = news.releases()
    if p is None:
        return web.json_response({"releases": rels, "unread": False, "newest": rels[0]["id"] if rels else "", "since": []})
    decks = profile_view(p)["decks"]
    created = profiles.db.execute("SELECT created FROM profiles WHERE id = ?", (p["id"],)).fetchone()[0]
    return web.json_response({"releases": rels, **news.state(profiles.db, {**p, "created": created}, decks, rels)})


async def news_seen(req):
    """The player opened the News screen (opened), or saw "Since you last played" (shown), up to a release."""
    p, body = me(req), await guard.body(req)
    news.mark(profiles.db, p["id"], opened=str(body.get("opened") or "")[:10], shown=str(body.get("shown") or "")[:10])
    return web.json_response({})


async def client_events(req):
    """What the client saw the player do (web/events.py), in batches."""
    p, body = me(req), await guard.body(req)
    return web.json_response({"kept": events.record_client(profiles.db, p["id"], body.get("events"))})


async def send_feedback(req):
    """A player's message and the moment it was sent from: kept, then mailed to Martin in the background."""
    p, body = me(req), await guard.body(req)
    guard.limit_ip(req, "feedback")
    ctx = body.get("context")
    context = {str(k)[:40]: guard.clean_text(v)[:200] if isinstance(v, str) else v
               for k, v in (ctx.items() if isinstance(ctx, dict) else ()) if isinstance(v, (str, int, float))}
    text, view = guard.clean_text(body.get("text")).strip(), body.get("view")
    if view is not None and len(json.dumps(view)) > feedback.VIEW_MAX:
        view = {"dropped": f"the view was over {feedback.VIEW_MAX} bytes"}
    try:
        feedback.keep(profiles.db, p["id"], display(p), text, context, view)
    except feedback.FeedbackError as e:
        raise web.HTTPBadRequest(text=str(e))
    if guard.limiter.allow("mail", "all"):    # kept either way; mailed while the server-wide hourly cap allows
        asyncio.get_running_loop().run_in_executor(None, feedback.mail, display(p), text, context, view)
        asyncio.get_running_loop().run_in_executor(None, discord.post, "feedback", discord.feedback_text(display(p), text, context))
    return web.json_response({})


# ----------------------------------------------------------------- the ladder (web/ladder.py)
RANKED_WAIT = 15            # seconds the queue waits for a person near your rating before giving you a bot
waiting: list[dict] = []    # people in the ranked queue: {pid, name, deck, rating, since, fut}
ladder: ranking.Ladder = None
tiers: tiers_mod.Tiers = None   # each person's league and stars, beside the rating (web/tiers.py, docs/ranked-leagues.md)


def _window(entry: dict, now: float) -> float:
    """How far apart two people's ratings may be to meet: wider the longer they've waited."""
    return 200 + 20 * (now - entry["since"])


def _meets(entry: dict, league: int | None, rating: float, now: float) -> bool:
    """Whether a person in `league` at `rating` meets one waiting in the queue: the same league below the top; in the top
    league (or before leagues) ratings within the window."""
    if league is not None and entry.get("league") is not None and (league != tiers_mod.TOP or entry["league"] != tiers_mod.TOP):
        return entry["league"] == league
    return abs(entry["rating"] - rating) <= _window(entry, now)


async def join_ranked(req):
    """Join the ranked queue with a deck; the answer is your match ({id, token, seat}) once there is one: a person from
    your league (in the top league, near your rating) if one is waiting or arrives within RANKED_WAIT seconds, else a bot
    from your league's band (web/tiers.py; in the top league the nearest bot). Leaving the request leaves the queue."""
    p, body = me(req), await guard.body(req)
    guard.limit("ranked", p["id"])
    try:
        deck = custom_decks.resolve(body.get("deck"))
    except EngineError as e:
        raise web.HTTPBadRequest(text=str(e))
    r, now = ladder.get(p["id"]).rating, time.time()
    lg = tiers.get(p["id"]).league if tiers else None
    for w in waiting:   # someone already waiting from your league (in the top league, near enough): theirs and yours
        if w["pid"] != p["id"] and not w["fut"].done() and _meets(w, lg, r, now):
            waiting.remove(w)
            mid, ta, tb = hub.new_id(), secrets.token_urlsafe(12), secrets.token_urlsafe(12)
            match = Match(mid, Seat(ta, w["name"], deck=w["deck"], profile=w["pid"], ladder=w["pid"]))
            match.join(Seat(tb, display(p), deck=deck, profile=p["id"], ladder=p["id"]))
            _open(match)
            w["fut"].set_result({"id": mid, "token": ta, "seat": "A"})
            return web.json_response({"id": mid, "token": tb, "seat": "B"})
    entry = {"pid": p["id"], "name": display(p), "deck": deck, "rating": r, "league": lg, "since": now,
             "fut": asyncio.get_running_loop().create_future()}
    waiting[:] = [w for w in waiting if w["pid"] != p["id"]] + [entry]   # one place in the queue per person
    asyncio.get_running_loop().run_in_executor(None, discord.post, "events", discord.queue_text(display(p)))   # the Discord channel hears it: someone may queue too
    try:
        res = await asyncio.wait_for(asyncio.shield(entry["fut"]), RANKED_WAIT)
        return web.json_response(res if res else {"cancelled": True})
    except asyncio.TimeoutError:
        pass
    finally:
        if entry in waiting:
            waiting.remove(entry)
    if entry["fut"].done():   # paired in the instant the wait ran out, or cancelled
        res = entry["fut"].result()
        return web.json_response(res if res else {"cancelled": True})
    recent = [h["opp_deck"] for h in profiles.history(p["id"]) if h.get("mode") == "ranked" and h["opp"].startswith("Bot (")][:ranking.RECENT_DECKS]
    slug = {name: s for s, name in DECK_NAMES.items()}
    avoid = {slug.get(d, d) for d in recent}   # never the deck of your last four bot games
    bid = ladder.bot_in(*tiers_mod.band(lg), random, avoid) if lg and lg != tiers_mod.TOP else None
    bid = bid or ladder.nearest_bot(r if not lg or lg == tiers_mod.TOP else tiers_mod.par(lg) + 50, random, avoid=avoid)
    level, bdeck = ranking.parse_bot(bid)
    mid, token = hub.new_id(), secrets.token_urlsafe(12)
    match = Match(mid, Seat(token, display(p), deck=deck, profile=p["id"], ladder=p["id"]))
    match.join(Seat(secrets.token_urlsafe(12), ladder_name(bid), bot=level, deck=bdeck, ladder=bid))
    _open(match)
    return web.json_response({"id": mid, "token": token, "seat": "A"})


async def leave_ranked(req):
    """Leave the ranked queue (Cancel): said outright, since the server doesn't notice the browser dropping its request, and a
    person searching meanwhile would be paired with someone gone."""
    p = me(req)
    for w in [w for w in waiting if w["pid"] == p["id"]]:
        waiting.remove(w)
        if not w["fut"].done():
            w["fut"].set_result(None)
    return web.json_response({})


def _open(match: Match) -> None:
    # A ranked match states both ratings as they stand going in (the versus moment shows them). A bot shows the rating of
    # the pairing that plays, its own leaderboard row (Martin, 2026-10-24).
    for seat in match.seats.values():
        if seat.ladder:
            seat.rating = ladder.get(seat.ladder).shown()
            if tiers and not seat.ladder.startswith("bot:"):   # a person: their league; the number only in the top league
                lg = league_of(seat.ladder)
                seat.league = lg["name"]
                if not lg["top"]:
                    seat.rating = None
    match.on_game_end = save_game
    match.on_match_end = record_match
    hub.matches[match.id] = match
    hub.save(match)
    hub.kick_bot(match)


def rate_match(match: Match) -> None:
    """A ranked match's result moves both ratings (a draw moves nothing)."""
    a, b = match.seats["A"].ladder, match.seats["B"].ladder
    score = match.score()
    if not (a and b) or score["A"] == score["B"]:
        return
    win, lose = (a, b) if score["A"] > score["B"] else (b, a)
    before = {p: ladder.get(match.seats[p].ladder) for p in "AB"}
    ladder.result(win, lose)
    # each person's league moves too (web/tiers.py); bots have no league
    match.tier_change = {}
    if tiers:
        for p in "AB":
            lid = match.seats[p].ladder
            if lid.startswith("bot:"):
                continue
            ch = tiers.result(lid, lid == win)
            match.tier_change[p] = {"line": ch.line(ladder.get(lid).shown()), **tiers_mod.view(ch.after, ladder.get(lid).shown())}
    match.rating_change = {p: {"before": before[p].shown(), "after": ladder.get(match.seats[p].ladder).shown(),
                               # the change between the numbers shown, so "1502 → 1490 (−12)" always adds up
                               "delta": round(ladder.get(match.seats[p].ladder).rating) - round(before[p].rating)} for p in "AB"}
    match.version += 1


def ladder_name(lid: str) -> str:
    bot = ranking.parse_bot(lid)
    if bot:   # a bot is named by its deck's archetype (Martin's names), else its deck, and its rung, never its pilot's level
        arch, names = _archetypes()
        deck = names.get(arch.get(bot[1]), DECK_NAMES.get(bot[1], bot[1]))
        return f"{deck} ({ranking.rung_of(ladder.get(lid).rating)} Bot)"
    p = profiles.get(lid)
    return display(p) if p else "?"


async def leaderboard(req):
    """Everyone ranked on the ladder, best first (name, rating, whether it's a bot, whether it's you); a player still placing
    (under ladder.PROVISIONAL games) isn't ranked yet and sees their own progress instead."""
    p = profile_of(req)
    mine, asked = (set(friends.of(p["id"])), friends.asked(p["id"])) if p else (set(), set())
    table = ladder.table()
    # A person is listed from their first rated game, with their league; the number shows only in the top league
    # (docs/ranked-leagues.md). Before leagues, a person still placing was left off (as on Lichess).
    def person(lid, r):
        lg = league_of(lid) if tiers else None
        return {"name": ladder_name(lid), "rating": r.shown() if not lg or lg["top"] else None, "league": lg,
                "bot": False, "you": bool(p and lid == p["id"]),
                **({} if p and lid == p["id"] else {"id": lid, "friend": lid in mine, "asked": lid in asked})}   # whether you're friends or have asked
    rows = [(person_key(lid, r), person(lid, r)) for lid, r in table if not lid.startswith("bot:") and (tiers or not r.provisional)]
    # The bots one row per pilot-and-deck pairing, each a player of its own (Martin, 2026-10-24; from 2026-10-02 to then the
    # bots were folded into one row per level, then per rung, to keep the board short).
    for lid, r in bot_rows(table):
        rows.append((r.rating, {"name": ladder_name(lid), "rating": r.shown(), "bot": True, "you": False,
                                "deck": ranking.parse_bot(lid)[1]}))
    rows = [row for _, row in sorted(rows, key=lambda x: -x[0])]
    me_ = ladder.get(p["id"]) if p else None
    placing = {"name": display(p), "rating": me_.shown(), "games": me_.games, "of": ranking.PROVISIONAL} \
        if me_ and me_.provisional and me_.games and not tiers else None
    return web.json_response({"rows": rows, "placing": placing})


# ----------------------------------------------------------------- the league (web/league.py, docs/league.md)
league: league_mod.Pool = None      # the lists the league added; `pool` is the /api/pool handler
meta: meta_mod.Meta = None          # the Meta tab's sums over every game's card facts (web/meta.py)


def league_auth(req) -> None:
    k = league_mod.key()
    if not k or not secrets.compare_digest(req.headers.get("X-AK-League-Key", "").encode(), k.encode()):
        raise web.HTTPForbidden(text="the league key")


async def league_pool(req):
    """The runner's view: every bot deck's list and name, every bot pairing's rating, the pilots' specs."""
    league_auth(req)
    decks = [{"slug": s, "name": DECK_NAMES.get(s, s), "list": load_premade_deck(s)} for s in ladder.decks]
    players = [{"id": lid, "rating": r.rating, "rd": r.rd, "games": r.games} for lid, r in ladder.bots().items()
               if ranking.parse_bot(lid)[1] in ladder.decks]
    return web.json_response({"decks": decks, "players": players, "pilots": dict(BOT_LEVELS)})


async def league_games(req):
    """Bot games played by the runner, rated here like anyone's: [{gid, a, b, winner, seed, turns, reason}], a and b bot
    ladder ids. A game whose `gid` came before is skipped (the runner resends what it could not confirm), counted as `seen`."""
    league_auth(req)
    body = await guard.body(req)
    games = body.get("games") if isinstance(body, dict) else None
    if not isinstance(games, list) or len(games) > 1000:
        raise web.HTTPBadRequest(text="games: a list of at most 1000")
    ok, touched = [], set()
    pairings = {lid for lid in ladder.bots() if ranking.parse_bot(lid)[1] in ladder.decks}
    gids = [str(g["gid"]) for g in games if isinstance(g, dict) and g.get("gid")]
    fresh = league.unseen(gids)
    seen = len(gids) - len(fresh)
    for g in games:
        if not isinstance(g, dict) or (g.get("gid") and str(g["gid"]) not in fresh):
            continue
        a, b, w = g.get("a"), g.get("b"), g.get("winner")
        if not (ranking.parse_bot(a or "") and ranking.parse_bot(b or "") and a != b):
            continue
        if a not in pairings or b not in pairings:   # a list at a pilot level it no longer plays (or a retired list): its result
            continue                                  # would bring the pairing back onto the ladder (2026-10-27)
        if w in ("A", "B"):
            ladder.result(a if w == "A" else b, b if w == "A" else a)
            touched |= {a, b}
        ok.append(g)
    league.record(ok)
    league.mark(list(fresh))
    meta.add({**g, **g["facts"]} for g in ok if isinstance(g.get("facts"), dict))   # the runner sends each game's card facts with it
    return web.json_response({"rated": len(ok), "seen": seen, "ratings": {lid: ladder.get(lid).shown() for lid in touched}})


async def league_facts(req):
    """Card facts of games already rated (a backfill from the runner's log): [{t, a, b, winner, ra, rb, A, B}], counted once."""
    league_auth(req)
    body = await guard.body(req)
    games = body.get("games") if isinstance(body, dict) else None
    if not isinstance(games, list) or len(games) > 5000:
        raise web.HTTPBadRequest(text="games: a list of at most 5000")
    return web.json_response({"counted": meta.add(g for g in games if isinstance(g, dict))})


async def league_meta_forget(req):
    """The Meta tab forgets every game of these lists, {slugs: [...]}: for a change to how a card plays that its print
    does not show (an engine fix, a config number)."""
    league_auth(req)
    body = await guard.body(req)
    slugs = body.get("slugs") if isinstance(body, dict) else None
    if not isinstance(slugs, list) or not all(isinstance(s, str) for s in slugs):
        raise web.HTTPBadRequest(text="slugs: a list of list slugs")
    meta.forget(slugs)
    return web.json_response({"forgotten": len(slugs)})


def _list_of(slug: str):
    try:
        return load_premade_deck(slug)
    except (KeyError, ValueError):
        return None


def _meta_args(req) -> tuple[int, int, int]:
    q = req.query
    def num(k, default):   # a bad number is the default, never a 500 (a provisional "1520?" once made the page send NaN)
        try:
            return int(float(q.get(k) or default))
        except (ValueError, OverflowError):
            return default
    lo, hi, days = num("lo", 0), num("hi", 10000), num("days", 0)
    return max(0, lo), min(10000, hi), max(0, min(60, days))


def _archetypes():
    return meta_mod.archetype_map(league.rows if league else {}, ladder.decks if ladder else [])


async def meta_overview(req):
    """The Meta tab: each archetype's share and win rate in a rating range over recent days, and the matchup matrix."""
    lo, hi, days = _meta_args(req)
    arch, names = _archetypes()
    p = profile_of(req)
    me_ = ladder.get(p["id"]) if p and ladder else None
    return web.json_response({**meta.overview(arch, names, lo, hi, days), "you": round(me_.rating) if me_ and me_.games else None})


async def meta_archetype(req):
    """One archetype: its lists and every card's figures in the range, against one opponent archetype when `vs` is given."""
    lo, hi, days = _meta_args(req)
    arch, names = _archetypes()
    x, vs = req.query.get("id", ""), req.query.get("vs") or None
    if x not in names or (vs and vs not in names):
        raise web.HTTPNotFound(text="no such archetype")
    return web.json_response({**meta.archetype(x, arch, lo, hi, days, vs, req.query.get("list") or None), "name": names[x], "vs_name": names.get(vs) if vs else None})


async def league_retire(req):
    """Lists out of the pool for good (Martin's call, 2026-10-25): {slugs: [...]}; they leave the ranked offers and the runner's pool
    at once, their ratings and games stay on record."""
    league_auth(req)
    body = await guard.body(req)
    slugs = body.get("slugs") if isinstance(body, dict) else None
    if not isinstance(slugs, list) or len(slugs) > 200:
        raise web.HTTPBadRequest(text="slugs: a list of at most 200")
    out = [s for s in map(str, slugs) if s in ladder.decks]
    league.retire(out)
    ladder.decks[:] = [s for s in ladder.decks if s not in out]
    return web.json_response({"retired": out})


async def league_levels(req):
    """The pilot levels pool lists play at: {slugs, levels}; the pairings at other levels leave the ladder, and a restart
    keeps it so (Martin, 2026-10-27: his 17 lists Expert only, after a restart had given them Easy and Normal pilots)."""
    league_auth(req)
    body = await guard.body(req)
    slugs, levels = (body.get("slugs"), body.get("levels")) if isinstance(body, dict) else (None, None)
    if not isinstance(slugs, list) or not isinstance(levels, list) or not levels or any(lv not in ranking.LEVELS for lv in levels):
        raise web.HTTPBadRequest(text="slugs: a list; levels: some of " + ", ".join(ranking.LEVELS))
    slugs = [s for s in map(str, slugs) if s in ladder.decks]
    league.set_levels(slugs, levels)
    for s in slugs:
        ladder.drop_levels(s, levels)
    return web.json_response({"slugs": slugs, "levels": levels})


async def league_reset_people(req):
    """People back to a fresh 1500 with placement games ahead: {ids: [profile ids]}; bots can't be reset here (Martin,
    2026-10-27, once the league became his 17 Expert lists and the scale moved)."""
    league_auth(req)
    body = await guard.body(req)
    ids = body.get("ids") if isinstance(body, dict) else None
    if not isinstance(ids, list) or len(ids) > 100:
        raise web.HTTPBadRequest(text="ids: a list of at most 100")
    out = [i for i in map(str, ids) if not ranking.parse_bot(i)]
    with ladder.db:
        ladder.db.executemany("DELETE FROM ladder WHERE id = ?", [(i,) for i in out])
    return web.json_response({"reset": out})


async def league_decks(req):
    """New lists for the pool: [{slug, name, list, source, parent, start, levels}]; each legal, distinct list joins as a
    placing player per pilot level (`levels`, every level when absent: Martin's 2026-10-27 league is Expert only), starting at
    `start` (the best prior the sender has: a parent's rating, a target's; 1500 when absent)."""
    league_auth(req)
    body = await guard.body(req)
    decks = body.get("decks") if isinstance(body, dict) else None
    if not isinstance(decks, list) or len(decks) > 100:
        raise web.HTTPBadRequest(text="decks: a list of at most 100")
    added, rejected = [], {}
    for d in decks:
        slug, name, lst = str(d.get("slug") or ""), str(d.get("name") or "").strip()[:40] or "Deck", d.get("list")
        if not isinstance(lst, list):
            rejected[slug] = ["list: 30 card ids"]; continue
        problems = league.add(slug, name, [str(c) for c in lst], str(d.get("source") or "league")[:20], d.get("parent"), set(ladder.decks))
        if problems:
            rejected[slug] = problems; continue
        ladder.decks.append(slug)
        start = d.get("start")
        start = min(3000.0, max(800.0, float(start))) if isinstance(start, (int, float)) else ranking.START
        levels = [lv for lv in (d.get("levels") or ranking.LEVELS) if lv in ranking.LEVELS] or list(ranking.LEVELS)
        if d.get("levels"):
            league.set_levels([slug], levels)
        for level in levels:
            ladder.add_player(ranking.bot_id(level, slug), start)
        added.append(slug)
    return web.json_response({"added": added, "rejected": rejected})


async def league_report_post(req):
    """The morning's meta report from the runner (league/report.py), kept as the latest."""
    league_auth(req)
    body = await guard.body(req)
    rep = body.get("report") if isinstance(body, dict) else None
    if not isinstance(rep, dict) or len(json.dumps(rep)) > 2_000_000:
        raise web.HTTPBadRequest(text="report: an object under 2 MB")
    league.put_report(rep)
    return web.json_response({"ok": True})


async def league_report(_req):
    """The latest meta report, with the people added (the Ladder screen's Meta tab); empty until the runner has posted one."""
    rep = league.report() if league else None
    if not rep:
        return web.json_response({"empty": True})
    people = [{"name": ladder_name(lid), "rating": r.shown(), "games": r.games}
              for lid, r in ladder.table() if not lid.startswith("bot:")]
    return web.json_response({**rep, "people": people})


# ----------------------------------------------------------------- friends and challenges (web/friends.py)
CHALLENGE_WAIT = 60          # seconds a challenge stands before it lapses
presence: dict[str, set] = {}   # profile id -> its open presence sockets (one per tab or device): online while any is open
challenges: dict[str, dict] = {}   # challenge id -> {from, to, deck, fut}
friends: Friends = None
chat: Chat = None


def friend_label(viewer: str, other: str) -> str:
    """`other`'s name as `viewer` sees it: without its #tag, unless another of viewer's friends shares the name."""
    full = display(profiles.get(other)); first = full.split("#")[0]
    same = sum(1 for f in friends.of(viewer) if (q := profiles.get(f)) and q["name"] == first)
    return full if same > 1 else first


async def _tell(pid: str, msg: dict) -> None:
    async def one(ws):
        try:
            await asyncio.wait_for(ws.send_json(msg), SEND_TIMEOUT)
        except Exception:
            presence.get(pid, set()).discard(ws)
            asyncio.ensure_future(_close_quietly(ws))
    await asyncio.gather(*(one(ws) for ws in list(presence.get(pid, ()))))


async def _tell_friends_online(pid: str, on: bool) -> None:
    """A player came online (their first open tab) or went away (their last closed): their friends' Friends buttons count it."""
    for fid in friends.of(pid):
        await _tell(fid, {"t": "online", "id": pid, "on": on})


async def presence_socket(req):
    """Online while open; carries challenges to you. The client opens it once it knows its profile."""
    p = profiles.by_code(req.query.get("key", ""))
    ws = web.WebSocketResponse(heartbeat=20, max_msg_size=guard.SOCKET_MSG_MAX)
    await ws.prepare(req)
    if p is None:
        await ws.close()
        return ws
    first = p["id"] not in presence
    presence.setdefault(p["id"], set()).add(ws)
    for cid, c in challenges.items():   # a challenge already standing reaches a tab opened since
        if c["to"] == p["id"]:
            await ws.send_json({"t": "challenge", "id": cid, "from": friend_label(p["id"], c["from"])})
    for frm in friends.requests_to(p["id"]):   # so does a friend request sent while you were away
        if (f := profiles.get(frm)):
            await ws.send_json({"t": "friendreq", "from": frm, "name": display(f)})
    await ws.send_json({"t": "build", "build": BUILD})
    if (unread := chat.unread(p["id"])):   # messages that came while you were away
        await ws.send_json({"t": "unread", "unread": unread})
    if first:
        await _tell_friends_online(p["id"], True)
    try:
        async for _ in ws:
            pass
    finally:
        presence.get(p["id"], set()).discard(ws)     # _tell may have dropped it already
        if p["id"] in presence and not presence[p["id"]]:
            del presence[p["id"]]
            friends.seen(p["id"])
            await asyncio.shield(_tell_friends_online(p["id"], False))   # the handler may be closing under a cancel
    return ws


async def friends_list(req):
    """Your friends (online first, then by when they were last on) and your friend code."""
    p = me(req)
    out, unread, last = [], chat.unread(p["id"]), chat.last(p["id"])
    for fid in friends.of(p["id"]):
        f = profiles.get(fid)
        if f:
            out.append({"id": fid, "name": display(f), "online": fid in presence, "seen": friends.last_seen(fid),
                        "unread": unread.get(fid, 0), "last": last.get(fid)})
    out.sort(key=lambda f: (not f["online"], -(f["seen"] or 0)))
    return web.json_response({"friends": out, "code": friends.code_for(p["id"])})


async def friend_peek(req):
    """Whose friend link this is (for the confirmation)."""
    owner = friends.owner(req.match_info["code"])
    o = owner and profiles.get(owner)
    if not o:
        raise web.HTTPNotFound(text="that friend link no longer works")
    p = profile_of(req)
    return web.json_response({"name": display(o), "self": bool(p and p["id"] == owner),
                              "already": bool(p and friends.are(p["id"], owner))})


async def friend_add(req):
    p, body = me(req), await guard.body(req)
    guard.limit("friend", p["id"])
    try:
        other = friends.add(p["id"], str(body.get("code") or ""))
    except FriendError as e:
        raise web.HTTPBadRequest(text=str(e))
    return web.json_response({"name": display(profiles.get(other))})


REJOIN_WITHIN = 3600      # seconds since a match's last move within which opening the game takes you back to it


async def current_match(req):
    """The match you are still playing, with your seat's token, so any tab or device can get back into it (a closed tab,
    a phone that dropped the page). Not a tutorial or a gauntlet: leaving those leaves them; nor a bot match you never
    made a move in."""
    p = profile_of(req)
    if not p:
        return web.json_response({})
    lessons = set(tutorial.BOTS.values())
    live = lambda m: time.time() - (m.started_at + (m.action_times[-1] if m.action_times else 0)) < REJOIN_WITHIN
    # a person waits for you in PvP; a bot match only once you've made a move in it (one left at the mulligan is left)
    started = lambda m, seat: not any(o.is_bot for o in m.seats.values()) or any(h.seat == seat for h in m.history)
    mine = [(m, s) for m in hub.matches.values() if m.phase == "playing" and not m.schedule and live(m)
            for seat, s in m.seats.items() if s.profile == p["id"] and started(m, seat)
            and not any(o.bot in lessons for o in m.seats.values())]
    if not mine:
        return web.json_response({})
    m, s = max(mine, key=lambda ms: ms[0].started_at)
    return web.json_response({"id": m.id, "token": s.token})


async def friend_request(req):
    """Ask a player on the leaderboard to be friends: they get it on their presence socket now, or when they next come."""
    p, body = me(req), await guard.body(req)
    guard.limit("friend", p["id"])
    other = str(body.get("to") or "")
    if not profiles.get(other):
        raise web.HTTPNotFound(text="no such player")
    try:
        done = friends.request(p["id"], other)
    except FriendError as e:
        raise web.HTTPBadRequest(text=str(e))
    if not done:
        await _tell(other, {"t": "friendreq", "from": p["id"], "name": display(p)})
    return web.json_response({"friends": done})


async def friend_request_answer(req):
    p, body = me(req), await guard.body(req)
    friends.answer(p["id"], req.match_info["frm"], bool(body.get("accept")))
    return web.json_response({})


async def friend_remove(req):
    friends.remove(me(req)["id"], req.match_info["id"])
    return web.json_response({})


async def chat_history(req):
    """Your conversation with a friend (web/chat.py), oldest first; opening it reads it."""
    p, other = me(req), req.match_info["id"]
    if not friends.are(p["id"], other):
        raise web.HTTPBadRequest(text="not your friend")
    chat.read(p["id"], other)
    return web.json_response({"messages": chat.history(p["id"], other)})


async def chat_send(req):
    """Send a friend a message: it reaches them at once if they are on (any tab), else waits in the conversation."""
    p, other, body = me(req), req.match_info["id"], await guard.body(req)
    guard.limit_ip(req, "chat")
    if not friends.are(p["id"], other):
        raise web.HTTPBadRequest(text="not your friend")
    try:
        m = chat.send(p["id"], other, body.get("text"))
    except ChatError as e:
        raise web.HTTPBadRequest(text=str(e))
    await _tell(other, {"t": "msg", "with": p["id"], "name": friend_label(other, p["id"]), "msg": m})
    await _tell(p["id"], {"t": "msg", "with": other, "msg": m})   # your other tabs show it too
    return web.json_response(m)


async def chat_read(req):
    """You have seen the conversation (it was open when a message came)."""
    chat.read(me(req)["id"], req.match_info["id"])
    return web.json_response({})


async def challenge(req):
    """Challenge an online friend with a deck; the answer is your match once they accept, or 409 when they decline, the
    challenge lapses, or they are offline. Leaving the request withdraws it."""
    p, body = me(req), await guard.body(req)
    guard.limit("challenge", p["id"])
    to = str(body.get("friend") or "")
    if not friends.are(p["id"], to):
        raise web.HTTPBadRequest(text="not your friend")
    if to not in presence:
        raise web.HTTPConflict(text="offline")
    try:
        deck = custom_decks.resolve(body.get("deck"))
    except EngineError as e:
        raise web.HTTPBadRequest(text=str(e))
    cid = secrets.token_urlsafe(8)
    c = challenges[cid] = {"from": p["id"], "name": display(p), "to": to, "deck": deck,
                           "fut": asyncio.get_running_loop().create_future()}
    await _tell(to, {"t": "challenge", "id": cid, "from": friend_label(to, p["id"])})
    try:
        m = await asyncio.wait_for(asyncio.shield(c["fut"]), CHALLENGE_WAIT)
    except asyncio.TimeoutError:
        m = None
    finally:
        challenges.pop(cid, None)
        if not c["fut"].done():
            c["fut"].set_result(None)
        await _tell(to, {"t": "challenge_gone", "id": cid})
    if not m:
        raise web.HTTPConflict(text=f"{display(profiles.get(to)).split('#')[0]} is busy")
    return web.json_response(m)


async def challenge_cancel(req):
    """Withdraw your challenges (the waiting request may not notice its client left): each friend's piece goes."""
    p = me(req)
    for c in list(challenges.values()):
        if c["from"] == p["id"] and not c["fut"].done():
            c["fut"].set_result(None)
    return web.json_response({})


async def challenge_answer(req):
    """Accept (with your deck: the match starts) or decline a challenge to you."""
    p, body = me(req), await guard.body(req)
    c = challenges.get(req.match_info["id"])
    if not c or c["to"] != p["id"] or c["fut"].done():
        raise web.HTTPGone(text="that challenge has gone")
    if not body.get("accept"):
        c["fut"].set_result(None)
        return web.json_response({})
    try:
        deck = custom_decks.resolve(body.get("deck"))
    except EngineError as e:
        raise web.HTTPBadRequest(text=str(e))
    mid, ta, tb = hub.new_id(), secrets.token_urlsafe(12), secrets.token_urlsafe(12)
    match = Match(mid, Seat(ta, c["name"], deck=c["deck"], profile=c["from"]))
    match.join(Seat(tb, display(p), deck=deck, profile=p["id"]))
    _open(match)
    c["fut"].set_result({"id": mid, "token": ta, "seat": "A"})
    return web.json_response({"id": mid, "token": tb, "seat": "B"})


async def index(_req):
    return web.FileResponse(STATIC / "index.html")


async def privacy(_req):
    return web.FileResponse(STATIC / "privacy.html")


async def pool(_req):
    return web.json_response({
        "cards": card_pool(),
        "decks": [{"id": d["slug"], "name": d["name"], "list": load_premade_deck(d["slug"]), "cover": d.get("cover", "")}
                  for d in STARTER_DECKS],
        "map": map_info(),
        "levels": list(BOT_LEVELS),
        "bot_decks": list(ladder.decks if ladder else BOT_DECKS),   # the pool a Random bot deck is drawn from (decks.BOT_DECKS plus the league's)
        # The bot decks that are not starters: shown by name and list wherever a bot's deck is (Practice's chooser,
        # the versus moment, the match history), never in a player's collection.
        "bot_only": [{"id": slug, "name": DECK_NAMES.get(slug, slug), "list": load_premade_deck(slug), "cover": STARTER_COVERS.get(slug, "")}
                     for slug in (ladder.decks if ladder else BOT_DECKS) if slug not in {d["slug"] for d in STARTER_DECKS}],
        "build": BUILD,
    })


def find_log(key: str, series: int, game) -> dict | None:
    """The logged game `game` (the last of the series when None) of match `key`'s series `series`, from LOG_DIR."""
    found = None
    for path in sorted(LOG_DIR.glob(f"web_*_{key}.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("series", 0) != series or (game is not None and rec.get("game_no") != game):
                continue
            found = rec
    return _renamed(found)   # a game logged before a card's id changed replays with its new id


def position_at(rec: dict, rnd: int, seat: str):
    """The logged game replayed to the start of `seat`'s turn in round `rnd` (a clone), or None if it never came."""
    from ..engine.actions import SKIP, ChoiceAction
    from ..engine.config import Config
    from ..engine.state import new_game
    lists = rec.get("lists")
    if not lists:
        return None
    state = new_game(list(lists[0]), list(lists[1]), rec["seed"], map_id=rec.get("map_id", MAP_ID),
                     config=Config.default().for_log(rec), first_player=rec["first_player"])
    for adict in rec["actions"]:
        while state.pending is not None and state.effect_stack[-1].get("op") == "mulligan" and adict["kind"] != "choice":
            rules.apply_action(state, ChoiceAction(SKIP))     # a log from before the mulligan rule
        if state.pending is None and rules.is_terminal(state) is None and state.player_to_act() == seat \
                and state.turn_counter // 2 + 1 == rnd:
            return state.clone()
        rules.apply_logged(state, adict)
    return None


STUDY_DIR = Path(__file__).resolve().parent / "studies"                               # shipped with the app
STUDY_DATA_DIR = Path(__file__).resolve().parents[2] / "results" / "studies"          # on the server's volume: a copy, no deploy


def study_files() -> dict[str, Path]:
    """Every study by name: the shipped ones, and those on the volume (`fly ssh sftp put` lands a new one in seconds), which win."""
    out: dict[str, Path] = {}
    for d in (STUDY_DIR, STUDY_DATA_DIR):
        if d.is_dir():
            for path in sorted(d.glob("*.json")):
                out[path.stem] = path
    return out


async def list_studies(req):
    """The studies you may open, for Settings: those naming you as owner, and those naming no owner."""
    p = me(req)
    out = []
    for name, path in sorted(study_files().items()):
        try:
            study = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if study.get("owner") in (None, p["id"]):
            out.append({"name": name, "title": study.get("title", name), "count": len(study.get("positions", []))})
    return web.json_response(out)


async def get_study(req):
    """A study (studies/<name>.json): positions from your logged games to play on from, in order, as the other seat. A
    developer's tool like the gauntlet: reached by its link, each position a 'Play from here'."""
    me(req)
    name = req.match_info["name"]
    path = study_files().get(name)
    if not name.replace("_", "").isalnum() or path is None:
        raise web.HTTPNotFound(text="No such study")
    study = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for pos in study.get("positions", []):
        rec = find_log(pos["match"], pos.get("series", 0), pos.get("game"))
        if rec is None:
            continue
        seat = pos.get("seat") or ("A" if rec["bots"][0] != "human" else "B")
        bot_deck, your_deck = (rec["deck_a"], rec["deck_b"]) if seat == "A" else (rec["deck_b"], rec["deck_a"])
        out.append({**pos, "seat": seat, "botDeck": DECK_NAMES.get(bot_deck, bot_deck), "yourDeck": DECK_NAMES.get(your_deck, "deck"),
                    "rounds": rec["turns"] // 2 + 1})
    return web.json_response({"title": study.get("title", name), "note": study.get("note", ""), "positions": out})


async def takeover_match(req, src: dict):
    """Play on from a position in one of your logged games, in the other seat, the Expert playing your old one. Martin,
    2026-10-21: "what would you do as the bot here?", asked on the real board instead of a rendering. The game is
    neither logged nor rated (Match.takeover)."""
    p = me(req)
    try:
        key, series, rnd = str(src.get("match", "")), int(src.get("series", 0)), int(src.get("round", 0))
    except (AttributeError, TypeError, ValueError, OverflowError):
        raise web.HTTPBadRequest(text="bad position")
    if not profiles.match(p["id"], f"{key}-{series}"):
        raise web.HTTPNotFound(text="Not one of your matches")
    rec = find_log(key, series, src.get("game"))
    if rec is None:
        raise web.HTTPNotFound(text="This game wasn't kept")
    seat = src.get("seat")
    if seat not in ("A", "B"):
        seat = "A" if rec["bots"][0] != "human" else "B"       # the seat that wasn't yours
    state = position_at(rec, rnd, seat)
    if state is None:
        raise web.HTTPBadRequest(text=f"Round {rnd} has no turn of that seat")
    for slug, lst in zip((rec["deck_a"], rec["deck_b"]), rec["lists"]):
        if slug not in DECK_NAMES:      # a custom deck this server no longer knows: registered under its logged slug
            custom_decks._register(slug, "Their deck", sorted(lst))
    mid, token = hub.new_id(), secrets.token_urlsafe(12)
    other = "B" if seat == "A" else "A"
    seats = {seat: Seat(token, display(p), profile=p["id"]), other: Seat(secrets.token_urlsafe(12), "Expert Bot", bot="expert")}
    match = Match(mid, seats["A"])
    match.join(seats["B"])              # no decks yet, so the match does not start on its own
    match.seats["A"].deck, match.seats["B"].deck = rec["deck_a"], rec["deck_b"]
    match.start_from(state, rec["seed"])
    hub.matches[mid] = match
    hub.save(match)
    return web.json_response({"id": mid, "token": token, "seat": seat})


def guest_name(body: dict, default: str) -> str:
    """A seat's name for a player with no profile: cleaned like a profile's, and with no #tag (a tag is a profile's)."""
    try:
        return clean_name(str(body.get("name") or "").split("#")[0])
    except ProfileError:
        return default


async def create_match(req):
    guard.limit_ip(req, "match")
    body = await guard.body(req)
    if body.get("from"):
        return await takeover_match(req, body["from"])
    try:
        try:
            lesson = int(body.get("tutorial") or 0)    # the tutorial's lesson: 1 or 2
        except (TypeError, ValueError, OverflowError):
            raise EngineError("no such lesson")
        if lesson not in (0, *tutorial.BOTS):
            raise EngineError("no such lesson")
        deck = f"{tutorial.BOTS[lesson]}_you" if lesson else custom_decks.resolve(body.get("deck"))
    except EngineError as e:
        raise web.HTTPBadRequest(text=str(e))
    mid, token = hub.new_id(), secrets.token_urlsafe(12)
    player = profile_of(req)
    match = Match(mid, Seat(token, display(player) if player else guest_name(body, "You"), deck=deck,
                            profile=player and player["id"]))
    bot = body.get("bot")
    gauntlet = body.get("gauntlet")
    if (bot is not None and not isinstance(bot, dict)) or (gauntlet is not None and not isinstance(gauntlet, dict)):
        raise web.HTTPBadRequest(text="bad bot")
    if lesson:     # the lesson's fixed deal against its opponent, straight into the game
        match.join(Seat(secrets.token_urlsafe(12), "Wild dogs", bot=tutorial.BOTS[lesson], deck=f"{tutorial.BOTS[lesson]}_them"))
        match.ready("A")
    elif gauntlet:
        level = gauntlet.get("level", "normal")
        if not isinstance(level, str):
            raise web.HTTPBadRequest(text="bad bot level")
        if level in ranking.BANDS:                   # the gauntlet's one pilot for the whole field: by the band's name
            level = next((l for l, b in ranking.PILOT_BAND.items() if b == level), "easy" if ranking.BANDS.index(level) < 2 else "expert")
        if level not in BOT_LEVELS:
            raise web.HTTPBadRequest(text="bad bot level")
        skip, games = gauntlet.get("skip") or [], gauntlet.get("games", 2 * gauntlet.get("per_seat", 5))   # games a deck
        if not isinstance(skip, list) or not all(isinstance(d, str) for d in skip) or not isinstance(games, int) or games not in range(1, 11):
            raise web.HTTPBadRequest(text="bad gauntlet")
        # The player's deck is no opponent, even sent as a custom list identical to a premade (the mirror isn't a test).
        mine = sorted(load_premade_deck(deck))
        wanted = gauntlet.get("decks")       # an explicit field (any shipped deck, the bots' own, a test deck such as lions30, or a saved player deck), else the starters
        if wanted is not None:
            if not isinstance(wanted, list) or not all(isinstance(d, (str, dict)) for d in wanted):
                raise web.HTTPBadRequest(text="bad gauntlet field")
            try:
                wanted = [custom_decks.resolve(d) if isinstance(d, dict) else d for d in wanted]   # a player's own deck as {name, list}, as the home piece sends its field
            except EngineError as e:
                raise web.HTTPBadRequest(text=str(e))
            if not all(d in PREMADE_DECKS or d in TEST_BOT_DECKS or d in custom_decks._saved for d in wanted):
                raise web.HTTPBadRequest(text="bad gauntlet field")
        mirror = bool(gauntlet.get("mirror"))   # both seats on each named deck in turn: the pilot is the only variable
        field = [d for d in (wanted if wanted is not None else sorted(DECK_SLUGS))
                 if mirror or (d != deck and d not in skip and sorted(load_premade_deck(d)) != mine)]
        if not field:
            raise web.HTTPBadRequest(text="empty gauntlet")
        if level == "expert" and player is None:
            raise web.HTTPUnauthorized(text="the Expert needs a profile")
        match.join(Seat(secrets.token_urlsafe(12), f"{ranking.PILOT_BAND[level]} Bot", bot=level, deck=field[0]))
        if mirror:
            match.make_gauntlet(field, games, mirror=True)
        elif gauntlet.get("reverse"):     # the bot keeps the chosen deck; the player plays the field
            match.seats["B"].deck = deck
            match.make_gauntlet(field, games, rotating="A")
        else:
            match.make_gauntlet(field, games)
        match._start_game()
        match.version += 1
    elif bot:
        level, bdeck = bot.get("level"), bot.get("deck")
        if not isinstance(level, str) or not isinstance(bdeck, str):
            raise web.HTTPBadRequest(text="bad bot")
        if level in ranking.BANDS and bdeck in PREMADE_DECKS:
            level = pilot_for(level, bdeck)          # one of the five bots, as on the ladder: the pilot follows the band
        if level not in BOT_LEVELS or bdeck not in {*PREMADE_DECKS, *TEST_BOT_DECKS}:
            raise web.HTTPBadRequest(text="bad bot")
        if level == "expert" and player is None:    # an Expert move takes a core for up to 8 s: only for a profile (Martin, 2026-11-05)
            raise web.HTTPUnauthorized(text="the Expert needs a profile")
        match.join(Seat(secrets.token_urlsafe(12), bot_seat_name(level, bdeck), bot=level, deck=bdeck))
    else:
        match.version += 1
    if not match.tutorial:      # a tutorial is neither a game log for balance nor a match in the history
        match.on_game_end = save_game
        match.on_match_end = record_match
    hub.matches[mid] = match
    hub.save(match)
    return web.json_response({"id": mid, "token": token, "seat": "A"})


def _local_seats(req, body: dict) -> tuple[Seat, Seat]:
    """A practice match's two seats, from the body home's Play sends (deck, bot: {level, deck}), checked as create_match
    checks a bot match."""
    try:
        deck = custom_decks.resolve(body.get("deck"))
    except EngineError as e:
        raise web.HTTPBadRequest(text=str(e))
    bot = body.get("bot") or {}
    level, bdeck = bot.get("level"), bot.get("deck")
    if level in ranking.BANDS and bdeck in PREMADE_DECKS:
        level = pilot_for(level, bdeck)
    if level not in BOT_LEVELS or bdeck not in {*PREMADE_DECKS, *TEST_BOT_DECKS}:
        raise web.HTTPBadRequest(text="bad bot")
    player = profile_of(req)
    host = Seat(secrets.token_urlsafe(12), display(player) if player else body.get("name") or "You", deck=deck,
                profile=player and player["id"], ready=True)
    return host, Seat(secrets.token_urlsafe(12), bot_seat_name(level, bdeck), bot=level, deck=bdeck, ready=True)


async def local_engine(_req):
    """What the browser's engine is built from (web/local.py): the cards, maps and Config, and the engine's source hash."""
    return web.Response(text=local.engine_doc(), content_type="application/json")


async def local_setup(req):
    """A practice match to play in the browser: both decklists, the seats as the view shows them, the bot's spec."""
    host, bot = _local_seats(req, await req.json())
    return web.json_response({"lists": {"A": load_premade_deck(host.deck), "B": load_premade_deck(bot.deck)},
                              "seats": local.seats_view(host, bot), "level": bot.bot, **local.bot_spec(bot.bot),
                              "pause": BOT_PAUSE,   # the bot's beat, as the server keeps it (a test server's is 0)
                              "source_hash": local.source_hash()})


async def local_cand(req):
    """The candidate network the Expert's whole-turn search reads, for the browser's bot (web/local.py cand_url)."""
    for level in BOT_LEVELS:          # after a restart nothing has asked for a setup yet: the addresses are built here
        local.bot_spec(level)
    text = local.cand_text(req.path)
    if text is None:
        raise web.HTTPNotFound()
    if req.path not in _cand_gz:
        _cand_gz[req.path] = gzip.compress(text.encode(), 6)
    return web.Response(body=_cand_gz[req.path], content_type="application/json",
                        headers={"Content-Encoding": "gzip", "Cache-Control": "public, max-age=31536000, immutable"})


_cand_gz: dict[str, bytes] = {}


_local_done: dict[str, str] = {}     # a finished local match's key -> its match id: a resent log is saved once


async def local_match(req):
    """A practice match the browser played, finished: replayed and saved as any match (web/local.py)."""
    body = await req.json()
    key = str(body.get("key") or "")[:40]
    if key and key in _local_done:
        return web.json_response({"id": _local_done[key]})
    host, bot = _local_seats(req, body)
    mid = hub.new_id()
    try:
        local.replay(mid, host, bot, body, save_game, record_match)
    except (EngineError, KeyError, ValueError, TypeError) as e:
        log.warning("local match refused: %s", e)
        raise web.HTTPBadRequest(text=f"the match does not replay: {e}")
    if key:
        _local_done[key] = mid
        while len(_local_done) > 2000:
            _local_done.pop(next(iter(_local_done)))
    return web.json_response({"id": mid})


async def join_match(req):
    guard.limit_ip(req, "match")
    match = hub.get(req.match_info["id"])
    if match is None:
        raise web.HTTPNotFound(text="no such match")
    body = await guard.body(req)
    try:
        deck = custom_decks.resolve(body.get("deck"))
    except EngineError as e:
        raise web.HTTPBadRequest(text=str(e))
    token = secrets.token_urlsafe(12)
    player = profile_of(req)
    try:
        seat = match.join(Seat(token, display(player) if player else guest_name(body, "Friend"), deck=deck,
                               profile=player and player["id"]))
    except EngineError as e:
        raise web.HTTPConflict(text=str(e))
    await hub.push(match)
    return web.json_response({"id": match.id, "token": token, "seat": seat})


def _changed(match: Match) -> tuple:
    """What a socket message may have changed, compared before and after it: only a change is pushed (and saved)."""
    return match.version, match.phase, len(match.results), match.seq


async def socket(req):
    match = hub.get(req.match_info["id"])
    seat = match.seat_of(req.query.get("token", "")) if match else None
    ws = web.WebSocketResponse(heartbeat=20, max_msg_size=guard.SOCKET_MSG_MAX)
    await ws.prepare(req)
    if seat is None:
        await ws.send_json({"t": "error", "error": "unknown match or seat"})
        await ws.close()
        return ws
    conns = hub.sockets.setdefault(match.id, set())
    conns.add((ws, seat))
    await ws.send_json({"t": "build", "build": BUILD})
    await ws.send_json({"t": "view", "view": match.view(seat)})
    hub.kick_bot(match)
    burst, (burst_n, burst_s) = [], guard.SOCKET_BURST
    try:
        async for msg in ws:
            if msg.type != WSMsgType.TEXT:
                continue
            now = time.monotonic()
            if '"played"' not in msg.data[:40]:     # a screen's acknowledgements are cheap and come one per view
                burst = [t for t in burst if now - t < burst_s] + [now]
            if len(burst) > burst_n:          # no screen sends this many: a loop, which would cost every player a view each
                log.warning("socket of match %s seat %s sent %d messages in %ss: closed", match.id, seat, len(burst), burst_s)
                await ws.send_json({"t": "error", "error": "too many messages"})
                await ws.close()
                break
            before = _changed(match)
            try:
                data = json.loads(msg.data)
                if not isinstance(data, dict):
                    raise ValueError("a message is a JSON object")
                kind = data.get("t")
                if kind == "act":
                    match.act(seat, data["action"])
                elif kind == "deck":
                    match.set_deck(seat, custom_decks.resolve(data["deck"]))
                elif kind == "ready":
                    match.ready(seat)
                elif kind == "next":
                    if match.phase == "playing":      # the other player already started it
                        continue
                    match.next_game()
                elif kind == "played":                # the client has played the events up to this one on screen (_watched);
                    seq = data.get("seq") or 0         # a clock that waited for it starts now
                    if not isinstance(seq, (int, float)) or isinstance(seq, bool) or not -1 < seq < 1 << 53:
                        raise ValueError("seq: a number")
                    if not match.played_out(seat, int(seq)):
                        continue
                elif kind == "hold":                  # the tutorial: its coach holds the opponent while a line awaits Next
                    match.hold = bool(data.get("on")) and match.tutorial
                    continue
                elif kind == "concede":
                    match.concede(seat)
                elif kind == "rematch":
                    match.offer_rematch(seat)
                elif kind == "rematch_decline":
                    match.decline_rematch(seat)
                else:
                    raise EngineError(f"unknown message {str(kind)[:40]!r}")
            except (EngineError, KeyError, ValueError, TypeError, AttributeError, OverflowError) as e:
                # a message the match refuses, or one no client sends (a wrong type anywhere in it): said, and the view again
                if not isinstance(e, (EngineError, KeyError, ValueError)):
                    log.info("match %s seat %s sent a malformed message: %r", match.id, seat, e)
                await hub._send(match.id, ws, seat, {"t": "error", "error": str(e)[:300]})    # the screen may have gone meanwhile
                await hub._send(match.id, ws, seat, {"t": "view", "view": match.view(seat)})
                continue
            if _changed(match) != before:
                await hub.push(match)
    finally:
        conns.discard((ws, seat))
        s = match.seats.get(seat)
        if s and s.profile and match.phase == "playing":   # left a game in progress (closed the tab, lost the connection)
            events.record(profiles.db, s.profile, "left_mid_game", {
                "match": match.id, "round": match.state.turn_counter // 2 + 1 if match.state else 0,
                "lesson": match.lesson() if match.tutorial else 0})
    return ws


def make_app() -> web.Application:
    app = web.Application()
    app.add_routes([
        web.get("/", index),
        web.get("/privacy", privacy),
        web.get("/api/pool", pool),
        web.post("/api/profile", create_profile),
        web.post("/api/signin", sign_in),
        web.get("/api/me", get_me),
        web.patch("/api/me", patch_me),
        web.put("/api/me/decks", put_decks),
        web.post("/api/auth/redeem", auth_redeem),
        web.post("/api/auth/{provider}", auth_start),
        web.post("/api/signout", sign_out),
        web.get("/auth/{provider}/callback", auth_callback),
        web.get("/api/replay/{match}", get_replay),
        web.get("/api/replay/{match}/lists", replay_lists),
        web.post("/api/replay/{match}/share", share_replay),
        web.get("/api/study/{name}", get_study),
        web.get("/api/studies", list_studies),
        web.post("/api/feedback", send_feedback),
        web.post("/api/events", client_events),
        web.get("/api/news", get_news),
        web.post("/api/news/seen", news_seen),
        web.post("/api/ranked", join_ranked),
        web.get("/api/league/pool", league_pool),
        web.post("/api/league/games", league_games),
        web.post("/api/league/retire", league_retire),
        web.post("/api/league/facts", league_facts),
        web.post("/api/league/meta/forget", league_meta_forget),
        web.get("/api/meta", meta_overview),
        web.get("/api/meta/archetype", meta_archetype),
        web.post("/api/league/decks", league_decks),
        web.post("/api/league/reset_people", league_reset_people),
        web.post("/api/league/levels", league_levels),
        web.post("/api/league/report", league_report_post),
        web.get("/api/league/report", league_report),
        web.delete("/api/ranked", leave_ranked),
        web.get("/api/leaderboard", leaderboard),
        web.get("/api/friends", friends_list),
        web.post("/api/friends", friend_add),
        web.get("/api/friends/link/{code}", friend_peek),
        web.delete("/api/friends/{id}", friend_remove),
        web.post("/api/friends/request", friend_request),
        web.get("/api/current", current_match),
        web.post("/api/friends/request/{frm}/answer", friend_request_answer),
        web.get("/api/chat/{id}", chat_history),
        web.post("/api/chat/{id}", chat_send),
        web.post("/api/chat/{id}/read", chat_read),
        web.post("/api/challenge", challenge),
        web.delete("/api/challenge", challenge_cancel),
        web.post("/api/challenge/{id}/answer", challenge_answer),
        web.get("/ws/presence", presence_socket),
        web.post("/api/match", create_match),
        web.get("/api/local/engine", local_engine),
        web.post("/api/local/setup", local_setup),
        web.get("/api/local/cand/{hash}", local_cand),
        web.post("/api/local/match", local_match),
        web.post("/api/match/{id}/join", join_match),
        web.get("/ws/{id}", socket),
        web.static("/static", STATIC),
    ])
    if os.environ.get("AK_ANALYSE"):   # the position analyser, localhost only (./play sets it; live never does)
        from . import analyse
        analyse.register(app)
    app.on_response_prepare.append(_revalidate)

    async def resume(_app):
        global profiles
        profiles = Profiles()
        linked, left = profiles.link_starters(starter_cards())
        if linked or left:
            log.info("starter decks: %d untouched cop%s now follow their starter, %d left alone",
                     linked, "y" if linked == 1 else "ies", left)
        global ladder, friends, chat, league, meta
        friends = Friends(profiles.db)
        chat = Chat(profiles.db)
        league = league_mod.Pool(profiles.db, DECK_NAMES)      # the lists the league added (web/league.py)
        ladder = ranking.Ladder(profiles.db, [s for s in sorted(BOT_DECKS) + league.slugs() if s not in league.retired()], league.levels())   # ranked offers the bot pool: shipped, ladder and league decks, less the retired
        meta = meta_mod.Meta(profiles.db, _list_of)
        with open(Path(__file__).resolve().parents[1] / "data" / ("cards" + ".json"), encoding="utf-8") as fh:
            stale = meta.track(meta_mod.card_prints(json.load(fh)["cards"]))
        if stale:
            log.info("meta: cards changed, %d lists count again from the new cards", len(stale))
        if ladder.apply_seed(Path(__file__).parent / "ladder_seed.json"):   # the bots' ratings from simulation (sim/ladder_seed.py)
            log.info("ladder: bots seeded from ladder_seed.json")
        global tiers
        tiers = tiers_mod.Tiers(profiles.db)
        placed = tiers.migrate({lid: r for lid, r in ladder.table() if not lid.startswith("bot:")})
        if placed:
            log.info("leagues: %d rated profiles placed from their rating (docs/ranked-leagues.md, Migration)", placed)
        custom_decks.load()
        replay.backfill(profiles, LOG_DIR, REPLAY_DIR)
        hub.load()
        for match in hub.matches.values():
            hub.kick_bot(match)

        async def forget_idle():
            while True:
                await asyncio.sleep(60)
                if (n := hub.forget()):
                    log.info("let go of %d idle matches (%d in memory)", n, len(hub.matches))
        _background.add(asyncio.create_task(forget_idle()))
    app.on_startup.append(resume)
    return app


async def _revalidate(request: web.Request, response: web.StreamResponse) -> None:
    """Make the browser revalidate the client on every load (a 304 when unchanged), so an edit shows on reload."""
    if request.path in ("/", "/privacy") or request.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    response.headers["Server"] = "animal-kingdom"   # not aiohttp's and Python's versions (aiohttp only sets one when none is)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="Serve the Animal Kingdom web client.")
    p.add_argument("--host", default="127.0.0.1", help="0.0.0.0 to let other machines connect")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--no-open", action="store_true", help="don't open a browser tab")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    url = f"http://localhost:{args.port}/"
    app = make_app()
    if not args.no_open:
        async def open_tab(_app):
            asyncio.get_running_loop().call_later(0.5, webbrowser.open, url)
        app.on_startup.append(open_tab)
    print(f"Animal Kingdom at {url}")
    web.run_app(app, host=args.host, port=args.port, print=None, access_log_class=guard.RedactingAccessLogger)


if __name__ == "__main__":
    main()
