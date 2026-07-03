"""Append-only, crash-tolerant JSONL writer for one recorded game attempt."""

from __future__ import annotations

import json
import os
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


def completed_game_ids(paths: Iterable[Path]) -> set[str]:
    """Return scheduled game IDs with a valid terminal result."""
    completed: set[str] = set()
    for path in paths:
        records = recover_records(path)
        meta = next((row for row in records if row.get("type") == "meta"), None)
        result = next((row for row in reversed(records) if row.get("type") == "result"), None)
        valid = result.get("game_valid", True) if result else False
        for row in records:
            if row.get("type") == "annotation" and row.get("annotation") == "game_validity":
                valid = bool(row["valid"])
        if meta and result and valid:
            scheduled_id = meta.get("scheduled_game_id")
            if scheduled_id:
                completed.add(scheduled_id)
    return completed
