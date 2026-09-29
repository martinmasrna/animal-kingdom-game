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
import time
import webbrowser
from pathlib import Path

from aiohttp import WSMsgType, web

from ..decks import PREMADE_DECKS, load_premade_deck
from ..engine.state import EngineError
from ..engine.cards import DECK_SLUGS
from . import custom_decks
from .profiles import ProfileError, Profiles
from .match import BOT_LEVELS, DECK_NAMES, Match, Seat, card_pool, map_info

STATIC = Path(__file__).parent / "static"
# Human games are the best design signal there is: every game with a human seat is kept,
# one JSONL file per match, replayable with `python -m animal_kingdom.sim.replay FILE --index N`.
LOG_DIR = Path(__file__).resolve().parents[2] / "results" / "human_games" / "web"
MATCH_DIR = Path(__file__).resolve().parents[2] / "results" / "web_matches"
KEEP_FINISHED = 24 * 3600    # seconds a finished match is still reloaded after a restart
BOT_PAUSE = {"open": 1.6, "move": 1.1, "choice": 0.6}   # seconds: a beat before the bot opens its turn, then time to follow each move
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


class Hub:
    def __init__(self):
        self.matches: dict[str, Match] = {}
        self.sockets: dict[str, set] = {}        # match id -> {(ws, seat)}
        self.bot_tasks: dict[str, asyncio.Task] = {}

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
        for ws, seat in list(self.sockets.get(match.id, ())):
            try:
                await ws.send_json({"t": "view", "view": match.view(seat)})
            except (ConnectionResetError, RuntimeError):
                self.sockets[match.id].discard((ws, seat))

    async def push(self, match: Match) -> None:
        await self.broadcast(match)
        self.kick_bot(match)

    def kick_bot(self, match: Match) -> None:
        s = match.to_act()
        if s is None or not match.seats[s].is_bot:
            return
        task = self.bot_tasks.get(match.id)
        if task is None or task.done():
            self.bot_tasks[match.id] = asyncio.create_task(self._run_bot(match))

    async def _run_bot(self, match: Match) -> None:
        while (s := match.to_act()) is not None and match.seats[s].is_bot:
            opening = not match.state.pending and match.state.actions_taken_this_turn == 0
            await asyncio.sleep(BOT_PAUSE["choice" if match.state.pending else "open" if opening else "move"])
            version = match.version
            try:
                action = await asyncio.to_thread(match.bot_move)
            except Exception:
                log.exception("bot failed in match %s", match.id)
                return
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


def profile_view(p: dict) -> dict:
    return {**p, "decks": profiles.decks(p["id"]), "history": profiles.history(p["id"])}


async def create_profile(req):
    body = await req.json() if req.can_read_body else {}
    try:
        code, p = profiles.create(body.get("name") or "Player")
        if body.get("decks"):
            profiles.save_decks(p["id"], body["decks"])
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
        decks = profiles.save_decks(me(req)["id"], await req.json())
    except ProfileError as e:
        raise web.HTTPBadRequest(text=str(e))
    return web.json_response(decks)


async def sign_in(req):
    body = await req.json()
    p = profiles.by_code(body.get("code", ""))
    if p is None:
        raise web.HTTPNotFound(text="no profile has that sign-in code")
    return web.json_response(profile_view(p))


def record_match(match: Match) -> None:
    """Add a finished series to each human player's history."""
    kind = "gauntlet" if match.schedule else "bot" if any(s.is_bot for s in match.seats.values()) else "friend"
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
                            opp=f"Bot · {other.bot.capitalize()}" if other.is_bot else other.name,
                            opp_deck=deck(o), won=score[p], lost=score[o])
        except Exception:
            log.exception("could not record match %s in a history", match.id)


async def index(_req):
    return web.FileResponse(STATIC / "index.html")


async def pool(_req):
    return web.json_response({
        "cards": card_pool(),
        "decks": [{"id": slug, "name": DECK_NAMES.get(slug, slug), "list": load_premade_deck(slug)}
                  for slug in DECK_NAMES if slug in PREMADE_DECKS or slug == "goodstuff"],
        "map": map_info(),
        "levels": list(BOT_LEVELS),
    })


async def create_match(req):
    body = await req.json()
    try:
        deck = custom_decks.resolve(body.get("deck"))
    except EngineError as e:
        raise web.HTTPBadRequest(text=str(e))
    mid, token = hub.new_id(), secrets.token_urlsafe(12)
    player = profile_of(req)
    match = Match(mid, Seat(token, display(player) if player else body.get("name") or "You", deck=deck,
                            profile=player and player["id"]))
    bot = body.get("bot")
    gauntlet = body.get("gauntlet")
    if gauntlet:
        level = gauntlet.get("level", "normal")
        if level not in BOT_LEVELS:
            raise web.HTTPBadRequest(text="bad bot level")
        field = [d for d in sorted(DECK_SLUGS) if d != deck]
        match.join(Seat(secrets.token_urlsafe(12), f"Bot · {level.capitalize()}", bot=level, deck=field[0]))
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
        match.join(Seat(secrets.token_urlsafe(12), f"Bot · {bot['level'].capitalize()}",
                        bot=bot["level"], deck=bot["deck"]))
    else:
        match.version += 1
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
                elif kind == "rematch":
                    match.rematch()
                elif kind == "note":
                    match.add_note(seat, str(data.get("text", "")))
                    continue                          # nothing on screen changes
                else:
                    raise EngineError(f"unknown message {kind!r}")
            except (EngineError, KeyError, ValueError) as e:
                await ws.send_json({"t": "error", "error": str(e)})
                await ws.send_json({"t": "view", "view": match.view(seat)})
                continue
            await hub.push(match)
    finally:
        conns.discard((ws, seat))
    return ws


def make_app() -> web.Application:
    app = web.Application()
    app.add_routes([
        web.get("/", index),
        web.get("/api/pool", pool),
        web.post("/api/profile", create_profile),
        web.post("/api/signin", sign_in),
        web.get("/api/me", get_me),
        web.patch("/api/me", patch_me),
        web.put("/api/me/decks", put_decks),
        web.post("/api/match", create_match),
        web.post("/api/match/{id}/join", join_match),
        web.get("/ws/{id}", socket),
        web.static("/static", STATIC),
    ])
    app.on_response_prepare.append(_revalidate)

    async def resume(_app):
        global profiles
        profiles = Profiles()
        custom_decks.load()
        hub.load()
        for match in hub.matches.values():
            hub.kick_bot(match)
    app.on_startup.append(resume)
    return app


async def _revalidate(request: web.Request, response: web.StreamResponse) -> None:
    """Make the browser revalidate the client on every load (a 304 when unchanged), so an edit shows on reload."""
    if request.path == "/" or request.path.startswith("/static/"):
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
