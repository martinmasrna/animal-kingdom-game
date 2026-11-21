"""The web server: static client, a small JSON API to create and join matches, and one
WebSocket per player that pushes that seat's view after every change.

Run: `./play` (or `python -m animal_kingdom.web.server --port 8000`). Every match is saved to
`results/web_matches/` after each change and reloaded on start, so a restart doesn't end it.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import secrets
import subprocess
import time
import webbrowser
from pathlib import Path

from aiohttp import WSMsgType, web

from ..game import CARDS, COPY_LIMITS, LEADERS, Config, EngineError, power_price
from ..decks import DECK_SIZE
from . import custom_decks, events, feedback, guard, oauth
from .chat import Chat, ChatError
from .friends import FriendError, Friends
from .match import DECK_NAMES, Match, Seat, card_pool, map_info
from .profiles import DECKS_MAX, ProfileError, Profiles, clean_name
from .renamed import RENAMED_IDS, renamed as _renamed


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
# Human games are the best design signal there is: every game with a human seat is kept, one JSONL file per match,
# replayable with `python -m animal_kingdom.replay FILE --index N`.
LOG_DIR = Path(__file__).resolve().parents[2] / "results" / "human_games" / "web"
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
BOT_THINK_MAX = 20          # seconds a bot move may take before the first legal move is played for it


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
        match.on_game_end = record_match
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
        now = (match.phase, match.rematches)
        was = self.noted.get(match.id)
        self.noted[match.id] = now
        if now == was:
            return
        people = [(p, s) for p, s in match.seats.items() if not s.is_bot and s.profile]
        if match.phase == "playing":
            for p, s in people:
                opp = match.seats.get("B" if p == "A" else "A")
                events.record(profiles.db, s.profile, "game_start", {
                    "match": match.id, "game": match.rematches + 1, "deck": s.deck,
                    "opp": opp and ("bot" if opp.is_bot else "person"), "opp_deck": opp and opp.deck})
        elif match.phase == "match_over" and match.result:
            r = match.result
            for p, s in people:
                events.record(profiles.db, s.profile, "game_end", {
                    "match": match.id, "game": match.rematches + 1, "won": r["winner"] == p, "reason": r["reason"],
                    "rounds": r["turns"]})

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
        while (s := match.to_act()) is not None and match.seats[s].is_bot:
            opening = not match.state.pending and match.state.mana_spent == 0
            await self._watched(match)
            await asyncio.sleep(BOT_PAUSE["choice" if match.state.pending else "open" if opening else "move"])
            version = match.version
            try:
                action = await asyncio.wait_for(asyncio.get_running_loop().run_in_executor(None, match.bot_move), BOT_THINK_MAX)
            except Exception:   # never a frozen match when a bot fails or hangs: a plain legal move instead
                log.exception("bot failed in match %s; playing the first legal move", match.id)
                action = match.fallback_move()
            if match.version != version:     # the position moved under the bot (a rematch, a concede)
                continue
            try:
                match.act(s, action)
            except Exception:
                log.exception("bot move refused in match %s; playing the first legal move", match.id)
                if match.version != version or match.to_act() != s:
                    continue
                try:
                    match.act(s, match.fallback_move())
                except Exception:   # the position itself is broken: say so loudly and stop hammering it
                    log.exception("bot gives up in match %s", match.id)
                    return
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


# The cards a player's saved decks keep: every card of the game.
COLLECTION = set(CARDS)


def profile_view(p: dict) -> dict:
    return {**p, "decks": profiles.decks(p["id"], COLLECTION, RENAMED_IDS),
            "logins": profiles.identities(p["id"]), "providers": oauth.available(), "patchSeen": profiles.patch_seen(p["id"])}


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
            profiles.save_decks(p["id"], body["decks"])
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


async def see_patch(req):
    """The patch notes were opened: that patch is seen, on every device of this profile."""
    profiles.see_patch(me(req)["id"], (await guard.body(req)).get("version", ""))
    return web.json_response({})


async def put_decks(req):
    try:
        decks = profiles.save_decks(me(req)["id"], await guard.body(req, list))
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
    return web.json_response({})


def record_match(match: Match, record: dict) -> None:
    """A finished game: its log, and a line in each person's match history (deploy/deploy.sh players reads it)."""
    save_game(match, record)
    r = match.result
    for p, seat in match.seats.items():
        if not seat.profile or seat.is_bot:
            continue
        other = match.seats["B" if p == "A" else "A"]
        try:
            profiles.record(seat.profile, f"{match.id}-{match.rematches}", kind="bot" if other.is_bot else "friend",
                            my_deck=DECK_NAMES.get(seat.deck, seat.deck), opp="Bot" if other.is_bot else other.name,
                            opp_deck=DECK_NAMES.get(other.deck, other.deck) if other.is_bot else "",   # a person's deck name is theirs
                            won=int(r["winner"] == p), lost=int(r["winner"] not in (p, None)))
        except Exception:
            log.exception("could not record match %s in a history", match.id)


def _open(match: Match) -> None:
    match.on_game_end = record_match
    hub.matches[match.id] = match
    hub.save(match)
    hub.kick_bot(match)


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
    a phone that dropped the page). Not a bot match you never made a move in."""
    p = profile_of(req)
    if not p:
        return web.json_response({})
    live = lambda m: time.time() - (m.started_at + (m.action_times[-1] if m.action_times else 0)) < REJOIN_WITHIN
    # a person waits for you; a bot match only once you've made a move in it (one left at the mulligan is left)
    started = lambda m, seat: not any(o.is_bot for o in m.seats.values()) or any(h.seat == seat for h in m.history)
    mine = [(m, s) for m in hub.matches.values() if m.phase == "playing" and live(m)
            for seat, s in m.seats.items() if s.profile == p["id"] and started(m, seat)]
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
        "map": map_info(),
        "build": BUILD,
        # The deck rules the collection builds to (decks.py, engine/cards.py, profiles.py): the client holds none of these numbers itself.
        "rules": {"deckSize": DECK_SIZE, "copies": COPY_LIMITS, "decksMax": DECKS_MAX},
        # the cards that can lead a deck, each with its kind and its ability (engine/leaders.py)
        "leaders": {lid: {"kind": kind, "text": text, **({"cost": power_price(lid, Config())} if kind == "power" else {})}
                    for lid, (kind, text) in LEADERS.items()},
    })


def guest_name(body: dict, default: str) -> str:
    """A seat's name for a player with no profile: cleaned like a profile's, and with no #tag (a tag is a profile's)."""
    try:
        return clean_name(str(body.get("name") or "").split("#")[0])
    except ProfileError:
        return default


async def create_match(req):
    """A match: against the bot ("bot": true; it plays "bot_deck", chosen in Practice, else a mirror of yours), or a
    lobby a friend joins by its code."""
    guard.limit_ip(req, "match")
    body = await guard.body(req)
    try:
        deck = custom_decks.resolve(body.get("deck"))
        bot_deck = custom_decks.resolve(body["bot_deck"]) if body.get("bot") and body.get("bot_deck") else deck
    except EngineError as e:
        raise web.HTTPBadRequest(text=str(e))
    mid, token = hub.new_id(), secrets.token_urlsafe(12)
    player = profile_of(req)
    match = Match(mid, Seat(token, display(player) if player else guest_name(body, "You"), deck=deck,
                            profile=player and player["id"]))
    if body.get("bot"):
        match.join(Seat(secrets.token_urlsafe(12), "Bot", bot=True, deck=bot_deck))
    else:
        match.version += 1
    _open(match)
    return web.json_response({"id": mid, "token": token, "seat": "A"})


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
    return match.version, match.phase, match.rematches, match.seq


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
                elif kind == "played":                # the client has played the events up to this one on screen (_watched);
                    seq = data.get("seq") or 0         # a clock that waited for it starts now
                    if not isinstance(seq, (int, float)) or isinstance(seq, bool) or not -1 < seq < 1 << 53:
                        raise ValueError("seq: a number")
                    if not match.played_out(seat, int(seq)):
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
                "match": match.id, "round": match.state.turn_counter // 2 + 1 if match.state else 0})
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
        web.post("/api/me/patch", see_patch),
        web.post("/api/auth/redeem", auth_redeem),
        web.post("/api/auth/{provider}", auth_start),
        web.post("/api/signout", sign_out),
        web.get("/auth/{provider}/callback", auth_callback),
        web.post("/api/feedback", send_feedback),
        web.post("/api/events", client_events),
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
        web.post("/api/match/{id}/join", join_match),
        web.get("/ws/{id}", socket),
        web.static("/static", STATIC),
    ])
    app.on_response_prepare.append(_revalidate)

    async def resume(_app):
        global profiles
        profiles = Profiles()
        global friends, chat
        friends = Friends(profiles.db)
        chat = Chat(profiles.db)
        custom_decks.load()
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
