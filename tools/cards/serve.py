"""The card table's server: the page, the game's static files (so cards draw as the game draws them), and a small API
that reads and writes the card data through hq.py. Martin's edits come in as by="martin"; Claude edits from the command
line (hq.py) instead, so the page polls and shows them as they land. Martin's edits are committed and pushed by
themselves once he stops editing for QUIET seconds; Claude commits its own.

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
from animal_kingdom.engine.cards import load_cards  # noqa: E402

HERE = Path(__file__).parent
STATIC = hq.ROOT / "animal_kingdom" / "web" / "static"


def pool() -> list[dict]:
    """The cards as the game's client gets them (web/match.py card_pool), read fresh so edits show at once."""
    cards = load_cards(json.loads(hq.CARDS.read_text()), validate=False)
    return [{"id": c.id, "name": c.name, "rarity": c.rarity, "tags": sorted(c.tags), "str": 0 if c.is_dynamic else c.base_strength,
             "text": c.text, "kw": sorted(c.keywords), "habitat": c.habitat, "related": list(c.related), "evolves": c.evolves}
            for c in cards.values()]


async def index(_req):
    return web.FileResponse(HERE / "index.html", headers={"Cache-Control": "no-store"})


async def state(_req):
    data = hq.load()
    data["pool"] = pool()
    return web.json_response(data, headers={"Cache-Control": "no-store"})


async def stamp(_req):
    return web.json_response({"stamp": hq.stamp()})


QUIET = 20    # seconds without an edit before Martin's edits are committed together
DATA = [hq.CARDS, hq.DECKLISTS, hq.ART_JS, hq.LEVELS]
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
