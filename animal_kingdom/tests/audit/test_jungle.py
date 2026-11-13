"""Card audit, Jungle (2026-11-05): each collectible Jungle card's printed text against the engine.

Every assertion is read off the card's text and the keyword meanings in docs/rules/keywords.md. Map A (the test
fixture): a 4x3 grid, A's den fronts column 1, B's column 4; "2,2" neighbours "1,2", "3,2", "2,1", "2,3".
Regions: R1 = 1,1 2,1 1,2 2,2 (10 food), R4 = 1,2 2,2 1,3 2,3 (10), R2/R5 the middle ones (20).
"""

from __future__ import annotations

import pytest

from animal_kingdom.engine import effects, rules, statics
from animal_kingdom.engine.actions import SKIP, ChoiceAction, DrawAction, PassAction, PlaceAction, RoamAction
from animal_kingdom.engine.cards import load_cards
from animal_kingdom.engine.state import EngineError
from animal_kingdom.engine.strength import effective_strength, placement_strength

from .._helpers import apply_click, hand_ids, make_state, put

CARDS = load_cards()
DECK = {"A": ["lion"] * 8, "B": ["lion"] * 8}


def decks():
    return {p: list(v) for p, v in DECK.items()}


def end_turn(s):
    s.idle_turns = 0
    rules.apply_action(s, PassAction())


def choose(s, option):
    assert s.pending is not None and option in s.pending["options"], (option, s.pending)
    rules.apply_action(s, ChoiceAction(option))


def hand_inst(s, player, card_id):
    return next(u for u in s.hands[player] if u.card_id == card_id)


def places(s, card_id, cr):
    return PlaceAction(card_id, ("cr", cr)) in rules.legal_actions(s)


def strength(card_id):
    return CARDS[card_id].base_strength


def test_jungle_cards_are_the_audited_set():
    ids = sorted(c.id for c in CARDS.values() if c.status == "collectible" and str(c.habitat).lower().endswith("jungle"))
    assert len(ids) == 37


# ------------------------------------------------------------------ army_ant_legend: Dusk: gain 2 food per animal

def test_army_ant_legend_dusk_gains_two_food_for_each_animal_you_control():
    s = make_state(decks=decks())
    put(s, "1,1", "army_ant_legend", "A")
    put(s, "1,3", "lion", "A")
    put(s, "3,3", "mouse", "A")
    put(s, "4,1", "lion", "B")                                   # an enemy: not counted
    end_turn(s)
    assert s.food["A"] == 2 * 3


def test_army_ant_legend_does_not_count_a_buried_ally_and_not_at_the_opponents_dusk():
    s = make_state(decks=decks())
    put(s, "1,1", "army_ant_legend", "A")
    put(s, "3,3", "mouse", "A")
    put(s, "3,3", "lion", "B")                                   # the Mouse is buried: not controlled
    end_turn(s)
    assert s.food["A"] == 2 * 1
    end_turn(s)                                                  # B's Dusk: Solenia's isn't B's
    assert s.food["A"] == 2 and s.food["B"] == 0


# -------------------------------------------------- soldier_ant: Roar: if 4+ Colony, remove an adjacent enemy

def test_soldier_ant_with_four_colony_including_itself_removes_an_adjacent_enemy():
    s = make_state(hands={"A": ["soldier_ant"]})
    for cr in ("1,1", "1,3", "3,3"):
        put(s, cr, "worker_ant", "A")                            # 3 other Colony + the Soldier Ant = 4
    put(s, "2,2", "lion", "B")
    apply_click(s, PlaceAction("soldier_ant", ("cr", "1,2")))
    assert s.top_unit("2,2") is None and "lion" in s.remove_pile


def test_soldier_ant_with_three_colony_removes_nothing():
    s = make_state(hands={"A": ["soldier_ant"]})
    for cr in ("1,1", "1,3"):
        put(s, cr, "worker_ant", "A")
    put(s, "2,2", "lion", "B")
    apply_click(s, PlaceAction("soldier_ant", ("cr", "1,2")))
    assert s.pending is None and s.top_unit("2,2").card_id == "lion"


def test_soldier_ant_cannot_choose_a_stealth_enemy():
    s = make_state(hands={"A": ["soldier_ant"]})
    for cr in ("1,1", "1,3", "3,3"):
        put(s, cr, "worker_ant", "A")
    put(s, "2,2", "stick_insect", "B")
    apply_click(s, PlaceAction("soldier_ant", ("cr", "1,2")))
    assert s.pending is None and s.top_unit("2,2").card_id == "stick_insect"


# ------------------------------------- piranha: your Fish can cover enemies of strength up to the number of Fish

def test_piranha_lets_a_fish_cover_an_enemy_as_strong_as_your_fish_count():
    s = make_state(hands={"A": ["remora"]})                      # a 2
    put(s, "1,1", "piranha", "A")
    put(s, "1,3", "cod", "A")
    put(s, "3,3", "mahi_mahi", "A")                              # 3 Fish on the board
    put(s, "1,2", "lion", "B")
    s.top_unit("1,2").strength_counter = 3 - strength("lion")    # an enemy 3, stronger than the Remora
    assert places(s, "remora", "1,2")


def test_piranha_fish_cannot_cover_above_the_fish_count_and_non_fish_get_nothing():
    s = make_state(hands={"A": ["remora", "alley_cat"]})
    put(s, "1,1", "piranha", "A")
    put(s, "1,3", "cod", "A")                                    # 2 Fish
    put(s, "1,2", "lion", "B")
    s.top_unit("1,2").strength_counter = 3 - strength("lion")    # a 3: above 2 and above the Remora
    assert not places(s, "remora", "1,2")
    s.top_unit("1,2").strength_counter = 2 - strength("lion")    # a 2: the count reaches it
    assert places(s, "remora", "1,2")
    assert not places(s, "alley_cat", "1,2")                     # a 2 Cat, not a Fish: needs more than 2


# --------------------------------------------- python: whenever an enemy is removed, gain 1 strength (wherever)

def test_python_on_the_board_grows_with_an_enemy_removal_not_an_ally_or_a_cover():
    s = make_state(hands={"B": ["lion"]}, current="A")
    py = put(s, "1,1", "python", "A")
    put(s, "2,1", "mouse", "B"); effects.remove_top(s, "2,1", by_player="A")
    assert effective_strength(s, py) == 1
    put(s, "2,2", "mouse", "A"); effects.remove_top(s, "2,2", by_player="B")
    assert effective_strength(s, py) == 1                        # an ally removed: not an enemy
    put(s, "2,3", "mouse", "B"); put(s, "2,3", "lion", "A")      # covering isn't removing
    assert effective_strength(s, py) == 1


def test_python_in_hand_grows_with_an_enemy_removal():
    s = make_state(hands={"A": ["python"]})
    put(s, "2,1", "mouse", "B"); effects.remove_top(s, "2,1", by_player="A")
    assert placement_strength(s, hand_inst(s, "A", "python")) == 1


def test_python_in_the_deck_grows_with_an_enemy_removal():
    # "wherever this is": the deck is one of the places a card can be.
    s = make_state(decks={"A": ["python"], "B": []})
    put(s, "2,1", "mouse", "B"); effects.remove_top(s, "2,1", by_player="A")
    rules.apply_action(s, DrawAction())
    assert placement_strength(s, hand_inst(s, "A", "python")) == 1


# ------------------------------------- dhole: Roam; whenever it covers an enemy with no other enemy next to it, draw 2

def test_dhole_placed_on_an_isolated_enemy_draws_two():
    s = make_state(hands={"A": ["dhole"]}, decks=decks())
    put(s, "1,1", "lion", "A")
    put(s, "2,1", "mouse", "B")
    rules.apply_action(s, PlaceAction("dhole", ("cr", "2,1")))
    assert hand_ids(s, "A") == ["lion", "lion"]


def test_dhole_draws_nothing_when_another_enemy_is_next_to_its_prey_or_it_covers_nothing():
    s = make_state(hands={"A": ["dhole", "dhole"]}, decks=decks())
    put(s, "1,1", "lion", "A")
    put(s, "2,1", "mouse", "B")
    put(s, "3,1", "mouse", "B")                                  # another enemy beside the prey
    rules.apply_action(s, PlaceAction("dhole", ("cr", "2,1")))
    assert hand_ids(s, "A") == ["dhole"]
    rules.apply_action(s, PlaceAction("dhole", ("cr", "1,3")))   # onto an empty crossroad: no cover
    assert hand_ids(s, "A") == []


def test_dhole_roaming_onto_an_isolated_enemy_draws_two():
    s = make_state(decks=decks())
    put(s, "1,1", "dhole", "A")
    put(s, "2,1", "mouse", "B")
    rules.apply_action(s, RoamAction("1,1", ("cr", "2,1")))
    assert s.top_unit("2,1").card_id == "dhole" and hand_ids(s, "A") == ["lion", "lion"]


# ------------------------------------------- bush_dog: Roam; whenever it roams, place a Pup on the crossroad it left

def test_bush_dog_leaves_a_pup_where_it_roamed_from():
    s = make_state(decks=decks())
    put(s, "1,2", "bush_dog", "A")
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    pup = s.top_unit("1,2")
    assert pup.card_id == "pup" and pup.owner == "A" and s.top_unit("2,2").card_id == "bush_dog"


def test_bush_dog_placed_is_not_a_roam_and_leaves_no_pup():
    s = make_state(hands={"A": ["bush_dog"]}, decks=decks())
    rules.apply_action(s, PlaceAction("bush_dog", ("cr", "1,2")))
    assert not any(u.card_id == "pup" for st in s.board.values() for u in st)


# --------------------------------------------------- chameleon: Roar: become a copy of an animal in your hand

def test_chameleon_becomes_a_copy_of_a_card_in_hand_and_the_card_stays():
    s = make_state(hands={"A": ["chameleon", "lion"]})
    rules.apply_action(s, PlaceAction("chameleon", ("cr", "1,2")))
    if s.pending:
        choose(s, hand_inst(s, "A", "lion").iid)
    me = s.top_unit("1,2")
    assert me.card_id == "lion" and effective_strength(s, me) == strength("lion") and hand_ids(s, "A") == ["lion"]


def test_chameleon_with_an_empty_hand_stays_a_chameleon():
    s = make_state(hands={"A": ["chameleon"]})
    rules.apply_action(s, PlaceAction("chameleon", ("cr", "1,2")))
    assert s.pending is None and s.top_unit("1,2").card_id == "chameleon"


# ------------------------------------------------- jaguar: Roar: remove an adjacent enemy of strength 4 or less

def test_jaguar_removes_an_adjacent_enemy_of_4_not_5_and_never_an_ally():
    for enemy, gone in (("mouse", True), ("lynx", False)):       # a 4 and a 5
        s = make_state(hands={"A": ["jaguar"]})
        put(s, "2,2", enemy, "B")
        put(s, "1,1", "gazelle", "A")                            # an adjacent ally of 2
        apply_click(s, PlaceAction("jaguar", ("cr", "1,2")))
        assert (s.top_unit("2,2") is None) == gone
        assert s.top_unit("1,1").card_id == "gazelle"


def test_jaguar_not_adjacent_removes_nothing():
    s = make_state(hands={"A": ["jaguar"]})
    put(s, "3,2", "mouse", "B")                                  # two steps away
    apply_click(s, PlaceAction("jaguar", ("cr", "1,2")))
    assert s.top_unit("3,2").card_id == "mouse"


# ----------------------------------------------------------------- black_panther: Apex Predator. Stealth.

def test_black_panther_cannot_be_placed_on_an_empty_crossroad_and_eats_what_it_lands_on():
    s = make_state(hands={"A": ["black_panther"]})
    assert not places(s, "black_panther", "1,2")
    put(s, "1,2", "lion", "B")
    s.top_unit("1,2").strength_counter = -1                      # a 6
    rules.apply_action(s, PlaceAction("black_panther", ("cr", "1,2")))
    assert [u.card_id for u in s.board["1,2"]] == ["black_panther"] and "lion" in s.remove_pile


def test_black_panther_cannot_be_chosen_by_an_enemy_removal():
    s = make_state(current="B", hands={"B": ["tiger_legend"]})
    put(s, "4,2", "mouse", "B")                                  # prey for B's Apex
    put(s, "3,2", "black_panther", "A")                          # a 7 next to it: in range, but Stealth
    apply_click(s, PlaceAction("tiger_legend", ("cr", "4,2")))
    assert s.top_unit("3,2").card_id == "black_panther"


# ------------------------------------------------------------------------------------ tiger: Apex Predator.

def test_tiger_must_land_on_an_animal_and_eats_an_enemy_or_an_ally():
    s = make_state(hands={"A": ["tiger", "tiger"]})
    assert not places(s, "tiger", "1,2")                         # no prey anywhere
    put(s, "1,2", "lion", "B")                                   # a 7: not strictly less
    assert not places(s, "tiger", "1,2")
    put(s, "1,1", "lion", "A")                                   # its own: no strength needed
    rules.apply_action(s, PlaceAction("tiger", ("cr", "1,1")))
    assert [u.card_id for u in s.board["1,1"]] == ["tiger"] and s.remove_pile == ["lion"]


def test_tiger_covers_an_armored_enemy_without_eating_it():
    s = make_state(hands={"A": ["tiger"]})
    put(s, "1,2", "tortoise", "B")                               # a 6 with Armor
    rules.apply_action(s, PlaceAction("tiger", ("cr", "1,2")))
    assert [u.card_id for u in s.board["1,2"]] == ["tortoise", "tiger"] and s.remove_pile == []


def test_tiger_cannot_land_on_a_den():
    s = make_state(hands={"A": ["tiger", "mouse"]})
    for cr in ("1,1", "2,1", "3,1", "4,1"):
        put(s, cr, "mouse", "A")                                 # a chain to B's den front
    den = [a.target for a in rules.legal_actions(s) if isinstance(a, PlaceAction) and a.target[0] != "cr"]
    assert ("hq", "B") in den                                    # the Mouse may take it
    assert PlaceAction("tiger", ("hq", "B")) not in rules.legal_actions(s)


# ------------------------------------------- piranha_legend: Roar: remove each enemy next to 2 or more of your Fish

def test_piranha_legend_removes_each_enemy_next_to_two_fish_itself_included():
    s = make_state(hands={"A": ["piranha_legend"]})
    put(s, "2,1", "cod", "A")
    put(s, "2,2", "lion", "B")                                   # next to the Cod and the Piranha
    put(s, "3,1", "lion", "B")                                   # next to the Cod only
    put(s, "1,1", "mouse", "A")                                  # an ally next to both: not an enemy
    rules.apply_action(s, PlaceAction("piranha_legend", ("cr", "1,2")))
    assert s.top_unit("2,2") is None and s.top_unit("3,1").card_id == "lion" and s.top_unit("1,1").card_id == "mouse"


def test_piranha_legend_hits_a_stealth_enemy_since_nobody_chooses():
    s = make_state(hands={"A": ["piranha_legend"]})
    put(s, "2,1", "cod", "A")
    put(s, "2,2", "stick_insect", "B")
    rules.apply_action(s, PlaceAction("piranha_legend", ("cr", "1,2")))
    assert s.top_unit("2,2") is None


# --------------------------------------------- capybara_legend: Roar: repeat the Roar of each adjacent Rodent

def test_capybara_legend_repeats_each_adjacent_allied_rodents_roar():
    s = make_state(hands={"A": ["capybara_legend"]})
    put(s, "1,1", "squirrel", "A")                               # adjacent: Roar gain 10 food
    put(s, "2,2", "squirrel", "A")                               # adjacent too
    put(s, "3,3", "squirrel", "A")                               # not adjacent
    put(s, "1,3", "squirrel", "B")                               # adjacent, but not yours
    apply_click(s, PlaceAction("capybara_legend", ("cr", "1,2")))
    assert s.food["A"] == 2 * s.config.squirrel_food and s.food["B"] == 0


def test_capybara_legend_with_no_adjacent_rodent_does_nothing():
    s = make_state(hands={"A": ["capybara_legend"]})
    put(s, "1,1", "lion", "A")
    apply_click(s, PlaceAction("capybara_legend", ("cr", "1,2")))
    assert s.food["A"] == 0 and s.pending is None


# ------------------------- chameleon_legend: Roar: choose an adjacent animal; become a copy, add another to your hand

def test_iris_copies_an_adjacent_enemy_and_adds_a_copy_to_hand():
    s = make_state(hands={"A": ["chameleon_legend"]})
    put(s, "2,2", "lion", "B")
    apply_click(s, PlaceAction("chameleon_legend", ("cr", "1,2")))
    me = s.top_unit("1,2")
    assert me.card_id == "lion" and me.owner == "A" and hand_ids(s, "A") == ["lion"]
    assert s.top_unit("2,2").card_id == "lion" and s.top_unit("2,2").owner == "B"


def test_iris_with_no_adjacent_animal_stays_herself_and_adds_nothing():
    s = make_state(hands={"A": ["chameleon_legend"]})
    put(s, "3,3", "lion", "B")
    apply_click(s, PlaceAction("chameleon_legend", ("cr", "1,2")))
    assert s.top_unit("1,2").card_id == "chameleon_legend" and hand_ids(s, "A") == []


def test_iris_cannot_choose_a_stealth_enemy():
    s = make_state(hands={"A": ["chameleon_legend"]})
    put(s, "2,2", "stick_insect", "B")
    apply_click(s, PlaceAction("chameleon_legend", ("cr", "1,2")))
    assert s.top_unit("1,2").card_id == "chameleon_legend" and hand_ids(s, "A") == []


# ----------------- capybara: if your starting deck has no animal of strength 4 or more, this has 8 strength

def test_capybara_is_an_8_with_a_small_starting_deck_and_a_2_otherwise():
    small = make_state(hands={"A": ["capybara"]})
    small.starting_decks = {"A": ("capybara", "chameleon", "gazelle", "snake_egg"), "B": ("lion",)}
    assert placement_strength(small, small.hands["A"][0]) == 8
    big = make_state(hands={"A": ["capybara"]})
    big.starting_decks = {"A": ("capybara", "chameleon", "mouse"), "B": ()}     # the Mouse is a 4: exactly 4
    assert placement_strength(big, big.hands["A"][0]) == 2


def test_capybara_counts_its_own_starting_deck_not_the_opponents():
    s = make_state(hands={"A": ["capybara"]})
    s.starting_decks = {"A": ("capybara", "gazelle"), "B": ("lion", "tiger")}
    put(s, "1,2", "lion", "A")                                   # a big animal on the board, not in the starting deck
    assert placement_strength(s, s.hands["A"][0]) == 8


# ---------------------------- golden_orb_weaver: when an enemy with Flight or Roam is placed next to this, remove it

def test_golden_orb_weaver_removes_a_flying_enemy_placed_next_to_it():
    s = make_state(current="B", hands={"B": ["pigeon"]})
    put(s, "2,2", "golden_orb_weaver", "A")
    rules.apply_action(s, PlaceAction("pigeon", ("cr", "2,1")))
    assert s.top_unit("2,1") is None and "pigeon" in s.remove_pile


def test_golden_orb_weaver_spares_a_plain_enemy_a_far_flyer_and_an_allied_flyer():
    s = make_state(current="B", hands={"B": ["mouse", "pigeon"]})
    put(s, "3,2", "golden_orb_weaver", "A")
    rules.apply_action(s, PlaceAction("mouse", ("cr", "4,2")))  # next to it, but no Flight or Roam
    assert s.top_unit("4,2").card_id == "mouse"
    rules.apply_action(s, PlaceAction("pigeon", ("cr", "1,1")))  # Flight, but not next to it
    assert s.top_unit("1,1").card_id == "pigeon"
    s2 = make_state(hands={"A": ["pigeon"]})
    put(s2, "2,2", "golden_orb_weaver", "A")
    rules.apply_action(s2, PlaceAction("pigeon", ("cr", "2,1")))   # your own flyer
    assert s2.top_unit("2,1").card_id == "pigeon"


def test_golden_orb_weaver_removes_a_roam_enemy_placed_next_to_it():
    s = make_state(current="B", hands={"B": ["wolf"]})
    put(s, "3,2", "golden_orb_weaver", "A")
    rules.apply_action(s, PlaceAction("wolf", ("cr", "4,2")))
    assert s.top_unit("4,2") is None and "wolf" in s.remove_pile


def test_golden_orb_weaver_removes_an_enemy_roaming_next_to_it():
    s = make_state(current="B")
    put(s, "3,1", "golden_orb_weaver", "A")
    put(s, "4,2", "wolf", "B")
    rules.apply_action(s, RoamAction("4,2", ("cr", "4,1")))      # arrives next to it by roaming
    assert "wolf" in s.remove_pile and s.top_unit("4,1") is None


# ----------------------------------------------------------- armadillo: Armor. Your adjacent animals have Armor.

def test_armadillo_cannot_be_removed():
    s = make_state(current="B", hands={"B": ["tiger_legend"]})
    put(s, "4,2", "mouse", "B")                                  # the Tiger's prey
    put(s, "3,2", "armadillo", "A")                              # a 5 beside where the Tiger lands
    apply_click(s, PlaceAction("tiger_legend", ("cr", "4,2")))
    assert s.top_unit("3,2").card_id == "armadillo"


def test_armadillo_gives_its_adjacent_ally_armor():
    s = make_state(current="B", hands={"B": ["tiger_legend"]})
    put(s, "4,2", "mouse", "B")
    put(s, "3,1", "armadillo", "A")                              # not next to the Tiger
    put(s, "4,1", "gazelle", "A")                                # next to the Tiger and to the Armadillo
    apply_click(s, PlaceAction("tiger_legend", ("cr", "4,2")))
    assert s.top_unit("4,1").card_id == "gazelle" and s.top_unit("3,1").card_id == "armadillo"


def test_armadillo_gives_no_armor_to_an_ally_not_adjacent_or_to_an_enemy():
    s = make_state(current="B", hands={"B": ["jaguar"]})
    put(s, "1,1", "armadillo", "A")
    put(s, "3,2", "gazelle", "A")                                # far from the Armadillo
    apply_click(s, PlaceAction("jaguar", ("cr", "4,2")))
    assert s.top_unit("3,2") is None
    s2 = make_state()
    put(s2, "1,1", "armadillo", "A")
    enemy = put(s2, "2,1", "gazelle", "B")
    assert "Armor" not in statics.unit_keywords(s2, enemy)


def test_armadillo_can_still_be_covered():
    s = make_state(current="B", hands={"B": ["lion"]})
    put(s, "4,2", "mouse", "B")
    put(s, "3,2", "armadillo", "A")
    assert places(s, "lion", "3,2")


# ---------------------------------------------- dart_frog: Reach. Poison. Fall: remove all animals next to this.

def test_dart_frog_fall_removes_every_animal_next_to_it_both_sides():
    s = make_state(current="B", hands={"B": ["jaguar"]})
    put(s, "3,2", "dart_frog", "A")
    put(s, "2,2", "mouse", "A")
    put(s, "3,1", "mouse", "B")
    put(s, "3,3", "mouse", "A")
    put(s, "2,1", "lion", "B")                                   # not next to it
    apply_click(s, PlaceAction("jaguar", ("cr", "4,2")))         # the Jaguar removes the Frog (1), then stands beside it
    assert all(s.top_unit(cr) is None for cr in ("3,2", "2,2", "3,1", "3,3", "4,2"))
    assert s.top_unit("2,1").card_id == "lion"


def test_dart_frog_covered_is_not_removed_and_falls_nothing():
    s = make_state(current="B", hands={"B": ["lion"]}, decks=decks())
    put(s, "4,2", "mouse", "B")
    put(s, "3,2", "dart_frog", "A")
    put(s, "3,1", "mouse", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))
    assert s.top_unit("3,1").card_id == "mouse"                  # a cover is not a removal


def test_dart_frog_poison_removes_its_coverer_at_the_start_of_its_owners_next_turn():
    s = make_state(current="B", hands={"B": ["lion"]}, decks=decks())
    put(s, "4,2", "mouse", "B")
    put(s, "3,2", "dart_frog", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))
    assert s.top_unit("3,2").card_id == "lion"                   # the coverer has the rest of its turn
    end_turn(s)                                                  # A's turn starts: the Lion dies, the Frog resurfaces
    assert s.current == "A" and s.top_unit("3,2").card_id == "dart_frog" and "lion" in s.remove_pile


def test_dart_frog_reach_lands_two_crossroads_from_a_connected_ally_not_three():
    s = make_state(hands={"A": ["dart_frog"]})
    put(s, "1,2", "lion", "A")
    assert places(s, "dart_frog", "3,2")
    assert not places(s, "dart_frog", "4,3")


# ------------------------------- anaconda_legend: Apex Predator. Dusk: shuffle Eon into your deck at -1, draw a card

def test_eon_at_dusk_goes_into_the_deck_one_weaker_and_draws_a_card():
    s = make_state(decks={"A": [], "B": ["lion"] * 4})
    put(s, "1,2", "anaconda_legend", "A")
    end_turn(s)                                                  # the deck was empty: the card it draws is Eon itself
    assert s.top_unit("1,2") is None and hand_ids(s, "A") == ["anaconda_legend"] and s.decks["A"] == []
    assert placement_strength(s, s.hands["A"][0]) == strength("anaconda_legend") - 1


def test_eon_shuffled_into_a_deck_draws_one_card():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 4})
    put(s, "1,2", "anaconda_legend", "A")
    end_turn(s)
    assert s.top_unit("1,2") is None and len(s.hands["A"]) == 1
    assert sorted(hand_ids(s, "A") + list(s.decks["A"])) == ["anaconda_legend"] + ["lion"] * 3


def test_eon_does_nothing_at_the_opponents_dusk():
    s = make_state(current="B", decks=decks())
    put(s, "1,2", "anaconda_legend", "A")
    end_turn(s)                                                  # B's Dusk
    assert s.top_unit("1,2").card_id == "anaconda_legend" and hand_ids(s, "A") == []


# ------------------------------------- snake_egg: Roar: draw a Snake. In 2 turns, remove this and draw 2 Snakes.

@pytest.mark.xfail(strict=True, reason='two readings of "In 2 turns": A) two turns of play, the opponent\'s and then yours, so it happens at the start of your next turn (the count keywords.md gives a Wild animal); B) two of your own turns, at the start of your turn after next (the engine, config sloth_delay/egg_hatch_delay = 2 owner-turns)')
def test_snake_egg_draws_a_snake_now_and_two_more_in_two_turns_then_is_removed():
    s = make_state(hands={"A": ["snake_egg"]},
                   decks={"A": ["python", "viper", "anaconda", "lion", "lion", "lion"], "B": ["lion"] * 6})
    rules.apply_action(s, PlaceAction("snake_egg", ("cr", "1,2")))
    assert len(s.hands["A"]) == 1 and "Snake" in CARDS[hand_ids(s, "A")[0]].tags
    end_turn(s)                                                  # A's turn ends (1)
    assert s.top_unit("1,2").card_id == "snake_egg"
    end_turn(s)                                                  # B's turn ends (2): A's turn starts
    assert s.top_unit("1,2") is None and "snake_egg" in s.remove_pile
    assert sorted(hand_ids(s, "A")) == ["anaconda", "python", "viper"]


def test_snake_egg_hatches_removing_itself_and_drawing_two_snakes():
    s = make_state(hands={"A": ["snake_egg"]},
                   decks={"A": ["python", "viper", "anaconda", "lion", "lion", "lion"], "B": ["lion"] * 6})
    rules.apply_action(s, PlaceAction("snake_egg", ("cr", "1,2")))
    for _ in range(4):
        if s.top_unit("1,2") is None:
            break
        end_turn(s)
    assert s.top_unit("1,2") is None and "snake_egg" in s.remove_pile
    assert sorted(hand_ids(s, "A")) == ["anaconda", "python", "viper"]


def test_snake_egg_with_no_snake_in_the_deck_draws_nothing():
    s = make_state(hands={"A": ["snake_egg"]}, decks={"A": ["lion"] * 3, "B": []})
    rules.apply_action(s, PlaceAction("snake_egg", ("cr", "1,2")))
    assert hand_ids(s, "A") == []


# --------------------------------------------- gorilla_legend: Roar: give all animals in your hand +1 strength

def test_gorilla_legend_gives_every_card_in_your_hand_plus_one_for_good():
    s = make_state(hands={"A": ["orangutan_legend", "lion", "mouse"], "B": ["lion"]}, decks=decks())
    rules.apply_action(s, PlaceAction("orangutan_legend", ("cr", "1,2")))
    assert [u.strength_counter for u in s.hands["A"]] == [1, 1]
    assert s.hands["B"][0].strength_counter == 0
    rules.apply_action(s, DrawAction())                          # drawn after: not buffed
    assert [u.strength_counter for u in s.hands["A"]][2:] == [0, 0]


# --------------------------------------------------------------- hummingbird: Flight. Roar: draw 2 cards.

def test_hummingbird_flies_anywhere_and_draws_two():
    s = make_state(hands={"A": ["hummingbird"]}, decks=decks())
    rules.apply_action(s, PlaceAction("hummingbird", ("cr", "3,3")))   # not connected: Flight
    assert hand_ids(s, "A") == ["lion", "lion"]


def test_hummingbird_with_one_card_left_draws_it_and_does_not_break():
    s = make_state(hands={"A": ["hummingbird"]}, decks={"A": ["lion"], "B": []})
    rules.apply_action(s, PlaceAction("hummingbird", ("cr", "1,2")))
    assert hand_ids(s, "A") == ["lion"]


# ------------------------------------------------------ orangutan: Roar: duplicate a Primate in your hand

def test_orangutan_duplicates_a_primate_with_its_counter():
    s = make_state(hands={"A": ["orangutan", "chimpanzee", "lion"]})
    hand_inst(s, "A", "chimpanzee").strength_counter = 2
    apply_click(s, PlaceAction("orangutan", ("cr", "1,2")))
    chimps = [u for u in s.hands["A"] if u.card_id == "chimpanzee"]
    assert len(chimps) == 2 and all(u.strength_counter == 2 for u in chimps) and hand_ids(s, "A").count("lion") == 1


def test_orangutan_with_no_primate_in_hand_does_nothing():
    s = make_state(hands={"A": ["orangutan", "lion"]})
    apply_click(s, PlaceAction("orangutan", ("cr", "1,2")))
    assert s.pending is None and hand_ids(s, "A") == ["lion"]


# ----------------------------- tarsier: Roar: draw a Primate, then give a Primate in your hand +2 strength

def test_tarsier_draws_a_primate_then_gives_a_primate_in_hand_two():
    s = make_state(hands={"A": ["tarsier"]}, decks={"A": ["lion", "gorilla", "lion"], "B": []})
    apply_click(s, PlaceAction("tarsier", ("cr", "1,2")))
    assert hand_ids(s, "A") == ["gorilla"] and hand_inst(s, "A", "gorilla").strength_counter == 2


def test_tarsier_with_no_primate_in_the_deck_still_trains_one_in_hand():
    s = make_state(hands={"A": ["tarsier", "chimpanzee"]}, decks={"A": ["lion"], "B": []})
    apply_click(s, PlaceAction("tarsier", ("cr", "1,2")))
    assert hand_ids(s, "A") == ["chimpanzee"] and hand_inst(s, "A", "chimpanzee").strength_counter == 2


def test_tarsier_with_no_primate_anywhere_does_nothing():
    s = make_state(hands={"A": ["tarsier", "lion"]}, decks={"A": ["lion"], "B": []})
    apply_click(s, PlaceAction("tarsier", ("cr", "1,2")))
    assert s.pending is None and hand_ids(s, "A") == ["lion"] and hand_inst(s, "A", "lion").strength_counter == 0


# ------------------------------------------- chimpanzee: Roar: remove an adjacent enemy of equal or lower strength

def test_chimpanzee_removes_an_adjacent_enemy_of_equal_strength_not_stronger():
    for enemy, gone in (("mouse", True), ("lynx", False)):       # a 4 (equal) and a 5
        s = make_state(hands={"A": ["chimpanzee"]})
        put(s, "2,2", enemy, "B")
        apply_click(s, PlaceAction("chimpanzee", ("cr", "1,2")))
        assert (s.top_unit("2,2") is None) == gone


# ------------------------------------------------------- gorilla: Roar: if this has 8 or more strength, draw a card

def test_gorilla_draws_only_at_8_or_more():
    for counter, drawn in ((2, 1), (1, 0)):
        s = make_state(hands={"A": ["gorilla"]}, decks=decks())
        hand_inst(s, "A", "gorilla").strength_counter = counter
        rules.apply_action(s, PlaceAction("gorilla", ("cr", "1,2")))
        assert len(s.hands["A"]) == drawn


# -------------------------------------------------------- peacock: has +1 strength for each card in your hand

def test_peacock_in_hand_counts_itself_among_the_cards():
    s = make_state(hands={"A": ["peacock", "lion", "lion"]})
    assert placement_strength(s, hand_inst(s, "A", "peacock")) == 1 + 3


def test_peacock_on_the_board_has_one_more_for_each_card_in_hand_live():
    s = make_state(hands={"A": ["lion", "lion", "lion"], "B": ["lion"] * 5})
    pea = put(s, "1,2", "peacock", "A")
    assert effective_strength(s, pea) == 1 + 3
    s.hands["A"].pop()
    assert effective_strength(s, pea) == 1 + 2                   # an anthem: it follows the hand
    s.hands["A"].clear()
    assert effective_strength(s, pea) == 1                       # the opponent's hand counts for nothing


# --------------------------------------------------------------------- sloth: Roar: in 2 turns, gain 30 food

@pytest.mark.xfail(strict=True, reason='two readings of "In 2 turns": A) two turns of play, the opponent\'s and then yours, so it happens at the start of your next turn (the count keywords.md gives a Wild animal); B) two of your own turns, at the start of your turn after next (the engine, config sloth_delay/egg_hatch_delay = 2 owner-turns)')
def test_sloth_gains_30_food_in_two_turns_not_before():
    s = make_state(hands={"A": ["sloth"]}, decks=decks())
    rules.apply_action(s, PlaceAction("sloth", ("cr", "1,2")))
    assert s.food["A"] == 0
    end_turn(s)
    assert s.food["A"] == 0
    end_turn(s)                                                  # A's next turn starts
    assert s.food["A"] == 30


def test_sloth_gains_30_food_once():
    s = make_state(hands={"A": ["sloth"]}, decks=decks())
    rules.apply_action(s, PlaceAction("sloth", ("cr", "1,2")))
    for _ in range(8):
        end_turn(s)
    assert s.food["A"] == 30


# ----------------------------------------------------- okapi: Dawn and Dusk: if this is grazing, draw a card

def test_okapi_grazing_draws_at_dusk_and_at_dawn():
    s = make_state(decks=decks())
    put(s, "1,1", "okapi", "A")
    for cr in ("2,1", "1,2", "2,2"):
        put(s, cr, "mouse", "A")                                 # R1 is yours: the Okapi grazes
    end_turn(s)
    assert len(s.hands["A"]) == 1
    end_turn(s)                                                  # A's Dawn
    assert len(s.hands["A"]) == 2


def test_okapi_not_grazing_draws_nothing():
    s = make_state(decks=decks())
    put(s, "1,1", "okapi", "A")
    for cr in ("2,1", "1,2"):
        put(s, cr, "mouse", "A")
    put(s, "2,2", "mouse", "B")                                  # R1 is not yours
    end_turn(s); end_turn(s)
    assert len(s.hands["A"]) == 0


# ------------------------------------------------- macaw: Flight. Roar: repeat the last Roar your opponent played

def test_macaw_repeats_the_opponents_last_played_roar_for_you():
    s = make_state(current="B", hands={"B": ["squirrel"], "A": ["macaw"]}, decks=decks())
    rules.apply_action(s, PlaceAction("squirrel", ("cr", "4,2")))
    end_turn(s)
    rules.apply_action(s, PlaceAction("macaw", ("cr", "3,3")))   # Flight: unconnected
    assert s.food["A"] == s.config.squirrel_food


def test_macaw_does_not_repeat_your_own_roar_or_anything_before_the_opponent_roars():
    s = make_state(hands={"A": ["squirrel", "macaw"]}, decks=decks())
    rules.apply_action(s, PlaceAction("squirrel", ("cr", "1,2")))
    food = s.food["A"]
    rules.apply_action(s, PlaceAction("macaw", ("cr", "1,1")))
    assert s.food["A"] == food


# ------------------------------------------ anaconda: Apex Predator. Whenever this removes an animal, gain its strength

def test_anaconda_eats_and_gains_its_preys_strength_for_good():
    s = make_state(hands={"A": ["anaconda"]})
    put(s, "1,2", "mouse", "B")                                  # a 4
    rules.apply_action(s, PlaceAction("anaconda", ("cr", "1,2")))
    a = s.top_unit("1,2")
    assert a.card_id == "anaconda" and effective_strength(s, a) == 5 + 4 and a.strength_counter == 4


def test_anaconda_cannot_be_placed_on_an_empty_crossroad():
    s = make_state(hands={"A": ["anaconda"]})
    assert not places(s, "anaconda", "1,2")


# -------------------------------------------------------------- sloth_legend: your Dusk effects happen twice

def test_sloth_legend_doubles_your_dusk_effects_only():
    s = make_state(decks=decks())
    put(s, "1,1", "sloth_legend", "A")
    put(s, "1,3", "army_ant_legend", "A")                        # Dusk: 2 food per animal (2 animals)
    put(s, "4,3", "army_ant_legend", "B")
    end_turn(s)
    assert s.food["A"] == 2 * (2 * 2)
    end_turn(s)                                                  # B's Dusk: not doubled
    assert s.food["B"] == 2 * 1


# -------------------------------- tarantula: Dusk: remove the weakest animal next to this and gain its strength

def test_tarantula_eats_the_weakest_neighbour_at_dusk_and_grows():
    s = make_state(decks=decks())
    t = put(s, "1,2", "tarantula", "A")
    put(s, "1,1", "lion", "A")
    put(s, "2,2", "gazelle", "B")                                # 2: the weakest
    end_turn(s)
    assert s.top_unit("2,2") is None and s.top_unit("1,1").card_id == "lion"
    assert effective_strength(s, t) == 5 + 2


def test_tarantula_eats_an_ally_if_it_is_the_weakest_and_nothing_with_no_neighbour():
    s = make_state(decks=decks())
    t = put(s, "1,2", "tarantula", "A")
    put(s, "1,1", "gazelle", "A")
    put(s, "2,2", "lion", "B")
    end_turn(s)
    assert s.top_unit("1,1") is None and effective_strength(s, t) == 7
    s2 = make_state(decks=decks())
    t2 = put(s2, "1,2", "tarantula", "A")
    end_turn(s2)
    assert effective_strength(s2, t2) == 5


# ----------------------------------------------- electric_eel: Roar: your opponent takes only 1 action next turn

def test_electric_eel_leaves_the_opponent_one_action_next_turn_only():
    s = make_state(hands={"A": ["electric_eel"]}, decks={"A": ["mouse"] * 12, "B": ["mouse"] * 12})
    rules.apply_action(s, PlaceAction("electric_eel", ("cr", "1,2")))
    rules.apply_action(s, DrawAction())
    assert s.current == "B"
    rules.apply_action(s, DrawAction())
    assert s.current == "A"                                      # B's turn ended after one action
    rules.apply_action(s, DrawAction()); rules.apply_action(s, DrawAction())
    assert s.current == "B"
    rules.apply_action(s, DrawAction())
    assert s.current == "B"                                      # the turn after has two again


# ------------------------------- tiger_legend: Apex Predator. Roar: remove an adjacent enemy of strength 7 or less

def test_tiger_legend_eats_then_removes_an_adjacent_enemy_of_7_not_8():
    for neighbour, gone in (("lion", True), ("rhinoceros_legend", False)):
        s = make_state(hands={"A": ["tiger_legend"]})
        put(s, "1,1", "lion", "A")
        put(s, "2,1", "mouse", "B")
        put(s, "2,2", neighbour, "B")
        apply_click(s, PlaceAction("tiger_legend", ("cr", "2,1")))
        assert s.top_unit("2,1").card_id == "tiger_legend" and "mouse" in s.remove_pile
        assert (s.top_unit("2,2") is None) == gone


def test_tiger_legend_cannot_be_placed_on_an_empty_crossroad():
    s = make_state(hands={"A": ["tiger_legend"]})
    assert not places(s, "tiger_legend", "1,2")


# ------------------------------------------------- ocelot: Roar: if you control another Cat, play another Cat

def test_ocelot_with_another_cat_plays_a_cat_from_hand_for_free():
    s = make_state(hands={"A": ["ocelot", "lion", "mouse"]})
    put(s, "1,3", "caracal", "A")
    rules.apply_action(s, PlaceAction("ocelot", ("cr", "1,2")))
    offered = {a.card_id for a in rules.legal_actions(s) if isinstance(a, PlaceAction)}
    assert offered == {"lion"}                                   # a Cat only
    rules.apply_action(s, PlaceAction("lion", ("cr", "1,1")))
    assert s.top_unit("1,1").card_id == "lion" and s.current == "A" and rules.turn_actions(s) - s.actions_taken_this_turn == 1


def test_ocelot_without_another_cat_plays_nothing():
    s = make_state(hands={"A": ["ocelot", "lion"]})
    put(s, "1,3", "lion", "B")                                   # an enemy Cat doesn't count
    rules.apply_action(s, PlaceAction("ocelot", ("cr", "1,2")))
    assert s.pending is None and hand_ids(s, "A") == ["lion"]


# --------------------------------------------------------------------------------- stick_insect: Stealth.

def test_stick_insect_cannot_be_chosen_by_an_enemy_but_its_owner_may_choose_it():
    s = make_state(current="B", hands={"B": ["tiger_legend"]})
    put(s, "4,2", "mouse", "B")
    put(s, "3,2", "stick_insect", "A")                           # a 6 beside the Tiger
    apply_click(s, PlaceAction("tiger_legend", ("cr", "4,2")))
    assert s.top_unit("3,2").card_id == "stick_insect"
    s2 = make_state(hands={"A": ["chameleon_legend"]})
    put(s2, "2,2", "stick_insect", "A")
    apply_click(s2, PlaceAction("chameleon_legend", ("cr", "1,2")))
    assert s2.top_unit("1,2").card_id == "stick_insect"           # Iris may copy her own


def test_stick_insect_can_be_covered():
    s = make_state(current="B", hands={"B": ["lion"]})
    put(s, "4,2", "mouse", "B")
    put(s, "3,2", "stick_insect", "A")
    assert places(s, "lion", "3,2")


# ------------------------------------------------------- hercules_beetle: can cover animals of any strength

def test_hercules_beetle_covers_an_enemy_of_any_strength():
    s = make_state(hands={"A": ["hercules_beetle"]})
    put(s, "1,2", "anaconda_legend", "B")                        # a 10
    assert places(s, "hercules_beetle", "1,2")
    rules.apply_action(s, PlaceAction("hercules_beetle", ("cr", "1,2")))
    assert s.top_unit("1,2").card_id == "hercules_beetle"


def test_hercules_beetle_is_itself_covered_by_anything_stronger_than_0():
    s = make_state(current="B", hands={"B": ["gazelle"]})
    put(s, "4,2", "mouse", "B")
    put(s, "3,2", "hercules_beetle", "A")
    assert places(s, "gazelle", "3,2")


def test_macaw_repeats_the_last_roar_even_when_a_roarless_animal_came_after():
    s = make_state(current="B", hands={"B": ["squirrel", "lion"], "A": ["macaw"]}, decks=decks())
    rules.apply_action(s, PlaceAction("squirrel", ("cr", "4,2")))
    rules.apply_action(s, PlaceAction("lion", ("cr", "4,1")))      # no Roar: the Squirrel's stays the last
    rules.apply_action(s, PlaceAction("macaw", ("cr", "3,3")))
    assert s.food["A"] == s.config.squirrel_food


def test_capybara_on_the_board_is_an_8_with_a_small_starting_deck():
    s = make_state()
    s.starting_decks = {"A": ("capybara", "gazelle"), "B": ()}
    cap = put(s, "1,2", "capybara", "A")
    assert effective_strength(s, cap) == 8
