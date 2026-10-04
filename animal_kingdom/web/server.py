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
import time
import webbrowser
from collections import Counter
from pathlib import Path

from aiohttp import WSMsgType, web

from ..decks import PREMADE_DECKS, load_premade_deck
from ..engine.state import EngineError
from ..engine.cards import DECK_SLUGS, load_cards
from . import custom_decks
from . import events, feedback, news
from .chat import Chat, ChatError
from .friends import FriendError, Friends
from . import ladder as ranking
from . import oauth
from .profiles import ProfileError, Profiles
from . import replay
from . import tutorial
from .match import BOT_LEVELS, DECK_NAMES, Match, Seat, card_pool, map_info

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
BOT_PAUSE = {"open": 0.6, "move": 0.4, "choice": 0.3}   # seconds: the bot's thinking beat, once the players have watched its last move
BOT_WAIT_MAX = 6.0          # seconds a bot waits for a player's screen to play its last move out (a stalled client never stalls it)
if os.environ.get("AK_BOT_PAUSE") is not None:   # the test harness sets 0: tests wait on nothing a player needs to follow
    BOT_PAUSE = {k: v * float(os.environ["AK_BOT_PAUSE"]) for k, v in BOT_PAUSE.items()}
log = logging.getLogger("animal_kingdom.web")


def save_game(match: Match, record: dict) -> None:
    if os.environ.get("AK_NO_GAME_LOGS") or all(seat.is_bot for seat in match.seats.values()):
        return
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        stamp = match.created.strftime("%Y%m%dT%H%M%S")
        with open(LOG_DIR / f"web_{stamp}_{match.id}.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except OSError:
        log.exception("could not save the game log for match %s", match.id)


BOT_THINK_MAX = 15          # seconds a bot may think before the Easy bot's move is played for it


class Hub:
    def __init__(self):
        self.matches: dict[str, Match] = {}
        self.sockets: dict[str, set] = {}        # match id -> {(ws, seat)}
        self.bot_tasks: dict[str, asyncio.Task] = {}
        self.noted: dict[str, tuple] = {}        # match id -> (phase, games ended) as last recorded (note)
        self.clock_tasks: dict[str, asyncio.Task] = {}

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
        except Exception:
            log.exception("could not save match %s", match.id)

    def load(self) -> None:
        """Reload saved matches: every unfinished one, and finished ones from the last day."""
        if not MATCH_DIR.is_dir():
            return
        now = time.time()
        for path in MATCH_DIR.glob("*.json"):
            try:
                d = json.loads(path.read_text(encoding="utf-8"))
                if d["phase"] == "match_over" and now - path.stat().st_mtime > KEEP_FINISHED:
                    continue
                match = Match.from_dict(d)
            except Exception:
                log.exception("could not reload %s", path.name)
                continue
            match.on_game_end = save_game
            match.on_match_end = record_match
            self.matches[match.id] = match
        log.info("reloaded %d saved matches", len(self.matches))

    async def broadcast(self, match: Match) -> None:
        self.save(match)
        self.note(match)
        for ws, seat in list(self.sockets.get(match.id, ())):
            try:
                await ws.send_json({"t": "view", "view": match.view(seat)})
            except (ConnectionResetError, RuntimeError):
                self.sockets[match.id].discard((ws, seat))

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
            self.bot_tasks[match.id] = asyncio.create_task(self._run_bot(match))

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
            opening = not match.state.pending and match.state.actions_taken_this_turn == 0
            await self._watched(match)
            await asyncio.sleep(BOT_PAUSE["choice" if match.state.pending else "open" if opening else "move"])
            while match.hold:                 # the tutorial's coach is talking: the opponent waits for its Next (the client
                await asyncio.sleep(0.1)      # lets go only once what Next set off has played)
            version = match.version
            try:
                action = await asyncio.wait_for(asyncio.to_thread(match.bot_move), BOT_THINK_MAX)
            except asyncio.TimeoutError:   # never a hanging opponent (feedback 2026-10-01: an Expert move took 4 minutes on a throttled CPU)
                log.warning("bot over %ss in match %s; playing a fallback move", BOT_THINK_MAX, match.id)
                action = match.fallback_move()
            except Exception:   # nor a frozen match when a bot fails: a plain legal move instead
                log.exception("bot failed in match %s; playing a fallback move", match.id)
                action = match.fallback_move()
            if match.version != version:     # the position moved under the bot (rematch etc.)
                continue
            match.act(s, action)
            await self.broadcast(match)


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


# A profile starts with the starter decks as its own (covers as on the play screen).
STARTER_COVERS = {"cats_midrange": "king_theron", "canine_buff_tempo": "lobo", "aggro_hq_rush": "verminus",
                  "colony_food_swarm": "queen_honoria", "egg_control": "eon", "food_otk": "rat_king", "ramp": "borealis",
                  "goodstuff": "gale"}


def starter_decks() -> list[dict]:
    out = []
    for slug in DECK_NAMES:
        if slug not in PREMADE_DECKS:
            continue
        cards: dict = {}
        for cid in load_premade_deck(slug):
            cards[cid] = cards.get(cid, 0) + 1
        out.append({"id": slug, "name": DECK_NAMES[slug], "cards": cards, "cover": STARTER_COVERS.get(slug, "")})
    return out


def starter_cards() -> dict[str, dict]:
    """Every starter's id -> its current {card id: copies}, for resolving a profile's unedited copies."""
    return {d["id"]: d["cards"] for d in starter_decks()}


def profile_view(p: dict) -> dict:
    starters = starter_decks()
    profiles.seed_decks(p["id"], starters)
    return {**p, "decks": profiles.decks(p["id"], {d["id"]: d["cards"] for d in starters}),
            "history": profiles.history(p["id"]), "records": profiles.records(p["id"]),
            "logins": profiles.identities(p["id"]), "providers": oauth.available(),
            "rating": ladder.get(p["id"]).shown() if ladder else None, **standing(p["id"])}


def bot_levels(table) -> dict[str, float]:
    """Each bot level's rating on the leaderboard: its decks' ratings averaged by games played."""
    levels: dict[str, list] = {}
    for lid, r in table:
        if (b := ranking.parse_bot(lid)):
            levels.setdefault(b[0], []).append(r)
    return {level: sum(r.rating * max(1, r.games) for r in rs) / sum(max(1, r.games) for r in rs) for level, rs in levels.items()}


def standing(pid: str) -> dict:
    """Where you stand, for home's name piece: your place among the ranked (people and bots), or your placement games so far."""
    if not ladder:
        return {}
    r = ladder.get(pid)
    if r.provisional:
        return {"placing": {"games": r.games, "of": ranking.PROVISIONAL}}
    # your row's place on the leaderboard: the ranked people and the bot levels above you
    table = ladder.table()
    above = sum(1 for lid, x in table if not lid.startswith("bot:") and not x.provisional and x.rating > r.rating)
    return {"rank": 1 + above + sum(1 for avg in bot_levels(table).values() if avg > r.rating)}


# ----------------------------------------------------------------- sign in with Google / Discord
flow = oauth.Flow()


def callback_url(req, provider: str) -> str:
    base = os.environ.get("AK_BASE_URL") or f"{req.headers.get('X-Forwarded-Proto', req.scheme)}://{req.host}"
    return f"{base}/auth/{provider}/callback"


async def auth_start(req):
    provider, player = req.match_info["provider"], profile_of(req)
    try:
        url = flow.start(provider, player and player["id"], callback_url(req, provider))
    except oauth.OAuthError as e:
        raise web.HTTPBadRequest(text=str(e))
    return web.json_response({"url": url})


async def auth_callback(req):
    provider = req.match_info["provider"]
    try:
        if "code" not in req.query:
            raise oauth.OAuthError(req.query.get("error", "sign-in cancelled"))
        guest = flow.claim(provider, req.query.get("state", ""))
        subject, label = await oauth.identify(provider, req.query["code"], callback_url(req, provider))
        p = profiles.sign_in(provider, subject, label, guest)
        raise web.HTTPFound(f"/#/auth/{flow.hand_off(profiles.new_session(p['id']))}")
    except oauth.OAuthError as e:
        log.info("sign-in with %s failed: %s", provider, e)
        raise web.HTTPFound("/#/auth/failed")


async def auth_redeem(req):
    key = flow.redeem((await req.json()).get("code", ""))
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
    body = await req.json() if req.can_read_body else {}
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
    body = await req.json()
    try:
        p = profiles.rename(me(req)["id"], body.get("name"))
    except ProfileError as e:
        raise web.HTTPBadRequest(text=str(e))
    return web.json_response(profile_view(p))


async def put_decks(req):
    try:
        decks = profiles.save_decks(me(req)["id"], await req.json(), starter_cards())
    except ProfileError as e:
        raise web.HTTPBadRequest(text=str(e))
    return web.json_response(decks)


async def sign_in(req):
    body = await req.json()
    p = profiles.by_code(body.get("code", ""))
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
                            opp=f"Bot ({other.bot.capitalize()})" if other.is_bot else other.name,
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
    """Every view you saw in one of your finished matches (key: the history's match), as saved when it ended: a JSON list."""
    p = me(req)
    key = req.match_info["match"]
    row = profiles.match(p["id"], key)
    saved = row and row["seat"] and replay.load(REPLAY_DIR, key, row["seat"])
    if not saved:
        raise web.HTTPNotFound(text="This match can't be replayed")
    return web.Response(body=saved, content_type="application/json", headers={"Content-Encoding": "gzip"})


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
    p, body = me(req), await req.json()
    news.mark(profiles.db, p["id"], opened=str(body.get("opened") or "")[:10], shown=str(body.get("shown") or "")[:10])
    return web.json_response({})


async def client_events(req):
    """What the client saw the player do (web/events.py), in batches."""
    p, body = me(req), await req.json()
    return web.json_response({"kept": events.record_client(profiles.db, p["id"], body.get("events"))})


async def send_feedback(req):
    """A player's message and the moment it was sent from: kept, then mailed to Martin in the background."""
    p, body = me(req), await req.json()
    context = {k: v for k, v in (body.get("context") or {}).items() if isinstance(v, (str, int, float))}
    try:
        feedback.keep(profiles.db, p["id"], display(p), body.get("text"), context, body.get("view"))
    except feedback.FeedbackError as e:
        raise web.HTTPBadRequest(text=str(e))
    asyncio.get_running_loop().run_in_executor(None, feedback.mail, display(p), body["text"].strip(), context, body.get("view"))
    return web.json_response({})


# ----------------------------------------------------------------- the ladder (web/ladder.py)
RANKED_WAIT = 15            # seconds the queue waits for a person near your rating before giving you a bot
waiting: list[dict] = []    # people in the ranked queue: {pid, name, deck, rating, since, fut}
ladder: ranking.Ladder = None


def _window(entry: dict, now: float) -> float:
    """How far apart two people's ratings may be to meet: wider the longer they've waited."""
    return 200 + 20 * (now - entry["since"])


async def join_ranked(req):
    """Join the ranked queue with a deck; the answer is your match ({id, token, seat}) once there is one: a person near
    your rating if one is waiting or arrives within RANKED_WAIT seconds, else the nearest bot. Leaving the request leaves
    the queue."""
    p, body = me(req), await req.json()
    try:
        deck = custom_decks.resolve(body.get("deck"))
    except EngineError as e:
        raise web.HTTPBadRequest(text=str(e))
    r, now = ladder.get(p["id"]).rating, time.time()
    for w in waiting:   # someone already waiting near enough: the match is theirs and yours
        if w["pid"] != p["id"] and not w["fut"].done() and abs(w["rating"] - r) <= _window(w, now):
            waiting.remove(w)
            mid, ta, tb = hub.new_id(), secrets.token_urlsafe(12), secrets.token_urlsafe(12)
            match = Match(mid, Seat(ta, w["name"], deck=w["deck"], profile=w["pid"], ladder=w["pid"]))
            match.join(Seat(tb, display(p), deck=deck, profile=p["id"], ladder=p["id"]))
            _open(match)
            w["fut"].set_result({"id": mid, "token": ta, "seat": "A"})
            return web.json_response({"id": mid, "token": tb, "seat": "B"})
    entry = {"pid": p["id"], "name": display(p), "deck": deck, "rating": r, "since": now,
             "fut": asyncio.get_running_loop().create_future()}
    waiting[:] = [w for w in waiting if w["pid"] != p["id"]] + [entry]   # one place in the queue per person
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
    recent = [h["opp_deck"] for h in profiles.history(p["id"]) if h.get("mode") == "ranked" and h["opp"].startswith("Bot (")][:2]
    slug = {name: s for s, name in DECK_NAMES.items()}
    bid = ladder.nearest_bot(r, random, avoid={slug.get(d, d) for d in recent})   # never the deck of your last two bot games
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
    # A ranked match states both ratings as they stand going in (the versus moment shows them). A bot shows its level's
    # rating, the one the leaderboard lists (Martin, 2026-10-04: one number per bot everywhere); matchmaking still rates
    # each of its decks on its own, out of sight.
    for seat in match.seats.values():
        if seat.ladder:
            bot = ranking.parse_bot(seat.ladder)
            seat.rating = str(round(bot_levels(ladder.table())[bot[0]])) if bot else ladder.get(seat.ladder).shown()
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
    match.rating_change = {p: {"before": before[p].shown(), "after": ladder.get(match.seats[p].ladder).shown(),
                               # the change between the numbers shown, so "1502 → 1490 (−12)" always adds up
                               "delta": round(ladder.get(match.seats[p].ladder).rating) - round(before[p].rating)} for p in "AB"}
    match.version += 1


def ladder_name(lid: str) -> str:
    bot = ranking.parse_bot(lid)
    if bot:
        return f"{DECK_NAMES.get(bot[1], bot[1])} ({bot[0].capitalize()} Bot)"
    p = profiles.get(lid)
    return display(p) if p else "?"


async def leaderboard(req):
    """Everyone ranked on the ladder, best first (name, rating, whether it's a bot, whether it's you); a player still placing
    (under ladder.PROVISIONAL games) isn't ranked yet and sees their own progress instead."""
    p = profile_of(req)
    mine, asked = (set(friends.of(p["id"])), friends.asked(p["id"])) if p else (set(), set())
    table = ladder.table()
    rows = [(r.rating, {"name": ladder_name(lid), "rating": r.shown(), "bot": False, "you": bool(p and lid == p["id"]),
                        **({} if p and lid == p["id"] else {"id": lid, "friend": lid in mine, "asked": lid in asked})})   # whether you're friends or have asked
            for lid, r in table if not lid.startswith("bot:") and not r.provisional]   # still placing: not ranked yet (as on Lichess)
    # The bots as one row per level (Martin, 2026-10-02: 21 level-and-deck rows cluttered it): its decks' ratings averaged
    # by games played. Matchmaking still rates each deck on its own (a bot plays some decks far better than others).
    for level, avg in bot_levels(table).items():
        rows.append((avg, {"name": f"{level.capitalize()} Bot", "rating": str(round(avg)), "bot": True, "you": False}))
    rows = [row for _, row in sorted(rows, key=lambda x: -x[0])]
    me_ = ladder.get(p["id"]) if p else None
    placing = {"name": display(p), "rating": me_.shown(), "games": me_.games, "of": ranking.PROVISIONAL} \
        if me_ and me_.provisional and me_.games else None
    return web.json_response({"rows": rows, "placing": placing})


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
    for ws in list(presence.get(pid, ())):
        try:
            await ws.send_json(msg)
        except Exception:
            pass


async def _tell_friends_online(pid: str, on: bool) -> None:
    """A player came online (their first open tab) or went away (their last closed): their friends' Friends buttons count it."""
    for fid in friends.of(pid):
        await _tell(fid, {"t": "online", "id": pid, "on": on})


async def presence_socket(req):
    """Online while open; carries challenges to you. The client opens it once it knows its profile."""
    p = profiles.by_code(req.query.get("key", ""))
    ws = web.WebSocketResponse(heartbeat=20)
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
        presence[p["id"]].discard(ws)
        if not presence[p["id"]]:
            del presence[p["id"]]
            friends.seen(p["id"])
            await _tell_friends_online(p["id"], False)
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
    p, body = me(req), await req.json()
    try:
        other = friends.add(p["id"], body.get("code"))
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
    p, body = me(req), await req.json()
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
    p, body = me(req), await req.json()
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
    p, other, body = me(req), req.match_info["id"], await req.json()
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
    p, body = me(req), await req.json()
    to = body.get("friend")
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
    p, body = me(req), await req.json()
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
        "decks": [{"id": slug, "name": DECK_NAMES.get(slug, slug), "list": load_premade_deck(slug)}
                  for slug in DECK_NAMES if slug in PREMADE_DECKS or slug == "goodstuff"],
        "map": map_info(),
        "levels": list(BOT_LEVELS),
        "build": BUILD,
    })


async def create_match(req):
    body = await req.json()
    try:
        lesson = int(body.get("tutorial") or 0)    # the tutorial's lesson: 1 or 2
        if lesson not in (0, *tutorial.BOTS):
            raise EngineError("no such lesson")
        deck = f"{tutorial.BOTS[lesson]}_you" if lesson else custom_decks.resolve(body.get("deck"))
    except EngineError as e:
        raise web.HTTPBadRequest(text=str(e))
    mid, token = hub.new_id(), secrets.token_urlsafe(12)
    player = profile_of(req)
    match = Match(mid, Seat(token, display(player) if player else body.get("name") or "You", deck=deck,
                            profile=player and player["id"]))
    bot = body.get("bot")
    gauntlet = body.get("gauntlet")
    if lesson:     # the lesson's fixed deal against its opponent, straight into the game
        match.join(Seat(secrets.token_urlsafe(12), "Wild dogs", bot=tutorial.BOTS[lesson], deck=f"{tutorial.BOTS[lesson]}_them"))
        match.ready("A")
    elif gauntlet:
        level = gauntlet.get("level", "normal")
        if level not in BOT_LEVELS:
            raise web.HTTPBadRequest(text="bad bot level")
        field = [d for d in sorted(DECK_SLUGS) if d != deck]
        match.join(Seat(secrets.token_urlsafe(12), f"Bot ({level.capitalize()})", bot=level, deck=field[0]))
        if gauntlet.get("reverse"):     # the bot keeps the chosen deck; the player plays the field
            match.seats["B"].deck = deck
            match.make_gauntlet(field, per_seat=5, rotating="A")
        else:
            match.make_gauntlet(field, per_seat=5)
        match._start_game()
        match.version += 1
    elif bot:
        if bot.get("level") not in BOT_LEVELS or bot.get("deck") not in {*PREMADE_DECKS, "goodstuff"}:
            raise web.HTTPBadRequest(text="bad bot")
        match.join(Seat(secrets.token_urlsafe(12), f"Bot ({bot['level'].capitalize()})",
                        bot=bot["level"], deck=bot["deck"]))
    else:
        match.version += 1
    if not match.tutorial:      # a tutorial is neither a game log for balance nor a match in the history
        match.on_game_end = save_game
        match.on_match_end = record_match
    hub.matches[mid] = match
    hub.save(match)
    return web.json_response({"id": mid, "token": token, "seat": "A"})


async def join_match(req):
    match = hub.matches.get(req.match_info["id"])
    if match is None:
        raise web.HTTPNotFound(text="no such match")
    body = await req.json()
    try:
        deck = custom_decks.resolve(body.get("deck"))
    except EngineError as e:
        raise web.HTTPBadRequest(text=str(e))
    token = secrets.token_urlsafe(12)
    player = profile_of(req)
    try:
        seat = match.join(Seat(token, display(player) if player else body.get("name") or "Friend", deck=deck,
                               profile=player and player["id"]))
    except EngineError as e:
        raise web.HTTPConflict(text=str(e))
    await hub.push(match)
    return web.json_response({"id": match.id, "token": token, "seat": seat})


async def socket(req):
    match = hub.matches.get(req.match_info["id"])
    seat = match.seat_of(req.query.get("token", "")) if match else None
    ws = web.WebSocketResponse(heartbeat=20)
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
    try:
        async for msg in ws:
            if msg.type != WSMsgType.TEXT:
                continue
            data = msg.json()
            try:
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
                elif kind == "played":                # the client has played the events up to this one on screen (_watched)
                    match.played[seat] = int(data.get("seq") or 0)
                    continue
                elif kind == "hold":                  # the tutorial: its coach holds the opponent while a line awaits Next
                    match.hold = bool(data.get("on")) and match.tutorial
                    continue
                elif kind == "concede":
                    match.concede(seat)
                elif kind == "rematch":
                    match.rematch()
                else:
                    raise EngineError(f"unknown message {kind!r}")
            except (EngineError, KeyError, ValueError) as e:
                await ws.send_json({"t": "error", "error": str(e)})
                await ws.send_json({"t": "view", "view": match.view(seat)})
                continue
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
        web.post("/api/feedback", send_feedback),
        web.post("/api/events", client_events),
        web.get("/api/news", get_news),
        web.post("/api/news/seen", news_seen),
        web.post("/api/ranked", join_ranked),
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
        web.post("/api/match/{id}/join", join_match),
        web.get("/ws/{id}", socket),
        web.static("/static", STATIC),
    ])
    app.on_response_prepare.append(_revalidate)

    async def resume(_app):
        global profiles
        profiles = Profiles()
        linked, left = profiles.link_starters(starter_cards())
        if linked or left:
            log.info("starter decks: %d untouched cop%s now follow their starter, %d left alone",
                     linked, "y" if linked == 1 else "ies", left)
        global ladder, friends, chat
        friends = Friends(profiles.db)
        chat = Chat(profiles.db)
        ladder = ranking.Ladder(profiles.db, [d for d in sorted(PREMADE_DECKS) if d != "goodstuff"])
        if ladder.apply_seed(Path(__file__).parent / "ladder_seed.json"):   # the bots' ratings from simulation (sim/ladder_seed.py)
            log.info("ladder: bots seeded from ladder_seed.json")
        custom_decks.load()
        replay.backfill(profiles, LOG_DIR, REPLAY_DIR)
        hub.load()
        for match in hub.matches.values():
            hub.kick_bot(match)
    app.on_startup.append(resume)
    return app


async def _revalidate(request: web.Request, response: web.StreamResponse) -> None:
    """Make the browser revalidate the client on every load (a 304 when unchanged), so an edit shows on reload."""
    if request.path in ("/", "/privacy") or request.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"


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
    web.run_app(app, host=args.host, port=args.port, print=None)


if __name__ == "__main__":
    main()
