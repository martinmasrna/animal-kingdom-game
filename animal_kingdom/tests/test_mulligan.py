"""The bots' mulligan (bots/mulligan.py): send back the weakest card while the deck's average replacement is better,
never read the deck order."""

import random

import pytest

from animal_kingdom.bots import mulligan
from animal_kingdom.decks import load_premade_deck
from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import SKIP, ChoiceAction
from animal_kingdom.engine.state import new_game


def _deal(hand: list[str], seed: int = 1):
    """A Food Aggro opening (seat A, first) against 30 Lions, with `hand` swapped in for the dealt cards."""
    s = new_game(load_premade_deck("food_aggro"), ["lion"] * 30, seed, first_player="A")
    deck = s.decks["A"] + [u.card_id for u in s.hands["A"]]
    for cid in hand:
        deck.remove(cid)
    s.decks["A"] = deck
    for u, cid in zip(s.hands["A"], hand):
        u.card_id = cid
    return s


@pytest.fixture
def table(monkeypatch):
    t = {}
    monkeypatch.setattr(mulligan, "impacts", lambda: t)
    return t


def _sent(s):
    a = mulligan.mulligan_choice(s, "A", rules.legal_actions(s))
    return None if a.choice == SKIP else next(u.card_id for u in s.hands["A"] if u.iid == a.choice)


def test_the_weakest_card_goes_back_when_the_deck_is_better_on_average(table):
    table.update({"muskrat": -10.0, "gopher": 2.0, "hamster": 2.0, "chipmunk": 15.0})
    assert _sent(_deal(["muskrat", "gopher", "hamster", "chipmunk"])) == "muskrat"


def test_a_hand_at_least_as_good_as_the_deck_is_kept(table):
    table.update({"chipmunk": 15.0, "big_gus": 12.0, "macaque_legend": 12.0, "beaver": 5.0})
    assert _sent(_deal(["chipmunk", "big_gus", "macaque_legend", "beaver"])) is None


def test_a_card_already_sent_back_cannot_be_the_replacement(table):
    # Every other card is -5; only the blacklisted Chipmunk would make the deck look better than the hand.
    s = _deal(["muskrat", "gopher", "hamster", "beaver"])
    table.update({c: -5.0 for c in s.decks["A"] + ["muskrat", "gopher", "hamster", "beaver"]})
    table["chipmunk"] = 100.0
    assert _sent(s) is not None
    step = {"op": "mulligan", "player": "A", "returned": ["chipmunk"]}
    s.effect_stack.append(step)
    try:
        assert _sent(s) is None
    finally:
        s.effect_stack.remove(step)


def test_the_choice_never_reads_the_decks_order(table):
    table.update({"muskrat": -10.0, "squirrel": -5.0})
    s = _deal(["muskrat", "muskrat", "gopher", "hamster"])
    t = s.clone()
    random.Random(9).shuffle(t.decks["A"])          # the same cards, another hidden order
    assert mulligan.mulligan_choice(s, "A", rules.legal_actions(s)) == mulligan.mulligan_choice(t, "A", rules.legal_actions(t))
