"""Decks players build in the collection: checked against the deck rules, registered under a slug derived from their
content, and kept in `results/web_decks.json` so a restart can still load the matches that use them."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..decks import DECKS, deck_problems, register_deck
from ..game import EngineError
from .match import DECK_NAMES
from .renamed import renamed

DECKS_FILE = Path(__file__).resolve().parents[2] / "results" / "web_decks.json"
_saved: dict[str, dict] = {}


def _register(slug: str, name: str, decklist: list[str], leader: str | None) -> None:
    register_deck(slug, decklist, leader)
    DECK_NAMES.setdefault(slug, name)
    _saved[slug] = {"name": name, "list": decklist, **({"leader": leader} if leader else {})}


def load() -> None:
    if DECKS_FILE.is_file():
        for slug, d in json.loads(DECKS_FILE.read_text(encoding="utf-8")).items():
            _register(slug, d["name"], renamed(d["list"]), d.get("leader"))


def resolve(spec) -> str:
    """A player's deck, given as {"name", "list", "leader"} (or the slug of one registered before): the slug to play it
    under. Refused unless it is legal now."""
    if isinstance(spec, str):
        if spec not in DECKS:
            raise EngineError("unknown deck")
        d = _saved.get(spec, {})
        problems = deck_problems(DECKS[spec], d.get("leader"))
        if problems:
            raise EngineError("illegal deck: " + "; ".join(problems))
        return spec
    if not isinstance(spec, dict) or not isinstance(spec.get("list"), list):
        raise EngineError("unknown deck")
    decklist = sorted(str(c) for c in spec["list"])
    name = (str(spec.get("name") or "").strip() or "My deck")[:40]
    leader = str(spec.get("leader") or "") or None
    problems = deck_problems(decklist, leader)
    if problems:
        raise EngineError("illegal deck: " + "; ".join(problems))
    slug = "custom_" + hashlib.sha1((name + "|" + ",".join(decklist) + (f"|{leader}" if leader else "")).encode()).hexdigest()[:10]
    if slug not in _saved:
        _register(slug, name, decklist, leader)
        try:
            DECKS_FILE.parent.mkdir(parents=True, exist_ok=True)
            tmp = DECKS_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(_saved), encoding="utf-8")
            tmp.replace(DECKS_FILE)
        except OSError:
            pass
    return slug
