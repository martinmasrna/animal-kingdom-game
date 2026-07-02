"""M1 engine tests: fuzz (legality + termination), determinism/replay, clone
independence, serialization round-trips, and per-seat view filtering."""

from __future__ import annotations

import random

import pytest

from animal_kingdom.bots.random_bot import RandomBot
from animal_kingdom.decks import PREMADE_DECKS, load_premade_deck, make_vanilla_deck
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


def _play_premade(seed: int, slug_a: str, slug_b: str):
    """A RandomBot game between two premade decks, asserting the fuzz invariants."""
    state = new_game(load_premade_deck(slug_a), load_premade_deck(slug_b), seed)
    bots = {"A": RandomBot(seed=seed + 1), "B": RandomBot(seed=seed + 2)}
    while True:
        result = rules.is_terminal(state)
        if result is not None:
            return state, result
        actor = state.player_to_act()
        legal = rules.legal_actions(state)
        assert legal, "non-terminal state must have a legal action"
        action = bots[actor].choose(state.view_for(actor), legal)
        assert action in legal
        rules.apply_action(state, action)


def test_fuzz_premade_decks_full_matrix_terminates():
    """Every premade deck vs every premade deck (incl. the dynamic-strength cards) stays
    legal and terminates - the real decks the engine is built to simulate."""
    cfg = Config.default()
    slugs = sorted(PREMADE_DECKS)
    for a in slugs:
        for b in slugs:
            for seed in range(4):
                state, result = _play_premade(seed, a, b)
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


# ---- clone() fast-path helpers: must stay byte-for-byte equivalent to the generic versions
# they replaced (copy.deepcopy + random.Random()). These are the search hot path (millions of
# clones/decision); the speedup is only sound if it is provably semantic-preserving.

def test_plain_copy_matches_deepcopy_and_is_independent():
    import copy

    from animal_kingdom.engine.state import _plain_copy

    # The shape the effect-model containers actually take: nested dict/list of primitives.
    original = {
        "chooser": "A", "kind": "place", "count": 3, "done": False, "note": None,
        "opts": [{"cr": "r1c2", "iid": 5, "flags": [True, False, None]},
                 {"cr": "r2c3", "iid": 9, "buff": 2}],
        "meta": {"src": "lion", "nested": {"deep": [1, 2, {"x": "y"}]}},
    }
    copied = _plain_copy(original)
    assert copied == copy.deepcopy(original)      # value-equal to the generic copy
    copied["opts"][0]["flags"].append("MUT")      # deep mutation of the copy...
    copied["meta"]["nested"]["deep"][2]["x"] = "Z"
    assert original["opts"][0]["flags"] == [True, False, None]   # ...never touches the original
    assert original["meta"]["nested"]["deep"][2]["x"] == "y"


def test_plain_copy_falls_back_for_non_plain_types():
    import copy

    from animal_kingdom.engine.state import _plain_copy

    # A type outside the plain-data set must still be deep-copied correctly (defensive path),
    # so correctness never depends on the plain-data assumption holding for future effects.
    original = {"set_val": {1, 2, 3}, "tup": (1, [2, 3])}
    copied = _plain_copy(original)
    assert copied == copy.deepcopy(original)
    copied["tup"][1].append(99)
    assert original["tup"][1] == [2, 3]


def test_copy_rng_is_independent_and_position_preserving():
    from animal_kingdom.engine.state import _copy_rng

    src = random.Random(4242)
    for _ in range(37):
        src.random()                      # advance to a non-initial position
    copy_rng = _copy_rng(src)
    # Same position: the copy reproduces the source's continuation exactly.
    assert [copy_rng.random() for _ in range(20)] == [src.random() for _ in range(20)]
    # Independent stream: further draws on the copy do not disturb the source.
    src_state = src.getstate()
    for _ in range(10):
        copy_rng.random()
    assert src.getstate() == src_state


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
    assert v.own_hand == tuple(u.card_id for u in s.hands["A"])
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
