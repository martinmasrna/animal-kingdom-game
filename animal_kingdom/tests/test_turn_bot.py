"""Tests for TurnBot - the scalable complete-own-turn planner (bots/turn_bot.py).

TurnBot shares the determinized information-set search with RefereeBot but stops at the turn
boundary instead of rolling out the opponent's reply, so the discriminating behaviours are:
it sequences a whole two-action turn as one plan (draw -> play, ordered Battlecries, effect-
granted extra placements), it stays honest about hidden information, it refuses to hang its
HQ, and it models any opponent-owned sub-choice opened during its turn adversarially. The
tests here cover the acceptance list, plus one
same-turn sequencing puzzle per deck family so the bot can't be tuned only to Colony.

Map A geometry: A's HQ fronts are column 1, B's column 4; a 4x3 grid of "col,row"
crossroads with orthogonal neighbours.
"""

from __future__ import annotations

from animal_kingdom.bots.turn_bot import TurnBot
from animal_kingdom.decks import load_premade_deck
from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import ChoiceAction, DrawAction, PlaceAction
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.state import new_game
from animal_kingdom.sim.runner import run_pairs

from .test_greedy_bot import make_state, put

TWO_ACTION = Config.default().sweep(actions_per_turn=2, draw_action_count=1)


def small_turn(seed=0) -> TurnBot:
    """Cheap configuration for behaviour tests (worlds x beam kept tiny)."""
    return TurnBot(seed=seed, determinizations=2, beam_width=4)


def play_turn(bot: TurnBot, s, seat: str = "A") -> list:
    """Drive `bot` through `seat`'s whole turn, returning the actions it took."""
    actions = []
    guard = 0
    while s.current == seat and rules.is_terminal(s) is None and guard < 30:
        guard += 1
        action = bot.choose(s.view_for(s.player_to_act()), rules.legal_actions(s), s)
        actions.append(action)
        rules.apply_action(s, action)
    return actions


def own_ids(s, seat: str = "A") -> list[str]:
    return [u.card_id for stack in s.board.values() for u in stack if u.owner == seat]


# ------------------------------------------------------------------- tactics / sanity

def test_takes_lethal_hq_capture():
    s = make_state(hands={"A": ["lion"]})
    for cr in ("1,1", "2,1", "3,1", "4,1"):   # "4,1" is in B's HQ front
        put(s, cr, "lion", "A")
    legal = rules.legal_actions(s)
    assert PlaceAction("lion", ("hq", "B")) in legal
    assert small_turn().choose(s.view_for("A"), legal, s) == PlaceAction("lion", ("hq", "B"))


# --------------------------------------------------- 1: complete two-action turn as one plan

def test_plans_draw_then_queen_then_king_as_one_turn():
    # The locally best first action is to slam the Queen body immediately; the whole-turn plan
    # is to Draw (to reach the King on top of deck), play the Queen (grants an extra Colony
    # play), then the King - only visible when both actions are scored together.
    s = make_state(current="A", hands={"A": ["termite_queen"]},
                   decks={"A": ["termite_king"], "B": ["mouse"] * 4}, config=TWO_ACTION)
    bot = small_turn()
    assert bot.choose(s.view_for("A"), rules.legal_actions(s), s) == DrawAction()
    rules.apply_action(s, DrawAction())

    queen = bot.choose(s.view_for("A"), rules.legal_actions(s), s)
    assert isinstance(queen, PlaceAction) and queen.card_id == "termite_queen"
    rules.apply_action(s, queen)
    assert any(isinstance(a, PlaceAction) and a.card_id == "termite_king"
               for a in rules.legal_actions(s))


# ------------------------------------------------- 2: shares the Draw, then adapts to the card

def test_shares_draw_then_adapts_to_the_observed_card():
    # Worlds that differ only in the (unobserved) top of deck share the opening Draw; once the
    # card is actually drawn the follow-up is conditioned on it - a strong draw gets played, a
    # weak one may be held. (The "share the Draw across indistinguishable worlds" invariant is
    # the same honesty property asserted directly in test_ignores_hidden_information.)
    def follow_up(top: str):
        # A already occupies B's HQ front, so whatever is drawn can capture. Hand starts empty,
        # so the opening is forced to Draw; the deck's last card is drawn and then wins.
        s = make_state(current="A", hands={"A": []},
                       decks={"A": ["rat", top], "B": ["mouse"] * 4}, config=TWO_ACTION)
        for cr in ("1,1", "2,1", "3,1", "4,1"):   # "4,1" is B's HQ front
            put(s, cr, "lion", "A")
        bot = small_turn()
        first = bot.choose(s.view_for("A"), rules.legal_actions(s), s)
        assert first == DrawAction()
        rules.apply_action(s, first)
        return bot.choose(s.view_for("A"), rules.legal_actions(s), s)

    strong = follow_up("cheetah")
    weak = follow_up("mouse")
    assert isinstance(strong, PlaceAction) and strong.is_hq_capture and strong.card_id == "cheetah"
    assert weak.is_hq_capture and weak.card_id == "mouse"
    assert strong != weak                     # the follow-up uses whichever card was observed


# ------------------------------------------------------ 4: effect-granted extra placements

def test_plans_nurse_then_queen_bee_then_worker_as_one_turn():
    s = make_state(current="A", hands={"A": ["nurse_bumblebee"]},
                   decks={"A": ["worker_wasp", "queen_bee"], "B": ["mouse"] * 4},
                   config=TWO_ACTION)
    for cr in ("1,1", "1,2", "1,3", "2,1", "2,2"):
        put(s, cr, "guard_hornet", "A")
    bot = small_turn()

    nurse = bot.choose(s.view_for("A"), rules.legal_actions(s), s)
    assert isinstance(nurse, PlaceAction) and nurse.card_id == "nurse_bumblebee"
    rules.apply_action(s, nurse)

    queen = bot.choose(s.view_for("A"), rules.legal_actions(s), s)
    assert isinstance(queen, PlaceAction) and queen.card_id == "queen_bee"
    rules.apply_action(s, queen)
    assert all(isinstance(a, PlaceAction) and a.card_id == "worker_wasp"
               for a in rules.legal_actions(s))


def test_resolves_mandatory_removal_target_choice():
    # Jaguar's Battlecry must remove one adjacent enemy; the search resolves the pending pick
    # rather than leaving the turn unfinished. It should take the stronger legal target.
    s = make_state(current="A", hands={"A": ["jaguar"]},
                   decks={"A": [], "B": ["mouse"] * 4}, config=TWO_ACTION)
    put(s, "1,1", "lion", "A")
    put(s, "2,1", "mouse", "B")     # str 1, adjacent to 1,1
    put(s, "1,2", "caracal", "B")   # str 4, adjacent to 1,1 - the better removal
    rules.apply_action(s, PlaceAction("jaguar", ("cr", "1,1")))  # covers lion, adjacent to both
    legal = rules.legal_actions(s)
    assert all(isinstance(a, ChoiceAction) for a in legal)
    chosen = small_turn().choose(s.view_for("A"), legal, s)
    assert chosen == ChoiceAction("1,2")   # removes the caracal (str 4), not the mouse


# ------------------------------------------------------------ 5: adversarial opponent choice

def test_models_opponent_subchoice_adversarially():
    # No card in the current pool hands the *opponent* a choice during your turn, so build one:
    # a pending where B picks which of A's units to remove. B, modelled adversarially, must be
    # assumed to take the worst option for A - removing the strong Lion, not the weak Mouse.
    s = make_state(current="A", hands={"A": []},
                   decks={"A": [], "B": ["mouse"] * 4}, config=TWO_ACTION)
    put(s, "1,1", "lion", "A")      # str 7
    put(s, "1,3", "mouse", "A")     # str 1
    s.actions_taken_this_turn = s.config.actions_per_turn   # A has no top-level actions left
    s.pending = {"mode": "choice", "chooser": "B", "optional": False,
                 "options": ["1,1", "1,3"]}
    s.effect_stack = [{"op": "remove_choice", "chooser": "B", "by_player": "B",
                       "by_card": None, "options": ["1,1", "1,3"]}]

    out = small_turn()._complete_own_turn([(s.clone(), 0.0)], "A", guard=0)
    assert len(out) == 1
    final = out[0][0]
    assert final.top_unit("1,1") is None                      # Lion assumed removed (worst for A)
    assert final.top_unit("1,3") is not None
    assert final.top_unit("1,3").card_id == "mouse"


# --------------------------------------------------------------------------- 6: HQ safety

def test_blocks_imminent_hq_threat_from_a_held_card():
    # B's connected chain already stands on A's HQ front ("1,2"); every A line except covering
    # it lets B capture next turn. TurnBot must find the block with no lethal-check crutch.
    s = make_state(current="A", hands={"A": ["lion", "mouse"]},
                   decks={"A": ["rat"], "B": ["mouse", "mouse"]})
    s.add_to_hand("B", "mouse")
    for cr in ("4,2", "3,2", "2,2", "1,2"):
        put(s, cr, "mouse", "B")
    legal = rules.legal_actions(s)
    block = PlaceAction("lion", ("cr", "1,2"))
    assert block in legal
    assert small_turn().choose(s.view_for("A"), legal, s) == block


def test_blocks_draw_then_capture_threat_during_an_effect_choice():
    # Two-action shape: an empty opposing hand can still draw and capture. Resolve Jaguar's
    # pending target by breaking the HQ lane, not by grabbing an irrelevant unit.
    s = make_state(current="A", hands={"A": ["jaguar"]},
                   decks={"A": ["mouse"], "B": ["mouse"]}, config=TWO_ACTION)
    for cr in ("4,2", "3,2", "2,2", "1,2", "2,1"):
        put(s, cr, "mouse", "B")
    rules.apply_action(s, PlaceAction("jaguar", ("cr", "1,1")))
    legal = rules.legal_actions(s)
    assert set(legal) == {ChoiceAction("1,2"), ChoiceAction("2,1")}
    assert small_turn().choose(s.view_for("A"), legal, s) == ChoiceAction("1,2")


# --------------------------------------------------------- 3: no hidden-information leak

def test_ignores_hidden_information():
    # Two states identical in everything A can see; B's hand/deck split and A's own deck order
    # differ. An honest bot must choose identically.
    def position(b_hand, b_deck, a_deck):
        s = make_state(current="A", hands={"A": ["lion", "rat"]},
                       decks={"A": list(a_deck), "B": list(b_deck)})
        for card_id in b_hand:
            s.add_to_hand("B", card_id)
        put(s, "2,2", "mouse", "B")
        put(s, "1,1", "lion", "A")
        return s

    s1 = position(b_hand=["lion", "mouse"], b_deck=["rat", "caracal"], a_deck=["mouse", "caracal"])
    s2 = position(b_hand=["rat", "caracal"], b_deck=["lion", "mouse"], a_deck=["caracal", "mouse"])
    legal1, legal2 = rules.legal_actions(s1), rules.legal_actions(s2)
    assert legal1 == legal2
    a1 = small_turn(seed=0).choose(s1.view_for("A"), legal1, s1)
    a2 = small_turn(seed=0).choose(s2.view_for("A"), legal2, s2)
    assert a1 == a2


# --------------------------------------------------------------------- 7: determinism

def test_choose_is_deterministic():
    s = new_game(load_premade_deck("ramp"), load_premade_deck("aggro_hq_rush"), seed=3)
    actor = s.player_to_act()
    legal = rules.legal_actions(s)
    a1 = small_turn(seed=0).choose(s.view_for(actor), legal, s)
    a2 = small_turn(seed=0).choose(s.view_for(actor), legal, s)
    assert a1 == a2


def test_serial_and_parallel_simulations_match():
    pairs = [("ramp", "cats_midrange")]
    kw = dict(bots=("turn", "greedy"), map_id="map_b", config=TWO_ACTION)
    serial = run_pairs(pairs, 4, base_seed=683470156, jobs=1, **kw)
    parallel = run_pairs(pairs, 4, base_seed=683470156, jobs=2, **kw)
    assert [r.to_dict() for r in serial] == [r.to_dict() for r in parallel]


# ----------------------------------------------------------------- 8: performance guard

def test_beam_prunes_a_wide_flight_fixture():
    # A single Flight unit is legal on many crossroads; the beam must not keep them all.
    s = make_state(current="A", hands={"A": ["bat"]}, decks={"A": ["mouse"] * 3})
    put(s, "1,1", "lion", "A")   # give A a connected anchor so plenty of tiles are legal
    bot = small_turn()
    legal = rules.legal_actions(s)
    placements = [a for a in legal if isinstance(a, PlaceAction)]
    assert len(placements) >= 8                       # genuinely wide fixture
    kept = bot._beam(s, list(legal), "A")
    assert len(kept) < len(legal)                     # pruning happened
    assert len(kept) <= bot.beam_width + 3            # bounded by beam + a few reserved


# ------------------------------------------- same-turn puzzles, one per non-Colony family

def test_cats_plays_twin_enabler_before_the_twin():
    # house_cat's Battlecry plays one more Cat when you control another Cat. Playing it first
    # (extra-casting caracal) avoids the wasted-Battlecry both cards fizzling the other order.
    s = make_state(current="A", hands={"A": ["house_cat", "caracal"]},
                   decks={"A": [], "B": ["mouse"] * 4}, config=TWO_ACTION)
    put(s, "1,1", "lion", "A")     # the "another Cat" house_cat needs
    bot = small_turn()
    first = bot.choose(s.view_for("A"), rules.legal_actions(s), s)
    assert isinstance(first, PlaceAction) and first.card_id == "house_cat"
    play_turn(bot, s)
    assert {"house_cat", "caracal"} <= set(own_ids(s))


def test_canine_buffs_before_the_strength_gated_payoff():
    # Coyote only draws at 5+ strength. Raksha (+2 to your other Canines) must land first so
    # the str-3 Coyote reaches 5 and its Battlecry fires instead of fizzling.
    s = make_state(current="A", hands={"A": ["raksha", "coyote"]},
                   decks={"A": ["dog", "dog", "dog"], "B": ["mouse"] * 4}, config=TWO_ACTION)
    bot = small_turn()
    first = bot.choose(s.view_for("A"), rules.legal_actions(s), s)
    assert isinstance(first, PlaceAction) and first.card_id == "raksha"


def test_rattlesnake_grows_from_ravens_two_shuffles():
    s = make_state(current="A", hands={"A": ["rattlesnake", "raven"]},
                   decks={"A": ["eagle", "eagle", "eagle", "eagle"], "B": ["mouse"] * 4},
                   food={"A": 0, "B": 0}, config=TWO_ACTION)
    rules.apply_action(s, PlaceAction("rattlesnake", ("cr", "1,2")))
    rules.apply_action(s, PlaceAction("raven", ("cr", "2,2")))
    while s.pending is not None:
        rules.apply_action(s, rules.legal_actions(s)[0])
    assert s.card_strength_counters["A"]["rattlesnake"] == 2


def test_ramp_pays_food_for_the_big_body_battlecry():
    # Bulwark costs 20 food and clears adjacent enemies. With food in the bank TurnBot spends
    # it to play the big body; placing it on the connected HQ front next to the enemy wipes it.
    s = make_state(current="A", hands={"A": ["bulwark"]},
                   decks={"A": ["mouse"] * 3, "B": ["mouse"] * 4},
                   food={"A": 30, "B": 0}, config=TWO_ACTION)
    put(s, "1,1", "lion", "A")      # connects the HQ front
    for cr in ("4,2", "3,2", "2,2", "1,2"):
        put(s, cr, "mouse", "B")     # genuine connected enemy chain to A's HQ
    bot = small_turn()
    play_turn(bot, s)
    assert "bulwark" in own_ids(s, "A")
    assert s.food["A"] <= 12                              # paid the 20-food cost
    top = s.top_unit("1,2")
    assert top is None or top.owner == "A"                # enemy on A's HQ front neutralized


def test_aggro_swarms_extra_body_before_the_filler():
    # Jerboa's Battlecry plays another unit; leading with it extra-casts the Cheetah for free
    # instead of fizzling one of the two.
    s = make_state(current="A", hands={"A": ["jerboa", "cheetah"]},
                   decks={"A": [], "B": ["mouse"] * 4}, config=TWO_ACTION)
    put(s, "1,1", "lion", "A")
    bot = small_turn()
    first = bot.choose(s.view_for("A"), rules.legal_actions(s), s)
    assert isinstance(first, PlaceAction) and first.card_id == "jerboa"
    play_turn(bot, s)
    assert {"jerboa", "cheetah"} <= set(own_ids(s))
