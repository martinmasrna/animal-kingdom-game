"""Record whole bot-vs-bot matches as the sequence of views one seat receives, for the client's browser tests.

Each match is played through the real `Match` (the same object the server drives), so the views are exactly what a
browser gets over the socket: one after every action, across game ends and next games. The browser test feeds them
through the client one by one (window.__ak.feed) and checks the screen against each.

    python -m animal_kingdom.web.test.record_views OUT_DIR [--matches N]
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

from ...decks import PREMADE_DECKS
from ..match import Match, Seat

MAX_VIEWS = 400


def record(deck_a: str, deck_b: str, seed: int, seat: str = "A") -> list[dict]:
    """Play a best-of-3 between two bots and return every view `seat` would have seen."""
    m = Match(f"T{seed}", Seat("a", "Bot A", bot="easy", deck=deck_a))
    m.rng.seed(seed)
    m.join(Seat("b", "Bot B", bot="easy", deck=deck_b))
    for s in "AB":
        if m.phase == "prematch":
            m.ready(s)
    views = [m.view(seat)]
    while len(views) < MAX_VIEWS:
        if m.phase == "game_over":
            m.next_game()
        elif m.phase != "playing":
            break
        else:
            m.act(m.to_act(), m.bot_move())
        views.append(m.view(seat))
    return views


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("out", type=Path)
    ap.add_argument("--matches", type=int, default=7)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    decks = sorted(PREMADE_DECKS)
    pairs = list(itertools.islice(itertools.cycle(zip(decks, decks[1:] + decks[:1])), args.matches))
    for i, (a, b) in enumerate(pairs):
        for seat in "AB":   # both seats: the client mirrors the board for seat B
            views = record(a, b, 1000 + i, seat)
            path = args.out / f"{i:02d}_{a}_vs_{b}_{seat}.json"
            path.write_text(json.dumps(views))
            print(path, len(views), "views")


if __name__ == "__main__":
    main()
