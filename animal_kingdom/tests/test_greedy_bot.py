"""M3 tests for GreedyBot and its evaluation heuristic.

Reuses the constructed-state helpers from the effects tests' conventions. Map A geometry:
A's HQ fronts are column 1, B's are column 4; the grid is 4x3 with orthogonal neighbours.
"""

from __future__ import annotations

import pytest

from animal_kingdom.bots.greedy_bot import (
    GreedyBot,
    GreedyWeights,
    _battlecry_fizzled,
    _enabled_battlecry_count,
    evaluate,
)
from animal_kingdom.decks import load_premade_deck
from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import ChoiceAction, DrawAction, PlaceAction
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.state import GameState, new_game

from ._helpers import make_state, put

W = GreedyWeights()


# --------------------------------------------------------------------- choose

def test_takes_lethal_hq_capture():
    # A holds a connected column to B's HQ front, so an HQ capture is legal — and lethal.
    s = make_state(hands={"A": ["lion"]})
    for cr in ("1,1", "2,1", "3,1", "4,1"):   # "4,1" is in B's HQ front
        put(s, cr, "lion", "A")

    legal = rules.legal_actions(s)
    assert PlaceAction("lion", ("hq", "B")) in legal     # the capture is on offer
    chosen = GreedyBot(seed=0).choose(s.view_for("A"), legal, s)
    assert chosen == PlaceAction("lion", ("hq", "B"))    # the bot takes the win


def test_prefers_stronger_of_two_placements():
    # Same crossroad (so region/connection terms match) — the stronger body wins on presence.
    s = make_state(hands={"A": ["lion", "mouse"]})
    legal = [PlaceAction("lion", ("cr", "1,1")), PlaceAction("mouse", ("cr", "1,1"))]
    chosen = GreedyBot(seed=0).choose(s.view_for("A"), legal, s)
    assert chosen.card_id == "lion"


def test_choose_is_deterministic():
    s = new_game(load_premade_deck("ramp"), load_premade_deck("aggro_hq_rush"), seed=3)
    actor = s.player_to_act()
    legal = rules.legal_actions(s)
    a1 = GreedyBot(seed=0).choose(s.view_for(actor), legal, s)
    a2 = GreedyBot(seed=0).choose(s.view_for(actor), legal, s)
    assert a1 == a2


def test_no_state_falls_back_without_crashing():
    s = make_state(hands={"A": ["lion"]})
    legal = rules.legal_actions(s)
    assert GreedyBot(seed=0).choose(s.view_for("A"), legal, state=None) in legal


def test_blocks_draw_then_capture_threat_during_an_effect_choice():
    # Two-action regression from the 2026-07-02 Colony-vs-Cats game: B has reached A's
    # HQ front but has an empty hand. That is still lethal next turn because B can draw,
    # then capture. Jaguar must remove the unit at 1,2 rather than an irrelevant target.
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

    chosen = GreedyBot(seed=0).choose(s.view_for("A"), legal, s)
    assert chosen == ChoiceAction("1,2")


# ------------------------------------------------------------------- evaluate

def test_controlling_more_board_scores_higher():
    empty = make_state()
    held = make_state()
    put(held, "2,2", "lion", "A")
    assert evaluate(held, "A", W) > evaluate(empty, "A", W)


def test_more_food_scores_higher():
    poor = make_state(food={"A": 0, "B": 0})
    rich = make_state(food={"A": 30, "B": 0})
    assert evaluate(rich, "A", W) > evaluate(poor, "A", W)


def test_region_progress_is_nonlinear_and_symmetric():
    only_regions = GreedyWeights(
        food_progress=0, food_proximity=0, board_presence=0, connection=0,
        region_control=1, enemy_hq_threat=0, own_hq_threat=0, card_economy=0,
        effect_readiness=0,
    )
    mine = make_state()
    put(mine, "1,1", "lion", "A")
    theirs = make_state()
    put(theirs, "1,1", "lion", "B")
    assert evaluate(mine, "A", only_regions) == pytest.approx(10 * (1 / 4) ** 3)
    assert evaluate(theirs, "A", only_regions) == -evaluate(mine, "A", only_regions)


def test_standing_in_front_of_enemy_hq_is_valued():
    # Isolate the HQ-threat term: the front unit is connected all the way from A's HQ.
    only_hq = GreedyWeights(food_progress=0, food_proximity=0, board_presence=0,
                            connection=0, region_control=0, own_hq_threat=0,
                            card_economy=0, effect_readiness=0)
    threat = make_state()
    for cr in ("1,2", "2,2", "3,2", "4,2"):
        put(threat, cr, "lion", "A")
    midboard = make_state()
    for cr in ("1,2", "2,2", "3,2"):
        put(midboard, cr, "lion", "A")
    assert evaluate(threat, "A", only_hq) > evaluate(midboard, "A", only_hq)


def test_isolated_flight_unit_is_not_an_hq_threat():
    only_hq = GreedyWeights(food_progress=0, food_proximity=0, board_presence=0,
                            connection=0, region_control=0, own_hq_threat=0,
                            card_economy=0, effect_readiness=0)
    isolated = make_state()
    put(isolated, "4,2", "eagle", "A")
    assert evaluate(isolated, "A", only_hq) == evaluate(make_state(), "A", only_hq)


def test_enemy_in_front_of_own_hq_is_penalised():
    only_hq = GreedyWeights(food_progress=0, food_proximity=0, board_presence=0,
                            connection=0, region_control=0, enemy_hq_threat=0,
                            card_economy=0, effect_readiness=0)
    under_threat = make_state()
    for cr in ("4,2", "3,2", "2,2", "1,2"):
        put(under_threat, cr, "lion", "B")
    assert evaluate(under_threat, "A", only_hq) < 0


def test_isolated_enemy_flight_unit_is_not_connected_hq_danger():
    only_hq = GreedyWeights(food_progress=0, food_proximity=0, board_presence=0,
                            connection=0, region_control=0, enemy_hq_threat=0,
                            card_economy=0, effect_readiness=0)
    isolated = make_state()
    put(isolated, "1,2", "eagle", "B")
    assert evaluate(isolated, "A", only_hq) == evaluate(make_state(), "A", only_hq)


def test_terminal_win_and_loss_are_decisive():
    from animal_kingdom.engine.state import Result
    won = make_state()
    won.result = Result("A", "hq_capture")
    lost = make_state()
    lost.result = Result("B", "hq_capture")
    assert evaluate(won, "A", W) == float("inf")
    assert evaluate(lost, "A", W) == float("-inf")


def test_eval_ignores_opponent_hand_contents():
    # Only the opponent's hand *count* is knowable; the card ids must not move the score.
    s1 = make_state(hands={"B": ["lion", "lion"]})
    s2 = make_state(hands={"B": ["mouse", "mouse"]})
    assert evaluate(s1, "A", W) == evaluate(s2, "A", W)


# ------------------------------------------------------- coverage-exposure belief term

# Isolate the coverage_exposure term (all other weights zeroed).
ONLY_COV = GreedyWeights(food_progress=0, food_proximity=0, board_presence=0, connection=0,
                         region_control=0, enemy_hq_threat=0, own_hq_threat=0, card_economy=0,
                         effect_readiness=0, coverage_exposure=40.0)


def _exposed_state(*, hands=None, decks=None) -> GameState:
    """A's strength-1 mouse defends HQ-front '1,2'; B has a connected chain 4,2-3,2-2,2 so
    '1,2' is a legal (coverable) placement for B next turn."""
    s = make_state(hands=hands, decks=decks)
    put(s, "1,2", "mouse", "A")
    for cr in ("4,2", "3,2", "2,2"):
        put(s, cr, "lion", "B")
    return s


def test_coverage_exposure_is_off_by_default():
    # Default weights (coverage_exposure=0.0) must not change any behaviour.
    strong = _exposed_state(hands={"B": ["lion"]})
    weak = _exposed_state(hands={"B": ["mouse"]})
    assert evaluate(strong, "A", W) == evaluate(weak, "A", W)


def test_coverage_exposure_penalises_a_probable_cover():
    # B certainly holds a coverer (lion 7 > mouse 1) -> full penalty; a mouse can't cover.
    certain = _exposed_state(hands={"B": ["lion"]})
    harmless = _exposed_state(hands={"B": ["mouse"]})
    assert evaluate(certain, "A", ONLY_COV) < evaluate(harmless, "A", ONLY_COV)
    assert evaluate(harmless, "A", ONLY_COV) == 0.0        # no coverer -> no exposure


def test_coverage_exposure_scales_with_probability():
    # Same coverer, different odds it's in hand: certain (hand) > 50% (1 of 2) > none.
    certain = _exposed_state(hands={"B": ["lion"]})                 # p = 1.0
    fifty = _exposed_state(hands={"B": ["mouse"]}, decks={"B": ["lion"]})  # p = 0.5
    none = _exposed_state(hands={"B": ["mouse"]})                   # p = 0.0
    assert evaluate(certain, "A", ONLY_COV) < evaluate(fifty, "A", ONLY_COV) \
        < evaluate(none, "A", ONLY_COV)


def test_coverage_exposure_is_partition_invariant_honesty_guard():
    # THE honesty boundary: holding the unseen multiset (lion+mouse) and hand SIZE (1) fixed,
    # which card sits in hand vs deck must not move the score. If it does, it's a hidden peek.
    lion_in_hand = _exposed_state(hands={"B": ["lion"]}, decks={"B": ["mouse"]})
    mouse_in_hand = _exposed_state(hands={"B": ["mouse"]}, decks={"B": ["lion"]})
    assert evaluate(lion_in_hand, "A", ONLY_COV) == evaluate(mouse_in_hand, "A", ONLY_COV)


def test_coverage_exposure_needs_reachability():
    # Identical hidden hand, but B has no board presence -> can't reach '1,2' -> no exposure.
    unreachable = make_state(hands={"B": ["lion"]})
    put(unreachable, "1,2", "mouse", "A")
    assert evaluate(unreachable, "A", ONLY_COV) == 0.0


# --------------------------------------------------------------- own-line lookahead

def test_default_depth_matches_original_1_ply_score():
    # depth=1 (the default) must be exactly the old behaviour: no fast-forwarding at all.
    s = new_game(load_premade_deck("ramp"), load_premade_deck("aggro_hq_rush"), seed=3)
    nxt = s.clone()
    rules.apply_action(nxt, rules.legal_actions(nxt)[0])
    assert GreedyBot(seed=0)._rollout_value(nxt, "A", 0) == evaluate(nxt, "A", W)


def test_lookahead_is_deterministic():
    s = new_game(load_premade_deck("ramp"), load_premade_deck("aggro_hq_rush"), seed=3)
    actor = s.player_to_act()
    legal = rules.legal_actions(s)
    a1 = GreedyBot(depth=3, seed=0).choose(s.view_for(actor), legal, s)
    a2 = GreedyBot(depth=3, seed=0).choose(s.view_for(actor), legal, s)
    assert a1 == a2


def test_pending_payoff_surfaces_grizzly_delayed_removal_at_1_ply():
    # A strength-7 blocker (stronger than Grizzly Bear's str-6 body and my other cards) can't be
    # covered directly by anything I hold - the only way to clear it is Grizzly Bear's "in 2
    # turns, remove a random adjacent enemy" battlecry. The blind eval (pending_payoff=0)
    # treats Grizzly as a plain vanilla body and needed deep own-line lookahead to play the
    # position forward until the removal fired; pending_payoff now credits the scheduled
    # removal directly, so the default 1-ply GreedyBot finds it without any lookahead. (That
    # subsumes the old lookahead-only demonstration of this exact line.)
    one_action = Config.default().sweep(actions_per_turn=1, draw_action_count=2)
    s = make_state(hands={"A": ["grizzly_bear", "lion", "mouse", "mouse"], "B": ["mouse"]},
                   decks={"A": ["mouse"] * 5, "B": ["mouse"] * 5}, config=one_action)
    put(s, "2,2", "lion", "B")
    legal = rules.legal_actions(s)
    grizzly = PlaceAction("grizzly_bear", ("cr", "1,2"))

    blind = GreedyBot(seed=0, weights=GreedyWeights(pending_payoff=0.0))
    assert blind.choose(s.view_for("A"), legal, s) != grizzly   # 1-ply blind eval misses it
    assert GreedyBot(seed=0).choose(s.view_for("A"), legal, s) == grizzly  # the fix finds it


# --------------------------------------------------------- wasted-battlecry detection

def test_battlecry_fizzles_with_no_target():
    # Rat's "remove a card in hand to destroy an adjacent enemy" has nothing to hit.
    s = make_state(hands={"A": ["rat", "mouse"]})
    action = PlaceAction("rat", ("cr", "1,2"))
    nxt = s.clone()
    rules.apply_action(nxt, action)
    assert _battlecry_fizzled(s, nxt, "A", action)


def test_battlecry_with_a_pending_choice_is_not_fizzled():
    # Rat with a valid adjacent target leaves an unresolved pending choice (which enemy) -
    # that's a live effect mid-resolution, not a fizzle, even though nothing has happened yet.
    s = make_state(hands={"A": ["rat", "mouse"]})
    put(s, "2,2", "mouse", "B")
    action = PlaceAction("rat", ("cr", "1,2"))
    nxt = s.clone()
    rules.apply_action(nxt, action)
    assert nxt.pending is not None
    assert not _battlecry_fizzled(s, nxt, "A", action)


def test_passive_rules_text_is_not_a_fizzled_battlecry():
    s = make_state(hands={"A": ["guard_hornet"]})
    action = PlaceAction("guard_hornet", ("cr", "1,2"))
    nxt = s.clone()
    rules.apply_action(nxt, action)
    assert not _battlecry_fizzled(s, nxt, "A", action)


def test_scheduled_battlecry_is_not_fizzled():
    s = make_state(hands={"A": ["grizzly_bear"]})
    action = PlaceAction("grizzly_bear", ("cr", "1,2"))
    nxt = s.clone()
    rules.apply_action(nxt, action)
    assert nxt.scheduled
    assert not _battlecry_fizzled(s, nxt, "A", action)


def test_effect_readiness_detects_enabled_condition_without_card_special_case():
    disabled = make_state(
        hands={"A": ["nurse_bee"]},
        decks={"A": ["mouse", "lion"], "B": []},
    )
    enabled = disabled.clone()
    put(enabled, "1,1", "guard_hornet", "A")
    put(enabled, "1,2", "guard_hornet", "A")
    assert _enabled_battlecry_count(disabled, "A") == 0
    assert _enabled_battlecry_count(enabled, "A") == 1


def test_vanilla_card_is_never_fizzled():
    # Lion has no ability text, so there's nothing for it to waste.
    s = make_state(hands={"A": ["lion"]})
    action = PlaceAction("lion", ("cr", "1,2"))
    nxt = s.clone()
    rules.apply_action(nxt, action)
    assert not _battlecry_fizzled(s, nxt, "A", action)


def test_choose_does_not_waste_a_battlecry_when_drawing_has_more_value():
    # Mouse is live and Rat is not, but the standard draw produces more immediate card
    # economy than spending Mouse to replace itself. The readiness term must not force a
    # live Battlecry over a strictly better non-placement action.
    s = make_state(hands={"A": ["rat", "mouse"]}, decks={"A": ["mouse"] * 3, "B": []})
    legal = rules.legal_actions(s)
    chosen = GreedyBot(seed=0).choose(s.view_for("A"), legal, s)
    assert isinstance(chosen, DrawAction)
