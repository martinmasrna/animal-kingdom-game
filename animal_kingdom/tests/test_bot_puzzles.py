"""Tactical regression puzzles for the bots: hand-built boards with an objectively-correct
move, asserted directly (not inferred from aggregate win-rate deltas, which can hide a bot
that regressed on one obvious tactic while improving on average).

Reuses the constructed-state helpers from test_greedy_bot.py rather than reinventing them.
"""

from __future__ import annotations

import pytest

from animal_kingdom.bots.greedy_bot import GreedyBot, GreedyWeights, evaluate
from animal_kingdom.bots.referee_bot import RefereeBot
from animal_kingdom.bots.turn_bot import TurnBot
from animal_kingdom.decks import load_premade_deck
from animal_kingdom.engine.cards import load_cards
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.maps import load_map
from animal_kingdom.engine.state import GameState, UnitInstance
from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import PlaceAction

from ._helpers import make_state, put

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
    # Worker Ant's roar (gain 12 food, non-lethal here) trades a strong body (Lion, 7
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


def test_recognizes_grizzly_bear_delayed_removal_as_better_than_a_vanilla_body():
    # Retired xfail (2026-07-04): GreedyWeights.pending_payoff now credits owned scheduled
    # effects, so a Grizzly Bear's delayed removal outscores a plain vanilla body even though
    # Grizzly's own body is smaller (str 6 after the 2026-07-05 nerf) than the vanilla Lion (7).
    # This was the tripwire for the scheduled/delayed-effect blind spot; the fix trips it.
    s = make_state(hands={"A": ["grizzly_bear", "lion"]})   # grizzly str 6 + effect vs lion str 7
    put(s, "2,2", "mouse", "B")                              # a free future target

    grizzly = s.clone()
    rules.apply_action(grizzly, PlaceAction("grizzly_bear", ("cr", "1,2")))
    vanilla_twin = s.clone()
    rules.apply_action(vanilla_twin, PlaceAction("lion", ("cr", "1,2")))

    assert grizzly.scheduled, "Grizzly Bear's roar should schedule the delayed removal"
    assert evaluate(grizzly, "A", W) > evaluate(vanilla_twin, "A", W)


@pytest.mark.xfail(strict=True, reason="effect_readiness pays +16 for holding a live Roar, "
                   "so the search keeps Jerboa in hand rather than spend it (gauntlet, 2026-09-29)")
@pytest.mark.parametrize("bot_cls", [TurnBot, RefereeBot])
def test_last_action_spends_an_extra_play_roar(bot_cls):
    # The turn's last action. Jerboa ("Roar: play another unit") lands two units for one
    # action; Lion alone lands one and keeps Jerboa in hand. Nothing threatens either line,
    # so the two-unit play is simply better. From Martin's reverse gauntlet, where RefereeBot
    # piloting the Roar-heavy decks (Egg, Colony, Cats) kept its effect cards in hand while
    # he played them.
    deck = ["lion"] * 10
    s = make_state(hands={"A": ["jerboa", "lion", "tiger", "lynx", "caracal", "cheetah"],
                          "B": ["lion"] * 3},
                   decks={"A": list(deck), "B": list(deck)})
    s.actions_taken_this_turn = 1
    put(s, "1,2", "mouse", "A")
    put(s, "3,2", "lion", "B")

    chosen = bot_cls(seed=0).choose(s.view_for("A"), rules.legal_actions(s), s)
    assert chosen.card_id == "jerboa"


@pytest.mark.xfail(strict=True, reason="the eval pays for live Roars and hand size against the "
                   "opponent's, so the search draws a seventh and eighth card (2026-09-30)")
@pytest.mark.parametrize("bot_cls", [TurnBot, RefereeBot])
def test_canine_develops_instead_of_drawing_a_full_hand(bot_cls):
    # From a RefereeBot game (Canine vs the goodstuff pile, round 2): Dhole on Canine's den
    # front, the pile drew twice and has nothing on the board, Canine already drew with its
    # first action and holds six. The bot drew again. Martin: the move is Dhole,
    # Fox or Dingo; drawing is the worst and a vanilla Wolf the second worst (Jackal and
    # Raksha are wrong too). One good line is a second Dhole in the middle row, then Fox into a
    # corner next turn (+2 from each Dhole, a draw for each), then Dingo beside them.
    canine = load_premade_deck("canine_buff_tempo")
    pile = load_premade_deck("goodstuff")
    hand_a = ["dire_wolf", "gray_wolf", "dingo", "raksha", "fox", "red_wolf"]
    hand_b = ["tiger", "elephant", "lemming", "gale", "tiger", "rhinoceros", "rhinoceros", "elephant"]
    deck_a, deck_b = list(canine), list(pile)
    for c in hand_a + ["red_wolf"]:
        deck_a.remove(c)
    for c in hand_b:
        deck_b.remove(c)
    s = GameState(load_map("map_b"), load_cards(), Config.default(), board={},
                  hands={"A": [], "B": []}, decks={"A": deck_a, "B": deck_b},
                  remove_pile=[], food={"A": 0, "B": 0}, current="A", first_player="A")
    for player, ids in (("A", hand_a), ("B", hand_b)):
        for c in ids:
            s.add_to_hand(player, c)
    s.board["1,2"] = [UnitInstance("red_wolf", "A", s.new_iid(), placed_on_turn=0)]
    s.turn_counter = 2
    s.actions_taken_this_turn = 1

    # Draw and the placements sit within a point of each other, so one seed is a coin flip:
    # the right move has to win on every seed.
    for seed in range(5):
        chosen = bot_cls(seed=seed).choose(s.view_for("A"), rules.legal_actions(s), s)
        assert isinstance(chosen, PlaceAction) and chosen.card_id in {"red_wolf", "fox", "dingo"}, seed
