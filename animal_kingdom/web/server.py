"""The web server: static client, a small JSON API to create and join matches, and one
WebSocket per player that pushes that seat's view after every change.

Run: `./play` (or `python -m animal_kingdom.web.server --port 8000`). Matches live in memory;
a restart ends them.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import secrets
import webbrowser
from pathlib import Path

from aiohttp import WSMsgType, web

from ..decks import PREMADE_DECKS
from ..engine.state import EngineError
from .match import BOT_LEVELS, DECK_NAMES, Match, Seat, card_pool, map_info

STATIC = Path(__file__).parent / "static"
BOT_PAUSE = {"move": 0.9, "choice": 0.6}   # seconds, so a human can follow the bot's moves
log = logging.getLogger("animal_kingdom.web")


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

    async def broadcast(self, match: Match) -> None:
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
            await asyncio.sleep(BOT_PAUSE["choice" if match.state.pending else "move"])
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


async def index(_req):
    return web.FileResponse(STATIC / "index.html")


async def pool(_req):
    return web.json_response({
        "cards": card_pool(),
        "decks": [{"id": slug, "name": DECK_NAMES.get(slug, slug), "list": PREMADE_DECKS[slug]}
                  for slug in DECK_NAMES],
        "map": map_info(),
        "levels": list(BOT_LEVELS),
    })


async def create_match(req):
    body = await req.json()
    deck = body.get("deck")
    if deck not in PREMADE_DECKS:
        raise web.HTTPBadRequest(text="unknown deck")
    mid, token = hub.new_id(), secrets.token_urlsafe(12)
    match = Match(mid, Seat(token, body.get("name") or "You", deck=deck))
    bot = body.get("bot")
    if bot:
        if bot.get("level") not in BOT_LEVELS or bot.get("deck") not in PREMADE_DECKS:
            raise web.HTTPBadRequest(text="bad bot")
        match.join(Seat(secrets.token_urlsafe(12), f"Bot · {bot['level'].capitalize()}",
                        bot=bot["level"], deck=bot["deck"]))
    else:
        match.version += 1
    hub.matches[mid] = match
    return web.json_response({"id": mid, "token": token, "seat": "A"})


async def join_match(req):
    match = hub.matches.get(req.match_info["id"])
    if match is None:
        raise web.HTTPNotFound(text="no such match")
    body = await req.json()
    if body.get("deck") not in PREMADE_DECKS:
        raise web.HTTPBadRequest(text="unknown deck")
    token = secrets.token_urlsafe(12)
    try:
        seat = match.join(Seat(token, body.get("name") or "Friend", deck=body["deck"]))
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
                    match.set_deck(seat, data["deck"])
                elif kind == "ready":
                    match.ready(seat)
                elif kind == "next":
                    match.next_game()
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
    return ws


def make_app() -> web.Application:
    app = web.Application()
    app.add_routes([
        web.get("/", index),
        web.get("/api/pool", pool),
        web.post("/api/match", create_match),
        web.post("/api/match/{id}/join", join_match),
        web.get("/ws/{id}", socket),
        web.static("/static", STATIC),
    ])
    return app


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
