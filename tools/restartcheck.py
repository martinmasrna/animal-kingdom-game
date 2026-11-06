"""Restarts keep matches, checked on a real process: the Dockerfile's command over a temp copy of a checkout's package,
a bot match and a friend match played to round 3, the process killed, a new one started on the same results/, both
matches reconnected with their old seat tokens (the bot match's position compared) and played to the end.

  .venv/bin/python tools/restartcheck.py . SIGKILL      # or SIGTERM (a deploy); the first argument is the checkout

Prints each stage and the server's logged errors. Needs aiohttp (the web extra); uses tools/loadtest.py's players."""
import asyncio, json, os, random, shutil, signal, subprocess, sys, tempfile, time
from pathlib import Path
import aiohttp
sys.path.insert(0, str(Path(__file__).resolve().parent)); import loadtest as L  # noqa: E402
CODE, SIG = Path(sys.argv[1]), getattr(signal, sys.argv[2])
tree = Path(tempfile.mkdtemp(prefix="ak-restart-"))
shutil.copytree(CODE / "animal_kingdom", tree / "animal_kingdom", ignore=shutil.ignore_patterns("tests", "node_modules", "__pycache__", "test"))
port = L.free_port(); url = f"http://127.0.0.1:{port}"
def start():
    env = {**os.environ, "AK_RUST_BOTS": "1", "PYTHONUNBUFFERED": "1"}; env.pop("AK_NO_GAME_LOGS", None)
    return subprocess.Popen([sys.executable, "-m", "animal_kingdom.web.server", "--host", "127.0.0.1", "--port", str(port), "--no-open"],
                            cwd=tree, env=env, stdout=open(tree / "server.log", "a"), stderr=subprocess.STDOUT)
Args = type("A", (), {"seed": 1, "think": (0, 0.05), "grace": 0, "path": "bot"})
async def seat_play(http, mid, tok, p, until):
    ws = await http.ws_connect(f"{url}/ws/{mid}?token={tok}"); last = None
    try:
        while True:
            msg = await asyncio.wait_for(ws.receive(), 60)
            if msg.type != aiohttp.WSMsgType.TEXT: return last
            d = json.loads(msg.data)
            if d["t"] != "view": continue
            v = last = d["view"]; g = v["game"]
            if g and g["events"]: await ws.send_json({"t": "played", "seq": g["events"][-1]["seq"]})
            if until(v): return v
            if g and g["toAct"] == v["you"] and g["decision"] in ("yours", "your_choice", "mulligan"):
                a = p.pick(g)
                if a: await ws.send_json({"t": "act", "action": a})
    finally:
        await ws.close()
mid_game = lambda v: v["phase"] != "playing" or (v["game"]["round"] >= 3 and v["game"]["toAct"] == v["you"] and v["game"]["decision"] == "yours")
over = lambda v: v["phase"] != "playing"
async def main():
    proc = start(); await L.wait_up(url, proc)
    async with aiohttp.ClientSession() as http:
        st = L.Stats(); pool = {"bot_decks": ["cats", "canines"], "lists": {}}
        a, b = L.Player(0, url, http, st, Args, pool), L.Player(1, url, http, st, Args, pool)
        await a.sign_in(); await b.sign_in()
        bm = await a.call("POST", "/api/match", json={"deck": "cats", "bot": {"level": "normal", "deck": "canines"}})
        before_bot = await seat_play(http, bm["id"], bm["token"], a, mid_game)
        fm = await a.call("POST", "/api/match", json={"deck": "cats"}); fj = await b.call("POST", f"/api/match/{fm['id']}/join", json={"deck": "canines"})
        pa = asyncio.ensure_future(seat_play(http, fm["id"], fm["token"], a, mid_game))
        pb = asyncio.ensure_future(seat_play(http, fj["id"], fj["token"], b, lambda v: pa.done()))
        before_pvp = await pa; await asyncio.sleep(0.5); pb.cancel()
    print("before:", before_bot["phase"], "round", before_bot["game"]["round"], "| pvp", before_pvp["phase"], "round", before_pvp["game"]["round"])
    t = time.time(); proc.send_signal(SIG); proc.wait(30); print(f"{sys.argv[2]}: exited {proc.returncode} in {time.time()-t:.1f}s")
    proc = start(); t = time.time(); await L.wait_up(url, proc); print(f"back up in {time.time()-t:.1f}s")
    async with aiohttp.ClientSession() as http:
        st = L.Stats(); a, b = L.Player(0, url, http, st, Args, pool), L.Player(1, url, http, st, Args, pool)
        ws = await http.ws_connect(f"{url}/ws/{bm['id']}?token={bm['token']}"); await ws.receive()
        v = json.loads((await ws.receive()).data)["view"]; await ws.close()
        same = (v["game"]["round"], v["game"]["hand"], v["game"]["board"]) == (before_bot["game"]["round"], before_bot["game"]["hand"], before_bot["game"]["board"])
        print("bot match after restart: phase", v["phase"], "same position:", same)
        end_bot = await seat_play(http, bm["id"], bm["token"], a, over)
        ra = asyncio.ensure_future(seat_play(http, fm["id"], fm["token"], a, over)); rb = asyncio.ensure_future(seat_play(http, fj["id"], fj["token"], b, over))
        e1, e2 = await asyncio.gather(ra, rb)
        print("played out: bot match", end_bot["phase"], "| friend match", e1["phase"], e2["phase"])
    proc.terminate(); proc.wait(30)
    errs = [l for l in open(tree / "server.log") if "Traceback" in l or "could not" in l or "ERROR" in l]
    print("server errors:", len(errs), errs[:3])
    shutil.rmtree(tree, ignore_errors=True)
asyncio.run(main())
