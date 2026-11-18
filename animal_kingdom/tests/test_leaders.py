"""The leaders prototype (branch leaders; engine/leaders.py): a deck's leader on its den, with a hero power, a
once-per-game power or a passive, and the leaders' cards as they change with it. Map A: a 4x3 grid "col,row"; A's den
fronts column 1, B's column 4."""

from __future__ import annotations

import dataclasses

import pytest

from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import ActAction, ChoiceAction, DrawAction, LeaderAction, PassAction, PlaceAction, action_from_dict
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.leaders import JULIETTE_WISHES, MELISSIA_SPEC, leader_state
from animal_kingdom.engine.state import EngineError, GameState, new_game
from animal_kingdom.engine.strength import effective_strength, placement_strength, strength_breakdown

from ._helpers import cards_with, hand_ids, make_state, put

CARDS = cards_with({"id": "t_big", "base_strength": 9}, {"id": "t_body", "base_strength": 4},
                   {"id": "t_small", "base_strength": 2}, {"id": "t_cat", "base_strength": 6, "tags": ["Cat"]})


def state(leader=None, who="A", **kw) -> GameState:
    s = make_state(cards=CARDS, **kw)
    if leader:
        s.leaders[who] = leader_state(leader)
    return s


def can_press(s) -> bool:
    return LeaderAction() in rules.legal_actions(s)


def press(s):
    rules.apply_action(s, LeaderAction())


def end_turn(s):
    """End the turn having acted (a Draw), so two turns in a row without acting never end the game."""
    if DrawAction() in rules.legal_actions(s):
        rules.apply_action(s, DrawAction())
    if s.actions_taken_this_turn:
        rules.apply_action(s, PassAction())


def choose(s, value):
    rules.apply_action(s, ChoiceAction(value))


# ===================================================================== the frame

def test_no_leader_no_den_power_and_nothing_new_in_play():
    s = state(decks={"A": ["t_body"] * 5, "B": []})
    assert not can_press(s)
    assert s.to_dict()["leaders"] == {}


def test_a_leader_must_be_a_leader_and_in_its_deck():
    deck = ["t_body"] * 24 + ["lion_legend_4"]
    st = new_game(deck, ["t_body"] * 25, 3, leaders={"A": "lion_legend_4"}, cards=CARDS)
    assert st.leaders["A"]["id"] == "lion_legend_4" and "B" not in st.leaders
    plain = new_game(deck, ["t_body"] * 25, 3, cards=CARDS)
    assert plain.decks == st.decks and plain.hands["A"][0].card_id == st.hands["A"][0].card_id   # same stream
    with pytest.raises(EngineError):
        new_game(["t_body"] * 25, ["t_body"] * 25, 3, leaders={"A": "lion_legend_4"}, cards=CARDS)
    with pytest.raises(EngineError):
        new_game(deck + ["lion"], ["t_body"] * 25, 3, leaders={"A": "lion"}, cards=CARDS)


def test_leader_state_round_trips_and_the_action_too():
    s = state("butterfly_legend")
    s.leaders["A"]["stage"] = 3
    d = GameState.from_dict(s.to_dict(), cards=CARDS).to_dict()
    assert d["leaders"] == {"A": {"id": "butterfly_legend", "kills": 0, "stage": 3, "spent": False}}
    assert action_from_dict(LeaderAction().to_dict()) == LeaderAction()
    c = s.clone()
    c.leaders["A"]["stage"] = 4
    assert s.leaders["A"]["stage"] == 3


# ===================================================================== the two Cat leaders

def test_adira_gains_five_food_when_one_of_her_cats_covers_an_enemy():
    s = state("lion_legend_4", hands={"A": ["t_cat", "t_body"]})
    put(s, "1,1", "t_small", "B")
    put(s, "1,2", "t_small", "B")
    rules.apply_action(s, PlaceAction("t_cat", ("cr", "1,1")))
    assert s.food["A"] == 5
    rules.apply_action(s, PlaceAction("t_body", ("cr", "1,2")))          # not a Cat: nothing
    assert s.food["A"] == 5


def test_adira_gains_nothing_for_a_cat_on_an_empty_crossroad_or_on_her_own_animal():
    s = state("lion_legend_4", hands={"A": ["t_cat", "t_cat"]})
    put(s, "1,2", "t_small", "A")
    rules.apply_action(s, PlaceAction("t_cat", ("cr", "1,1")))
    rules.apply_action(s, PlaceAction("t_cat", ("cr", "1,2")))
    assert s.food["A"] == 0


def test_theron_gives_the_cat_that_covered_one_strength():
    s = state("lion_legend_3", hands={"A": ["t_cat", "t_body"]})
    put(s, "1,1", "t_small", "B")
    put(s, "1,2", "t_small", "B")
    rules.apply_action(s, PlaceAction("t_cat", ("cr", "1,1")))
    assert effective_strength(s, s.board["1,1"][-1]) == 7
    rules.apply_action(s, PlaceAction("t_body", ("cr", "1,2")))          # not a Cat: nothing
    assert effective_strength(s, s.board["1,2"][-1]) == 4


def test_theron_gives_nothing_on_an_empty_crossroad_and_the_strength_comes_after_the_cover():
    s = state("lion_legend_3", hands={"A": ["t_cat", "t_cat"]})
    put(s, "1,2", "t_cat", "B")
    assert PlaceAction("t_cat", ("cr", "1,2")) not in rules.legal_actions(s)    # a 6 still can't cover a 6
    rules.apply_action(s, PlaceAction("t_cat", ("cr", "1,1")))
    assert effective_strength(s, s.board["1,1"][-1]) == 6


def test_the_cat_leaders_texts_print_their_config_numbers():
    from animal_kingdom.engine.config import Config
    from animal_kingdom.engine.leaders import LEADERS
    cfg = Config.default()
    assert f"gain {cfg.adira_leader_food} food" in LEADERS["lion_legend_4"][1]
    assert f"+{cfg.theron_leader_grant} strength" in LEADERS["lion_legend_3"][1]


def test_neither_cat_leader_has_a_den_to_press():
    for leader in ("lion_legend_4", "lion_legend_3"):
        assert not can_press(state(leader, decks={"A": ["t_body"] * 5, "B": []}, hands={"A": ["t_cat"]}))


# ===================================================================== the legendary Mole

def rules_adjacent(s, cr, target) -> bool:
    return target[0] == "cr" and s.game_map.adjacent(cr, target[1])


def test_the_mole_leader_draws_a_card_when_the_third_animal_of_a_turn_is_played():
    s = state("mole_legend", hands={"A": ["mole", "t_small", "t_small"], "B": ["t_small"]}, decks={"A": ["t_body"] * 5, "B": ["t_body"] * 5})
    rules.apply_action(s, PlaceAction("mole", ("cr", "1,1")))            # the Mole, and its extra animal next to it
    t = s.pending["placements"][0]
    assert all(rules_adjacent(s, "1,1", tuple(q["target"])) for q in s.pending["placements"])   # next to the Mole
    rules.apply_action(s, PlaceAction(t["card_id"], tuple(t["target"])))
    assert len(s.hands["A"]) == 1                                        # two animals played: nothing yet
    spot = next(q for q in rules.legal_actions(s) if isinstance(q, PlaceAction))
    rules.apply_action(s, spot)
    assert [u.card_id for u in s.hands["A"]] == ["t_body"] * Config.default().mole_leader_draw   # the third: a card


def test_the_mole_leader_gives_nothing_for_two_animals():
    s = state("mole_legend", hands={"A": ["t_small", "t_small"], "B": ["t_small"]}, decks={"A": ["t_body"] * 5, "B": ["t_body"] * 5})
    rules.apply_action(s, PlaceAction("t_small", ("cr", "1,1")))
    rules.apply_action(s, PlaceAction("t_small", ("cr", "1,2")))
    assert not s.hands["A"] and s.current == "B"


# ===================================================================== Don Santo

def test_don_santos_last_animal_in_hand_has_three_more_strength_and_keeps_it():
    s = state("macaque_legend", hands={"A": ["t_small", "t_small"], "B": ["t_small"]}, decks={"A": [], "B": ["t_body"] * 5})
    assert [placement_strength(s, u) for u in s.hands["A"]] == [2, 2]        # two in hand: neither is the last
    rules.apply_action(s, PlaceAction("t_small", ("cr", "1,1")))
    assert placement_strength(s, s.hands["A"][0]) == 5
    rules.apply_action(s, PlaceAction("t_small", ("cr", "1,2")))
    assert effective_strength(s, s.board["1,1"][-1]) == 2 and effective_strength(s, s.board["1,2"][-1]) == 5


# ===================================================================== Yuki

def test_yukis_leader_keeps_a_connected_ally_from_being_covered_until_her_next_turn_three_times_a_match():
    s = state("squirrel_legend", hands={"A": ["t_small"] * 4, "B": ["t_big"] * 4}, decks={"A": ["t_body"] * 9, "B": ["t_body"] * 9})
    for cr in ("1,1", "1,2", "2,1"):
        put(s, cr, "t_small", "A")
    put(s, "3,3", "t_small", "A")                                    # cut off from her den: no choice
    for cr in ("4,2", "3,2", "2,2"):
        put(s, cr, "t_small", "B")
    press(s)
    assert s.pending["options"] == ["1,1", "1,2", "2,1"]
    choose(s, "1,2")
    assert s.leaders["A"]["stage"] == 1
    rules.apply_action(s, PassAction())
    legal = rules.legal_actions(s)
    assert s.current == "B" and PlaceAction("t_big", ("cr", "1,2")) not in legal and PlaceAction("t_big", ("cr", "2,1")) in legal
    s.current, s.turn_counter = "B", s.turn_counter + 2              # her next turn has come and gone
    assert PlaceAction("t_big", ("cr", "1,2")) in rules.legal_actions(s)
    s.leaders["A"]["stage"], s.current = 3, "A"
    assert not can_press(s)                                          # three uses a match


# ===================================================================== Ash

def test_ashs_leader_gains_a_food_at_dusk_for_each_keyword_on_her_animals_double_next_to_an_enemy():
    s = state("honey_badger_legend", hands={"A": ["t_small"], "B": ["t_small"]}, decks={"A": ["t_body"] * 5, "B": ["t_body"] * 5})
    put(s, "3,1", "honey_badger_legend", "A")       # next to the Toad: Armor, Stealth, Poison, Spikes, doubled: 8
    put(s, "4,2", "tortoise", "A")                  # next to the Toad: Armor, doubled: 2
    put(s, "1,3", "tortoise", "A")                  # no enemy next to it: 1
    put(s, "3,3", "hedgehog", "A").retaliation_used = True     # spent Spikes: 0
    put(s, "4,1", "toad", "B")                      # hers, not Ash's
    rules.apply_action(s, PassAction()) if PassAction() in rules.legal_actions(s) else end_turn(s)
    assert s.food["A"] == 11


# ===================================================================== Iris

def test_iris_plays_a_fourth_copy_the_first_time_she_controls_three_copies_of_an_animal():
    s = state("chameleon_legend", hands={"A": ["t_small", "chameleon"], "B": ["t_small"]}, decks={"A": ["t_body"] * 5, "B": ["t_body"] * 5})
    put(s, "1,1", "t_small", "A")
    rules.apply_action(s, PlaceAction("t_small", ("cr", "1,2")))
    assert s.pending is None                                          # two copies: nothing
    rules.apply_action(s, PlaceAction("chameleon", ("cr", "1,3")))
    choose(s, "1,2")                                                  # the Chameleon becomes the third copy
    assert s.pending["mode"] == "place" and {q["card_id"] for q in s.pending["placements"]} == {"t_small"}
    t = next(q for q in s.pending["placements"] if q["target"][1] not in s.board)      # an empty crossroad
    rules.apply_action(s, PlaceAction(t["card_id"], tuple(t["target"])))
    assert sum(1 for stack in s.board.values() if stack[-1].card_id == "t_small" and stack[-1].owner == "A") == 4
    assert s.trios["A"] == {"t_small": 1} and s.pending is None      # once for each animal


# ===================================================================== Grimm

def test_grimm_draws_two_and_may_press_twice_a_turn():
    s = state("raven_legend", decks={"A": ["t_body"] * 10, "B": ["t_body"] * 5})
    press(s)
    assert len(s.hands["A"]) == 2 and s.actions_taken_this_turn == 1 and s.current == "A"
    assert can_press(s)
    press(s)
    assert len(s.hands["A"]) == 4 and s.current == "B"


def test_grimm_needs_a_deck():
    assert not can_press(state("raven_legend", decks={"A": [], "B": []}, hands={"A": ["t_body"]}))


def test_grimm_counts_every_enemy_removed_whatever_removed_it_and_draws_one_more_for_every_five():
    from animal_kingdom.engine.effects import remove_top
    s = state("raven_legend", decks={"A": ["t_body"] * 10, "B": []})
    for i in range(5):
        put(s, "1,1", "t_small", "B")
        remove_top(s, "1,1", by_player="A" if i % 2 else None, by_card="t_body" if i % 2 else None)
    put(s, "1,2", "t_small", "A")
    remove_top(s, "1,2", by_player="B", by_card="t_body")          # his own animal: no count
    assert s.leaders["A"]["kills"] == 5
    press(s)
    assert len(s.hands["A"]) == 3


# ===================================================================== Lady Juliette

def test_juliette_leader_gives_your_animals_plus_one_with_a_small_starting_deck():
    s = state("bee_legend_2", hands={"A": ["t_small"]})
    s.starting_decks = {"A": ("t_small",) * 24 + ("bee_legend_2",), "B": ()}
    u = put(s, "1,1", "t_small", "A")
    e = put(s, "4,1", "t_small", "B")
    assert effective_strength(s, u) == 3 and effective_strength(s, e) == 2
    assert placement_strength(s, s.hands["A"][0]) == 3
    assert ["bee_legend_2", 1] in strength_breakdown(s, u)["auras"]
    s.starting_decks = {"A": ("t_small",) * 23 + ("t_body", "bee_legend_2"), "B": ()}
    assert effective_strength(s, u) == 2


def test_juliettes_card_shows_three_small_animals_and_plays_the_one_chosen():
    s = state(hands={"A": ["bee_legend_2"]})
    s.starting_decks = {"A": ("t_small",) * 24 + ("bee_legend_2",), "B": ()}
    rules.apply_action(s, PlaceAction("bee_legend_2", ("cr", "1,1")))
    opts = s.pending["options"]
    assert len(opts) == 3 and set(opts) <= set(JULIETTE_WISHES)
    pick = sorted(opts)[0]
    choose(s, pick)
    assert s.pending["mode"] == "place"
    target = s.pending["placements"][0]
    rules.apply_action(s, PlaceAction(target["card_id"], tuple(target["target"])))
    while s.pending:   # the wished animal's own Roar may ask something: take the first offer
        p = s.pending
        rules.apply_action(s, ChoiceAction(p["options"][0]) if p["mode"] == "choice" else
                           PlaceAction(p["placements"][0]["card_id"], tuple(p["placements"][0]["target"])))
    assert any(st[-1].card_id == pick for st in s.board.values() if st) or pick in hand_ids(s, "A") or \
        pick in s.remove_pile


def test_juliettes_card_does_nothing_with_a_big_deck():
    s = state(hands={"A": ["bee_legend_2"]})
    s.starting_decks = {"A": ("t_big",) * 24 + ("bee_legend_2",), "B": ()}
    rules.apply_action(s, PlaceAction("bee_legend_2", ("cr", "1,1")))
    assert s.pending is None


# ===================================================================== Lord Bumbleton

def test_bumbleton_leader_adds_one_to_every_gain_and_his_card_counts_the_gains():
    from animal_kingdom.engine.effects import gain_food
    s = state("bumblebee_legend", hands={"A": ["bumblebee_legend"]})
    gain_food(s, "A", 5)
    gain_food(s, "A", 3)
    assert s.food["A"] == 10 and s.food_gains["A"] == 2      # the extra 1 is part of the same gain
    rules.apply_action(s, PlaceAction("bumblebee_legend", ("cr", "1,1")))
    assert s.food["A"] == 10 + 4 + 1 and s.food_gains["A"] == 3


def test_bumbletons_card_without_his_leader():
    from animal_kingdom.engine.effects import gain_food
    s = state(hands={"A": ["bumblebee_legend"]})
    gain_food(s, "A", 5)
    rules.apply_action(s, PlaceAction("bumblebee_legend", ("cr", "1,1")))
    assert s.food["A"] == 7


# ===================================================================== Queen Melissia

def test_melissia_scouts_only_worker_soldier_or_nurse_colony_animals():
    from animal_kingdom.engine.effects import _matches
    s = state("bee_legend", decks={"A": ["worker_ant", "soldier_ant", "t_body", "nurse_bee", "lion"], "B": []})
    press(s)
    assert set(s.pending["options"]) == {"worker_ant", "soldier_ant", "nurse_bee"}
    choose(s, "soldier_ant")
    assert hand_ids(s, "A") == ["soldier_ant"] and sorted(s.decks["A"]) == sorted(["worker_ant", "t_body", "nurse_bee", "lion"])
    assert not can_press(state("bee_legend", decks={"A": ["t_body", "lion"], "B": []}))
    assert not _matches(CARDS["queen_bee"], MELISSIA_SPEC)


# ===================================================================== Queen Solenia

def test_solenia_leader_gains_one_food_per_animal_at_dusk():
    s = state("army_ant_legend", decks={"A": ["t_body"] * 4, "B": ["t_body"] * 4})
    for cr in ("1,1", "1,2", "2,2"):
        put(s, cr, "t_small", "A")
    end_turn(s)
    assert s.food["A"] == 3


def test_solenias_card_gains_three_per_animal_and_the_opponent_loses_as_much():
    s = state(hands={"A": ["army_ant_legend"]}, food={"A": 0, "B": 4})
    put(s, "1,2", "t_small", "A")
    rules.apply_action(s, PlaceAction("army_ant_legend", ("cr", "1,1")))
    assert s.food == {"A": 6, "B": 0}


# ===================================================================== Babaji

def test_babaji_power_scouts_and_gives_the_card_plus_one():
    s = state("baboon_legend", decks={"A": ["t_small", "t_body", "lion"], "B": []})
    press(s)
    choose(s, "lion")
    (lion,) = s.hands["A"]
    assert lion.card_id == "lion" and lion.strength_counter == 1


def test_babaji_returns_an_ally_gives_it_two_and_plays_it_again_and_echo_repeats_it():
    s = state(hands={"A": ["baboon_legend"]}, decks={"A": ["t_body"] * 5, "B": ["t_body"] * 5})
    ally = put(s, "1,2", "t_small", "A")
    rules.apply_action(s, PlaceAction("baboon_legend", ("cr", "1,1")))
    assert s.pending["options"] == ["1,2"]
    choose(s, "1,2")
    assert s.pending["mode"] == "place" and not s.pending["optional"]
    pl = next(p for p in s.pending["placements"] if p["target"] == ["cr", "2,1"])
    rules.apply_action(s, PlaceAction(pl["card_id"], tuple(pl["target"]), pl.get("iid")))
    back = s.board["2,1"][-1]
    assert back.card_id == "t_small" and effective_strength(s, back) == 4 and "1,2" not in s.board
    assert s.actions_taken_this_turn == 1
    assert ActAction("1,1") in rules.legal_actions(s)          # Echo: one action, his Roar again
    rules.apply_action(s, ActAction("1,1"))
    choose(s, "2,1")
    pl = next(p for p in s.pending["placements"] if p["target"] == ["cr", "1,3"])
    rules.apply_action(s, PlaceAction(pl["card_id"], tuple(pl["target"]), pl.get("iid")))
    assert s.current == "B"
    assert effective_strength(s, s.board["1,3"][-1]) == 6


def test_echo_needs_an_ally_to_return():
    s = state()
    put(s, "1,1", "baboon_legend", "A")
    assert ActAction("1,1") not in rules.legal_actions(s)


# ===================================================================== Xanthe

def test_xanthe_evolves_at_each_dawn_and_her_power_is_once_per_game():
    s = state("butterfly_legend", decks={"A": ["t_body"] * 20, "B": ["t_body"] * 20})
    assert s.leaders["A"]["stage"] == 0 and not can_press(s)          # Egg: nothing
    end_turn(s); end_turn(s)
    assert s.leaders["A"]["stage"] == 1 and can_press(s)              # Caterpillar: draw a card
    end_turn(s); end_turn(s)
    assert s.leaders["A"]["stage"] == 2 and not can_press(s)          # Chrysalis: nothing
    end_turn(s); end_turn(s); end_turn(s); end_turn(s)
    assert s.leaders["A"]["stage"] == 4
    end_turn(s); end_turn(s)
    assert s.leaders["A"]["stage"] == 4                               # Monarch stays
    s.hands["A"] = s.hands["A"][:3]
    press(s)
    assert len(s.hands["A"]) == 4 and all(u.strength_counter == 1 for u in s.hands["A"])
    assert s.leaders["A"]["spent"] and not can_press(s)


def test_xanthe_butterfly_draws_then_buffs_one():
    s = state("butterfly_legend", decks={"A": ["t_body"] * 3, "B": []}, hands={"A": ["t_small"]})
    s.leaders["A"]["stage"] = 3
    press(s)
    assert len(s.pending["options"]) == 2
    choose(s, s.pending["options"][0])
    assert sorted(u.strength_counter for u in s.hands["A"]) == [0, 1]


def test_xanthes_card_evolves_only_when_it_gains_strength():
    s = state(hands={"A": ["butterfly_legend"]}, decks={"A": ["t_body"] * 3, "B": ["t_body"] * 3})
    end_turn(s); end_turn(s)
    assert hand_ids(s, "A")[0] == "butterfly_legend"                  # no Dawn evolution any more
    from animal_kingdom.engine.effects import _grant, resolve
    _grant(s, [s.hands["A"][0].iid], 1); resolve(s)
    assert hand_ids(s, "A")[0] == "butterfly_legend_caterpillar"


def test_monarch_draws_two_then_gives_two_animals_plus_two():
    s = state(hands={"A": ["butterfly_legend_monarch", "t_small", "t_small", "t_body"]}, decks={"A": ["t_body"] * 3, "B": []})
    rules.apply_action(s, PlaceAction("butterfly_legend_monarch", ("cr", "1,1")))
    assert len(s.pending["options"]) == 5
    choose(s, s.pending["options"][0])
    choose(s, s.pending["options"][0])
    assert sorted(u.strength_counter for u in s.hands["A"]) == [0, 0, 0, 2, 2]


def test_the_caterpillar_turns_on_the_board_too():
    s = state(decks={"A": ["t_body"] * 3, "B": []})
    u = put(s, "1,1", "caterpillar", "A")
    from animal_kingdom.engine.effects import _grant, resolve
    _grant(s, [u.iid], 1); resolve(s)
    assert u.card_id == "butterfly" and len(s.hands["A"]) == 1


# ===================================================================== Arne

def test_arne_copies_in_hand_share_the_strongest_copys_strength_and_keep_it_on_the_board():
    s = state("eagle_legend", hands={"A": ["t_body", "t_body", "t_small"]}, decks={"A": ["t_body"], "B": []})
    s.hands["A"][0].strength_counter = 3
    assert [placement_strength(s, u) for u in s.hands["A"]] == [7, 7, 2]
    rules.apply_action(s, DrawAction())
    assert [placement_strength(s, u) for u in s.hands["A"] if u.card_id == "t_body"] == [7, 7, 7]   # a drawn copy joins
    rules.apply_action(s, PlaceAction("t_body", ("cr", "1,1")))
    assert effective_strength(s, s.board["1,1"][-1]) == 7


def test_without_arne_copies_keep_their_own():
    s = state(hands={"A": ["t_body", "t_body"]})
    s.hands["A"][0].strength_counter = 3
    assert [placement_strength(s, u) for u in s.hands["A"]] == [7, 4]


# ===================================================================== [GORILLA]

def test_gorilla_leader_first_play_each_turn_has_plus_one():
    s = state("gorilla_legend_2", hands={"A": ["t_small", "t_small"], "B": ["t_small"]})
    assert placement_strength(s, s.hands["A"][0]) == 3
    rules.apply_action(s, PlaceAction("t_small", ("cr", "1,1")))
    assert effective_strength(s, s.board["1,1"][-1]) == 3
    assert placement_strength(s, s.hands["A"][0]) == 2
    rules.apply_action(s, PlaceAction("t_small", ("cr", "1,2")))
    assert effective_strength(s, s.board["1,2"][-1]) == 2


def test_gorilla_card_sets_the_next_play_to_his_strength_across_turns_and_lower_too():
    s = state(hands={"A": ["gorilla_legend_2", "t_big", "t_small"]}, decks={"A": [], "B": ["t_body"] * 3})
    rules.apply_action(s, PlaceAction("gorilla_legend_2", ("cr", "1,1")))
    assert s.next_strength == {"A": 7}
    rules.apply_action(s, DrawAction()) if DrawAction() in rules.legal_actions(s) else end_turn(s)
    if s.current == "A":
        end_turn(s)
    end_turn(s)                                                         # B's turn passes
    assert s.current == "A" and s.next_strength == {"A": 7}
    assert placement_strength(s, next(u for u in s.hands["A"] if u.card_id == "t_big")) == 7
    rules.apply_action(s, PlaceAction("t_big", ("cr", "1,2")))
    assert effective_strength(s, s.board["1,2"][-1]) == 7 and s.next_strength == {}
    rules.apply_action(s, PlaceAction("t_small", ("cr", "2,2")))
    assert effective_strength(s, s.board["2,2"][-1]) == 2


# ===================================================================== the web match

def test_a_web_match_shows_both_leaders_offers_the_den_and_logs_them_for_its_replay():
    import json, random
    from animal_kingdom.sim.replay import replay
    from animal_kingdom.web.match import Match, Seat
    from animal_kingdom.web.replay import game_views
    m = Match("T", Seat("ta", "A", deck="cats_lion_legend_4"))
    logs = []
    m.on_game_end = lambda match, rec: logs.append(json.loads(json.dumps(rec)))
    m.join(Seat("tb", "B", deck="handlock_butterfly_legend"))
    v = m.view("A")["game"]
    assert v["leaders"]["A"]["id"] == "lion_legend_4" and v["leaders"]["A"]["kind"] == "passive"
    assert v["leaders"]["B"]["stageName"] == "Egg" and v["leaders"]["B"]["kind"] == "once"
    rng, pressed = random.Random(3), 0
    while m.phase == "playing":
        s = m.to_act()
        legal = rules.legal_actions(m.state)
        a = LeaderAction() if LeaderAction() in legal and rng.random() < .5 else rng.choice(legal)
        if isinstance(a, LeaderAction):
            assert m.view(s)["game"]["legal"]["leader"]
            pressed += 1
        m.act(s, a.to_dict())
    assert pressed and logs[0]["leaders"] == {"A": "lion_legend_4", "B": "butterfly_legend"}
    _, result, _ = replay(logs[0])
    assert (result.winner, result.reason) == (logs[0]["winner"], logs[0]["reason"])
    assert any(h["kind"] == "leader" for h in m.view("A")["game"]["history"])
    views = game_views(logs[0], "A", {})                      # the match's replay, view by view, leaders and all
    assert views[-1]["game"]["leaders"]["B"]["id"] == "butterfly_legend"


def test_two_babajis_return_each_other_and_the_turn_cap_ends_the_loop():
    """The card prints no exception: a second Babaji (an Orangutan's copy) is an ally his Roar may return, and two replay
    each other until the turn's action cap (Config.max_actions_per_turn) ends the turn (Martin, 2026-11-18)."""
    from animal_kingdom.bots.greedy_bot import GreedyBot
    s = state(hands={"A": ["baboon_legend"]}, decks={"A": ["t_body"] * 5, "B": ["t_body"] * 5})
    put(s, "1,2", "baboon_legend", "A")
    rules.apply_action(s, PlaceAction("baboon_legend", ("cr", "1,1")))
    assert s.pending is not None and s.pending["options"] == ["1,2"]          # the other Babaji is returnable now
    bot = GreedyBot(seed=1)
    steps = 0
    while s.current == "A" and s.result is None:
        a = bot.choose(s.view_for("A"), rules.legal_actions(s), s)
        rules.apply_action(s, a)
        steps += 1
        assert steps <= s.config.max_actions_per_turn
    assert s.current == "B" and s.pending is None and not s.effect_stack
    assert [(c["cap"], c["cards"]) for c in s.caps] == [("actions", ["baboon_legend"])]
    assert any(e["e"] == "turn_capped" and e["cap"] == "actions" for e in s.events)


def test_the_turn_cap_ends_the_turn_mid_effect_and_resets():
    s = state(hands={"A": ["baboon_legend"]}, decks={"A": ["t_body"] * 5, "B": ["t_body"] * 5},
              config=dataclasses.replace(Config.default(), max_actions_per_turn=2))
    put(s, "1,2", "t_small", "A")
    rules.apply_action(s, PlaceAction("baboon_legend", ("cr", "1,1")))      # 1: the Roar asks which ally to return
    assert s.pending is not None and s.current == "A"
    choose(s, "1,2")                                                          # 2: the cap; the placement it asked for is dropped
    assert s.current == "B" and s.pending is None and not s.effect_stack and s.applied_this_turn == 0
