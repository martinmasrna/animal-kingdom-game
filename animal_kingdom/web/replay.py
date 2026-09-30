"""A finished match played back: every view one seat saw, one per action.

The views are rebuilt through the real `Match` from each game's seed and actions (`Match.game_log`), so they are
exactly what the player's browser was sent. That only holds while the cards are as they were, so a match's replay
is rendered once when it ends and saved (`save`/`load`); matches from before that are rebuilt from their game logs,
and one that no longer ends the way it did is refused rather than shown wrong.
"""

from __future__ import annotations

import gzip
import json
from collections import Counter
from pathlib import Path
from typing import Optional

from ..decks import load_premade_deck
from ..engine.state import EngineError, new_game, other_player
from .match import Match, Seat


class ReplayError(ValueError):
    pass


CHANGED = "The cards have changed since this match, so it can't be replayed"


def _path(replay_dir: Path, key: str, seat: str) -> Path:
    return replay_dir / f"{key}-{seat}.json.gz"


def save(replay_dir: Path, key: str, seat: str, views: list[dict]) -> None:
    replay_dir.mkdir(parents=True, exist_ok=True)
    _path(replay_dir, key, seat).write_bytes(gzip.compress(json.dumps(views, separators=(",", ":")).encode()))


def load(replay_dir: Path, key: str, seat: str) -> Optional[bytes]:
    """The saved replay, still gzipped (served as is)."""
    p = _path(replay_dir, key, seat)
    return p.read_bytes() if p.is_file() else None


def series_games(log_dir: Path, match_id: str, series: int) -> list[dict]:
    """The logged games of one series (a match, or one of its rematches), in order."""
    games = []
    for path in sorted(log_dir.glob(f"web_*_{match_id}.jsonl")):
        games += [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    n = -1
    out = []
    for g in games:
        # logs from before "series" was recorded: a series starts at game 1
        n = g["series"] if "series" in g else n + (g.get("game_no") == 1)
        if n == series:
            out.append(g)
    return out


def human_seat(game: dict) -> Optional[str]:
    humans = [p for p, b in zip("AB", game["bots"]) if b == "human"]
    return humans[0] if len(humans) == 1 else None


def series_views(games: list[dict], seat: str, names: dict) -> list[dict]:
    """Every view `seat` received across the series, one per action, games back to back."""
    g0 = games[0]
    m = Match(g0.get("match_id", "replay"), Seat("", names.get("A", ""), deck=g0["deck_a"]))
    m.seats["B"] = Seat("", names.get("B", ""), deck=g0["deck_b"])
    for p, b in zip("AB", g0["bots"]):
        m.seats[p].bot = None if b == "human" else b
    out = []
    for g in games:
        m.seats["A"].deck, m.seats["B"].deck = g["deck_a"], g["deck_b"]
        try:
            lists = g.get("lists") or [load_premade_deck(g["deck_a"]), load_premade_deck(g["deck_b"])]
            m.seed, m.phase, m.history, m.actions, m.clock = g["seed"], "playing", [], [], None
            m.state = new_game(lists[0], lists[1], g["seed"], map_id=g["map_id"], first_player=g["first_player"])
            views = [m.view(seat)]
            for a in g["actions"]:
                m.act(m.to_act(), a)
                views.append(m.view(seat))
            if m.state.result is None and g["reason"] == "concede":
                m.concede(other_player(g["winner"]))
                views.append(m.view(seat))
        except (EngineError, KeyError, ValueError) as e:
            raise ReplayError(CHANGED) from e
        r = m.state.result
        if r is None or r.winner != g["winner"] or r.reason != g["reason"]:
            raise ReplayError(CHANGED)
        counts = {"A": dict(Counter(lists[0])), "B": dict(Counter(lists[1]))}
        for v in views:
            v["lists"] = counts     # the lists as played, not as the decks read today
        views[-1]["phase"] = "game_over" if g is not games[-1] else "match_over"   # the series as it was (best-of-3 once)
        out += views
    return out
