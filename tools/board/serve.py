"""The card board: every card on one big table, as the game draws it, for Martin to spread out and sort into piles of his own.
Nothing on it means anything to the game; it is a sandbox. The cards are read fresh from the game's card data each time the
page asks, and each board's arrangement (where each card lies, the piles, which are squared into a stack) lives in its own
file, committed and pushed by itself once he stops moving things for QUIET seconds. The first board, Main, is
tools/board/board.json; every other board is tools/board/boards/<id>.json, named inside the file. A board whose file lists
`only` (card ids) shows just those cards; one with `notext` draws them without their effect text.

The board is also where Martin designs cards: a card's strength, stars, name, text and family changed on the card, and new
cards (blank or copied from one). None of it touches the game: it lives in tools/board/changes.json, shared by every board,
committed like the arrangement, and applied to the game only when he asks an agent to (tools/board/CHANGES.md says how). The
file always says what still differs from the game: a change the game has caught up with drops out by itself.

    ./board                 # http://localhost:8004
    ./board --port 8005 --no-open
    ./board --port 8014 --no-open --board /tmp/x.json   # a test server that never touches his arrangement or changes
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
CHANGES = HERE / "changes.json"  # Martin's card design: what he changed on the board, shared by every board
ON_BOARD = {"collectible", "reserve", "planned"}   # tokens, evolution stages and the tutorial's deal stay off
STARS = {"common": 0, "rare": 1, "legendary": 2}   # a card's starting stars when its record has none
FIELDS = ("name", "strength", "stars", "text", "tags")   # what a card's change may hold, in the file's order


def _raw() -> list[dict]:
    return json.loads(hq.CARDS.read_text(encoding="utf-8"))["cards"]


def cards(only: list[str] | None = None) -> list[dict]:
    """The cards in the shape the game's cardHTML (static/card.js) draws, with their stars; planned cards (no rarity or
    strength yet) as blanks. These are the game's values: the page lays Martin's changes over them."""
    raw = _raw()
    real = load_cards({"cards": raw}, validate=False)
    out = []
    for r in raw:
        if r.get("status") not in ON_BOARD or (only is not None and r["id"] not in only):
            continue
        c = real.get(r["id"])
        stars = r.get("stars", STARS.get(r.get("rarity") or "", 0))
        if c:
            out.append({"id": c.id, "name": c.name, "rarity": c.rarity, "str": "*" if c.is_dynamic else c.base_strength,
                        "text": r.get("text", ""), "tags": list(r.get("tags", [])), "species": r.get("species", ""), "habitat": c.habitat,
                        "stars": stars})
        else:
            out.append({"id": r["id"], "name": r.get("name") or r.get("species") or r["id"], "rarity": "common", "str": "",
                        "text": r.get("text", ""), "tags": list(r.get("tags", [])), "species": r.get("species", ""),
                        "habitat": r.get("habitat", ""), "planned": True, "stars": stars})
    return out


def _game_values() -> dict[str, dict]:
    """Each card's values as the game has them, in the changes file's terms (strength None: not set yet; '*': the engine's)."""
    return {c["id"]: {"name": c["name"], "strength": None if c["str"] == "" else c["str"], "stars": c["stars"],
                      "text": c["text"], "tags": c["tags"]} for c in cards()}


def _clean_new(n: dict) -> dict:
    out = {"copy_of": n.get("copy_of") or None, "name": str(n.get("name") or "").strip()[:60] or "New card",
           "rarity": n.get("rarity") if n.get("rarity") in STARS else "common"}
    out["strength"] = max(0, min(99, int(n.get("strength") or 0)))
    out["stars"] = max(-1, min(3, int(n.get("stars") if n.get("stars") is not None else STARS[out["rarity"]])))
    out["text"] = " ".join(str(n.get("text") or "").split())
    out["tags"] = [str(t).strip() for t in n.get("tags") or [] if str(t).strip()]
    out["habitat"], out["species"] = str(n.get("habitat") or ""), str(n.get("species") or "")
    return out


def _clean_edit(field: str, v):
    if field == "strength":
        return max(0, min(99, int(v)))
    if field == "stars":
        return max(-1, min(3, int(v)))
    if field == "tags":
        return [str(t).strip() for t in v if str(t).strip()]
    return " ".join(str(v).split())   # name, text: one line, single spaces


def write_design(edits: dict, new: dict, rev: int) -> dict:
    """The changes file from the page's edits ({id: {field: value}}) and new cards: a change equal to the game's value is
    no change and is left out; each kept one says what the game has now (was) and what Martin wants (now)."""
    game = _game_values()
    changed = {}
    for cid, fs in sorted(edits.items()):
        if cid not in game:
            continue
        row = {}
        for f in FIELDS:
            if f not in fs or (f == "strength" and game[cid]["strength"] == "*"):
                continue
            v = _clean_edit(f, fs[f])
            if v != game[cid][f] and not (f in ("name", "text") and v == " ".join(str(game[cid][f] or "").split())):
                row[f] = {"was": game[cid][f], "now": v}
        if row:
            changed[cid] = row
    d = {"how_to_read": "tools/board/CHANGES.md", "rev": rev, "changed": changed,
         "new": {nid: _clean_new(n) for nid, n in new.items() if nid.startswith("new") and nid[3:].isdigit()}}
    if CHANGES.exists() and json.loads(CHANGES.read_text(encoding="utf-8")) == d:
        return d
    tmp = CHANGES.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(CHANGES)
    try:
        _later()
    except RuntimeError:   # no event loop: called outside the server
        pass
    return d


def design() -> dict:
    """The changes file brought up to date with the game (rewritten only when that changes it), as the page holds it."""
    d = json.loads(CHANGES.read_text(encoding="utf-8")) if CHANGES.exists() else {"rev": 0, "changed": {}, "new": {}}
    edits = {cid: {f: x["now"] for f, x in row.items()} for cid, row in d.get("changed", {}).items()}
    d = write_design(edits, d.get("new", {}), d.get("rev", 0)) if CHANGES.exists() else d
    return {"rev": d["rev"], "edits": {cid: {f: x["now"] for f, x in row.items()} for cid, row in d["changed"].items()},
            "new": d["new"]}


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
    return web.json_response({"cards": cards(b.get("only")), "design": design(), "board": b, "boards": boards()},
                             headers={"Cache-Control": "no-store"})


async def put_design(req):
    """Martin's changes as the page holds them, with the revision it started from; a stale one (another tab) is refused."""
    new = await req.json()
    cur = design()
    if new.get("rev") != cur["rev"]:
        raise web.HTTPConflict(text="The changes moved on in another tab; reloading.")
    d = write_design(new.get("edits") or {}, new.get("new") or {}, cur["rev"] + 1)
    return web.json_response({"rev": d["rev"]})


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
    fs = [str(f.relative_to(hq.ROOT)) for f in (BOARD, CHANGES) if f.exists()] + ([str(BOARDS.relative_to(hq.ROOT))] if BOARDS.exists() else [])
    subprocess.run([*git, "add", "--", *fs], check=False)
    if subprocess.run([*git, "diff", "--cached", "--quiet", "--", *fs]).returncode == 0:
        return
    if subprocess.run([*git, "commit", "-q", "-m", "Card board (Martin): arrangement and card changes", "--", *fs], check=False).returncode == 0:
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
                    web.put("/api/design", put_design),
                    web.post("/api/boards", new_board),
                    web.static("/static", STATIC)])
    return app


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8004)
    ap.add_argument("--no-open", action="store_true")
    ap.add_argument("--board", type=Path, help="the arrangement file (a test server keeps its own), never committed")
    a = ap.parse_args()
    global BOARD, BOARDS, CHANGES, _commit
    if a.board:
        BOARD, BOARDS, CHANGES, _commit = a.board, a.board.with_suffix(".boards"), a.board.with_suffix(".changes.json"), lambda: None
    if not a.no_open:
        webbrowser.open(f"http://localhost:{a.port}/")
    web.run_app(make_app(), host="127.0.0.1", port=a.port, print=lambda *_: print(f"Board: http://localhost:{a.port}/"))


if __name__ == "__main__":
    main()
