"""The card board: every card on one big table, as the game draws it, for Martin to spread out and sort into piles of his own.
Nothing on it means anything to the game; it is a sandbox. The cards are read fresh from the game's card data each time the
page asks, and each board's arrangement (where each card lies, the piles, which are squared into a stack) lives in its own
file, committed and pushed by itself once he stops moving things for QUIET seconds. The first board, Main, is
tools/board/board.json; every other board is tools/board/boards/<id>.json, named inside the file. A board whose file lists
`only` (card ids) shows just those cards; one with `notext` draws them without their effect text.

    ./board                 # http://localhost:8004
    ./board --port 8005 --no-open
    ./board --port 8014 --no-open --board /tmp/x.json   # a test server that never touches his arrangement
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

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "cards"))
import hq  # noqa: E402
from animal_kingdom.engine.cards import load_cards  # noqa: E402

STATIC = hq.ROOT / "animal_kingdom" / "web" / "static"
BOARD = HERE / "board.json"      # the Main board
BOARDS = HERE / "boards"          # every other board, one file each
ON_BOARD = {"collectible", "reserve", "planned"}   # tokens, evolution stages and the tutorial's deal stay off


def cards(only: list[str] | None = None, notext: bool = False) -> list[dict]:
    """The cards in the shape the game's cardHTML (static/card.js) draws; planned cards (no rarity or strength yet) as blanks."""
    raw = json.loads(hq.CARDS.read_text(encoding="utf-8"))["cards"]
    real = load_cards({"cards": raw}, validate=False)
    out = []
    for r in raw:
        if r.get("status") not in ON_BOARD or (only is not None and r["id"] not in only):
            continue
        c = real.get(r["id"])
        if c:
            out.append({"id": c.id, "name": c.name, "rarity": c.rarity, "str": "*" if c.is_dynamic else c.base_strength,
                        "text": "" if notext else c.text, "tags": sorted(c.tags), "species": r.get("species", ""), "habitat": c.habitat})
        else:
            out.append({"id": r["id"], "name": r.get("name") or r.get("species") or r["id"], "rarity": "common", "str": "",
                        "text": "", "tags": [], "species": r.get("species", ""), "habitat": r.get("habitat", ""), "planned": True})
    return out


def path_of(bid: str) -> Path:
    if bid in ("", "main"):
        return BOARD
    if not bid.isalnum():
        raise web.HTTPBadRequest(text="bad board id")
    return BOARDS / f"{bid}.json"


def board(bid: str = "main") -> dict:
    f = path_of(bid)
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"rev": 0, "cards": {}, "piles": []}


def boards() -> list[dict]:
    out = [{"id": "main", "name": board("main").get("name") or "Main"}]
    for f in sorted(BOARDS.glob("*.json")) if BOARDS.exists() else []:
        out.append({"id": f.stem, "name": json.loads(f.read_text(encoding="utf-8")).get("name") or f.stem})
    return out


async def index(_req):
    return web.FileResponse(HERE / "index.html", headers={"Cache-Control": "no-store"})


async def get_state(req):
    b = board(req.query.get("b", "main"))
    return web.json_response({"cards": cards(b.get("only"), bool(b.get("notext"))), "board": b, "boards": boards()}, headers={"Cache-Control": "no-store"})


async def new_board(req):
    """A new, empty board with every card, under the name the page sends; returns its id."""
    name = ((await req.json()).get("name") or "").strip()[:60] or "New board"
    BOARDS.mkdir(exist_ok=True)
    n = 1
    while (BOARDS / f"b{n}.json").exists():
        n += 1
    bid = f"b{n}"
    (BOARDS / f"{bid}.json").write_text(json.dumps({"rev": 0, "name": name, "cards": {}, "piles": []}, indent=1) + "\n", encoding="utf-8")
    _later()
    return web.json_response({"id": bid})


QUIET = 20
_timer: asyncio.TimerHandle | None = None


def _commit() -> None:
    global _timer
    _timer = None
    git = ["git", "-C", str(hq.ROOT)]
    fs = [str(BOARD.relative_to(hq.ROOT))] + ([str(BOARDS.relative_to(hq.ROOT))] if BOARDS.exists() else [])
    subprocess.run([*git, "add", "--", *fs], check=False)
    if subprocess.run([*git, "diff", "--cached", "--quiet", "--", *fs]).returncode == 0:
        return
    if subprocess.run([*git, "commit", "-q", "-m", "Card board (Martin): arrangement", "--", *fs], check=False).returncode == 0:
        subprocess.Popen([*git, "push", "-q"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


async def put_state(req):
    """The page sends the whole arrangement with the revision it started from; a stale one (another tab) is refused."""
    global _timer
    bid = req.query.get("b", "main")
    f = path_of(bid)
    new = await req.json()
    cur = board(bid)
    if new.get("rev") != cur.get("rev"):
        raise web.HTTPConflict(text="The board changed elsewhere; reloading.")
    new["rev"] = cur.get("rev", 0) + 1
    for k in ("name", "only", "notext"):   # set when the board is made, never by the page
        if k in cur:
            new[k] = cur[k]
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(new, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(f)
    _later()
    return web.json_response({"rev": new["rev"]})


def _later() -> None:
    global _timer
    if _timer:
        _timer.cancel()
    _timer = asyncio.get_running_loop().call_later(QUIET, lambda: _commit())


def make_app() -> web.Application:
    app = web.Application(client_max_size=8 * 1024 * 1024)
    app.add_routes([web.get("/", index), web.get("/api/state", get_state), web.put("/api/state", put_state),
                    web.post("/api/boards", new_board),
                    web.static("/static", STATIC)])
    return app


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8004)
    ap.add_argument("--no-open", action="store_true")
    ap.add_argument("--board", type=Path, help="the arrangement file (a test server keeps its own), never committed")
    a = ap.parse_args()
    global BOARD, BOARDS, _commit
    if a.board:
        BOARD, BOARDS, _commit = a.board, a.board.with_suffix(".boards"), lambda: None
    if not a.no_open:
        webbrowser.open(f"http://localhost:{a.port}/")
    web.run_app(make_app(), host="127.0.0.1", port=a.port, print=lambda *_: print(f"Board: http://localhost:{a.port}/"))


if __name__ == "__main__":
    main()
