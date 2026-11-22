"""The card table's server: the page, the game's static files (so cards draw as the game draws them), and a small API
that reads and writes the card data through hq.py. Martin's edits come in as by="martin"; Claude edits from the command
line (hq.py) instead, so the page polls and shows them as they land. Martin's edits are committed and pushed by
themselves once he stops editing for QUIET seconds; Claude commits its own. /board is the card board: every collectible
card as the game draws it on a table to pan, zoom, pile, snap and bin, following the card data as it changes; its layout
is saved to board.json beside this file.

    ./cards                 # http://localhost:8002
    ./cards --port 8003 --no-open
"""
from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import webbrowser
from pathlib import Path

from aiohttp import web

sys.path.insert(0, str(Path(__file__).parent))
import hq  # noqa: E402
from animal_kingdom.game import PLANNED  # noqa: E402

HERE = Path(__file__).parent
STATIC = hq.ROOT / "animal_kingdom" / "web" / "static"


def pool() -> list[dict]:
    """The cards as the game's client gets them (web/match.py card_pool), read fresh so edits show at once."""
    cards = [c for c in json.loads(hq.CARDS.read_text())["cards"] if c.get("status") != PLANNED]
    return [{"id": c["id"], "name": c["name"], "rarity": c["rarity"], "str": 0 if c["base_strength"] == "dynamic" else c["base_strength"],
             "text": c.get("text", ""), "kw": sorted(c.get("keywords", [])), "mana": c["cost"]} for c in cards]


async def index(_req):
    return web.FileResponse(HERE / "index.html", headers={"Cache-Control": "no-store"})


async def state(_req):
    data = hq.load()
    data["pool"] = pool()
    return web.json_response(data, headers={"Cache-Control": "no-store"})


BOARD = HERE / "board.json"   # Martin's layout on the card board (/board): his own, not the game's, so not in git


async def board_page(_req):
    return web.FileResponse(HERE / "board.html", headers={"Cache-Control": "no-store"})


async def board_get(_req):
    """The collectible cards, fresh, and the saved layout."""
    ids = {c["id"] for c in json.loads(hq.CARDS.read_text())["cards"] if c.get("status") == "collectible"}
    layout = json.loads(BOARD.read_text()) if BOARD.exists() else None
    return web.json_response({"cards": [c for c in pool() if c["id"] in ids], "layout": layout, "stamp": hq.stamp()},
                             headers={"Cache-Control": "no-store"})


async def board_put(req):
    body = await req.json()
    tmp = BOARD.with_suffix(".tmp")
    tmp.write_text(json.dumps(body, separators=(",", ":")))
    tmp.replace(BOARD)
    return web.json_response({"ok": True})


async def stamp(_req):
    return web.json_response({"stamp": hq.stamp()})


QUIET = 20    # seconds without an edit before Martin's edits are committed together
DATA = [hq.CARDS, hq.ART_JS, hq.LEVELS]
_pending: list[str] = []
_timer: asyncio.TimerHandle | None = None


def _commit() -> None:
    """Commit the card files with what Martin changed as the message, then push in the background: his edits land in git
    like anyone's, instead of waiting in the working tree for a session to notice them."""
    global _timer
    _timer = None
    lines, _pending[:] = list(_pending), []
    git = ["git", "-C", str(hq.ROOT)]
    files = [str(p.relative_to(hq.ROOT)) for p in DATA]
    subprocess.run([*git, "add", "--", *files], check=False)
    if subprocess.run([*git, "diff", "--cached", "--quiet", "--", *files]).returncode == 0:
        return
    head = lines[0] if len(lines) == 1 else f"{len(lines)} edits" if lines else "edits made before the table last started"
    msg = f"Card table (Martin): {head}\n\n" + "\n".join(f"- {l}" for l in lines if l)
    if subprocess.run([*git, "commit", "-q", "-m", msg, "--", *files], check=False).returncode == 0:
        subprocess.Popen([*git, "push", "-q"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _act(fn, what):
    async def handler(req):
        global _timer
        body = await req.json()
        try:
            report = fn(body)
        except hq.Refused as e:
            raise web.HTTPConflict(text=str(e))
        except (KeyError, ValueError, RuntimeError) as e:
            raise web.HTTPBadRequest(text=str(e))
        _pending.append(report or what(body))
        if _timer:
            _timer.cancel()
        _timer = asyncio.get_running_loop().call_later(QUIET, _commit)
        return web.json_response({"ok": True, "report": report or "", "stamp": hq.stamp()})
    return handler


def make_app() -> web.Application:
    app = web.Application()
    app.add_routes([
        web.get("/", index),
        web.get("/api/state", state),
        web.get("/api/stamp", stamp),
        web.get("/board", board_page),
        web.get("/api/board", board_get),
        web.post("/api/board", board_put),
        web.post("/api/value", _act(lambda b: hq.set_value(b["id"], b["col"], b["value"], "martin"),
                                    lambda b: f"{b['id']} {b['col']}: {b['value']}")),
        web.post("/api/level", _act(lambda b: hq.set_level(b["id"], b["col"], b["lv"], "martin", b.get("note")),
                                    lambda b: f"{b['id']} {b['col']} {b['lv']}" + (f" ({b['note']})" if b.get("note") else ""))),
        web.post("/api/note", _act(lambda b: hq.set_note(b["id"], b["col"], b["note"], "martin"),
                                   lambda b: f"{b['id']} {b['col']} note: {b['note']}")),
        web.post("/api/crop", _act(lambda b: hq.set_crop(b["id"], b.get("crop"), b.get("strip"), b.get("full"), "martin"),
                                   lambda b: f"{b['id']} crop")),
        web.post("/api/accept", _act(lambda b: hq.accept(b["id"], b["col"]), lambda b: f"{b['id']} {b['col']} accepted")),
        web.post("/api/revert", _act(lambda b: hq.revert(b["id"], b["col"]), lambda b: f"{b['id']} {b['col']} reverted")),
        web.static("/static", STATIC),
    ])
    return app


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8002)
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()
    if not a.no_open:
        webbrowser.open(f"http://localhost:{a.port}/")
    web.run_app(make_app(), host="127.0.0.1", port=a.port, print=lambda *_: print(f"Cards: http://localhost:{a.port}/"))


if __name__ == "__main__":
    main()
