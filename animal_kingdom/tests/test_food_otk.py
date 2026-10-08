"""Golden tests for the pure-OTK food_otk overhaul (2026-07-05).

Covers the signature mechanic ("food gained this turn") and its cards (Food Aggro's since the launch decks): Barley,
Scrooge, Chipmunk (bonus action), Hedgehog, Gopher, Muskrat, Groundhog, and the Armadillo Stealth aura. Map A geometry
(4x3): "2,2" neighbours "1,2","3,2","2,1","2,3"; A's HQ fronts column 1, B's column 4.
"""

from __future__ import annotations

from animal_kingdom.engine import effects, rules, statics
from animal_kingdom.engine.actions import ChoiceAction, DrawAction, PlaceAction
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.strength import effective_strength

from ._helpers import hand_ids, make_state, put

CFG = Config.default()


def advance_to(s, target_tc):
    while s.turn_counter < target_tc and rules.is_terminal(s) is None:
        rules.apply_action(s, DrawAction())


# ---------------------------------------------------- "food gained this turn" signature

def test_food_gained_counter_tracks_and_resets_between_turns():
    s = make_state(hands={"A": ["squirrel"]}, decks={"A": ["mouse"] * 4, "B": ["mouse"] * 4})
    rules.apply_action(s, PlaceAction("squirrel", ("cr", "1,2")))     # gain 12 (action 1)
    assert effects._food_gained_this_turn(s, "A") == CFG.squirrel_food
    advance_to(s, 2)                                                   # into A's next turn
    assert effects._food_gained_this_turn(s, "A") == 0                # reset each turn


def test_scrooge_doubles_this_turns_haul():
    s = make_state(hands={"A": ["scrooge"]}, food={"A": 20, "B": 0})
    s.turn_flags["food_gained_A"] = 20                                # gained earlier this turn
    rules.apply_action(s, PlaceAction("scrooge", ("cr", "1,2")))
    assert s.food["A"] == 20 + 20 * CFG.scrooge_gain_multiplier


def test_gopher_draws_only_when_fed():
    fed = make_state(hands={"A": ["gopher"]}, decks={"A": ["mouse", "mouse"], "B": []})
    fed.turn_flags["food_gained_A"] = CFG.fed_threshold
    rules.apply_action(fed, PlaceAction("gopher", ("cr", "1,2")))
    assert len(fed.hands["A"]) == CFG.gopher_draw

    unfed = make_state(hands={"A": ["gopher"]}, decks={"A": ["mouse", "mouse"], "B": []})
    rules.apply_action(unfed, PlaceAction("gopher", ("cr", "1,2")))
    assert len(unfed.hands["A"]) == 0


def test_muskrat_removes_adjacent_enemy_only_when_fed():
    fed = make_state(current="A", hands={"A": ["muskrat"]})
    fed.turn_flags["food_gained_A"] = CFG.fed_threshold
    put(fed, "1,2", "lion", "A")                                      # connects 2,2
    put(fed, "2,1", "mouse", "B")                                     # enemy adjacent to 2,2
    rules.apply_action(fed, PlaceAction("muskrat", ("cr", "2,2")))
    if fed.pending is not None:
        rules.apply_action(fed, ChoiceAction("2,1"))
    assert fed.owner_of("2,1") is None and "mouse" in fed.remove_pile

    unfed = make_state(current="A", hands={"A": ["muskrat"]})
    put(unfed, "1,2", "lion", "A")
    put(unfed, "2,1", "mouse", "B")
    rules.apply_action(unfed, PlaceAction("muskrat", ("cr", "2,2")))
    assert unfed.owner_of("2,1") == "B"                               # no removal offered


def test_fed_muskrat_survives_the_hippo_it_removes():
    """A fed Muskrat placed next to an enemy Hippo removes it FIRST (roar before
    reactions, decision 8); the Hippo's queued reactive removal then fizzles because its
    source is gone - Muskrat lives. An UNfed Muskrat (str 2 <= Hippo's max) is still
    removed by the Hippo, which survives."""
    fed = make_state(current="A", hands={"A": ["muskrat"]})
    fed.turn_flags["food_gained_A"] = CFG.fed_threshold
    put(fed, "1,2", "lion", "A")                                      # connects 2,2
    put(fed, "2,1", "hippopotamus", "B")                             # enemy Hippo adjacent
    rules.apply_action(fed, PlaceAction("muskrat", ("cr", "2,2")))
    if fed.pending is not None:
        rules.apply_action(fed, ChoiceAction("2,1"))                  # Muskrat removes the Hippo
    assert fed.owner_of("2,2") == "A"                                 # Muskrat survives...
    assert fed.owner_of("2,1") is None                               # ...and the Hippo is gone
    assert "hippopotamus" in fed.remove_pile and "muskrat" not in fed.remove_pile

    unfed = make_state(current="A", hands={"A": ["muskrat"]})
    put(unfed, "1,2", "lion", "A")
    put(unfed, "2,1", "hippopotamus", "B")
    rules.apply_action(unfed, PlaceAction("muskrat", ("cr", "2,2")))
    assert unfed.owner_of("2,2") is None                             # Hippo removes the Muskrat
    assert unfed.owner_of("2,1") == "B"                              # Hippo survives
    assert "muskrat" in unfed.remove_pile


def test_groundhog_gains_food_only_when_fed():
    fed = make_state(hands={"A": ["groundhog"]})
    fed.turn_flags["food_gained_A"] = CFG.fed_threshold
    rules.apply_action(fed, PlaceAction("groundhog", ("cr", "1,2")))
    assert fed.food["A"] == CFG.groundhog_food

    unfed = make_state(hands={"A": ["groundhog"]})
    rules.apply_action(unfed, PlaceAction("groundhog", ("cr", "1,2")))
    assert unfed.food["A"] == 0



# ------------------------------------------------------------------ go-wide rodent payoff

def test_rat_king_gains_food_per_other_rodent_and_draws():
    s = make_state(hands={"A": ["rat_king"]}, decks={"A": ["lion"], "B": []})
    put(s, "1,1", "squirrel", "A")                                    # Rodent
    put(s, "1,3", "hamster", "A")                                     # Rodent
    rules.apply_action(s, PlaceAction("rat_king", ("cr", "1,2")))
    assert s.food["A"] == 2 * CFG.rat_king_per_rodent                 # two OTHER rodents
    assert "lion" in hand_ids(s, "A")                                 # drew 1


def test_hedgehog_feeds_and_its_spines_remove_the_first_coverer():
    s = make_state(hands={"A": ["hedgehog"]})
    rules.apply_action(s, PlaceAction("hedgehog", ("cr", "1,2")))
    assert s.food["A"] == CFG.hedgehog_food

    s = make_state(current="B", hands={"B": ["lion"]})
    put(s, "4,2", "caracal", "B")                                       # B connects to 3,2
    hedgehog = put(s, "3,2", "hedgehog", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))           # 7 covers 5...
    assert s.top_unit("3,2") is hedgehog and "lion" in s.remove_pile    # ...and is removed


# ------------------------------------------------------------------- Chipmunk (tempo)

def test_chipmunk_grants_an_extra_action_next_turn():
    s = make_state(hands={"A": ["chipmunk"]},
                   decks={"A": ["mouse"] * 12, "B": ["mouse"] * 12})
    rules.apply_action(s, PlaceAction("chipmunk", ("cr", "1,2")))     # action 1
    assert len(s.hands["A"]) == 0                                     # no draw
    assert any(x["step"]["op"] == "grant_action" for x in s.scheduled)
    advance_to(s, 2)                                                  # into A's next turn
    assert s.turn_flags.get("bonus_actions_A") == CFG.chipmunk_bonus_actions

    before = s.turn_counter
    for _ in range(CFG.actions_per_turn + CFG.chipmunk_bonus_actions):
        assert s.current == "A"                                       # turn stays open for 3 actions
        rules.apply_action(s, DrawAction())
    assert s.turn_counter == before + 1                              # ended only after the 3rd


# ------------------------------------------------------------------- Armadillo aura

def test_armadillo_shields_adjacent_ally_from_targeted_removal():
    s = make_state(current="B", hands={"B": ["jaguar"]})
    put(s, "4,2", "lion", "B")                                        # connects B's 3,2
    put(s, "2,2", "squirrel", "A")                                    # str 3, a jaguar target (<=5)
    put(s, "2,1", "armadillo", "A")                                   # adjacent -> grants Stealth
    rules.apply_action(s, PlaceAction("jaguar", ("cr", "3,2")))
    assert s.pending is None                                          # no legal target: it's sheltered
    assert s.owner_of("2,2") == "A"


def test_armadillo_absent_the_ally_is_removable():
    s = make_state(current="B", hands={"B": ["jaguar"]})
    put(s, "4,2", "lion", "B")
    put(s, "2,2", "squirrel", "A")
    rules.apply_action(s, PlaceAction("jaguar", ("cr", "3,2")))
    if s.pending is not None:
        rules.apply_action(s, ChoiceAction("2,2"))
    assert s.owner_of("2,2") is None                                 # removed without the shield
