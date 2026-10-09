"""The launch decks' mechanics and cards, one scenario each (the card workbench's twelve decks, 2026-10-08).

Map A (the test fixture): a 4x3 grid, A's den fronts column 1, B's column 4; "2,2" neighbours "1,2", "3,2", "2,1",
"2,3". Regions: R1 = 1,1 2,1 1,2 2,2 (10 food), R4 = 1,2 2,2 1,3 2,3 (10), R2/R5 the middle ones (20).
"""

from __future__ import annotations

import pytest

from animal_kingdom.engine import effects, rules, statics
from animal_kingdom.engine.actions import SKIP, ChoiceAction, DrawAction, PassAction, PlaceAction, RoamAction
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.strength import effective_strength, placement_strength

from animal_kingdom.engine.cards import load_cards

from ._helpers import apply_click, hand_ids, make_state, put

CFG = Config.default()


def end_turn(s):
    """End the turn of whoever is to move (a pass; two in a row would end the game, so the count is reset)."""
    s.idle_turns = 0
    rules.apply_action(s, PassAction())


def choose(s, option):
    assert s.pending is not None and option in s.pending["options"], (option, s.pending)
    rules.apply_action(s, ChoiceAction(option))


def hand_inst(s, player, card_id):
    return next(u for u in s.hands[player] if u.card_id == card_id)


def removed(s, card_id):
    return card_id in s.remove_pile


# ================================================================================ keywords

def test_hungry_eats_at_the_start_of_your_turn_or_shrinks_for_good():
    s = make_state(food={"A": 7, "B": 0}, decks={"A": ["lion"] * 4, "B": ["lion"] * 4})
    ele = put(s, "1,2", "elephant", "A")                       # Hungry 5
    end_turn(s); end_turn(s)                                   # A's next turn starts: it eats 5
    assert s.food["A"] == 2 and effective_strength(s, ele) == 9
    end_turn(s); end_turn(s)                                   # 2 food: it can't eat
    assert s.food["A"] == 2 and effective_strength(s, ele) == 9 - 5


def test_an_adjacent_legendary_oxpecker_feeds_hungry_animals():
    s = make_state(food={"A": 0, "B": 0}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    ele = put(s, "1,2", "elephant", "A")
    put(s, "2,2", "giants_legend_oxpecker", "A")
    end_turn(s); end_turn(s)
    assert effective_strength(s, ele) == 9


def test_titan_costs_two_actions_and_no_free_placement_pays_for_it():
    s = make_state(hands={"A": ["blue_whale", "lion"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    assert PlaceAction("blue_whale", ("cr", "1,2")) in rules.legal_actions(s)
    rules.apply_action(s, PlaceAction("blue_whale", ("cr", "1,2")))
    assert s.current == "B"                                    # both actions spent
    s2 = make_state(hands={"A": ["lion", "blue_whale"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    rules.apply_action(s2, PlaceAction("lion", ("cr", "1,1")))  # one action left
    assert not [a for a in rules.legal_actions(s2) if getattr(a, "card_id", None) == "blue_whale"]
    s3 = make_state(hands={"A": ["calib_extra_2", "blue_whale"]})
    rules.apply_action(s3, PlaceAction("calib_extra_2", ("cr", "1,1")))   # "play another animal": a free placement
    assert s3.pending is None or all(p["card_id"] != "blue_whale" for p in s3.pending.get("placements", []))


def test_flee_returns_the_covered_animal_to_its_owners_hand():
    s = make_state(current="B", hands={"B": ["lion"]})
    put(s, "4,2", "lion", "B")
    put(s, "3,2", "gazelle", "A")                              # Flee, 3
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))
    assert "gazelle" in hand_ids(s, "A") and [u.card_id for u in s.board["3,2"]] == ["lion"]
    assert not removed(s, "gazelle")                           # a return, not a removal


def test_flee_runs_before_an_apex_predator_can_eat():
    s = make_state(current="B", hands={"B": ["tiger"]})
    put(s, "4,2", "lion", "B")
    put(s, "3,2", "gazelle", "A")
    rules.apply_action(s, PlaceAction("tiger", ("cr", "3,2")))
    assert "gazelle" in hand_ids(s, "A") and s.top_unit("3,2").card_id == "tiger"


def test_the_zebra_flees_and_sends_its_coverer_home_too():
    s = make_state(current="B", hands={"B": ["lion"]})
    put(s, "4,2", "lion", "B")
    put(s, "3,2", "zebra", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))
    assert "zebra" in hand_ids(s, "A") and "lion" in hand_ids(s, "B") and s.top_unit("3,2") is None


def test_octopus_ink_switches_one_chosen_enemys_effects_off_until_the_inkers_next_turn():
    s = make_state(hands={"A": ["octopus", "lion"]}, decks={"A": ["lion"] * 4, "B": ["lion"] * 4})
    put(s, "1,2", "caracal", "A")
    porc = put(s, "3,2", "porcupine", "B")                     # Spikes, 7
    py = put(s, "2,3", "goliath", "B")                         # dynamic strength
    s.pile_add("lion", "A"); s.pile_add("lion", "A")
    assert effective_strength(s, py) == 2
    rules.apply_action(s, PlaceAction("octopus", ("cr", "2,2")))
    choose(s, "3,2")                                            # one target: the Porcupine
    assert statics.inked(s, porc) and not statics.inked(s, py) and effective_strength(s, py) == 2
    assert "Spikes" not in statics.unit_keywords(s, porc)
    end_turn(s)                                                 # the opponent's turn: still inked
    assert statics.inked(s, porc)
    end_turn(s)                                                 # the inking player's next turn: the ink is gone
    assert not statics.inked(s, porc)


def test_capybara_gives_its_neighbours_armor():
    s2 = make_state(current="B", hands={"B": ["jaguar"]})
    put(s2, "3,3", "capybara", "A")
    sq = put(s2, "3,2", "squirrel", "A")
    assert not statics.can_be_removed(s2, sq)
    put(s2, "4,3", "lion", "B")
    rules.apply_action(s2, PlaceAction("jaguar", ("cr", "4,2")))   # beside the Squirrel: no target it may remove
    assert s2.top_unit("3,2") is sq and s2.pending is None


def test_the_legendary_jellyfish_poisons_its_adjacent_fish():
    s = make_state(current="B", hands={"B": ["lion"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "4,2", "lion", "B")
    put(s, "3,3", "fish_legend_jellyfish", "A")
    put(s, "3,2", "sardine", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))  # covers the poisoned Sardine
    end_turn(s)                                                 # A's turn starts: the coverer dies
    assert s.top_unit("3,2").card_id == "sardine" and removed(s, "lion")


# ============================================================================= Aristocrats

def test_the_legendary_cuckoo_removes_an_ally_and_plays_another_animal():
    s = make_state(hands={"A": ["aristocrats_legend_cuckoo", "lion"]})
    put(s, "1,1", "cockroach", "A")
    rules.apply_action(s, PlaceAction("aristocrats_legend_cuckoo", ("cr", "1,2")))
    choose(s, "1,1")
    assert s.pending and s.pending["mode"] == "place"         # it was yours: play another animal
    s2 = make_state(hands={"A": ["aristocrats_legend_cuckoo", "lion"]})
    put(s2, "2,2", "squirrel", "B")
    rules.apply_action(s2, PlaceAction("aristocrats_legend_cuckoo", ("cr", "1,2")))
    choose(s2, "2,2")
    assert s2.pending is None and removed(s2, "squirrel")


def test_the_legendary_opossum_removes_a_covered_ally_and_draws():
    s = make_state(current="B", hands={"B": ["lion"]}, decks={"A": ["lion"], "B": []})
    put(s, "4,2", "lion", "B")
    put(s, "3,3", "aristocrats_legend_opossum", "A")
    put(s, "3,2", "squirrel", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))
    assert [u.card_id for u in s.board["3,2"]] == ["lion"] and removed(s, "squirrel")
    assert hand_ids(s, "A") == ["lion"]


def test_the_legendary_sloth_makes_dusk_effects_happen_twice():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,1", "aristocrats_legend_sloth", "A")
    put(s, "1,2", "methuselah", "A")
    end_turn(s)
    assert s.food["A"] == 2 * CFG.methuselah_food


def test_praying_mantis_may_remove_an_ally_to_draw_two():
    s = make_state(hands={"A": ["praying_mantis"]}, decks={"A": ["lion"] * 3, "B": []})
    put(s, "1,1", "cockroach", "A")
    rules.apply_action(s, PlaceAction("praying_mantis", ("cr", "1,2")))
    assert s.pending["optional"]
    choose(s, "1,1")
    assert hand_ids(s, "A").count("lion") == CFG.mantis_draw + 1   # the Cockroach drew one too
    assert "cockroach" in hand_ids(s, "A")                     # and came back to hand


def test_tarantula_eats_an_adjacent_ally_at_dusk_and_grows():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    t = put(s, "1,2", "tarantula", "A")
    put(s, "1,1", "lion", "A")
    end_turn(s)
    assert s.top_unit("1,1") is None and effective_strength(s, t) == 5 + 7


def test_sea_turtle_lays_a_baby_turtle_and_a_city_spider_eats_it():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,2", "sea_turtle", "A")
    put(s, "1,1", "lion", "A"); put(s, "2,2", "lion", "A")    # the only empty neighbour: 1,3
    put(s, "2,3", "city_spider", "B")
    end_turn(s)
    assert s.top_unit("1,3") is None and removed(s, "baby_turtle")   # the turtle hatched beside the spider


def test_raccoon_returns_only_your_own_removed_animal():
    s = make_state(hands={"A": ["raccoon"]})
    s.pile_add("tiger", "B"); s.pile_add("lion", "A")
    rules.apply_action(s, PlaceAction("raccoon", ("cr", "1,2")))
    assert s.pending["options"] == ["lion"]
    choose(s, "lion")
    assert "lion" in hand_ids(s, "A") and s.remove_pile == ["tiger"]


def test_piranha_needs_an_ally_removed_this_turn():
    s = make_state(hands={"A": ["piranha", "piranha"]})
    put(s, "2,2", "lion", "B")
    apply_click(s, PlaceAction("piranha", ("cr", "1,2")))
    assert s.top_unit("2,2") is not None                       # no blood in the water
    put(s, "1,1", "cockroach", "A")
    effects.remove_top(s, "1,1", by_player="B")
    apply_click(s, PlaceAction("piranha", ("cr", "1,2")))       # on top of the first one, beside the Lion
    assert s.top_unit("2,2") is None


def test_hyena_gains_food_for_each_of_your_animals_removed_this_turn():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,2", "hyena", "A")
    for cr in ("1,1", "1,3"):
        put(s, cr, "lion", "A")
        effects.remove_top(s, cr, by_player="B")
    end_turn(s)
    assert s.food["A"] == 2 * CFG.hyena_food_per


def test_earthworm_leaves_two_worms_and_a_worm_draws_when_removed():
    s = make_state(decks={"A": ["lion"] * 3, "B": []})
    put(s, "1,2", "earthworm", "A")
    effects.remove_top(s, "1,2", by_player="B")
    assert [u.card_id for u in s.board["1,2"]] == ["worm", "worm"]
    effects.remove_top(s, "1,2", by_player="B")
    assert hand_ids(s, "A") == ["lion"]


def test_cockroach_comes_back_to_hand_and_draws():
    s = make_state(decks={"A": ["lion"], "B": []})
    put(s, "1,2", "cockroach", "A")
    effects.remove_top(s, "1,2", by_player="B")
    assert sorted(hand_ids(s, "A")) == ["cockroach", "lion"] and not removed(s, "cockroach")


# ================================================================================= Canines

def test_clarion_gives_a_free_roam_to_a_canine_only():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,1", "clarion", "A")
    put(s, "1,2", "dire_wolf", "A")                            # Wolf: Roam
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert s.actions_taken_this_turn == 0                      # the free roam paid
    s2 = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s2, "1,1", "clarion", "A")
    put(s2, "1,2", "orca", "A")                                # Roam, not a Canine
    put(s2, "2,2", "squirrel", "A")
    rules.apply_action(s2, RoamAction("1,2", ("cr", "2,2")))
    assert s2.actions_taken_this_turn == 1


def test_lobo_draws_when_an_ally_roams_onto_an_enemy():
    s = make_state(decks={"A": ["lion"] * 3, "B": []})
    put(s, "1,1", "lobo", "A")
    put(s, "1,2", "dire_wolf", "A")
    put(s, "2,2", "squirrel", "B")
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert hand_ids(s, "A") == ["lion"]


def test_the_legendary_wolf_buffs_its_new_neighbours_when_it_roams():
    s = make_state()
    put(s, "1,2", "canines_legend_wolf", "A")
    ally = put(s, "2,1", "squirrel", "A")                      # beside 1,1, where it goes
    old = put(s, "1,3", "squirrel", "A")                       # beside 1,2, where it was
    rules.apply_action(s, RoamAction("1,2", ("cr", "1,1")))
    assert ally.strength_counter == CFG.wolf_legend_grant and old.strength_counter == 0


def test_the_fox_draws_whenever_it_covers_an_enemy():
    s = make_state(hands={"A": ["fox"]}, decks={"A": ["lion"] * 3, "B": []})
    put(s, "1,1", "squirrel", "B")
    rules.apply_action(s, PlaceAction("fox", ("cr", "1,2")))
    assert hand_ids(s, "A") == []
    put(s, "2,2", "worker_ant", "B")
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))   # roams onto the 1
    assert hand_ids(s, "A") == ["lion"]


def test_jackal_removes_only_an_enemy_another_canine_flanks():
    s = make_state(hands={"A": ["gray_wolf"]})
    put(s, "1,1", "lion", "A")
    put(s, "2,2", "lion", "B")
    rules.apply_action(s, PlaceAction("gray_wolf", ("cr", "1,2")))
    assert s.pending is None                                   # nobody flanks the Lion
    s2 = make_state(hands={"A": ["gray_wolf"]})
    put(s2, "2,1", "dire_wolf", "A")
    put(s2, "1,1", "lion", "A")
    put(s2, "2,2", "lion", "B")
    apply_click(s2, PlaceAction("gray_wolf", ("cr", "1,2")))
    assert s2.top_unit("2,2") is None


def test_dhole_lets_your_animals_roam_onto_an_equal_enemy():
    s = make_state()
    put(s, "1,1", "red_wolf", "A")                             # Dhole
    put(s, "1,2", "dire_wolf", "A")                            # Wolf 6
    put(s, "2,2", "caracal", "B")                              # 6
    assert RoamAction("1,2", ("cr", "2,2")) in rules.legal_actions(s)


def test_raccoon_dog_grows_a_roaming_canine():
    s = make_state()
    put(s, "1,1", "raccoon_dog", "A")
    w = put(s, "1,2", "dire_wolf", "A")
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert w.strength_counter == CFG.raccoon_dog_grant


def test_stray_dog_buffs_an_ally_with_roam_and_it_roams():
    s = make_state(hands={"A": ["dog"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    w = put(s, "1,1", "dire_wolf", "A")
    rules.apply_action(s, PlaceAction("dog", ("cr", "1,2")))
    choose(s, "1,1")
    assert w.strength_counter == CFG.stray_dog_grant
    choose(s, "2,1")
    assert s.top_unit("2,1") is w and s.actions_taken_this_turn == 1


def test_badger_draws_an_animal_with_roam():
    s = make_state(hands={"A": ["badger"]}, decks={"A": ["lion", "orca", "squirrel"], "B": []})
    rules.apply_action(s, PlaceAction("badger", ("cr", "1,2")))
    assert hand_ids(s, "A") == ["orca"]


# ==================================================================================== Cats

def test_serval_sets_an_adjacent_enemys_strength_to_one():
    s = make_state(hands={"A": ["serval"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    big = put(s, "2,2", "elephant", "B")
    apply_click(s, PlaceAction("serval", ("cr", "1,2")))
    assert effective_strength(s, big) == CFG.serval_set


def test_lynx_draws_only_when_placed_on_an_enemy():
    s = make_state(hands={"A": ["lynx", "lynx"]}, decks={"A": ["lion"] * 2, "B": []})
    rules.apply_action(s, PlaceAction("lynx", ("cr", "1,2")))
    assert hand_ids(s, "A") == ["lynx"]
    put(s, "2,2", "squirrel", "B")
    rules.apply_action(s, PlaceAction("lynx", ("cr", "2,2")))
    assert hand_ids(s, "A") == ["lion"]


# ================================================================================ Den Rush

def test_greywhisker_gains_draws_plays_then_discards():
    s = make_state(hands={"A": ["greywhisker", "lion", "tiger"]}, decks={"A": ["squirrel"], "B": []})
    rules.apply_action(s, PlaceAction("greywhisker", ("cr", "1,2")))
    assert s.food["A"] == CFG.greywhisker_food and "squirrel" in hand_ids(s, "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "1,1")))      # play another animal
    assert s.pending["mode"] == "choice"                           # then discard a card of your choice
    choose(s, hand_inst(s, "A", "tiger").iid)
    assert hand_ids(s, "A") == ["squirrel"] and removed(s, "tiger")


def test_hare_draws_after_three_animals_this_turn():
    s = make_state(hands={"A": ["hare"]}, decks={"A": ["lion"], "B": []})
    s.units_placed_this_turn = 2
    rules.apply_action(s, PlaceAction("hare", ("cr", "1,2")))
    assert hand_ids(s, "A") == ["lion"]


# ============================================================================= Egg Control

def test_the_legendary_raven_takes_from_the_opponents_remove_pile():
    s = make_state(hands={"A": ["egg_control_legend_raven"]})
    s.pile_add("tiger", "B"); s.pile_add("lion", "A")
    rules.apply_action(s, PlaceAction("egg_control_legend_raven", ("cr", "1,2")))
    assert s.pending["options"] == ["tiger"]
    choose(s, "tiger")
    assert hand_inst(s, "A", "tiger").owner == "A" and s.remove_pile == ["lion"]


def test_mosquito_drains_two():
    s = make_state(hands={"A": ["mosquito"]})
    t = put(s, "2,2", "tiger", "B")
    apply_click(s, PlaceAction("mosquito", ("cr", "1,2")))
    assert effective_strength(s, t) == 7 - CFG.mosquito_drain


def test_black_swan_discards_on_every_draw():
    s = make_state(decks={"A": ["omen", "omen"], "B": []})
    for _ in range(2):
        s.add_to_hand("B", "lion")
    effects.draw_cards(s, "A", 2)
    assert s.hands["B"] == []


# ==================================================================================== Fish

def test_the_legendary_tuna_pays_per_region():
    s = make_state(hands={"A": ["fish_legend_tuna"]}, decks={"A": ["lion"] * 3, "B": []})
    for cr in ("1,1", "2,1", "2,2"):
        put(s, cr, "sardine", "A")
    rules.apply_action(s, PlaceAction("fish_legend_tuna", ("cr", "1,2")))   # closes R1
    assert s.food["A"] == CFG.tuna_legend_food and len(s.hands["A"]) == 1


def test_the_legendary_manta_ray_draws_two_at_dusk_with_two_regions():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    for cr in ("1,1", "2,1", "2,2", "1,3", "2,3"):
        put(s, cr, "sardine", "A")
    put(s, "1,2", "fish_legend_manta_ray", "A")                # R1 and R4
    end_turn(s)
    assert len(s.hands["A"]) == CFG.manta_legend_draw == 2


def test_the_legendary_piranha_lets_fish_cover_up_to_the_school_size():
    s = make_state(hands={"A": ["sardine"]})
    for cr in ("1,1", "1,3"):
        put(s, cr, "sardine", "A")
    put(s, "2,1", "fish_legend_piranha", "A")                  # 3 Fish on the board
    put(s, "1,2", "lion", "B")                                 # a 7: too big
    put(s, "2,2", "chameleon", "B")
    assert PlaceAction("sardine", ("cr", "1,2")) not in rules.legal_actions(s)
    s.board["1,2"][-1].strength_counter = -4                   # now a 3
    assert PlaceAction("sardine", ("cr", "1,2")) in rules.legal_actions(s)


def test_swordfish_removes_a_random_enemy_per_adjacent_allied_fish():
    s = make_state(hands={"A": ["swordfish"]})
    put(s, "1,1", "sardine", "A")
    put(s, "2,2", "lion", "B"); put(s, "1,3", "lion", "B")
    rules.apply_action(s, PlaceAction("swordfish", ("cr", "1,2")))
    assert s.remove_pile == ["lion"]                           # one Fish beside it: one enemy


def test_barracuda_removes_up_to_the_number_of_your_fish():
    s = make_state(hands={"A": ["barracuda"]})
    put(s, "1,1", "sardine", "A")
    put(s, "2,2", "baby_turtle", "B")
    put(s, "1,3", "squirrel", "B")                             # 3 > 2 Fish
    apply_click(s, PlaceAction("barracuda", ("cr", "1,2")))
    assert removed(s, "baby_turtle") and s.top_unit("1,3") is not None


def test_manta_ray_draws_when_the_opponent_covers_an_allied_fish():
    s = make_state(current="B", hands={"B": ["lion"]}, decks={"A": ["lion"], "B": []})
    put(s, "4,2", "lion", "B")
    put(s, "3,3", "manta_ray", "A")
    put(s, "3,2", "sardine", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))
    assert hand_ids(s, "A") == ["lion"]


def test_cod_draws_per_adjacent_allied_fish_and_remora_plays_a_fish():
    s = make_state(hands={"A": ["cod"]}, decks={"A": ["lion"] * 3, "B": []})
    put(s, "1,1", "sardine", "A"); put(s, "1,3", "tuna", "A")
    rules.apply_action(s, PlaceAction("cod", ("cr", "1,2")))
    assert len(s.hands["A"]) == 2
    s2 = make_state(hands={"A": ["remora", "lion", "sardine"]})
    rules.apply_action(s2, PlaceAction("remora", ("cr", "1,2")))
    assert {p["card_id"] for p in s2.pending["placements"]} == {"sardine"}


def test_sardines_fill_adjacent_empty_crossroads_from_hand_and_deck_without_roaring():
    s = make_state(hands={"A": ["sardine", "sardine"]}, decks={"A": ["sardine", "lion"], "B": []})
    rules.apply_action(s, PlaceAction("sardine", ("cr", "1,2")))   # neighbours 1,1 1,3 2,2: three spots
    assert sum(u.card_id == "sardine" for st in s.board.values() for u in st) == 3
    assert s.decks["A"] == ["lion"] and hand_ids(s, "A") == []


def test_mahi_mahi_mackerel_and_tuna_grow_the_school():
    s = make_state(hands={"A": ["mahi_mahi"]})
    sar = put(s, "1,1", "sardine", "A")
    tuna = put(s, "1,3", "tuna", "A")
    assert effective_strength(s, tuna) == 3 + 1                # one other Fish
    rules.apply_action(s, PlaceAction("mahi_mahi", ("cr", "1,2")))
    assert sar.strength_counter == CFG.mahi_mahi_grant
    put(s, "2,2", "mackerel", "A")
    assert effective_strength(s, sar) == 1 + CFG.mahi_mahi_grant + CFG.mackerel_anthem


def test_sunfish_places_a_baby_fish_where_you_choose():
    s = make_state(hands={"A": ["sunfish"]})
    rules.apply_action(s, PlaceAction("sunfish", ("cr", "1,2")))
    choose(s, "2,2")
    assert s.top_unit("2,2").card_id == "baby_fish" and s.top_unit("2,2").owner == "A"


# ============================================================================= Food Aggro

def test_the_repeat_legend_roars_its_adjacent_rodents_again():
    s = make_state(hands={"A": ["food_aggro_legend_repeat"]})
    put(s, "1,1", "squirrel", "A"); put(s, "2,2", "squirrel", "A")
    put(s, "1,3", "lion", "A")                                 # not a Rodent
    rules.apply_action(s, PlaceAction("food_aggro_legend_repeat", ("cr", "1,2")))
    assert s.food["A"] == 2 * CFG.squirrel_food


def test_two_repeat_legends_side_by_side_do_not_repeat_each_other_for_ever():
    s = make_state(hands={"A": ["food_aggro_legend_repeat"]})
    put(s, "1,1", "food_aggro_legend_repeat", "A")             # a mimic Octopus's copy, say
    put(s, "2,2", "squirrel", "A")
    rules.apply_action(s, PlaceAction("food_aggro_legend_repeat", ("cr", "1,2")))
    assert s.food["A"] == CFG.squirrel_food


def test_the_refill_legend_draws_up_to_the_opponents_hand():
    s = make_state(hands={"A": ["food_aggro_legend_refill"], "B": ["lion"] * 4}, decks={"A": ["lion"] * 9, "B": []})
    rules.apply_action(s, PlaceAction("food_aggro_legend_refill", ("cr", "1,2")))
    assert len(s.hands["A"]) == 4


def test_meerkat_draws_when_an_enemy_lands_beside_it():
    s = make_state(current="B", hands={"B": ["lion"]}, decks={"A": ["lion"], "B": []})
    put(s, "4,2", "lion", "B")
    put(s, "2,2", "meerkat", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))
    assert hand_ids(s, "A") == ["lion"]


def test_dormouse_and_mole_pay_on_an_empty_hand():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,2", "dormouse", "A")
    end_turn(s)
    assert s.food["A"] == CFG.dormouse_food
    s2 = make_state(hands={"A": ["mole"]}, decks={"A": ["lion"] * 3, "B": []})
    rules.apply_action(s2, PlaceAction("mole", ("cr", "1,2")))
    assert s2.food["A"] == CFG.mole_food and len(s2.hands["A"]) == CFG.mole_draw


# ================================================================================ Food OTK

def test_the_legendary_squirrel_stakes_your_food_and_triples_it_in_two_turns():
    s = make_state(hands={"A": ["food_otk_legend_squirrel"]}, food={"A": 20, "B": 0},
                   decks={"A": ["lion"] * 8, "B": ["lion"] * 8})
    rules.apply_action(s, PlaceAction("food_otk_legend_squirrel", ("cr", "1,2")))
    assert s.food["A"] == 0
    end_turn(s); end_turn(s); end_turn(s)
    assert s.food["A"] == 0
    end_turn(s)                                                 # the second of A's turns
    assert s.food["A"] == 20 * CFG.otk_squirrel_multiplier


def test_covering_the_legendary_squirrel_pauses_its_timer():
    s = make_state(hands={"A": ["food_otk_legend_squirrel"]}, food={"A": 20, "B": 0},
                   decks={"A": ["lion"] * 8, "B": ["lion"] * 8})
    rules.apply_action(s, PlaceAction("food_otk_legend_squirrel", ("cr", "1,2")))
    put(s, "1,2", "lion", "B")
    for _ in range(4):
        end_turn(s)
    assert s.food["A"] == 0


def test_the_mimic_octopus_becomes_a_copy_of_an_adjacent_animal_but_not_its_roar():
    s = make_state(hands={"A": ["food_otk_legend_octopus"]})
    por = put(s, "2,2", "porcupine", "B")
    por.strength_counter = 1
    rules.apply_action(s, PlaceAction("food_otk_legend_octopus", ("cr", "1,2")))
    choose(s, "2,2")
    me = s.top_unit("1,2")
    assert me.card_id == "porcupine" and effective_strength(s, me) == 8 and "Spikes" in statics.unit_keywords(s, me)
    s2 = make_state(hands={"A": ["food_otk_legend_octopus"]})
    put(s2, "2,2", "squirrel", "A")
    rules.apply_action(s2, PlaceAction("food_otk_legend_octopus", ("cr", "1,2")))
    choose(s2, "2,2")
    assert s2.food["A"] == 0                                   # copying the Squirrel doesn't gain its Roar's food


def test_golden_orb_weaver_catches_a_flyer_landing_beside_it():
    s = make_state(current="B", hands={"B": ["eagle"]})
    put(s, "2,2", "golden_orb_weaver", "A")
    rules.apply_action(s, PlaceAction("eagle", ("cr", "2,1")))
    assert removed(s, "eagle")


def test_tortoise_counts_armor_including_a_capybaras():
    s = make_state(hands={"A": ["tortoise"]})
    put(s, "1,1", "capybara", "A")
    rules.apply_action(s, PlaceAction("tortoise", ("cr", "1,2")))   # Armor printed, and beside the Capybara
    assert s.food["A"] == CFG.tortoise_per_armor


def test_the_legendary_honey_badger_has_every_keyword():
    s = make_state()
    hb = put(s, "1,2", "food_otk_legend_honey_badger", "A")
    assert statics.unit_keywords(s, hb) >= {"Armor", "Stealth", "Poison", "Spikes"}


# ================================================================================== Giants

def test_mocha_removes_every_enemy_adjacent_to_your_animals():
    s = make_state(hands={"A": ["mocha"]})
    put(s, "1,1", "lion", "A")
    put(s, "2,1", "lion", "B")                                 # beside the Lion
    put(s, "2,2", "lion", "B")                                 # beside Mocha
    put(s, "4,3", "lion", "B")                                 # beside nothing of A's
    rules.apply_action(s, PlaceAction("mocha", ("cr", "1,2")))
    assert s.top_unit("2,1") is None and s.top_unit("2,2") is None and s.top_unit("4,3") is not None


def test_dung_beetle_feeds_on_hungry_animals_and_anteater_eats_the_drawn_cards_strength():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,1", "dung_beetle", "A")
    put(s, "1,2", "elephant", "A"); put(s, "1,3", "rhinoceros", "A")
    end_turn(s)
    assert s.food["A"] == 2 * CFG.dung_beetle_per
    s2 = make_state(hands={"A": ["anteater"]}, decks={"A": ["tiger"], "B": []})
    rules.apply_action(s2, PlaceAction("anteater", ("cr", "1,2")))
    assert s2.food["A"] == 7 and hand_ids(s2, "A") == ["tiger"]


def test_whale_shark_draws_a_card_at_the_end_of_your_turn():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,2", "whale_shark", "A")
    end_turn(s)
    assert len(s.hands["A"]) == 1


# ================================================================================ Handlock

def test_silverback_trains_the_whole_hand_and_the_grizzly_counts_it():
    s = make_state(hands={"A": ["silverback", "lion", "grizzly_bear"]})
    assert placement_strength(s, hand_inst(s, "A", "grizzly_bear")) == 2 + 2   # two other cards in hand
    rules.apply_action(s, PlaceAction("silverback", ("cr", "1,2")))
    assert hand_inst(s, "A", "lion").strength_counter == CFG.silverback_grant


def test_the_legendary_butterfly_moves_one_stage_per_buff():
    s = make_state(hands={"A": ["handlock_legend_butterfly", "silverback", "silverback"]}, decks={"A": ["lion"] * 9, "B": ["lion"] * 9})
    bf = hand_inst(s, "A", "handlock_legend_butterfly")
    rules.apply_action(s, PlaceAction("silverback", ("cr", "1,1")))
    assert bf.card_id == "handlock_legend_butterfly_2" and placement_strength(s, bf) == 1 + CFG.silverback_grant
    rules.apply_action(s, PlaceAction("silverback", ("cr", "1,3")))
    assert bf.card_id == "handlock_legend_butterfly_3"         # one buff, one stage
    end_turn(s)                                                 # the opponent's turn passes: A's again
    rules.apply_action(s, PlaceAction("handlock_legend_butterfly_3", ("cr", "1,2")))   # Stealth. Roar: draw, then +1
    assert s.pending and s.pending["mode"] == "choice"


def test_the_caterpillar_turns_into_a_butterfly_and_draws_when_trained():
    s = make_state(hands={"A": ["caterpillar", "silverback"]}, decks={"A": ["lion"], "B": []})
    cat = hand_inst(s, "A", "caterpillar")
    rules.apply_action(s, PlaceAction("silverback", ("cr", "1,2")))
    assert cat.card_id == "butterfly" and "lion" in hand_ids(s, "A")


def test_the_legendary_eagle_brings_its_mate_and_they_share_every_buff():
    s = make_state(decks={"A": ["handlock_legend_eagle"], "B": []})
    effects.draw_cards(s, "A", 1)
    assert sorted(hand_ids(s, "A")) == ["handlock_legend_eagle", "handlock_legend_eagle_mate"]
    s.add_to_hand("A", "baboon")
    eagle, mate = hand_inst(s, "A", "handlock_legend_eagle"), hand_inst(s, "A", "handlock_legend_eagle_mate")
    effects._grant(s, [eagle.iid], 3)
    effects.resolve(s)
    assert eagle.strength_counter == mate.strength_counter == 3


def test_orangutan_duplicates_a_primate_and_tarsier_scouts_one_and_trains_it():
    s = make_state(hands={"A": ["orangutan", "gorilla", "lion"]})
    rules.apply_action(s, PlaceAction("orangutan", ("cr", "1,2")))
    assert s.pending["options"] == [hand_inst(s, "A", "gorilla").iid]
    choose(s, hand_inst(s, "A", "gorilla").iid)
    assert hand_ids(s, "A").count("gorilla") == 2
    s2 = make_state(hands={"A": ["tarsier"]}, decks={"A": ["lion", "gorilla", "lion"], "B": []})
    apply_click(s2, PlaceAction("tarsier", ("cr", "1,2")))
    assert hand_inst(s2, "A", "gorilla").strength_counter == CFG.tarsier_grant


def test_baboon_trains_two_different_cards_and_the_legend_two_random_ones_at_dusk():
    s = make_state(hands={"A": ["baboon", "lion", "tiger", "squirrel"]})
    rules.apply_action(s, PlaceAction("baboon", ("cr", "1,2")))
    choose(s, hand_inst(s, "A", "lion").iid)
    assert hand_inst(s, "A", "lion").iid not in s.pending["options"]
    choose(s, hand_inst(s, "A", "tiger").iid)
    assert [u.strength_counter for u in s.hands["A"]] == [1, 1, 0]
    s2 = make_state(hands={"A": ["lion", "tiger", "squirrel"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s2, "1,2", "handlock_legend_baboon", "A")
    end_turn(s2)
    assert sum(u.strength_counter for u in s2.hands["A"]) == CFG.baboon_legend_count


def test_stork_adds_two_different_younglings():
    s = make_state(hands={"A": ["stork"]})
    rules.apply_action(s, PlaceAction("stork", ("cr", "1,2")))
    young = hand_ids(s, "A")
    assert len(young) == 2 and len(set(young)) == 2 and all(c in effects.YOUNGLINGS for c in young)


def test_gorilla_and_macaque_gate_on_their_thresholds():
    s = make_state(hands={"A": ["gorilla"]}, decks={"A": ["lion"], "B": []})
    hand_inst(s, "A", "gorilla").strength_counter = 2
    rules.apply_action(s, PlaceAction("gorilla", ("cr", "1,2")))
    assert hand_ids(s, "A") == ["lion"]
    s2 = make_state(hands={"A": ["macaque"] + ["lion"] * 5})
    put(s2, "2,2", "tiger", "B")
    apply_click(s2, PlaceAction("macaque", ("cr", "1,2")))
    assert s2.top_unit("2,2") is None


# ================================================================================== Hoofed

def test_the_legendary_wildebeest_and_boar_move_region_income():
    s = make_state()
    for cr in ("1,1", "2,1", "2,2"):
        put(s, cr, "squirrel", "A")
    put(s, "1,2", "hoofed_legend_wildebeest", "A")             # R1 (10)
    assert rules.region_income(s, "A") == 10 + CFG.migration_bonus
    put(s, "4,3", "hoofed_legend_boar", "B")
    assert rules.region_income(s, "A") == 10 + CFG.migration_bonus - CFG.boar_penalty
    r1 = s.game_map.regions["R1"]
    assert rules.region_yield(s, "A", r1) == 10 + CFG.migration_bonus - CFG.boar_penalty   # what its stone shows
    assert rules.region_yield(s, "B", r1) == 10                 # the Wildebeest is A's, the Boar works on A


def test_the_legendary_giraffe_reveals_the_opponents_hand():
    s = make_state(hands={"B": ["lion"]})
    assert s.view_for("A").opponent_hand is None
    put(s, "1,2", "hoofed_legend_giraffe", "A")
    assert s.view_for("A").opponent_hand == ("lion",) and s.view_for("B").opponent_hand is None


def test_the_legendary_zebra_draws_per_different_hoofed_animal_you_control_anywhere():
    s = make_state(hands={"A": ["hoofed_legend_zebra"]}, decks={"A": ["lion"] * 5, "B": []})
    put(s, "1,2", "gazelle", "A"); put(s, "4,3", "gazelle", "A")   # two copies count once; far away counts
    put(s, "3,1", "deer", "A")
    put(s, "3,2", "boar", "B")                                  # an enemy's Hoofed animal doesn't count
    put(s, "1,1", "lion", "A")                                  # nor an ally that isn't Hoofed
    rules.apply_action(s, PlaceAction("hoofed_legend_zebra", ("cr", "2,2")))
    assert len(s.hands["A"]) == 3                               # Gazelle, Deer and the Zebra itself


def test_grazing_okapi_draws_wildebeest_feeds_and_boar_grows():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,1", "okapi", "A"); put(s, "2,1", "wildebeest", "A"); put(s, "2,2", "squirrel", "A")
    boar = put(s, "1,2", "boar", "A")                           # closes R1: all four graze
    assert statics.grazing(s, boar) and effective_strength(s, boar) == 5 + CFG.boar_grazing_bonus
    end_turn(s)
    assert len(s.hands["A"]) == 1 and s.food["A"] == CFG.wildebeest_food + 10   # Wildebeest, then R1's income


def test_giraffe_and_moose_are_bigger_on_the_opponents_turn():
    s = make_state()
    g = put(s, "1,2", "giraffe", "A"); put(s, "1,1", "moose", "A")
    assert effective_strength(s, g) == 4
    s.current = "B"
    assert effective_strength(s, g) == 4 + CFG.giraffe_bonus + CFG.moose_anthem


def test_cape_buffalo_removes_the_enemy_covering_an_allied_hoofed():
    s = make_state(hands={"A": ["cape_buffalo"]})
    put(s, "2,2", "gazelle", "A"); put(s, "2,2", "lion", "B")
    put(s, "1,1", "lion", "B")                                  # covering nothing of A's
    apply_click(s, PlaceAction("cape_buffalo", ("cr", "1,2")))
    assert [u.card_id for u in s.board["2,2"]] == ["gazelle"] and s.top_unit("1,1").owner == "B"


# ==================================================================================== Pool

def test_great_white_shark_has_reach_three_after_a_removal():
    s = make_state(hands={"A": ["great_white_shark"]}, decks={"A": ["lion"] * 3, "B": []})
    put(s, "3,2", "lion", "B").strength_counter = -1           # a 6, three crossroads out: the shark (7) eats it
    assert PlaceAction("great_white_shark", ("cr", "3,2")) not in rules.legal_actions(s)
    put(s, "4,3", "squirrel", "B")
    effects.remove_top(s, "4,3", by_player="A")
    assert PlaceAction("great_white_shark", ("cr", "3,2")) in rules.legal_actions(s)


def test_cuckoo_eggs_clog_the_opponents_deck_and_feed_you():
    s = make_state(hands={"A": ["cuckoo"]}, decks={"A": ["lion"] * 3, "B": []})
    rules.apply_action(s, PlaceAction("cuckoo", ("cr", "1,2")))
    assert s.decks["B"] == ["cuckoo_egg"] * CFG.cuckoo_eggs
    effects.draw_cards(s, "B", 1)
    assert hand_ids(s, "B") == ["cuckoo_egg"] and hand_ids(s, "A") == ["lion"]


def test_opossum_returns_an_adjacent_ally_to_hand():
    s = make_state(hands={"A": ["opossum"]})
    put(s, "1,1", "squirrel", "A")
    apply_click(s, PlaceAction("opossum", ("cr", "1,2")))
    assert "squirrel" in hand_ids(s, "A") and not removed(s, "squirrel")


def test_every_launch_card_can_be_played_by_the_bots_without_crashing():
    """A smoke: a few random games over every pairing of the twelve decks (the full fuzz runs in the slow tier)."""
    import random
    from animal_kingdom.decks import load_premade_deck
    from animal_kingdom.engine.cards import DECK_SLUGS
    from animal_kingdom.engine.state import new_game
    decks = sorted(DECK_SLUGS)
    for i, a in enumerate(decks):
        b = decks[(i + 5) % len(decks)]
        s, rng = new_game(load_premade_deck(a), load_premade_deck(b), 77 + i), random.Random(i)
        for _ in range(600):
            if rules.is_terminal(s) is not None:
                break
            rules.apply_action(s, rng.choice(rules.legal_actions(s)))


def test_the_macaw_makes_the_next_roar_this_turn_happen_twice():
    s = make_state(hands={"A": ["macaw", "squirrel", "squirrel"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    rules.apply_action(s, PlaceAction("macaw", ("cr", "1,2")))
    rules.apply_action(s, PlaceAction("squirrel", ("cr", "1,1")))
    assert s.food["A"] == 2 * s.config.squirrel_food
    assert "A" not in s.roar_twice                              # spent by that Roar


# ================================================================================ 2026-10-09: the fit and rarity passes

def test_the_fox_and_the_african_wild_dog_ids_follow_their_animals():
    cards = load_cards()
    fox, dog = cards["fox"], cards["african_wild_dog"]
    assert (fox.name, fox.rarity, "Roam" in fox.keywords) == ("Fox", "rare", True)
    assert (dog.name, dog.rarity, dog.text) == ("African Wild Dog", "common", "Dusk: give your adjacent animals +1 strength.")


def test_the_african_wild_dog_gives_its_adjacent_allies_one_at_dusk():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "2,2", "african_wild_dog", "A")
    ally, far, enemy = put(s, "1,2", "lion", "A"), put(s, "4,2", "lion", "A"), put(s, "3,2", "lion", "B")
    end_turn(s)
    assert (ally.strength_counter, far.strength_counter, enemy.strength_counter) == (CFG.wild_dog_grant, 0, 0)


def test_the_termite_king_draws_two_with_a_colony_queen():
    s = make_state(hands={"A": ["termite_king"]}, decks={"A": ["lion"] * 3, "B": []})
    put(s, "1,1", "termite_queen", "A")
    rules.apply_action(s, PlaceAction("termite_king", ("cr", "1,2")))
    assert len(s.hands["A"]) == CFG.termite_king_draw == 2


def test_the_legendary_leopard_is_eight():
    assert load_cards()["canines_legend_leopard"].base_strength == 8


def test_the_lemming_is_a_plain_one_now():
    s = make_state(hands={"A": ["lemming", "lemming"]}, decks={"A": ["lemming"], "B": []})
    rules.apply_action(s, PlaceAction("lemming", ("cr", "1,2")))
    assert sum(len(st) for st in s.board.values()) == 1 and hand_ids(s, "A") == ["lemming"]


def test_the_legendary_cuckoo_is_a_bird():
    assert "Bird" in load_cards()["aristocrats_legend_cuckoo"].tags


# --- Vesper: "Flight. When an enemy covers an allied Queen, place Vesper on it from your hand or deck." -------------

def _queen_covered_by(coverer, *, b_hand=(), b_deck=(), extra=None):
    """A's `coverer` covers B's Queen Bee on 2,2 (A holds 1,2, so 2,2 is in reach)."""
    s = make_state(hands={"A": [coverer], "B": list(b_hand)}, decks={"A": ["lion"] * 3, "B": list(b_deck)})
    put(s, "1,2", "lion", "A")
    put(s, "2,2", "queen_bee", "B")
    if extra:
        extra(s)
    rules.apply_action(s, PlaceAction(coverer, ("cr", "2,2")))
    return s


def test_vesper_is_placed_from_hand_on_the_enemy_that_covers_an_allied_queen():
    s = _queen_covered_by("lion", b_hand=["vesper", "lion"])
    assert [u.card_id for u in s.board["2,2"]] == ["queen_bee", "lion", "vesper"]
    assert hand_ids(s, "B") == ["lion"] and s.board["2,2"][-1].owner == "B"
    place = next(e for e in s.events if e["e"] == "place" and e["card"] == "vesper")
    assert place["from_hand"] and place["reveal"] and place["cause"] == "vesper"
    assert s.current == "A" and s.actions_taken_this_turn == 1   # B spent nothing; A's turn goes on


def test_vesper_is_placed_from_the_deck_too():
    s = _queen_covered_by("lion", b_deck=["lion", "vesper", "lion"])
    assert s.board["2,2"][-1].card_id == "vesper" and s.decks["B"] == ["lion", "lion"]
    place = next(e for e in s.events if e["e"] == "place" and e["card"] == "vesper")
    assert not place["from_hand"]


def test_vesper_lands_on_any_strength_and_skips_connection():
    s = _queen_covered_by("mock_vanilla_10", b_hand=["vesper"])   # 5 on a 10, far from B's den
    assert [u.card_id for u in s.board["2,2"]] == ["queen_bee", "mock_vanilla_10", "vesper"]


def test_vesper_on_the_board_or_in_the_remove_pile_does_nothing():
    s = _queen_covered_by("lion", extra=lambda s: put(s, "4,1", "vesper", "B"))
    assert [u.card_id for u in s.board["2,2"]] == ["queen_bee", "lion"]
    s = _queen_covered_by("lion", extra=lambda s: s.pile_add("vesper", "B"))
    assert [u.card_id for u in s.board["2,2"]] == ["queen_bee", "lion"]


def test_vesper_ignores_a_non_queen_ally_and_a_friendly_cover():
    s = make_state(hands={"A": ["lion"], "B": ["vesper"]}, decks={"A": [], "B": []})
    put(s, "1,2", "lion", "A")
    put(s, "2,2", "worker_bee", "B")                            # Colony, but no Queen
    rules.apply_action(s, PlaceAction("lion", ("cr", "2,2")))
    assert s.board["2,2"][-1].card_id == "lion" and hand_ids(s, "B") == ["vesper"]
    s = make_state(current="B", hands={"B": ["lion", "vesper"]}, decks={"A": [], "B": []})
    put(s, "4,2", "lion", "B"); put(s, "3,2", "queen_bee", "B")
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))      # B covers its own Queen
    assert s.board["3,2"][-1].card_id == "lion" and hand_ids(s, "B") == ["vesper"]


def test_vesper_answers_a_roaming_cover_too():
    s = make_state(decks={"A": [], "B": []}, hands={"B": ["vesper"]})
    put(s, "1,2", "fox", "A"); put(s, "2,2", "queen_bee", "B")
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert [u.card_id for u in s.board["2,2"]] == ["queen_bee", "fox", "vesper"]


def test_vesper_resolves_after_the_coverers_roar_and_is_placed_not_played():
    """The Bat's Roar draws first; Vesper comes after it, without an action and without Queen Honoria's food (placing
    isn't playing)."""
    s = _queen_covered_by("bat", b_hand=["vesper"], extra=lambda s: put(s, "4,1", "queen_honoria", "B"))
    order = [e["e"] for e in s.events if e["e"] in ("draw", "place")]
    assert order == ["place", "draw", "place"] and s.board["2,2"][-1].card_id == "vesper"
    assert s.food["B"] == 0


def test_vesper_fires_identically_from_any_determinized_world():
    """Honesty: the bots' sampled worlds re-deal B's hand and deck, but Vesper is in one or the other in every world,
    so a search that covers B's Queen sees the same answer whatever it may not know."""
    import random
    from animal_kingdom.bots.determinize import determinize
    s = make_state(hands={"A": ["lion"], "B": ["lion", "lion"]}, decks={"A": [], "B": ["vesper", "lion", "lion"]})
    put(s, "1,2", "lion", "A"); put(s, "2,2", "queen_bee", "B")
    for seed in range(6):
        w = determinize(s, "A", random.Random(seed))
        rules.apply_action(w, PlaceAction("lion", ("cr", "2,2")), validate=False)
        assert w.board["2,2"][-1].card_id == "vesper"


# --- Methuselah: "Armor. Each player gains at most 20 food per turn. Dusk: gain 5 food." --------------------------

def test_methuselah_caps_each_players_food_per_turn_from_any_source():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "4,3", "methuselah", "B")
    effects.gain_food(s, "A", 15); effects.gain_food(s, "A", 15)
    effects.gain_food(s, "B", 30)                               # the opponent's gains this turn are capped too
    assert (s.food["A"], s.food["B"]) == (CFG.methuselah_food_cap, CFG.methuselah_food_cap) == (20, 20)
    end_turn(s)                                                  # a new turn: a fresh 20
    effects.gain_food(s, "A", 30)
    assert s.food["A"] == 40


def test_methuselahs_own_dusk_counts_toward_the_cap_before_region_income():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    for cr in ("1,1", "2,1", "2,2", "1,3", "2,3"):
        put(s, cr, "lion", "A")
    put(s, "1,2", "methuselah", "A")                            # R1 and R4: 20 food of income
    assert rules.region_income(s, "A") == 20
    end_turn(s)
    assert s.food["A"] == 20                                    # Dusk's 5, then 15 of the 20


def test_a_buried_methuselah_caps_nothing():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "2,2", "methuselah", "A"); put(s, "2,2", "lion", "B")
    effects.gain_food(s, "A", 30)
    assert s.food["A"] == 30


def test_vesper_landing_is_a_cover_spikes_remove_it_and_an_apex_still_eats_the_queen():
    s = _queen_covered_by("hedgehog", b_hand=["vesper"])           # Spikes: the first enemy to cover it is removed
    assert [u.card_id for u in s.board["2,2"]] == ["queen_bee", "hedgehog"] and removed(s, "vesper")
    s = _queen_covered_by("polar_bear", b_hand=["vesper"])
    assert [u.card_id for u in s.board["2,2"]] == ["polar_bear", "vesper"] and removed(s, "queen_bee")
