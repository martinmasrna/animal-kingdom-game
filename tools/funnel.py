"""The newcomer funnel, read from the server's player data.

    deploy/deploy.sh players            # pulls profiles, histories and events into results/players.json
    .venv/bin/python tools/funnel.py    # [--since 2026-10-20] [--all] [path]

One row per profile: when they came, how far they got (Learn to play, lesson 1, lesson 2, the first real match, the
first ranked game), how much they played and when they were last seen. Then the funnel itself: how many reached each
stage. Test agents (headless browsers) and profiles that never did anything are left out unless --all.

Stages come from web/events.py (the server's game_start/game_end with a lesson number, left_mid_game; the client's
learn_to_play, skip_tutorial, tutorial_step, screen, hidden/shown) and the match history.
"""

from __future__ import annotations

import argparse
import collections
import datetime
import json
import statistics
import sys

SESSION_GAP = 30 * 60   # seconds of silence that end a session


def day(t: float) -> str:
    return datetime.datetime.fromtimestamp(t).strftime("%m-%d")


def read(path: str, since: str | None, everyone: bool):
    d = json.load(open(path))
    events = collections.defaultdict(list)
    for e in d["events"]:
        e["d"] = json.loads(e["data"]) if isinstance(e["data"], str) else e["data"]
        events[e["profile"]].append(e)
    history = collections.defaultdict(list)
    for h in d["history"]:
        history[h["profile"]].append(h)
    rows = []
    for p in sorted(d["profiles"], key=lambda p: p["created"]):
        ev, hs = events[p["id"]], history[p["id"]]
        if since and datetime.date.fromtimestamp(p["created"]).isoformat() < since:
            continue
        agent = next((e["d"].get("agent", "") for e in ev if e["kind"] == "profile_created"), "")
        if not everyone and ("HeadlessChrome" in agent or not (ev or hs)):
            continue
        rows.append(profile_row(p, ev, hs))
    return rows


def profile_row(p, ev, hs):
    kinds = collections.Counter(e["kind"] for e in ev)
    lesson_started = {e["d"].get("lesson") for e in ev if e["kind"] == "game_start" and e["d"].get("lesson")}
    lesson_done = {e["d"].get("lesson") for e in ev if e["kind"] == "game_end" and e["d"].get("lesson") and e["d"].get("won")}
    steps = collections.defaultdict(set)   # the distinct coach steps reached in each lesson (step ids are names, not numbers)
    for e in ev:
        if e["kind"] == "c_tutorial_step":
            steps[e["d"].get("lesson")].add(e["d"].get("step"))
    real = [e for e in ev if e["kind"] == "game_start" and not e["d"].get("lesson")]
    real_done = [e for e in ev if e["kind"] == "game_end" and not e["d"].get("lesson")]
    ranked = [e for e in real if e["d"].get("ranked")]
    ts = sorted([e["t"] for e in ev] + [h["ended"] for h in hs])
    sessions, start, last = [], None, None
    for t in ts:
        if start is None or t - last > SESSION_GAP:
            if start is not None:
                sessions.append(last - start)
            start = t
        last = t
    if start is not None:
        sessions.append(last - start)
    return {
        "name": f"{p['name']}#{p['tag']}", "created": day(p["created"]),
        "learn": "skip" if kinds["c_skip_tutorial"] else ("yes" if kinds["c_learn_to_play"] else ""),
        "l1": "done" if 1 in lesson_done else ("started" if 1 in lesson_started else ""),
        "l2": "done" if 2 in lesson_done else ("started" if 2 in lesson_started else ""),
        "steps": " ".join(f"L{k}:{len(v)}" for k, v in sorted(steps.items())),
        "match": len(real), "finished": len(real_done), "won": sum(1 for e in real_done if e["d"].get("won")),
        "ranked": len(ranked), "left": kinds["left_mid_game"], "js_err": kinds["c_js_error"],
        "games": len(hs), "days": len({day(t) for t in ts}) if ts else 0,
        "last": day(ts[-1]) if ts else "", "sessions": len(sessions),
        "median_min": round(statistics.median(sessions) / 60, 1) if sessions else 0,
        "first_min": round(sessions[0] / 60, 1) if sessions else 0,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("path", nargs="?", default="results/players.json")
    ap.add_argument("--since", help="profiles created on or after this ISO date")
    ap.add_argument("--all", action="store_true", help="include test agents and empty profiles")
    a = ap.parse_args(argv)
    rows = read(a.path, a.since, a.all)
    cols = ["name", "created", "learn", "l1", "l2", "steps", "match", "finished", "won", "ranked", "left", "js_err", "games", "days", "last", "sessions", "first_min", "median_min"]
    widths = {c: max(len(c), *(len(str(r[c])) for r in rows)) if rows else len(c) for c in cols}
    print("  ".join(c.ljust(widths[c]) for c in cols))
    for r in rows:
        print("  ".join(str(r[c]).ljust(widths[c]) for c in cols))
    n = len(rows)
    if not n:
        return
    stage = [
        ("came", n),
        ("clicked Learn to play", sum(1 for r in rows if r["learn"] == "yes")),
        ("finished lesson 1", sum(1 for r in rows if r["l1"] == "done")),
        ("finished lesson 2", sum(1 for r in rows if r["l2"] == "done")),
        ("started a real match", sum(1 for r in rows if r["match"])),
        ("finished one", sum(1 for r in rows if r["finished"])),
        ("won one", sum(1 for r in rows if r["won"])),
        ("played ranked", sum(1 for r in rows if r["ranked"])),
        ("came back another day", sum(1 for r in rows if r["days"] >= 2)),
        ("played a week later", sum(1 for r in rows if r["days"] >= 2 and _span(r) >= 7)),
    ]
    print("\nFunnel")
    for name, k in stage:
        print(f"  {name:24} {k:4}  {100 * k // n:3}%")


def _span(r):
    try:
        a = datetime.datetime.strptime(r["created"], "%m-%d"); b = datetime.datetime.strptime(r["last"], "%m-%d")
        return (b - a).days
    except ValueError:
        return 0


if __name__ == "__main__":
    sys.exit(main())
