"""Run the web server and restart it whenever what it loads at start changes (./play runs this).

The server reads the card table, the decks, the maps, the rules engine and its own code once, at start; files under
static/ it serves fresh on every request. So a card edited in the card table, an engine rebuilt or a server change
needs a restart to show, and this does it within a second: running matches are saved after every move and reloaded,
and an open tab reloads itself when the build changes. Engine source newer than the built module is rebuilt first
(engine_rs/build.sh --if-stale). AK_NO_WATCH=1 makes ./play run the server once, as before.

    .venv/bin/python tools/play/watch.py [server arguments]
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WATCH = [ROOT / "animal_kingdom" / "data", ROOT / "animal_kingdom" / "web", ROOT / "animal_kingdom" / "game.py", ROOT / "engine_rs" / "src"]
SKIP = {"static", "test", "__pycache__", "node_modules"}


def stamp() -> float:
    """The newest change among the files the server loads at start."""
    newest = 0.0
    for top in WATCH:
        files = [top] if top.is_file() else top.rglob("*")
        for f in files:
            if top.is_dir() and any(part in SKIP for part in f.relative_to(top).parts):
                continue
            if f.suffix in (".py", ".json", ".rs") and f.is_file():
                newest = max(newest, f.stat().st_mtime)
    spec = importlib.util.find_spec("ak_engine")
    if spec and spec.origin:
        newest = max(newest, Path(spec.origin).stat().st_mtime)
    return newest


def main() -> None:
    args = sys.argv[1:]
    first = True
    while True:
        seen = stamp()
        extra = [] if first or "--no-open" in args else ["--no-open"]
        proc = subprocess.Popen([sys.executable, "-m", "animal_kingdom.web.server", *args, *extra], cwd=ROOT)
        first = False
        try:
            while proc.poll() is None:
                time.sleep(1)
                if stamp() != seen:
                    time.sleep(0.5)   # let a save that writes several files finish
                    print("watch: what the server loads changed; restarting it", flush=True)
                    subprocess.run([str(ROOT / "engine_rs" / "build.sh"), "--if-stale"], cwd=ROOT)
                    proc.terminate()
                    try:
                        proc.wait(10)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    break
            else:
                sys.exit(proc.returncode)
        except KeyboardInterrupt:
            proc.terminate()
            proc.wait()
            return


if __name__ == "__main__":
    main()
