"""Keyword audit (2026-11-05): how the keywords behave where they meet each other and each kind of removal.

The per-card audits beside this file check each card's own text; these check the meetings: Armor against every kind
of removal, Stealth against every chosen effect, a Flight or Roam landing next to a trap, a Flee animal covered by each
kind of unit, an Apex Predator eating each keyword, Hungry, Titan, Wild timers, Dawn and Dusk, Fall from each cause, a
doubled Roar. Each assertion is read off docs/rules/keywords.md, overview.md and rulings.md, never off the effect code.
The results are recorded line by line in knowledge/audit/keywords-meet-2026-11-05.md.

Map A (the test fixture): a 4x3 grid, A's den fronts column 1 ("1,1" "1,2" "1,3"), B's column 4; orthogonal
neighbours, so "2,2" neighbours "1,2", "3,2", "2,1", "2,3". Region R1 = 1,1 2,1 1,2 2,2 (10 food).
Only real cards: blank bodies are the Lion (7), the Pigeon (5, Flight), the Chinchilla (4), the Muskrat (3), the
Jerboa (2) and the Lemming (1).
"""

from __future__ import annotations

import pytest

from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import ChoiceAction, PassAction, PlaceAction, RoamAction
from animal_kingdom.engine.state import WILD
from animal_kingdom.engine.strength import effective_strength

from .._helpers import hand_ids, make_state, place_targets, put

FILLER = ["lion"] * 8


def st(**kw):
    kw.setdefault("decks", {"A": FILLER[:], "B": FILLER[:]})
    return make_state(**kw)


def end_turn(s):
    s.idle_turns = 0
    rules.apply_action(s, PassAction())


def choose(s, option):
    assert s.pending is not None and option in s.pending["options"], (option, s.pending)
    rules.apply_action(s, ChoiceAction(option))


def options(s):
    return set(s.pending["options"]) if s.pending else set()


def play(s, card_id, cr):
    rules.apply_action(s, PlaceAction(card_id, ("cr", cr)))


def roam(s, origin, cr):
    rules.apply_action(s, RoamAction(origin, ("cr", cr)))


def legal(s, action):
    return action in rules.legal_actions(s)


def top(s, cr):
    u = s.top_unit(cr)
    return (u.card_id, u.owner) if u else None


def stack(s, cr):
    return [u.card_id for u in s.board.get(cr, [])]


def removed(s, card_id):
    return card_id in s.remove_pile


# ===================================================================================================== Armor
# "cannot be removed, returned to hand, or eaten by any ability, the enemy's or its own controller's. It can still be
# covered ... It still dies if its strength drops below 0."

def test_armor_meets_a_chosen_roar_removal():
    s = st(hands={"A": ["black_mamba"]})                        # remove an adjacent enemy of strength 6 or less
    put(s, "2,2", "tortoise", "B")                              # 6, Armor
    put(s, "2,3", "muskrat", "B")
    play(s, "black_mamba", "1,2")
    assert "2,2" not in options(s)
    assert top(s, "2,2") == ("tortoise", "B")


def test_armor_meets_a_mass_roar_removal():
    s = st(hands={"A": ["rhinoceros"]})                         # remove all adjacent enemies of strength 3 or less
    put(s, "2,2", "tortoise_legend", "B")                       # 3, Armor
    put(s, "1,1", "lemming", "B")
    play(s, "rhinoceros", "1,2")
    assert top(s, "2,2") == ("tortoise_legend", "B")
    assert s.top_unit("1,1") is None


def test_armor_meets_a_remove_all_roar_sperm_whale():
    s = st(hands={"A": ["sperm_whale"]})                        # Titan. Roar: remove all adjacent animals
    put(s, "2,2", "tortoise", "B")
    put(s, "1,1", "stag_beetle", "A")                           # its own controller's ability can't either
    put(s, "1,3", "lion", "A")
    play(s, "sperm_whale", "1,2")
    assert top(s, "2,2") == ("tortoise", "B") and top(s, "1,1") == ("stag_beetle", "A")
    assert s.top_unit("1,3") is None


def test_armor_meets_its_own_controllers_removal_praying_mantis():
    s = st(hands={"A": ["praying_mantis"]})                     # Roar: remove an adjacent ally to draw 2 cards
    put(s, "1,1", "tortoise", "A")                              # the only adjacent ally has Armor: the cost can't be paid
    play(s, "praying_mantis", "1,2")
    if s.pending:
        assert "1,1" not in options(s)
    assert top(s, "1,1") == ("tortoise", "A") and hand_ids(s, "A") == []


def test_armor_meets_a_bounce_skunk():
    s = st(hands={"A": ["skunk"]})                              # Roar: return an adjacent enemy to its owner's hand
    put(s, "2,2", "tortoise", "B")
    play(s, "skunk", "1,2")
    assert "2,2" not in options(s)
    assert top(s, "2,2") == ("tortoise", "B") and hand_ids(s, "B") == []


def test_armor_meets_its_own_controllers_return_opossum():
    s = st(hands={"A": ["opossum"]})                            # Roar: return an adjacent ally to your hand
    put(s, "1,1", "stag_beetle", "A")
    play(s, "opossum", "1,2")
    assert "1,1" not in options(s)
    assert top(s, "1,1") == ("stag_beetle", "A")


def test_armor_meets_an_apex_predator_it_is_covered_not_eaten():
    s = st(hands={"A": ["tiger"]})
    put(s, "1,2", "tortoise", "B")                              # 6 < 7
    play(s, "tiger", "1,2")
    assert stack(s, "1,2") == ["tortoise", "tiger"] and not removed(s, "tortoise")


def test_armor_meets_spikes_the_armor_coverer_stays_and_the_spikes_are_spent():
    s = st(hands={"A": ["tortoise"]})
    hh = put(s, "1,2", "hedgehog", "B")                         # 5 < 6
    play(s, "tortoise", "1,2")
    assert top(s, "1,2") == ("tortoise", "A") and not removed(s, "tortoise")
    assert hh.retaliation_used                                  # "the Spikes are gone all the same"


def test_armor_meets_poison_the_armor_coverer_survives():
    s = st(hands={"A": ["tortoise"]})
    put(s, "1,2", "toad", "B")                                  # 5 < 6, Poison
    play(s, "tortoise", "1,2")
    end_turn(s)                                                 # B's turn starts: the poison would remove it
    assert top(s, "1,2") == ("tortoise", "A") and not removed(s, "tortoise")


def test_armor_meets_a_trap_hippopotamus():
    s = st(hands={"A": ["stag_beetle"]})                        # 4: the Hippo removes enemies of 4 or less placed next to it
    put(s, "2,2", "hippopotamus", "B")
    play(s, "stag_beetle", "1,2")
    assert top(s, "1,2") == ("stag_beetle", "A")


def test_armor_meets_a_trap_boar():
    s = st(hands={"A": ["tortoise", "lion"]})
    put(s, "2,2", "boar", "B")                                  # remove the first enemy placed next to this
    play(s, "tortoise", "1,2")
    assert top(s, "1,2") == ("tortoise", "A")


def test_armor_meets_a_trap_golden_orb_weaver_via_the_armadillo():
    s = st(hands={"A": ["pigeon"]})                             # Flight: the Orb-Weaver removes it, unless it has Armor
    put(s, "3,2", "golden_orb_weaver", "B")
    put(s, "3,1", "armadillo", "A")                             # your adjacent animals have Armor
    play(s, "pigeon", "2,1")                                    # next to both
    assert top(s, "2,1") == ("pigeon", "A")


def test_armor_meets_fall_dart_frog():
    s = st(hands={"B": ["black_mamba"]}, current="B")
    put(s, "2,2", "dart_frog", "A")                             # Fall: remove all animals next to this
    put(s, "1,2", "tortoise", "A")
    put(s, "2,1", "lion", "A")
    put(s, "3,2", "lion", "B")
    put(s, "4,3", "lion", "B")
    put(s, "3,3", "lion", "B")
    play(s, "black_mamba", "2,3")
    choose(s, "2,2")
    assert top(s, "1,2") == ("tortoise", "A")
    assert s.top_unit("2,1") is None and s.top_unit("3,2") is None


def test_armor_meets_a_plague_rat_legend_2_skips_a_buried_armor_in_place():
    s = st(hands={"A": ["rat_legend_2"]})                       # remove an adjacent animal and every animal under it
    put(s, "2,2", "lemming", "B")
    put(s, "2,2", "tortoise", "B")
    put(s, "2,2", "lion", "B")
    play(s, "rat_legend_2", "1,2")
    choose(s, "2,2")
    assert stack(s, "2,2") == ["tortoise"]


def test_armor_meets_a_plague_rat_legend_2_cannot_choose_an_armor_top():
    s = st(hands={"A": ["rat_legend_2"]})
    put(s, "2,2", "lemming", "B")
    put(s, "2,2", "tortoise", "B")
    put(s, "1,1", "lion", "B")
    play(s, "rat_legend_2", "1,2")
    assert "2,2" not in options(s)


def test_armor_meets_dying_below_zero():
    s = st(hands={"B": ["viper", "mosquito"]}, current="B")     # -3, then -2
    put(s, "4,1", "lion", "B")
    put(s, "3,2", "tortoise_legend", "A")                       # 3, Armor
    play(s, "viper", "3,1")
    if s.pending:
        choose(s, "3,2")
    assert top(s, "3,2") == ("tortoise_legend", "A")            # 0: still alive
    play(s, "mosquito", "3,3")
    if s.pending:
        choose(s, "3,2")
    assert s.top_unit("3,2") is None and removed(s, "tortoise_legend")


def test_armor_meets_a_locust_the_swarm_does_not_eat_it():
    s = st(hands={"A": ["locust_legend"]})
    put(s, "2,2", "tortoise", "B")
    put(s, "2,3", "lion", "B")
    play(s, "locust_legend", "1,2")
    end_turn(s); end_turn(s)                                    # B's turn, then A's: the swarm eats
    assert top(s, "2,2") == ("tortoise", "B")
    assert s.top_unit("2,3") is None


def test_armor_meets_the_octopus_ink_loses_it():
    s = st(hands={"A": ["octopus", "black_mamba"]})             # adjacent enemies lose all their effects
    put(s, "2,2", "tortoise", "B")
    put(s, "1,3", "lemming", "A")
    play(s, "octopus", "1,2")
    play(s, "black_mamba", "2,3")
    choose(s, "2,2")
    assert s.top_unit("2,2") is None


def test_armor_meets_a_dawn_removal_tarantula_city_spider():
    s = st()
    put(s, "2,2", "city_spider", "A")                           # Dawn: remove the weakest animal next to this
    put(s, "2,3", "tortoise_legend", "B")                       # 3, Armor: the weakest, excluded
    put(s, "3,2", "chinchilla", "B")                            # 4
    end_turn(s); end_turn(s)
    assert top(s, "2,3") == ("tortoise_legend", "B") and s.top_unit("3,2") is None


def test_armor_meets_a_random_removal_swordfish():
    s = st(hands={"A": ["swordfish"]})                          # a random adjacent enemy for each adjacent allied Fish
    put(s, "1,1", "tuna", "A")                                  # one Fish
    put(s, "2,2", "tortoise", "B")                              # the only adjacent enemy: Armor stays
    play(s, "swordfish", "1,2")
    assert top(s, "2,2") == ("tortoise", "B")


# ==================================================================================================== Stealth
# "Cannot be chosen by an enemy ability. Mass, random, and automatic effects hit it normally, and so does an Apex
# Predator's eat. Its own controller may still choose it freely."

def test_stealth_meets_a_chosen_roar_removal():
    s = st(hands={"A": ["black_mamba"]})
    put(s, "2,2", "stick_insect", "B")                          # 6, Stealth
    put(s, "1,1", "muskrat", "B")
    play(s, "black_mamba", "1,2")
    assert options(s) == {"1,1"}


def test_stealth_meets_a_chosen_bounce_skunk():
    s = st(hands={"A": ["skunk"]})
    put(s, "2,2", "stick_insect", "B")
    put(s, "1,1", "muskrat", "B")
    play(s, "skunk", "1,2")
    assert "2,2" not in options(s)


def test_stealth_meets_a_chosen_strength_loss_mosquito():
    s = st(hands={"A": ["mosquito"]})                           # give an adjacent enemy -2 strength
    si = put(s, "2,2", "stick_insect", "B")
    play(s, "mosquito", "1,2")
    assert "2,2" not in options(s)
    assert effective_strength(s, si) == 6


def test_stealth_meets_a_chosen_plague_rat_legend_2():
    s = st(hands={"A": ["rat_legend_2"]})
    put(s, "2,2", "stick_insect", "B")
    put(s, "1,1", "lemming", "B")
    play(s, "rat_legend_2", "1,2")
    assert "2,2" not in options(s)


def test_stealth_meets_a_chosen_copy_chameleon_legend():
    s = st(hands={"A": ["chameleon_legend"]})                   # choose an adjacent animal, become a copy of it
    put(s, "2,2", "stick_insect", "B")
    put(s, "1,1", "lion", "B")
    play(s, "chameleon_legend", "1,2")
    assert "2,2" not in options(s)


def test_stealth_meets_its_own_controllers_choice_praying_mantis():
    s = st(hands={"A": ["praying_mantis"]})
    put(s, "1,1", "stick_insect", "A")
    play(s, "praying_mantis", "1,2")
    if s.pending:
        choose(s, "1,1")
    assert s.top_unit("1,1") is None and len(s.hands["A"]) == 2


def test_stealth_meets_a_mass_roar_removal_albatross():
    s = st(hands={"A": ["albatross"]})                          # Flight. Roar: remove all adjacent enemies of 3 or less
    put(s, "3,2", "butterfly_legend_chrysalis", "B")            # 0, Stealth
    play(s, "albatross", "3,3")
    assert s.top_unit("3,2") is None


def test_stealth_meets_a_remove_all_roar_sperm_whale():
    s = st(hands={"A": ["sperm_whale"]})
    put(s, "2,2", "stick_insect", "B")
    play(s, "sperm_whale", "1,2")
    assert s.top_unit("2,2") is None


def test_stealth_meets_a_random_removal_swordfish():
    s2 = st(hands={"A": ["swordfish"]})
    put(s2, "1,1", "tuna", "A")
    put(s2, "2,2", "stick_insect", "B")
    play(s2, "swordfish", "1,2")                                # next to the Tuna (1,1) and the Stick Insect (2,2)
    assert s2.top_unit("2,2") is None


def test_stealth_meets_an_apex_predator():
    s = st(hands={"A": ["tiger"]})
    put(s, "1,2", "stick_insect", "B")                          # 6 < 7
    play(s, "tiger", "1,2")
    assert stack(s, "1,2") == ["tiger"] and removed(s, "stick_insect")


def test_stealth_meets_a_trap_hippopotamus():
    s = st(hands={"A": ["butterfly_legend_chrysalis"]})         # 0, Stealth: placed next to the Hippo
    put(s, "2,2", "hippopotamus", "B")
    play(s, "butterfly_legend_chrysalis", "1,2")
    while s.pending:
        rules.apply_action(s, ChoiceAction(s.pending["options"][0]))
    assert s.top_unit("1,2") is None


def test_stealth_meets_a_trap_boar():
    s = st(hands={"A": ["stick_insect"]})
    put(s, "2,2", "boar", "B")
    play(s, "stick_insect", "1,2")
    assert s.top_unit("1,2") is None


def test_stealth_meets_a_dawn_removal_city_spider():
    s = st()
    put(s, "2,2", "city_spider", "A")
    put(s, "2,3", "butterfly_legend_chrysalis", "B")            # 0, Stealth: the weakest
    put(s, "3,2", "chinchilla", "B")
    end_turn(s); end_turn(s)
    assert s.top_unit("2,3") is None and top(s, "3,2") == ("chinchilla", "B")


def test_stealth_meets_the_octopus_ink_reaches_it_and_it_loses_stealth():
    s = st(hands={"A": ["octopus", "black_mamba"]})
    put(s, "2,2", "stick_insect", "B")
    put(s, "1,3", "lemming", "A")
    play(s, "octopus", "1,2")
    play(s, "black_mamba", "2,3")
    assert "2,2" in options(s)


def test_stealth_meets_spikes_a_stealth_coverer_is_removed():
    s = st(hands={"A": ["black_panther"]})                      # 7, Stealth, Apex Predator
    put(s, "1,2", "hedgehog", "B")
    play(s, "black_panther", "1,2")
    assert removed(s, "black_panther") and removed(s, "hedgehog")   # both die (Apex on Spikes)


def test_stealth_meets_poison_a_stealth_coverer_is_removed():
    s = st(hands={"A": ["stick_insect"]})
    put(s, "1,2", "toad", "B")
    play(s, "stick_insect", "1,2")
    end_turn(s)
    assert top(s, "1,2") == ("toad", "B") and removed(s, "stick_insect")


def test_stealth_meets_a_removal_on_the_stealth_animal_the_enemy_cover_still_works():
    s = st(hands={"A": ["lion"]})                               # covering isn't choosing
    put(s, "1,2", "stick_insect", "B")
    assert "1,2" in place_targets(s)


# ===================================================================================================== Flight
# "Can be placed ignoring connection, except onto a den. All other placement rules still apply."

def test_flight_meets_a_trap_hippopotamus_far_from_home():
    s = st(hands={"A": ["pigeon"]})                             # 5 > 4: the Hippo lets it be
    put(s, "3,2", "hippopotamus", "B")
    s2 = st(hands={"A": ["falcon"]})                            # 4: removed
    put(s2, "3,2", "hippopotamus", "B")
    play(s, "pigeon", "3,3")
    play(s2, "falcon", "3,3")
    assert top(s, "3,3") == ("pigeon", "A") and s2.top_unit("3,3") is None


def test_flight_meets_a_trap_boar():
    s = st(hands={"A": ["pigeon"]})
    put(s, "3,2", "boar", "B")
    play(s, "pigeon", "3,3")
    assert s.top_unit("3,3") is None


def test_flight_meets_a_trap_golden_orb_weaver():
    s = st(hands={"A": ["pigeon"]})
    put(s, "3,2", "golden_orb_weaver", "B")                     # an enemy with Flight placed next to this: removed
    play(s, "pigeon", "3,3")
    assert s.top_unit("3,3") is None


def test_flight_meets_a_den_it_lands_next_to_it_but_never_captures():
    s = st(hands={"A": ["pigeon"]})
    assert "4,2" in place_targets(s)                            # a front crossroad of B's den, far from home
    assert not any(isinstance(a, PlaceAction) and a.target[0] == "hq" for a in rules.legal_actions(s))
    play(s, "pigeon", "4,2")
    s.actions_taken_this_turn = 0
    s.hands["A"] = []
    s.add_to_hand("A", "pigeon")
    assert not any(isinstance(a, PlaceAction) and a.target[0] == "hq" for a in rules.legal_actions(s))


def test_flight_meets_armor_it_covers_a_weaker_armor_enemy_not_a_stronger_one():
    s = st(hands={"A": ["pigeon"]})                             # 5
    put(s, "3,2", "stag_beetle", "B")                           # 4, Armor
    put(s, "3,3", "tortoise", "B")                              # 6, Armor
    t = place_targets(s)
    assert "3,2" in t and "3,3" not in t


def test_flight_meets_spikes_guard_bee_covered_by_an_enemy():
    s = st(hands={"A": ["pigeon"]})
    put(s, "3,2", "guard_bee", "B")                             # 3, Flight, Spikes
    play(s, "pigeon", "3,2")
    assert top(s, "3,2") == ("guard_bee", "B") and removed(s, "pigeon")


def test_flight_meets_poison_a_flier_covering_poison_is_removed_next_turn():
    s = st(hands={"A": ["pigeon"]})
    put(s, "3,2", "dart_frog", "B")                             # 1, Poison
    play(s, "pigeon", "3,2")
    assert top(s, "3,2") == ("pigeon", "A")
    end_turn(s)
    assert top(s, "3,2") == ("dart_frog", "B")


def test_flight_meets_flee_a_flier_covers_a_fleer():
    s = st(hands={"A": ["pigeon"]})
    put(s, "3,2", "gazelle", "B")
    play(s, "pigeon", "3,2")
    assert stack(s, "3,2") == ["pigeon"] and "gazelle" in hand_ids(s, "B")


def test_flight_meets_apex_predator_eagle_eats_far_from_home():
    s = st(hands={"A": ["eagle"]})
    put(s, "3,2", "lion", "A")                                  # stranded, its own
    put(s, "3,3", "muskrat", "B")
    t = place_targets(s)
    assert {"3,2", "3,3"} <= t and "2,2" not in t               # never an empty crossroad
    play(s, "eagle", "3,3")
    assert stack(s, "3,3") == ["eagle"] and removed(s, "muskrat")


# ====================================================================================================== Reach
# "up to two crossroads away from one of your connected units ... jumping over whatever stands between ... it never
# captures. All other placement rules still apply."

def test_reach_meets_an_enemy_wall_it_jumps_over_it():
    s = st(hands={"A": ["caracal"]})
    put(s, "1,2", "muskrat", "A")
    put(s, "2,2", "lion", "B")                                  # stands between
    assert "3,2" in place_targets(s)


def test_reach_meets_a_stranded_launch_point():
    s = st(hands={"A": ["caracal"]})
    put(s, "3,1", "muskrat", "A")                               # not connected
    t = place_targets(s)
    assert "4,1" not in t and "3,3" not in t


def test_reach_meets_a_den_it_never_captures():
    s = st(hands={"A": ["caracal"]})
    put(s, "1,2", "muskrat", "A")
    put(s, "2,2", "muskrat", "A")
    put(s, "3,2", "lion", "B")                                  # the chain breaks before B's front
    assert not any(isinstance(a, PlaceAction) and a.target[0] == "hq" for a in rules.legal_actions(s))


def test_reach_meets_armor_covering_still_needs_greater_strength():
    s = st(hands={"A": ["caracal"]})                            # 6
    put(s, "1,2", "muskrat", "A")
    put(s, "3,2", "stag_beetle", "B")                           # 4: coverable
    put(s, "2,1", "tortoise", "B")                              # 6: not
    t = place_targets(s)
    assert "3,2" in t and "2,1" not in t


def test_reach_meets_a_trap_dart_frog_next_to_a_hippo_falls_and_takes_it():
    s = st(hands={"A": ["dart_frog"]})                          # 1, Reach, Poison. Fall: remove all animals next to this
    put(s, "1,2", "muskrat", "A")
    put(s, "2,2", "lion", "B")
    put(s, "3,3", "hippopotamus", "B")
    play(s, "dart_frog", "3,2")                                 # two away, next to the Hippo
    assert s.top_unit("3,2") is None and removed(s, "dart_frog")
    assert s.top_unit("3,3") is None and s.top_unit("2,2") is None


# ======================================================================================================= Roam
# "moves through your own animals connected to it, then ... one [step] without [Reach] ... It lands by the placement
# rules ... arriving next to a trap sets it off as a placement would, and covering by roaming sets off Spikes and
# Poison. ... An Apex Predator ... roams only onto an animal, and eats it."

def test_roam_meets_its_pack_it_walks_through_and_one_step_beyond():
    s = st()
    put(s, "1,1", "wolf", "A")
    put(s, "2,1", "muskrat", "A")
    put(s, "2,2", "muskrat", "A")
    assert legal(s, RoamAction("1,1", ("cr", "2,3")))           # through 2,1 and 2,2, one beyond
    assert not legal(s, RoamAction("1,1", ("cr", "4,2")))


def test_roam_meets_an_enemy_in_the_way_the_pack_never_includes_it():
    s = st()
    put(s, "1,1", "wolf", "A")
    put(s, "2,1", "lion", "B")                                  # 7: an enemy, not pack, and not coverable
    assert not legal(s, RoamAction("1,1", ("cr", "3,1")))


def test_roam_meets_a_trap_hippopotamus():
    s = st()
    put(s, "1,2", "bush_dog", "A")                              # 3, Roam
    put(s, "3,2", "hippopotamus", "B")
    roam(s, "1,2", "2,2")
    assert s.top_unit("2,2") is None and removed(s, "bush_dog")


def test_roam_meets_a_trap_boar():
    s = st()
    put(s, "1,2", "wolf", "A")
    put(s, "3,2", "boar", "B")
    roam(s, "1,2", "2,2")
    assert s.top_unit("2,2") is None and removed(s, "wolf")


def test_roam_meets_a_trap_golden_orb_weaver():
    s = st()
    put(s, "1,2", "wolf", "A")
    put(s, "3,2", "golden_orb_weaver", "B")
    roam(s, "1,2", "2,2")
    assert s.top_unit("2,2") is None and removed(s, "wolf")


def test_roam_meets_spikes():
    s = st()
    put(s, "1,2", "wolf", "A")                                  # 6 > 5
    put(s, "2,2", "hedgehog", "B")
    roam(s, "1,2", "2,2")
    assert top(s, "2,2") == ("hedgehog", "B") and removed(s, "wolf")


def test_roam_meets_poison():
    s = st()
    put(s, "1,2", "wolf", "A")
    put(s, "2,2", "toad", "B")
    roam(s, "1,2", "2,2")
    assert top(s, "2,2") == ("wolf", "A")
    end_turn(s)
    assert top(s, "2,2") == ("toad", "B") and removed(s, "wolf")


def test_roam_meets_flee():
    s = st()
    put(s, "1,2", "wolf", "A")
    put(s, "2,2", "gazelle", "B")
    roam(s, "1,2", "2,2")
    assert stack(s, "2,2") == ["wolf"] and "gazelle" in hand_ids(s, "B")


def test_roam_meets_armor_it_covers_a_weaker_armor_enemy():
    s = st()
    put(s, "1,2", "wolf", "A")
    put(s, "2,2", "stag_beetle", "B")
    put(s, "1,1", "tortoise", "B")
    assert legal(s, RoamAction("1,2", ("cr", "2,2")))
    assert not legal(s, RoamAction("1,2", ("cr", "1,1")))


def test_roam_meets_stealth_it_covers_a_stealth_enemy():
    s = st()
    put(s, "1,2", "moose", "A")                                 # 8, Roam
    put(s, "2,2", "stick_insect", "B")
    assert legal(s, RoamAction("1,2", ("cr", "2,2")))


def test_roam_meets_apex_predator_orca_only_onto_an_animal_and_eats_it():
    s = st()
    put(s, "1,2", "orca", "A")                                  # 6, Apex Predator, Roam
    put(s, "2,2", "muskrat", "B")
    assert not legal(s, RoamAction("1,2", ("cr", "1,1")))       # empty
    roam(s, "1,2", "2,2")
    assert stack(s, "2,2") == ["orca"] and removed(s, "muskrat")


def test_roam_meets_apex_and_armor_orca_buries_it():
    s = st()
    put(s, "1,2", "orca", "A")
    put(s, "2,2", "stag_beetle", "B")
    roam(s, "1,2", "2,2")
    assert stack(s, "2,2") == ["stag_beetle", "orca"]


def test_roam_meets_reach_leopard_legend_pounces_two_beyond_over_an_enemy():
    s = st()
    put(s, "1,2", "leopard_legend", "A")                        # Apex, Roam, Reach
    put(s, "2,2", "lion", "B")                                  # stands between
    put(s, "3,2", "muskrat", "B")
    assert legal(s, RoamAction("1,2", ("cr", "3,2")))


def test_roam_meets_a_roar_moving_is_not_placing_the_roar_does_not_happen():
    s = st(hands={"A": ["coyote"]})                             # give a connected ally Roam. It roams.
    put(s, "1,1", "black_mamba", "A")                           # Roar: remove an adjacent enemy of 6 or less
    put(s, "3,1", "muskrat", "B")
    play(s, "coyote", "1,2")
    choose(s, "1,1")
    choose(s, "2,1")                                            # lands next to the Muskrat
    assert top(s, "2,1") == ("black_mamba", "A") and top(s, "3,1") == ("muskrat", "B")


def test_roam_meets_wild_a_roamer_covers_a_locust():
    s = st(hands={"A": ["locust_legend"]})
    play(s, "locust_legend", "1,2")
    end_turn(s)
    s.hands["B"] = []
    s.add_to_hand("B", "wolf")
    play(s, "wolf", "4,2")                                      # B covers a Locust, then roams onto the next one
    roam(s, "4,2", "3,2")                                       # B's two actions: A's turn starts, the swarm eats
    assert stack(s, "3,2") == ["locust_swarm", "wolf"]          # the covered Locust waits


def test_roam_meets_titan_and_hungry_moose_is_hungry_whether_or_not_it_roamed():
    s = st(food={"A": 3, "B": 0})
    put(s, "1,2", "moose", "A")                                 # Hungry 3. Roam.
    roam(s, "1,2", "2,2")
    end_turn(s); end_turn(s)
    assert s.food["A"] == 0 and effective_strength(s, s.top_unit("2,2")) == 8


# ======================================================================================================= Flee
# "When an enemy covers this, it returns to your hand: the cover takes the crossroad, but nothing dies." Flee happens
# before every other reaction to the cover.

def test_flee_meets_a_plain_enemy_cover():
    s = st(hands={"A": ["lion"]})
    put(s, "1,2", "deer", "B")
    play(s, "lion", "1,2")
    assert stack(s, "1,2") == ["lion"] and hand_ids(s, "B") == ["deer"] and not removed(s, "deer")


def test_flee_meets_its_own_controllers_cover():
    s = st(hands={"A": ["lion"]})
    put(s, "1,2", "deer", "A")
    play(s, "lion", "1,2")
    assert stack(s, "1,2") == ["deer", "lion"] and hand_ids(s, "A") == []


def test_flee_meets_an_apex_predator_nothing_left_to_eat():
    s = st(hands={"A": ["tiger"]})
    put(s, "1,2", "lemming", "B")
    put(s, "1,2", "gazelle", "B")
    play(s, "tiger", "1,2")
    assert "gazelle" in hand_ids(s, "B") and not removed(s, "gazelle")
    assert stack(s, "1,2") == ["lemming", "tiger"] and not removed(s, "lemming")


def test_flee_meets_a_stealth_apex_black_panther():
    s = st(hands={"A": ["black_panther"]})
    put(s, "1,2", "hare", "B")
    play(s, "black_panther", "1,2")
    assert "hare" in hand_ids(s, "B") and stack(s, "1,2") == ["black_panther"]


def test_flee_meets_a_titan_cover():
    s = st(hands={"A": ["blue_whale"]})
    put(s, "1,2", "zebra", "B")                                 # When this flees, return the enemy that covered it
    play(s, "blue_whale", "1,2")
    assert "zebra" in hand_ids(s, "B") and "blue_whale" in hand_ids(s, "A") and s.top_unit("1,2") is None


def test_flee_meets_an_armor_coverer_zebra_cannot_return_it():
    s = st(hands={"A": ["tortoise"]})
    put(s, "1,2", "zebra", "B")                                 # 5 < 6
    play(s, "tortoise", "1,2")
    assert "zebra" in hand_ids(s, "B") and top(s, "1,2") == ("tortoise", "A")


def test_flee_meets_a_removal_it_does_not_flee_from_a_removal():
    s = st(hands={"A": ["hawk"]})                               # remove an adjacent enemy of 4 or less
    put(s, "2,2", "gazelle", "B")
    play(s, "hawk", "1,2")
    choose(s, "2,2")
    assert removed(s, "gazelle") and "gazelle" not in hand_ids(s, "B")


def test_flee_meets_a_wild_locust_cover():
    s = st(hands={"A": ["locust_legend"]})
    put(s, "2,2", "gazelle", "B")
    play(s, "locust_legend", "1,2")
    assert "gazelle" in hand_ids(s, "B") and top(s, "2,2")[1] == WILD


def test_flee_meets_spikes_coverer_order_flee_first():
    s = st(hands={"A": ["lion"]})                               # an enemy Porcupine's aura gives the Deer Spikes
    put(s, "1,2", "deer", "B")
    put(s, "1,1", "porcupine", "B")
    play(s, "lion", "1,2")
    assert "deer" in hand_ids(s, "B")
    assert removed(s, "lion")                                    # the cover still set the Spikes off


# ================================================================================================ Apex Predator
# "It covers, then eats ... If the occupant can't be eaten (Armor) ... it simply covers it". Stealth doesn't stop the eat.

def test_apex_predator_meets_poison_it_eats_and_is_poisoned():
    s = st(hands={"A": ["tiger"]})
    put(s, "1,2", "toad", "B")
    play(s, "tiger", "1,2")
    assert removed(s, "toad") and top(s, "1,2") == ("tiger", "A")
    end_turn(s)                                                 # B's next turn: the poison resolves, the Toad gone or not
    assert s.top_unit("1,2") is None and removed(s, "tiger")


def test_apex_predator_meets_spikes_both_die():
    s = st(hands={"A": ["tiger"]})
    put(s, "1,2", "hedgehog", "B")
    play(s, "tiger", "1,2")
    assert removed(s, "tiger") and removed(s, "hedgehog") and s.top_unit("1,2") is None


def test_apex_predator_meets_wild_it_eats_a_locust():
    s = st(hands={"A": ["locust_legend", "tiger"]})
    put(s, "1,1", "lemming", "B")
    play(s, "locust_legend", "1,2")
    play(s, "tiger", "1,1")
    assert stack(s, "1,1") == ["lemming", "tiger"]


def test_apex_predator_meets_its_own_animal_eats_it_without_strength():
    s = st(hands={"A": ["tiger"]})
    put(s, "1,2", "blue_whale", "A")                            # 12 > 7: its own, so no strength needed
    play(s, "tiger", "1,2")
    assert stack(s, "1,2") == ["tiger"] and removed(s, "blue_whale")


def test_apex_predator_meets_an_empty_crossroad_and_a_den():
    s = st(hands={"A": ["tiger"]})
    put(s, "1,2", "muskrat", "A")
    put(s, "2,2", "muskrat", "A")
    put(s, "3,2", "muskrat", "A")
    put(s, "4,2", "muskrat", "A")
    t = place_targets(s)
    assert "2,1" not in t and "4,2" in t
    assert not any(isinstance(a, PlaceAction) and a.target[0] == "hq" for a in rules.legal_actions(s))


def test_apex_predator_meets_fall_earthworm_eaten_falls():
    s = st(hands={"A": ["tiger"]}, decks={"A": FILLER[:], "B": ["lion", "lion"]})
    put(s, "1,2", "earthworm", "B")                             # Fall: draw a card and place two Worms on its crossroad
    play(s, "tiger", "1,2")
    assert removed(s, "earthworm") and len(s.hands["B"]) == 1
    assert stack(s, "1,2")[-1] == "tiger"                       # under an enemy there is no room for Worms


def test_apex_predator_meets_armor_aura_armadillo_buries_the_ally():
    s = st(hands={"A": ["tiger"]})
    put(s, "2,2", "muskrat", "B")
    put(s, "2,1", "armadillo", "B")                             # your adjacent animals have Armor
    put(s, "1,2", "lion", "A")
    play(s, "tiger", "2,2")
    assert stack(s, "2,2") == ["muskrat", "tiger"]


def test_apex_predator_meets_stealth_and_apex_black_panther_eats_a_stealth():
    s = st(hands={"A": ["black_panther"]})
    put(s, "1,2", "stick_insect", "B")                          # 6 < 7
    play(s, "black_panther", "1,2")
    assert stack(s, "1,2") == ["black_panther"] and removed(s, "stick_insect")


# ====================================================================================================== Spikes

def test_spikes_meets_a_second_enemy_cover_once_only():
    s = st(hands={"A": ["lion", "lion"]})
    put(s, "1,2", "hedgehog", "B")
    play(s, "lion", "1,2")
    assert top(s, "1,2") == ("hedgehog", "B")
    play(s, "lion", "1,2")
    assert top(s, "1,2") == ("lion", "A")


def test_spikes_meets_a_friendly_cover():
    s = st(hands={"A": ["lion", "lion"]}, current="B")
    hh = put(s, "4,2", "hedgehog", "B")
    s.hands["B"] = []
    s.add_to_hand("B", "lion")
    play(s, "lion", "4,2")
    assert stack(s, "4,2") == ["hedgehog", "lion"] and not hh.retaliation_used


def test_spikes_meets_the_coverers_roar_the_roar_first():
    s = st(hands={"A": ["jaguar"]})                             # 6. Roar: remove an adjacent enemy of 4 or less
    put(s, "1,2", "hedgehog", "B")
    put(s, "2,2", "muskrat", "B")
    play(s, "jaguar", "1,2")
    if s.pending:
        choose(s, "2,2")
    assert s.top_unit("2,2") is None and removed(s, "jaguar")


def test_spikes_meets_an_aura_porcupine_gives_it_to_a_neighbour():
    s = st(hands={"A": ["lion"]})
    put(s, "1,2", "muskrat", "B")
    put(s, "2,2", "porcupine", "B")
    play(s, "lion", "1,2")
    assert top(s, "1,2") == ("muskrat", "B") and removed(s, "lion")


def test_spikes_meets_a_titan():
    s = st(hands={"A": ["blue_whale"]})
    put(s, "1,2", "hedgehog", "B")
    play(s, "blue_whale", "1,2")
    assert removed(s, "blue_whale")


def test_spikes_meets_wild_a_locust_on_spikes_is_removed():
    s = st(hands={"A": ["locust_legend"]})
    put(s, "2,2", "hedgehog", "B")
    play(s, "locust_legend", "1,2")
    assert top(s, "2,2") == ("hedgehog", "B")


def test_spikes_meets_the_octopus_an_inked_hedgehog_has_none():
    s = st(hands={"A": ["octopus", "lion"]})
    put(s, "2,2", "hedgehog", "B")
    play(s, "octopus", "1,2")
    play(s, "lion", "2,2")
    assert top(s, "2,2") == ("lion", "A")


# ====================================================================================================== Poison
# "When an enemy covers it, that enemy is removed at the start of your next turn. Every time, not once ... it resolves
# even if the Poison animal is gone by then ... A friendly cover doesn't set it off."

def test_poison_meets_a_cover_every_time():
    s = st(hands={"A": ["lion", "lion"]})
    put(s, "1,2", "toad", "B")
    play(s, "lion", "1,2")
    end_turn(s)
    assert top(s, "1,2") == ("toad", "B")
    end_turn(s)
    play(s, "lion", "1,2")
    end_turn(s)
    assert top(s, "1,2") == ("toad", "B") and s.remove_pile.count("lion") == 2


def test_poison_meets_a_friendly_cover():
    s = st(current="B", hands={"B": ["lion"]})
    put(s, "4,2", "toad", "B")
    play(s, "lion", "4,2")
    end_turn(s); end_turn(s)
    assert stack(s, "4,2") == ["toad", "lion"]


def test_poison_meets_a_cover_on_the_coverer_it_ticks_underneath():
    s = st(hands={"A": ["lion", "lion"]})
    put(s, "1,2", "toad", "B")
    play(s, "lion", "1,2")
    play(s, "lion", "1,2")                                      # A covers its own poisoned Lion
    end_turn(s)
    assert stack(s, "1,2") == ["toad", "lion"] and s.remove_pile == ["lion"]


def test_poison_meets_the_coverer_getting_the_rest_of_its_turn():
    s = st(hands={"A": ["lion", "lion"]})
    put(s, "1,2", "toad", "B")
    play(s, "lion", "1,2")
    assert "2,2" in place_targets(s)                            # the chain through it holds for the rest of the turn


def test_poison_meets_an_aura_jellyfish():
    s = st(hands={"A": ["lion"]})
    put(s, "1,2", "muskrat", "B")
    put(s, "2,2", "jellyfish", "B")                             # your adjacent animals have Poison
    play(s, "lion", "1,2")
    end_turn(s)
    assert top(s, "1,2") == ("muskrat", "B")


def test_poison_meets_wild_a_locust_on_poison_is_removed_before_it_eats():
    s = st(hands={"A": ["locust_legend"]})
    put(s, "2,2", "toad", "B")
    play(s, "locust_legend", "1,2")
    end_turn(s)                                                 # B's turn starts: the poison removes the Locust
    assert top(s, "2,2") == ("toad", "B")
    end_turn(s)
    assert top(s, "2,2") == ("toad", "B")


def test_poison_meets_the_octopus_an_inked_toad_has_none():
    s = st(hands={"A": ["octopus", "lion"]})
    put(s, "2,2", "toad", "B")
    play(s, "octopus", "1,2")
    play(s, "lion", "2,2")
    end_turn(s)
    assert top(s, "2,2") == ("lion", "A")


# ======================================================================================================= Titan
# "Playing it costs two actions instead of one. A free placement can't pay for it; an extra action can."

def test_titan_meets_one_action_left():
    s = st(hands={"A": ["blue_whale", "muskrat"]})
    assert "1,2" in {a.target[1] for a in rules.legal_actions(s) if isinstance(a, PlaceAction) and a.card_id == "blue_whale"}
    play(s, "muskrat", "1,1")
    assert not any(isinstance(a, PlaceAction) and a.card_id == "blue_whale" for a in rules.legal_actions(s))


def test_titan_meets_a_free_placement_mole():
    s = st(hands={"A": ["mole", "blue_whale", "muskrat"]})      # Roar: play another animal next to this
    play(s, "mole", "1,2")
    offered = {p["card_id"] for p in s.pending["placements"]}
    assert offered == {"muskrat"}                                # the Muskrat can be played free; the Whale can't


def test_titan_meets_krill_it_costs_one_action():
    s = st(hands={"A": ["krill", "blue_whale"]})
    play(s, "krill", "1,1")
    assert any(isinstance(a, PlaceAction) and a.card_id == "blue_whale" for a in rules.legal_actions(s))


def test_titan_meets_covering_it_needs_greater_strength_like_any_animal():
    s = st(hands={"A": ["blue_whale"]})
    put(s, "1,2", "lion", "B")
    put(s, "1,1", "blue_whale", "B")                            # 12 == 12
    t = place_targets(s)
    assert "1,2" in t and "1,1" not in t


# ====================================================================================================== Hungry
# "At the start of your turn this eats up to N of your food, and gets -1 strength, for good, for each food it was short.
# Below 0 it dies."

def test_hungry_meets_enough_food():
    s = st(food={"A": 7, "B": 0})
    el = put(s, "1,2", "elephant", "A")                         # Hungry 5
    end_turn(s); end_turn(s)
    assert s.food["A"] == 2 and effective_strength(s, el) == 9


def test_hungry_meets_too_little_food():
    s = st(food={"A": 2, "B": 0})
    el = put(s, "1,2", "elephant", "A")
    end_turn(s); end_turn(s)
    assert s.food["A"] == 0 and effective_strength(s, el) == 6
    end_turn(s); end_turn(s)
    assert effective_strength(s, el) == 1                       # for good


def test_hungry_meets_the_opponents_dawn():
    s = st(food={"A": 5, "B": 0})
    put(s, "1,2", "elephant", "A")
    end_turn(s)                                                 # B's Dawn
    assert s.food["A"] == 5


def test_hungry_meets_being_buried():
    s = st(food={"A": 5, "B": 0})
    el = put(s, "1,2", "elephant", "A")
    put(s, "1,2", "blue_whale", "B")
    end_turn(s); end_turn(s)
    assert s.food["A"] == 5 and el.strength_counter == 0


def test_hungry_meets_dying_below_zero_armor_does_not_save_it():
    s = st(food={"A": 0, "B": 0})
    el = put(s, "1,2", "elephant", "A")
    el.strength_counter = -8                                    # a 1: five short takes it to -4
    put(s, "1,1", "armadillo", "A")                             # gives it Armor
    end_turn(s); end_turn(s)
    assert removed(s, "elephant") and top(s, "1,2") is None


def test_hungry_meets_a_delayed_food_payout_sloth_feeds_it_that_dawn():
    s = st(hands={"A": ["sloth"]}, food={"A": 0, "B": 0})       # Roar: in 2 turns, gain 30 food
    el = put(s, "1,2", "elephant", "A")
    play(s, "sloth", "1,1")
    strengths = [9]
    for _ in range(3):
        end_turn(s); end_turn(s)
        strengths.append(effective_strength(s, el))
        if s.food["A"]:
            break
    assert s.food["A"] == 25 and strengths[-1] == strengths[-2]     # fed the Dawn the food came


def test_hungry_meets_the_octopus_an_inked_animal_isnt_hungry():
    s = st(current="B", hands={"B": ["octopus"]}, food={"A": 5, "B": 0})
    put(s, "4,1", "lion", "B")
    el = put(s, "3,2", "elephant", "A")
    play(s, "octopus", "3,1")
    end_turn(s)
    assert s.food["A"] == 5 and el.strength_counter == 0


# ======================================================================================================== Wild
# "Belongs to no one ... connects no one and holds no region ... any animal of strength 1 or more covers it ... 'enemy'
# effects see it ... Its timers tick every turn, both players'".

def test_wild_meets_a_region_it_holds_none_and_pays_no_one():
    s = st(hands={"A": ["locust_legend"]})
    for cr in ("1,1", "2,1", "2,2"):
        put(s, cr, "muskrat", "A")
    play(s, "locust_legend", "1,2")                             # A would hold R1 with it; the swarm covers all
    end_turn(s)
    assert s.food["A"] == 0


def test_wild_meets_connection_it_connects_no_one():
    s = st(hands={"A": ["locust_legend", "muskrat"]})
    put(s, "1,2", "muskrat", "A")
    put(s, "2,2", "muskrat", "A")
    play(s, "locust_legend", "1,3")
    # every crossroad is a Locust now, A's chain included: A enters again only from its den front
    assert place_targets(s) == {"1,1", "1,2", "1,3"}


def test_wild_meets_strength_any_animal_of_1_or_more_covers_it_and_0_does_not():
    s = st(hands={"A": ["locust_legend", "lemming", "sardine"]})
    play(s, "locust_legend", "1,3")
    lemming = {a.target[1] for a in rules.legal_actions(s) if isinstance(a, PlaceAction) and a.card_id == "lemming"}
    sardine = {a.target[1] for a in rules.legal_actions(s) if isinstance(a, PlaceAction) and a.card_id == "sardine"}
    assert "1,1" in lemming and "1,1" not in sardine


def test_wild_meets_the_opponent_they_cover_it_too():
    s = st(hands={"A": ["locust_legend"]}, decks={"A": FILLER[:], "B": FILLER[:]})
    play(s, "locust_legend", "1,3")
    end_turn(s)
    s.hands["B"] = []
    s.add_to_hand("B", "lemming")
    assert "4,2" in place_targets(s)


def test_wild_meets_an_enemy_effect_hawk_can_remove_a_locust():
    s = st(hands={"A": ["locust_legend", "hawk"]})
    play(s, "locust_legend", "1,3")
    play(s, "hawk", "1,2")                                      # on top of a Locust, its own Roar next
    assert "2,2" in options(s)


def test_wild_meets_timers_across_turns_the_swarm_eats_after_the_opponents_turn():
    s = st(hands={"A": ["locust_legend"]})
    put(s, "3,2", "lion", "B")
    play(s, "locust_legend", "1,2")
    end_turn(s)                                                 # B's turn: one tick
    assert stack(s, "3,2") == ["lion", "locust_swarm"]
    end_turn(s)                                                 # A's turn: the second; it eats, then flies away
    assert s.top_unit("3,2") is None and removed(s, "lion") and not removed(s, "locust_swarm")


def test_wild_meets_a_cover_a_covered_locust_waits():
    s = st(hands={"A": ["locust_legend", "lion"]})
    put(s, "1,1", "lemming", "A")
    play(s, "locust_legend", "1,2")
    play(s, "lion", "1,1")
    end_turn(s); end_turn(s)
    assert stack(s, "1,1") == ["lemming", "locust_swarm", "lion"]


def test_wild_meets_dawn_a_buried_groundhog_under_a_locust():
    s2 = st(hands={"A": ["locust_legend"]})
    put(s2, "2,3", "groundhog", "A")
    play(s2, "locust_legend", "1,2")
    end_turn(s2); end_turn(s2)                                  # A's Dawn: the Groundhog is buried, then eaten
    assert s2.food["A"] == 0 and removed(s2, "groundhog")


def test_wild_meets_fall_a_locust_eating_an_earthworm():
    s = st(hands={"A": ["locust_legend"]}, decks={"A": FILLER[:], "B": ["lion"] * 3})
    put(s, "3,2", "earthworm", "B")
    play(s, "locust_legend", "1,2")
    end_turn(s)
    n = len(s.hands["B"])
    end_turn(s)
    assert removed(s, "earthworm") and len(s.hands["B"]) == n + 1
    assert stack(s, "3,2") == ["worm", "worm"]


# ================================================================================================ Dawn and Dusk

def test_dawn_meets_both_players_turns():
    s = st()
    put(s, "1,2", "groundhog", "A")
    end_turn(s)
    assert s.food["A"] == 0                                     # B's Dawn
    end_turn(s)
    assert s.food["A"] == 10                                    # A's


def test_dusk_meets_both_players_turns():
    s = st()
    put(s, "1,2", "sea_turtle", "A")                            # Dusk: add a Baby Turtle to your hand
    end_turn(s)
    assert hand_ids(s, "A") == ["baby_turtle"]
    end_turn(s)                                                 # B's Dusk
    assert hand_ids(s, "A") == ["baby_turtle"]


def test_dawn_meets_burial():
    s = st()
    put(s, "1,2", "groundhog", "A")
    put(s, "1,2", "lion", "B")
    end_turn(s); end_turn(s)
    assert s.food["A"] == 0


def test_dusk_meets_burial():
    s = st()
    put(s, "1,2", "sea_turtle", "A")
    put(s, "1,2", "lion", "B")
    end_turn(s)
    assert hand_ids(s, "A") == []


def test_dawn_meets_resurfacing():
    s = st(hands={"A": ["praying_mantis"]})                     # Roar: remove an adjacent ally to draw 2 cards
    put(s, "1,2", "lemming", "A")
    put(s, "3,2", "groundhog", "B")                             # Dawn: gain 10 food
    put(s, "3,2", "muskrat", "A")                               # buried under A's Muskrat
    play(s, "praying_mantis", "2,2")
    choose(s, "3,2")                                            # the cover leaves: the Groundhog resurfaces
    end_turn(s)
    assert s.food["B"] == 10


def test_dusk_meets_the_legendary_sloth_twice():
    s = st()
    put(s, "1,2", "sea_turtle", "A")
    put(s, "1,1", "sloth_legend", "A")                          # your Dusk effects happen twice
    end_turn(s)
    assert hand_ids(s, "A") == ["baby_turtle", "baby_turtle"]


def test_dawn_meets_the_octopus_an_inked_groundhog_gains_nothing():
    s = st(current="B", hands={"B": ["octopus"]})
    put(s, "4,1", "lion", "B")
    put(s, "3,2", "groundhog", "A")
    play(s, "octopus", "3,1")
    end_turn(s)
    assert s.food["A"] == 0


# ======================================================================================================== Fall
# "resolves when this unit is removed from the board: by an effect, by an Apex Predator eating it, or by dying below 0".

def test_fall_meets_a_chosen_roar_removal():
    s = st(hands={"A": ["hawk"]}, decks={"A": FILLER[:], "B": ["lion"] * 3})
    put(s, "2,2", "earthworm", "B")
    play(s, "hawk", "1,2")
    choose(s, "2,2")
    assert removed(s, "earthworm") and len(s.hands["B"]) == 1 and stack(s, "2,2") == ["worm", "worm"]


def test_fall_meets_a_mass_roar_removal():
    s = st(hands={"A": ["rhinoceros"]}, decks={"A": FILLER[:], "B": ["lion"] * 3})
    put(s, "2,2", "earthworm", "B")
    play(s, "rhinoceros", "1,2")
    assert len(s.hands["B"]) == 1 and stack(s, "2,2") == ["worm", "worm"]


def test_fall_meets_dying_below_zero():
    s = st(hands={"A": ["viper"]}, decks={"A": FILLER[:], "B": ["lion"] * 3})
    put(s, "2,2", "earthworm", "B")
    play(s, "viper", "1,2")
    if s.pending:
        choose(s, "2,2")
    assert removed(s, "earthworm") and len(s.hands["B"]) == 1


def test_fall_meets_a_trap_hippopotamus():
    s = st(hands={"A": ["earthworm"]})
    put(s, "2,2", "hippopotamus", "B")
    play(s, "earthworm", "1,2")
    # the Worms are placed next to the Hippo too (traps see a placed animal), and each falls in turn
    assert removed(s, "earthworm") and s.remove_pile.count("worm") == 2 and len(s.hands["A"]) == 3
    assert stack(s, "1,2") == []


def test_fall_meets_spikes_pheasant_legend():
    s = st(hands={"A": ["pheasant_legend"]})                    # 7, Flight. Fall: shuffle Ember into your deck
    put(s, "3,2", "hedgehog", "B")
    play(s, "pheasant_legend", "3,2")
    assert s.top_unit("3,2").card_id == "hedgehog" and "pheasant_legend" in s.decks["A"]


def test_fall_meets_poison_pheasant_legend():
    s = st(hands={"A": ["pheasant_legend"]})
    put(s, "3,2", "toad", "B")
    play(s, "pheasant_legend", "3,2")
    end_turn(s)
    assert top(s, "3,2") == ("toad", "B") and "pheasant_legend" in s.decks["A"]


def test_fall_meets_a_cover_it_does_not_fall():
    s = st(hands={"A": ["lion"]}, decks={"A": FILLER[:], "B": ["lion"] * 3})
    put(s, "1,2", "earthworm", "B")
    play(s, "lion", "1,2")
    assert hand_ids(s, "B") == [] and stack(s, "1,2") == ["earthworm", "lion"]


def test_fall_meets_a_bounce_it_does_not_fall():
    s = st(hands={"A": ["skunk"]}, decks={"A": FILLER[:], "B": ["lion"] * 3})
    put(s, "2,2", "earthworm", "B")
    play(s, "skunk", "1,2")
    if s.pending:
        choose(s, "2,2")
    assert hand_ids(s, "B") == ["earthworm"] and s.top_unit("2,2") is None


def test_fall_meets_a_plague_a_buried_earthworm_falls_too():
    s = st(hands={"A": ["rat_legend_2"]}, decks={"A": FILLER[:], "B": ["lion"] * 3})
    put(s, "2,2", "earthworm", "B")
    put(s, "2,2", "muskrat", "B")
    play(s, "rat_legend_2", "1,2")
    choose(s, "2,2")
    assert removed(s, "earthworm") and len(s.hands["B"]) == 1


def test_fall_meets_a_chain_dart_frog_falls_next_to_a_cockroach():
    s = st(hands={"A": ["hawk"]})
    put(s, "2,2", "dart_frog", "B")
    put(s, "3,2", "cockroach", "B")
    play(s, "hawk", "1,2")
    choose(s, "2,2")
    assert top(s, "3,2") == ("cockroach", "B")                  # removed by the frog's Fall, and fell back


def test_fall_meets_the_octopus_an_inked_earthworm_does_not_fall():
    s = st(hands={"A": ["octopus", "hawk"]}, decks={"A": FILLER[:], "B": ["lion"] * 3})
    put(s, "2,2", "earthworm", "B")
    play(s, "octopus", "1,2")
    play(s, "hawk", "2,1")
    choose(s, "2,2")
    assert hand_ids(s, "B") == [] and s.top_unit("2,2") is None


# ================================================================================================ Roar doubled
# Woodpecker: "Roar: your next Roar this turn happens twice."

def test_roar_doubled_meets_armor_the_second_finds_no_target():
    s = st(hands={"A": ["woodpecker", "hawk"]})
    put(s, "2,2", "muskrat", "B")
    put(s, "1,1", "stag_beetle", "B")                           # 4, Armor
    play(s, "woodpecker", "3,3")
    play(s, "hawk", "1,2")
    assert options(s) == {"2,2"}
    choose(s, "2,2")
    assert not s.pending and top(s, "1,1") == ("stag_beetle", "B")


def test_roar_doubled_meets_stealth_neither_roar_chooses_it():
    s = st(hands={"A": ["woodpecker", "hawk"]})
    put(s, "2,2", "muskrat", "B")
    put(s, "1,1", "butterfly_legend_chrysalis", "B")
    put(s, "1,3", "chinchilla", "B")
    play(s, "woodpecker", "3,3")
    play(s, "hawk", "1,2")
    assert "1,1" not in options(s)
    choose(s, "2,2")
    assert "1,1" not in options(s)


def test_roar_doubled_meets_a_mass_removal_albatross():
    s = st(hands={"A": ["woodpecker", "albatross"]})
    put(s, "3,2", "cockroach", "B")                             # removed, falls back, removed again
    play(s, "woodpecker", "1,1")
    play(s, "albatross", "3,3")
    # each Roar removed a Cockroach and each fell (a fresh one back, a Roach beside it): two Roaches
    assert top(s, "3,2") == ("cockroach", "B")
    assert len([cr for cr in s.board if (u := s.top_unit(cr)) and u.card_id == "roach"]) == 2


def test_roar_doubled_meets_fall_the_second_roar_can_take_the_fresh_cockroach():
    s = st(hands={"A": ["woodpecker", "hawk"]})
    put(s, "2,2", "cockroach", "B")
    play(s, "woodpecker", "3,3")
    play(s, "hawk", "1,2")
    choose(s, "2,2")
    assert "2,2" in options(s)


def test_roar_doubled_meets_a_trap_honey_badger_next_to_a_hippo():
    s = st(hands={"A": ["woodpecker", "honey_badger"]})         # 3. Roar: remove an adjacent enemy of 6 or more
    put(s, "2,2", "hippopotamus", "B")
    play(s, "woodpecker", "3,3")
    play(s, "honey_badger", "1,2")
    while s.pending:
        rules.apply_action(s, ChoiceAction(s.pending["options"][0]))
    assert s.top_unit("2,2") is None and removed(s, "hippopotamus")
    assert s.top_unit("1,2") is None and removed(s, "honey_badger")   # the trap still went off


def test_roar_meets_a_trap_the_trap_resolves_after_the_roar_removed_it():
    s = st(hands={"A": ["honey_badger"]})
    put(s, "2,2", "hippopotamus", "B")
    play(s, "honey_badger", "1,2")
    while s.pending:
        rules.apply_action(s, ChoiceAction(s.pending["options"][0]))
    assert removed(s, "hippopotamus") and removed(s, "honey_badger")


def test_roar_meets_a_boar_the_boar_is_spent_by_the_first_enemy():
    s = st(hands={"A": ["muskrat", "muskrat"]})
    put(s, "2,2", "boar", "B")
    put(s, "1,1", "lemming", "A")
    play(s, "muskrat", "1,2")
    assert s.top_unit("1,2") is None
    play(s, "muskrat", "2,1")
    assert top(s, "2,1") == ("muskrat", "A")


# ================================================================================================ The legend with all four
# The legendary Honey Badger: Armor. Stealth. Poison. Spikes.

def test_armor_stealth_poison_spikes_meet_an_apex_predator():
    s = st(hands={"A": ["tiger"]})
    put(s, "1,2", "honey_badger_legend", "B")                   # 5 < 7
    play(s, "tiger", "1,2")
    # covered, not eaten (Armor); the spikes remove the Tiger at once
    assert top(s, "1,2") == ("honey_badger_legend", "B") and removed(s, "tiger")


def test_armor_stealth_meet_a_chosen_removal_and_a_mass_one():
    s = st(hands={"A": ["sperm_whale"]})
    put(s, "2,2", "honey_badger_legend", "B")
    play(s, "sperm_whale", "1,2")
    assert top(s, "2,2") == ("honey_badger_legend", "B")


# ================================================================================================ second pass

def test_armor_meets_a_trap_boar_the_armor_animal_spends_it():
    s = st(hands={"A": ["tortoise", "muskrat"]})
    put(s, "2,2", "boar", "B")
    put(s, "1,1", "lemming", "A")
    play(s, "tortoise", "1,2")                                  # the first enemy placed next to it: it stays
    play(s, "muskrat", "2,1")                                   # not the first any more
    assert top(s, "1,2") == ("tortoise", "A") and top(s, "2,1") == ("muskrat", "A")


def test_armor_meets_fall_an_armored_earthworm_cannot_be_chosen():
    s = st(hands={"A": ["hawk"]})
    put(s, "2,2", "earthworm", "B")
    put(s, "3,2", "armadillo", "B")                             # gives the Earthworm Armor
    put(s, "1,1", "lemming", "B")
    play(s, "hawk", "1,2")
    assert "2,2" not in options(s)


def test_stealth_meets_a_locust_eat():
    s = st(hands={"A": ["locust_legend"]})
    put(s, "3,2", "stick_insect", "B")
    play(s, "locust_legend", "1,2")
    end_turn(s); end_turn(s)
    assert removed(s, "stick_insect")


def test_flee_meets_an_apex_predator_and_the_zebra_the_predator_goes_home_hungry():
    s = st(hands={"A": ["tiger"]})
    put(s, "1,2", "zebra", "B")                                 # 5 < 7
    play(s, "tiger", "1,2")
    assert "zebra" in hand_ids(s, "B") and "tiger" in hand_ids(s, "A") and s.top_unit("1,2") is None


def test_flee_meets_a_wild_locust_and_the_zebra_the_locust_just_leaves():
    s = st(hands={"A": ["locust_legend"]})
    put(s, "2,2", "zebra", "B")
    play(s, "locust_legend", "1,2")
    assert "zebra" in hand_ids(s, "B") and s.top_unit("2,2") is None
    assert "locust_swarm" not in hand_ids(s, "A") + hand_ids(s, "B")


def test_flee_meets_its_own_roamer():
    s = st()
    put(s, "1,2", "wolf", "A")
    put(s, "2,2", "gazelle", "A")
    roam(s, "1,2", "2,2")
    assert stack(s, "2,2") == ["gazelle", "wolf"] and hand_ids(s, "A") == []


def test_flee_meets_poison_given_by_an_aura_the_cover_still_poisons():
    s = st(hands={"A": ["lion"]})
    put(s, "1,2", "deer", "B")
    put(s, "1,1", "jellyfish", "B")                             # gives the Deer Poison
    play(s, "lion", "1,2")
    assert "deer" in hand_ids(s, "B")
    end_turn(s)
    assert removed(s, "lion")


def test_flee_meets_vesper_placed_on_top_of_a_fleer():
    s = st(current="B", hands={"A": ["hornet_legend"], "B": ["hare"]})
    put(s, "3,2", "worker_ant", "A")                            # Colony
    put(s, "4,2", "lion", "B")
    play(s, "hare", "3,2")                                      # 4 > 2: B covers a Colony ally; Vesper lands on the Hare
    assert "hare" in hand_ids(s, "B") and stack(s, "3,2") == ["worker_ant", "hornet_legend"]


def test_roam_meets_apex_on_its_own_animal_orca_eats_it():
    s = st()
    put(s, "1,2", "orca", "A")
    put(s, "2,2", "blue_whale", "A")
    roam(s, "1,2", "2,2")
    assert stack(s, "2,2") == ["orca"] and removed(s, "blue_whale")


def test_roam_meets_a_den_a_stranded_pouncer_never_captures():
    s = st()
    put(s, "3,2", "leopard_legend", "A")                        # stranded next to B's front
    assert not any(isinstance(a, RoamAction) and a.target[0] == "hq" for a in rules.legal_actions(s))


def test_roam_meets_a_den_a_pack_on_the_front_connected_home_captures():
    s = st()
    for cr in ("1,2", "2,2", "3,2"):
        put(s, cr, "muskrat", "A")
    put(s, "4,2", "muskrat", "A")
    put(s, "1,1", "wolf", "A")
    assert any(isinstance(a, RoamAction) and a.origin == "1,1" and a.target[0] == "hq" for a in rules.legal_actions(s))


def test_titan_meets_poison():
    s = st(hands={"A": ["blue_whale"]})
    put(s, "1,2", "toad", "B")
    play(s, "blue_whale", "1,2")
    end_turn(s)
    assert removed(s, "blue_whale") and top(s, "1,2") == ("toad", "B")


def test_titan_meets_an_apex_predator_eaten_like_any_animal():
    s = st(current="B", hands={"B": ["tiger"]})
    put(s, "4,2", "blue_whale", "B")                            # its own: no strength needed
    play(s, "tiger", "4,2")
    assert stack(s, "4,2") == ["tiger"] and removed(s, "blue_whale")


def test_fall_meets_a_dawn_removal_city_spider():
    s = st(decks={"A": FILLER[:], "B": ["lion"] * 3})
    put(s, "2,2", "city_spider", "A")
    put(s, "3,2", "earthworm", "B")
    put(s, "1,2", "lion", "A")
    end_turn(s)
    n = len(s.hands["B"])
    end_turn(s)                                                 # A's Dawn
    assert removed(s, "earthworm") and len(s.hands["B"]) == n + 1


def test_hungry_meets_a_hungry_death_it_counts_as_removed_hyena():
    s = st(food={"A": 0, "B": 0})
    el = put(s, "1,2", "elephant", "A")
    el.strength_counter = -8
    put(s, "1,1", "hyena", "A")                                 # Dusk: gain 3 food for each animal removed this turn
    end_turn(s); end_turn(s)                                    # A's Dawn: the Elephant dies
    end_turn(s)                                                 # A's Dusk
    assert removed(s, "elephant") and s.food["A"] == 3


# Martin, 2026-11-05: the swarm lands all at once, and the Hippopotamus takes every Locust around it.
def test_wild_meets_a_trap_every_locust_placed_next_to_a_hippo_is_removed():
    s = st(hands={"A": ["locust_legend"]})
    put(s, "3,2", "hippopotamus", "B")
    play(s, "locust_legend", "1,2")
    assert all(s.top_unit(cr) is None for cr in ("2,2", "3,1", "3,3", "4,2"))


def test_wild_meets_poison_of_the_casters_own_toad_the_toad_was_played_first():
    s = st(hands={"A": ["locust_legend"]})
    put(s, "1,1", "toad", "A")
    play(s, "locust_legend", "1,2")
    end_turn(s); end_turn(s)                                    # A's turn: the poison (the Toad's, played first) first
    assert stack(s, "1,1") == ["toad"]


def test_roam_meets_poison_walking_off_does_not_cure_it():
    s = st(current="B", hands={"B": ["wolf"]})
    put(s, "3,2", "toad", "A")
    put(s, "4,2", "lion", "B")
    play(s, "wolf", "3,2")                                      # 6 > 5: poisoned
    roam(s, "3,2", "3,3")                                       # walks off; the Toad resurfaces
    assert top(s, "3,2") == ("toad", "A")                       # B's two actions: A's turn starts
    assert s.top_unit("3,3") is None and removed(s, "wolf")     # the poison belongs to the coverer, wherever it went


def test_roam_meets_flee_an_apex_roamer_finds_nothing_to_eat():
    s = st()
    put(s, "1,2", "orca", "A")
    put(s, "2,2", "lemming", "B")
    put(s, "2,2", "gazelle", "B")
    roam(s, "1,2", "2,2")
    assert "gazelle" in hand_ids(s, "B") and stack(s, "2,2") == ["lemming", "orca"]


def test_roam_meets_poison_an_apex_roamer_eats_and_is_poisoned():
    s = st()
    put(s, "1,2", "orca", "A")
    put(s, "2,2", "dart_frog", "B")                             # Poison; Fall: remove all animals next to this
    roam(s, "1,2", "2,2")
    # eaten: the frog falls and takes every animal next to it; the Orca sits on its crossroad, poisoned
    assert removed(s, "dart_frog") and top(s, "2,2") == ("orca", "A")
    end_turn(s)
    assert removed(s, "orca")


def test_flight_meets_apex_and_armor_the_eagle_buries_an_armor_animal_far_from_home():
    s = st(hands={"A": ["eagle"]})
    put(s, "3,2", "stag_beetle", "B")
    play(s, "eagle", "3,2")
    assert stack(s, "3,2") == ["stag_beetle", "eagle"]


def test_roar_doubled_meets_it_roams_coyote_moves_twice():
    s = st(hands={"A": ["woodpecker", "coyote"]})
    put(s, "1,1", "lemming", "A")
    play(s, "woodpecker", "3,3")
    play(s, "coyote", "1,2")
    choose(s, "1,1")
    choose(s, "2,2")                                            # the first Roar: it roams
    assert s.pending is not None                                # the second Roar asks again
    choose(s, "2,2")
    choose(s, "3,2")
    assert top(s, "3,2") == ("lemming", "A")


def test_flee_meets_the_casters_own_locust_the_swarm_is_no_ones():
    s = st(hands={"A": ["locust_legend"]})
    put(s, "1,1", "gazelle", "A")                               # the Locust isn't A's either: an enemy cover
    play(s, "locust_legend", "1,2")
    assert "gazelle" in hand_ids(s, "A")


def test_spikes_meets_the_casters_own_locust():
    s = st(hands={"A": ["locust_legend"]})
    put(s, "1,1", "hedgehog", "A")
    play(s, "locust_legend", "1,2")
    assert stack(s, "1,1") == ["hedgehog"]


def test_apex_predator_meets_its_own_spikes_no_spikes_for_a_friend():
    s = st(hands={"A": ["tiger"]})
    put(s, "1,2", "hedgehog", "A")
    play(s, "tiger", "1,2")
    assert stack(s, "1,2") == ["tiger"] and removed(s, "hedgehog") and not removed(s, "tiger")


def test_apex_predator_meets_its_own_poison_no_poison_for_a_friend():
    s = st(hands={"A": ["tiger"]})
    put(s, "1,2", "toad", "A")
    play(s, "tiger", "1,2")
    end_turn(s); end_turn(s)
    assert stack(s, "1,2") == ["tiger"] and not removed(s, "tiger")


def test_apex_predator_meets_its_own_fleer_it_is_eaten():
    s = st(hands={"A": ["tiger"]})
    put(s, "1,2", "gazelle", "A")
    play(s, "tiger", "1,2")
    assert stack(s, "1,2") == ["tiger"] and removed(s, "gazelle") and hand_ids(s, "A") == []


def test_poison_meets_a_return_to_hand_the_coverer_leaves_first_and_is_spared():
    s = st(current="B", hands={"B": ["lion", "opossum"]})       # Opossum: return an adjacent ally to your hand
    put(s, "3,2", "toad", "A")
    put(s, "4,2", "lemming", "B")
    play(s, "lion", "3,2")
    play(s, "opossum", "4,2")
    if s.pending:
        choose(s, "3,2")
    assert "lion" in hand_ids(s, "B") and top(s, "3,2") == ("toad", "A")
    assert s.current == "A" and not removed(s, "lion")          # A's turn has started: no poison left to resolve
    end_turn(s)
    play(s, "lion", "4,3")                                      # played again: a fresh animal
    end_turn(s)
    assert s.current == "A" and top(s, "4,3") == ("lion", "B") and not removed(s, "lion")


def test_roam_meets_a_trap_it_already_stood_next_to():
    s = st()
    put(s, "2,2", "hippopotamus", "B")
    put(s, "1,1", "lemming", "A")
    put(s, "2,1", "bush_dog", "A")                              # already next to the Hippo
    roam(s, "2,1", "1,2")                                       # through its pack (1,1), arriving next to it again
    assert s.top_unit("1,2") is None and removed(s, "bush_dog")
