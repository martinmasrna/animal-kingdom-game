"""Tactical regression puzzles for GreedyBot: hand-built boards with an objectively-correct
move, asserted directly (not inferred from aggregate win-rate deltas, which can hide a bot
that regressed on one obvious tactic while improving on average).

Reuses the constructed-state helpers from test_greedy_bot.py rather than reinventing them.
"""

from __future__ import annotations

import pytest

from animal_kingdom.bots.greedy_bot import GreedyBot, GreedyWeights, evaluate
from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import PlaceAction
from animal_kingdom.sim.metrics import GREEDY_CAVEAT

from .test_greedy_bot import make_state, put

W = GreedyWeights()


def test_blocks_imminent_hq_threat_over_unrelated_offense():
    # B has a connected chain of weak units running all the way onto "1,2" (A's own HQ
    # front) - if left alone, B captures A's HQ next turn. A also has an unrelated,
    # perfectly fine offensive play available ("1,1", another empty HQ-front cell). A must
    # cover "1,2" (breaking B's connection) rather than chase the unrelated offense.
    s = make_state(current="A", hands={"A": ["lion", "mouse"]})
    for cr in ("4,2", "3,2", "2,2", "1,2"):
        put(s, cr, "mouse", "B")

    legal = rules.legal_actions(s)
    block = PlaceAction("lion", ("cr", "1,2"))
    offense = PlaceAction("lion", ("cr", "1,1"))
    assert block in legal and offense in legal

    chosen = GreedyBot(seed=0).choose(s.view_for("A"), legal, s)
    assert chosen == block


def test_prefers_big_food_gain_over_marginal_board_presence():
    # Worker Ant's battlecry (gain 8 food, non-lethal here) trades a strong body (Lion, 7
    # strength) for a weak one (1 strength) - the food swing should win out over the
    # marginal board-presence loss.
    s = make_state(hands={"A": ["worker_ant", "lion"]}, food={"A": 50, "B": 0})
    legal = rules.legal_actions(s)

    chosen = GreedyBot(seed=0).choose(s.view_for("A"), legal, s)
    assert chosen.card_id == "worker_ant"


def test_prefers_region_richer_hq_front_tile():
    # Same card, same connection/presence value either way - "1,2" is a corner of two
    # regions (R1 + R4) while "1,1" is a corner of only one (R1), so region_control should
    # be the deciding factor between two otherwise-tied HQ-front placements.
    s = make_state(hands={"A": ["lion"]})
    legal = rules.legal_actions(s)
    richer = PlaceAction("lion", ("cr", "1,2"))
    poorer = PlaceAction("lion", ("cr", "1,1"))
    assert richer in legal and poorer in legal

    chosen = GreedyBot(seed=0).choose(s.view_for("A"), legal, s)
    assert chosen == richer


@pytest.mark.xfail(strict=True, reason=(
    "Known limitation tracked by metrics.GREEDY_CAVEAT: a 1-ply greedy bot can't see past "
    "the current action, so it scores a delayed payoff (Grizzly Bear's 'in 2 turns, remove "
    "a random adjacent enemy') exactly the same as a same-strength vanilla body with no "
    "payoff at all. Once the bot's evaluation accounts for scheduled/delayed effects, this "
    "assertion should start passing - which is the signal to update GREEDY_CAVEAT."
))
def test_recognizes_grizzly_bear_delayed_removal_as_better_than_a_vanilla_twin():
    assert GREEDY_CAVEAT  # the caveat this puzzle exists to eventually retire

    s = make_state(hands={"A": ["grizzly_bear", "lion"]})   # both base_strength 7
    put(s, "2,2", "mouse", "B")                              # a free future target

    grizzly = s.clone()
    rules.apply_action(grizzly, PlaceAction("grizzly_bear", ("cr", "1,2")))
    vanilla_twin = s.clone()
    rules.apply_action(vanilla_twin, PlaceAction("lion", ("cr", "1,2")))

    assert grizzly.scheduled, "Grizzly Bear's battlecry should schedule the delayed removal"
    assert evaluate(grizzly, "A", W) > evaluate(vanilla_twin, "A", W)
