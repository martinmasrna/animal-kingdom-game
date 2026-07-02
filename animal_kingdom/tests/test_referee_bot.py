"""Tests for RefereeBot - the determinized adversarial calibration bot.

The discriminating behaviors are the ones GreedyBot structurally lacks: seeing the
opponent's punishing reply (so holding a card to draw can beat a doomed placement)
and doing so without reading hidden information (no-cheat by construction).
Map A geometry reminder: A's HQ fronts are column 1, B's are column 4; orthogonal
neighbours on a 4x3 grid of "col,row" crossroads.
"""

from __future__ import annotations

from animal_kingdom.bots.greedy_bot import GreedyBot
from animal_kingdom.bots.referee_bot import RefereeBot
from animal_kingdom.decks import load_premade_deck
from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import DrawAction, PlaceAction
from animal_kingdom.engine.state import new_game

from .test_greedy_bot import make_state, put


def small_referee(seed=0) -> RefereeBot:
    """Cheap configuration for behavior tests (worlds x beam kept tiny)."""
    return RefereeBot(seed=seed, determinizations=2, beam_width=4)


# --------------------------------------------------------------------- tactics

def test_takes_lethal_hq_capture():
    s = make_state(hands={"A": ["lion"]})
    for cr in ("1,1", "2,1", "3,1", "4,1"):   # "4,1" is in B's HQ front
        put(s, cr, "lion", "A")

    legal = rules.legal_actions(s)
    assert PlaceAction("lion", ("hq", "B")) in legal
    chosen = small_referee().choose(s.view_for("A"), legal, s)
    assert chosen == PlaceAction("lion", ("hq", "B"))


def test_blocks_imminent_hq_threat_from_the_adversarial_reply():
    # B's connected chain already stands on "1,2" (A's HQ front): every A line except
    # covering "1,2" lets the simulated B reply capture A's HQ (-1e9 in every world).
    # GreedyBot needs the special-cased _opponent_lethal_next_turn check for this;
    # the referee's rollout must find it with no crutch.
    s = make_state(current="A", hands={"A": ["lion", "mouse"]},
                   decks={"A": ["rat"], "B": ["mouse", "mouse"]})
    s.add_to_hand("B", "mouse")               # B must hold a card for the capture
    for cr in ("4,2", "3,2", "2,2", "1,2"):
        put(s, cr, "mouse", "B")

    legal = rules.legal_actions(s)
    block = PlaceAction("lion", ("cr", "1,2"))
    assert block in legal
    chosen = small_referee().choose(s.view_for("A"), legal, s)
    assert chosen == block


def test_prefers_drawing_over_a_doomed_placement():
    # A's only placement is a mouse onto "1,2" (its lions on "1,1"/"1,3" wall off the
    # rest: B's str-1 chain can't be covered by a mouse, equal strength). B's pool is
    # all lions, so in every sampled world the reply covers the mouse - the placement
    # buys nothing and costs the card. Drawing keeps the hand advantage; the referee
    # must see the punishment coming. This is exactly the card-holding behavior the
    # 1-ply GreedyBot structurally lacks (asserted below as the discriminating
    # contrast - if greedy ever starts drawing here, the referee stops being the only
    # bot with this skill and the caveat docs should be revisited).
    s = make_state(current="A", hands={"A": ["mouse"]},
                   decks={"A": ["lion"], "B": ["lion", "lion"]})
    s.add_to_hand("B", "lion")
    s.add_to_hand("B", "lion")
    put(s, "1,1", "lion", "A")
    put(s, "1,3", "lion", "A")
    # "3,1"/"3,3" included: they corner the rich 20-food regions, and if left empty
    # B's simulated reply grabs one of those instead of punishing the mouse.
    for cr in ("4,2", "3,2", "2,2", "2,1", "2,3", "3,1", "3,3"):
        put(s, cr, "mouse", "B")

    legal = rules.legal_actions(s)
    doomed = PlaceAction("mouse", ("cr", "1,2"))
    # The only other placements are self-covers burying A's own lions - worse still.
    assert DrawAction() in legal and doomed in legal

    assert small_referee().choose(s.view_for("A"), legal, s) == DrawAction()
    assert GreedyBot(seed=0).choose(s.view_for("A"), legal, s) == doomed


# ------------------------------------------------------------- determinism / honesty

def test_choose_is_deterministic():
    s = new_game(load_premade_deck("ramp"), load_premade_deck("aggro_hq_rush"), seed=3)
    actor = s.player_to_act()
    legal = rules.legal_actions(s)
    a1 = small_referee(seed=0).choose(s.view_for(actor), legal, s)
    a2 = small_referee(seed=0).choose(s.view_for(actor), legal, s)
    assert a1 == a2


def test_referee_ignores_hidden_information():
    # Two states identical in everything A can see; B's hand/deck split and A's own
    # deck order differ. An honest bot must choose identically.
    def position(b_hand, b_deck, a_deck):
        s = make_state(current="A", hands={"A": ["lion", "rat"]},
                       decks={"A": list(a_deck), "B": list(b_deck)})
        for card_id in b_hand:
            s.add_to_hand("B", card_id)
        put(s, "2,2", "mouse", "B")
        put(s, "1,1", "lion", "A")
        return s

    s1 = position(b_hand=["lion", "mouse"], b_deck=["rat", "caracal"],
                  a_deck=["mouse", "caracal"])
    s2 = position(b_hand=["rat", "caracal"], b_deck=["lion", "mouse"],
                  a_deck=["caracal", "mouse"])

    legal1 = rules.legal_actions(s1)
    legal2 = rules.legal_actions(s2)
    assert legal1 == legal2
    a1 = small_referee(seed=0).choose(s1.view_for("A"), legal1, s1)
    a2 = small_referee(seed=0).choose(s2.view_for("A"), legal2, s2)
    assert a1 == a2


# ----------------------------------------------------------------- short circuits

def test_single_legal_action_short_circuits():
    s = make_state(hands={"A": ["lion"]}, decks={"A": [], "B": []})
    legal = [PlaceAction("lion", ("cr", "1,1"))]
    assert small_referee().choose(s.view_for("A"), legal, s) == legal[0]


def test_no_state_falls_back_without_crashing():
    s = make_state(hands={"A": ["lion"]})
    legal = rules.legal_actions(s)
    assert small_referee().choose(s.view_for("A"), legal, state=None) in legal
