"""Tests for bots/determinize.py - the hidden-info re-sampling seam for search bots.

The load-bearing property is honesty: a determinized world must depend only on what
`me` can legitimately know (public state + own hand + the opponent's combined
hand+deck multiset), never on the true hand/deck split or deck orders.
"""

from __future__ import annotations

import random
from collections import Counter

from animal_kingdom.bots.determinize import determinize
from animal_kingdom.tests.test_greedy_bot import make_state, put


def _opp_pool(state, opp="B") -> Counter:
    return Counter([u.card_id for u in state.hands[opp]] + list(state.decks[opp]))


def rich_state():
    """A mid-game-ish position: board units, food, remove pile, hands and decks."""
    s = make_state(
        hands={"A": ["lion", "mouse"], "B": ["skunk", "rat", "lion"]},
        decks={"A": ["caracal", "black_panther", "mouse"], "B": ["mouse", "jerboa", "rat"]},
        food={"A": 12, "B": 7},
    )
    put(s, "2,2", "lion", "A")
    put(s, "3,2", "rat", "B")
    s.remove_pile.extend(["gazelle", "impala"])
    s.turn_counter = 4
    return s


# ------------------------------------------------------------------ conservation

def test_opponent_pool_and_counts_are_conserved():
    s = rich_state()
    world = determinize(s, "A", random.Random(0))
    assert _opp_pool(world) == _opp_pool(s)
    assert len(world.hands["B"]) == len(s.hands["B"])
    assert len(world.decks["B"]) == len(s.decks["B"])


def test_my_side_and_public_state_are_untouched():
    s = rich_state()
    world = determinize(s, "A", random.Random(0))
    # My hand: same instances in the same order (iids preserved).
    assert [u.iid for u in world.hands["A"]] == [u.iid for u in s.hands["A"]]
    assert [u.card_id for u in world.hands["A"]] == [u.card_id for u in s.hands["A"]]
    # My deck: same multiset (order is legitimately re-shuffled).
    assert Counter(world.decks["A"]) == Counter(s.decks["A"])
    # Public state untouched.
    assert {cr: [(u.card_id, u.owner) for u in st] for cr, st in world.board.items()} \
        == {cr: [(u.card_id, u.owner) for u in st] for cr, st in s.board.items()}
    assert world.remove_pile == s.remove_pile
    assert world.food == s.food
    assert world.current == s.current
    assert world.turn_counter == s.turn_counter


def test_original_state_is_never_mutated():
    s = rich_state()
    before = s.to_dict()
    determinize(s, "A", random.Random(0))
    assert s.to_dict() == before


# ------------------------------------------------------------------ lock handling

def test_skunk_locked_opponent_card_stays_in_hand_with_lock():
    s = rich_state()
    locked = s.hands["B"][0]
    locked.locked_until_turn = s.turn_counter + 2   # publicly-known Skunk bounce
    world = determinize(s, "A", random.Random(0))
    kept = [u for u in world.hands["B"] if u.iid == locked.iid]
    assert len(kept) == 1
    assert kept[0].card_id == locked.card_id
    assert kept[0].locked_until_turn == locked.locked_until_turn
    # Pool conservation still holds with the lock in place.
    assert _opp_pool(world) == _opp_pool(s)


def test_expired_lock_is_treated_as_hidden():
    s = rich_state()
    s.hands["B"][0].locked_until_turn = s.turn_counter   # lock already expired
    world = determinize(s, "A", random.Random(1))
    # No instance is pinned: all hand iids are fresh (re-dealt).
    old_iids = {u.iid for u in s.hands["B"]}
    assert all(u.iid not in old_iids for u in world.hands["B"])


# ------------------------------------------------------------------ determinism / independence

def test_same_seed_gives_identical_worlds():
    s = rich_state()
    w1 = determinize(s, "A", random.Random(7))
    w2 = determinize(s, "A", random.Random(7))
    assert w1.to_dict() == w2.to_dict()


def test_one_rng_yields_varied_worlds():
    s = rich_state()
    rng = random.Random(0)
    worlds = [determinize(s, "A", rng) for _ in range(8)]
    splits = {tuple(sorted(u.card_id for u in w.hands["B"])) for w in worlds}
    assert len(splits) > 1   # the hand/deck split actually varies across worlds


def test_world_rng_is_reseeded():
    s = rich_state()
    rng = random.Random(0)
    w1 = determinize(s, "A", rng)
    w2 = determinize(s, "A", rng)
    assert w1.rng.getstate() != s.rng.getstate()      # not the original stream
    assert w1.rng.getstate() != w2.rng.getstate()     # and not shared across worlds


def test_world_is_independent_of_original():
    s = rich_state()
    world = determinize(s, "A", random.Random(0))
    world.hands["A"][0].strength_counter = 99
    world.decks["A"].clear()
    world.food["A"] = 999
    assert s.hands["A"][0].strength_counter == 0
    assert s.decks["A"]
    assert s.food["A"] == 12


# ------------------------------------------------------------------ honesty

def test_worlds_depend_only_on_public_info_not_the_hidden_split():
    """Two states identical except for the opponent's (hidden) hand/deck split and
    deck order must determinize to identical worlds under the same seed - the
    no-cheat property, by construction."""
    a = make_state(hands={"A": ["lion"], "B": ["lion", "lion"]},
                   decks={"A": ["mouse", "rat"], "B": ["mouse", "mouse"]})
    b = make_state(hands={"A": ["lion"], "B": ["mouse", "mouse"]},
                   decks={"A": ["rat", "mouse"], "B": ["lion", "lion"]})
    wa = determinize(a, "A", random.Random(3))
    wb = determinize(b, "A", random.Random(3))
    assert [u.card_id for u in wa.hands["B"]] == [u.card_id for u in wb.hands["B"]]
    assert wa.decks["B"] == wb.decks["B"]
    # My own deck order is hidden info too (I know contents, not order): states
    # differing only in that order must sample identical worlds.
    assert wa.decks["A"] == wb.decks["A"]
