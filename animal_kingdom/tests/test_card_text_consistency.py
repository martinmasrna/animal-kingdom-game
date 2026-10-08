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
    "eon_food_engine": ["eon_food"],
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
    "hamster": ["hamster_food_now", "hamster_food_later"],
    "tutorial_chipmunk": ["hamster_food_now", "hamster_food_later"],
    "hedgehog": ["hedgehog_food"],
    "groundhog": ["groundhog_food"],
    "gazelle": ["gazelle_food"],
    "mole": ["mole_food"],
    "dormouse": ["dormouse_food"],
    "wildebeest": ["wildebeest_food"],
    "hyena": ["hyena_food_per"],
    "tortoise": ["tortoise_per_armor"],
    "dung_beetle": ["dung_beetle_per"],
    "fish_legend_tuna": ["tuna_legend_food"],
    **{f"calib_food10_{n}": ["squirrel_food"] for n in (2, 3, 4, 5, 6)},
    **{f"calib_food3t_{n}": ["worker_wasp_food"] for n in (2, 3, 4, 5, 6)},
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
FED_THRESHOLD_CARDS = {"gopher", "muskrat", "groundhog"}


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


STRENGTH_LIMIT_RE = re.compile(r"strength (\d+) or (?:less|more)", re.IGNORECASE)

# card_id -> the config attr holding its "strength N or less/more" removal limit.
STRENGTH_LIMITS = {
    "jaguar": "jaguar_max",
    "honey_badger": "honey_badger_min",
    "aristocrats_legend_cuckoo": "cuckoo_legend_max",
    "city_spider": "city_spider_max",
    "stoop": "stoop_max",
    "rhinoceros": "rhinoceros_max",
    "black_mamba": "black_mamba_max",
    "hippopotamus": "hippopotamus_max",
    "mock_sentry": "stoop_max",
    "mock_hunter": "calib_rm4_max",
    **{f"calib_rm3_{n}": "stoop_max" for n in (2, 3, 4, 5, 6)},
    **{f"calib_rm4_{n}": "calib_rm4_max" for n in (2, 3, 4, 5, 6)},
    **{f"calib_rm6_{n}": "calib_rm6_min" for n in (1, 2, 3, 4, 5)},
}


def test_strength_limit_text_matches_config():
    """Every printed "strength N or less/more" removal limit equals the constant its effect uses."""
    cfg = Config.default()
    for cid, attr in STRENGTH_LIMITS.items():
        (text_n,) = (int(n) for n in STRENGTH_LIMIT_RE.findall(_cards()[cid].text))
        assert getattr(cfg, attr) == text_n, f"{cid}: text says {text_n}, {attr} is {getattr(cfg, attr)}"


def test_no_strength_limit_card_escapes_the_check():
    # Oxpecker's "strength 8 or more" counts its own decklist, not a removal limit (checked below).
    printed = {cid for cid, c in _cards().items() if STRENGTH_LIMIT_RE.search(c.text)}
    assert printed - {"oxpecker"} == set(STRENGTH_LIMITS)


STRENGTH_LOSS_RE = re.compile(r"(?:gets?|enemy) -(\d+) strength", re.IGNORECASE)


def test_strength_loss_text_matches_config():
    """Viper's and Mosquito's printed "-N strength" equal their constants, and no other card prints a loss unchecked."""
    printed = {cid: int(m.group(1)) for cid, c in _cards().items() if (m := STRENGTH_LOSS_RE.search(c.text))}
    assert printed == {"viper": Config.default().viper_poison, "mosquito": Config.default().mosquito_drain}


def test_eon_decay_text_matches_config():
    (n,) = re.findall(r"with -(\d+) strength", _cards()["eon"].text)
    assert int(n) == Config.default().eon_decay


DELAY_RE = re.compile(r"in (\d+) turns", re.IGNORECASE)

# card_id -> the config attr its printed "in N turns" delay comes from.
DELAY_CONSTANTS = {
    "black_bear": "black_bear_delay",
    "sloth": "sloth_delay",
    "food_otk_legend_squirrel": "otk_squirrel_delay",
    "snake_egg": "egg_hatch_delay",
}


def test_delay_text_matches_config():
    """Every printed "in N turns" equals its delay constant, and no card prints one unchecked."""
    cfg = Config.default()
    printed = {cid: int(m.group(1)) for cid, c in _cards().items() if (m := DELAY_RE.search(c.text))}
    assert printed == {cid: getattr(cfg, attr) for cid, attr in DELAY_CONSTANTS.items()}


def test_egg_text_matches_config():
    cfg = Config.default()
    snake = _cards()["snake_egg"].text
    assert "draw a Snake" in snake and cfg.snake_egg_draw == 1
    assert f"draw {cfg.egg_hatch_draw} Snakes" in snake
    assert "Next turn" in _cards()["bird_egg"].text and cfg.bird_egg_hatch_delay == 1


def test_egg_eater_growth_text_matches_config():
    (n,) = re.findall(r"Has \+(\d+) strength for each removed Egg", _cards()["egg_eater"].text)
    assert int(n) == Config.default().egg_eater_growth


def test_roar_label_matches_placement_effect():
    """"Roar:" in the text exactly when the engine runs an effect on placement (Caracal's
    only when placed onto an enemy).

    The bots read `has_roar` off the text, so an unlabelled placement effect (Andean
    Condor, Oxpecker, Sloth and Skunk until 2026-09-30) was invisible to them.
    """
    from animal_kingdom.engine.effects import EFFECTS

    mismatched = sorted(
        cid for cid, card in load_cards().items()
        if card.has_roar != any(hook.startswith("on_place") for hook in EFFECTS.get(cid, {})))
    assert mismatched == []


DRAW_RE = re.compile(r"\bdraw (\d+) (?:cards|snakes)", re.IGNORECASE)
SHUFFLE_RE = re.compile(r"\bshuffle (\d+) cards back", re.IGNORECASE)

# card_id -> config attrs, one per printed "draw N cards/Snakes" number in text, in order. Every card printing such a
# number must be listed (checked below), so a new draw card can't print a number its effect doesn't use.
DRAW_CONSTANTS: dict[str, list[str]] = {
    "raven": ["raven_draw"],
    "nurse_bee": ["nurse_bee_draw"],
    "nurse_bumblebee": ["nurse_bumblebee_draw"],
    "black_bear": ["black_bear_draw"],
    "gopher": ["gopher_draw"],
    "praying_mantis": ["mantis_draw"],
    "mole": ["mole_draw"],
    "hummingbird": ["hummingbird_draw"],
    "whale_shark": ["whale_shark_draw"],
    "handlock_legend_butterfly_5": ["butterfly_legend_stage5_draw"],
    "snake_egg": ["egg_hatch_draw"],   # "draw a Snake" now (snake_egg_draw, no printed number), "draw 2 Snakes" at the hatch
    **{cid: ["test_draw"] for cid in ("mock_draw2", "mock_skully", *(f"calib_draw2_{n}" for n in range(4)))},
}
SHUFFLE_CONSTANTS = {"raven": "raven_shuffle"}


def test_draw_and_shuffle_text_matches_config():
    """Every printed "draw N cards" and "shuffle N cards back" equals the constant its effect uses, and no card prints one
    unlisted (Raven's 3 and 2 and the Nurse Bees' 2 were literals in effect code until 2026-10-02)."""
    cfg, cards = Config.default(), _cards()
    problems = []
    for cid, card in cards.items():
        nums = [int(n) for n in DRAW_RE.findall(card.text)]
        if nums and cid not in DRAW_CONSTANTS:
            problems.append(f"{cid}: text prints draw {nums} but DRAW_CONSTANTS doesn't list it")
        for n, attr in zip(nums, DRAW_CONSTANTS.get(cid, [])):
            if n != getattr(cfg, attr):
                problems.append(f"{cid}: text says draw {n}, config.{attr} = {getattr(cfg, attr)}")
        for n in (int(x) for x in SHUFFLE_RE.findall(card.text)):
            attr = SHUFFLE_CONSTANTS.get(cid)
            if attr is None or n != getattr(cfg, attr):
                problems.append(f"{cid}: text says shuffle {n} back, config.{attr} = {attr and getattr(cfg, attr)}")
    for cid in DRAW_CONSTANTS:
        assert cid in cards, f"{cid}: in DRAW_CONSTANTS but not a card"
    assert not problems, "card text / config desync:\n  " + "\n  ".join(problems)


STRENGTH_BONUS_RE = re.compile(r"\+(\d+) strength")

# card_id -> config attrs, one per printed "+N strength" (a "give" counter or a "has/have" anthem), in order. Every card
# printing one must be listed (checked below): the launch decks brought a dozen of them at once.
STRENGTH_BONUS_CONSTANTS: dict[str, list[str]] = {
    "vesper": ["anthem_vesper_per"],
    "guard_hornet": ["guard_hornet_bonus"],
    "verminus": ["anthem_verminus_per"],
    "goliath": [],                             # dynamic strength: its +1 per removed animal is the rule itself
    "raksha": ["raksha_anthem"],
    "dingo": ["dingo_grant"],
    "shuck": ["shuck_grant"],
    "egg_eater": ["egg_eater_growth"],
    "canines_legend_wolf": ["wolf_legend_grant"],
    "bush_dog": ["bush_dog_grant"],
    "raccoon_dog": ["raccoon_dog_grant"],
    "fox": ["fox_grant"],
    "dog": ["stray_dog_grant"],
    "mahi_mahi": ["mahi_mahi_grant"],
    "mackerel": ["mackerel_anthem"],
    "tuna": ["tuna_per_fish"],
    "handlock_legend_baboon": ["baboon_legend_grant"],
    "silverback": ["silverback_grant"],
    "tarsier": ["tarsier_grant"],
    "baboon": ["baboon_grant"],
    "grizzly_bear": ["grizzly_per_card"],
    "butterfly": ["butterfly_grant"],
    "handlock_legend_butterfly_3": ["butterfly_grant"],
    "handlock_legend_butterfly_4": ["butterfly_legend_stage4_grant"],
    "handlock_legend_butterfly_5": ["butterfly_legend_stage5_grant"],
    "moose": ["moose_anthem"],
    "giraffe": ["giraffe_bonus"],
    "boar": ["boar_grazing_bonus"],
}


def test_strength_bonus_text_matches_config():
    """Every printed "+N strength" equals the constant its effect or anthem uses, and no card prints one unlisted."""
    cfg, cards = Config.default(), _cards()
    problems = []
    for cid, card in cards.items():
        nums = [int(n) for n in STRENGTH_BONUS_RE.findall(card.text)]
        if not nums:
            continue
        if cid not in STRENGTH_BONUS_CONSTANTS:
            problems.append(f"{cid}: text prints +{nums} strength but STRENGTH_BONUS_CONSTANTS doesn't list it")
            continue
        attrs = STRENGTH_BONUS_CONSTANTS[cid]
        if cid == "goliath":
            assert nums == [1]
            continue
        if len(attrs) != len(nums):
            problems.append(f"{cid}: {len(nums)} printed numbers, {len(attrs)} constants")
        for n, attr in zip(nums, attrs):
            if n != getattr(cfg, attr):
                problems.append(f"{cid}: text says +{n}, config.{attr} = {getattr(cfg, attr)}")
    for cid in STRENGTH_BONUS_CONSTANTS:
        assert cid in cards, f"{cid}: listed but not a card"
    assert not problems, "card text / config desync:\n  " + "\n  ".join(problems)


COUNT_THRESHOLD_RE = re.compile(r"(\d+) or more (animals|cards|strength|regions|Colony animals)")

# card_id -> the config attr of its printed "N or more <things>" threshold.
THRESHOLDS = {
    "hare": "hare_played_min",
    "macaque": "macaque_hand_min",
    "gorilla": "gorilla_min",
    "fish_legend_manta_ray": "manta_legend_regions",
    "nurse_bumblebee": "colony_synergy_threshold",
    "guard_hornet": "guard_hornet_colony_threshold",
    "soldier_ant": "colony_synergy_threshold",
    "unnamed_canine": "unnamed_canine_draw_threshold",
}


def test_thresholds_text_matches_config():
    cfg, cards = Config.default(), _cards()
    printed = {cid: int(m.group(1)) for cid, c in cards.items() if (m := COUNT_THRESHOLD_RE.search(c.text))}
    assert printed == {cid: getattr(cfg, attr) for cid, attr in THRESHOLDS.items()}


def test_oxpecker_threshold_matches_config():
    (n,) = re.findall(r"strength (\d+) or more", _cards()["oxpecker"].text)
    assert int(n) == Config.default().oxpecker_min


def test_the_launch_decks_other_numbers_match_config():
    """The numbers printed as words, or in a shape the patterns above don't read."""
    cfg, c = Config.default(), _cards()
    words = {"two": 2, "three": 3}
    assert words[re.search(r"add (\w+) random younglings", c["stork"].text).group(1)] == cfg.stork_younglings
    assert words[re.search(r"shuffle (\w+) Cuckoo Eggs", c["cuckoo"].text).group(1)] == cfg.cuckoo_eggs
    assert words[re.search(r"place (\w+) Worms", c["earthworm"].text).group(1)] == cfg.earthworm_worms
    assert words[re.search(r"gain (\w+) times as much", c["food_otk_legend_squirrel"].text).group(1)] == cfg.otk_squirrel_multiplier
    assert int(re.search(r"give (\d+) random animals", c["handlock_legend_baboon"].text).group(1)) == cfg.baboon_legend_count
    assert int(re.search(r"give (\d+) animals", c["baboon"].text).group(1)) == cfg.baboon_count
    assert int(re.search(r"produce (\d+) more food", c["hoofed_legend_wildebeest"].text).group(1)) == cfg.migration_bonus
    assert int(re.search(r"produce (\d+) less food", c["hoofed_legend_boar"].text).group(1)) == cfg.boar_penalty
    assert int(re.search(r"Reach (\d+)", c["great_white_shark"].text).group(1)) == cfg.shark_reach
    assert int(re.search(r"strength to (\d+)", c["serval"].text).group(1)) == cfg.serval_set
    assert "Poppy and Rusty" in c["alpha"].text and cfg.alpha_pups == 2


def test_hungry_and_reach_numbers_match_their_fields():
    """"Hungry N" and "Reach N" opening a card's text are its `hungry` and `reach` fields (written by the converter)."""
    for cid, card in _cards().items():
        for kw, field in (("Hungry", card.hungry), ("Reach", card.reach)):
            m = re.match(r"(?:\w+(?: \w+)?\. )*" + kw + r" (\d+)\.", card.text)
            if kw in card.keywords:
                assert m and int(m.group(1)) == field, f"{cid}: {kw} {field} vs text {card.text!r}"
