"""Shared scenario builders for the hand-constructed engine/bot tests.

map_a is the test-fixture map (the shipped game is map_b); these helpers build a bare
GameState on it and place units directly, so each test reads as one explicit scenario.
"""

from __future__ import annotations

from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import PlaceAction
from animal_kingdom.engine.cards import load_cards
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.maps import load_map
from animal_kingdom.engine.state import GameState, UnitInstance


def make_state(*, current="A", hands=None, decks=None, food=None, config=None) -> GameState:
    state = GameState(
        load_map("map_a"), load_cards(), config or Config.default(),
        board={}, hands={"A": [], "B": []}, decks=decks or {"A": [], "B": []},
        remove_pile=[], food=food or {"A": 0, "B": 0}, current=current, first_player="A",
    )
    for player, ids in (hands or {}).items():
        for card_id in ids:
            state.add_to_hand(player, card_id)
    return state


def put(state: GameState, cr: str, card_id: str, owner: str) -> UnitInstance:
    u = UnitInstance(card_id, owner, state.new_iid(), placed_on_turn=state.turn_counter)
    state.board.setdefault(cr, []).append(u)
    return u


def hand_ids(state, player):
    return [u.card_id for u in state.hands[player]]


def place_targets(state):
    return {a.target[1] for a in rules.legal_actions(state)
            if isinstance(a, PlaceAction) and a.target[0] == "cr"}
