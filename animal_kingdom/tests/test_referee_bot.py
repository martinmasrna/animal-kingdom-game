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
from animal_kingdom.engine.actions import ChoiceAction, DrawAction, PlaceAction
from animal_kingdom.engine.config import Config
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


def test_blocks_draw_then_capture_threat_during_an_effect_choice():
    # Exact tactical shape of the 2026-07-02 regression: with two actions per turn, an
    # empty opposing hand can still draw and capture. Resolve Jaguar's pending target
    # choice by breaking the HQ lane, not by taking an irrelevant unit for immediate value.
    config = Config.default().sweep(actions_per_turn=2, draw_action_count=1)
    s = make_state(
        current="A",
        hands={"A": ["jaguar"]},
        decks={"A": ["mouse"], "B": ["mouse"]},
        config=config,
    )
    for cr in ("4,2", "3,2", "2,2", "1,2", "2,1"):
        put(s, cr, "mouse", "B")

    rules.apply_action(s, PlaceAction("jaguar", ("cr", "1,1")))
    legal = rules.legal_actions(s)
    assert set(legal) == {ChoiceAction("1,2"), ChoiceAction("2,1")}

    chosen = small_referee().choose(s.view_for("A"), legal, s)
    assert chosen == ChoiceAction("1,2")


def test_plans_draw_then_queen_then_king_as_one_turn():
    config = Config.default().sweep(actions_per_turn=2, draw_action_count=1)
    s = make_state(
        current="A",
        hands={"A": ["termite_queen"]},
        decks={"A": ["termite_king"], "B": ["mouse"] * 4},
        config=config,
    )
    bot = small_referee()
    assert bot.choose(s.view_for("A"), rules.legal_actions(s), s) == DrawAction()
    rules.apply_action(s, DrawAction())

    queen = bot.choose(s.view_for("A"), rules.legal_actions(s), s)
    assert isinstance(queen, PlaceAction) and queen.card_id == "termite_queen"
    rules.apply_action(s, queen)
    assert any(
        isinstance(a, PlaceAction) and a.card_id == "termite_king"
        for a in rules.legal_actions(s)
    )


def test_plans_nurse_then_queen_bee_then_worker_as_one_turn():
    config = Config.default().sweep(actions_per_turn=2, draw_action_count=1)
    s = make_state(
        current="A",
        hands={"A": ["nurse_bumblebee"]},
        decks={"A": ["worker_wasp", "queen_bee"], "B": ["mouse"] * 4},
        config=config,
    )
    for cr in ("1,1", "1,2", "1,3", "2,1", "2,2"):
        put(s, cr, "guard_hornet", "A")

    bot = small_referee()
    nurse = bot.choose(s.view_for("A"), rules.legal_actions(s), s)
    assert isinstance(nurse, PlaceAction) and nurse.card_id == "nurse_bumblebee"
    rules.apply_action(s, nurse)

    queen = bot.choose(s.view_for("A"), rules.legal_actions(s), s)
    assert isinstance(queen, PlaceAction) and queen.card_id == "queen_bee"
    rules.apply_action(s, queen)
    assert all(
        isinstance(a, PlaceAction) and a.card_id == "worker_wasp"
        for a in rules.legal_actions(s)
    )


def test_saved_game_opening_preserves_the_duplicate_setup():
    config = Config.default().sweep(actions_per_turn=2, draw_action_count=1)
    s = new_game(
        load_premade_deck("colony_food_swarm"),
        load_premade_deck("cats_midrange"),
        seed=683470156,
        map_id="map_b",
        config=config,
    )
    bot = RefereeBot(seed=683470157)
    chosen = []
    while s.current == "A":
        action = bot.choose(s.view_for("A"), rules.legal_actions(s), s)
        chosen.append(action)
        rules.apply_action(s, action)

    assert [a.card_id for a in chosen if isinstance(a, PlaceAction)] == [
        "guard_hornet", "guard_hornet",
    ]
    assert all(isinstance(a, PlaceAction) for a in chosen)
    assert all(a.crossroad not in s.game_map.hq_front("B") for a in chosen)


def test_prefers_drawing_over_a_doomed_placement():
    # A's only placement is a mouse onto "1,2" (its lions on "1,1"/"1,3" wall off the
    # rest: B's str-1 chain can't be covered by a mouse, equal strength). B's pool is
    # all lions, so in every sampled world the reply covers the mouse - the placement
    # buys nothing and costs the card. Drawing keeps the hand advantage; the referee
    # must see the punishment coming. This is exactly the card-holding behavior the
    # 1-ply GreedyBot structurally lacks (asserted below as the discriminating
    # contrast historically distinguished the bots; the nonlinear region evaluator now
    # makes the shallow bot reject the doomed placement too.
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
    assert GreedyBot(seed=0).choose(s.view_for("A"), legal, s) == DrawAction()


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
