"""The actions prototype (branch actions): "Action: <effect>." animals, [ACTION 1] to [ACTION 8].

The rule: using an Action costs one of the turn's actions, the animal may use it the turn it is placed, at most once a
turn, only from the top of its crossroad and only while its effects work; it is not a placement and not a Roar. Food and
draws go through the normal paths. Map A: a 4x3 grid "col,row"; A's den fronts column 1, B's column 4.
"""

from __future__ import annotations

from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import ActAction, ChoiceAction, DrawAction, PassAction, PlaceAction, action_from_dict
from animal_kingdom.engine.state import GameState
from animal_kingdom.engine.strength import effective_strength, strength_breakdown

from ._helpers import cards_with, make_state, put

CARDS = cards_with({"id": "t_big", "base_strength": 9}, {"id": "t_body", "base_strength": 4})


def state(**kw) -> GameState:
    return make_state(cards=CARDS, **kw)


def acts(s):
    return {a.origin for a in rules.legal_actions(s) if isinstance(a, ActAction)}


def end_turn(s):
    rules.apply_action(s, PassAction())


# ===================================================================== the rule

def test_an_action_costs_one_of_the_turns_actions_and_comes_once_a_turn():
    s = state(decks={"A": ["t_body"] * 5, "B": ["t_body"] * 5})
    put(s, "1,1", "action_1", "A")
    assert acts(s) == {"1,1"}
    rules.apply_action(s, ActAction("1,1"))
    assert s.food["A"] == 10 and s.actions_taken_this_turn == 1 and s.current == "A"
    assert acts(s) == set()                                  # once per animal per turn
    assert DrawAction() in rules.legal_actions(s)            # the other action is still there
    rules.apply_action(s, DrawAction())
    assert s.current == "B"
    end_turn(s)
    assert acts(s) == {"1,1"}                                # a new turn, a new use


def test_with_no_action_left_it_is_not_offered():
    s = state(decks={"A": ["t_body"] * 5, "B": ["t_body"] * 5})
    put(s, "1,1", "action_1", "A")
    put(s, "1,2", "action_1", "A")
    rules.apply_action(s, ActAction("1,1"))
    rules.apply_action(s, ActAction("1,2"))                  # two animals, one action each
    assert s.food["A"] == 20 and s.current == "B"            # the turn's two actions are spent: it ends
    assert action_from_dict(ActAction("1,1").to_dict()) == ActAction("1,1")


def test_usable_the_turn_it_is_placed():
    s = state(hands={"A": ["action_1"]})
    rules.apply_action(s, PlaceAction("action_1", ("cr", "1,1")))
    assert acts(s) == {"1,1"}
    rules.apply_action(s, ActAction("1,1"))
    assert s.food["A"] == 10


def test_a_covered_animal_cannot_act_and_an_inked_one_has_no_action():
    s = state()
    put(s, "2,2", "action_1", "A")
    put(s, "2,2", "t_big", "B")                              # covered by an enemy
    u = put(s, "1,1", "action_1", "A")
    assert acts(s) == {"1,1"}
    s.inked.add(u.iid)                                       # lost all its effects
    assert acts(s) == set()
    put(s, "1,3", "action_7", "B")                           # the opponent's never offered to you
    assert acts(s) == set()


def test_an_action_is_not_a_placement_nor_a_roar():
    # the Worker Wasp gains food whenever you place an animal; the Macaw repeats the last Roar your opponent played
    s = state(hands={"B": ["macaw"]})
    put(s, "1,1", "worker_wasp", "A")
    put(s, "1,2", "action_1", "A")
    rules.apply_action(s, ActAction("1,2"))
    assert s.food["A"] == 10                                 # the Action's food only, no Worker Wasp food
    assert "A" not in s.last_roar                            # nothing for a Macaw to repeat
    assert s.units_placed_this_turn == 0


def test_food_from_an_action_counts_as_food_gained_and_meets_the_riders():
    s = state(decks={"A": ["t_body"] * 3, "B": []})
    put(s, "1,1", "bumblebee_legend", "A")                   # Lord Bumbleton: gain 3 more whenever you gain food
    put(s, "1,2", "action_1", "A")
    rules.apply_action(s, ActAction("1,2"))
    assert s.food["A"] == 13
    assert s.turn_flags["food_gained_A"] == 13               # "if you gained 10 or more food this turn" sees it


def test_an_action_survives_a_save_and_a_reload():
    s = state(decks={"A": ["t_body"] * 3, "B": []})
    u = put(s, "1,1", "action_8", "A")
    rules.apply_action(s, ActAction("1,1"))
    d = s.to_dict()
    back = GameState.from_dict(d, cards=CARDS, config=s.config)
    assert back.to_dict() == d and d["action_guard"] == {"A": [3, 2]} and d["turn_flags"][f"acted_{u.iid}"] is True


# ===================================================================== the eight cards

def test_action_2_discards_the_card_you_choose_then_gains_15():
    s = state(hands={"A": ["t_body", "t_big"]})
    put(s, "1,1", "action_2", "A")
    rules.apply_action(s, ActAction("1,1"))
    big = next(u for u in s.hands["A"] if u.card_id == "t_big")
    assert s.pending and set(s.pending["options"]) == {u.iid for u in s.hands["A"]}
    assert s.food["A"] == 0                                  # the discard comes first
    rules.apply_action(s, ChoiceAction(big.iid))
    assert [u.card_id for u in s.hands["A"]] == ["t_body"] and s.food["A"] == 15


def test_action_2_is_not_offered_with_an_empty_hand():
    s = state()
    put(s, "1,1", "action_2", "A")
    assert acts(s) == set()


def test_action_3_gains_5_and_draws_a_card_and_with_an_empty_deck_still_gains():
    s = state(decks={"A": ["t_body"], "B": []})
    put(s, "1,1", "action_3", "A")
    put(s, "1,2", "hamster", "A")                            # whenever you draw a card, gain 5 food: a normal draw
    rules.apply_action(s, ActAction("1,1"))
    assert s.food["A"] == 10 and [u.card_id for u in s.hands["A"]] == ["t_body"]
    s = state()                                              # an empty deck: the food all the same
    put(s, "1,1", "action_3", "A")
    rules.apply_action(s, ActAction("1,1"))
    assert s.food["A"] == 5 and s.hands["A"] == []


def test_action_4_gives_the_hand_animal_you_choose_plus_2_and_it_carries_onto_the_board():
    s = state(hands={"A": ["t_body", "t_big"]})
    put(s, "1,1", "action_4", "A")
    rules.apply_action(s, ActAction("1,1"))
    body = next(u for u in s.hands["A"] if u.card_id == "t_body")
    rules.apply_action(s, ChoiceAction(body.iid))
    assert body.strength_counter == 2
    rules.apply_action(s, PlaceAction("t_body", ("cr", "1,2")))
    assert effective_strength(s, s.board["1,2"][-1]) == 6


def test_action_4_is_not_offered_without_an_animal_in_hand():
    s = state()
    put(s, "1,1", "action_4", "A")
    assert acts(s) == set()


def test_action_5_lets_the_next_animal_you_play_land_anywhere_then_is_spent():
    s = state(hands={"A": ["t_body", "t_body"]}, decks={"A": ["t_body"] * 3, "B": ["t_body"] * 3})
    s.turn_counter = 4
    s.turn_flags["bonus_actions_A"] = 1                      # three actions, to see the second play
    put(s, "1,1", "action_5", "A")

    def places(s):
        return {a.target for a in rules.legal_actions(s) if isinstance(a, PlaceAction)}

    assert ("cr", "3,2") not in places(s)
    rules.apply_action(s, ActAction("1,1"))
    assert ("cr", "3,2") in places(s) and ("cr", "4,3") in places(s)   # any crossroad, connected or not
    assert ("hq", "B") not in places(s)                      # Flight never takes a den
    rules.apply_action(s, PlaceAction("t_body", ("cr", "3,2")))
    assert "flight_next_A" not in s.turn_flags and ("cr", "4,3") not in places(s)


def test_action_5_unused_is_gone_at_the_end_of_the_turn():
    s = state(hands={"A": ["t_body"]}, decks={"A": ["t_body"] * 3, "B": ["t_body"] * 3})
    put(s, "1,1", "action_5", "A")
    rules.apply_action(s, ActAction("1,1"))
    rules.apply_action(s, DrawAction())
    assert s.current == "B"
    end_turn(s)
    assert not any(a.target == ("cr", "3,2") for a in rules.legal_actions(s) if isinstance(a, PlaceAction))


def test_action_6_scouts_a_card():
    s = state(decks={"A": ["t_body", "t_big", "hamster", "macaw"], "B": []})
    put(s, "1,1", "action_6", "A")
    rules.apply_action(s, ActAction("1,1"))
    assert s.pending and set(s.pending["options"]) == {"t_big", "hamster", "macaw"}   # the top three
    rules.apply_action(s, ChoiceAction("t_big"))
    assert [u.card_id for u in s.hands["A"]] == ["t_big"] and sorted(s.decks["A"]) == ["hamster", "macaw", "t_body"]


def test_action_6_is_not_offered_with_an_empty_deck():
    s = state()
    put(s, "1,1", "action_6", "A")
    assert acts(s) == set()


def test_action_7_takes_10_food_never_below_0():
    s = state(food={"A": 0, "B": 25})
    put(s, "1,1", "action_7", "A")
    put(s, "1,2", "action_7", "A")
    rules.apply_action(s, ActAction("1,1"))
    assert s.food["B"] == 15
    s.food["B"] = 4
    rules.apply_action(s, ActAction("1,2"))
    assert s.food["B"] == 0


def test_action_8_gives_your_animals_plus_2_through_the_opponents_next_turn_only():
    s = state(hands={"B": ["t_body"]}, decks={"A": ["t_body"] * 5, "B": ["t_body"] * 5})
    me = put(s, "1,1", "action_8", "A")
    ally = put(s, "1,2", "t_body", "A")
    rules.apply_action(s, ActAction("1,1"))
    assert effective_strength(s, ally) == 4                  # not during your own turn
    rules.apply_action(s, DrawAction())
    assert s.current == "B"
    assert effective_strength(s, ally) == 6 and effective_strength(s, me) == 4   # itself included
    assert ["action_8", 2] in strength_breakdown(s, ally)["auras"]
    s.board.pop("1,1")                                       # it holds even if the animal that gave it is gone
    assert effective_strength(s, ally) == 6
    late = put(s, "1,3", "t_body", "A")                      # one arriving during that turn has it too
    assert effective_strength(s, late) == 6
    end_turn(s)
    assert effective_strength(s, ally) == 4                  # over when that turn ends


def test_action_8_used_twice_stacks():
    s = state(decks={"A": ["t_body"] * 5, "B": ["t_body"] * 5})
    put(s, "1,1", "action_8", "A")
    put(s, "1,2", "action_8", "A")
    ally = put(s, "1,3", "t_body", "A")
    rules.apply_action(s, ActAction("1,1"))
    rules.apply_action(s, ActAction("1,2"))
    assert s.current == "B" and effective_strength(s, ally) == 8


def test_action_8_stops_a_cover_it_would_have_allowed():
    s = state(hands={"B": ["t_body"]}, decks={"A": ["t_body"] * 5, "B": ["t_body"] * 5})
    put(s, "3,2", "action_8", "A")                           # strength 2: a 4 covers it, a 2+2 it can't
    put(s, "4,2", "t_body", "B")
    put(s, "1,2", "t_body", "A"); put(s, "2,2", "t_body", "A")
    rules.apply_action(s, ActAction("3,2"))
    rules.apply_action(s, DrawAction())
    assert s.current == "B"
    assert not any(isinstance(a, PlaceAction) and a.target == ("cr", "3,2") for a in rules.legal_actions(s))
