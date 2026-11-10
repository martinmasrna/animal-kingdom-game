"""Card audit, City habitat (2026-11-05): each collectible City card's printed text against the engine.

Every assertion is read off the card text and keywords.md / rulings.md, not off the effect code. Map A (the test
fixture): a 4x3 grid, A's den fronts column 1 ("1,1" "1,2" "1,3"), B's column 4; "2,2" neighbours "1,2", "3,2",
"2,1", "2,3".
"""

from __future__ import annotations

import pytest

from animal_kingdom.engine import effects, rules
from animal_kingdom.engine.actions import ChoiceAction, PassAction, PlaceAction
from animal_kingdom.engine.cards import load_cards
from animal_kingdom.engine.strength import effective_strength

from .._helpers import apply_click, hand_ids, make_state, place_targets, put

CARDS = load_cards()
FILLER = ["lion"] * 6


def end_turn(s):
    s.idle_turns = 0
    rules.apply_action(s, PassAction())


def choose(s, option):
    assert s.pending is not None and option in s.pending["options"], (option, s.pending)
    rules.apply_action(s, ChoiceAction(option))


def options(s):
    return set(s.pending["options"]) if s.pending else set()


# ============================================================================== Alley Cat

def test_alley_cat_adds_two_kittens_to_hand_without_touching_the_deck():
    s = make_state(hands={"A": ["alley_cat"]}, decks={"A": ["lion", "tiger"], "B": []})
    rules.apply_action(s, PlaceAction("alley_cat", ("cr", "1,2")))
    assert sorted(hand_ids(s, "A")) == ["kitten", "kitten"]
    assert s.decks["A"] == ["lion", "tiger"]                    # added, not drawn


def test_alley_cat_at_the_hand_limit_burns_the_kitten_past_ten():
    s = make_state(hands={"A": ["alley_cat"] + ["lion"] * 9})  # 9 left once it is played: one Kitten fits
    rules.apply_action(s, PlaceAction("alley_cat", ("cr", "1,2")))
    assert len(s.hands["A"]) == 10 and hand_ids(s, "A").count("kitten") == 1 and s.remove_pile == ["kitten"]


def test_alley_cat_with_an_empty_deck_still_adds_its_kittens():
    s = make_state(hands={"A": ["alley_cat"]})
    rules.apply_action(s, PlaceAction("alley_cat", ("cr", "1,2")))
    assert hand_ids(s, "A") == ["kitten", "kitten"]


# ==================================================================================== Bat

def test_bat_flies_and_draws_a_card():
    s = make_state(hands={"A": ["bat"]}, decks={"A": ["tiger"], "B": []})
    assert "3,2" in place_targets(s)                            # Flight: no connection needed
    rules.apply_action(s, PlaceAction("bat", ("cr", "3,2")))
    assert hand_ids(s, "A") == ["tiger"] and s.decks["A"] == []


def test_bat_with_an_empty_deck_just_lands():
    s = make_state(hands={"A": ["bat"]})
    rules.apply_action(s, PlaceAction("bat", ("cr", "3,2")))
    assert s.top_unit("3,2").card_id == "bat" and hand_ids(s, "A") == []


def test_bat_flight_cannot_capture_a_disconnected_den():
    s = make_state(hands={"A": ["bat"]})
    put(s, "4,2", "lion", "A")                                  # stranded on B's den front, no chain home
    assert not any(isinstance(a, PlaceAction) and a.target[0] == "hq" for a in rules.legal_actions(s))


def test_bat_cannot_cover_an_enemy_of_equal_strength():
    s = make_state(hands={"A": ["bat"]})
    put(s, "3,2", "beaver", "B")                                # 5 > 3
    put(s, "3,3", "rat", "B")                                   # 3 == 3
    put(s, "3,1", "cockroach", "B")                             # 1 < 3
    t = place_targets(s)
    assert "3,2" not in t and "3,3" not in t and "3,1" in t


# ====================================================================== [BAT] (legendary)

def test_bat_legend_draws_at_its_owners_dawn_only():
    s = make_state(decks={"A": ["tiger", "lion"], "B": FILLER[:]})
    put(s, "3,2", "bat_legend", "A")
    end_turn(s)                                                 # A's turn ends: B's Dawn, not A's
    assert hand_ids(s, "A") == []
    end_turn(s)                                                 # A's Dawn
    assert hand_ids(s, "A") == ["lion"]


def test_bat_legend_buried_draws_nothing():
    s = make_state(decks={"A": ["tiger", "lion"], "B": FILLER[:]})
    put(s, "3,2", "bat_legend", "A")
    put(s, "3,2", "lion", "B")                                  # covered
    end_turn(s); end_turn(s)
    assert hand_ids(s, "A") == []


def test_bat_legend_flies():
    s = make_state(hands={"A": ["bat_legend"]})
    assert "3,3" in place_targets(s)


# ============================================================================= City Spider

def test_city_spider_removes_the_weakest_animal_next_to_it_either_side():
    s = make_state(decks={"A": FILLER[:], "B": FILLER[:]})
    put(s, "2,2", "city_spider", "A")
    put(s, "1,2", "lion", "A")                                  # 7
    put(s, "3,2", "lion", "B")                                  # 7
    put(s, "2,1", "chipmunk", "A")                              # 1: an ally, the weakest
    put(s, "2,3", "squirrel", "B")                              # 4
    end_turn(s); end_turn(s)
    assert s.top_unit("2,1") is None and "chipmunk" in s.remove_pile
    assert s.top_unit("2,3").card_id == "squirrel"              # only one


def test_city_spider_does_nothing_at_the_opponents_dawn():
    s = make_state(decks={"A": FILLER[:], "B": FILLER[:]})
    put(s, "2,2", "city_spider", "A")
    put(s, "2,3", "squirrel", "B")
    end_turn(s)                                                 # B's Dawn
    assert s.top_unit("2,3").card_id == "squirrel"


def test_city_spider_with_no_neighbour_removes_nothing_and_not_itself():
    s = make_state(decks={"A": FILLER[:], "B": FILLER[:]})
    put(s, "2,2", "city_spider", "A")
    end_turn(s); end_turn(s)
    assert s.top_unit("2,2").card_id == "city_spider"


def test_city_spider_hits_stealth_but_not_armor():
    s = make_state(decks={"A": FILLER[:], "B": FILLER[:]})
    put(s, "2,2", "city_spider", "A")
    put(s, "2,3", "tortoise", "B")                              # 6, Armor: can't be removed
    put(s, "3,2", "stick_insect", "B")                          # 6, Stealth: not chosen, so hit
    put(s, "1,2", "lion", "A")                                  # 7
    end_turn(s); end_turn(s)
    assert s.top_unit("2,3").card_id == "tortoise"
    assert s.top_unit("3,2") is None


def test_city_spider_buried_does_nothing():
    s = make_state(decks={"A": FILLER[:], "B": FILLER[:]})
    put(s, "2,2", "city_spider", "A")
    put(s, "2,2", "lion", "B")
    put(s, "2,3", "chipmunk", "B")
    end_turn(s); end_turn(s)
    assert s.top_unit("2,3").card_id == "chipmunk"


# =============================================================================== Cockroach

def test_cockroach_falls_back_onto_its_crossroad_and_places_a_roach():
    s = make_state(decks={"A": FILLER[:], "B": []})
    put(s, "1,2", "cockroach", "A")
    put(s, "1,1", "lion", "B")                                  # 1,1 full: the Roach goes to 1,3 or 2,2
    effects.remove_top(s, "1,2", by_player="B")
    back = s.top_unit("1,2")
    assert back.card_id == "cockroach" and back.owner == "A"
    roaches = [cr for cr in ("1,3", "2,2") if (t := s.top_unit(cr)) and t.card_id == "roach" and t.owner == "A"]
    assert len(roaches) == 1
    assert s.top_unit("1,1").card_id == "lion"                  # never on an occupied neighbour


@pytest.mark.xfail(strict=True, reason=(
    "Two readings of 'Fall: replace this with a Cockroach'. A: Fall is a real removal, so the removed Cockroach goes "
    "to its owner's Remove Pile and a fresh Cockroach takes its place (rulings: 'a real removal, then the effect ... a "
    "fresh Cockroach'). B: the card itself comes back, so the Remove Pile stays empty. The engine follows B."))
def test_cockroach_that_falls_lands_in_the_remove_pile_and_a_fresh_one_replaces_it():
    s = make_state(decks={"A": FILLER[:], "B": []})
    put(s, "1,2", "cockroach", "A")
    effects.remove_top(s, "1,2", by_player="B")
    assert s.top_unit("1,2").card_id == "cockroach"
    assert s.pile_cards_of("A") == ["cockroach"]


def test_cockroach_eaten_by_an_apex_predator_falls():
    s = make_state(hands={"B": ["tiger"]}, current="B", decks={"A": [], "B": []})
    put(s, "4,2", "lion", "B")
    put(s, "3,2", "cockroach", "A")
    rules.apply_action(s, PlaceAction("tiger", ("cr", "3,2")))
    # the Tiger covers then eats; the Cockroach falls and is replaced at the same height, under the Tiger
    assert [u.card_id for u in s.board["3,2"]][0] == "cockroach"
    assert any((t := s.top_unit(cr)) and t.card_id == "roach" for cr in ("2,2", "3,1", "3,3"))


def test_cockroach_covered_is_not_removed_and_does_not_fall():
    s = make_state(hands={"B": ["lion"]}, current="B", decks={"A": [], "B": []})
    put(s, "4,2", "lion", "B")
    put(s, "3,2", "cockroach", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))
    assert [u.card_id for u in s.board["3,2"]] == ["cockroach", "lion"]
    assert not any((t := s.top_unit(cr)) and t.card_id == "roach" for cr in s.board)


# ============================================================================== Roach King

def test_cockroach_legend_comes_back_with_one_more_strength_and_draws():
    s = make_state(decks={"A": ["tiger", "lion"], "B": []})
    put(s, "1,2", "cockroach_legend", "A")
    effects.remove_top(s, "1,2", by_player="B")
    king = s.top_unit("1,2")
    assert king.card_id == "cockroach_legend" and king.owner == "A"
    assert effective_strength(s, king) == CARDS["cockroach_legend"].base_strength + 1
    assert hand_ids(s, "A") == ["lion"]
    effects.remove_top(s, "1,2", by_player="B")                 # again: +1 more, another card
    king = s.top_unit("1,2")
    assert effective_strength(s, king) == CARDS["cockroach_legend"].base_strength + 2
    assert sorted(hand_ids(s, "A")) == ["lion", "tiger"]


def test_cockroach_legend_with_an_empty_deck_still_comes_back():
    s = make_state()
    put(s, "1,2", "cockroach_legend", "A")
    effects.remove_top(s, "1,2", by_player="B")
    assert s.top_unit("1,2").card_id == "cockroach_legend"


def test_cockroach_legend_covered_does_not_fall():
    s = make_state(hands={"B": ["lion"]}, current="B", decks={"A": ["tiger"], "B": []})
    put(s, "4,2", "lion", "B")
    put(s, "3,2", "cockroach_legend", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))
    assert hand_ids(s, "A") == [] and s.board["3,2"][0].strength_counter == 0


# ================================================================================= Macaque

def test_macaque_with_five_cards_in_hand_removes_an_adjacent_enemy_of_any_strength():
    s = make_state(hands={"A": ["macaque"] + ["lion"] * 5})
    put(s, "2,2", "elephant", "B")                              # 9: no strength gate
    apply_click(s, PlaceAction("macaque", ("cr", "1,2")))
    assert s.top_unit("2,2") is None


def test_macaque_with_four_cards_in_hand_removes_nothing():
    s = make_state(hands={"A": ["macaque"] + ["lion"] * 4})     # five with the Macaque, four once it is played
    put(s, "2,2", "elephant", "B")
    apply_click(s, PlaceAction("macaque", ("cr", "1,2")))
    assert s.top_unit("2,2").card_id == "elephant"


def test_macaque_never_removes_an_ally_and_respects_stealth_and_armor():
    s = make_state(hands={"A": ["macaque"] + ["lion"] * 5})
    put(s, "1,1", "lion", "A")
    put(s, "1,3", "stick_insect", "B")
    put(s, "2,2", "tortoise", "B")
    apply_click(s, PlaceAction("macaque", ("cr", "1,2")))
    assert s.top_unit("1,1").card_id == "lion"
    assert s.top_unit("1,3").card_id == "stick_insect" and s.top_unit("2,2").card_id == "tortoise"


# ======================================================================= [MACAQUE] (legend)

def test_macaque_legend_draws_up_to_the_opponents_hand_size():
    s = make_state(hands={"A": ["macaque_legend", "lion"], "B": ["lion"] * 4}, decks={"A": ["tiger"] * 6, "B": []})
    rules.apply_action(s, PlaceAction("macaque_legend", ("cr", "1,2")))
    assert len(s.hands["A"]) == 4                               # 1 left after playing it, draws 3


def test_macaque_legend_draws_nothing_when_ahead_or_level():
    s = make_state(hands={"A": ["macaque_legend", "lion", "lion"], "B": ["lion"]}, decks={"A": ["tiger"] * 6, "B": []})
    rules.apply_action(s, PlaceAction("macaque_legend", ("cr", "1,2")))
    assert len(s.hands["A"]) == 2 and len(s.decks["A"]) == 6


def test_macaque_legend_stops_when_the_deck_runs_out():
    s = make_state(hands={"A": ["macaque_legend"], "B": ["lion"] * 5}, decks={"A": ["tiger"] * 2, "B": []})
    rules.apply_action(s, PlaceAction("macaque_legend", ("cr", "1,2")))
    assert len(s.hands["A"]) == 2 and s.decks["A"] == []


# ================================================================================ Mosquito

def test_mosquito_gives_an_adjacent_enemy_minus_two_for_good():
    s = make_state(hands={"A": ["mosquito"]})
    t = put(s, "3,3", "lion", "B")
    put(s, "3,1", "lion", "A")                                  # an ally: not a target
    apply_click(s, PlaceAction("mosquito", ("cr", "3,2")))      # Flight: 3,2 is far from A's chain
    assert t.strength_counter == -2 and effective_strength(s, t) == 5
    effects.remove_top(s, "3,2", by_player="B")                 # the Mosquito gone: a give, so it stays
    assert effective_strength(s, t) == 5
    assert s.top_unit("3,1").strength_counter == 0


def test_mosquito_offers_only_enemies():
    s = make_state(hands={"A": ["mosquito"]})
    put(s, "3,3", "lion", "B"); put(s, "3,1", "lion", "A")
    rules.apply_action(s, PlaceAction("mosquito", ("cr", "3,2")))
    assert options(s) == {"3,3"} and not s.pending["optional"]


def test_mosquito_kills_an_enemy_pushed_below_zero_but_not_at_zero():
    s = make_state(hands={"A": ["mosquito", "mosquito"]})
    put(s, "3,3", "cockroach", "B")                             # 1 -> -1: dies (it falls and comes back)
    apply_click(s, PlaceAction("mosquito", ("cr", "3,2")))
    assert s.top_unit("3,3").card_id == "cockroach" and s.top_unit("3,3").strength_counter == 0
    s2 = make_state(hands={"A": ["mosquito"]})
    v = put(s2, "3,3", "alley_cat", "B")                        # 2 -> 0: not below 0, lives
    apply_click(s2, PlaceAction("mosquito", ("cr", "3,2")))
    assert s2.top_unit("3,3") is v and effective_strength(s2, v) == 0


def test_mosquito_with_no_adjacent_enemy_just_lands():
    s = make_state(hands={"A": ["mosquito"]})
    rules.apply_action(s, PlaceAction("mosquito", ("cr", "3,2")))
    assert s.pending is None and s.top_unit("3,2").card_id == "mosquito"


def test_mosquito_cannot_choose_a_stealth_enemy():
    s = make_state(hands={"A": ["mosquito"]})
    st = put(s, "3,3", "stick_insect", "B")
    apply_click(s, PlaceAction("mosquito", ("cr", "3,2")))
    assert st.strength_counter == 0


# =================================================================================== Mouse

def test_mouse_draws_a_rodent_from_the_deck():
    s = make_state(hands={"A": ["mouse"]}, decks={"A": ["lion", "squirrel", "tiger"], "B": []})
    rules.apply_action(s, PlaceAction("mouse", ("cr", "1,2")))
    assert hand_ids(s, "A") == ["squirrel"] and sorted(s.decks["A"]) == ["lion", "tiger"]


def test_mouse_with_no_rodent_in_the_deck_draws_nothing():
    s = make_state(hands={"A": ["mouse"]}, decks={"A": ["lion", "tiger"], "B": []})
    rules.apply_action(s, PlaceAction("mouse", ("cr", "1,2")))
    assert hand_ids(s, "A") == [] and len(s.decks["A"]) == 2


# ================================================================================= Opossum

def test_opossum_returns_an_adjacent_ally_to_hand_not_an_enemy():
    s = make_state(hands={"A": ["opossum"]})
    put(s, "1,1", "squirrel", "A")
    put(s, "2,2", "lion", "B")
    rules.apply_action(s, PlaceAction("opossum", ("cr", "1,2")))
    assert options(s) == {"1,1"} and not s.pending["optional"]  # its Roar isn't declined (rulings)
    choose(s, "1,1")
    assert hand_ids(s, "A") == ["squirrel"] and s.top_unit("1,1") is None
    assert "squirrel" not in s.remove_pile and s.top_unit("2,2").card_id == "lion"


def test_opossum_returning_a_top_ally_uncovers_what_was_beneath():
    s = make_state(hands={"A": ["opossum"]})
    put(s, "1,1", "lion", "B")
    put(s, "1,1", "elephant", "A")
    apply_click(s, PlaceAction("opossum", ("cr", "1,2")))
    assert hand_ids(s, "A") == ["elephant"] and s.top_unit("1,1").card_id == "lion"


def test_opossum_with_no_adjacent_ally_just_lands():
    s = make_state(hands={"A": ["opossum"]})
    put(s, "2,2", "lion", "B")
    rules.apply_action(s, PlaceAction("opossum", ("cr", "1,2")))
    assert s.pending is None and s.top_unit("2,2").card_id == "lion"


def test_opossum_cannot_return_an_armored_ally():
    s = make_state(hands={"A": ["opossum"]})
    put(s, "1,1", "tortoise", "A")
    rules.apply_action(s, PlaceAction("opossum", ("cr", "1,2")))
    assert s.pending is None and s.top_unit("1,1").card_id == "tortoise"


# ================================================================================== Pigeon

def test_pigeon_flies_anywhere_but_covers_only_weaker_enemies():
    s = make_state(hands={"A": ["pigeon"]})
    put(s, "3,2", "squirrel", "B")                              # 4 < 5
    put(s, "3,3", "beaver", "B")                                # 5 == 5
    t = place_targets(s)
    assert {"3,1", "3,2", "4,1"} <= t and "3,3" not in t


def test_pigeon_cannot_capture_a_den_without_a_chain():
    s = make_state(hands={"A": ["pigeon"]})
    assert not any(isinstance(a, PlaceAction) and a.target[0] == "hq" for a in rules.legal_actions(s))


def test_pigeon_captures_a_den_with_a_chain_like_any_animal():
    s = make_state(hands={"A": ["pigeon"]})
    for cr in ("1,1", "2,1", "3,1", "4,1"):
        put(s, cr, "lion", "A")
    assert any(isinstance(a, PlaceAction) and a.target[0] == "hq" for a in rules.legal_actions(s))


# ================================================================================= Raccoon

def test_raccoon_returns_one_of_your_removed_animals_never_the_opponents():
    s = make_state(hands={"A": ["raccoon"]})
    s.pile_add("tiger", "B"); s.pile_add("lion", "A")
    rules.apply_action(s, PlaceAction("raccoon", ("cr", "1,2")))
    assert options(s) == {"lion"}
    choose(s, "lion")
    assert hand_ids(s, "A") == ["lion"] and s.remove_pile == ["tiger"]


def test_raccoon_with_an_empty_remove_pile_just_lands():
    s = make_state(hands={"A": ["raccoon"]})
    s.pile_add("tiger", "B")
    rules.apply_action(s, PlaceAction("raccoon", ("cr", "1,2")))
    assert s.pending is None and hand_ids(s, "A") == []


# ===================================================================================== Rat

def test_rat_with_an_empty_hand_removes_an_adjacent_enemy_of_any_strength():
    s = make_state(hands={"A": ["rat"]})
    put(s, "2,2", "elephant", "B")
    apply_click(s, PlaceAction("rat", ("cr", "1,2")))
    assert s.top_unit("2,2") is None


def test_rat_with_a_card_left_in_hand_removes_nothing():
    s = make_state(hands={"A": ["lion", "rat"]})
    put(s, "2,2", "elephant", "B")
    apply_click(s, PlaceAction("rat", ("cr", "1,2")))
    assert s.top_unit("2,2").card_id == "elephant"


def test_rat_with_an_empty_hand_never_removes_an_ally():
    s = make_state(hands={"A": ["rat"]})
    put(s, "2,2", "lion", "A")
    rules.apply_action(s, PlaceAction("rat", ("cr", "1,2")))
    assert s.top_unit("2,2").card_id == "lion"


def test_rat_legend_gains_four_food_for_each_other_rodent_you_control_and_draws():
    s = make_state(hands={"A": ["rat_legend"]}, decks={"A": ["tiger"], "B": []})
    put(s, "1,1", "squirrel", "A")                              # a Rodent you control
    put(s, "2,2", "mouse", "A")                                 # another
    put(s, "3,2", "mouse", "B")                                 # the opponent's: not yours
    put(s, "1,3", "mouse", "A"); put(s, "1,3", "lion", "B")     # buried under an enemy: you don't control it
    rules.apply_action(s, PlaceAction("rat_legend", ("cr", "1,2")))
    assert s.food["A"] == 8 and hand_ids(s, "A") == ["tiger"]


def test_rat_legend_with_no_other_rodent_still_draws():
    s = make_state(hands={"A": ["rat_legend"]}, decks={"A": ["tiger"], "B": []})
    rules.apply_action(s, PlaceAction("rat_legend", ("cr", "1,2")))
    assert s.food["A"] == 0 and hand_ids(s, "A") == ["tiger"]


# ================================================================================== Pestis

def test_rat_legend_2_removes_an_adjacent_stack_whole_both_players_units():
    s = make_state(hands={"A": ["rat_legend_2"]})
    put(s, "2,2", "lion", "A"); put(s, "2,2", "elephant", "B")
    put(s, "1,1", "squirrel", "A")
    rules.apply_action(s, PlaceAction("rat_legend_2", ("cr", "1,2")))
    assert {"1,1", "2,2"} <= options(s)                         # "an adjacent animal": yours too
    choose(s, "2,2")
    assert s.board.get("2,2", []) == [] and {"lion", "elephant"} <= set(s.remove_pile)


def test_rat_legend_2_next_to_only_its_own_animal_removes_it():
    s = make_state(hands={"A": ["rat_legend_2"]})
    put(s, "1,1", "squirrel", "A")
    apply_click(s, PlaceAction("rat_legend_2", ("cr", "1,2")))
    assert s.top_unit("1,1") is None


def test_rat_legend_2_skips_a_buried_armored_animal_in_place_and_cannot_choose_armor_or_stealth():
    s = make_state(hands={"A": ["rat_legend_2"]})
    put(s, "2,2", "tortoise", "A"); put(s, "2,2", "elephant", "B")
    put(s, "1,1", "tortoise", "B")
    put(s, "1,3", "stick_insect", "B")
    rules.apply_action(s, PlaceAction("rat_legend_2", ("cr", "1,2")))
    assert "1,1" not in options(s) and "1,3" not in options(s)
    choose(s, "2,2")
    assert [u.card_id for u in s.board["2,2"]] == ["tortoise"]


def test_rat_legend_2_with_nothing_adjacent_just_lands():
    s = make_state(hands={"A": ["rat_legend_2"]})
    rules.apply_action(s, PlaceAction("rat_legend_2", ("cr", "1,2")))
    assert s.pending is None


# ============================================================================== Street Dog

def test_street_dog_gives_a_connected_roamer_plus_three_and_it_roams():
    s = make_state(hands={"A": ["street_dog"]}, decks={"A": FILLER[:], "B": FILLER[:]})
    wolf = put(s, "1,1", "wolf", "A")
    put(s, "1,3", "lion", "A")                                  # connected, no Roam: not offered
    put(s, "4,3", "wolf", "A")                                  # Roam, not connected: not offered
    rules.apply_action(s, PlaceAction("street_dog", ("cr", "1,2")))
    assert options(s) == {"1,1"}
    choose(s, "1,1")
    assert wolf.strength_counter == 3
    assert s.pending and "2,1" in options(s)
    choose(s, "2,1")
    assert s.top_unit("2,1") is wolf and s.actions_taken_this_turn == 1
    effects.remove_top(s, "1,2", by_player="B")                 # a give: it stays when the Street Dog is gone
    assert wolf.strength_counter == 3


def test_street_dog_with_no_connected_roamer_just_lands():
    s = make_state(hands={"A": ["street_dog"]})
    put(s, "1,1", "lion", "A")
    rules.apply_action(s, PlaceAction("street_dog", ("cr", "1,2")))
    assert s.pending is None


def test_street_dog_does_not_choose_itself_or_an_enemy_roamer():
    s = make_state(hands={"A": ["street_dog"]})
    put(s, "2,2", "wolf", "B")
    rules.apply_action(s, PlaceAction("street_dog", ("cr", "1,2")))
    assert s.pending is None
