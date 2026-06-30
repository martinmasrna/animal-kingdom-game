"""M1 rules tests: connection, covering, stacks, region food, and the win conditions,
each in a hand-constructed scenario."""

from __future__ import annotations

from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import DrawAction, PlaceAction
from animal_kingdom.engine.cards import load_cards
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.maps import load_map
from animal_kingdom.engine.state import GameState, Result, UnitInstance

# Reworked-pool card ids with known integer strengths used below, all vanilla-bodied
# for rules tests (no Phase-1 effect handler, no keyword): house_cat=1, caracal=4,
# cheetah=5, lion=7.


def make_state(*, current="A", hands=None, decks=None, food=None) -> GameState:
    return GameState(
        load_map("map_a"),
        load_cards(),
        Config.default(),
        board={},
        hands=hands or {"A": [], "B": []},
        decks=decks or {"A": [], "B": []},
        discard=[],
        food=food or {"A": 0, "B": 0},
        current=current,
        first_player="A",
    )


def put(state: GameState, cr: str, card_id: str, owner: str) -> None:
    state.board.setdefault(cr, []).append(UnitInstance(card_id, owner, state.new_iid()))


def place_targets(state):
    return {a.target[1] for a in rules.legal_actions(state)
            if isinstance(a, PlaceAction) and a.target[0] == "cr"}


# ---------------------------------------------------------------------- connection

def test_empty_board_only_own_hq_fronts_are_legal():
    s = make_state(hands={"A": ["lion"], "B": []})
    assert place_targets(s) == {"1,1", "1,2", "1,3"}
    assert DrawAction() not in rules.legal_actions(s)  # deck empty


def test_connection_extends_through_occupied():
    s = make_state(hands={"A": ["lion"], "B": []})
    put(s, "1,2", "caracal", "A")  # an occupied, connected front
    assert place_targets(s) == {"1,1", "1,2", "1,3", "2,2"}
    assert "3,2" not in place_targets(s)  # two hops away, no chain yet


# ------------------------------------------------------------------------ covering

def test_covering_requires_strictly_greater_strength():
    s = make_state(hands={"A": ["lion", "house_cat", "caracal"], "B": []})
    put(s, "1,2", "caracal", "A")           # A holds a connected front
    put(s, "2,2", "caracal", "B")  # enemy strength 4, adjacent → connected for A
    legal = rules.legal_actions(s)
    assert PlaceAction("lion", ("cr", "2,2")) in legal             # 7 > 4 ✓
    assert PlaceAction("house_cat", ("cr", "2,2")) not in legal  # 1 > 4 ✗
    assert PlaceAction("caracal", ("cr", "2,2")) not in legal  # 4 > 4 ✗ (strict)


def test_own_stacking_needs_no_strength():
    s = make_state(hands={"A": ["house_cat"], "B": []})
    put(s, "1,2", "lion", "A")  # own strong unit
    assert PlaceAction("house_cat", ("cr", "1,2")) in rules.legal_actions(s)


def test_stack_reveal_on_removal():
    s = make_state()
    put(s, "2,2", "caracal", "B")  # B (bottom)
    put(s, "2,2", "lion", "A")             # A covers (top)
    assert rules.owner_of(s, "2,2") == "A"
    s.board["2,2"].pop()                   # remove the top
    assert rules.owner_of(s, "2,2") == "B"  # the unit beneath now controls


# ------------------------------------------------------------------ region & food

def test_region_control_produces_food_at_end_of_turn():
    s = make_state(current="A", decks={"A": ["lion"], "B": []})
    for cr in ("1,1", "2,1", "1,2", "2,2"):  # all corners of R1 (food 10)
        put(s, cr, "caracal", "A")
    rules.apply_action(s, DrawAction())
    assert s.food["A"] == 10
    assert s.current == "B"  # turn passed


# -------------------------------------------------------------------- win conditions

def test_food_win():
    s = make_state(current="A", decks={"A": ["lion"], "B": []}, food={"A": 95, "B": 0})
    for cr in ("1,1", "2,1", "1,2", "2,2"):
        put(s, cr, "caracal", "A")
    rules.apply_action(s, DrawAction())  # +10 → 105 ≥ 100
    assert s.result == Result("A", "food")
    assert rules.is_terminal(s) == Result("A", "food")


def test_hq_capture_win():
    s = make_state(current="A", hands={"A": ["lion"], "B": []})
    for cr in ("1,2", "2,2", "3,2", "4,2"):  # connected chain to B's front (4,2)
        put(s, cr, "caracal", "A")
    assert PlaceAction("lion", ("hq", "B")) in rules.legal_actions(s)
    rules.apply_action(s, PlaceAction("lion", ("hq", "B")))
    assert s.result == Result("A", "hq_capture")


def test_exhaustion_more_food_wins():
    s = make_state(current="A", food={"A": 5, "B": 3})  # A cannot draw or place
    assert rules.legal_actions(s) == []
    assert rules.is_terminal(s) == Result("A", "exhaustion")


def test_exhaustion_tie_breaks_against_player_who_cannot_act():
    s = make_state(current="A", food={"A": 3, "B": 3})
    assert rules.is_terminal(s) == Result("B", "exhaustion")  # A is stuck → A loses
