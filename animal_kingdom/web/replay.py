"""A finished match (one game) played back: every view one seat saw, one per action.

The views are rebuilt through the real `Match` from the game's seed and actions (`Match.game_log`), so they are
exactly what the player's browser was sent. That only holds while the cards are as they were, so a match's replay
is rendered once when it ends and saved (`save`/`load`). Every match in a history has its replay: `backfill` gives
older ones theirs from the game logs, and drops from the history any that can no longer be replayed.
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
    """The logged games of one series (a match, or one of its rematches; best-of-3 once), in order."""
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


def backfill(profiles, log_dir: Path, replay_dir: Path) -> None:
    """Save the replay of every match in a history that has none, rebuilt from its game log. A match that can't be
    (not recorded, a best-of-3 from before a match was one game, a gauntlet, or its cards changed since) leaves the history."""
    for r in profiles.all_matches():
        if r["seat"] and _path(replay_dir, r["match"], r["seat"]).is_file():
            continue
        mid, _, series = r["match"].rpartition("-")
        games = series_games(log_dir, mid, int(series)) if series.isdigit() and r["kind"] != "gauntlet" else []
        seat = r["seat"] or (human_seat(games[0]) if games else None)
        try:
            if len(games) != 1 or not seat:
                raise ReplayError("no single game to replay")
            save(replay_dir, r["match"], seat, game_views(games[0], seat, {}))
            profiles.set_seat(r["profile"], r["match"], seat)
        except ReplayError:
            profiles.forget(r["profile"], r["match"])


def game_views(g: dict, seat: str, names: dict) -> list[dict]:
    """Every view `seat` received in the game, one per action."""
    m = Match(g.get("match_id", "replay"), Seat("", names.get("A", ""), deck=g["deck_a"]))
    m.seats["B"] = Seat("", names.get("B", ""), deck=g["deck_b"])
    for p, b in zip("AB", g["bots"]):
        m.seats[p].bot = None if b == "human" else b
    try:
        lists = g.get("lists") or [load_premade_deck(g["deck_a"]), load_premade_deck(g["deck_b"])]
        m.seed, m.phase = g["seed"], "playing"
        m.state = new_game(lists[0], lists[1], g["seed"], map_id=g["map_id"], first_player=g["first_player"])
        views = [m.view(seat)]
        for a in g["actions"]:
            m.act(m.to_act(), a)
            views.append(m.view(seat))
        if m.state.result is None and g["reason"] == "concede":
            m.concede(other_player(g["winner"]))
            views.append(m.view(seat))
    except (EngineError, KeyError, ValueError) as e:
        raise ReplayError("its cards have changed since") from e
    r = m.state.result
    if r is None or r.winner != g["winner"] or r.reason != g["reason"]:
        raise ReplayError("its cards have changed since")
    counts = {"A": dict(Counter(lists[0])), "B": dict(Counter(lists[1]))}
    for v in views:
        v["lists"] = counts     # the lists as played, not as the decks read today
    return views
