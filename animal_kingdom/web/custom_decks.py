"""Decks players build in the collection: checked against the deck rules, registered under a
slug derived from their content, and kept in `results/web_decks.json` so a restart can still
load the matches that use them."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..decks import PREMADE_DECKS, decklist_problems, register_deck
from ..engine.state import EngineError
from .match import DECK_NAMES

DECKS_FILE = Path(__file__).resolve().parents[2] / "results" / "web_decks.json"
_saved: dict[str, dict] = {}


def _register(slug: str, name: str, decklist: list[str]) -> None:
    register_deck(slug, decklist)
    DECK_NAMES[slug] = name
    _saved[slug] = {"name": name, "list": decklist}


def load() -> None:
    if DECKS_FILE.is_file():
        for slug, d in json.loads(DECKS_FILE.read_text(encoding="utf-8")).items():
            _register(slug, d["name"], d["list"])


def resolve(spec) -> str:
    """A premade slug, or a player's deck given as {"name", "list"}: returns the slug to play it under."""
    if isinstance(spec, str):
        if spec in PREMADE_DECKS or spec in _saved or spec == "goodstuff":
            return spec
        raise EngineError("unknown deck")
    if not isinstance(spec, dict) or not isinstance(spec.get("list"), list):
        raise EngineError("unknown deck")
    decklist = sorted(str(c) for c in spec["list"])
    problems = decklist_problems(decklist)
    if problems:
        raise EngineError("illegal deck: " + "; ".join(problems))
    name = (str(spec.get("name") or "").strip() or "My deck")[:40]
    slug = "custom_" + hashlib.sha1((name + "|" + ",".join(decklist)).encode()).hexdigest()[:10]
    if slug not in _saved:
        _register(slug, name, decklist)
        try:
            DECKS_FILE.parent.mkdir(parents=True, exist_ok=True)
            tmp = DECKS_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(_saved), encoding="utf-8")
            tmp.replace(DECKS_FILE)
        except OSError:
            pass
    return slug
