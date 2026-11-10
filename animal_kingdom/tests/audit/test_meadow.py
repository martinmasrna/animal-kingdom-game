"""Card audit, Meadow (2026-11-05): does the engine do what each collectible Meadow card's printed text says?

Each test is written from the printed text and the keyword definitions (docs/rules/keywords.md), read literally, with
the rulings in docs/rules/rulings.md where the text leaves room. Map A: A's den fronts are column 1, B's column 4; a
4x3 grid with orthogonal neighbours.
"""

from __future__ import annotations

import pytest

from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import SKIP, ChoiceAction, DrawAction, PassAction, PlaceAction
from animal_kingdom.engine.cards import load_cards
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.state import WILD
from animal_kingdom.engine.strength import effective_strength, placement_strength

from .._helpers import apply_click, hand_ids, make_state, place_targets, put

CFG = Config.default()
CARDS = load_cards()


def base(card_id):
    return CARDS[card_id].base_strength


def end_turn(s):
    s.idle_turns = 0
    rules.apply_action(s, PassAction())


def choose(s, option):
    assert s.pending is not None and option in s.pending["options"], (option, s.pending)
    rules.apply_action(s, ChoiceAction(option))


def hand_inst(s, player, card_id):
    return next(u for u in s.hands[player] if u.card_id == card_id)


def decks(a=("lion",) * 6, b=("lion",) * 6):
    return {"A": list(a), "B": list(b)}


def assert_flight(card_id):
    """Flight: placeable ignoring connection (3,2 is nowhere near A's chain), never onto the enemy den."""
    s = make_state(hands={"A": [card_id]}, decks=decks())
    assert "3,2" in place_targets(s)
    assert not any(isinstance(a, PlaceAction) and a.target[0] == "hq" for a in rules.legal_actions(s))
    put(s, "4,2", "lion", "B")                             # even next to the den with no chain of A's, no capture
    assert not any(isinstance(a, PlaceAction) and a.target[0] == "hq" for a in rules.legal_actions(s))


# ------------------------------------------------------------------------------------------------ Queen Melissia

def test_bee_legend_draws_a_worker_a_soldier_and_a_nurse():
    # "Roar: draw a Worker, a Soldier and a Nurse Colony animal."
    deck = ["lion", "worker_bee", "lion", "guard_bee", "lion", "nurse_bee", "lion"]
    s = make_state(hands={"A": ["bee_legend"]}, decks=decks(deck))
    rules.apply_action(s, PlaceAction("bee_legend", ("cr", "1,2")))
    assert sorted(hand_ids(s, "A")) == ["guard_bee", "nurse_bee", "worker_bee"]
    assert s.decks["A"].count("lion") == 4


def test_bee_legend_draws_only_what_the_deck_holds():
    s = make_state(hands={"A": ["bee_legend"]}, decks=decks(["lion", "worker_bee", "lion", "nurse_bumblebee"]))
    rules.apply_action(s, PlaceAction("bee_legend", ("cr", "1,2")))
    assert sorted(hand_ids(s, "A")) == ["nurse_bumblebee", "worker_bee"]      # no Soldier in the deck: none drawn


# ------------------------------------------------------------------------------------------------ Lord Bumbleton

def test_bumblebee_legend_adds_three_to_each_food_gain_of_yours_only():
    # "Flight. Whenever you gain food, gain 3 additional food."
    s = make_state(hands={"A": ["worker_bee"], "B": ["worker_bee"]}, decks=decks())
    put(s, "2,2", "bumblebee_legend", "A")
    rules.apply_action(s, PlaceAction("worker_bee", ("cr", "1,2")))
    assert s.food["A"] == CFG.worker_bee_food + CFG.bumblebee_legend_food_rider       # once, not a loop
    end_turn(s)
    rules.apply_action(s, PlaceAction("worker_bee", ("cr", "4,2")))
    assert s.food["B"] == CFG.worker_bee_food                                          # the opponent's gain: no rider
    assert s.food["A"] == CFG.worker_bee_food + CFG.bumblebee_legend_food_rider


def test_bumblebee_legend_no_food_no_rider():
    s = make_state(hands={"A": ["lion"]}, decks=decks())
    put(s, "2,2", "bumblebee_legend", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "1,2")))
    assert s.food["A"] == 0


def test_bumblebee_legend_rides_on_region_income_and_not_when_buried():
    s = make_state(decks=decks())
    for cr in ("1,1", "2,1", "1,2"):
        put(s, cr, "fox", "A")
    put(s, "2,2", "bumblebee_legend", "A")                   # the fourth corner of R1
    end_turn(s)                                               # A's region pays at the end of A's turn
    assert s.food["A"] == 10 + CFG.bumblebee_legend_food_rider
    s2 = make_state(hands={"A": ["worker_bee"]}, decks=decks())
    put(s2, "2,2", "bumblebee_legend", "A")
    put(s2, "2,2", "lion", "B")                               # buried: its effect is off
    rules.apply_action(s2, PlaceAction("worker_bee", ("cr", "1,2")))
    assert s2.food["A"] == CFG.worker_bee_food


def test_bumblebee_legend_has_flight():
    assert_flight("bumblebee_legend")


# ------------------------------------------------------------------------------------------------ Nurse Bee

def test_nurse_bee_draws_two_with_four_colony_counting_itself():
    # "Flight. Roar: if you control 4 or more Colony animals, draw 2 cards." Once placed, it is one of them.
    s = make_state(hands={"A": ["nurse_bee"]}, decks=decks())
    for cr in ("1,1", "1,3", "2,1"):
        put(s, cr, "worker_bee", "A")
    rules.apply_action(s, PlaceAction("nurse_bee", ("cr", "3,2")))
    assert hand_ids(s, "A") == ["lion"] * CFG.nurse_bee_draw


def test_nurse_bee_no_draw_with_three_colony():
    s = make_state(hands={"A": ["nurse_bee"]}, decks=decks())
    for cr in ("1,1", "1,3"):
        put(s, cr, "worker_bee", "A")
    put(s, "2,1", "worker_bee", "B")                        # the opponent's Colony animal isn't yours
    rules.apply_action(s, PlaceAction("nurse_bee", ("cr", "1,2")))
    assert hand_ids(s, "A") == []


def test_nurse_bee_has_flight():
    assert_flight("nurse_bee")


# ------------------------------------------------------------------------------------------------ Nurse Bumblebee

def test_nurse_bumblebee_draws_a_colony_animal():
    # "Flight. Roar: draw a Colony animal."
    s = make_state(hands={"A": ["nurse_bumblebee"]}, decks=decks(["lion", "worker_bee", "tiger"]))
    rules.apply_action(s, PlaceAction("nurse_bumblebee", ("cr", "3,2")))
    assert hand_ids(s, "A") == ["worker_bee"]


def test_nurse_bumblebee_no_colony_in_deck_draws_nothing():
    s = make_state(hands={"A": ["nurse_bumblebee"]}, decks=decks(["lion", "tiger"]))
    rules.apply_action(s, PlaceAction("nurse_bumblebee", ("cr", "1,2")))
    assert hand_ids(s, "A") == [] and len(s.decks["A"]) == 2


def test_nurse_bumblebee_has_flight():
    assert_flight("nurse_bumblebee")


# ------------------------------------------------------------------------------------------------ Queen Bee

@pytest.mark.parametrize("pick", ["worker_bee", "guard_bee", "nurse_bee"])
def test_queen_bee_adds_the_chosen_bee_to_hand(pick):
    # "Roar: add a Worker Bee, Soldier Bee or Nurse Bee to your hand." Added, not drawn: an empty deck is no matter.
    s = make_state(hands={"A": ["queen_bee"]}, decks={"A": [], "B": []})
    rules.apply_action(s, PlaceAction("queen_bee", ("cr", "1,2")))
    assert sorted(s.pending["options"]) == ["guard_bee", "nurse_bee", "worker_bee"]
    assert CARDS["guard_bee"].name == "Soldier Bee"
    choose(s, pick)
    assert hand_ids(s, "A") == [pick] and s.decks["A"] == []


# ------------------------------------------------------------------------------------------------ Worker Bee

def test_worker_bee_gains_twelve_food():
    # "Flight. Roar: gain 12 food."
    s = make_state(hands={"A": ["worker_bee"]}, food={"A": 3, "B": 0}, decks=decks())
    rules.apply_action(s, PlaceAction("worker_bee", ("cr", "3,2")))
    assert s.food == {"A": 3 + 12, "B": 0}
    assert CFG.worker_bee_food == 12


def test_worker_bee_has_flight():
    assert_flight("worker_bee")


# ------------------------------------------------------------------------------------------------ Praying Mantis

def test_praying_mantis_removes_an_adjacent_ally_and_draws_two():
    # "Roar: remove an adjacent ally to draw 2 cards."
    s = make_state(hands={"A": ["praying_mantis"]}, decks=decks())
    put(s, "1,1", "fox", "A")
    put(s, "2,2", "fox", "B")                               # an enemy is no ally
    rules.apply_action(s, PlaceAction("praying_mantis", ("cr", "1,2")))
    assert set(s.pending["options"]) - {SKIP} == {"1,1"}
    choose(s, "1,1")
    assert "1,1" not in s.board and "fox" in s.remove_pile
    assert hand_ids(s, "A") == ["lion"] * CFG.mantis_draw
    assert s.top_unit("2,2").card_id == "fox"


def test_praying_mantis_with_no_adjacent_ally_draws_nothing():
    s = make_state(hands={"A": ["praying_mantis"]}, decks=decks())
    put(s, "2,2", "fox", "B")
    put(s, "1,3", "fox", "A")                               # an ally, but not adjacent to 1,1
    rules.apply_action(s, PlaceAction("praying_mantis", ("cr", "1,1")))
    assert s.pending is None and hand_ids(s, "A") == []
    assert s.top_unit("2,2").card_id == "fox" and s.top_unit("1,3").card_id == "fox"


def test_praying_mantis_cannot_remove_an_armored_ally():
    s = make_state(hands={"A": ["praying_mantis"]}, decks=decks())
    put(s, "1,1", "tortoise", "A")
    rules.apply_action(s, PlaceAction("praying_mantis", ("cr", "1,2")))
    assert s.pending is None and hand_ids(s, "A") == [] and s.top_unit("1,1").card_id == "tortoise"


# ------------------------------------------------------------------------------------------------ Earthworm

def test_earthworm_fall_draws_and_places_two_worms():
    # "Fall: draw a card and place two Worms on its crossroad."
    s = make_state(hands={"A": ["praying_mantis"]}, decks=decks())
    put(s, "1,1", "earthworm", "A")
    rules.apply_action(s, PlaceAction("praying_mantis", ("cr", "1,2")))
    choose(s, "1,1")
    assert len(s.hands["A"]) == CFG.mantis_draw + 1
    assert [(u.card_id, u.owner) for u in s.board["1,1"]] == [("worm", "A"), ("worm", "A")]
    assert "earthworm" in s.remove_pile


def test_earthworm_covered_is_not_removed_so_no_fall():
    s = make_state(current="B", hands={"B": ["lion"]}, decks=decks())
    put(s, "4,2", "lion", "B")
    put(s, "3,2", "earthworm", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))
    assert [u.card_id for u in s.board["3,2"]] == ["earthworm", "lion"]
    assert hand_ids(s, "A") == []


def test_earthworm_eaten_by_an_enemy_predator_still_draws():
    # Eaten is removed: Fall happens. The crossroad is under the enemy predator, so (rulings.md) no Worms land.
    s = make_state(current="B", hands={"B": ["tiger"]}, decks=decks())
    put(s, "4,2", "lion", "B")
    put(s, "3,2", "earthworm", "A")
    rules.apply_action(s, PlaceAction("tiger", ("cr", "3,2")))
    assert "earthworm" in s.remove_pile and len(s.hands["A"]) == 1
    assert [u.card_id for u in s.board["3,2"]] == ["tiger"]


# ------------------------------------------------------------------------------------------------ Toad

def test_toad_poison_removes_the_enemy_coverer_at_the_start_of_the_toads_controllers_turn():
    # "Poison." When an enemy covers it, that enemy is removed at the start of your next turn. Every time.
    s = make_state(current="B", hands={"B": ["lion", "lion"]}, decks=decks())
    put(s, "4,2", "caracal", "B")
    toad = put(s, "3,2", "toad", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))
    assert s.top_unit("3,2").card_id == "lion"               # the coverer keeps the rest of its turn
    end_turn(s)
    assert s.current == "A" and s.top_unit("3,2") is toad and "lion" in s.remove_pile
    end_turn(s)
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))    # every time, not once
    end_turn(s)
    assert s.top_unit("3,2") is toad


def test_toad_friendly_cover_is_not_poisoned():
    s = make_state(hands={"A": ["lion"]}, decks=decks())
    put(s, "1,2", "toad", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "1,2")))
    end_turn(s); end_turn(s)
    assert s.top_unit("1,2").card_id == "lion"


# ------------------------------------------------------------------------------------------------ The First of Many

def test_locust_legend_covers_the_board_with_wild_locusts_that_eat_in_two_turns():
    # "Roar: cover the board with Locusts." Locust: "Wild. In 2 turns, remove the animal underneath, then fly away."
    s = make_state(hands={"A": ["locust_legend"]}, decks=decks())
    lion = put(s, "3,2", "lion", "B")
    rules.apply_action(s, PlaceAction("locust_legend", ("cr", "1,2")))
    assert all(s.board[c][-1].card_id == "locust_swarm" and s.board[c][-1].owner == WILD for c in s.game_map.crossroads)
    assert s.board["3,2"][-2] is lion
    end_turn(s)                                              # turn 1 of 2: the opponent's
    assert s.board["3,2"][-1].card_id == "locust_swarm"
    end_turn(s)                                              # turn 2: the caster's; the swarm eats and flies away
    assert "3,2" not in s.board and "1,2" not in s.board
    assert not any(u.card_id == "locust_swarm" for st in s.board.values() for u in st)


# ------------------------------------------------------------------------------------------------ Hare

def test_hare_draws_two_when_it_leaves_the_hand_empty():
    # "Flee. Roar: if your hand is empty, draw 2 cards."
    s = make_state(hands={"A": ["hare"]}, decks=decks())
    rules.apply_action(s, PlaceAction("hare", ("cr", "1,3")))
    assert hand_ids(s, "A") == ["lion"] * CFG.hare_draw


def test_hare_draws_nothing_with_a_card_left_in_hand():
    s = make_state(hands={"A": ["fox", "hare"]}, decks=decks())
    rules.apply_action(s, PlaceAction("hare", ("cr", "1,3")))
    assert hand_ids(s, "A") == ["fox"]


def test_hare_flees_to_hand_when_an_enemy_covers_it():
    s = make_state(current="B", hands={"B": ["lion"]}, decks=decks())
    put(s, "4,2", "lion", "B")
    put(s, "3,2", "hare", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))
    assert [u.card_id for u in s.board["3,2"]] == ["lion"] and hand_ids(s, "A") == ["hare"]
    assert "hare" not in s.remove_pile


# ------------------------------------------------------------------------------------------------ Mole

def test_mole_plays_another_animal_next_to_it_for_free():
    # "Roar: play another animal next to this."
    s = make_state(hands={"A": ["mole", "lion"]}, decks=decks())
    rules.apply_action(s, PlaceAction("mole", ("cr", "1,1")))
    assert s.pending is not None and s.pending["mode"] == "place"
    targets = {tuple(p["target"]) for p in s.pending["placements"]}
    assert targets == {("cr", "1,2"), ("cr", "2,1")}             # 1,3 is connected but not next to the Mole
    rules.apply_action(s, PlaceAction("lion", ("cr", "2,1")))
    assert s.top_unit("2,1").card_id == "lion"
    assert s.actions_taken_this_turn == 1 and s.player_to_act() == "A"


def test_mole_with_an_empty_hand_does_nothing():
    s = make_state(hands={"A": ["mole"]}, decks=decks())
    rules.apply_action(s, PlaceAction("mole", ("cr", "1,1")))
    assert s.pending is None


def test_mole_free_play_still_needs_strength_to_cover():
    s = make_state(hands={"A": ["mole", "fox"]}, decks=decks())
    put(s, "1,2", "lion", "B"); put(s, "2,1", "lion", "B")       # both neighbours hold a 7: a Fox (3) covers neither
    rules.apply_action(s, PlaceAction("mole", ("cr", "1,1")))
    assert s.pending is None or not s.pending.get("placements")
    assert hand_ids(s, "A") == ["fox"]


# ------------------------------------------------------------------------------------------------ [MOLE]

def test_mole_legend_draws_plays_then_discards():
    # "Roar: draw a card, play another animal, then discard a card."
    s = make_state(hands={"A": ["mole_legend", "fox", "tiger"]}, decks=decks(["squirrel"]))
    rules.apply_action(s, PlaceAction("mole_legend", ("cr", "1,2")))
    assert "squirrel" in hand_ids(s, "A")
    assert s.pending["mode"] == "place"
    rules.apply_action(s, PlaceAction("squirrel", ("cr", "1,1")))     # the drawn card may be the one played
    assert s.food["A"] == CFG.squirrel_food                           # a play: its Roar happens
    assert s.pending["mode"] == "choice"
    choose(s, hand_inst(s, "A", "tiger").iid)
    assert hand_ids(s, "A") == ["fox"] and s.actions_taken_this_turn == 1


def test_mole_legend_with_nothing_to_play_still_discards():
    # A Titan can't be paid for by a free play, so nothing can be played; the discard still happens.
    s = make_state(hands={"A": ["mole_legend", "blue_whale"]}, decks={"A": [], "B": []})
    rules.apply_action(s, PlaceAction("mole_legend", ("cr", "1,2")))
    if s.pending and s.pending["mode"] == "choice":
        choose(s, hand_inst(s, "A", "blue_whale").iid)
    assert s.pending is None
    assert hand_ids(s, "A") == [] and "blue_whale" in s.remove_pile


# ------------------------------------------------------------------------------------------------ Gopher

def test_gopher_removes_an_adjacent_enemy_after_ten_food_this_turn():
    # "Roar: if you gained 10 or more food this turn, remove an adjacent enemy." Any strength.
    s = make_state(hands={"A": ["worker_bee", "gopher"]}, decks=decks())
    put(s, "2,2", "lion", "B")
    rules.apply_action(s, PlaceAction("worker_bee", ("cr", "3,1")))
    apply_click(s, PlaceAction("gopher", ("cr", "1,2")))
    assert "2,2" not in s.board and "lion" in s.remove_pile


def test_gopher_unfed_removes_nothing_however_much_food_is_banked():
    s = make_state(hands={"A": ["gopher"]}, food={"A": 60, "B": 0}, decks=decks())
    put(s, "2,2", "lion", "B")
    apply_click(s, PlaceAction("gopher", ("cr", "1,2")))
    assert s.top_unit("2,2").card_id == "lion"


def test_gopher_fed_but_no_adjacent_enemy():
    s = make_state(hands={"A": ["worker_bee", "gopher"]}, decks=decks())
    put(s, "1,1", "fox", "A")
    rules.apply_action(s, PlaceAction("worker_bee", ("cr", "3,1")))
    apply_click(s, PlaceAction("gopher", ("cr", "1,2")))
    assert s.top_unit("1,1").card_id == "fox" and s.pending is None


def test_gopher_cannot_remove_armor_or_choose_stealth():
    s = make_state(hands={"A": ["worker_bee", "gopher"]}, decks=decks())
    put(s, "2,2", "tortoise", "B")
    put(s, "1,1", "stick_insect", "B")
    rules.apply_action(s, PlaceAction("worker_bee", ("cr", "3,1")))
    apply_click(s, PlaceAction("gopher", ("cr", "1,2")))
    assert s.top_unit("2,2").card_id == "tortoise" and s.top_unit("1,1").card_id == "stick_insect"


# ------------------------------------------------------------------------------------------------ Groundhog

def test_groundhog_gains_ten_at_the_start_of_your_turn_only():
    # "Dawn: gain 10 food."
    s = make_state(hands={"A": ["groundhog"]}, decks=decks())
    rules.apply_action(s, PlaceAction("groundhog", ("cr", "1,2")))
    assert s.food["A"] == 0
    end_turn(s)                                               # B's Dawn: nothing for A
    assert s.current == "B" and s.food["A"] == 0
    end_turn(s)
    assert s.current == "A" and s.food["A"] == CFG.groundhog_food == 10


# ------------------------------------------------------------------------------------------------ Hamster

def test_hamster_gains_five_per_card_you_draw():
    # "Whenever you draw a card, gain 5 food."
    s = make_state(decks=decks())
    put(s, "1,2", "hamster", "A")
    rules.apply_action(s, DrawAction())
    assert s.food["A"] == CFG.draw_action_count * CFG.hamster_draw_food
    s.actions_taken_this_turn = CFG.actions_per_turn - 1
    rules.apply_action(s, DrawAction())                       # ends A's turn
    before = s.food["A"]
    rules.apply_action(s, DrawAction())                       # the opponent draws: nothing for A
    assert s.current == "B" and s.food["A"] == before


def test_hamster_buried_gains_nothing():
    # Only a top animal's effects work: a covered Hamster isn't there to see the draw.
    s = make_state(decks=decks())
    put(s, "1,2", "hamster", "A")
    put(s, "1,2", "lion", "B")
    rules.apply_action(s, DrawAction())
    assert s.food["A"] == 0


# ------------------------------------------------------------------------------------------------ Hedgehog

def test_hedgehog_spikes_remove_the_first_enemy_coverer_only():
    # "Spikes." The first time an enemy covers it, that enemy is removed.
    s = make_state(current="B", hands={"B": ["lion", "lion"]}, decks=decks())
    put(s, "4,2", "caracal", "B")
    hh = put(s, "3,2", "hedgehog", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))
    assert s.top_unit("3,2") is hh and "lion" in s.remove_pile
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))
    assert s.top_unit("3,2").card_id == "lion"


def test_hedgehog_friendly_cover_leaves_spikes():
    s = make_state(hands={"A": ["lion"]}, decks=decks())
    hh = put(s, "1,2", "hedgehog", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "1,2")))
    assert s.top_unit("1,2").card_id == "lion" and not hh.retaliation_used


# ------------------------------------------------------------------------------------------------ [BUTTERFLY]

def test_butterfly_legend_evolves_at_dawn_on_the_board():
    # "Dawn: evolve. Whenever this gains strength, evolve."
    s = make_state(decks=decks())
    bf = put(s, "1,2", "butterfly_legend", "A")
    end_turn(s)
    assert bf.card_id == "butterfly_legend"                   # the opponent's Dawn: no
    end_turn(s)
    assert bf.card_id == "butterfly_legend_caterpillar"


def test_butterfly_legend_evolves_when_it_gains_strength():
    s = make_state(hands={"A": ["butterfly", "butterfly_legend"]}, decks=decks())
    bl = hand_inst(s, "A", "butterfly_legend")
    rules.apply_action(s, PlaceAction("butterfly", ("cr", "1,2")))
    choose(s, bl.iid)
    assert bl.card_id == "butterfly_legend_caterpillar"


# ------------------------------------------------------------------------------------------------ Stork

def test_stork_adds_two_younglings_to_hand():
    # "Flight. Roar: add two random younglings to your hand." Added, not drawn.
    s = make_state(hands={"A": ["stork"]}, decks={"A": [], "B": []})
    rules.apply_action(s, PlaceAction("stork", ("cr", "3,2")))
    young = hand_ids(s, "A")
    assert len(young) == CFG.stork_younglings == 2
    assert all(CARDS[c].status == "token" and c.startswith("baby_") for c in young)


def test_stork_has_flight():
    assert_flight("stork")


# ------------------------------------------------------------------------------------------------ Caterpillar

def test_caterpillar_in_hand_gaining_strength_draws_and_becomes_a_butterfly_but_not_on_the_board():
    # "When this gains strength in your hand, draw a card and turn into a Butterfly."
    s = make_state(hands={"A": ["bee_legend_2", "caterpillar"]}, decks=decks(["fox", "fox"]))
    s.starting_decks = {"A": ("bee_legend_2", "caterpillar", "caterpillar", "fox", "fox"), "B": ()}
    in_hand = hand_inst(s, "A", "caterpillar")
    on_board = put(s, "1,1", "caterpillar", "A")
    rules.apply_action(s, PlaceAction("bee_legend_2", ("cr", "1,2")))
    assert in_hand.card_id == "butterfly" and in_hand.strength_counter == CFG.jelly_grant
    assert on_board.card_id == "caterpillar"                  # on the board: nothing
    assert hand_ids(s, "A").count("fox") == 1                 # one card drawn, for the one in hand


def test_caterpillar_turns_even_with_an_empty_deck():
    s = make_state(hands={"A": ["butterfly", "caterpillar"]}, decks={"A": [], "B": []})
    cat = hand_inst(s, "A", "caterpillar")
    rules.apply_action(s, PlaceAction("butterfly", ("cr", "1,2")))
    if s.pending:
        choose(s, cat.iid)
    assert cat.card_id == "butterfly" and cat.strength_counter == CFG.butterfly_grant and hand_ids(s, "A") == ["butterfly"]


def test_caterpillar_without_a_gain_stays():
    s = make_state(hands={"A": ["lion", "caterpillar"]}, decks=decks())
    rules.apply_action(s, PlaceAction("lion", ("cr", "1,2")))
    assert hand_ids(s, "A") == ["caterpillar"]


# ------------------------------------------------------------------------------------------------ Butterfly

def test_butterfly_draws_then_gives_an_animal_in_hand_plus_one():
    # "Flight. Roar: draw a card, then give an animal in your hand +1 strength." The drawn card can take it.
    s = make_state(hands={"A": ["butterfly"]}, decks=decks(["fox"]))
    apply_click(s, PlaceAction("butterfly", ("cr", "3,2")))
    fox = hand_inst(s, "A", "fox")
    assert fox.strength_counter == CFG.butterfly_grant == 1
    assert effective_strength(s, s.top_unit("3,2")) == base("butterfly")   # it is on the board, not in hand


def test_butterfly_with_empty_deck_and_hand_does_nothing():
    s = make_state(hands={"A": ["butterfly"]}, decks={"A": [], "B": []})
    apply_click(s, PlaceAction("butterfly", ("cr", "1,2")))
    assert s.pending is None and hand_ids(s, "A") == []


def test_butterfly_lets_you_choose_which_animal_in_hand():
    s = make_state(hands={"A": ["butterfly", "fox", "lion"]}, decks=decks(["tiger"]))
    rules.apply_action(s, PlaceAction("butterfly", ("cr", "1,2")))
    ids = {u.iid: u for u in s.hands["A"]}
    assert set(s.pending["options"]) - {SKIP} == set(ids)    # the drawn Tiger among them
    lion = hand_inst(s, "A", "lion")
    choose(s, lion.iid)
    assert lion.strength_counter == 1 and hand_inst(s, "A", "fox").strength_counter == 0


def test_butterfly_has_flight():
    assert_flight("butterfly")


# ------------------------------------------------------------------------------------------------ Cuckoo

def test_cuckoo_shuffles_two_eggs_into_the_opponents_deck():
    # "Flight. Roar: shuffle two Cuckoo Eggs into your opponent's deck."
    s = make_state(hands={"A": ["cuckoo"]}, decks=decks(["lion"] * 3, ["tiger"] * 3))
    rules.apply_action(s, PlaceAction("cuckoo", ("cr", "3,2")))
    assert sorted(s.decks["B"]) == ["cuckoo_egg", "cuckoo_egg", "tiger", "tiger", "tiger"]
    assert s.decks["A"] == ["lion"] * 3


def test_cuckoo_into_an_empty_deck():
    s = make_state(hands={"A": ["cuckoo"]}, decks={"A": [], "B": []})
    rules.apply_action(s, PlaceAction("cuckoo", ("cr", "1,2")))
    assert s.decks["B"] == ["cuckoo_egg", "cuckoo_egg"]


def test_cuckoo_has_flight():
    assert_flight("cuckoo")


# ------------------------------------------------------------------------------------------------ [CUCKOO]

def test_cuckoo_legend_removes_an_adjacent_enemy_of_four_or_less_and_plays_nothing():
    # "Roar: remove an adjacent animal of strength 4 or less. If it was yours, play another animal."
    s = make_state(hands={"A": ["cuckoo_legend", "fox"]}, decks=decks())
    put(s, "2,2", "squirrel", "B")                            # a 4
    put(s, "1,1", "lion", "A")                                # a 7 of A's: too strong
    rules.apply_action(s, PlaceAction("cuckoo_legend", ("cr", "1,2")))
    assert set(s.pending["options"]) - {SKIP} == {"2,2"}
    choose(s, "2,2")
    assert "2,2" not in s.board and s.pending is None and hand_ids(s, "A") == ["fox"]


def test_cuckoo_legend_removing_an_ally_plays_another_animal_for_free():
    s = make_state(hands={"A": ["cuckoo_legend", "fox"]}, decks=decks())
    put(s, "1,1", "worker_bee", "A")
    rules.apply_action(s, PlaceAction("cuckoo_legend", ("cr", "1,2")))
    choose(s, "1,1")
    assert "1,1" not in s.board
    assert s.pending and s.pending["mode"] == "place"
    rules.apply_action(s, PlaceAction("fox", ("cr", "2,2")))
    assert s.top_unit("2,2").card_id == "fox" and s.actions_taken_this_turn == 1


def test_cuckoo_legend_nothing_of_four_or_less_adjacent():
    s = make_state(hands={"A": ["cuckoo_legend", "fox"]}, decks=decks())
    put(s, "2,2", "hedgehog", "B")                            # a 5
    put(s, "1,3", "stick_insect", "B")                        # Stealth: can't be chosen (and a 6)
    rules.apply_action(s, PlaceAction("cuckoo_legend", ("cr", "1,2")))
    assert s.pending is None and s.top_unit("2,2").card_id == "hedgehog"


# ------------------------------------------------------------------------------------------------ Soldier Bee



def test_guard_bee_spikes_remove_the_first_enemy_coverer():
    s = make_state(current="B", hands={"B": ["squirrel", "squirrel"]}, decks=decks())
    put(s, "4,2", "caracal", "B")
    gb = put(s, "3,2", "guard_bee", "A")
    rules.apply_action(s, PlaceAction("squirrel", ("cr", "3,2")))
    assert s.top_unit("3,2") is gb and "squirrel" in s.remove_pile
    rules.apply_action(s, PlaceAction("squirrel", ("cr", "3,2")))
    assert s.top_unit("3,2").card_id == "squirrel"


def test_guard_bee_has_flight():
    assert_flight("guard_bee")


# ------------------------------------------------------------------------------------------------ [BEE]

def test_bee_legend_2_gives_plus_two_everywhere_with_a_small_starting_deck():
    # "Roar: if your starting deck has no animals of strength 4 or more, give your animals +2 strength (wherever they are)."
    s = make_state(hands={"A": ["bee_legend_2", "fox"]}, decks=decks(["worker_bee", "worker_bee"]))
    s.starting_decks = {"A": ("bee_legend_2", "fox", "worker_bee", "worker_bee", "worm"), "B": ()}
    ally = put(s, "1,1", "worker_bee", "A")
    enemy = put(s, "2,1", "worker_bee", "B")
    rules.apply_action(s, PlaceAction("bee_legend_2", ("cr", "1,2")))
    g = 2
    assert effective_strength(s, s.top_unit("1,2")) == base("bee_legend_2") + g
    assert effective_strength(s, ally) == base("worker_bee") + g
    assert placement_strength(s, hand_inst(s, "A", "fox")) == base("fox") + g
    assert effective_strength(s, enemy) == base("worker_bee")
    rules.apply_action(s, DrawAction())                       # the deck's animals were given it too
    drawn = [u for u in s.hands["A"] if u.card_id == "worker_bee"]
    assert drawn and all(placement_strength(s, u) == base("worker_bee") + g for u in drawn)


def test_bee_legend_2_does_nothing_with_a_four_in_the_starting_deck():
    s = make_state(hands={"A": ["bee_legend_2", "fox"]}, decks=decks(["worker_bee"]))
    s.starting_decks = {"A": ("bee_legend_2", "fox", "worker_bee", "squirrel"), "B": ()}   # the Squirrel is a 4
    ally = put(s, "1,1", "worker_bee", "A")
    rules.apply_action(s, PlaceAction("bee_legend_2", ("cr", "1,2")))
    assert effective_strength(s, ally) == base("worker_bee")
    assert placement_strength(s, hand_inst(s, "A", "fox")) == base("fox")


# ------------------------------------------------------------------------------------------------ Mara

def test_mara_draws_two_after_ten_food_this_turn():
    # "Roar: if you gained 10 or more food this turn, draw 2 cards."
    s = make_state(hands={"A": ["worker_bee", "mara"]}, decks=decks())
    rules.apply_action(s, PlaceAction("worker_bee", ("cr", "3,1")))
    rules.apply_action(s, PlaceAction("mara", ("cr", "1,2")))
    assert hand_ids(s, "A") == ["lion"] * CFG.mara_draw


def test_mara_unfed_draws_nothing():
    s = make_state(hands={"A": ["mara"]}, food={"A": 50, "B": 0}, decks=decks())
    rules.apply_action(s, PlaceAction("mara", ("cr", "1,2")))
    assert hand_ids(s, "A") == []


# ------------------------------------------------------------------------------------------------ Rabbit

def test_rabbit_plays_a_bunny_next_to_it():
    # "Roar: play a Bunny next to this."
    s = make_state(hands={"A": ["rabbit"]}, decks=decks())
    rules.apply_action(s, PlaceAction("rabbit", ("cr", "1,1")))
    targets = {tuple(p["target"]) for p in s.pending["placements"]}
    assert targets == {("cr", "1,2"), ("cr", "2,1")}
    rules.apply_action(s, PlaceAction("bunny", ("cr", "2,1")))
    assert s.top_unit("2,1").card_id == "bunny" and s.top_unit("2,1").owner == "A"
    assert s.actions_taken_this_turn == 1 and hand_ids(s, "A") == []


def test_rabbit_with_no_legal_neighbour_makes_no_bunny():
    s = make_state(hands={"A": ["rabbit"]}, decks=decks())
    put(s, "1,2", "fox", "B"); put(s, "2,1", "fox", "B")      # a Bunny (1) covers neither
    rules.apply_action(s, PlaceAction("rabbit", ("cr", "1,1")))
    assert s.pending is None and hand_ids(s, "A") == []
    assert not any(u.card_id == "bunny" for st in s.board.values() for u in st)


# ------------------------------------------------------------------------------------------------ Vole

def test_vole_repeats_an_adjacent_allied_rodents_roar():
    # "Roar: repeat the Roar of an adjacent Rodent."
    s = make_state(hands={"A": ["vole"]}, decks=decks())
    put(s, "1,1", "squirrel", "A")
    put(s, "2,2", "hamster", "A")                             # a Rodent with no Roar
    apply_click(s, PlaceAction("vole", ("cr", "1,2")))
    assert s.food["A"] == CFG.squirrel_food


def test_vole_repeating_a_rabbit_plays_a_bunny_next_to_the_vole():
    # The repeated Roar is the Vole's own (rulings.md, Vole): "next to this" is next to the Vole.
    s = make_state(hands={"A": ["vole"]}, decks=decks())
    put(s, "1,1", "rabbit", "A")
    rules.apply_action(s, PlaceAction("vole", ("cr", "1,2")))
    if s.pending["mode"] == "choice":
        choose(s, "1,1")
    targets = {tuple(p["target"]) for p in s.pending["placements"]}
    assert targets == {("cr", "1,1"), ("cr", "1,3"), ("cr", "2,2")}
    rules.apply_action(s, PlaceAction("bunny", ("cr", "2,2")))
    assert s.top_unit("2,2").card_id == "bunny"


def test_vole_with_no_adjacent_rodent_does_nothing():
    s = make_state(hands={"A": ["vole"]}, decks=decks())
    put(s, "1,1", "worker_bee", "A")                          # a Roar, but no Rodent
    apply_click(s, PlaceAction("vole", ("cr", "1,2")))
    assert s.food["A"] == 0 and s.pending is None


@pytest.mark.xfail(strict=True, reason="two readings: 'an adjacent Rodent' read literally takes any Rodent, the "
                   "opponent's too; the engine (rulings.md, Vole, Martin 2026-10-29) takes only an adjacent allied Rodent")
def test_vole_repeats_an_adjacent_enemy_rodents_roar_literal_reading():
    s = make_state(hands={"A": ["vole"]}, decks=decks())
    put(s, "2,2", "squirrel", "B")
    apply_click(s, PlaceAction("vole", ("cr", "1,2")))
    assert s.food["A"] == CFG.squirrel_food


# ------------------------------------------------------------------------------------------------ Marmot

def test_marmot_has_plus_one_per_ten_food_in_hand_and_on_board():
    # "Has +1 strength for each 10 food you have."
    s = make_state(hands={"A": ["marmot"]}, food={"A": 29, "B": 90})
    assert placement_strength(s, hand_inst(s, "A", "marmot")) == base("marmot") + 2
    m = put(s, "1,2", "marmot", "A")
    assert effective_strength(s, m) == base("marmot") + 2     # the opponent's 90 is not yours
    s.food["A"] = 9
    assert effective_strength(s, m) == base("marmot")
    s.food["A"] = 40
    assert effective_strength(s, m) == base("marmot") + 4
