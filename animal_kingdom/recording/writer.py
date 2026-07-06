"""Append-only, crash-tolerant JSONL writer for one recorded game attempt."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


class JsonlGameWriter:
    """Write one durable JSON record per line, flushing each completed record."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = open(self.path, "a", encoding="utf-8")

    def append(self, record: dict) -> None:
        self._handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
        self._handle.flush()
        os.fsync(self._handle.fileno())

    def close(self) -> None:
        if not self._handle.closed:
            self._handle.close()

    def __enter__(self) -> "JsonlGameWriter":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()


def recover_records(path: Path) -> list[dict]:
    """Read valid records and truncate only an incomplete final JSON line."""
    path = Path(path)
    records: list[dict] = []
    with open(path, "rb+") as handle:
        line_number = 0
        while True:
            start = handle.tell()
            raw = handle.readline()
            if not raw:
                break
            line_number += 1
            try:
                records.append(json.loads(raw))
            except (UnicodeDecodeError, json.JSONDecodeError):
                if raw.endswith(b"\n") or handle.read(1):
                    raise ValueError(f"{path}:{line_number}: corrupt JSONL record") from None
                handle.seek(start)
                handle.truncate()
                handle.flush()
                os.fsync(handle.fileno())
                break
            if not raw.endswith(b"\n"):
                handle.seek(0, os.SEEK_END)
                handle.write(b"\n")
                handle.flush()
                os.fsync(handle.fileno())
                break
    return records


def _parse_game(records: list[dict]) -> tuple[dict | None, dict | None, bool]:
    """Extract (meta, result, valid) from one game's records. `valid` is True only for a
    completed game not marked excluded (by the result flag or a validity annotation)."""
    meta = next((row for row in records if row.get("type") == "meta"), None)
    result = next((row for row in reversed(records) if row.get("type") == "result"), None)
    valid = result.get("game_valid", True) if result else False
    for row in records:
        if row.get("type") == "annotation" and row.get("annotation") == "game_validity":
            valid = bool(row["valid"])
    return meta, result, valid


def completed_game_ids(paths: Iterable[Path]) -> set[str]:
    """Return scheduled game IDs with a valid terminal result."""
    completed: set[str] = set()
    for path in paths:
        meta, result, valid = _parse_game(recover_records(path))
        if meta and result and valid:
            scheduled_id = meta.get("scheduled_game_id")
            if scheduled_id:
                completed.add(scheduled_id)
    return completed


@dataclass
class CohortProgress:
    """The human's running record across a cohort's completed, valid games."""

    completed_ids: set[str] = field(default_factory=set)
    win: int = 0
    loss: int = 0
    draw: int = 0
    per_opponent: dict[str, list[int]] = field(default_factory=dict)  # opp_deck -> [w, l, d]

    @property
    def played(self) -> int:
        return self.win + self.loss + self.draw

    @property
    def decided(self) -> int:
        return self.win + self.loss

    @property
    def win_pct(self) -> float:
        return 100.0 * self.win / self.decided if self.decided else 0.0

    def _bump(self, opp: str, idx: int) -> None:
        self.per_opponent.setdefault(opp, [0, 0, 0])[idx] += 1


def summarize_cohort(paths: Iterable[Path]) -> CohortProgress:
    """Scan a cohort's game files once, returning completed ids plus the human's W/L/D tally
    (overall and per opponent deck). A win is `result.winner == meta.human_seat`."""
    prog = CohortProgress()
    for path in paths:
        records = recover_records(path)
        meta, result, valid = _parse_game(records)
        if not (meta and result and valid):
            continue
        scheduled_id = meta.get("scheduled_game_id")
        if scheduled_id:
            prog.completed_ids.add(scheduled_id)
        human_seat = meta.get("human_seat")
        opp = meta.get("decks", {}).get("B" if human_seat == "A" else "A", "?")
        winner = result.get("winner")
        if winner is None:
            prog.draw += 1
            prog._bump(opp, 2)
        elif winner == human_seat:
            prog.win += 1
            prog._bump(opp, 0)
        else:
            prog.loss += 1
            prog._bump(opp, 1)
    return prog
