"""Phase 2 golden tests: one focused scenario per reworked card / mechanism.

Grows stage by stage (the module-wide skip was dropped in Stage 2.1). Map A geometry used
below: A's HQ fronts are column 1 ("1,1"/"1,2"/"1,3"), B's are column 4; crossroads are a
4x3 grid with orthogonal neighbours, so "2,2" is adjacent to "1,2","3,2","2,1","2,3".
"""

from __future__ import annotations

import pytest

from animal_kingdom.engine import effects, rules
from animal_kingdom.engine.actions import SKIP, ChoiceAction, DrawAction, PlaceAction, RoamAction
from animal_kingdom.engine.cards import load_cards
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.state import EngineError, UnitInstance
from animal_kingdom.engine.strength import card_strength, effective_strength, placement_strength

from ._helpers import apply_click, hand_ids, make_state, place_targets, put

CFG = Config.default()
CARDS = load_cards()
GW = CARDS["guard_wasp"].base_strength


def hand_inst(state, player, card_id):
    return next(u for u in state.hands[player] if u.card_id == card_id)


def advance_to(state, target_tc):
    """Advance by drawing each turn until turn_counter reaches target_tc (or terminal)."""
    while state.turn_counter < target_tc and rules.is_terminal(state) is None:
        rules.apply_action(state, DrawAction())


# ============================================================== anthems ("has +X", live)



def test_guard_hornet_anthem_gated_on_four_colony():
    s = make_state()
    gh = put(s, "1,1", "guard_wasp", "A")
    assert effective_strength(s, gh) == GW
    for cr in ("1,2", "1,3"):
        put(s, cr, "worker_ant", "A")
    assert effective_strength(s, gh) == GW               # only 3 Colony incl. self
    put(s, "2,1", "worker_ant", "A")                     # three more Colony -> 4 incl. self
    assert effective_strength(s, gh) == GW + CFG.guard_hornet_bonus   # the anthem


def test_nurse_bumblebee_draws_a_colony_animal():
    s = make_state(hands={"A": ["nurse_bumblebee"]}, decks={"A": ["lion", "worker_ant", "tiger"], "B": []})
    rules.apply_action(s, PlaceAction("nurse_bumblebee", ("cr", "1,2")))
    assert hand_ids(s, "A") == ["worker_ant"]


# ============================================== counters ("give +X", stored on instance)





def test_scarlett_places_poppy_and_rusty():
    s = make_state(hands={"A": ["fox_legend"]})
    put(s, "1,2", "street_dog", "A")                                # HQ-front anchor so 2,2 is connected
    rules.apply_action(s, PlaceAction("fox_legend", ("cr", "2,2")))
    cubs = sorted(u.card_id for st in s.board.values() for u in st if u.owner == "A" and u.card_id in ("baby_fox", "baby_fox_2"))
    assert cubs == ["baby_fox", "baby_fox_2"]






def test_outrider_lets_canines_ignore_connection():
    s = make_state(hands={"A": ["jackal"]})
    put(s, "3,2", "street_dog", "A")                                # a friendly Canine with no path to HQ
    assert "2,2" not in place_targets(s)                     # can't reach it normally
    put(s, "3,3", "outrider", "A")                           # control a Coyote (also disconnected)
    assert "2,2" in place_targets(s)                         # may now place adjacent to the pack




def test_hand_counter_travels_onto_the_board():
    s = make_state(hands={"A": ["chimpanzee"]})
    hand_inst(s, "A", "chimpanzee").strength_counter = 2
    iid = hand_inst(s, "A", "chimpanzee").iid
    rules.apply_action(s, PlaceAction("chimpanzee", ("cr", "1,1")))
    placed = s.top_unit("1,1")
    assert placed.iid == iid and placed.strength_counter == 2  # same instance moved
    assert effective_strength(s, placed) == 6                  # base 4 + counter


def test_dingo_buffs_adjacent_canine_at_end_of_turn():
    s = make_state(current="A", decks={"A": ["lion"], "B": ["lynx"]})
    put(s, "2,2", "dingo", "A")
    fox = put(s, "1,2", "fox", "A")
    s.actions_taken_this_turn = s.config.actions_per_turn - 1
    rules.apply_action(s, DrawAction())                  # ends A's turn -> Dingo fires
    assert fox.strength_counter == 1


def test_dingo_buffs_every_adjacent_canine_not_just_one():
    s = make_state(current="A", decks={"A": ["lion"], "B": ["lynx"]})
    put(s, "2,2", "dingo", "A")
    canines = [put(s, cr, "fox", "A") for cr in ("1,2", "3,2", "2,1")]
    s.actions_taken_this_turn = s.config.actions_per_turn - 1
    rules.apply_action(s, DrawAction())
    assert [c.strength_counter for c in canines] == [1, 1, 1]


# =================================================================== Canine removal/draw

def test_chimpanzee_removes_enemy_up_to_its_buffed_strength():
    s = make_state(hands={"A": ["chimpanzee"]})
    hand_inst(s, "A", "chimpanzee").strength_counter = 2  # buffed body 6
    put(s, "1,2", "lion", "A")                           # connects 2,2
    put(s, "3,2", "leopard", "B")                        # enemy str 6, adjacent to 2,2
    put(s, "2,3", "lion", "B")                            # enemy str 7, adjacent to 2,2
    apply_click(s, PlaceAction("chimpanzee", ("cr", "2,2")))
    assert s.owner_of("3,2") is None                     # 6 <= 6 removed
    assert s.owner_of("2,3") == "B"                       # 7 > 6 survives


# ===================================================================== Group A statics

def test_porcupine_removes_the_first_enemy_that_covers_it_then_is_an_ordinary_unit():
    s = make_state(current="B", hands={"B": ["elephant", "elephant"]}, food={"A": 0, "B": 40})
    put(s, "4,2", "caracal", "B")                        # B front connects 3,2
    porcupine = put(s, "3,2", "porcupine", "A")          # A porcupine (str 7)
    rules.apply_action(s, PlaceAction("elephant", ("cr", "3,2")))   # 9 covers 7...
    assert s.top_unit("3,2") is porcupine                # ...and the spines remove it
    assert "elephant" in s.remove_pile
    rules.apply_action(s, PlaceAction("elephant", ("cr", "3,2")))   # only the first time
    assert s.top_unit("3,2").card_id == "elephant"


def test_the_hercules_beetle_covers_enemies_of_any_strength():
    cover = make_state(hands={"A": ["hercules_beetle"]})
    put(cover, "1,2", "caracal", "A")
    put(cover, "2,2", "lion", "B")                       # str 7 enemy
    assert PlaceAction("hercules_beetle", ("cr", "2,2")) in rules.legal_actions(cover)

    covered = make_state(current="B", hands={"B": ["alley_cat"]})
    put(covered, "4,2", "caracal", "B")
    put(covered, "3,2", "hercules_beetle", "A")          # a plain 0: str 1 alley_cat covers it
    assert PlaceAction("alley_cat", ("cr", "3,2")) in rules.legal_actions(covered)


def test_python_grows_with_every_removal_wherever_it_is():
    s = make_state(hands={"A": ["python"]})
    g = put(s, "1,1", "python", "A")
    assert effective_strength(s, g) == 0
    for cr, who in (("2,1", "B"), ("2,2", "A"), ("2,3", "B")):
        put(s, cr, "mouse", who)
        effects.remove_top(s, cr, by_player="A")
    assert effective_strength(s, g) == 3 and placement_strength(s, s.hands["A"][0]) == 3   # on the board and in hand


def test_armor_survives_removal_effect():
    s = make_state(hands={"A": ["chimpanzee"]})
    hand_inst(s, "A", "chimpanzee").strength_counter = 3  # body 7 - clears Armadillo's str 5
    put(s, "1,2", "lion", "A")
    put(s, "3,2", "armadillo", "B")                      # str 5 but Armor
    rules.apply_action(s, PlaceAction("chimpanzee", ("cr", "2,2")))
    assert s.owner_of("3,2") == "B"


def test_leopard_lets_other_cats_cover_equal_strength():
    s = make_state(hands={"A": ["caracal"]})
    put(s, "1,2", "leopard", "A")                        # connects 2,2; the static's source
    put(s, "2,2", "caracal", "B")                        # enemy str 6
    assert PlaceAction("caracal", ("cr", "2,2")) in rules.legal_actions(s)  # 6 >= 6


def test_leopard_lets_a_roaming_cat_cover_equal_strength():
    # Placing and roaming cover by one rule (Martin, 2026-10-24)
    s = make_state()
    put(s, "1,1", "leopard", "A")                        # the static's source
    put(s, "1,2", "leopard_legend", "A")
    put(s, "2,2", "wolf", "B")
    roamer, prey = s.top_unit("1,2"), s.top_unit("2,2")
    roamer.strength_counter += effective_strength(s, prey) - effective_strength(s, roamer)
    assert RoamAction("1,2", ("cr", "2,2")) in rules.legal_actions(s)


def test_second_leopard_benefits_from_the_first():
    s = make_state(hands={"A": ["leopard"]})
    put(s, "1,2", "leopard", "A")                        # connects 2,2; the static's source
    put(s, "2,2", "wolf", "B")                      # enemy str 6
    assert PlaceAction("leopard", ("cr", "2,2")) in rules.legal_actions(s)  # 6 >= 6


def test_leopard_alone_needs_strictly_greater():
    s = make_state(hands={"A": ["leopard"]})
    put(s, "1,2", "lion", "A")                           # connects 2,2; no Leopard on the board
    put(s, "2,2", "wolf", "B")                      # enemy str 6
    assert PlaceAction("leopard", ("cr", "2,2")) not in rules.legal_actions(s)


def test_cougar_places_adjacent_to_a_cat_ignoring_connection():
    s = make_state(hands={"A": ["cougar"]})
    put(s, "3,3", "lion", "A")                           # a Cat, disconnected from HQ
    assert "3,2" in place_targets(s)                     # a neighbour of the Cat


def test_black_panther_untargetable_by_enemy_effect():
    s = make_state(current="B", hands={"B": ["chimpanzee"]})
    hand_inst(s, "B", "chimpanzee").strength_counter = 3  # body 7
    put(s, "4,3", "caracal", "B")                        # B front connects 3,3
    put(s, "3,2", "black_panther", "A")                  # str 6, adjacent to 3,3
    rules.apply_action(s, PlaceAction("chimpanzee", ("cr", "3,3")))
    assert s.owner_of("3,2") == "A"                      # untargetable -> survives


# =============================================================== shared (kept from M2a)

def test_gale_draws_for_each_unit_you_control_next_to_the_opponents_den_itself_included():
    s = make_state(current="A", hands={"A": ["falcon_legend"]}, decks={"A": ["lion"] * 5, "B": []})
    put(s, "4,1", "rat", "A")                            # B's front crossroads: 4,1 4,2 4,3
    put(s, "4,3", "lion", "B")
    before = len(s.hands["A"])
    rules.apply_action(s, PlaceAction("falcon_legend", ("cr", "4,2")))   # Gale lands on the third
    assert len(s.hands["A"]) == before - 1 + 2          # the Rat and Gale itself


def test_spines_ignore_a_friendly_cover():
    s = make_state(current="A", hands={"A": ["lion"]})
    put(s, "1,2", "caracal", "A")
    porcupine = put(s, "2,2", "porcupine", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "2,2")))
    assert s.top_unit("2,2").card_id == "lion" and porcupine.retaliation_used is False


def test_spines_cannot_remove_an_armor_coverer():
    s = make_state(current="A", hands={"A": ["cairn"]}, food={"A": 20, "B": 0})
    put(s, "1,2", "caracal", "A")
    porcupine = put(s, "2,2", "porcupine", "B")          # str 7
    rules.apply_action(s, PlaceAction("cairn", ("cr", "2,2")))  # str 10 Armor covers it
    assert s.owner_of("2,2") == "A"                      # Armor resists the spines
    assert porcupine.retaliation_used is True            # but they're spent


# ===================================================================== clone w/ counters

def test_clone_is_independent_with_strength_counters():
    s = make_state()
    put(s, "1,1", "fox", "A")
    c = s.clone()
    c.board["1,1"][0].strength_counter = 5
    assert s.board["1,1"][0].strength_counter == 0       # original untouched


# ======================================== Stage 2.2: draw / shuffle / remove event engine

def test_rattlesnake_gains_strength_per_own_card_shuffled_in_every_zone():
    s = make_state(hands={"A": ["rattlesnake"]},
                   decks={"A": ["rattlesnake"], "B": []})
    buried = put(s, "1,1", "rattlesnake", "A")
    put(s, "1,1", "lion", "A")                        # Rattlesnake is covered/inactive
    effects.shuffle_back(s, "A", ["lion", "fox"])         # two cards = two events
    assert effective_strength(s, buried) == 2
    assert placement_strength(s, hand_inst(s, "A", "rattlesnake")) == 2
    assert card_strength(s, "rattlesnake", "A") == 2       # also applies to the deck copy
    effects.shuffle_back(s, "B", ["mouse"])                # only your shuffles count
    assert card_strength(s, "rattlesnake", "A") == 2


def test_egg_eater_has_strength_for_each_removed_egg():
    s = make_state()
    eater = put(s, "1,1", "egg_eater", "A")
    rat = put(s, "2,2", "rat", "B")
    effects._remove_specific(s, "2,2", rat, by_player="A")
    assert effective_strength(s, eater) == 0                        # not an Egg
    egg = put(s, "3,3", "bird_egg", "B")
    effects._remove_specific(s, "3,3", egg, by_player="A", by_effect=False)
    assert effective_strength(s, eater) == CFG.egg_eater_growth
    assert card_strength(s, "egg_eater", "A") == CFG.egg_eater_growth  # in hand and deck too
    mine = put(s, "3,2", "snake_egg", "A")                            # anyone's Egg counts
    effects._remove_specific(s, "3,2", mine, by_player="A", by_effect=False)
    assert effective_strength(s, eater) == 2 * CFG.egg_eater_growth


def test_omen_when_drawn_discards_from_opponents_hand_only():
    s = make_state(current="A", decks={"A": ["swan_legend"], "B": []})
    s.add_to_hand("A", "lion")
    s.add_to_hand("B", "fox")
    effects.draw_cards(s, "A", 1)                        # draws Black Swan
    assert sorted(hand_ids(s, "A")) == ["lion", "swan_legend"]
    assert len(s.hands["B"]) == 0                        # lost its only card
    assert s.remove_pile == ["fox"]


def test_omen_fires_every_time_it_is_drawn():
    s = make_state(current="A")
    s.add_to_hand("B", "fox")
    s.add_to_hand("B", "lion")
    for left in (1, 0):                                  # "Whenever you draw Black Swan": no cap, twice a turn too
        inst = UnitInstance("swan_legend", "A", s.new_iid())
        s.hands["A"].append(inst)
        effects._omen_drawn(s, inst)
        assert len(s.hands["B"]) == left


def test_ember_deathrattle_shuffles_itself_back_to_deck():
    s = make_state(decks={"A": [], "B": []})
    e = put(s, "2,2", "pheasant_legend", "A")
    effects._remove_specific(s, "2,2", e, by_player="A", by_effect=False)
    assert "pheasant_legend" not in s.remove_pile                 # relocated out of the pile
    assert "pheasant_legend" in s.decks["A"]


def test_mouse_draws_a_rodent_at_random():
    s = make_state(hands={"A": ["mouse"]}, decks={"A": ["lion", "squirrel", "eagle"], "B": []})
    rules.apply_action(s, PlaceAction("mouse", ("cr", "1,2")))
    assert "squirrel" in hand_ids(s, "A")               # the only Rodent in the deck
    assert "squirrel" not in s.decks["A"]


def test_fathom_draws_a_legendary():
    s = make_state(hands={"A": ["octopus_legend_2"]}, decks={"A": ["lion", "anaconda_legend", "eagle"], "B": []})
    rules.apply_action(s, PlaceAction("octopus_legend_2", ("cr", "1,2")))
    assert "anaconda_legend" in hand_ids(s, "A")                    # the only legendary in the deck


def test_snake_egg_draws_a_snake_now_and_two_when_it_hatches():
    snakes = ["python", "rattlesnake", "cottonmouth", "black_mamba"]
    s = make_state(hands={"A": ["snake_egg"]}, decks={"A": snakes + ["owl", "raven"], "B": []})
    rules.apply_action(s, PlaceAction("snake_egg", ("cr", "1,2")))
    assert [CARDS[c].tags >= {"Snake"} for c in hand_ids(s, "A")] == [True] * CFG.snake_egg_draw
    hatch = next(x for x in s.scheduled if x["step"]["op"] == "egg_hatch")
    assert hatch["remaining"] == CFG.egg_hatch_delay
    effects._op_egg_hatch(s, hatch["step"])
    assert s.owner_of("1,2") is None                    # the egg removes itself (feeds Python)
    assert "snake_egg" in s.remove_pile
    assert sum("Snake" in CARDS[c].tags for c in hand_ids(s, "A")) == CFG.snake_egg_draw + CFG.egg_hatch_draw


def test_bird_egg_scouts_now_and_draws_a_bird_when_it_hatches_next_turn():
    birds = ["owl", "raven", "hawk", "magpie", "pheasant_legend"]
    s = make_state(current="A", hands={"A": ["bird_egg"]},
                   decks={"A": birds + ["python"] * 4, "B": ["lion"] * 6})
    rules.apply_action(s, PlaceAction("bird_egg", ("cr", "1,2")))
    assert s.pending is not None and s.pending["from_deck_reveal"]
    options = s.pending["options"]
    assert len(options) <= CFG.scout_count and all("Bird" in CARDS[c].tags for c in options)
    rules.apply_action(s, ChoiceAction(options[0]))
    assert hand_ids(s, "A") == [options[0]]
    assert len(s.decks["A"]) == 8                       # the others went back
    rules.apply_action(s, DrawAction())                 # A's second action ends the turn
    birds_in_hand = sum("Bird" in CARDS[c].tags for c in hand_ids(s, "A"))
    rules.apply_action(s, DrawAction())                 # B's turn
    rules.apply_action(s, DrawAction())
    assert s.current == "A" and s.owner_of("1,2") is None   # hatched at the start of A's turn
    assert s.pending is None                            # no choice at the start of a turn: it draws a Bird
    assert sum("Bird" in CARDS[c].tags for c in hand_ids(s, "A")) == birds_in_hand + 1


def test_scout_with_a_filter_only_shows_matching_cards():
    s = make_state(current="A", hands={"A": ["octopus_legend_2"]},
                   decks={"A": ["lion", "anaconda_legend", "goose_legend", "swan_legend", "pheasant_legend", "tiger"], "B": []})
    rules.apply_action(s, PlaceAction("octopus_legend_2", ("cr", "1,2")))
    options = s.pending["options"]
    assert len(options) == CFG.scout_count and all(CARDS[c].rarity == "legendary" for c in options)
    rules.apply_action(s, ChoiceAction(options[1]))
    assert hand_ids(s, "A") == [options[1]] and len(s.decks["A"]) == 5


def test_owl_scouts_the_top_three_draws_one_and_shuffles_the_rest():
    s = make_state(current="A", hands={"A": ["owl"]},
                   decks={"A": ["lion", "fox", "rat", "eagle"], "B": []})
    rules.apply_action(s, PlaceAction("owl", ("cr", "1,2")))
    assert s.pending is not None                        # choose among the top 3
    rules.apply_action(s, ChoiceAction("fox"))
    assert "fox" in hand_ids(s, "A")
    assert sorted(s.decks["A"]) == ["eagle", "lion", "rat"]   # the other two shuffled back


def test_scout_shows_three_different_cards_when_the_deck_has_them():
    # Owl: copies near the top are passed over until three different cards are found (they stay where they were).
    s = make_state(current="A", hands={"A": ["owl"]},
                   decks={"A": ["eagle", "rat", "lion", "lion", "lion"], "B": []})
    rules.apply_action(s, PlaceAction("owl", ("cr", "1,2")))
    assert sorted(s.pending["options"]) == ["eagle", "lion", "rat"]
    # Scout a Bird: three different Birds however many copies of one the deck holds.
    s = make_state(current="A", hands={"A": ["octopus_legend_2"]},
                   decks={"A": ["anaconda_legend", "anaconda_legend", "anaconda_legend", "goose_legend", "goose_legend", "swan_legend"], "B": []})
    rules.apply_action(s, PlaceAction("octopus_legend_2", ("cr", "1,2")))
    assert sorted(s.pending["options"]) == ["anaconda_legend", "goose_legend", "swan_legend"]


def test_raven_draws_three_then_shuffles_two_cards_from_hand():
    s = make_state(current="A", hands={"A": ["raven"]},
                   decks={"A": ["lion", "fox", "rat", "eagle", "owl"], "B": []})
    rules.apply_action(s, PlaceAction("raven", ("cr", "1,2")))
    assert len(s.hands["A"]) == 3                        # drew 3; must choose 2 to shuffle
    first = s.hands["A"][0]
    rules.apply_action(s, ChoiceAction(first.iid))
    second = s.hands["A"][0]
    rules.apply_action(s, ChoiceAction(second.iid))
    assert len(s.hands["A"]) == 1                        # net +1 card
    assert len(s.decks["A"]) == 4


def test_deck_reveal_choices_are_tagged_from_deck_reveal():
    # Owl/Raven selections are over cards revealed from the hidden deck. The generic
    # `from_deck_reveal` provenance tag is the contract search bots rely on to collapse these
    # noise-in-lookahead choices (bots/turn_search.py); other choices must NOT carry it.
    owl = make_state(current="A", hands={"A": ["owl"]},
                     decks={"A": ["lion", "fox", "rat"], "B": []})
    rules.apply_action(owl, PlaceAction("owl", ("cr", "1,2")))
    assert owl.pending["from_deck_reveal"] is True

    raven = make_state(current="A", hands={"A": ["raven"]},
                       decks={"A": ["lion", "fox", "rat", "eagle"], "B": []})
    rules.apply_action(raven, PlaceAction("raven", ("cr", "1,2")))
    assert raven.pending["from_deck_reveal"] is True


# =================================================== Stage 2.3: Apex Predator (decision D)

def test_apex_eats_a_weaker_enemy_and_occupies():
    s = make_state(hands={"A": ["tiger"]})
    put(s, "1,2", "lion", "A")                          # connects 2,2
    put(s, "2,2", "tuna", "B")                        # enemy str 3 < tiger 7
    rules.apply_action(s, PlaceAction("tiger", ("cr", "2,2")))
    assert s.top_unit("2,2").card_id == "tiger"          # occupies (not stacks)
    assert "tuna" in s.remove_pile                     # the prey was eaten


def test_apex_cannot_land_on_empty_or_capture_hq():
    s = make_state(hands={"A": ["tiger"]})
    for cr in ("1,2", "2,2", "3,2", "4,2"):             # chain to B's front
        put(s, cr, "caracal", "A")
    legal = rules.legal_actions(s)
    assert all(not (a.target == ("cr", "1,1")) for a in legal if a.card_id == "tiger")  # no empty
    assert PlaceAction("tiger", ("hq", "B")) not in legal                                # no HQ


def test_apex_may_eat_its_own_unit():
    eats_own = make_state(hands={"A": ["tiger"]})
    put(eats_own, "1,2", "alley_cat", "A")
    rules.apply_action(eats_own, PlaceAction("tiger", ("cr", "1,2")))
    assert eats_own.top_unit("1,2").card_id == "tiger" and "alley_cat" in eats_own.remove_pile


def test_apex_covers_but_does_not_eat_an_armor():
    # Armor can't be eaten, but the predator may still land on it under normal covering
    # rules (strictly-greater) and simply bury it.
    s = make_state(hands={"A": ["tiger"]})
    put(s, "1,2", "armadillo", "A")                    # own Armor (str 5)
    assert PlaceAction("tiger", ("cr", "1,2")) in rules.legal_actions(s)
    rules.apply_action(s, PlaceAction("tiger", ("cr", "1,2")))
    assert s.top_unit("1,2").card_id == "tiger"         # tiger on top
    assert s.board["1,2"][0].card_id == "armadillo"    # armadillo buried, not eaten
    assert "armadillo" not in s.remove_pile


def test_apex_eats_an_enemy_with_stealth():
    # Stealth hides from chosen targets, not from a predator landing on it (Martin, 2026-10-01).
    s = make_state(current="A", hands={"A": ["polar_bear"]})
    put(s, "1,2", "lion", "A")                          # connects 2,2
    put(s, "2,2", "black_panther", "B")                 # enemy str 7, untargetable
    assert PlaceAction("polar_bear", ("cr", "2,2")) in rules.legal_actions(s)
    rules.apply_action(s, PlaceAction("polar_bear", ("cr", "2,2")))
    assert [u.card_id for u in s.board["2,2"]] == ["polar_bear"]
    assert "black_panther" in s.remove_pile


def test_apex_destroys_an_egg():
    s = make_state(current="A", hands={"A": ["tiger"]})
    put(s, "1,2", "caracal", "A")
    put(s, "2,2", "bird_egg", "B")
    rules.apply_action(s, PlaceAction("tiger", ("cr", "2,2")))
    assert s.top_unit("2,2").card_id == "tiger" and "bird_egg" in s.remove_pile


# ====================================================== Stage 2.3: "Costs X food" (dec. F)

def test_food_cost_gates_placement_and_is_paid():
    s = make_state(hands={"A": ["cairn"]}, food={"A": 14, "B": 0})
    assert not [a for a in rules.legal_actions(s) if a.card_id == "cairn"]      # 14 < 15
    s.food["A"] = 15
    assert [a for a in rules.legal_actions(s) if a.card_id == "cairn"]          # now affordable
    rules.apply_action(s, PlaceAction("cairn", ("cr", "1,2")))
    assert s.food["A"] == 0                              # 15 paid on placement


# ============================== timed effects vs the stack (rules overview.md 9.1, ruled 2026-07-15)
#
# A pending timer advances ONLY while its unit is the top of its crossroad; removal cancels it
# outright; bounce resets it. Before this ruling the scheduler booked an absolute fire-turn and
# mostly forgot the unit - Chipmunk/Black Bear/Chinchilla paid out even when destroyed, and Grizzly
# Bear struck from under a stack. See docs/rules/timed-effect-ruling.md.

def _tick(s, player="A"):
    """Advance `player`'s timers exactly as the turn loop does, and resolve what fires."""
    effects.start_of_turn(s, player)
    effects.resolve(s)


def _pending(s, op):
    return [x for x in s.scheduled if x["step"]["op"] == op]


def test_sloth_schedules_a_delayed_food_payout():
    s = make_state(hands={"A": ["sloth"], "B": ["lion"]})
    rules.apply_action(s, PlaceAction("sloth", ("cr", "1,2")))
    sched = _pending(s, "gain_food")
    assert len(sched) == 1
    assert sched[0]["step"]["amount"] == CFG.sloth_food
    assert sched[0]["remaining"] == CFG.sloth_delay
    assert sched[0]["iid"] == s.top_unit("1,2").iid      # the timer belongs to the unit


def test_sloth_pays_out_after_its_delay_when_left_uncovered():
    s = make_state(hands={"A": ["sloth"], "B": ["lion"]})
    rules.apply_action(s, PlaceAction("sloth", ("cr", "1,2")))
    food_before = s.food["A"]
    for _ in range(CFG.sloth_delay - 1):
        _tick(s)
        assert s.food["A"] == food_before               # not due yet
    _tick(s)
    assert s.food["A"] == food_before + CFG.sloth_food
    assert not _pending(s, "gain_food")                  # fired and dropped
    sloth = s.board["1,2"][-1]
    assert [e.get("cause_iid") for e in s.events if e["e"] == "food" and not e.get("income")] == [sloth.iid]   # its food flies from it


def test_timer_is_suspended_while_the_unit_is_buried():
    s = make_state(hands={"A": ["sloth"], "B": ["lion"]})
    rules.apply_action(s, PlaceAction("sloth", ("cr", "1,2")))
    food_before = s.food["A"]
    put(s, "1,2", "lion", "B")                           # cover the str-3 Sloth with a str-7
    for _ in range(CFG.sloth_delay + 3):                 # well past its delay
        _tick(s)
    assert s.food["A"] == food_before                    # buried: never paid out
    assert _pending(s, "gain_food")[0]["remaining"] == CFG.sloth_delay  # and never ticked


def test_timer_resumes_when_the_unit_is_uncovered():
    s = make_state(hands={"A": ["sloth"], "B": ["lion"]})
    rules.apply_action(s, PlaceAction("sloth", ("cr", "1,2")))
    food_before = s.food["A"]
    put(s, "1,2", "lion", "B")
    _tick(s)                                             # suspended
    s.board["1,2"].pop()                                 # remove the coverer; Sloth resurfaces
    for _ in range(CFG.sloth_delay):
        _tick(s)
    assert s.food["A"] == food_before + CFG.sloth_food    # waited, then resumed


def test_removal_cancels_the_timer_outright():
    s = make_state(hands={"A": ["sloth"], "B": ["lion"]})
    rules.apply_action(s, PlaceAction("sloth", ("cr", "1,2")))
    food_before = s.food["A"]
    effects._remove_specific(s, "1,2", s.top_unit("1,2"), by_player="B", by_effect=False)
    for _ in range(CFG.sloth_delay + 1):
        _tick(s)
    assert s.food["A"] == food_before
    assert not _pending(s, "gain_food")                  # cancelled and pruned


def test_bounce_resets_the_timer():
    """A bounced unit returns as a fresh instance, so replaying it starts a new timer."""
    s = make_state(hands={"A": ["sloth"], "B": ["lion"]})
    rules.apply_action(s, PlaceAction("sloth", ("cr", "1,2")))
    first_iid = s.top_unit("1,2").iid
    _tick(s)                                             # burn one turn off the timer
    assert _pending(s, "gain_food")[0]["remaining"] == CFG.sloth_delay - 1

    effects._remove_specific(s, "1,2", s.top_unit("1,2"), by_player="B", by_effect=False)
    s.add_to_hand("A", "sloth")   # bounce: off the board, back to hand
    s.current = "A"               # placing ended A's turn; hand it back so A can replay the Sloth
    rules.apply_action(s, PlaceAction("sloth", ("cr", "1,2")))
    live = [x for x in _pending(s, "gain_food") if x["iid"] == s.top_unit("1,2").iid]
    assert s.top_unit("1,2").iid != first_iid            # a new instance
    assert live[0]["remaining"] == CFG.sloth_delay       # full timer, not the partly-elapsed one


def test_chipmunk_no_longer_pays_out_after_it_is_destroyed():
    """The 2026-07-12 finding ("chipmunk works when covered as well?"), now ruled: Chipmunk
    scheduled its second payout with no reference to its unit, so it fired even when destroyed."""
    s = make_state(hands={"A": ["chipmunk"]})
    rules.apply_action(s, PlaceAction("chipmunk", ("cr", "1,2")))
    food_after_roar = s.food["A"]
    effects._remove_specific(s, "1,2", s.top_unit("1,2"), by_player="B", by_effect=False)
    _tick(s)
    assert s.food["A"] == food_after_roar           # no second helping


# ====================================== Stage 2.3: extra placements (decision F1) + twins

def test_mole_plays_another_unit_adjacent_to_it():
    s = make_state(current="A", hands={"A": ["mole", "lion"]})
    rules.apply_action(s, PlaceAction("mole", ("cr", "1,2")))
    assert s.pending is not None and s.pending["mode"] == "place"
    assert {tuple(p["target"]) for p in s.pending["placements"]} == {("cr", "1,1"), ("cr", "1,3"), ("cr", "2,2")}
    rules.apply_action(s, PlaceAction("lion", ("cr", "1,1")))
    assert s.owner_of("1,2") == "A" and s.owner_of("1,1") == "A" and s.hands["A"] == []


def test_ocelot_extra_play_is_gated_on_another_cat():
    with_cat = make_state(current="A", hands={"A": ["ocelot", "lion"]})
    put(with_cat, "1,3", "caracal", "A")                # already control another Cat
    rules.apply_action(with_cat, PlaceAction("ocelot", ("cr", "1,2")))
    assert with_cat.pending is not None                 # may play one more Cat

    no_cat = make_state(current="A", hands={"A": ["ocelot", "lion"]})
    rules.apply_action(no_cat, PlaceAction("ocelot", ("cr", "1,2")))
    assert no_cat.pending is None and "lion" in hand_ids(no_cat, "A")   # no extra play


def test_termite_queen_plays_a_non_queen_colony_animal():
    s = make_state(current="A", hands={"A": ["termite_queen", "worker_ant", "queen_bee", "lion"]})
    rules.apply_action(s, PlaceAction("termite_queen", ("cr", "1,2")))
    assert s.pending is not None and not s.pending["optional"]
    assert {a.card_id for a in rules.legal_actions(s) if isinstance(a, PlaceAction)} == {"worker_ant"}


def test_prince_leo_plays_the_twin_from_deck():
    s = make_state(current="A", hands={"A": ["lion_legend"]},
                   decks={"A": ["lion_legend_2", "lion"], "B": []})
    rules.apply_action(s, PlaceAction("lion_legend", ("cr", "1,2")))
    assert s.pending is not None and not s.pending["optional"]   # must play Princess Lea
    rules.apply_action(s, PlaceAction("lion_legend_2", ("cr", "1,1")))
    assert s.top_unit("1,1").card_id == "lion_legend_2"
    assert "lion_legend_2" not in s.decks["A"]            # fetched from the deck


# ============================== Stage 2.3: HQ-adjacency draw (F6) + start-of-turn (goose_legend)

def test_cheetah_draws_when_placed_next_to_enemy_base():
    s = make_state(current="A", hands={"A": ["cheetah"]}, decks={"A": ["lion"], "B": []})
    for cr in ("1,2", "2,2", "3,2"):                    # chain up to B's front column
        put(s, cr, "caracal", "A")
    rules.apply_action(s, PlaceAction("cheetah", ("cr", "4,2")))   # 4,2 is HQ_B's front
    assert len(s.hands["A"]) == 1


def test_legendary_bat_draws_at_the_start_of_its_owners_turn():
    s = make_state(current="A", decks={"A": ["lion", "fox", "rat"], "B": ["lynx", "lynx"]})
    put(s, "1,2", "bat_legend", "A")
    rules.apply_action(s, DrawAction())                 # A's turn ends
    hand_a = len(s.hands["A"])
    rules.apply_action(s, DrawAction())                 # B's turn ends -> start of A's turn
    assert len(s.hands["A"]) == hand_a + 1              # the Bat drew


# ============================================ Stage 2.4: removal roars / reactive

def test_jaguar_removes_a_4_but_not_a_5():
    four = make_state(hands={"A": ["jaguar"]})
    put(four, "1,2", "lion", "A")
    put(four, "3,2", "deer", "B")                               # str 4: in reach
    apply_click(four, PlaceAction("jaguar", ("cr", "2,2")))
    assert four.owner_of("3,2") is None

    five = make_state(hands={"A": ["jaguar"]})
    put(five, "1,2", "lion", "A")
    put(five, "3,2", "jaguar", "B")                             # str 5: out of reach
    apply_click(five, PlaceAction("jaguar", ("cr", "2,2")))
    assert five.owner_of("3,2") == "B"


def test_jaguar_and_honey_badger_respect_strength_bounds():
    jag = make_state(hands={"A": ["jaguar"]})
    put(jag, "1,2", "lion", "A")
    put(jag, "3,2", "tuna", "B")                      # str 3 <= 4
    apply_click(jag, PlaceAction("jaguar", ("cr", "2,2")))
    assert jag.owner_of("3,2") is None

    big = make_state(hands={"A": ["jaguar"]})
    put(big, "1,2", "lion", "A")
    put(big, "3,2", "wolf", "B")                   # str 6 > 4: out of reach
    apply_click(big, PlaceAction("jaguar", ("cr", "2,2")))
    assert big.owner_of("3,2") == "B"

    srv = make_state(hands={"A": ["honey_badger"]})
    put(srv, "1,2", "lion", "A")
    put(srv, "3,2", "lion", "B")                        # str 7 >= 6 (the Honey Badger's only legal target)
    put(srv, "2,3", "tuna", "B")                      # str 3 < 6: survives
    apply_click(srv, PlaceAction("honey_badger", ("cr", "2,2")))
    assert srv.owner_of("3,2") is None and srv.owner_of("2,3") == "B"


def test_soldier_ant_removal_gated_on_four_colony():
    few = make_state(hands={"A": ["soldier_ant"]})
    put(few, "1,2", "worker_ant", "A")
    put(few, "1,3", "worker_ant", "A")
    put(few, "3,2", "tuna", "B")
    apply_click(few, PlaceAction("soldier_ant", ("cr", "2,2")))   # only 3 Colony incl. Soldier
    assert few.owner_of("3,2") == "B"

    many = make_state(hands={"A": ["soldier_ant"]})
    for cr in ("1,1", "1,2", "1,3"):
        put(many, cr, "worker_ant", "A")               # 3 + Soldier = 4 Colony
    put(many, "3,2", "tuna", "B")
    apply_click(many, PlaceAction("soldier_ant", ("cr", "2,2")))
    assert many.owner_of("3,2") is None


def test_rhinoceros_sweeps_only_small_adjacent_enemies():
    s = make_state(hands={"A": ["rhinoceros"]})
    put(s, "1,2", "lion", "A")
    put(s, "3,2", "tuna", "B")                          # 3 - removed (<= 3)
    put(s, "2,3", "warthog", "B")                       # 4 - survives
    put(s, "2,1", "lion", "B")                          # 7 - survives
    rules.apply_action(s, PlaceAction("rhinoceros", ("cr", "2,2")))
    assert s.owner_of("3,2") is None
    assert s.owner_of("2,3") == "B" and s.owner_of("2,1") == "B"


def test_brutus_removes_one_adjacent_enemy_of_any_strength():
    s = make_state(hands={"A": ["rhinoceros_legend"]}, food={"A": 20, "B": 0})
    put(s, "1,2", "caracal", "A")                       # friendly - connects 2,2, untouched
    put(s, "3,2", "elephant", "B")                      # 9 - the horn has no cap
    put(s, "2,1", "mouse", "B")                         # the other target, left alone
    apply_click(s, PlaceAction("rhinoceros_legend", ("cr", "2,2")))
    assert s.pending and s.pending.get("options")       # two enemies: the player picks
    rules.apply_action(s, ChoiceAction("3,2"))
    assert s.owner_of("3,2") is None and s.owner_of("2,1") == "B" and s.owner_of("1,2") == "A"


def test_hippopotamus_removes_a_weak_enemy_placed_adjacent():
    s = make_state(current="B", hands={"B": ["tuna"]})
    put(s, "3,2", "hippopotamus", "A")
    put(s, "4,1", "caracal", "B")                       # B front, connects 3,1
    rules.apply_action(s, PlaceAction("tuna", ("cr", "3,1")))  # str 3 <= 3, adjacent to hippo
    assert s.owner_of("3,1") is None


# =================================================== Stage 2.4: hand-cost / sacrifice removal

def test_hornet_saccs_a_spare_copy_to_destroy_an_enemy():
    s = make_state(hands={"A": ["hornet", "hornet"]})
    put(s, "1,2", "caracal", "A")
    put(s, "3,2", "lion", "B")
    rules.apply_action(s, PlaceAction("hornet", ("cr", "2,2")))
    rules.apply_action(s, ChoiceAction("3,2"))
    assert s.owner_of("3,2") is None and s.owner_of("2,2") == "A"   # hornet itself survives
    assert s.remove_pile == ["hornet", "lion"] and hand_ids(s, "A") == []  # spare paid, target killed


def test_hornet_has_no_effect_without_a_spare_copy():
    s = make_state(hands={"A": ["hornet"]})
    put(s, "1,2", "caracal", "A")
    put(s, "3,2", "lion", "B")
    rules.apply_action(s, PlaceAction("hornet", ("cr", "2,2")))
    assert s.pending is None                            # no spare in hand or deck -> no offer
    assert s.owner_of("3,2") == "B"



def test_hornet_removes_nothing_when_its_spare_is_gone_before_the_roar_resolves():
    s = make_state(hands={"A": ["hornet"]}, decks={"A": ["hornet"], "B": []})
    put(s, "1,2", "caracal", "A")
    put(s, "3,2", "lion", "B")
    rules.apply_action(s, PlaceAction("hornet", ("cr", "2,2")))
    s.decks["A"].remove("hornet")                       # the spare leaves the deck while the Roar waits
    rules.apply_action(s, ChoiceAction("3,2"))
    assert s.owner_of("3,2") == "B" and s.remove_pile == []   # nothing to discard, so nothing removed

# ================================================================ Stage 2.4: mass effects

def test_pestis_wipes_an_adjacent_enemy_and_everything_under_it():
    s = make_state(hands={"A": ["rat_legend_2"]})
    put(s, "1,2", "caracal", "A")
    put(s, "3,2", "lion", "B")                          # bottom
    put(s, "3,2", "tuna", "B")                        # top (same owner stacks freely)
    rules.apply_action(s, PlaceAction("rat_legend_2", ("cr", "2,2")))
    rules.apply_action(s, ChoiceAction("3,2"))            # the enemy stack
    assert s.board.get("3,2") is None
    assert s.remove_pile.count("lion") == 1 and s.remove_pile.count("tuna") == 1


def test_pestis_next_to_only_allies_must_wipe_one():
    # A Roar's cost is never declined (Martin, 2026-10-21): next to its own animals only, the Pestis wipes one of them.
    s = make_state(hands={"A": ["rat_legend_2"]})
    put(s, "1,2", "caracal", "A")                       # the only adjacent animal is an ally
    rules.apply_action(s, PlaceAction("rat_legend_2", ("cr", "2,2")))
    assert not s.pending["optional"]
    with pytest.raises(EngineError):
        rules.apply_action(s, ChoiceAction(SKIP))
    rules.apply_action(s, ChoiceAction("1,2"))
    assert s.top_unit("1,2") is None


def test_sirocco_bounces_all_adjacent_enemies_to_hand():
    s = make_state(hands={"A": ["skunk_legend"]})
    put(s, "1,2", "caracal", "A")
    put(s, "3,2", "tuna", "B")
    put(s, "2,3", "fox", "B")
    rules.apply_action(s, PlaceAction("skunk_legend", ("cr", "2,2")))
    assert s.owner_of("3,2") is None and s.owner_of("2,3") is None
    assert {"tuna", "fox"} <= set(hand_ids(s, "B")) and "tuna" not in s.remove_pile


def test_skunk_bounces_and_locks_the_card():
    s = make_state(current="A", hands={"A": ["skunk"]})
    put(s, "1,2", "caracal", "A")
    put(s, "3,2", "tuna", "B")
    apply_click(s, PlaceAction("skunk", ("cr", "2,2")))
    tuna = next(u for u in s.hands["B"] if u.card_id == "tuna")
    assert tuna.locked_until_turn == 4                # placed on turn 2: locked through B's next turn
    assert "tuna" not in {a.card_id for a in rules.legal_actions(s) if isinstance(a, PlaceAction)}


# ============================================================= Stage 2.4: team triggers

def test_king_theron_and_queen_adira_combo_on_a_cat_cover():
    s = make_state(current="A", hands={"A": ["lion"]}, decks={"A": ["fox", "rat"], "B": []})
    put(s, "1,1", "lion_legend_3", "A")
    put(s, "1,3", "lion_legend_4", "A")
    put(s, "1,2", "caracal", "A")                       # connects 2,2
    put(s, "2,2", "tuna", "B")                        # a Cat (lion) will cover this enemy
    rules.apply_action(s, PlaceAction("lion", ("cr", "2,2")))
    assert s.owner_of("2,2") == "A" and "tuna" in s.remove_pile    # Theron removed it
    assert len(s.hands["A"]) == 1                       # Adira drew off the Cat removal


# =============================================== Stage 2.4: food gains / play & food riders

def test_bumbleton_rider_lands_on_a_colony_roar():
    s = make_state(current="A", hands={"A": ["worker_bee"]})
    put(s, "1,3", "bumblebee_legend", "A")                      # +3 whenever you gain food
    put(s, "1,2", "caracal", "A")
    rules.apply_action(s, PlaceAction("worker_bee", ("cr", "2,2")))
    assert s.food["A"] == CFG.worker_bee_food + CFG.bumblebee_legend_food_rider


def test_queen_solenia_pays_at_dusk_for_every_animal_you_control():
    s = make_state(current="A", decks={"A": ["lion"], "B": ["lynx"]})
    put(s, "1,1", "worker_ant", "A")
    put(s, "1,3", "caracal", "A")                    # any animal counts, not only Colony
    put(s, "1,2", "army_ant_legend", "A")
    s.actions_taken_this_turn = s.config.actions_per_turn - 1
    rules.apply_action(s, DrawAction())
    assert s.food["A"] == 3 * CFG.army_ant_legend_per   # herself and two others


def test_queen_melissia_draws_one_of_each_caste():
    deck = ["lion", "worker_bee", "guard_wasp", "nurse_bee", "queen_bee", "lion"]
    s = make_state(current="A", hands={"A": ["bee_legend"]}, decks={"A": deck, "B": []})
    rules.apply_action(s, PlaceAction("bee_legend", ("cr", "1,2")))
    assert sorted(hand_ids(s, "A")) == ["guard_wasp", "nurse_bee", "worker_bee"]


def test_chipmunk_pays_now_and_next_turn():
    s = make_state(current="A", hands={"A": ["chipmunk"]},
                   decks={"A": ["lion"], "B": ["lynx", "lynx"]})
    s.actions_taken_this_turn = s.config.actions_per_turn - 1  # Place ends A's turn
    rules.apply_action(s, PlaceAction("chipmunk", ("cr", "1,2")))
    assert s.food["A"] == CFG.chipmunk_food_now
    s.actions_taken_this_turn = s.config.actions_per_turn - 1  # Draw ends B's turn -> start of A's next
    rules.apply_action(s, DrawAction())                 # B's turn -> start of A's next turn
    assert s.food["A"] == CFG.chipmunk_food_now + CFG.chipmunk_food_later


def test_methuselah_gains_food_at_end_of_turn():
    s = make_state(current="A", decks={"A": ["lion"], "B": ["lynx"]})
    put(s, "1,1", "tortoise_legend", "A")
    s.actions_taken_this_turn = s.config.actions_per_turn - 1
    rules.apply_action(s, DrawAction())
    assert s.food["A"] == CFG.tortoise_legend_food


# ===================================================== Stage 2.4: conditional / delayed / reveal

def test_bobcat_draws_only_with_another_cat():
    s = make_state(current="A", hands={"A": ["bobcat"]}, decks={"A": ["lion"], "B": []})
    put(s, "1,1", "caracal", "A")                       # another Cat
    rules.apply_action(s, PlaceAction("bobcat", ("cr", "1,2")))
    assert len(s.hands["A"]) == 1


def test_black_bear_schedules_a_delayed_draw():
    s = make_state(hands={"A": ["black_bear"]}, decks={"A": ["lion"], "B": []})
    rules.apply_action(s, PlaceAction("black_bear", ("cr", "1,2")))
    sched = [x for x in s.scheduled if x["step"]["op"] == "draw" and x["owner"] == "A"]
    assert sched                                        # a delayed draw was queued
    effects._op_draw(s, sched[0]["step"])               # fire it: pulls from the deck
    assert "lion" in hand_ids(s, "A")




def test_scrooge_gains_3_for_each_10_food_you_have():
    s = make_state(current="A", hands={"A": ["chipmunk_legend"]}, food={"A": 67, "B": 0})
    rules.apply_action(s, PlaceAction("chipmunk_legend", ("cr", "1,2")))
    assert s.food["A"] == 67 + 6 * CFG.chipmunk_legend_food_per     # 67 is six whole tens


def test_andean_condor_draws_only_when_its_top_is_stronger():
    win = make_state(hands={"A": ["andean_condor"]}, decks={"A": ["lion"], "B": ["tuna"]})
    rules.apply_action(win, PlaceAction("andean_condor", ("cr", "1,2")))
    assert "lion" in hand_ids(win, "A")

    lose = make_state(hands={"A": ["andean_condor"]}, decks={"A": ["tuna"], "B": ["lion"]})
    rules.apply_action(lose, PlaceAction("andean_condor", ("cr", "1,2")))
    assert lose.hands["A"] == []


def test_oxpecker_counts_strong_units_in_the_starting_deck():
    s = make_state(hands={"A": ["oxpecker"]})
    s.starting_decks["A"] = ("elephant", "rhinoceros_legend", "lion", "squirrel", "python")  # 9,8 qualify; 7,3,dyn don't
    rules.apply_action(s, PlaceAction("oxpecker", ("cr", "1,2")))
    assert s.food["A"] == 2


# ============================================ Snake/Bird control (2026-09-26 redesign)

def test_viper_permanently_shrinks_an_adjacent_enemy_so_a_bird_can_cover_it():
    s = make_state(hands={"A": ["viper", "eagle"]})
    put(s, "2,1", "lion", "B")                            # a 7: Eagle (5) can't cover it
    assert PlaceAction("eagle", ("cr", "2,1")) not in rules.legal_actions(s)
    apply_click(s, PlaceAction("viper", ("cr", "1,1")))        # bites the Lion: 7 -> 4
    assert effective_strength(s, s.top_unit("2,1")) == 4
    apply_click(s, PlaceAction("eagle", ("cr", "2,1")))
    assert s.owner_of("2,1") == "A"


def test_king_cobra_venom_removes_the_bitten_unit_next_turn_even_if_buried_or_the_cobra_is_gone():
    s = make_state(hands={"A": ["cottonmouth"], "B": ["tiger"]},
                   decks={"A": ["eagle"] * 8, "B": ["eagle"] * 8})
    put(s, "2,1", "lion", "B")
    apply_click(s, PlaceAction("cottonmouth", ("cr", "1,1")))  # bites the Lion at 2,1
    lion = s.top_unit("2,1")
    assert lion.card_id == "lion"
    apply_click(s, DrawAction())                   # A ends the turn
    put(s, "1,1", "lion", "B")                            # the cobra is covered...
    put(s, "2,1", "tiger", "B")                           # ...and the Lion buried under B's own Tiger
    apply_click(s, DrawAction()); apply_click(s, DrawAction())   # B's turn
    assert "lion" in s.remove_pile and s.top_unit("2,1").card_id == "tiger"


def test_the_swarming_rat_removes_an_adjacent_enemy_of_any_strength_and_keeps_the_hand():
    s = make_state(hands={"A": ["rat", "lion", "eagle"]})
    put(s, "2,1", "lion_legend_3", "B")                     # an 8: Rat reaches any strength
    s.units_placed_this_turn = 2                            # the Rat is the turn's third animal
    apply_click(s, PlaceAction("rat", ("cr", "1,1")))
    assert s.top_unit("2,1") is None and "lion_legend_3" in s.remove_pile
    assert len(s.hands["A"]) == 2                           # no discard any more


def test_queen_adira_uncovered_by_the_removal_does_not_draw():
    # Martin's game 2026-09-28: Tiger ate the Grizzly (then a 1) sitting on Queen Adira; she was buried when
    # it was removed, so she must not see that removal (then the Tiger buries her again).
    s = make_state(hands={"A": ["tiger"]}, decks={"A": ["lion", "lion"], "B": []})
    put(s, "1,2", "lion_legend_4", "A")
    put(s, "1,2", "mouse", "B")                         # covers Adira
    rules.apply_action(s, PlaceAction("tiger", ("cr", "1,2")))
    assert [u.card_id for u in s.board["1,2"]] == ["lion_legend_4", "tiger"]
    assert len(s.hands["A"]) == 0                        # no Adira draw


def test_queen_adira_on_top_still_draws_for_a_cat_removal():
    s = make_state(hands={"A": ["tiger"]}, decks={"A": ["lion", "lion"], "B": []})
    put(s, "1,2", "lion_legend_4", "A")                   # visible, connects 2,2
    put(s, "2,2", "mouse", "B")
    rules.apply_action(s, PlaceAction("tiger", ("cr", "2,2")))
    assert len(s.hands["A"]) == 1


def test_eon_eats_then_shuffles_itself_back_one_smaller_each_cycle():
    s = make_state(hands={"A": ["anaconda_legend"]}, decks={"A": ["lion"] * 6, "B": ["lion"] * 6})
    put(s, "1,1", "caracal", "A")
    put(s, "2,1", "lion_legend_3", "B")                     # an 8: Eon (10) lands on it and eats it
    rules.apply_action(s, PlaceAction("anaconda_legend", ("cr", "2,1")))
    assert "lion_legend_3" in s.remove_pile and s.top_unit("2,1").card_id == "anaconda_legend"
    rules.apply_action(s, DrawAction())                   # A's turn ends: Eon leaves
    assert s.top_unit("2,1") is None and "anaconda_legend" in s.decks["A"] and "anaconda_legend" not in s.remove_pile
    assert card_strength(s, "anaconda_legend", "A") == 10 - CFG.anaconda_legend_decay


def test_eon_shrunk_to_nothing_is_removed_instead_of_looping():
    s = make_state(hands={"A": ["anaconda_legend"]}, decks={"A": ["lion"] * 6, "B": ["lion"] * 6})
    s.card_strength_counters["A"] = {"anaconda_legend": CFG.anaconda_legend_decay - 10}   # an Eon at its last strength
    put(s, "1,1", "caracal", "A")
    rules.apply_action(s, PlaceAction("anaconda_legend", ("cr", "1,1")))   # onto its own animal, as the endless loop did
    rules.apply_action(s, DrawAction())                   # A's turn ends: one more cycle would make it 0
    assert "anaconda_legend" in s.remove_pile and "anaconda_legend" not in s.decks["A"]


def test_magpie_takes_a_random_enemy_card_then_discards_one_of_yours():
    s = make_state(hands={"A": ["magpie", "mouse"], "B": ["lion"]},
                   decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    rules.apply_action(s, PlaceAction("magpie", ("cr", "1,1")))
    assert s.hands["B"] == []                              # the Lion was taken
    rules.apply_action(s, ChoiceAction(next(u.iid for u in s.hands["A"] if u.card_id == "mouse")))
    assert hand_ids(s, "A") == ["lion"] and "mouse" in s.remove_pile and "mouse" not in s.decks["A"]
    assert all(u.owner == "A" for u in s.hands["A"])


def test_black_mamba_removes_an_adjacent_enemy_of_strength_6_or_less():
    s = make_state(hands={"A": ["black_mamba"]})
    put(s, "2,1", "jaguar", "B")                          # a 6: in reach
    apply_click(s, PlaceAction("black_mamba", ("cr", "1,1")))
    assert "jaguar" in s.remove_pile

    s2 = make_state(hands={"A": ["black_mamba"]})
    put(s2, "2,1", "lion", "B")                           # a 7: out of reach
    apply_click(s2, PlaceAction("black_mamba", ("cr", "1,1")))
    assert s2.top_unit("2,1").card_id == "lion"


def test_guard_wasp_in_hand_does_not_count_itself_toward_four_colony():
    s = make_state(hands={"A": ["guard_wasp"]})
    for cr in ("1,1", "1,2", "1,3"):
        put(s, cr, "worker_ant", "A")                    # 3 Colony on the board
    assert card_strength(s, "guard_wasp", "A") == GW   # not yet controlled: no bonus to cover with
    put(s, "2,1", "worker_ant", "A")
    assert card_strength(s, "guard_wasp", "A") == GW + CFG.guard_hornet_bonus


def test_falstaffs_extra_food_is_its_own_doing():
    # The client flies a gain's fruit from the animal whose doing it is: Falstaff's extra flies from Falstaff, even after
    # region income or another animal's Roar (Martin, 2026-10-15).
    s = make_state(food={"A": 0, "B": 0})
    put(s, "1,1", "bumblebee_legend", "A")
    effects.gain_food(s, "A", 5, income=True)
    rider = [e for e in s.events if e["e"] == "food" and not e.get("income")]
    assert [(e["cause"], e["cause_iid"]) for e in rider] == [("bumblebee_legend", s.board["1,1"][-1].iid)]


def test_queen_bee_makes_the_chosen_bee_in_hand():
    s = make_state(current="A", hands={"A": ["queen_bee"]}, decks={"A": [], "B": []})
    rules.apply_action(s, PlaceAction("queen_bee", ("cr", "1,2")))
    assert sorted(s.pending["options"]) == ["guard_bee", "nurse_bee", "worker_bee"]
    rules.apply_action(s, ChoiceAction("nurse_bee"))
    assert hand_ids(s, "A") == ["nurse_bee"] and s.decks["A"] == []
