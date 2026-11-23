"""Martin's review of a patch before it deploys: http://localhost:8004/

    .venv/bin/python tools/patch/review.py 0.0.2

The page is the game's own Patch notes screen (static/patch.js) on the draft: the cards and hero powers changed since
the last patch, the rule bullets from web/patches/VERSION.md. He edits a bullet in place (Enter adds one, an emptied one
goes) and clicks any card or pair to leave a note on it. Every change saves at once: the bullets straight into
VERSION.md, the notes and the bullets as they first were into web/patches/VERSION.review.json, which the agent reads,
acts on, and deletes once every note is resolved.
"""

from __future__ import annotations

import json
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402

STATIC = build.WEB / "static"
VERSION = sys.argv[1] if len(sys.argv) > 1 else sys.exit("usage: review.py VERSION")
MD = build.WEB / "patches" / f"{VERSION}.md"
REVIEW = build.WEB / "patches" / f"{VERSION}.review.json"


def draft() -> dict:
    _, was = build.last_snapshot(VERSION)
    rules = build.rules_of(VERSION) if MD.exists() else []
    review = json.loads(REVIEW.read_text()) if REVIEW.exists() else {"notes": {}}
    import datetime
    return {"patch": {"version": VERSION, "name": f"Patch {VERSION}", "date": datetime.date.today().strftime("%-d %B %Y"),
                      "rules": rules, **build.diff(was, build.snapshot())}, "review": review,
            "map": __import__("animal_kingdom.web.match", fromlist=["map_info"]).map_info()}   # the board AK_MAP picks: its card is the one drawn


def save(body: dict) -> None:
    review = json.loads(REVIEW.read_text()) if REVIEW.exists() else {}
    review.setdefault("rules_before", build.rules_of(VERSION) if MD.exists() else [])
    rules = [r.strip() for r in body.get("rules", []) if r.strip()]
    MD.write_text(f"# Patch {VERSION}\n\n## Rules\n\n" + "".join(f"- {r}\n" for r in rules))
    review["notes"] = {k: v for k, v in body.get("notes", {}).items() if v.strip()}
    REVIEW.write_text(json.dumps(review, indent=1, ensure_ascii=False) + "\n")


PAGE = (Path(__file__).resolve().parent / "review.html").read_text


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Cache-Control", "no-cache")
        self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            return self.send(200, PAGE().encode(), "text/html; charset=utf-8")
        if path == "/draft.json":
            return self.send(200, json.dumps(draft()).encode(), "application/json")
        if path.startswith("/static/"):
            f = (STATIC / path[len("/static/"):]).resolve()
            if f.is_file() and STATIC.resolve() in f.parents:
                return self.send(200, f.read_bytes(), mimetypes.guess_type(f.name)[0] or "application/octet-stream")
        self.send(404, b"", "text/plain")

    def do_POST(self):
        if self.path == "/save":
            save(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            return self.send(200, b"{}", "application/json")
        self.send(404, b"", "text/plain")


if __name__ == "__main__":
    mimetypes.add_type("text/javascript", ".js"); mimetypes.add_type("image/webp", ".webp"); mimetypes.add_type("image/svg+xml", ".svg")
    import os
    port = int(os.environ.get("AK_REVIEW_PORT", 8004))   # another port while an old review still holds 8004
    print(f"reviewing Patch {VERSION}: http://localhost:{port}/")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
