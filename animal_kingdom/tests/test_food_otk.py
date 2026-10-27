"""Golden tests for the pure-OTK food_otk overhaul (2026-07-05).

Covers the signature mechanic ("food gained this turn") and its cards (Food Aggro's since the launch decks): Barley,
Scrooge, Beaver (bonus action), Hedgehog, Gopher, Muskrat, Groundhog, and the Armadillo and Porcupine auras. Map A geometry
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
    advance_to(s, 4)                                                   # into A's next turn
    assert effects._food_gained_this_turn(s, "A") == 0                # reset each turn


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


def test_fed_muskrat_and_the_hippo_it_removes_go_together():
    """A fed Muskrat placed next to an enemy Hippo removes it first (roar before reactions), and the Hippo's
    removal, already set off by the placement, still takes the Muskrat (Martin, 2026-10-27). An UNfed
    Muskrat (str 2 <= Hippo's max) is removed by the Hippo, which survives."""
    fed = make_state(current="A", hands={"A": ["muskrat"]})
    fed.turn_flags["food_gained_A"] = CFG.fed_threshold
    put(fed, "1,2", "lion", "A")                                      # connects 2,2
    put(fed, "2,1", "hippopotamus", "B")                             # enemy Hippo adjacent
    rules.apply_action(fed, PlaceAction("muskrat", ("cr", "2,2")))
    if fed.pending is not None:
        rules.apply_action(fed, ChoiceAction("2,1"))                  # Muskrat removes the Hippo
    assert fed.owner_of("2,2") is None and fed.owner_of("2,1") is None
    assert "hippopotamus" in fed.remove_pile and "muskrat" in fed.remove_pile

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
    s = make_state(hands={"A": ["rat_legend"]}, decks={"A": ["lion"], "B": []})
    put(s, "1,1", "squirrel", "A")                                    # Rodent
    put(s, "1,3", "chipmunk", "A")                                     # Rodent
    rules.apply_action(s, PlaceAction("rat_legend", ("cr", "1,2")))
    assert s.food["A"] == 2 * CFG.rat_king_per_rodent                 # two OTHER rodents
    assert "lion" in hand_ids(s, "A")                                 # drew 1


def test_hedgehogs_spines_remove_the_first_coverer():
    s = make_state(hands={"A": ["hedgehog"]})
    rules.apply_action(s, PlaceAction("hedgehog", ("cr", "1,2")))
    assert s.food["A"] == 0                                             # the Spikes common: no food Roar (2026-10-21)

    s = make_state(current="B", hands={"B": ["lion"]})
    put(s, "4,2", "caracal", "B")                                       # B connects to 3,2
    hedgehog = put(s, "3,2", "hedgehog", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))           # 7 covers 5...
    assert s.top_unit("3,2") is hedgehog and "lion" in s.remove_pile    # ...and is removed


# --------------------------------------------------------------------- Beaver (tempo)

def test_beaver_grants_an_extra_action_next_turn():
    s = make_state(hands={"A": ["beaver"]},
                   decks={"A": ["mouse"] * 12, "B": ["mouse"] * 12})
    rules.apply_action(s, PlaceAction("beaver", ("cr", "1,2")))     # action 1
    assert len(s.hands["A"]) == 0                                     # no draw
    assert any(x["step"]["op"] == "grant_action" for x in s.scheduled)
    advance_to(s, 4)                                                  # into A's next turn
    assert s.turn_flags.get("bonus_actions_A") == CFG.beaver_bonus_actions

    before = s.turn_counter
    for _ in range(CFG.actions_per_turn + CFG.beaver_bonus_actions):
        assert s.current == "A"                                       # turn stays open for 3 actions
        rules.apply_action(s, DrawAction())
    assert s.turn_counter == before + 1                              # ended only after the 3rd


def test_the_electric_eel_leaves_the_opponent_only_one_action_next_turn():
    """The Beaver's mirror (Martin, 2026-10-22): "Roar: your opponent takes only 1 action next turn". Two Eels change
    nothing more: one action is the floor the text names."""
    s = make_state(hands={"A": ["electric_eel"] * 3}, decks={"A": ["mouse"] * 12, "B": ["mouse"] * 12})
    rules.apply_action(s, PlaceAction("electric_eel", ("cr", "1,2")))
    rules.apply_action(s, DrawAction())                               # A's turn ends
    assert s.current == "B" and rules.turn_actions(s) == CFG.eel_actions == 1
    rules.apply_action(s, DrawAction())
    assert s.current == "A"                                           # B's turn ended after its one action
    assert rules.turn_actions(s) == CFG.actions_per_turn              # and A's own turn is whole
    rules.apply_action(s, PlaceAction("electric_eel", ("cr", "1,1")))
    rules.apply_action(s, PlaceAction("electric_eel", ("cr", "1,3")))
    assert s.current == "B" and rules.turn_actions(s) == 1


# ------------------------------------------------------------------- Armadillo and Porcupine auras

def test_armadillo_shields_adjacent_ally_from_targeted_removal():
    s = make_state(current="B", hands={"B": ["jaguar"]})
    put(s, "4,2", "lion", "B")                                        # connects B's 3,2
    put(s, "2,2", "squirrel", "A")                                    # str 3, a jaguar target (<=4)
    put(s, "2,1", "armadillo", "A")                                   # adjacent -> grants Armor
    rules.apply_action(s, PlaceAction("jaguar", ("cr", "3,2")))
    assert s.pending is None                                          # nothing it can remove: it's shielded
    assert s.owner_of("2,2") == "A"


def test_armadillo_absent_the_ally_is_removable():
    s = make_state(current="B", hands={"B": ["jaguar"]})
    put(s, "4,2", "lion", "B")
    put(s, "2,2", "squirrel", "A")
    rules.apply_action(s, PlaceAction("jaguar", ("cr", "3,2")))
    if s.pending is not None:
        rules.apply_action(s, ChoiceAction("2,2"))
    assert s.owner_of("2,2") is None                                 # removed without the shield


def test_armadillo_shields_adjacent_ally_from_mass_removal_too():
    # Armor, not Stealth (2026-10-21): an effect that picks nobody still can't remove it.
    s = make_state(current="B")
    put(s, "2,2", "squirrel", "A")
    put(s, "2,1", "armadillo", "A")
    assert not statics.can_be_removed(s, s.top_unit("2,2"), "2,2")


def test_porcupine_gives_its_neighbours_spikes_each_kills_its_first_coverer():
    s = make_state(current="B", hands={"B": ["lion", "lion"]})
    put(s, "4,2", "caracal", "B")                                     # B connects to 3,2
    squirrel = put(s, "3,2", "squirrel", "A")
    put(s, "3,1", "porcupine", "A")                                   # adjacent -> grants Spikes
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))         # 7 covers 3...
    assert s.top_unit("3,2") is squirrel and "lion" in s.remove_pile  # ...and the borrowed spines remove it
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))         # spent: the second cover holds
    assert s.top_unit("3,2").card_id == "lion"
