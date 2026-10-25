"""The Meta tab's backfill: the card facts the runner logged (results/league/facts/<day>.jsonl) posted to a server's
/api/league/facts, for games it rated before it counted facts itself.

    .venv/bin/python -m animal_kingdom.league.backfill --server https://animal-kingdom-staging.fly.dev [--until <epoch seconds>]

`--until` stops at the time the runner began sending facts with its games, so no game is counted twice.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..web.league import key as league_key
from .runner import api


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--server", required=True)
    ap.add_argument("--facts", default="results/league/facts")
    ap.add_argument("--until", type=float, default=None)
    ap.add_argument("--chunk", type=int, default=500)   # under the server's 1 MB body limit
    args = ap.parse_args(argv)
    key = league_key()
    games = [json.loads(l) for f in sorted(Path(args.facts).glob("*.jsonl")) for l in f.read_text().splitlines() if l.strip()]
    games = [g for g in games if args.until is None or g["t"] < args.until]
    counted = 0
    for i in range(0, len(games), args.chunk):
        counted += api(args.server, "/api/league/facts", key, {"games": games[i:i + args.chunk]})["counted"]
    print(f"{counted} of {len(games)} games counted on {args.server}")


if __name__ == "__main__":
    main()
