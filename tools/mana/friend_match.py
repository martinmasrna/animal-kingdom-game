"""A whole friend match, played through the server's own API and websockets from both seats.

Starts a throwaway server (AK_NO_GAME_LOGS=1: it keeps nothing) on a spare port, creates a friend match for seat A,
joins it as seat B, and plays both seats from what each one's view says: keep the opening hand, play the most expensive
card the mana pays for on the tile that completes the most regions, take the first option of any choice, end the turn
when nothing is left. Prints one line per action (turn, seat, mana before, the action, both players' food) and the
result. A check that the server runs the game end to end, not a bot. Both seats play the same deck: two of each Wisp,
two Cantrips, two Spikes and the Warlord.

    .venv/bin/python tools/mana/friend_match.py [--port 8011]
"""
from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

import aiohttp

ROOT = Path(__file__).resolve().parents[2]
SKIP = "__skip__"


def choose(v: dict, regions: list[set], costs: dict) -> dict:
    """One seat's action from its own view."""
    g = v["game"]
    p = g["pending"]
    if p is not None:
        if p["kind"] == "mulligan":
            return {"kind": "choice", "choice": SKIP}
        if p["mode"] == "choice":
            opts = [o["v"] for o in p["options"]]
            return {"kind": "choice", "choice": opts[0] if opts else SKIP}
    me = v["you"]
    mine = {cr for cr, st in g["board"].items() if st[-1]["owner"] == me}
    places = g["legal"]["place"]
    if not places:
        return {"kind": "pass"}

    def score(o):
        card, tgt = o
        cr = tgt[1]
        done = sum(1 for r in regions if cr in r and r <= mine | {cr})
        return (done, costs.get(card) or 0, cr)
    card, tgt = max(((card, t) for card, ts in places.items() for t in ts), key=score)
    return {"kind": "place", "card_id": card, "target": tgt}


DECK = {"name": "Wisps", "leader": "warlord_legend",
        "list": [f"wisp_{n}" for n in range(1, 11) for _ in range(2)] + ["scout_2", "scout_2", "spiky_3", "spiky_3", "warlord_legend"]}


async def play(port: int) -> int:
    base = f"http://127.0.0.1:{port}"
    async with aiohttp.ClientSession() as http:
        pool = await (await http.get(f"{base}/api/pool")).json()
        regions = [set(r["corners"]) for r in pool["map"]["regions"]]
        costs = {c["id"]: c["mana"] for c in pool["cards"]}
        r = await http.post(f"{base}/api/match", json={"deck": DECK, "name": "Ann"})
        assert r.status == 200, await r.text()
        a = await r.json()
        r = await http.post(f"{base}/api/match/{a['id']}/join", json={"deck": DECK, "name": "Bob"})
        assert r.status == 200, await r.text()
        b = await r.json()
        socks = {s["seat"]: await http.ws_connect(f"{base}/ws/{a['id']}?token={s['token']}") for s in (a, b)}
        views: dict = {}
        sent = 0

        async def latest(seat):
            """Read the seat's socket until its newest view."""
            ws = socks[seat]
            while True:
                try:
                    msg = await ws.receive_json(timeout=0.3 if seat in views else 10)
                except asyncio.TimeoutError:
                    return
                if msg.get("t") == "view":
                    views[seat] = msg["view"]
                elif msg.get("t") == "error":
                    raise SystemExit(f"{seat}: {msg}")

        print(f"match {a['id']}")
        print(f"{'turn':>4} seat  mana  action{'':36} food A-B")
        while True:
            for s in "AB":
                await latest(s)
            va = views["A"]
            if va["phase"] != "playing":
                break
            g = va["game"]
            if g["decision"] == "mulligan":
                for s in "AB":
                    gs = views[s]["game"]
                    if gs["toAct"] == s:
                        await socks[s].send_json({"t": "act", "action": {"kind": "choice", "choice": SKIP}})
                continue
            seat = g["toAct"]
            v = views[seat]
            act = choose(v, regions, costs)
            mana = v["game"]["mana"][v["game"]["current"]]
            what = act["kind"] if act["kind"] != "place" else f"play {act['card_id']} ({costs.get(act['card_id'])}) on {act['target'][1]}"
            if act["kind"] == "choice":
                what = f"choose {act['choice']}"
            await socks[seat].send_json({"t": "act", "action": act})
            sent += 1
            await latest(seat)
            ng = views[seat]["game"]
            print(f"{g['round']:>4}  {seat}   {mana['left']}/{mana['total']}  {what:<42} {ng['food']['A']}-{ng['food']['B']}")
            if sent > 2000:
                raise SystemExit("no end after 2000 actions")
        res = va["game"]["result"]
        print(f"result: {res['winner']} wins by {res['reason']}, food {va['game']['food']['A']}-{va['game']['food']['B']}, "
              f"after {va['game']['round']} rounds")
        for ws in socks.values():
            await ws.close()
        return 0 if res["reason"] in ("food", "starved") else 1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8011)
    a = ap.parse_args()
    env = {**os.environ, "AK_NO_GAME_LOGS": "1", "PYTHONWARNINGS": "ignore"}
    srv = subprocess.Popen([sys.executable, "-m", "animal_kingdom.web.server", "--port", str(a.port)], cwd=ROOT, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                import urllib.request
                urllib.request.urlopen(f"http://127.0.0.1:{a.port}/api/pool", timeout=1)
                break
            except OSError:
                time.sleep(0.2)
        sys.exit(asyncio.run(play(a.port)))
    finally:
        srv.terminate()


if __name__ == "__main__":
    main()
