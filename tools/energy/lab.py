"""The energy prototype's lab: the Costs board and a local game that follows it.

    .venv/bin/python tools/energy/lab.py          # board: http://localhost:8006/#b=costs   game: http://localhost:8010/

Runs the card board (tools/board/serve.py) and the game server under the energy rules. Whenever the board saves
(tools/energy/edits.json changes), the prototype's data is rebuilt (build.py) and the game server restarted, so a cost
moved on the board is in the next game a few seconds later."""
import os, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PY = str(ROOT / ".venv" / "bin" / "python")
EDITS = HERE / "edits.json"
BOARD_PORT, GAME_PORT = "8006", "8010"


def game():
    env = dict(os.environ, AK_ENERGY="1", AK_RUST_BOTS="1")
    return subprocess.Popen([PY, "-m", "animal_kingdom.web.server", "--port", GAME_PORT, "--no-open"], cwd=ROOT, env=env,
                            stdout=open(HERE / "game.log", "a"), stderr=subprocess.STDOUT)


def build() -> bool:
    r = subprocess.run([PY, "-W", "ignore", str(HERE / "build.py")], cwd=ROOT, capture_output=True, text=True)
    (HERE / "build.log").write_text(r.stdout + r.stderr)
    return r.returncode == 0


def main():
    board = subprocess.Popen([PY, str(ROOT / "tools" / "board" / "serve.py"), "--port", BOARD_PORT, "--no-open"], cwd=ROOT,
                             stdout=open(HERE / "board.log", "a"), stderr=subprocess.STDOUT)
    build()
    g = game()
    seen = EDITS.stat().st_mtime if EDITS.exists() else 0
    print(f"Costs board: http://localhost:{BOARD_PORT}/#b=costs   game: http://localhost:{GAME_PORT}/", flush=True)
    try:
        while True:
            time.sleep(0.7)
            m = EDITS.stat().st_mtime if EDITS.exists() else 0
            if m != seen:
                time.sleep(1.0)                       # let a burst of moves settle
                seen = EDITS.stat().st_mtime
                if build():
                    g.terminate()
                    try:
                        g.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        g.kill()
                    g = game()
                    print(time.strftime("%H:%M:%S"), "rebuilt, game restarted", flush=True)
                else:
                    print(time.strftime("%H:%M:%S"), "build failed: see tools/energy/build.log (the game keeps the last good data)", flush=True)
            if g.poll() is not None:                  # the game died: bring it back
                g = game()
    finally:
        for p in (g, board):
            p.terminate()


if __name__ == "__main__":
    main()
