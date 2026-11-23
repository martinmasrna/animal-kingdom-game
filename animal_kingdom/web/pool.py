"""The ranked bots' pool: the decks they play, and the rating each bot starts from.

The decks are the premade ones (`data/decks.json`) that are legal with today's cards. One a card change made illegal is
out of the pool until its list is mended, and comes back by itself when it is.

A bot is one level (web/match.py BOT_LEVELS) with one deck. Its rating is measured: `tools/ladder/seed.py` plays every
bot against every other and writes `web/ladder_seed.json`, each rating beside a print of what it was measured with (the
level's bot, the map, the rules' numbers, the deck's list and every card in it as the engine reads it). A rating whose
print no longer matches was measured with other cards: the bot then stands on its level's rating (the mean of that level
over the decks measured, which a deck's cards do not move) with a wider uncertainty, so it counts for less and finds its
place faster, until the seed is measured again. The numbers a card change does not reach stay as they are.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Optional

from .. import game
from ..decks import register_deck
from . import ladder
from .match import BOT_LEVELS, DECK_NAMES

SEED_FILE = Path(__file__).parent / "ladder_seed.json"


def premade() -> list[dict]:
    """Every premade deck: {slug, name, leader, cards}."""
    return [{**d, "slug": re.sub(r"[^a-z0-9]+", "_", d["name"].lower()).strip("_")} for d in game.load_bundled_json("decks.json")["decks"]]


def legal(decks: Optional[list[dict]] = None, cards: Optional[dict] = None) -> list[dict]:
    """The premade decks today's cards allow."""
    return [d for d in (premade() if decks is None else decks) if not game.deck_problems(d["cards"], d["leader"], cards=cards)]


def load() -> list[dict]:
    """The pool, its decks registered to be played under their slugs."""
    decks = legal()
    for d in decks:
        register_deck(d["slug"], d["cards"], d["leader"])
        DECK_NAMES.setdefault(d["slug"], d["name"])
    return decks


def measured_with(level: str, deck: dict, map_id: str = game.MAP_ID, cards: Optional[dict] = None) -> str:
    """A print of everything a bot's rating was measured with. A card in another bot's deck is not in it: a change there
    moves this bot's rating a little, through the games against that deck, and that is left to the next seed."""
    cards = game.CARDS if cards is None else cards
    seen, todo = {}, sorted(set(deck["cards"]))
    while todo:   # the deck's cards and the cards they make
        cid = todo.pop()
        if cid in seen or cid not in cards:
            continue
        c = cards[cid]
        seen[cid] = [c.rarity, c.base_strength, c.cost, sorted(c.keywords), c.dynamic_strength, c.text, list(c.makes), c.weaken]
        todo += c.makes
    what = [BOT_LEVELS[level], map_id, sorted(game.Config().as_dict().items()), deck["leader"], sorted(deck["cards"]), sorted(seen.items())]
    return hashlib.sha1(json.dumps(what).encode()).hexdigest()[:12]


def read_seed(path: Path = SEED_FILE) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def ratings(decks: list[dict], seed: Optional[dict] = None, map_id: str = game.MAP_ID, cards: Optional[dict] = None) -> dict[str, tuple[float, float, str]]:
    """Where each bot of the pool starts: bot ladder id -> (rating, uncertainty, source) for ladder.Ladder.set_bots. The
    seed's own number when it was measured with what the bot plays with today; else the level's."""
    seed = read_seed() if seed is None else seed
    version, levels, rows = seed.get("version", "none"), seed.get("levels", {}), {}
    for d in decks:
        for level in ladder.LEVELS:
            lid, now = ladder.bot_id(level, d["slug"]), measured_with(level, d, map_id, cards)
            row = seed.get("ratings", {}).get(lid)
            if row and row["with"] == now:
                rows[lid] = (row["rating"], ladder.BOT_RD, f"{version}:{now}")
            else:
                lv = levels.get(level, {})
                base = lv["rating"] if lv.get("bot") == BOT_LEVELS[level] else ladder.LEVEL_START[level]
                rows[lid] = (base, ladder.UNMEASURED_RD, f"{version}:level:{now}")
    return rows
