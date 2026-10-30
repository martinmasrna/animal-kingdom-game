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
    "army_ant_legend": ["army_ant_legend_per"],
    "forager_ant": ["forager_ant_food"],
    "worker_ant": ["worker_ant_per"],
    "worker_wasp": ["worker_wasp_per_place"],
    "worker_bee": ["worker_bee_food"],
    "tortoise_legend": ["tortoise_legend_food"],
    "sloth": ["sloth_food"],
    "rat_legend": ["rat_king_per_rodent"],
    "flying_squirrel": ["flying_squirrel_food"],
    "squirrel": ["squirrel_food"],
    "chipmunk": ["chipmunk_food_now", "chipmunk_food_later"],
    "tutorial_chipmunk": ["chipmunk_food_now", "chipmunk_food_later"],
    "groundhog": ["groundhog_food"],
    "gazelle": ["gazelle_food"],
    "hamster": ["hamster_draw_food"],
    "chipmunk_legend": ["chipmunk_legend_food_per"],
    "wildebeest": ["wildebeest_food"],
    "hyena": ["hyena_food_per"],
    "stag_beetle": ["stag_beetle_per_armor"],
    "dung_beetle": ["dung_beetle_per"],
    "tuna_legend": ["tuna_legend_food"],
}

# Cards whose food-gain number is structural, not a tunable constant, so there is
# nothing in config to compare against. Keep this list tight — it is the escape
# hatch, and every entry needs a reason.
NO_CONSTANT: set = set()

# Cards read the shared fed_threshold via "gained N or more food this turn".
FED_THRESHOLD_CARDS = {"gopher", "mara", "forager_ant"}


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
    "tiger_legend": "tiger_legend_max",
    "honey_badger": "honey_badger_min",
    "cuckoo_legend": "cuckoo_legend_max",
    "hawk": "stoop_max",
    "rhinoceros": "rhinoceros_max",
    "albatross": "albatross_max",
    "black_mamba": "black_mamba_max",
    "hippopotamus": "hippopotamus_max",
    "elephant_legend": "elephant_legend_max",
}


def test_strength_limit_text_matches_config():
    """Every printed "strength N or less/more" removal limit equals the constant its effect uses."""
    cfg = Config.default()
    for cid, attr in STRENGTH_LIMITS.items():
        (text_n,) = (int(n) for n in STRENGTH_LIMIT_RE.findall(_cards()[cid].text))
        assert getattr(cfg, attr) == text_n, f"{cid}: text says {text_n}, {attr} is {getattr(cfg, attr)}"


def test_no_strength_limit_card_escapes_the_check():
    # The Capybara's and the legendary Bee's "strength 4 or more" read the starting deck and the legendary Oxpecker's
    # "strength 8 or more" is the coverer's size, none a removal limit (test_capybara_numbers_match_config, and below).
    printed = {cid for cid, c in _cards().items() if STRENGTH_LIMIT_RE.search(c.text)}
    assert printed - {"capybara", "bee_legend_2", "oxpecker_legend"} == set(STRENGTH_LIMITS)
    (n,) = re.findall(r"strength (\d+) or more", _cards()["oxpecker_legend"].text)
    assert int(n) == Config.default().oxpecker_legend_min


def test_royal_jelly_number_matches_config():
    assert int(re.search(r"\+(\d+) strength", _cards()["bee_legend_2"].text).group(1)) == Config.default().jelly_grant


def test_capybara_numbers_match_config():
    cfg, text = Config.default(), _cards()["capybara"].text
    assert int(STRENGTH_LIMIT_RE.search(text).group(1)) == cfg.capybara_small_max + 1
    assert int(re.search(r"this has (\d+) strength", text).group(1)) == cfg.capybara_strength


STRENGTH_LOSS_RE = re.compile(r"(?:gets?|enemy) -(\d+) strength", re.IGNORECASE)


def test_strength_loss_text_matches_config():
    """Viper's and Mosquito's printed "-N strength" equal their constants, and no other card prints a loss unchecked."""
    printed = {cid: int(m.group(1)) for cid, c in _cards().items() if (m := STRENGTH_LOSS_RE.search(c.text))}
    assert printed == {"viper": Config.default().viper_poison, "mosquito": Config.default().mosquito_drain}


def test_eon_decay_text_matches_config():
    (n,) = re.findall(r"with -(\d+) strength", _cards()["anaconda_legend"].text)
    assert int(n) == Config.default().anaconda_legend_decay


DELAY_RE = re.compile(r"in (\d+) turns", re.IGNORECASE)

# card_id -> the config attr its printed "in N turns" delay comes from.
DELAY_CONSTANTS = {
    "black_bear": "black_bear_delay",
    "sloth": "sloth_delay",
    "squirrel_legend": "otk_squirrel_delay",
    "snake_egg": "egg_hatch_delay",
    "locust_swarm": "locust_delay",
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

    # "Whenever this lands" (the legendary Elephant) runs on placement and on a roam's arrival: it has the hook, no label.
    mismatched = sorted(
        cid for cid, card in load_cards().items()
        if "Whenever this lands" not in card.text
        and card.has_roar != any(hook.startswith("on_place") for hook in EFFECTS.get(cid, {})))
    assert mismatched == []


DRAW_RE = re.compile(r"\bdraw (\d+) (?:cards|snakes)", re.IGNORECASE)
SHUFFLE_RE = re.compile(r"\bshuffle (\d+) cards back", re.IGNORECASE)

# card_id -> config attrs, one per printed "draw N cards/Snakes" number in text, in order. Every card printing such a
# number must be listed (checked below), so a new draw card can't print a number its effect doesn't use.
DRAW_CONSTANTS: dict[str, list[str]] = {
    "raven": ["raven_draw"],
    "golden_egg": ["golden_egg_draw"],
    "hare": ["hare_draw"],
    "cheetah": ["cheetah_draw"],
    "nurse_bee": ["nurse_bee_draw"],
    "black_bear": ["black_bear_draw"],
    "mara": ["mara_draw"],
    "praying_mantis": ["mantis_draw"],
    "hummingbird": ["hummingbird_draw"],
    "lynx": ["lynx_draw"],
    "fox": ["fox_draw"],
    "dhole": ["dhole_draw"],
    "alley_cat": ["alley_cat_kittens"],
    "manta_ray_legend": ["manta_legend_draw"],
    "butterfly_legend_monarch": ["butterfly_legend_stage5_draw"],
    "snake_egg": ["egg_hatch_draw"],   # "draw a Snake" now (snake_egg_draw, no printed number), "draw 2 Snakes" at the hatch
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


def test_the_black_wolfs_card_is_one_and_the_wolverine_prints_no_number():
    """"Give it +1 strength and draw a card" (the +1 is in STRENGTH_BONUS_CONSTANTS below); the Wolverine's text has no
    number to map."""
    assert Config.default().black_wolf_draw == 1
    assert not re.search(r"\d", _cards()["wolverine"].text)


STRENGTH_BONUS_RE = re.compile(r"\+(\d+) strength")

# card_id -> config attrs, one per printed "+N strength" (a "give" counter or a "has/have" anthem), in order. Every card
# printing one must be listed (checked below): the launch decks brought a dozen of them at once.
STRENGTH_BONUS_CONSTANTS: dict[str, list[str]] = {
    "bee_legend_2": ["jelly_grant"],
    "guard_wasp": ["guard_hornet_bonus"],
    "python": ["python_growth"],
    "leopard_legend": ["leopard_legend_growth"],
    "dingo": ["dingo_grant"],
    "egg_eater": ["egg_eater_growth"],
    "wolf_legend": ["wolf_legend_grant"],
    "wolf_legend_2": ["black_wolf_grant"],
    "street_dog": ["street_dog_grant"],
    "mahi_mahi": ["mahi_mahi_anthem"],
    "tuna": ["tuna_per_fish"],
    "baboon_legend": ["baboon_legend_grant"],
    "gorilla_legend": ["gorilla_legend_grant"],
    "tarsier": ["tarsier_grant"],
    "baboon": ["baboon_grant"],
    "marmot": ["marmot_per_step"],
    "butterfly": ["butterfly_grant"],
    "butterfly_legend_chrysalis": ["butterfly_grant"],
    "butterfly_legend_butterfly": ["butterfly_legend_stage4_grant"],
    "butterfly_legend_monarch": ["butterfly_legend_stage5_grant"],
    "cape_buffalo": ["buffalo_anthem"],
    "peacock": ["hand_per_card"],
    "giraffe": ["giraffe_bonus"],
    "crocodile": ["crocodile_penalty"],
    "cockroach_legend": ["cockroach_legend_growth"],
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
        if len(attrs) != len(nums):
            problems.append(f"{cid}: {len(nums)} printed numbers, {len(attrs)} constants")
        for n, attr in zip(nums, attrs):
            if n != getattr(cfg, attr):
                problems.append(f"{cid}: text says +{n}, config.{attr} = {getattr(cfg, attr)}")
    for cid in STRENGTH_BONUS_CONSTANTS:
        assert cid in cards, f"{cid}: listed but not a card"
    assert not problems, "card text / config desync:\n  " + "\n  ".join(problems)


COUNT_THRESHOLD_RE = re.compile(r"(\d+) or more (animals|cards|strength|regions|Colony animals|removals|of your Fish)")

# card_id -> the config attr of its printed "N or more <things>" threshold.
THRESHOLDS = {
    "hare": "hare_played_min",
    "rat": "hare_played_min",
    "macaque": "macaque_hand_min",
    "gorilla": "gorilla_min",
    "manta_ray_legend": "manta_legend_regions",
    "nurse_bee": "colony_synergy_threshold",
    "guard_wasp": "guard_hornet_colony_threshold",
    "soldier_ant": "colony_synergy_threshold",
    "vulture": "vulture_removals",
    "piranha_legend": "piranha_legend_fish",
}


def test_thresholds_text_matches_config():
    cfg, cards = Config.default(), _cards()
    printed = {cid: int(m.group(1)) for cid, c in cards.items() if (m := COUNT_THRESHOLD_RE.search(c.text))}
    assert printed == {cid: getattr(cfg, attr) for cid, attr in THRESHOLDS.items()}


def test_the_launch_decks_other_numbers_match_config():
    """The numbers printed as words, or in a shape the patterns above don't read."""
    cfg, c = Config.default(), _cards()
    words = {"two": 2, "three": 3}
    assert words[re.search(r"add (\w+) random younglings", c["stork"].text).group(1)] == cfg.stork_younglings
    assert int(re.search(r"put (\d+) animals from your opponent's Remove Pile", c["raven_legend"].text).group(1)) == cfg.raven_legend_steals
    assert int(re.search(r"cost (\d+) food to play", c["krill_legend"].text).group(1)) == cfg.krill_legend_food
    assert int(re.search(r"for each (\d+) food you have", c["chipmunk_legend"].text).group(1)) == cfg.chipmunk_legend_food_step
    tiers = [int(re.search(r"Evolves at (\d+) food", c[f].text).group(1))
             for f in ("dung_beetle_legend", "dung_beetle_legend_form2", "dung_beetle_legend_form3")]
    assert tiers == [cfg.dung_beetle_legend_draw_at, cfg.dung_beetle_legend_food_at, cfg.dung_beetle_legend_play_at]
    assert words[re.search(r"shuffle (\w+) Cuckoo Eggs", c["cuckoo"].text).group(1)] == cfg.cuckoo_eggs
    assert words[re.search(r"shuffle (\w+) Golden Eggs", c["goose_legend"].text).group(1)] == cfg.aurum_eggs
    assert words[re.search(r"place (\w+) Worms", c["earthworm"].text).group(1)] == cfg.earthworm_worms
    assert words[re.search(r"gain (\w+) times as much", c["squirrel_legend"].text).group(1)] == cfg.otk_squirrel_multiplier
    assert int(re.search(r"give (\d+) random animals", c["baboon_legend"].text).group(1)) == cfg.baboon_legend_count
    assert int(re.search(r"give (\d+) animals", c["baboon"].text).group(1)) == cfg.baboon_count
    assert int(re.search(r"produce (\d+) more food", c["wildebeest_legend"].text).group(1)) == cfg.migration_bonus
    assert int(re.search(r"produce (\d+) less food", c["boar_legend"].text).group(1)) == cfg.boar_penalty
    assert c["great_white_shark"].text.endswith("Has Reach if an animal was removed this turn.")
    assert "Poppy and Rusty" in c["fox_legend"].text and cfg.alpha_pups == 2


def test_hungry_number_matches_its_field_and_reach_has_none():
    """"Hungry N" opening a card's text is its `hungry` field (written by the converter); Reach prints no number."""
    for cid, card in _cards().items():
        m = re.match(r"(?:\w+(?: \w+)?\. )*Hungry (\d+)\.", card.text)
        if "Hungry" in card.keywords:
            assert m and int(m.group(1)) == card.hungry, f"{cid}: Hungry {card.hungry} vs text {card.text!r}"
        assert not re.search(r"Reach \d", card.text), f"{cid}: {card.text!r}"


FOOD_CAP_RE = re.compile(r"gains at most (\d+) food per turn", re.IGNORECASE)
FOOD_CAPS = {"tortoise_legend": "tortoise_legend_food_cap"}


def test_food_cap_text_matches_config():
    """Methuselah's printed per-turn food cap equals the constant the engine caps at, and no card prints one unlisted."""
    cfg, cards = Config.default(), _cards()
    printed = {cid: int(m.group(1)) for cid, card in cards.items() if (m := FOOD_CAP_RE.search(card.text))}
    assert set(printed) == set(FOOD_CAPS)
    for cid, n in printed.items():
        assert n == getattr(cfg, FOOD_CAPS[cid]), cid
