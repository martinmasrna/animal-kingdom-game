"""M1 engine tests: fuzz (legality + termination), determinism/replay, clone
independence, serialization round-trips, and per-seat view filtering."""

from __future__ import annotations

import random

import pytest

from animal_kingdom.bots.random_bot import RandomBot
from animal_kingdom.decks import make_vanilla_deck
from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import DrawAction, PlaceAction, action_from_dict
from animal_kingdom.engine.cards import load_cards
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.state import GameState, new_game


def _setup(seed: int) -> GameState:
    cards = load_cards()
    drng = random.Random(seed)
    deck_a = make_vanilla_deck(seed=drng.randrange(1 << 30), cards=cards)
    deck_b = make_vanilla_deck(seed=drng.randrange(1 << 30), cards=cards)
    return new_game(deck_a, deck_b, seed, cards=cards)


def play_random(seed: int):
    """Play one RandomBot-vs-RandomBot game; returns (final_state, result, action_log).

    Asserts the core fuzz invariants along the way: there is always a legal action until
    terminal, and the chosen action is legal.
    """
    state = _setup(seed)
    bots = {"A": RandomBot(seed=seed + 1), "B": RandomBot(seed=seed + 2)}
    log = []
    while True:
        result = rules.is_terminal(state)
        if result is not None:
            return state, result, log
        actor = state.player_to_act()
        legal = rules.legal_actions(state)
        assert legal, "non-terminal state must have a legal action"
        action = bots[actor].choose(state.view_for(actor), legal)
        assert action in legal
        rules.apply_action(state, action)
        log.append(action)


def replay(seed: int, log) -> GameState:
    state = _setup(seed)
    for action in log:
        rules.apply_action(state, action)
    return state


def assert_board_legal(state: GameState) -> None:
    """Board structural sanity.

    (M1's strict-covering stack invariant no longer holds in M2: covering-rule modifiers
    — Honey Badger, Spotted Hyena, Chameleon — and Boa Constrictor's remove-instead-of-stack
    legitimately create non-strict stacks. Placement legality is instead guaranteed by the
    `action in legal` check in play_random.)
    """
    for cr, stack in state.board.items():
        assert stack, f"empty stack lingering at {cr}"
        for u in stack:
            assert u.card_id in state.cards


# ------------------------------------------------------------------------- fuzz

def test_fuzz_random_games_stay_legal_and_terminate():
    cfg = Config.default()
    for seed in range(1000):
        state, result, _ = play_random(seed)
        assert result is not None
        assert state.turn_counter <= cfg.max_turns
        assert_board_legal(state)


# ------------------------------------------------------------- determinism / replay

def test_same_seed_replays_identically():
    s1, r1, log = play_random(123)
    s2, r2, _ = play_random(123)
    assert r1 == r2
    assert s1.to_dict() == s2.to_dict()


def test_action_log_replays_to_identical_state():
    final, _, log = play_random(456)
    assert replay(456, log).to_dict() == final.to_dict()


# ------------------------------------------------------------------ clone guardrail

def test_clone_is_independent():
    s = _setup(9)
    before = s.to_dict()
    c = s.clone()
    rules.apply_action(c, rules.legal_actions(c)[0])  # mutate the clone
    assert s.to_dict() == before        # original untouched
    assert c.to_dict() != before        # clone moved on


# ------------------------------------------------------------------ serialization

def test_state_round_trips():
    final, _, _ = play_random(7)
    d = final.to_dict()
    assert GameState.from_dict(d).to_dict() == d


def test_action_round_trips():
    for a in (DrawAction(), PlaceAction("lion", ("cr", "2,2")), PlaceAction("lion", ("hq", "B"))):
        assert action_from_dict(a.to_dict()) == a


# --------------------------------------------------------------- per-seat view

def test_view_for_hides_opponent_hand_and_deck_contents():
    s = _setup(5)
    v = s.view_for("A")
    assert v.own_hand == tuple(s.hands["A"])
    assert v.opponent_hand_count == len(s.hands["B"])
    assert v.own_deck_count == len(s.decks["A"])
    assert v.opponent_deck_count == len(s.decks["B"])
    # no field leaks the opponent's hand/deck contents
    assert not hasattr(v, "opponent_hand")
    assert not hasattr(v, "decks")


def test_view_is_read_only():
    v = _setup(5).view_for("A")
    with pytest.raises(TypeError):
        v.food["A"] = 999  # MappingProxyType is read-only
