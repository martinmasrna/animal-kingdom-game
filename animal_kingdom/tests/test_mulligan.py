"""The bots' mulligan (bots/mulligan.py): keep a hand that plays, send back what can't start, never read the deck order."""

import random

from animal_kingdom.bots.greedy_bot import GreedyWeights
from animal_kingdom.bots.mulligan import mulligan_choice
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


def _choice(s, seed=0):
    return mulligan_choice(s, "A", rules.legal_actions(s), random.Random(seed), GreedyWeights())


def test_a_hand_nothing_can_start_sends_a_card_back():
    # Every card waits on "if you gained 10 or more food this turn", and nothing in hand gains it.
    s = _deal(["muskrat", "muskrat", "gopher", "groundhog"])
    a = _choice(s)
    assert isinstance(a, ChoiceAction) and a.choice != SKIP


def test_the_choice_never_reads_the_decks_order():
    s = _deal(["muskrat", "muskrat", "gopher", "hamster"])
    t = s.clone()
    random.Random(9).shuffle(t.decks["A"])          # the same cards, another hidden order
    assert _choice(s) == _choice(t)
