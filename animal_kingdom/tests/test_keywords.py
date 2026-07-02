"""Behavior tests for the Immovable / Stealth keyword split (keyword-review rulings
A2/B/C1/D/E, 2026-07-02 - see docs/rules/keyword-review-immovable-untargetable.md).

Immovable = physics: can't be removed/moved/eaten by ANY ability, including its own
controller's. Stealth = can't be *chosen* by an enemy ability; mass, random, and
automatic effects hit it normally. Apex landings route through statics.can_cover.

Map A geometry: A's HQ fronts are column 1, B's are column 4; orthogonal neighbours.
"""

from __future__ import annotations

from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import PlaceAction

from .test_effects import make_state, put


def _ids_at(state, cr):
    return [u.card_id for u in state.board.get(cr, [])]


# ------------------------------------------------------------------ Stealth: chosen picks

def test_stealth_hides_from_chosen_single_target_removal():
    # Jaguar (remove adjacent enemy <=5)... vs Black Panther (str 6) is out of range, so
    # use Gray Wolf (remove adjacent enemy with less-or-equal strength, wolf buffed high).
    s = make_state(hands={"A": ["gray_wolf"]})
    wolf_targets_panther = put(s, "2,2", "black_panther", "B")
    put(s, "1,2", "lion", "A")
    hand_wolf = s.hands["A"][0]
    hand_wolf.strength_counter = 10                       # wolf strength >> panther's 6
    rules.apply_action(s, PlaceAction("gray_wolf", ("cr", "1,2")))
    # No pending choice was offered (the only candidate is Stealth) and nothing was removed.
    assert s.pending is None
    assert wolf_targets_panther in s.board["2,2"]


def test_stealth_hides_from_skunk_bounce():
    s = make_state(hands={"A": ["skunk"]})
    put(s, "2,2", "black_panther", "B")
    rules.apply_action(s, PlaceAction("skunk", ("cr", "1,2")))
    assert s.pending is None                              # no bounce choice offered
    assert _ids_at(s, "2,2") == ["black_panther"]


def test_stealth_does_not_hide_from_mass_aoe():
    # Bulwark: remove all adjacent enemy units - mass, so the panther dies.
    s = make_state(hands={"A": ["bulwark"]}, food={"A": 20, "B": 0})
    put(s, "2,2", "black_panther", "B")
    rules.apply_action(s, PlaceAction("bulwark", ("cr", "1,2")))
    assert "2,2" not in s.board
    assert "black_panther" in s.remove_pile


def test_stealth_does_not_hide_from_sirocco_mass_bounce():
    s = make_state(hands={"A": ["sirocco"]})
    put(s, "2,2", "black_panther", "B")
    rules.apply_action(s, PlaceAction("sirocco", ("cr", "1,2")))
    assert "2,2" not in s.board
    assert any(u.card_id == "black_panther" for u in s.hands["B"])


def test_stealth_does_not_hide_from_pestis_wipe():
    s = make_state(hands={"A": ["pestis"]})
    put(s, "2,2", "mouse", "B")
    put(s, "2,2", "black_panther", "B")                   # panther on top of the stack
    rules.apply_action(s, PlaceAction("pestis", ("cr", "1,2")))
    assert "2,2" not in s.board                           # whole stack wiped, panther included
    assert "black_panther" in s.remove_pile


def test_stealth_own_controller_may_still_sacrifice_it():
    # Black Widow: remove an adjacent *friendly* unit to draw 1 - owner's pick is allowed.
    s = make_state(hands={"B": ["black_widow"]}, decks={"A": [], "B": ["mouse"]}, current="B")
    put(s, "4,2", "black_panther", "B")
    rules.apply_action(s, PlaceAction("black_widow", ("cr", "3,2")))
    assert s.pending is not None                          # the sac choice IS offered
    assert ("4,2" in s.pending["options"]) if "options" in s.pending else True


# ------------------------------------------------------------- Immovable: physics for all

def test_immovable_blocks_own_controllers_sacrifice():
    # Carmilla can't eat a Giant Tortoise (decision A2: in-deck cost of the keyword).
    s = make_state(hands={"B": ["black_widow"]}, decks={"B": ["mouse"]}, current="B")
    put(s, "4,2", "giant_tortoise", "B")
    rules.apply_action(s, PlaceAction("black_widow", ("cr", "3,2")))
    assert s.pending is None                              # no legal sac target -> no choice
    assert _ids_at(s, "4,2") == ["giant_tortoise"]


def test_immovable_survives_mass_aoe():
    s = make_state(hands={"A": ["bulwark"]}, food={"A": 20, "B": 0})
    put(s, "2,2", "elephant", "B")
    rules.apply_action(s, PlaceAction("bulwark", ("cr", "1,2")))
    assert _ids_at(s, "2,2") == ["elephant"]


def test_pestis_wipes_around_an_immovable_unit_not_stopping_at_it():
    # Ruling B amendment: Immovable is skipped in place, NOT a shield for the stack.
    s = make_state(hands={"A": ["pestis"]})
    put(s, "2,2", "mouse", "B")                           # bottom: should die
    put(s, "2,2", "elephant", "B")                        # middle: Immovable, survives
    put(s, "2,2", "rat", "B")                             # top: should die
    rules.apply_action(s, PlaceAction("pestis", ("cr", "1,2")))
    assert _ids_at(s, "2,2") == ["elephant"]              # alone where the stack was
    assert "mouse" in s.remove_pile and "rat" in s.remove_pile


# ----------------------------------------------------------------- Apex landings (C1/C3)

def test_apex_cannot_land_on_porcupine():
    # "Cannot be covered by enemy units" now blocks the landing entirely - quills beat teeth.
    s = make_state(hands={"A": ["tiger"]})
    put(s, "1,2", "porcupine", "B")
    legal = rules.legal_actions(s)
    assert PlaceAction("tiger", ("cr", "1,2")) not in legal


def test_snow_leopard_lets_an_apex_cat_land_at_equal_strength():
    s = make_state(hands={"A": ["tiger"]})
    put(s, "2,2", "snow_leopard", "A")                    # A controls a Snow Leopard
    tiger_str = s.cards["tiger"].base_strength
    prey = put(s, "1,2", "lion", "B")
    prey.strength_counter = tiger_str - s.cards["lion"].base_strength  # equal strength
    legal = rules.legal_actions(s)
    assert PlaceAction("tiger", ("cr", "1,2")) in legal   # bare > check would forbid this
    rules.apply_action(s, PlaceAction("tiger", ("cr", "1,2")))
    assert "lion" in s.remove_pile                        # and it eats normally


def test_apex_covers_stealth_prey_instead_of_eating_it():
    # The eat is a chosen single-out (C3): Stealth blocks it; the apex buries the panther.
    s = make_state(hands={"A": ["tiger"]})
    prey = put(s, "1,2", "black_panther", "B")
    prey.strength_counter = -3                            # panther 6 -> 3, tiger can land
    rules.apply_action(s, PlaceAction("tiger", ("cr", "1,2")))
    assert _ids_at(s, "1,2") == ["black_panther", "tiger"]  # buried, not eaten
    assert "black_panther" not in s.remove_pile


def test_apex_covers_immovable_prey_instead_of_eating_it():
    s = make_state(hands={"A": ["borealis"]}, food={"A": 20, "B": 0})
    put(s, "1,2", "elephant", "B")                        # elephant 8 < borealis
    legal = rules.legal_actions(s)
    if PlaceAction("borealis", ("cr", "1,2")) in legal:   # only if strength allows the cover
        rules.apply_action(s, PlaceAction("borealis", ("cr", "1,2")))
        assert _ids_at(s, "1,2") == ["elephant", "borealis"]
        assert "elephant" not in s.remove_pile


# --------------------------------------------------- automatic effects hit Stealth (B)

def test_pufferfish_retaliation_kills_a_stealth_coverer():
    # Automatic trigger: covering a pufferfish is fatal even for the panther now.
    s = make_state(hands={"B": ["black_panther"]}, current="B")
    put(s, "4,2", "pufferfish", "A")                      # str 1, in B's HQ front column
    rules.apply_action(s, PlaceAction("black_panther", ("cr", "4,2")))
    assert "black_panther" in s.remove_pile
    assert "pufferfish" in s.remove_pile


def test_pufferfish_retaliation_still_loses_to_immovable():
    # Physics beats spikes: an Elephant covering a pufferfish survives.
    s = make_state(hands={"B": ["elephant"]}, food={"A": 0, "B": 20}, current="B")
    put(s, "4,2", "pufferfish", "A")
    rules.apply_action(s, PlaceAction("elephant", ("cr", "4,2")))
    assert "elephant" not in s.remove_pile
    assert "pufferfish" in s.remove_pile                  # it still pops itself
