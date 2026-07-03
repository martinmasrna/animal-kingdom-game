"""Version fingerprints for durable human-game datasets."""

from __future__ import annotations

import hashlib
import inspect
import platform
from dataclasses import asdict
from importlib import resources
from pathlib import Path

from .. import __version__
from ..bots.base import Bot
from ..engine.config import Config


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _package_hashes(package: str) -> dict[str, str]:
    root = resources.files(package)
    return {
        entry.name: hashlib.sha256(entry.read_bytes()).hexdigest()
        for entry in sorted(root.iterdir(), key=lambda item: item.name)
        if entry.name.endswith(".py")
    }


def _bot_hashes(bot: Bot) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for cls in type(bot).__mro__:
        if not cls.__module__.startswith("animal_kingdom.bots"):
            continue
        source = inspect.getsourcefile(cls)
        if source is not None:
            path = Path(source)
            hashes[path.name] = _hash_file(path)
    return dict(sorted(hashes.items()))


def build_game_provenance(bot: Bot, bot_kind: str, config: Config) -> dict:
    """Fingerprint every input needed to interpret or reproduce a recorded game."""
    data_root = resources.files("animal_kingdom") / "data"
    return {
        "animal_kingdom_version": __version__,
        "python_version": platform.python_version(),
        "engine_sha256": _package_hashes("animal_kingdom.engine"),
        "data_sha256": {
            name: hashlib.sha256((data_root / name).read_bytes()).hexdigest()
            for name in ("cards.json", "maps.json")
        },
        "bot": {
            "kind": bot_kind,
            "class": type(bot).__name__,
            "source_sha256": _bot_hashes(bot),
        },
        "config": asdict(config),
    }
