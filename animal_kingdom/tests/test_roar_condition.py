"""roar_condition: the "if ..." of a Roar, asked of a card in hand (the client's glow)
and of the placed unit (the Roar itself), must agree."""
from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import PlaceAction
from animal_kingdom.engine.effects import roar_condition

from ._helpers import make_state, put


def test_cards_without_a_condition_answer_none():
    s = make_state()
    assert roar_condition(s, "A", "lion") is None
    assert roar_condition(s, "A", "falcon") is None       # depends on where it lands


def test_fed_cards_light_up_once_ten_food_came_in_this_turn():
    s = make_state()
    assert roar_condition(s, "A", "groundhog") is False
    s.turn_flags["food_gained_A"] = 10
    assert all(roar_condition(s, "A", c) for c in ("groundhog", "gopher", "muskrat"))


def test_another_cat_means_a_cat_other_than_the_one_being_played():
    s = make_state()
    assert roar_condition(s, "A", "bobcat") is False
    bobcat = put(s, "1,2", "bobcat", "A")
    assert roar_condition(s, "A", "bobcat", bobcat) is False   # placed alone: itself doesn't count
    assert roar_condition(s, "A", "bobcat") is True          # a second Bobcat in hand now has one


def test_colony_threshold_counts_the_card_itself():
    s = make_state()
    for cr in ("1,1", "1,2"):
        put(s, cr, "worker_ant", "A")
    assert roar_condition(s, "A", "soldier_ant") is False  # 2 + itself = 3
    put(s, "1,3", "worker_ant", "A")
    assert roar_condition(s, "A", "soldier_ant") is True   # 3 + itself = 4
    ant = put(s, "2,1", "soldier_ant", "A")
    assert roar_condition(s, "A", "soldier_ant", ant) is True


def test_nurse_bee_pairs_with_itself_from_hand():
    s = make_state()
    put(s, "1,2", "nurse_bee", "A")
    assert roar_condition(s, "A", "nurse_bee") is True


def test_the_hand_prediction_matches_what_the_roar_does():
    s = make_state(hands={"A": ["bobcat", "bobcat"]}, decks={"A": ["lion"] * 5, "B": []})
    put(s, "1,1", "lion", "A")                                  # a Cat already on the board
    assert roar_condition(s, "A", "bobcat") is True
    place = next(a for a in rules.legal_actions(s) if isinstance(a, PlaceAction) and a.card_id == "bobcat"
                 and a.target[1] not in s.board)                # beside the Lion, not on top of it
    before = len(s.hands["A"])
    rules.apply_action(s, place)
    assert len(s.hands["A"]) == before                          # played one, drew one
