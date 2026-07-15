"""Guard against card-text vs config-constant desync.

Card *text* (data/cards.json) and the *numbers* a card's effect actually uses
(engine/config.py) are authored independently — nothing structural forces them
to agree. On 2026-07-09 Flying Squirrel's text promised "gain 10 food" while
``flying_squirrel_food`` was 8, which silently broke the food_otk fed-threshold
combo (greywhisker 1 + squirrel 8 = 9 < 10). This test would have caught it.

Approach: the *linkage* between a card and its constant lives in effect code, so
it is expressed here as an explicit ``card_id -> [config attrs]`` map. But the
*expected numbers* are parsed out of the live card text — no number is hardcoded
in this test, so editing either side and forgetting the other fails the test.

``GAIN_FOOD_RE`` matches the "gain N food"/"gain N more" phrasings that denote a
concrete food amount; ``THRESHOLD_RE`` matches the shared "gained N or more food
this turn" fed-threshold phrasing.
"""

from __future__ import annotations

import re

from animal_kingdom.engine.cards import load_cards
from animal_kingdom.engine.config import Config

GAIN_FOOD_RE = re.compile(r"gain (\d+) (?:food|more)", re.IGNORECASE)
THRESHOLD_RE = re.compile(r"gained (\d+) or more food this turn", re.IGNORECASE)
COSTS_RE = re.compile(r"costs (\d+) food", re.IGNORECASE)

# card_id -> config attrs, one per "gain N food/more" number in text, in order.
FOOD_CONSTANTS: dict[str, list[str]] = {
    "eon": ["eon_food"],
    "egg_eater": ["egg_eater_food"],
    "queen_marabunta": ["queen_marabunta_per_colony"],
    "queen_honoria": ["queen_honoria_per_play"],
    "worker_ant": ["worker_ant_food"],
    "worker_wasp": ["worker_wasp_food"],
    "worker_bee": ["worker_bee_food", "worker_bee_extra"],
    "methuselah": ["methuselah_food"],
    "sloth": ["sloth_food"],
    "greywhisker": ["greywhisker_food"],
    "rat_king": ["rat_king_per_rodent"],
    "flying_squirrel": ["flying_squirrel_food"],
    "squirrel": ["squirrel_food"],
    "chipmunk": ["chipmunk_food_now", "chipmunk_food_later"],
    "hedgehog": ["hedgehog_food"],
    "groundhog": ["groundhog_food"],
    "gopher": ["rodent_last_turn_food"],
    "jackal": ["jackal_food"],
}

# Cards whose food-gain number is structural, not a tunable constant, so there is
# nothing in config to compare against. Keep this list tight — it is the escape
# hatch, and every entry needs a reason.
NO_CONSTANT = {
    # "gain 1 food for each unit ..." — the per-unit rate of 1 is hardcoded in
    # _oxpecker_place; there is no oxpecker_food dial.
    "oxpecker",
}

# Cards read the shared fed_threshold via "gained N or more food this turn".
FED_THRESHOLD_CARDS = {"hamster", "muskrat", "groundhog"}


def _cards():
    return load_cards()


def test_gain_food_text_matches_config():
    """Every "gain N food" number in card text equals the constant its effect uses."""
    cfg = Config.default()
    mismatches = []
    for cid, attrs in FOOD_CONSTANTS.items():
        card = _cards()[cid]
        text_nums = [int(n) for n in GAIN_FOOD_RE.findall(card.text)]
        assert len(text_nums) == len(attrs), (
            f"{cid}: text has {len(text_nums)} food-gain numbers {text_nums} but "
            f"FOOD_CONSTANTS lists {len(attrs)} attrs {attrs} — update the map."
        )
        for text_n, attr in zip(text_nums, attrs):
            cfg_n = getattr(cfg, attr)
            if text_n != cfg_n:
                mismatches.append(f"{cid}: text says {text_n}, config.{attr} = {cfg_n}")
    assert not mismatches, "card text / config desync:\n  " + "\n  ".join(mismatches)


def test_fed_threshold_text_matches_config():
    """The "gained N or more food this turn" phrasing equals config.fed_threshold."""
    cfg = Config.default()
    for cid in FED_THRESHOLD_CARDS:
        card = _cards()[cid]
        nums = [int(n) for n in THRESHOLD_RE.findall(card.text)]
        assert nums, f"{cid}: expected a fed-threshold phrase in text {card.text!r}"
        for n in nums:
            assert n == cfg.fed_threshold, (
                f"{cid}: text threshold {n} != config.fed_threshold {cfg.fed_threshold}"
            )


def test_costs_text_matches_food_cost():
    """A printed "Costs N food" must equal the card's `food_cost` (what effects.py charges).

    Unlike the gain-food numbers above, a placement cost is card-intrinsic: it lives in
    cards.json next to base_strength, NOT in config.py. A `costs_20_food = 20` constant sat in
    config until 2026-07-15 — unread by any code, and stale from a27f0df (which cut these bodies
    to 15). Nothing linked the printed number to the charged one; this does.
    """
    mismatches = []
    for cid, card in _cards().items():
        printed = [int(n) for n in COSTS_RE.findall(card.text)]
        if printed and printed[0] != card.food_cost:
            mismatches.append(f"{cid}: text says Costs {printed[0]} food, food_cost = {card.food_cost}")
    assert not mismatches, "card text / food_cost desync:\n  " + "\n  ".join(mismatches)


def test_no_costed_card_escapes_the_check():
    """A charged cost must be printed, and a printed cost must be charged — no silent gate."""
    unprinted, uncharged = [], []
    for cid, card in _cards().items():
        printed = COSTS_RE.findall(card.text)
        if card.food_cost and not printed:
            unprinted.append(f"{cid}: food_cost={card.food_cost} but text {card.text!r} never says so")
        if printed and not card.food_cost:
            uncharged.append(f"{cid}: text {card.text!r} promises a cost but food_cost=0")
    assert not unprinted, "cost charged but not printed:\n  " + "\n  ".join(unprinted)
    assert not uncharged, "cost printed but not charged:\n  " + "\n  ".join(uncharged)


def test_no_food_card_escapes_the_check():
    """Any card with a numeric food-gain in text must be mapped or explicitly skipped.

    This is what keeps the guard honest as the pool grows: add a card that reads
    "gain N food" and forget to wire it up, and this fails rather than silently
    leaving a desync uncovered.
    """
    covered = set(FOOD_CONSTANTS) | NO_CONSTANT
    unaccounted = [
        cid
        for cid, card in _cards().items()
        if GAIN_FOOD_RE.search(card.text or "") and cid not in covered
    ]
    assert not unaccounted, (
        "cards with a 'gain N food' text but no config mapping — add them to "
        f"FOOD_CONSTANTS or NO_CONSTANT in this test: {sorted(unaccounted)}"
    )
