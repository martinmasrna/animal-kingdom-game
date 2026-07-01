"""M3 tests for GreedyBot and its evaluation heuristic.

Reuses the constructed-state helpers from the effects tests' conventions. Map A geometry:
A's HQ fronts are column 1, B's are column 4; the grid is 4x3 with orthogonal neighbours.
"""

from __future__ import annotations

from animal_kingdom.bots.greedy_bot import GreedyBot, GreedyWeights, _battlecry_fizzled, evaluate
from animal_kingdom.decks import load_premade_deck
from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import PlaceAction
from animal_kingdom.engine.cards import load_cards
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.maps import load_map
from animal_kingdom.engine.state import GameState, UnitInstance, new_game

W = GreedyWeights()


def make_state(*, current="A", hands=None, decks=None, food=None) -> GameState:
    state = GameState(
        load_map("map_a"), load_cards(), Config.default(),
        board={}, hands={"A": [], "B": []}, decks=decks or {"A": [], "B": []},
        remove_pile=[], food=food or {"A": 0, "B": 0}, current=current, first_player="A",
    )
    for player, ids in (hands or {}).items():
        for card_id in ids:
            state.add_to_hand(player, card_id)
    return state


def put(state: GameState, cr: str, card_id: str, owner: str) -> UnitInstance:
    u = UnitInstance(card_id, owner, state.new_iid(), placed_on_turn=state.turn_counter)
    state.board.setdefault(cr, []).append(u)
    return u


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


def test_standing_in_front_of_enemy_hq_is_valued():
    # Isolate the HQ-threat term (region-corner coverage otherwise confounds positions).
    only_hq = GreedyWeights(food_progress=0, food_proximity=0, board_presence=0,
                            connection=0, region_control=0, card_economy=0)
    threat = make_state()
    put(threat, "4,2", "lion", "A")          # in B's HQ front
    midboard = make_state()
    put(midboard, "2,2", "lion", "A")        # central, no HQ pressure
    assert evaluate(threat, "A", only_hq) > evaluate(midboard, "A", only_hq)


def test_enemy_in_front_of_own_hq_is_penalised():
    only_hq = GreedyWeights(food_progress=0, food_proximity=0, board_presence=0,
                            connection=0, region_control=0, card_economy=0)
    under_threat = make_state()
    put(under_threat, "1,2", "lion", "B")    # B sitting in A's HQ front
    assert evaluate(under_threat, "A", only_hq) < 0


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


def test_lookahead_finds_the_grizzly_bear_delayed_removal_that_1_ply_misses():
    # A strength-7 blocker (same as Grizzly Bear's own strength, stronger than my only other
    # cards in hand) can't be covered directly by anything I hold - the only way to clear it
    # is Grizzly Bear's "in 2 turns, remove a random adjacent enemy" battlecry. 1-ply (and
    # even 2-ply, since the delay hasn't elapsed yet) can't see that payoff at all and treats
    # Grizzly Bear as a plain vanilla body; deep enough own-line lookahead plays the position
    # forward far enough for the removal to actually happen on the board, so it shows up.
    s = make_state(hands={"A": ["grizzly_bear", "lion", "mouse", "mouse"], "B": ["mouse"]},
                   decks={"A": ["mouse"] * 5, "B": ["mouse"] * 5})
    put(s, "2,2", "lion", "B")
    legal = rules.legal_actions(s)

    shallow = GreedyBot(depth=2, seed=0).choose(s.view_for("A"), legal, s)
    deep = GreedyBot(depth=3, seed=0).choose(s.view_for("A"), legal, s)

    assert shallow != PlaceAction("grizzly_bear", ("cr", "1,2"))
    assert deep == PlaceAction("grizzly_bear", ("cr", "1,2"))


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


def test_vanilla_card_is_never_fizzled():
    # Lion has no ability text, so there's nothing for it to waste.
    s = make_state(hands={"A": ["lion"]})
    action = PlaceAction("lion", ("cr", "1,2"))
    nxt = s.clone()
    rules.apply_action(nxt, action)
    assert not _battlecry_fizzled(s, nxt, "A", action)


def test_choose_prefers_a_live_battlecry_over_a_fizzling_one():
    # With no target for Rat and an empty deck, Mouse's "draw a Rodent" is the only card
    # whose battlecry can actually do something - the bot should prefer it.
    s = make_state(hands={"A": ["rat", "mouse"]}, decks={"A": ["mouse"] * 3, "B": []})
    legal = rules.legal_actions(s)
    chosen = GreedyBot(seed=0).choose(s.view_for("A"), legal, s)
    assert chosen.card_id == "mouse"
