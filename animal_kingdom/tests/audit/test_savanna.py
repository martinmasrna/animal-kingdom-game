"""Card audit, Savanna (2026-11-05): does the engine do what each collectible Savanna card's printed text says?

Each test is named after a card id; its assertion comes from the printed text read with the keyword meanings of
docs/rules/keywords.md (and the binding conventions there), never from the effect code. Map A geometry: a 4x3 grid,
A's den fronts are column 1 ("1,1"/"1,2"/"1,3"), B's are column 4; "2,2" is adjacent to "1,2","3,2","2,1","2,3".
Regions: R1 = 1,1 2,1 1,2 2,2 (10 food); R2 = 2,1 3,1 2,2 3,2 (20); R3 = 3,1 4,1 3,2 4,2 (10).
"""

from __future__ import annotations

import pytest

from animal_kingdom.engine import effects, rules, statics
from animal_kingdom.engine.actions import ChoiceAction, PassAction, PlaceAction, RoamAction
from animal_kingdom.engine.cards import load_cards
from animal_kingdom.engine.strength import effective_strength

from .._helpers import apply_click, hand_ids, make_state, place_targets, put

CARDS = load_cards()
DECKS = {"A": ["mouse"] * 6, "B": ["mouse"] * 6}


def end_turn(s):
    s.idle_turns = 0
    rules.apply_action(s, PassAction())


def choose(s, option):
    assert s.pending is not None and option in s.pending["options"], (option, s.pending)
    rules.apply_action(s, ChoiceAction(option))


def removed(s, card_id):
    return card_id in s.remove_pile


def legal(s, card_id, cr):
    target = ("hq", cr[3:]) if cr.startswith("hq:") else ("cr", cr)
    return PlaceAction(card_id, target) in rules.legal_actions(s)


def str_of(card_id):
    return CARDS[card_id].base_strength


def tops(s, card_id, owner=None):
    return [c for c, st in s.board.items() if st and st[-1].card_id == card_id and (owner is None or st[-1].owner == owner)]


def deck(*ids):
    return {"A": list(ids), "B": ["mouse"] * 6}


# ===================================================================== Colony

def test_termite_king_draws_one_per_colony_queen_you_control():
    s = make_state(hands={"A": ["termite_king"]}, decks=deck(*["mouse"] * 6))
    put(s, "1,1", "termite_queen", "A")
    put(s, "1,3", "queen_bee", "A")
    put(s, "2,1", "queen_ant", "A")
    put(s, "2,1", "lion", "B")                                   # a buried queen: not controlled
    put(s, "3,2", "queen_ant", "B")                              # the opponent's queen: not yours
    put(s, "2,3", "worker_ant", "A")                             # Colony, not a Queen
    rules.apply_action(s, PlaceAction("termite_king", ("cr", "1,2")))
    assert len(s.hands["A"]) == 2


def test_termite_king_with_no_queen_draws_nothing():
    s = make_state(hands={"A": ["termite_king"]}, decks=deck(*["mouse"] * 6))
    put(s, "1,1", "worker_ant", "A")
    rules.apply_action(s, PlaceAction("termite_king", ("cr", "1,2")))
    assert s.hands["A"] == []


def test_termite_queen_plays_a_non_queen_colony_animal_from_hand():
    s = make_state(hands={"A": ["termite_queen", "worker_ant", "queen_bee", "lion"]}, decks=DECKS)
    rules.apply_action(s, PlaceAction("termite_queen", ("cr", "1,2")))
    assert s.pending is not None
    assert {a.card_id for a in rules.legal_actions(s) if isinstance(a, PlaceAction)} == {"worker_ant"}
    rules.apply_action(s, PlaceAction("worker_ant", ("cr", "1,1")))
    assert s.top_unit("1,1").card_id == "worker_ant"
    assert s.current == "A" and s.actions_taken_this_turn == 1     # the play cost no action


def test_termite_queen_with_no_colony_animal_in_hand_does_nothing():
    s = make_state(hands={"A": ["termite_queen", "queen_bee", "lion"]}, decks=deck("worker_ant"))
    rules.apply_action(s, PlaceAction("termite_queen", ("cr", "1,2")))
    assert s.pending is None and s.decks["A"] == ["worker_ant"]   # "play" is from the hand: the deck isn't searched


# ===================================================================== Vulture

def _three_removals(s, owners=("B", "A", "B")):
    for cr, who in zip(("2,1", "2,2", "2,3"), owners):
        put(s, cr, "mouse", who)
        effects.remove_top(s, cr, by_player="A")


def test_vulture_flies_in_from_hand_and_deck_at_dusk_after_three_removals():
    s = make_state(hands={"A": ["vulture"]}, decks={"A": ["vulture", "lion"], "B": ["mouse"] * 4})
    _three_removals(s)                                           # both players' animals count
    end_turn(s)                                                  # A's Dusk
    assert len(tops(s, "vulture", "A")) == 2
    assert "vulture" not in hand_ids(s, "A") and s.decks["A"] == ["lion"]


def test_vulture_stays_after_only_two_removals():
    s = make_state(hands={"A": ["vulture"]}, decks={"A": ["vulture", "lion"], "B": ["mouse"] * 4})
    for cr in ("2,1", "2,2"):
        put(s, cr, "mouse", "B")
        effects.remove_top(s, cr, by_player="A")
    end_turn(s)
    assert tops(s, "vulture") == [] and hand_ids(s, "A") == ["vulture"]


def test_vulture_does_not_fly_in_at_the_opponents_dusk():
    s = make_state(current="B", hands={"A": ["vulture"]}, decks={"A": ["lion"] * 3, "B": ["mouse"] * 4})
    _three_removals(s)
    end_turn(s)                                                  # B's Dusk, not A's
    assert tops(s, "vulture") == [] and hand_ids(s, "A") == ["vulture"]


def test_vulture_has_flight():
    s = make_state(hands={"A": ["vulture"]}, decks=DECKS)
    assert legal(s, "vulture", "3,3")                            # no connection needed
    for cr in ("1,2", "2,2", "3,2", "4,2"):
        put(s, cr, "lion", "A")
    s2 = make_state(hands={"A": ["vulture"]}, decks=DECKS)
    put(s2, "4,2", "lion", "A")                                  # stranded next to B's den
    assert not legal(s2, "vulture", "hq:B")                      # Flight never captures


# ===================================================================== Cats

def test_leopard_legend_eats_and_grows():
    s = make_state(hands={"A": ["leopard_legend"]}, decks=DECKS)
    put(s, "1,2", "lion", "A")
    put(s, "2,2", "fox", "B")                                    # a 3
    rules.apply_action(s, PlaceAction("leopard_legend", ("cr", "2,2")))
    leo = s.top_unit("2,2")
    assert leo.card_id == "leopard_legend" and removed(s, "fox")
    assert effective_strength(s, leo) == str_of("leopard_legend") + 1


def test_leopard_legend_is_an_apex_predator_needs_prey_and_not_the_den():
    s = make_state(hands={"A": ["leopard_legend"]}, decks=DECKS)
    assert not any(a.card_id == "leopard_legend" for a in rules.legal_actions(s) if isinstance(a, PlaceAction))
    for cr in ("1,2", "2,2", "3,2", "4,2"):
        put(s, cr, "mouse", "A")
    assert not legal(s, "leopard_legend", "hq:B")


def test_leopard_legend_reaches_two_crossroads():
    s = make_state(hands={"A": ["leopard_legend"]}, decks=DECKS)
    put(s, "1,2", "lion", "A")
    put(s, "3,2", "fox", "B")                                    # two away from 1,2, past the empty 2,2
    assert legal(s, "leopard_legend", "3,2")


def test_leopard_legend_roams_onto_an_animal_eats_it_and_grows():
    s = make_state(decks=DECKS)
    leo = put(s, "1,2", "leopard_legend", "A")
    put(s, "2,2", "fox", "B")
    assert RoamAction("1,2", ("cr", "1,1")) not in rules.legal_actions(s)   # a predator roams only onto an animal
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert s.top_unit("2,2") is leo and removed(s, "fox")
    assert effective_strength(s, leo) == str_of("leopard_legend") + 1


def test_cheetah_draws_two_next_to_the_opponents_den():
    s = make_state(hands={"A": ["cheetah"]}, decks=deck("lion", "fox", "mouse"))
    for cr in ("1,2", "2,2", "3,2"):
        put(s, cr, "mouse", "A")
    rules.apply_action(s, PlaceAction("cheetah", ("cr", "4,2")))
    assert len(s.hands["A"]) == 2


def test_cheetah_elsewhere_draws_nothing():
    s = make_state(hands={"A": ["cheetah"]}, decks=deck("lion", "fox", "mouse"))
    for cr in ("1,2", "2,2"):
        put(s, cr, "mouse", "A")
    rules.apply_action(s, PlaceAction("cheetah", ("cr", "3,2")))
    assert s.hands["A"] == []


def test_lion_legend_plays_princess_lea_from_hand_or_deck():
    for hand, dk in ((["lion_legend", "lion_legend_2"], ["lion"]), (["lion_legend"], ["lion_legend_2", "lion"])):
        s = make_state(hands={"A": hand}, decks=deck(*dk))
        rules.apply_action(s, PlaceAction("lion_legend", ("cr", "1,2")))
        assert s.pending is not None
        assert {a.card_id for a in rules.legal_actions(s) if isinstance(a, PlaceAction)} == {"lion_legend_2"}
        rules.apply_action(s, PlaceAction("lion_legend_2", ("cr", "1,1")))
        assert s.top_unit("1,1").card_id == "lion_legend_2" and "lion_legend_2" not in hand_ids(s, "A") + s.decks["A"]


def test_lion_legend_without_princess_lea_does_nothing():
    s = make_state(hands={"A": ["lion_legend", "lion"]}, decks=deck("lion"))
    rules.apply_action(s, PlaceAction("lion_legend", ("cr", "1,2")))
    assert s.pending is None and hand_ids(s, "A") == ["lion"]


def test_lion_legend_2_plays_prince_leo_from_hand_or_deck():
    for hand, dk in ((["lion_legend_2", "lion_legend"], ["lion"]), (["lion_legend_2"], ["lion_legend", "lion"])):
        s = make_state(hands={"A": hand}, decks=deck(*dk))
        rules.apply_action(s, PlaceAction("lion_legend_2", ("cr", "1,2")))
        assert s.pending is not None
        assert {a.card_id for a in rules.legal_actions(s) if isinstance(a, PlaceAction)} == {"lion_legend"}
        rules.apply_action(s, PlaceAction("lion_legend", ("cr", "1,1")))
        assert s.top_unit("1,1").card_id == "lion_legend" and "lion_legend" not in hand_ids(s, "A") + s.decks["A"]


def test_lion_legend_2_without_prince_leo_does_nothing():
    s = make_state(hands={"A": ["lion_legend_2", "lion"]}, decks=deck("lion"))
    rules.apply_action(s, PlaceAction("lion_legend_2", ("cr", "1,2")))
    assert s.pending is None and hand_ids(s, "A") == ["lion"]


def test_lion_legend_3_removes_the_enemy_an_allied_cat_covers():
    s = make_state(hands={"A": ["lion"]}, decks=DECKS)
    put(s, "1,1", "lion_legend_3", "A")
    put(s, "1,2", "fox", "B")
    rules.apply_action(s, PlaceAction("lion", ("cr", "1,2")))
    assert [u.card_id for u in s.board["1,2"]] == ["lion"] and removed(s, "fox")


def test_lion_legend_3_ignores_a_cover_by_an_animal_that_isnt_a_cat():
    s = make_state(hands={"A": ["tortoise"]}, decks=DECKS)
    put(s, "1,1", "lion_legend_3", "A")
    put(s, "1,2", "fox", "B")
    rules.apply_action(s, PlaceAction("tortoise", ("cr", "1,2")))
    assert [u.card_id for u in s.board["1,2"]] == ["fox", "tortoise"]


def test_lion_legend_3_ignores_an_enemy_cat_covering_your_animal():
    s = make_state(current="B", hands={"B": ["lion"]}, decks=DECKS)
    put(s, "1,1", "lion_legend_3", "A")
    put(s, "4,2", "fox", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "4,2")))
    assert [u.card_id for u in s.board["4,2"]] == ["fox", "lion"]


def test_lion_legend_4_draws_when_an_allied_cat_removes_an_enemy():
    s = make_state(hands={"A": ["jaguar"]}, decks=deck("lion", "mouse"))
    put(s, "1,1", "lion_legend_4", "A")
    put(s, "2,2", "fox", "B")                                    # a 3: the Jaguar removes 4 or less
    apply_click(s, PlaceAction("jaguar", ("cr", "1,2")))
    assert removed(s, "fox") and len(s.hands["A"]) == 1


def test_lion_legend_4_ignores_a_removal_by_an_animal_that_isnt_a_cat():
    s = make_state(hands={"A": ["black_mamba"]}, decks=deck("lion", "mouse"))
    put(s, "1,1", "lion_legend_4", "A")
    put(s, "2,2", "fox", "B")
    apply_click(s, PlaceAction("black_mamba", ("cr", "1,2")))
    assert removed(s, "fox") and s.hands["A"] == []


def test_lion_legend_4_draws_when_an_apex_cat_eats_an_enemy():
    s = make_state(hands={"A": ["tiger"]}, decks=deck("lion", "mouse"))
    put(s, "1,1", "lion_legend_4", "A")
    put(s, "1,2", "fox", "B")
    rules.apply_action(s, PlaceAction("tiger", ("cr", "1,2")))
    assert removed(s, "fox") and len(s.hands["A"]) == 1


def test_serval_removes_an_adjacent_enemy_after_another_cat_this_turn():
    s = make_state(hands={"A": ["lion", "serval"]}, decks=DECKS)
    put(s, "2,2", "elephant", "B")                               # a 9: no strength limit printed
    rules.apply_action(s, PlaceAction("lion", ("cr", "1,1")))
    apply_click(s, PlaceAction("serval", ("cr", "1,2")))
    assert s.top_unit("2,2") is None and removed(s, "elephant")


def test_serval_without_another_cat_this_turn_removes_nothing():
    s = make_state(hands={"A": ["mouse", "serval"]}, decks=DECKS)
    put(s, "1,3", "lion", "A")                                   # a Cat on the board, not played this turn
    put(s, "2,2", "elephant", "B")
    rules.apply_action(s, PlaceAction("mouse", ("cr", "1,1")))   # an animal played, not a Cat
    apply_click(s, PlaceAction("serval", ("cr", "1,2")))
    assert s.top_unit("2,2").card_id == "elephant"


def test_leopard_lets_your_cats_cover_equal_strength():
    s = make_state(hands={"A": ["lion", "tortoise"]}, decks=DECKS)
    put(s, "1,1", "leopard", "A")
    put(s, "1,2", "lion", "B")                                   # a 7
    put(s, "1,3", "caracal", "B")                                # a 6
    assert legal(s, "lion", "1,2")                               # a Cat at equal strength
    assert not legal(s, "tortoise", "1,3")                       # not a Cat: strictly greater still


def test_leopard_does_not_help_the_opponents_cats():
    s = make_state(current="B", hands={"B": ["lion"]}, decks=DECKS)
    put(s, "1,1", "leopard", "A")
    put(s, "4,2", "lion", "A")
    assert not legal(s, "lion", "4,2")


def test_lion_covers_a_six_not_a_seven():
    s = make_state(hands={"A": ["lion"]}, decks=DECKS)
    put(s, "1,1", "caracal", "B")
    put(s, "1,2", "lion", "B")
    assert str_of("lion") == 7 and CARDS["lion"].text == ""
    assert legal(s, "lion", "1,1") and not legal(s, "lion", "1,2")


def test_caracal_has_reach():
    s = make_state(hands={"A": ["caracal", "lion"]}, decks=DECKS)
    put(s, "1,2", "mouse", "A")
    assert legal(s, "caracal", "3,2")                            # two away, over the empty 2,2
    assert not legal(s, "lion", "3,2")
    assert not legal(s, "caracal", "4,2")                        # three away: too far


def test_caracal_reach_never_captures_the_den():
    s = make_state(hands={"A": ["caracal"]}, decks=DECKS)
    for cr in ("1,2", "2,2", "3,2"):
        put(s, cr, "mouse", "A")                                 # 4,2 empty: the den is two away
    assert not legal(s, "caracal", "hq:B")


# ===================================================================== Meerkat, the badgers, the armored

def test_meerkat_roar_draws_a_card():
    s = make_state(hands={"A": ["meerkat"]}, decks=deck("lion", "fox"))
    rules.apply_action(s, PlaceAction("meerkat", ("cr", "1,2")))
    assert len(s.hands["A"]) == 1


def test_meerkat_draws_when_an_enemy_is_placed_next_to_it():
    s = make_state(current="B", hands={"B": ["mouse"]}, decks=deck("lion", "fox"))
    put(s, "3,2", "meerkat", "A")
    rules.apply_action(s, PlaceAction("mouse", ("cr", "4,2")))
    assert len(s.hands["A"]) == 1


def test_meerkat_ignores_your_own_animals_and_enemies_placed_elsewhere():
    s = make_state(hands={"A": ["mouse"]}, decks=deck("lion", "fox"))
    put(s, "1,1", "meerkat", "A")
    rules.apply_action(s, PlaceAction("mouse", ("cr", "1,2")))   # your own, next to it
    assert hand_ids(s, "A") == []
    s2 = make_state(current="B", hands={"B": ["mouse"]}, decks=deck("lion", "fox"))
    put(s2, "1,1", "meerkat", "A")
    rules.apply_action(s2, PlaceAction("mouse", ("cr", "4,2")))  # an enemy, far away
    assert s2.hands["A"] == []


def test_honey_badger_legend_armor_and_stealth_keep_it_from_removal():
    s = make_state(current="B", hands={"B": ["black_mamba", "honey_badger"]}, decks=DECKS)
    put(s, "3,2", "honey_badger_legend", "A")                    # a 5: in the Mamba's reach
    rules.apply_action(s, PlaceAction("black_mamba", ("cr", "4,2")))
    assert s.pending is None or "3,2" not in s.pending.get("options", [])
    assert s.top_unit("3,2").card_id == "honey_badger_legend"


def test_honey_badger_legend_armor_resists_an_automatic_removal():
    s = make_state(hands={"A": ["rhinoceros"]}, decks=DECKS)    # mass removal sees Stealth; Armor still holds
    ash = put(s, "2,2", "honey_badger_legend", "B")
    ash.strength_counter = -2                                    # a 3: in the Rhinoceros' reach
    put(s, "1,1", "mouse", "A")
    rules.apply_action(s, PlaceAction("rhinoceros", ("cr", "2,1")))
    assert s.top_unit("2,2") is ash


def test_honey_badger_legend_spikes_then_poison():
    s = make_state(current="B", hands={"B": ["lion", "elephant"]}, decks=DECKS, food={"A": 0, "B": 20})
    put(s, "3,2", "honey_badger_legend", "A")
    put(s, "4,2", "mouse", "B")
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))   # first enemy cover: Spikes remove it
    assert s.top_unit("3,2").card_id == "honey_badger_legend" and removed(s, "lion")
    end_turn(s); end_turn(s)                                     # back to B
    rules.apply_action(s, PlaceAction("elephant", ("cr", "3,2")))   # Spikes spent: the cover holds...
    assert s.top_unit("3,2").card_id == "elephant"
    end_turn(s)                                                  # ...until the start of A's next turn: Poison
    assert s.top_unit("3,2").card_id == "honey_badger_legend" and removed(s, "elephant")


def test_tortoise_has_armor_but_can_be_covered():
    s = make_state(current="B", hands={"B": ["black_mamba", "lion"]}, decks=DECKS)
    put(s, "3,2", "tortoise", "A")                               # a 6: in the Mamba's reach
    put(s, "4,1", "mouse", "B")
    apply_click(s, PlaceAction("black_mamba", ("cr", "4,2")))
    assert s.top_unit("3,2").card_id == "tortoise"
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))
    assert [u.card_id for u in s.board["3,2"]] == ["tortoise", "lion"]


def test_black_mamba_removes_an_adjacent_enemy_of_6_or_less():
    s = make_state(hands={"A": ["black_mamba"]}, decks=DECKS)
    put(s, "1,1", "mouse", "A")
    put(s, "2,2", "caracal", "B")                                # a 6
    put(s, "1,3", "lion", "B")                                   # a 7
    apply_click(s, PlaceAction("black_mamba", ("cr", "1,2")))
    assert s.top_unit("2,2") is None and s.top_unit("1,3").card_id == "lion"


def test_black_mamba_spares_a_seven_and_your_own():
    s = make_state(hands={"A": ["black_mamba"]}, decks=DECKS)
    put(s, "1,1", "mouse", "A")
    put(s, "2,2", "lion", "B")
    apply_click(s, PlaceAction("black_mamba", ("cr", "1,2")))
    assert s.pending is None and s.top_unit("2,2").card_id == "lion" and s.top_unit("1,1").card_id == "mouse"


def test_egg_eater_has_two_strength_per_removed_egg():
    s = make_state(decks=DECKS)
    ee = put(s, "1,1", "egg_eater", "A")
    assert effective_strength(s, ee) == 0
    put(s, "2,2", "bird_egg", "B")
    put(s, "2,3", "snake_egg", "A")
    put(s, "3,2", "mouse", "B")
    for cr in ("2,2", "2,3", "3,2"):
        effects.remove_top(s, cr, by_player="A")
    assert effective_strength(s, ee) == 4                        # two Eggs, either player's; the Mouse isn't one


def test_baboon_legend_gives_two_random_hand_animals_plus_one_at_dawn():
    s = make_state(hands={"A": ["lion", "fox", "mouse"]}, decks=DECKS)
    put(s, "1,1", "baboon_legend", "A")
    end_turn(s)                                                  # B's Dawn: not this one's
    assert [u.strength_counter for u in s.hands["A"]] == [0, 0, 0]
    end_turn(s)                                                  # A's Dawn
    assert sorted(u.strength_counter for u in s.hands["A"]) == [0, 1, 1]


def test_baboon_legend_with_one_animal_in_hand_gives_it_plus_one():
    s = make_state(hands={"A": ["lion"]}, decks=DECKS)
    put(s, "1,1", "baboon_legend", "A")
    end_turn(s); end_turn(s)
    assert [u.strength_counter for u in s.hands["A"]] == [1]


def test_baboon_gives_two_hand_animals_plus_one():
    s = make_state(hands={"A": ["baboon", "lion", "fox", "mouse"]}, decks=DECKS)
    rules.apply_action(s, PlaceAction("baboon", ("cr", "1,2")))
    picks = 0
    while s.pending:
        opts = [o for o in s.pending["options"] if o != "skip"]
        rules.apply_action(s, ChoiceAction(opts[0]))
        picks += 1
        assert picks < 5
    assert sorted(u.strength_counter for u in s.hands["A"]) == [0, 1, 1]


def test_baboon_with_one_card_in_hand_and_with_none():
    s = make_state(hands={"A": ["baboon", "lion"]}, decks=DECKS)
    apply_click(s, PlaceAction("baboon", ("cr", "1,2")))
    assert [u.strength_counter for u in s.hands["A"]] == [1]
    s2 = make_state(hands={"A": ["baboon"]}, decks=DECKS)
    apply_click(s2, PlaceAction("baboon", ("cr", "1,2")))
    assert s2.pending is None and s2.hands["A"] == []


# ===================================================================== Giants (Hungry)

def _dawn(s):
    end_turn(s); end_turn(s)                                     # A's turn ends, B's turn ends: A's Dawn


def test_rhinoceros_legend_removes_an_adjacent_enemy_of_any_strength():
    s = make_state(hands={"A": ["rhinoceros_legend"]}, decks=DECKS)
    put(s, "2,2", "elephant", "B")                               # a 9
    apply_click(s, PlaceAction("rhinoceros_legend", ("cr", "1,2")))
    assert s.top_unit("2,2") is None and removed(s, "elephant")


def test_rhinoceros_legend_with_only_allies_adjacent_removes_nothing():
    s = make_state(hands={"A": ["rhinoceros_legend"]}, decks=DECKS)
    put(s, "1,1", "mouse", "A")
    apply_click(s, PlaceAction("rhinoceros_legend", ("cr", "1,2")))
    assert s.pending is None and s.top_unit("1,1").card_id == "mouse"


def test_rhinoceros_legend_is_hungry_4():
    s = make_state(food={"A": 5, "B": 0}, decks=DECKS)
    r = put(s, "1,2", "rhinoceros_legend", "A")
    _dawn(s)
    assert s.food["A"] == 1 and effective_strength(s, r) == 8
    _dawn(s)                                                     # 1 food: eats it, 3 short
    assert s.food["A"] == 0 and effective_strength(s, r) == 5


def test_tortoise_legend_dusk_gains_five_food():
    s = make_state(decks=DECKS)
    put(s, "1,3", "tortoise_legend", "A")
    end_turn(s)
    assert s.food["A"] == 5


def test_tortoise_legend_caps_each_players_food_at_20_a_turn():
    s = make_state(decks=DECKS)
    put(s, "1,3", "tortoise_legend", "A")
    for cr in ("2,1", "3,1", "2,2", "3,2"):
        put(s, cr, "mouse", "A")                                 # R2: 20 food, plus the Dusk's 5
    end_turn(s)
    assert s.food["A"] == 20
    s2 = make_state(current="B", decks=DECKS)
    put(s2, "1,3", "tortoise_legend", "A")
    for cr in ("2,1", "3,1", "2,2", "3,2", "4,1", "4,2"):
        put(s2, cr, "mouse", "B")                                # R2 + R3: 30 food for the opponent
    end_turn(s2)
    assert s2.food["B"] == 20


def test_tortoise_legend_has_armor():
    s = make_state(current="B", hands={"B": ["black_mamba"]}, decks=DECKS)
    put(s, "3,2", "tortoise_legend", "A")
    apply_click(s, PlaceAction("black_mamba", ("cr", "4,2")))
    assert s.top_unit("3,2").card_id == "tortoise_legend"


def _oxpecker_board(hand):
    s = make_state(hands={"A": hand}, decks=deck("mouse", "mouse", "mouse"))
    put(s, "3,3", "oxpecker_legend", "A")
    put(s, "1,2", "lion", "B")
    return s


def test_oxpecker_legend_plays_an_oxpecker_when_a_big_ally_covers_an_enemy():
    s = _oxpecker_board(["elephant"])
    rules.apply_action(s, PlaceAction("elephant", ("cr", "1,2")))   # a 9 covers an enemy
    assert s.pending is not None
    assert {a.card_id for a in rules.legal_actions(s) if isinstance(a, PlaceAction)} == {"oxpecker"}


def test_oxpecker_legend_ignores_a_cover_under_8_and_an_own_cover():
    s = _oxpecker_board(["lion", "oxpecker"])
    put(s, "1,2", "fox", "B")                                    # a 3 on top of the Lion
    rules.apply_action(s, PlaceAction("lion", ("cr", "1,2")))   # a 7 covers: nothing
    assert s.pending is None
    s2 = _oxpecker_board(["elephant", "oxpecker"])
    put(s2, "1,1", "mouse", "A")
    rules.apply_action(s2, PlaceAction("elephant", ("cr", "1,1")))  # a 9 covers an ally: nothing
    assert s2.pending is None


# Martin, 2026-11-05: "play an Oxpecker" makes a new one ("new one of course"), as the Rabbit's Bunny; an Oxpecker in
# hand stays there, and none in hand is needed.
def test_oxpecker_legend_plays_a_new_oxpecker_and_leaves_the_one_in_hand():
    s = _oxpecker_board(["elephant", "oxpecker"])
    rules.apply_action(s, PlaceAction("elephant", ("cr", "1,2")))
    rules.apply_action(s, PlaceAction("oxpecker", ("cr", "4,3")))
    assert s.top_unit("4,3").card_id == "oxpecker"
    assert "oxpecker" in hand_ids(s, "A")                        # the one in hand stays
    s2 = _oxpecker_board(["elephant"])
    rules.apply_action(s2, PlaceAction("elephant", ("cr", "1,2")))
    assert s2.pending is not None                                # no Oxpecker in hand: a new one all the same


def test_rhinoceros_removes_all_adjacent_enemies_of_3_or_less():
    s = make_state(hands={"A": ["rhinoceros"]}, decks=DECKS)
    put(s, "1,2", "mouse", "A")
    put(s, "2,1", "fox", "B")                                    # a 3
    put(s, "2,3", "gazelle", "B")                                # a 2 (Flee: a removal isn't a cover)
    put(s, "3,2", "mouse", "B")                                  # a 4
    put(s, "1,2", "baby_impala", "A")                            # your own 1, next to it
    rules.apply_action(s, PlaceAction("rhinoceros", ("cr", "2,2")))
    assert s.top_unit("2,1") is None and s.top_unit("2,3") is None
    assert s.top_unit("3,2").card_id == "mouse" and s.top_unit("1,2").card_id == "baby_impala"


def test_rhinoceros_is_hungry_3():
    s = make_state(food={"A": 2, "B": 0}, decks=DECKS)
    r = put(s, "1,2", "rhinoceros", "A")
    _dawn(s)
    assert s.food["A"] == 0 and effective_strength(s, r) == 7


def test_hippopotamus_removes_an_enemy_of_4_or_less_placed_next_to_it():
    s = make_state(current="B", hands={"B": ["mouse"]}, decks=DECKS)
    put(s, "3,2", "hippopotamus", "A")
    rules.apply_action(s, PlaceAction("mouse", ("cr", "4,2")))
    assert s.top_unit("4,2") is None and removed(s, "mouse")


def test_hippopotamus_spares_a_five_an_ally_and_a_far_enemy():
    s = make_state(current="B", hands={"B": ["zebra", "mouse"]}, decks=DECKS)
    put(s, "3,2", "hippopotamus", "A")
    rules.apply_action(s, PlaceAction("zebra", ("cr", "4,2")))  # a 5
    assert s.top_unit("4,2").card_id == "zebra"
    rules.apply_action(s, PlaceAction("mouse", ("cr", "4,3")))  # not next to it
    assert s.top_unit("4,3").card_id == "mouse"
    s2 = make_state(hands={"A": ["mouse"]}, decks=DECKS)
    put(s2, "2,2", "hippopotamus", "A")
    rules.apply_action(s2, PlaceAction("mouse", ("cr", "1,2")))
    assert s2.top_unit("1,2").card_id == "mouse"


def test_hippopotamus_is_hungry_3():
    s = make_state(food={"A": 3, "B": 0}, decks=DECKS)
    h = put(s, "1,2", "hippopotamus", "A")
    _dawn(s)
    assert s.food["A"] == 0 and effective_strength(s, h) == 8


def test_oxpecker_draws_then_gains_the_strongest_in_hand():
    s = make_state(hands={"A": ["oxpecker", "lion"]}, decks=deck("elephant"))
    rules.apply_action(s, PlaceAction("oxpecker", ("cr", "3,3")))   # Flight
    assert sorted(hand_ids(s, "A")) == ["elephant", "lion"] and s.food["A"] == 9   # the drawn 9 counts


def test_oxpecker_with_an_empty_deck_and_an_empty_hand():
    s = make_state(hands={"A": ["oxpecker", "lion"]}, decks={"A": [], "B": ["mouse"] * 3})
    rules.apply_action(s, PlaceAction("oxpecker", ("cr", "1,2")))
    assert s.food["A"] == 7
    s2 = make_state(hands={"A": ["oxpecker"]}, decks={"A": [], "B": ["mouse"] * 3})
    rules.apply_action(s2, PlaceAction("oxpecker", ("cr", "1,2")))
    assert s2.food["A"] == 0


def test_oxpecker_has_flight():
    s = make_state(hands={"A": ["oxpecker"]}, decks=DECKS)
    assert legal(s, "oxpecker", "3,3")


def test_dung_beetle_gains_four_per_hungry_animal_you_control_at_dusk():
    s = make_state(decks=DECKS)
    put(s, "1,1", "dung_beetle", "A")
    put(s, "1,3", "elephant", "A")
    put(s, "2,3", "giraffe", "A")
    put(s, "3,2", "elephant", "B")                               # the opponent's: not yours
    put(s, "2,1", "elephant", "A")
    put(s, "2,1", "lion", "B")                                   # buried: not controlled
    end_turn(s)
    assert s.food["A"] == 8


def test_dung_beetle_without_hungry_animals_gains_nothing():
    s = make_state(decks=DECKS)
    put(s, "1,1", "dung_beetle", "A")
    end_turn(s)
    assert s.food["A"] == 0


def test_elephant_is_a_nine_hungry_5():
    s = make_state(food={"A": 6, "B": 0}, decks=DECKS)
    e = put(s, "1,2", "elephant", "A")
    assert effective_strength(s, e) == 9
    _dawn(s)
    assert s.food["A"] == 1 and effective_strength(s, e) == 9
    _dawn(s)
    assert s.food["A"] == 0 and effective_strength(s, e) == 5


def test_elephant_legend_removes_adjacent_enemies_of_3_or_less_when_placed():
    s = make_state(hands={"A": ["elephant_legend"]}, decks=DECKS)
    put(s, "1,2", "mouse", "A")
    put(s, "2,1", "fox", "B")                                    # a 3
    put(s, "3,2", "mouse", "B")                                  # a 4
    put(s, "2,3", "baby_impala", "A")                            # your own 1
    rules.apply_action(s, PlaceAction("elephant_legend", ("cr", "2,2")))
    assert s.top_unit("2,1") is None and s.top_unit("3,2").card_id == "mouse"
    assert s.top_unit("2,3").card_id == "baby_impala"


def test_elephant_legend_removes_them_when_it_roams_too():
    s = make_state(decks=DECKS)
    e = put(s, "1,2", "elephant_legend", "A")
    put(s, "3,2", "fox", "B")
    put(s, "2,3", "mouse", "B")
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert s.top_unit("2,2") is e and s.top_unit("3,2") is None and s.top_unit("2,3").card_id == "mouse"


def test_elephant_legend_is_hungry_6():
    s = make_state(food={"A": 4, "B": 0}, decks=DECKS)
    e = put(s, "1,2", "elephant_legend", "A")
    _dawn(s)
    assert s.food["A"] == 0 and effective_strength(s, e) == 7


def test_dung_beetle_legend_evolves_at_10_food_eaten():
    s = make_state(hands={"A": ["dung_beetle_legend"]}, food={"A": 9, "B": 0}, decks=DECKS)
    put(s, "1,2", "elephant", "A")
    _dawn(s)                                                     # 5 eaten
    assert hand_ids(s, "A") == ["dung_beetle_legend"]
    _dawn(s)                                                     # 4 more: 9
    assert hand_ids(s, "A") == ["dung_beetle_legend"]
    s.food["A"] = 1
    _dawn(s)                                                     # 10
    assert hand_ids(s, "A") == ["dung_beetle_legend_form2"]


def test_dung_beetle_legend_ignores_the_opponents_hungry_animals():
    s = make_state(hands={"A": ["dung_beetle_legend"]}, food={"A": 0, "B": 20}, decks=DECKS)
    put(s, "4,2", "elephant", "B")
    end_turn(s); end_turn(s); end_turn(s)                        # B's Dawn, twice: 10 eaten by the opponent's
    assert hand_ids(s, "A") == ["dung_beetle_legend"]


# ===================================================================== Hoofed

def test_wildebeest_legend_makes_your_regions_produce_five_more():
    def income(card):
        s = make_state(decks=DECKS)
        for cr in ("1,1", "2,1", "1,2"):
            put(s, cr, "mouse", "A")
        put(s, "2,2", card, "A")
        put(s, "4,1", "mouse", "B"); put(s, "4,2", "mouse", "B"); put(s, "3,1", "mouse", "B"); put(s, "3,2", "mouse", "B")
        end_turn(s)
        a = s.food["A"]
        end_turn(s)
        return a, s.food["B"]
    assert income("wildebeest_legend") == (15, 10)               # only your regions
    assert income("mouse") == (10, 10)


def test_zebra_legend_draws_per_grazing_hoofed_animal_itself_included():
    s = make_state(hands={"A": ["zebra_legend"]}, decks=deck(*["mouse"] * 6))
    put(s, "1,1", "zebra", "A")
    put(s, "2,1", "wildebeest", "A")
    put(s, "2,2", "mouse", "A")
    put(s, "1,3", "gazelle", "A")                                # Hoofed, not grazing
    rules.apply_action(s, PlaceAction("zebra_legend", ("cr", "1,2")))   # closes R1
    assert len(s.hands["A"]) == 3


def test_zebra_legend_with_no_grazing_hoofed_draws_nothing():
    s = make_state(hands={"A": ["zebra_legend"]}, decks=deck(*["mouse"] * 6))
    put(s, "1,1", "zebra", "A")
    rules.apply_action(s, PlaceAction("zebra_legend", ("cr", "1,2")))
    assert s.hands["A"] == []


def test_giraffe_legend_reveals_the_opponents_hand():
    s = make_state(hands={"A": [], "B": ["lion"]}, decks=DECKS)
    assert not statics.hand_revealed(s, "B")
    g = put(s, "1,2", "giraffe_legend", "A")
    assert statics.hand_revealed(s, "B") and not statics.hand_revealed(s, "A")
    s.board["1,2"].remove(g)
    assert not statics.hand_revealed(s, "B")


def test_honey_badger_removes_an_adjacent_enemy_of_6_or_more():
    s = make_state(hands={"A": ["honey_badger"]}, decks=DECKS)
    put(s, "1,1", "mouse", "A")
    put(s, "2,2", "caracal", "B")                                # a 6
    put(s, "1,3", "zebra", "B")                                  # a 5
    apply_click(s, PlaceAction("honey_badger", ("cr", "1,2")))
    assert s.top_unit("2,2") is None and s.top_unit("1,3").card_id == "zebra"


def test_honey_badger_spares_a_five():
    s = make_state(hands={"A": ["honey_badger"]}, decks=DECKS)
    put(s, "2,2", "zebra", "B")
    apply_click(s, PlaceAction("honey_badger", ("cr", "1,2")))
    assert s.pending is None and s.top_unit("2,2").card_id == "zebra"


def test_zebra_flees_and_returns_its_coverer():
    s = make_state(current="B", hands={"B": ["lion"]}, decks=DECKS)
    put(s, "4,2", "mouse", "B")
    put(s, "3,2", "zebra", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))
    assert "zebra" in hand_ids(s, "A") and "lion" in hand_ids(s, "B") and s.top_unit("3,2") is None
    assert not removed(s, "zebra") and not removed(s, "lion")


def test_zebra_covered_by_its_own_player_does_not_flee():
    s = make_state(hands={"A": ["lion"]}, decks=DECKS)
    put(s, "1,2", "zebra", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "1,2")))
    assert [u.card_id for u in s.board["1,2"]] == ["zebra", "lion"]


def test_zebra_cannot_return_an_armored_coverer():
    s = make_state(current="B", hands={"B": ["tortoise"]}, decks=DECKS)
    put(s, "4,2", "mouse", "B")
    put(s, "3,2", "zebra", "A")
    rules.apply_action(s, PlaceAction("tortoise", ("cr", "3,2")))
    assert "zebra" in hand_ids(s, "A") and s.top_unit("3,2").card_id == "tortoise"


def test_giraffe_has_plus_3_during_the_opponents_turn():
    s = make_state(decks=DECKS)
    g = put(s, "1,2", "giraffe", "A")
    assert effective_strength(s, g) == 6
    end_turn(s)
    assert effective_strength(s, g) == 9


def test_giraffe_is_hungry_2():
    s = make_state(food={"A": 1, "B": 0}, decks=DECKS)
    g = put(s, "1,2", "giraffe", "A")
    _dawn(s)
    assert s.food["A"] == 0 and effective_strength(s, g) == 5


def test_cape_buffalo_gives_your_other_hoofed_plus_1_during_the_opponents_turn():
    s = make_state(decks=DECKS)
    cb = put(s, "1,1", "cape_buffalo", "A")
    z = put(s, "2,3", "zebra", "A")                              # anywhere on the board
    ez = put(s, "4,2", "zebra", "B")
    lion = put(s, "1,3", "lion", "A")
    assert (effective_strength(s, z), effective_strength(s, cb)) == (5, 7)
    end_turn(s)
    assert effective_strength(s, z) == 6
    assert effective_strength(s, cb) == 7                        # "other"
    assert effective_strength(s, ez) == 5 and effective_strength(s, lion) == 7


def test_gazelle_draws_a_card_and_gains_5_food():
    s = make_state(hands={"A": ["gazelle"]}, decks=deck("lion"))
    rules.apply_action(s, PlaceAction("gazelle", ("cr", "1,2")))
    assert hand_ids(s, "A") == ["lion"] and s.food["A"] == 5


def test_gazelle_flees_when_an_enemy_covers_it():
    s = make_state(current="B", hands={"B": ["mouse"]}, decks=DECKS)
    put(s, "4,2", "mouse", "B")
    put(s, "3,2", "gazelle", "A")
    rules.apply_action(s, PlaceAction("mouse", ("cr", "3,2")))
    assert "gazelle" in hand_ids(s, "A") and [u.card_id for u in s.board["3,2"]] == ["mouse"]


def test_wildebeest_gains_6_at_dusk_while_grazing():
    def food(card):
        s = make_state(decks=DECKS)
        for cr in ("1,1", "2,1", "1,2"):
            put(s, cr, "mouse", "A")
        put(s, "2,2", card, "A")
        end_turn(s)
        return s.food["A"]
    assert food("wildebeest") - food("mouse") == 6


def test_wildebeest_not_grazing_gains_nothing():
    s = make_state(decks=DECKS)
    put(s, "1,2", "wildebeest", "A")
    end_turn(s)
    assert s.food["A"] == 0


def test_warthog_removes_an_adjacent_enemy_flanked_by_another_hoofed():
    s = make_state(hands={"A": ["warthog"]}, decks=DECKS)
    put(s, "1,2", "mouse", "A")
    put(s, "3,2", "elephant", "B")                               # no strength limit printed
    put(s, "3,1", "zebra", "A")                                  # another Hoofed of yours next to the enemy
    apply_click(s, PlaceAction("warthog", ("cr", "2,2")))
    assert s.top_unit("3,2") is None


def test_warthog_alone_does_not_count_itself():
    s = make_state(hands={"A": ["warthog"]}, decks=DECKS)
    put(s, "1,2", "mouse", "A")
    put(s, "3,2", "elephant", "B")
    put(s, "3,1", "lion", "A")                                   # an ally next to it, not Hoofed
    apply_click(s, PlaceAction("warthog", ("cr", "2,2")))
    assert s.pending is None and s.top_unit("3,2").card_id == "elephant"


def test_hyena_gains_3_per_animal_removed_this_turn():
    s = make_state(decks=DECKS)
    put(s, "1,3", "hyena", "A")
    _three_removals(s)                                           # both players'
    end_turn(s)
    assert s.food["A"] == 9


def test_hyena_with_no_removals_gains_nothing():
    s = make_state(decks=DECKS)
    put(s, "1,3", "hyena", "A")
    end_turn(s)
    assert s.food["A"] == 0


def test_crocodile_has_minus_3_during_the_opponents_turn():
    s = make_state(decks=DECKS)
    c = put(s, "1,2", "crocodile", "A")
    assert effective_strength(s, c) == 8
    end_turn(s)
    assert effective_strength(s, c) == 5


def test_crocodile_is_an_apex_predator():
    s = make_state(hands={"A": ["crocodile"]}, decks=DECKS)
    put(s, "1,2", "lion", "B")
    assert not legal(s, "crocodile", "1,1")                      # never on an empty crossroad
    rules.apply_action(s, PlaceAction("crocodile", ("cr", "1,2")))
    assert [u.card_id for u in s.board["1,2"]] == ["crocodile"] and removed(s, "lion")


def test_impala_plays_a_baby_impala():
    s = make_state(hands={"A": ["impala"]}, decks=DECKS)
    rules.apply_action(s, PlaceAction("impala", ("cr", "1,2")))
    assert s.pending is not None
    rules.apply_action(s, PlaceAction("baby_impala", ("cr", "1,3")))
    assert s.top_unit("1,3").card_id == "baby_impala" and s.actions_taken_this_turn == 1


def test_impala_flees():
    s = make_state(current="B", hands={"B": ["mouse"]}, decks=DECKS)
    put(s, "4,2", "mouse", "B")
    put(s, "3,2", "impala", "A")
    rules.apply_action(s, PlaceAction("mouse", ("cr", "3,2")))
    assert "impala" in hand_ids(s, "A")


def test_jackal_removes_an_adjacent_weaker_enemy_when_it_roams():
    s = make_state(decks=DECKS)
    put(s, "1,1", "jackal", "A")
    put(s, "2,2", "gazelle", "B")                                # a 2
    put(s, "1,3", "fox", "B")                                    # a 3: not weaker
    rules.apply_action(s, RoamAction("1,1", ("cr", "1,2")))
    assert s.pending is not None and s.pending["options"] == ["2,2"]
    choose(s, "2,2")
    assert s.top_unit("2,2") is None and s.top_unit("1,3").card_id == "fox"


def test_jackal_placed_removes_nothing():
    s = make_state(hands={"A": ["jackal"]}, decks=DECKS)
    put(s, "2,2", "gazelle", "B")
    rules.apply_action(s, PlaceAction("jackal", ("cr", "1,2")))
    assert s.pending is None and s.top_unit("2,2").card_id == "gazelle"


def test_african_wild_dog_makes_a_canine_you_play_next_to_it_roam():
    s = make_state(hands={"A": ["fox"]}, decks=DECKS)
    put(s, "1,1", "african_wild_dog", "A")
    rules.apply_action(s, PlaceAction("fox", ("cr", "1,2")))
    fox = s.top_unit("1,2")
    choose(s, "2,2")
    assert s.top_unit("2,2") is fox


def test_african_wild_dog_ignores_a_non_canine_and_the_opponents_canine():
    s = make_state(hands={"A": ["lion"]}, decks=DECKS)
    put(s, "1,1", "african_wild_dog", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "1,2")))
    assert s.pending is None
    s2 = make_state(current="B", hands={"B": ["fox"]}, decks=DECKS)
    put(s2, "3,2", "african_wild_dog", "A")
    rules.apply_action(s2, PlaceAction("fox", ("cr", "4,2")))
    assert s2.pending is None and s2.top_unit("4,2").card_id == "fox"


# ===================================================================== roaming sets off what a placement does

def test_hippopotamus_removes_a_small_enemy_that_roams_next_to_it():
    s = make_state(current="B", decks=DECKS)
    put(s, "3,1", "hippopotamus", "A")
    put(s, "4,2", "jackal", "B")                                 # a 3
    rules.apply_action(s, RoamAction("4,2", ("cr", "3,2")))
    assert removed(s, "jackal") and s.top_unit("3,2") is None


def test_meerkat_draws_when_an_enemy_roams_next_to_it():
    s = make_state(current="B", decks=deck("lion", "fox"))
    put(s, "3,1", "meerkat", "A")
    put(s, "4,2", "jackal", "B")
    rules.apply_action(s, RoamAction("4,2", ("cr", "3,2")))
    assert len(s.hands["A"]) == 1


def test_zebra_flees_from_a_roaming_coverer_and_returns_it():
    s = make_state(current="B", decks=DECKS)
    put(s, "3,2", "zebra", "A")
    put(s, "4,2", "wolf", "B")                                   # a 6 roams onto the 5
    rules.apply_action(s, RoamAction("4,2", ("cr", "3,2")))
    assert "zebra" in hand_ids(s, "A") and "wolf" in hand_ids(s, "B") and s.top_unit("3,2") is None


def test_oxpecker_legend_sees_a_cover_by_roaming():
    s = make_state(decks=DECKS)
    put(s, "3,3", "oxpecker_legend", "A")
    put(s, "1,2", "elephant_legend", "A")
    put(s, "2,2", "lion", "B")
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert s.pending is not None
    assert "oxpecker" in {a.card_id for a in rules.legal_actions(s) if isinstance(a, PlaceAction)}


def test_warthog_does_not_count_the_opponents_hoofed():
    s = make_state(hands={"A": ["warthog"]}, decks=DECKS)
    put(s, "1,2", "mouse", "A")
    put(s, "3,2", "elephant", "B")
    put(s, "3,1", "zebra", "B")                                  # Hoofed, but not yours
    apply_click(s, PlaceAction("warthog", ("cr", "2,2")))
    assert s.pending is None and s.top_unit("3,2").card_id == "elephant"


def test_lion_legend_4_draws_when_king_theron_an_allied_cat_removes_an_enemy():
    s = make_state(hands={"A": ["lion"]}, decks=deck("lion", "mouse"))
    put(s, "1,1", "lion_legend_4", "A")
    put(s, "1,3", "lion_legend_3", "A")
    put(s, "1,2", "fox", "B")
    rules.apply_action(s, PlaceAction("lion", ("cr", "1,2")))   # Theron, a Cat of yours, removes the covered Fox
    assert removed(s, "fox") and len(s.hands["A"]) == 1


def test_lion_legend_4_ignores_an_armored_enemy_that_stays():
    s = make_state(hands={"A": ["tiger"]}, decks=deck("lion", "mouse"))
    put(s, "1,1", "lion_legend_4", "A")
    put(s, "1,2", "tortoise", "B")                               # Armor: covered, not eaten
    rules.apply_action(s, PlaceAction("tiger", ("cr", "1,2")))
    assert not removed(s, "tortoise") and s.hands["A"] == []
