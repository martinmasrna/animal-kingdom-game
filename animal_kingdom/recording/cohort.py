"""Explicit, reviewable schedules for comparable human-game cohorts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, Sequence

from ..decks import PREMADE_DECKS
from ..engine.config import Config
from ..engine.maps import load_map
from ..sim.runner import BOT_KINDS


@dataclass(frozen=True)
class ScheduledGame:
    game_id: str
    seed: int
    human_seat: str
    human_deck: str
    opponent_deck: str
    opponent_kind: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ScheduledGame":
        game = cls(
            game_id=str(raw["game_id"]),
            seed=int(raw["seed"]),
            human_seat=str(raw["human_seat"]),
            human_deck=str(raw["human_deck"]),
            opponent_deck=str(raw["opponent_deck"]),
            opponent_kind=str(raw["opponent_kind"]),
        )
        game.validate()
        return game

    def validate(self) -> None:
        if not self.game_id:
            raise ValueError("scheduled game_id must not be empty")
        if self.human_seat not in ("A", "B"):
            raise ValueError(f"bad human seat {self.human_seat!r}")
        for label, slug in (
            ("human_deck", self.human_deck),
            ("opponent_deck", self.opponent_deck),
        ):
            if slug not in PREMADE_DECKS:
                raise ValueError(f"unknown {label} {slug!r}")
        if self.opponent_kind not in BOT_KINDS:
            raise ValueError(f"unknown opponent kind {self.opponent_kind!r}")


@dataclass(frozen=True)
class CohortManifest:
    cohort_id: str
    map_id: str
    config: Config
    games: tuple[ScheduledGame, ...]
    generation: dict[str, Any]
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "cohort_id": self.cohort_id,
            "map_id": self.map_id,
            "config": asdict(self.config),
            "generation": self.generation,
            "games": [game.to_dict() for game in self.games],
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "CohortManifest":
        if raw.get("schema_version") != 1:
            raise ValueError(f"unsupported cohort schema {raw.get('schema_version')!r}")
        config = Config(**raw["config"])
        manifest = cls(
            cohort_id=str(raw["cohort_id"]),
            map_id=str(raw["map_id"]),
            config=config,
            generation=dict(raw.get("generation") or {}),
            games=tuple(ScheduledGame.from_dict(game) for game in raw["games"]),
        )
        manifest.validate()
        return manifest

    def validate(self) -> None:
        if not self.cohort_id:
            raise ValueError("cohort_id must not be empty")
        load_map(self.map_id)
        if not self.games:
            raise ValueError("cohort must contain at least one game")
        ids = [game.game_id for game in self.games]
        if len(ids) != len(set(ids)):
            raise ValueError("cohort contains duplicate game IDs")


def config_drift(config: Config) -> list[tuple[str, Any, Any]]:
    """Pinned constants whose value differs from the current code default (`Config.default()`),
    as (name, pinned, current) triples. A schedule freezes the config at generation time so a
    cohort's games share identical rules; if a balance constant is changed in code afterwards, the
    schedule keeps recording with the stale pinned value. A non-empty result flags exactly that."""
    default = Config.default()
    return [
        (f.name, getattr(config, f.name), getattr(default, f.name))
        for f in fields(Config)
        if getattr(config, f.name) != getattr(default, f.name)
    ]


def load_manifest(path: Path | str) -> CohortManifest:
    with open(path, encoding="utf-8") as handle:
        return CohortManifest.from_dict(json.load(handle))


def write_manifest(path: Path | str, manifest: CohortManifest) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n")


def _game_id(cohort_id: str, payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(f"{cohort_id}:{canonical}".encode()).hexdigest()[:12]
    return f"{cohort_id}-{digest}"


def generate_manifest(
    *,
    cohort_id: str,
    human_decks: Sequence[str],
    opponent_decks: Sequence[str],
    opponent_kinds: Sequence[str],
    repetitions: int,
    seats: Sequence[str],
    base_seed: int,
    schedule_seed: int,
    map_id: str,
    config: Config,
    exclude_mirrors: bool = False,
    shuffle: bool = True,
) -> CohortManifest:
    """Expand a balanced grid into explicit games. By default the games are shuffled
    reproducibly (comparable-cohort methodology); pass shuffle=False to keep them grouped by
    matchup in generation order (all reps of one opponent consecutively) for focused play."""
    import random

    if repetitions <= 0:
        raise ValueError("repetitions must be positive")
    if not seats or any(seat not in ("A", "B") for seat in seats):
        raise ValueError("seats must contain A and/or B")
    load_map(map_id)
    for slug in (*human_decks, *opponent_decks):
        if slug not in PREMADE_DECKS:
            raise ValueError(f"unknown deck {slug!r}")
    for kind in opponent_kinds:
        if kind not in BOT_KINDS:
            raise ValueError(f"unknown bot kind {kind!r}")

    games: list[ScheduledGame] = []
    pair_index = 0
    for human_deck in human_decks:
        for opponent_deck in opponent_decks:
            if exclude_mirrors and human_deck == opponent_deck:
                continue
            for opponent_kind in opponent_kinds:
                for repetition in range(repetitions):
                    seed = base_seed + pair_index
                    pair_index += 1
                    for seat in seats:
                        identity = {
                            "human_deck": human_deck,
                            "opponent_deck": opponent_deck,
                            "opponent_kind": opponent_kind,
                            "repetition": repetition,
                            "human_seat": seat,
                            "seed": seed,
                        }
                        games.append(ScheduledGame(
                            game_id=_game_id(cohort_id, identity),
                            seed=seed,
                            human_seat=seat,
                            human_deck=human_deck,
                            opponent_deck=opponent_deck,
                            opponent_kind=opponent_kind,
                        ))
    if shuffle:
        random.Random(schedule_seed).shuffle(games)
    manifest = CohortManifest(
        cohort_id=cohort_id,
        map_id=map_id,
        config=config,
        games=tuple(games),
        generation={
            "human_decks": list(human_decks),
            "opponent_decks": list(opponent_decks),
            "opponent_kinds": list(opponent_kinds),
            "repetitions": repetitions,
            "seats": list(seats),
            "base_seed": base_seed,
            "schedule_seed": schedule_seed,
            "exclude_mirrors": exclude_mirrors,
            "shuffle": shuffle,
        },
    )
    manifest.validate()
    return manifest
