"""Decks players build in the collection: checked against the deck rules, registered under a
slug derived from their content, and kept in `results/web_decks.json` so a restart can still
load the matches that use them."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..decks import DECK_LEADERS, PREMADE_DECKS, deck_problems, load_premade_deck, register_deck
from ..engine.state import EngineError
from .match import DECK_NAMES
from .renamed import renamed

DECKS_FILE = Path(__file__).resolve().parents[2] / "results" / "web_decks.json"
_saved: dict[str, dict] = {}


def _register(slug: str, name: str, decklist: list[str], leader: str | None = None) -> None:
    if slug not in PREMADE_DECKS:      # a deck the ladder pool already holds under this slug (data/ladder_decks.json) is loadable as it is
        register_deck(slug, decklist, leader)
    DECK_NAMES.setdefault(slug, name)  # the pool's name for it stands; a new deck takes its builder's
    _saved[slug] = {"name": name, "list": decklist, **({"leader": leader} if leader else {})}


def load() -> None:
    # A deck saved before a card's id changed loads in the new ids, like a player's own decks and the game logs do:
    # the match view hands its list to the client, which knows only today's ids (Martin's study of 2026-10-22, blank).
    if DECKS_FILE.is_file():
        for slug, d in json.loads(DECKS_FILE.read_text(encoding="utf-8")).items():
            _register(slug, d["name"], renamed(d["list"]), d.get("leader"))


def resolve(spec, ruleset: str | None = None) -> str:
    """A premade slug, or a player's deck given as {"name", "list"}: returns the slug to play it under. Under a ruleset
    other than the default (the mana prototype), the deck must be legal under that ruleset's deck rules, a saved or
    premade slug included."""
    if isinstance(spec, str):
        if spec in PREMADE_DECKS or spec in _saved:
            if ruleset not in (None, "default"):
                leader = _saved[spec].get("leader") if spec in _saved else DECK_LEADERS.get(spec)
                problems = deck_problems(load_premade_deck(spec), leader, ruleset=ruleset)
                if problems:
                    raise EngineError(f"illegal deck for the {ruleset} rules: " + "; ".join(problems))
            return spec
        raise EngineError("unknown deck")
    if not isinstance(spec, dict) or not isinstance(spec.get("list"), list):
        raise EngineError("unknown deck")
    decklist = sorted(str(c) for c in spec["list"])
    name = (str(spec.get("name") or "").strip() or "My deck")[:40]
    leader = str(spec.get("leader") or "") or None          # the deck's leader, one of its legendaries: every deck has one
    problems = deck_problems(decklist, leader, ruleset=ruleset)
    if problems:
        raise EngineError(("illegal deck: " if ruleset in (None, "default") else f"illegal deck for the {ruleset} rules: ")
                          + "; ".join(problems))
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
