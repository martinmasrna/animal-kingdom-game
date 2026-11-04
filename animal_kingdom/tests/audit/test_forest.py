"""Card audit, Forest: does the engine do what each collectible Forest card's printed text says?

One test (or more) per card, named after its id, written from the printed text and keywords.md, not from the effect
code. Map A: a 4x3 grid, A's den fronts column 1 ("1,1" "1,2" "1,3"), B's column 4; orthogonal neighbours, so "2,2"
neighbours "1,2", "3,2", "2,1", "2,3". Regions: R1 = 1,1 2,1 1,2 2,2; R3 = 3,1 4,1 3,2 4,2 (10 food each).

The vanilla bodies v1..v9 (strength = the number, no text, no tags) and the Roam body v_roam are test-only cards.
"""

from __future__ import annotations

import pytest

from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import ChoiceAction, DrawAction, PassAction, PlaceAction, RoamAction
from animal_kingdom.engine.state import GameState

from .._helpers import cards_with, hand_ids, make_state, place_targets, put

CARDS = cards_with(*[{"id": f"v{n}", "base_strength": n} for n in range(1, 10)],
                   {"id": "v_roam", "base_strength": 4, "keywords": ["Roam"]})


def st(**kw) -> GameState:
    kw.setdefault("decks", {"A": ["v1"] * 6, "B": ["v1"] * 6})
    return make_state(cards=CARDS, **kw)


def strength(s, u):
    from animal_kingdom.engine.strength import effective_strength
    return effective_strength(s, u)


def end_turn(s):
    """End the turn of whoever is to move (a pass; the idle count is reset so two passes don't end the game)."""
    s.idle_turns = 0
    rules.apply_action(s, PassAction())


def choose(s, option):
    assert s.pending is not None and option in s.pending["options"], (option, s.pending)
    rules.apply_action(s, ChoiceAction(option))


def click_through(s):
    """Answer every pending choice with its first option (for choices the test doesn't care about)."""
    while s.pending and s.pending.get("options"):
        rules.apply_action(s, ChoiceAction(s.pending["options"][0]))


def play(s, card_id, cr):
    rules.apply_action(s, PlaceAction(card_id, ("cr", cr)))


def legal(s, action):
    return action in rules.legal_actions(s)


def on_board(s, card_id, owner=None):
    return [(cr, u) for cr, stack in s.board.items() for u in stack
            if u.card_id == card_id and (owner is None or u.owner == owner)]


# ============================================================ hornet_legend (Vesper)
# "Flight. When an enemy covers a Colony ally, place Vesper on top of it from your hand or deck."

def test_hornet_legend_answers_a_cover_of_a_colony_ally_from_hand():
    s = st(current="B", hands={"A": ["hornet_legend"], "B": ["v7"]})
    put(s, "3,2", "worker_ant", "A")
    put(s, "4,2", "v1", "B")
    play(s, "v7", "3,2")
    top = s.top_unit("3,2")
    assert top.card_id == "hornet_legend" and top.owner == "A"
    assert [u.card_id for u in s.board["3,2"]] == ["worker_ant", "v7", "hornet_legend"]
    assert "hornet_legend" not in hand_ids(s, "A")


def test_hornet_legend_answers_from_the_deck():
    s = st(current="B", hands={"B": ["v7"]}, decks={"A": ["v1", "hornet_legend", "v1"], "B": ["v1"] * 3})
    put(s, "3,2", "worker_ant", "A")
    put(s, "4,2", "v1", "B")
    play(s, "v7", "3,2")
    assert s.top_unit("3,2").card_id == "hornet_legend"
    assert "hornet_legend" not in s.decks["A"]


def test_hornet_legend_ignores_a_cover_of_a_non_colony_ally():
    s = st(current="B", hands={"A": ["hornet_legend"], "B": ["v7"]})
    put(s, "3,2", "v2", "A")
    put(s, "4,2", "v1", "B")
    play(s, "v7", "3,2")
    assert s.top_unit("3,2").card_id == "v7"
    assert "hornet_legend" in hand_ids(s, "A")


def test_hornet_legend_ignores_its_owners_own_cover():
    s = st(hands={"A": ["v5"]}, decks={"A": ["hornet_legend"] + ["v1"] * 3, "B": ["v1"] * 3})
    put(s, "1,2", "worker_ant", "A")
    play(s, "v5", "1,2")
    assert s.top_unit("1,2").card_id == "v5" and "hornet_legend" in s.decks["A"]


def test_hornet_legend_has_flight():
    s = st(hands={"A": ["hornet_legend"]})
    assert "3,3" in place_targets(s)


# ============================================================ guard_wasp (Soldier Wasp)
# "Flight. Has +4 strength while you control 4 or more Colony animals."

def test_guard_wasp_has_plus_4_only_with_4_colony_animals():
    s = st()
    w = put(s, "1,1", "guard_wasp", "A")
    put(s, "1,2", "worker_ant", "A")
    put(s, "1,3", "worker_ant", "A")
    put(s, "3,3", "worker_ant", "B")                                     # an enemy Colony animal doesn't count
    assert strength(s, w) == 3                                            # 3 Colony, itself included
    put(s, "2,1", "worker_ant", "A")
    assert strength(s, w) == 7                                            # 4: +4
    s.board["2,1"].pop()
    assert strength(s, w) == 3                                            # live: gone again


def test_guard_wasp_has_flight():
    s = st(hands={"A": ["guard_wasp"]})
    assert "3,3" in place_targets(s)


# ============================================================ worker_ant
# "Roar: gain 3 food for each animal you control."

def test_worker_ant_gains_3_food_for_each_animal_you_control_itself_included():
    s = st(hands={"A": ["worker_ant"]})
    put(s, "1,1", "v1", "A")
    put(s, "1,3", "v1", "A")
    put(s, "3,3", "v1", "B")                                              # not yours
    play(s, "worker_ant", "1,2")
    assert s.food["A"] == 9                                               # three animals: the ant and two


def test_worker_ant_alone_gains_3():
    s = st(hands={"A": ["worker_ant"]})
    play(s, "worker_ant", "1,2")
    assert s.food["A"] == 3


# ============================================================ worker_wasp
# "Flight. Whenever you place a Colony animal, gain 3 food."

def test_worker_wasp_gains_3_when_you_place_a_colony_animal():
    s = st(hands={"A": ["guard_wasp", "v1"]})
    put(s, "3,3", "worker_wasp", "A")
    play(s, "guard_wasp", "1,1")
    assert s.food["A"] == 3
    play(s, "v1", "1,2")                                                   # not Colony
    assert s.food["A"] == 3


def test_worker_wasp_ignores_the_opponents_colony_animal():
    s = st(current="B", hands={"B": ["guard_wasp"]})
    put(s, "1,1", "worker_wasp", "A")
    play(s, "guard_wasp", "4,1")
    assert s.food["A"] == 0


def test_worker_wasp_has_flight():
    s = st(hands={"A": ["worker_wasp"]})
    assert "3,3" in place_targets(s)


# ============================================================ pheasant_legend (Ember)
# "Flight. Fall: shuffle Ember into your deck."

def test_pheasant_legend_falls_into_its_owners_deck():
    s = st(current="B", hands={"B": ["wolverine"]}, decks={"A": ["v1"] * 3, "B": ["v1"] * 3})
    put(s, "2,1", "pheasant_legend", "A")
    put(s, "4,1", "v1", "B"); put(s, "3,1", "v1", "B")
    play(s, "wolverine", "3,1")
    click_through(s)
    assert s.top_unit("2,1") is None
    assert "pheasant_legend" in s.decks["A"] and len(s.decks["A"]) == 4
    assert "pheasant_legend" not in s.remove_pile


def test_pheasant_legend_covered_is_not_a_fall():
    s = st(current="B", hands={"B": ["v8"]})
    put(s, "3,1", "pheasant_legend", "A")
    put(s, "4,1", "v1", "B")
    play(s, "v8", "3,1")
    assert [u.card_id for u in s.board["3,1"]] == ["pheasant_legend", "v8"]
    assert "pheasant_legend" not in s.decks["A"]


def test_pheasant_legend_has_flight():
    s = st(hands={"A": ["pheasant_legend"]})
    assert "3,3" in place_targets(s)


# ============================================================ wolf_legend_3 (White Wolf)
# "Once each turn, an ally can roam for free."

def test_wolf_legend_3_gives_one_free_roam_each_turn():
    s = st()
    put(s, "1,1", "wolf_legend_3", "A")
    put(s, "1,2", "wolf", "A")
    put(s, "1,3", "wolf", "A")
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert s.actions_taken_this_turn == 0                                  # free
    rules.apply_action(s, RoamAction("1,3", ("cr", "2,3")))
    assert s.actions_taken_this_turn == 1                                  # only once each turn


def test_wolf_legend_3_free_roam_comes_back_next_turn():
    s = st()
    put(s, "1,1", "wolf_legend_3", "A")
    put(s, "1,2", "wolf", "A")
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    end_turn(s); end_turn(s)
    rules.apply_action(s, RoamAction("2,2", ("cr", "2,3")))
    assert s.actions_taken_this_turn == 0


@pytest.mark.xfail(strict=True, reason="two readings: A) 'an ally can roam' lets any ally roam, Roam or not; "
                                       "B) only an ally that has Roam (rulings.md: Clarion). The engine follows B.")
def test_wolf_legend_3_lets_an_ally_without_roam_roam():
    s = st()
    put(s, "1,1", "wolf_legend_3", "A")
    put(s, "1,2", "v3", "A")
    assert legal(s, RoamAction("1,2", ("cr", "2,2")))


# ============================================================ wolf_legend_2 (Black Wolf)
# "Roam. Whenever a Canine roams, give it +1 strength and draw a card."

def test_wolf_legend_2_grows_and_draws_when_it_roams():
    s = st()
    bw = put(s, "1,1", "wolf_legend_2", "A")
    rules.apply_action(s, RoamAction("1,1", ("cr", "2,1")))
    assert bw.strength_counter == 1 and len(s.hands["A"]) == 1


def test_wolf_legend_2_grows_another_canine_that_roams():
    s = st()
    put(s, "1,1", "wolf_legend_2", "A")
    w = put(s, "1,3", "wolf", "A")
    rules.apply_action(s, RoamAction("1,3", ("cr", "2,3")))
    assert w.strength_counter == 1 and len(s.hands["A"]) == 1


def test_wolf_legend_2_ignores_a_non_canine_roaming():
    s = st()
    put(s, "1,1", "wolf_legend_2", "A")
    r = put(s, "1,3", "v_roam", "A")
    rules.apply_action(s, RoamAction("1,3", ("cr", "2,3")))
    assert r.strength_counter == 0 and s.hands["A"] == []


@pytest.mark.xfail(strict=True, reason="two readings: A) 'a Canine' is any Canine, the opponent's included (it grows "
                                       "and the Black Wolf's owner draws); B) only your Canines (rulings.md). "
                                       "The engine follows B.")
def test_wolf_legend_2_sees_an_enemy_canine_roam():
    s = st(current="B")
    put(s, "1,1", "wolf_legend_2", "A")
    w = put(s, "4,3", "wolf", "B")
    rules.apply_action(s, RoamAction("4,3", ("cr", "3,3")))
    assert w.strength_counter == 1 and len(s.hands["A"]) == 1


# ============================================================ fox
# "Roar: if an ally roamed this turn, draw 2 cards."

def test_fox_draws_2_if_an_ally_roamed_this_turn():
    s = st(hands={"A": ["fox"]})
    put(s, "1,2", "wolf", "A")
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    play(s, "fox", "1,1")
    assert len(s.hands["A"]) == 2


def test_fox_draws_nothing_without_a_roam():
    s = st(hands={"A": ["fox"]})
    put(s, "1,2", "wolf", "A")
    play(s, "fox", "1,1")
    assert s.hands["A"] == []


def test_fox_a_roam_last_turn_doesnt_count():
    s = st(hands={"A": ["fox"]})
    put(s, "1,2", "wolf", "A")
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    end_turn(s); end_turn(s)
    play(s, "fox", "1,1")
    assert s.hands["A"] == []


# ============================================================ wolf
# "Roam."

def test_wolf_roams_through_its_pack_and_one_step_beyond_for_an_action():
    s = st()
    put(s, "1,1", "wolf", "A")
    put(s, "2,1", "v1", "A")
    assert legal(s, RoamAction("1,1", ("cr", "3,1")))                     # through the pack, one beyond
    assert not legal(s, RoamAction("1,1", ("cr", "4,1")))                 # two beyond needs Reach
    rules.apply_action(s, RoamAction("1,1", ("cr", "3,1")))
    assert s.top_unit("3,1").card_id == "wolf" and s.top_unit("1,1") is None
    assert s.actions_taken_this_turn == 1
    assert not legal(s, RoamAction("3,1", ("cr", "3,2")))                 # once per turn


def test_wolf_roam_covers_only_weaker_enemies():
    s = st()
    put(s, "1,1", "wolf", "A")
    put(s, "2,1", "v5", "B")
    put(s, "1,2", "v6", "B")
    assert legal(s, RoamAction("1,1", ("cr", "2,1")))
    assert not legal(s, RoamAction("1,1", ("cr", "1,2")))


# ============================================================ coyote
# "Roar: give a connected ally Roam. It roams."

def test_coyote_gives_a_connected_ally_roam_and_it_roams():
    s = st(hands={"A": ["coyote"]})
    ally = put(s, "1,1", "v3", "A")
    put(s, "3,3", "v3", "A")                                               # not connected to the Coyote
    play(s, "coyote", "1,2")
    assert s.pending and "3,3" not in s.pending["options"]
    choose(s, "1,1")
    choose(s, "2,1")
    assert s.top_unit("2,1") is ally and s.top_unit("1,1") is None
    end_turn(s); end_turn(s)
    assert legal(s, RoamAction("2,1", ("cr", "3,1")))                      # it keeps Roam


def test_coyote_without_a_connected_ally_does_nothing():
    s = st(hands={"A": ["coyote"]})
    put(s, "3,3", "v3", "A")
    play(s, "coyote", "1,2")
    assert s.pending is None


# ============================================================ badger
# "Roar: draw an animal with Roam."

def test_badger_draws_an_animal_with_roam():
    s = st(hands={"A": ["badger"]}, decks={"A": ["v1", "wolf", "v2"], "B": []})
    play(s, "badger", "1,2")
    assert hand_ids(s, "A") == ["wolf"] and sorted(s.decks["A"]) == ["v1", "v2"]


def test_badger_draws_nothing_without_a_roam_animal():
    s = st(hands={"A": ["badger"]}, decks={"A": ["v1", "v2"], "B": []})
    play(s, "badger", "1,2")
    assert s.hands["A"] == [] and len(s.decks["A"]) == 2


# ============================================================ skunk_legend (Rue)
# "Roar: return all adjacent enemies to your opponent's hand."

def test_skunk_legend_returns_all_adjacent_enemies():
    s = st(hands={"A": ["skunk_legend"]})
    put(s, "1,1", "v1", "B")
    put(s, "2,2", "v2", "B")
    put(s, "1,3", "v1", "A")                                               # an ally stays
    play(s, "skunk_legend", "1,2")
    assert s.top_unit("1,1") is None and s.top_unit("2,2") is None
    assert sorted(hand_ids(s, "B")) == ["v1", "v2"]
    assert s.top_unit("1,3").owner == "A"


def test_skunk_legend_cant_return_armor():
    s = st(hands={"A": ["skunk_legend"]})
    put(s, "2,2", "tortoise", "B")
    play(s, "skunk_legend", "1,2")
    assert s.top_unit("2,2").card_id == "tortoise"


# ============================================================ falcon_legend
# "Flight. Roar: draw a card for each ally next to your opponent's den."

def test_falcon_legend_draws_for_each_ally_next_to_the_enemy_den_itself_included():
    s = st(hands={"A": ["falcon_legend"]})
    put(s, "4,3", "v1", "A")
    put(s, "3,2", "v1", "A")                                               # not next to the den
    play(s, "falcon_legend", "4,1")
    assert len(s.hands["A"]) == 2


def test_falcon_legend_elsewhere_counts_the_others():
    s = st(hands={"A": ["falcon_legend"]})
    put(s, "4,3", "v1", "A")
    play(s, "falcon_legend", "2,2")
    assert len(s.hands["A"]) == 1


def test_falcon_legend_with_none_draws_nothing():
    s = st(hands={"A": ["falcon_legend"]})
    play(s, "falcon_legend", "2,2")
    assert s.hands["A"] == []


# ============================================================ hornet
# "Flight. Roar: discard a Hornet from your hand or deck to remove an adjacent enemy."

def test_hornet_discards_a_hornet_from_hand_to_remove_an_adjacent_enemy():
    s = st(hands={"A": ["hornet", "hornet"]})
    put(s, "2,1", "v9", "B")
    play(s, "hornet", "1,1")
    click_through(s)
    assert s.top_unit("2,1") is None
    assert "hornet" not in hand_ids(s, "A")


def test_hornet_discards_from_the_deck():
    s = st(hands={"A": ["hornet"]}, decks={"A": ["v1", "hornet"], "B": []})
    put(s, "2,1", "v9", "B")
    play(s, "hornet", "1,1")
    click_through(s)
    assert s.top_unit("2,1") is None and s.decks["A"] == ["v1"]


def test_hornet_without_a_spare_hornet_removes_nothing():
    s = st(hands={"A": ["hornet"]}, decks={"A": ["v1"], "B": []})
    put(s, "2,1", "v9", "B")
    play(s, "hornet", "1,1")
    click_through(s)
    assert s.top_unit("2,1").card_id == "v9"


def test_hornet_without_an_enemy_keeps_its_spare():
    s = st(hands={"A": ["hornet", "hornet"]})
    play(s, "hornet", "1,1")
    click_through(s)
    assert hand_ids(s, "A") == ["hornet"]


def test_hornet_has_flight():
    s = st(hands={"A": ["hornet"]})
    assert "3,3" in place_targets(s)


# ============================================================ skunk
# "Roar: return an adjacent enemy to its owner's hand. It can't be played next turn."

def test_skunk_returns_an_adjacent_enemy_which_cant_be_played_next_turn():
    s = st(hands={"A": ["skunk"]})
    put(s, "2,1", "v3", "B")
    play(s, "skunk", "1,1")
    click_through(s)
    assert s.top_unit("2,1") is None and hand_ids(s, "B") == ["v3"]
    end_turn(s)
    assert s.current == "B"
    assert not any(isinstance(a, PlaceAction) and a.card_id == "v3" for a in rules.legal_actions(s))
    end_turn(s); end_turn(s)
    assert s.current == "B"
    assert any(isinstance(a, PlaceAction) and a.card_id == "v3" for a in rules.legal_actions(s))


def test_skunk_returns_no_ally():
    s = st(hands={"A": ["skunk"]})
    put(s, "2,1", "v3", "A")
    play(s, "skunk", "1,1")
    click_through(s)
    assert s.top_unit("2,1").card_id == "v3"


# ============================================================ falcon
# "Flight. Roar: if this is next to your opponent's den, draw a card."

def test_falcon_next_to_the_enemy_den_draws():
    s = st(hands={"A": ["falcon"]})
    play(s, "falcon", "4,2")
    assert len(s.hands["A"]) == 1


def test_falcon_elsewhere_draws_nothing():
    s = st(hands={"A": ["falcon"]})
    play(s, "falcon", "3,2")
    assert s.hands["A"] == []


# ============================================================ fox_legend (Scarlett)
# "Roar: place Poppy and Rusty on random adjacent empty crossroads."

def test_fox_legend_places_both_cubs_on_adjacent_empty_crossroads():
    s = st(hands={"A": ["fox_legend"]})
    put(s, "1,2", "v1", "A")
    play(s, "fox_legend", "2,2")
    cubs = {u.card_id: cr for cr, stack in s.board.items() for u in stack if u.card_id in ("baby_fox", "baby_fox_2")}
    assert set(cubs) == {"baby_fox", "baby_fox_2"}
    assert set(cubs.values()) <= {"2,1", "3,2", "2,3"} and len(set(cubs.values())) == 2
    assert all(s.top_unit(cr).owner == "A" for cr in cubs.values())


def test_fox_legend_with_one_empty_crossroad_places_one_cub():
    s = st(hands={"A": ["fox_legend"]})
    put(s, "1,2", "v1", "A")
    play(s, "fox_legend", "1,1")                                           # neighbours: 1,2 (taken), 2,1
    cubs = [cr for cr, stack in s.board.items() for u in stack if u.card_id in ("baby_fox", "baby_fox_2")]
    assert cubs == ["2,1"]


def test_fox_legend_with_no_room_places_none():
    s = st(hands={"A": ["fox_legend"]})
    put(s, "1,2", "v1", "A")
    put(s, "2,1", "v1", "B")
    play(s, "fox_legend", "1,1")
    assert not on_board(s, "baby_fox") and not on_board(s, "baby_fox_2")


# ============================================================ lynx
# "Roar: if you place this on top of an enemy, draw 2 cards."

def test_lynx_on_an_enemy_draws_2():
    s = st(hands={"A": ["lynx"]})
    put(s, "1,1", "v4", "B")
    play(s, "lynx", "1,1")
    assert len(s.hands["A"]) == 2


def test_lynx_on_empty_or_an_ally_draws_nothing():
    s = st(hands={"A": ["lynx", "lynx"]})
    put(s, "1,2", "v4", "A")
    play(s, "lynx", "1,1")
    assert len(s.hands["A"]) == 1
    play(s, "lynx", "1,2")
    assert s.hands["A"] == []


# ============================================================ bobcat
# "Roar: if you control another Cat, draw a card."

def test_bobcat_with_another_cat_draws():
    s = st(hands={"A": ["bobcat"]})
    put(s, "3,3", "lion", "A")
    play(s, "bobcat", "1,2")
    assert len(s.hands["A"]) == 1


def test_bobcat_alone_or_with_an_enemy_cat_draws_nothing():
    s = st(hands={"A": ["bobcat"]})
    put(s, "3,3", "lion", "B")
    play(s, "bobcat", "1,2")
    assert s.hands["A"] == []


# ============================================================ chipmunk_legend (Tally)
# "Roar: gain 1 food for each 3 food you have."

def test_chipmunk_legend_gains_1_for_each_3_food():
    s = st(hands={"A": ["chipmunk_legend"]}, food={"A": 10, "B": 0})
    play(s, "chipmunk_legend", "1,2")
    assert s.food["A"] == 13


def test_chipmunk_legend_with_less_than_3_gains_nothing():
    s = st(hands={"A": ["chipmunk_legend"]}, food={"A": 2, "B": 0})
    play(s, "chipmunk_legend", "1,2")
    assert s.food["A"] == 2


# ============================================================ flying_squirrel
# "Flight. Roar: gain 10 food and draw a card."

def test_flying_squirrel_gains_10_and_draws():
    s = st(hands={"A": ["flying_squirrel"]})
    assert "3,3" in place_targets(s)
    play(s, "flying_squirrel", "3,3")
    assert s.food["A"] == 10 and len(s.hands["A"]) == 1


def test_flying_squirrel_with_an_empty_deck_still_gains():
    s = st(hands={"A": ["flying_squirrel"]}, decks={"A": [], "B": []})
    play(s, "flying_squirrel", "3,3")
    assert s.food["A"] == 10 and s.hands["A"] == []


# ============================================================ beaver
# "Roar: next turn, take 1 additional action."

def test_beaver_gives_one_more_action_next_turn_only():
    s = st(hands={"A": ["beaver"]}, decks={"A": ["v1"] * 10, "B": ["v1"] * 10})
    play(s, "beaver", "1,2")
    end_turn(s)
    assert s.current == "B"
    rules.apply_action(s, DrawAction()); rules.apply_action(s, DrawAction())
    assert s.current == "A"                                                # B's turn is a normal one
    rules.apply_action(s, DrawAction()); rules.apply_action(s, DrawAction())
    assert s.current == "A"                                                # a third action
    rules.apply_action(s, DrawAction())
    assert s.current == "B"
    rules.apply_action(s, DrawAction()); rules.apply_action(s, DrawAction())
    rules.apply_action(s, DrawAction()); rules.apply_action(s, DrawAction())
    assert s.current == "B"                                                # A's turn after is back to 2


# ============================================================ dormouse
# "Dusk: draw a card for each 10 food you gained this turn."

def test_dormouse_draws_one_for_each_10_food_gained_this_turn():
    s = st(hands={"A": ["squirrel", "squirrel"]})
    put(s, "3,3", "dormouse", "A")
    play(s, "squirrel", "1,1")
    play(s, "squirrel", "1,3")                                             # 20 gained; the turn ends
    assert s.current == "B" and len(s.hands["A"]) == 2


def test_dormouse_rounds_down():
    s = st(hands={"A": ["chipmunk_legend"]}, food={"A": 27, "B": 0})
    put(s, "3,3", "dormouse", "A")
    play(s, "chipmunk_legend", "1,1")                                      # gains 9
    end_turn(s)
    assert s.hands["A"] == []


def test_dormouse_does_nothing_at_the_opponents_dusk():
    s = st(current="B", hands={"B": ["squirrel", "squirrel"]})
    put(s, "1,1", "dormouse", "A")
    play(s, "squirrel", "4,1"); play(s, "squirrel", "4,3")
    assert s.hands["A"] == []


# ============================================================ squirrel
# "Roar: gain 10 food."

def test_squirrel_gains_10_food():
    s = st(hands={"A": ["squirrel"]}, food={"A": 5, "B": 0})
    play(s, "squirrel", "1,2")
    assert s.food["A"] == 15 and s.food["B"] == 0


# ============================================================ chipmunk
# "Roar: gain 10 food. At the start of your next turn, gain 10 more."

def test_chipmunk_gains_10_now_and_10_at_the_start_of_your_next_turn():
    s = st(hands={"A": ["chipmunk"]})
    play(s, "chipmunk", "1,2")
    assert s.food["A"] == 10
    end_turn(s)
    assert s.food["A"] == 10                                               # not on the opponent's turn
    end_turn(s)
    assert s.current == "A" and s.food["A"] == 20
    end_turn(s); end_turn(s)
    assert s.food["A"] == 20                                               # once


# ============================================================ squirrel_legend (Yuki)
# "Roar: lose all your food. In 2 turns, gain three times as much."

def test_squirrel_legend_loses_all_food_and_pays_three_times_in_2_turns():
    s = st(hands={"A": ["squirrel_legend"]}, food={"A": 7, "B": 3})
    play(s, "squirrel_legend", "1,2")
    assert s.food == {"A": 0, "B": 3}
    end_turn(s); end_turn(s)
    assert s.food["A"] == 0                                                # one of your turns on: not yet
    end_turn(s); end_turn(s)
    assert s.current == "A" and s.food["A"] == 21


def test_squirrel_legend_with_no_food_pays_nothing():
    s = st(hands={"A": ["squirrel_legend"]})
    play(s, "squirrel_legend", "1,2")
    for _ in range(4):
        end_turn(s)
    assert s.food["A"] == 0


# ============================================================ porcupine
# "Spikes. Your adjacent animals have Spikes."

def test_porcupine_spikes_remove_the_first_enemy_that_covers_it():
    s = st(current="B", hands={"B": ["v8", "v8"]})
    put(s, "4,2", "v1", "B")
    p = put(s, "3,2", "porcupine", "A")
    play(s, "v8", "3,2")
    assert s.top_unit("3,2") is p and "v8" in s.remove_pile
    play(s, "v8", "3,2")
    assert s.top_unit("3,2").card_id == "v8"                               # spent


def test_porcupine_gives_spikes_to_adjacent_allies_only():
    s = st(current="B", hands={"B": ["v8", "v8"]})
    put(s, "4,2", "v1", "B"); put(s, "4,1", "v1", "B")
    put(s, "3,3", "porcupine", "A")
    ally = put(s, "3,2", "v2", "A")                                        # next to the Porcupine
    put(s, "3,1", "v2", "A")                                               # not next to it
    play(s, "v8", "3,2")
    assert s.top_unit("3,2") is ally
    play(s, "v8", "3,1")
    assert s.top_unit("3,1").card_id == "v8"


# ============================================================ black_bear
# "Roar: in 2 turns, draw 2 cards."

def test_black_bear_draws_2_in_2_turns():
    s = st(hands={"A": ["black_bear"]})
    play(s, "black_bear", "1,2")
    end_turn(s); end_turn(s)
    assert s.hands["A"] == []
    end_turn(s); end_turn(s)
    assert s.current == "A" and len(s.hands["A"]) == 2


# ============================================================ owl
# "Flight. Roar: Scout a card."  Scout: look at three different cards from the top, draw one, shuffle the others back.

def test_owl_scouts_a_card_from_the_top_three():
    s = st(hands={"A": ["owl"]}, decks={"A": ["v1", "v2", "v3", "v4", "v5"], "B": []})
    play(s, "owl", "1,2")
    assert s.pending and len(s.pending["options"]) == 3
    click_through(s)
    assert len(s.hands["A"]) == 1 and hand_ids(s, "A")[0] in {"v3", "v4", "v5"}
    assert sorted(s.decks["A"] + hand_ids(s, "A")) == ["v1", "v2", "v3", "v4", "v5"]


def test_owl_with_an_empty_deck_scouts_nothing():
    s = st(hands={"A": ["owl"]}, decks={"A": [], "B": []})
    play(s, "owl", "1,2")
    assert s.pending is None and s.hands["A"] == []


def test_owl_has_flight():
    s = st(hands={"A": ["owl"]})
    assert "3,3" in place_targets(s)


# ============================================================ raven_legend (Grimm)
# "Flight. Roar: put 2 animals from your opponent's Remove Pile into your hand."

def test_raven_legend_takes_2_from_the_opponents_remove_pile():
    s = st(hands={"A": ["raven_legend"]})
    s.pile_add("v5", "B"); s.pile_add("v6", "B"); s.pile_add("v7", "A")
    play(s, "raven_legend", "1,2")
    click_through(s)
    assert sorted(hand_ids(s, "A")) == ["v5", "v6"]
    assert s.remove_pile == ["v7"]


def test_raven_legend_with_one_takes_one_and_never_your_own():
    s = st(hands={"A": ["raven_legend"]})
    s.pile_add("v5", "B"); s.pile_add("v7", "A")
    play(s, "raven_legend", "1,2")
    click_through(s)
    assert hand_ids(s, "A") == ["v5"]


# ============================================================ hawk
# "Flight. Roar: remove an adjacent enemy of strength 4 or less."

def test_hawk_removes_an_adjacent_enemy_of_4_or_less():
    s = st(hands={"A": ["hawk"]})
    put(s, "2,1", "v4", "B")
    play(s, "hawk", "1,1")
    click_through(s)
    assert s.top_unit("2,1") is None


def test_hawk_leaves_a_5():
    s = st(hands={"A": ["hawk"]})
    put(s, "2,1", "v5", "B")
    play(s, "hawk", "1,1")
    click_through(s)
    assert s.top_unit("2,1").card_id == "v5"


def test_hawk_has_flight_and_spares_allies():
    s = st(hands={"A": ["hawk"]})
    put(s, "3,2", "v1", "A")
    play(s, "hawk", "3,3")
    click_through(s)
    assert s.top_unit("3,2").card_id == "v1"


# ============================================================ magpie
# "Flight. Roar: steal a card from your opponent's hand, then discard a card."

def test_magpie_steals_then_discards():
    s = st(hands={"A": ["magpie", "v3"], "B": ["v6"]})
    play(s, "magpie", "1,1")
    assert s.hands["B"] == [] and "v6" in hand_ids(s, "A")
    v3 = next(u.iid for u in s.hands["A"] if u.card_id == "v3")
    choose(s, v3)
    assert hand_ids(s, "A") == ["v6"]


def test_magpie_has_flight():
    s = st(hands={"A": ["magpie"]})
    assert "3,3" in place_targets(s)


# ============================================================ raven
# "Flight. Roar: draw 3 cards, then shuffle 2 cards back."

def test_raven_draws_3_then_shuffles_2_back():
    s = st(hands={"A": ["raven"]}, decks={"A": ["v1", "v2", "v3", "v4", "v5"], "B": []})
    play(s, "raven", "1,2")
    click_through(s)
    assert len(s.hands["A"]) == 1 and len(s.decks["A"]) == 4


# ============================================================ bird_egg
# "Roar: Scout a Bird. Next turn, remove this and draw a Bird."

def test_bird_egg_scouts_a_bird_then_next_turn_is_removed_and_draws_a_bird():
    s = st(hands={"A": ["bird_egg"]}, decks={"A": ["falcon", "v1", "hawk", "v2", "owl", "v3", "pigeon"], "B": ["v1"] * 5})
    play(s, "bird_egg", "1,2")
    click_through(s)
    birds = {"falcon", "hawk", "owl", "pigeon"}
    assert len(s.hands["A"]) == 1 and hand_ids(s, "A")[0] in birds
    end_turn(s)
    assert s.top_unit("1,2").card_id == "bird_egg"                        # not on the opponent's turn
    end_turn(s)
    assert s.top_unit("1,2") is None and "bird_egg" in s.remove_pile
    assert len(s.hands["A"]) == 2 and all(c in birds for c in hand_ids(s, "A"))


# ============================================================ viper
# "Roar: give an adjacent enemy -3 strength."

def test_viper_gives_an_adjacent_enemy_minus_3():
    s = st(hands={"A": ["viper"]})
    e = put(s, "2,1", "v5", "B")
    play(s, "viper", "1,1")
    click_through(s)
    assert strength(s, e) == 2 and e.strength_counter == -3


def test_viper_spares_allies():
    s = st(hands={"A": ["viper"]})
    a = put(s, "2,1", "v5", "A")
    play(s, "viper", "1,1")
    click_through(s)
    assert strength(s, a) == 5


# ============================================================ eagle_legend
# "Flight. Apex Predator. When this enters your hand, add [NAME] to your hand."

def test_eagle_legend_brings_its_mate_when_drawn():
    s = st(decks={"A": ["eagle_legend"], "B": ["v1"]})
    rules.apply_action(s, DrawAction())
    assert sorted(hand_ids(s, "A")) == ["eagle_legend", "eagle_legend_2"]


def test_eagle_legend_flies_onto_prey_anywhere_and_eats_it():
    s = st(hands={"A": ["eagle_legend"]})
    put(s, "3,3", "v2", "B")
    assert "3,3" in place_targets(s) and "2,2" not in place_targets(s)   # never onto an empty crossroad
    play(s, "eagle_legend", "3,3")
    assert [u.card_id for u in s.board["3,3"]] == ["eagle_legend"] and "v2" in s.remove_pile


# ============================================================ moose
# "Hungry 3. Roam."

def test_moose_eats_3_at_the_start_of_your_turn():
    s = st(food={"A": 5, "B": 0})
    m = put(s, "1,2", "moose", "A")
    end_turn(s); end_turn(s)
    assert s.food["A"] == 2 and strength(s, m) == 8


def test_moose_short_of_food_shrinks_for_good():
    s = st(food={"A": 1, "B": 0})
    m = put(s, "1,2", "moose", "A")
    end_turn(s); end_turn(s)
    assert s.food["A"] == 0 and strength(s, m) == 6


def test_moose_roams():
    s = st()
    put(s, "1,2", "moose", "A")
    assert legal(s, RoamAction("1,2", ("cr", "2,2")))


# ============================================================ boar_legend
# "Your opponent's regions produce 5 less food."

def test_boar_legend_cuts_the_opponents_regions_by_5():
    s = st(current="B")
    for cr in ("3,1", "4,1", "3,2", "4,2"):
        put(s, cr, "v1", "B")                                              # B holds R3 (10)
    put(s, "1,2", "boar_legend", "A")
    end_turn(s)
    assert s.food["B"] == 5


def test_boar_legend_leaves_your_own_regions():
    s = st()
    for cr in ("1,1", "2,1", "2,2"):
        put(s, cr, "v1", "A")
    put(s, "1,2", "boar_legend", "A")                                      # A holds R1 (10)
    end_turn(s)
    assert s.food["A"] == 10


# ============================================================ deer
# "Flee. Roar: place a Fawn on a random adjacent empty crossroad."

def test_deer_places_a_fawn_adjacent():
    s = st(hands={"A": ["deer"]})
    put(s, "1,1", "v1", "B")
    play(s, "deer", "1,2")
    fawns = on_board(s, "fawn", "A")
    assert len(fawns) == 1 and fawns[0][0] in {"2,2", "1,3"}


def test_deer_with_no_room_places_no_fawn():
    s = st(hands={"A": ["deer"]})
    put(s, "2,1", "v1", "B")
    put(s, "1,2", "v1", "A")
    play(s, "deer", "1,1")
    assert not on_board(s, "fawn")


def test_deer_flees_when_an_enemy_covers_it():
    s = st(current="B", hands={"B": ["v5"]})
    put(s, "4,2", "v1", "B")
    put(s, "3,2", "deer", "A")
    play(s, "v5", "3,2")
    assert "deer" in hand_ids(s, "A") and [u.card_id for u in s.board["3,2"]] == ["v5"]


# ============================================================ boar
# "Remove the first enemy placed next to this."

def test_boar_removes_the_first_enemy_placed_next_to_it_only():
    s = st(current="B", hands={"B": ["v5", "v5"]})
    put(s, "3,1", "boar", "A")
    put(s, "4,2", "v1", "B")
    play(s, "v5", "4,1")
    assert s.top_unit("4,1") is None and "v5" in s.remove_pile
    play(s, "v5", "3,2")
    assert s.top_unit("3,2").card_id == "v5"


def test_boar_ignores_allies_placed_next_to_it():
    s = st(hands={"A": ["v5"]}, current="A")
    put(s, "2,1", "boar", "A")
    play(s, "v5", "1,1")
    assert s.top_unit("1,1").card_id == "v5"
    end_turn(s)
    s.hands["B"] = []
    s.add_to_hand("B", "v5")
    put(s, "4,1", "v1", "B")
    play(s, "v5", "3,1")
    assert s.top_unit("3,1") is None                                       # still the first enemy


# ============================================================ eagle
# "Flight. Apex Predator."

def test_eagle_lands_on_prey_anywhere_and_eats_it():
    s = st(hands={"A": ["eagle"]})
    put(s, "3,3", "v5", "B")
    put(s, "3,1", "v6", "B")
    targets = place_targets(s)
    assert "3,3" in targets and "3,1" not in targets and "2,2" not in targets
    play(s, "eagle", "3,3")
    assert [u.card_id for u in s.board["3,3"]] == ["eagle"] and "v5" in s.remove_pile


def test_eagle_eats_an_ally():
    s = st(hands={"A": ["eagle"]})
    put(s, "3,3", "v9", "A")
    play(s, "eagle", "3,3")
    assert [u.card_id for u in s.board["3,3"]] == ["eagle"] and "v9" in s.remove_pile


def test_eagle_never_onto_a_den():
    s = st(hands={"A": ["eagle"]})
    put(s, "4,2", "v1", "A"); put(s, "3,2", "v1", "A"); put(s, "2,2", "v1", "A"); put(s, "1,2", "v1", "A")
    assert not any(isinstance(a, PlaceAction) and a.target[0] == "hq" for a in rules.legal_actions(s))


# ============================================================ woodpecker
# "Flight. Roar: your next Roar this turn happens twice."

def test_woodpecker_doubles_your_next_roar_this_turn():
    s = st(hands={"A": ["woodpecker", "squirrel", "squirrel"]}, decks={"A": ["v1"] * 5, "B": ["v1"] * 5})
    play(s, "woodpecker", "3,3")
    play(s, "squirrel", "1,2")
    assert s.food["A"] == 20


def test_woodpecker_only_this_turn():
    s = st(hands={"A": ["woodpecker", "squirrel"]})
    play(s, "woodpecker", "3,3")
    end_turn(s); end_turn(s)
    play(s, "squirrel", "1,2")
    assert s.food["A"] == 10


def test_woodpecker_only_the_next_roar():
    s = st(hands={"A": ["woodpecker", "squirrel", "squirrel"]})
    play(s, "woodpecker", "3,3")
    play(s, "squirrel", "1,2")                                             # doubled: 20; the turn ends
    end_turn(s)
    play(s, "squirrel", "1,1")
    assert s.food["A"] == 30


# ============================================================ stag_beetle
# "Armor. Roar: gain 5 food for each of your animals with Armor."

def test_stag_beetle_gains_5_for_each_of_your_armored_animals():
    s = st(hands={"A": ["stag_beetle"]})
    put(s, "1,1", "tortoise", "A")
    put(s, "3,3", "tortoise", "B")                                         # not yours
    play(s, "stag_beetle", "1,2")
    assert s.food["A"] == 10                                               # the Tortoise and itself


def test_stag_beetle_has_armor():
    s = st(current="B", hands={"B": ["skunk_legend"]})
    put(s, "3,2", "stag_beetle", "A")
    put(s, "4,1", "v1", "B")
    play(s, "skunk_legend", "4,2")
    assert s.top_unit("3,2").card_id == "stag_beetle"


# ============================================================ grizzly_bear
# "Roar: your opponent draws a card."

def test_grizzly_bear_makes_the_opponent_draw():
    s = st(hands={"A": ["grizzly_bear"]}, decks={"A": ["v1"], "B": ["v2"]})
    play(s, "grizzly_bear", "1,2")
    assert hand_ids(s, "B") == ["v2"] and s.hands["A"] == []


def test_grizzly_bear_with_an_empty_opponent_deck():
    s = st(hands={"A": ["grizzly_bear"]}, decks={"A": ["v1"], "B": []})
    play(s, "grizzly_bear", "1,2")
    assert s.hands["B"] == [] and s.top_unit("1,2").card_id == "grizzly_bear"


# ============================================================ queen_ant
# "Dusk: place a Young Ant on an adjacent empty crossroad."

def test_queen_ant_lays_a_young_ant_at_your_dusk():
    s = st()
    put(s, "1,1", "queen_ant", "A")
    put(s, "1,2", "v1", "B")
    end_turn(s)
    ants = on_board(s, "young_ant", "A")
    assert [cr for cr, _ in ants] == ["2,1"]
    end_turn(s)
    assert len(on_board(s, "young_ant")) == 1                              # not at the opponent's dusk


def test_queen_ant_with_no_room_lays_nothing():
    s = st()
    put(s, "1,1", "queen_ant", "A")
    put(s, "1,2", "v1", "B"); put(s, "2,1", "v1", "A")
    end_turn(s)
    assert not on_board(s, "young_ant")


# ============================================================ wolverine
# "Roar: remove an adjacent enemy with no other enemy next to it."

def test_wolverine_removes_a_lone_adjacent_enemy():
    s = st(hands={"A": ["wolverine"]})
    put(s, "2,1", "v9", "B")
    play(s, "wolverine", "1,1")
    click_through(s)
    assert s.top_unit("2,1") is None


def test_wolverine_spares_an_enemy_with_another_enemy_beside_it():
    s = st(hands={"A": ["wolverine"]})
    put(s, "2,1", "v9", "B")
    put(s, "3,1", "v1", "B")
    play(s, "wolverine", "1,1")
    click_through(s)
    assert s.top_unit("2,1").card_id == "v9"


# ============================================================ rodent_legend
# "Roar: gain as much food as you gained this turn."

def test_rodent_legend_doubles_this_turns_food():
    s = st(hands={"A": ["squirrel", "rodent_legend"]}, food={"A": 5, "B": 0})
    play(s, "squirrel", "1,1")
    play(s, "rodent_legend", "1,2")
    assert s.food["A"] == 25


def test_rodent_legend_with_nothing_gained_gains_nothing():
    s = st(hands={"A": ["rodent_legend"]}, food={"A": 5, "B": 0})
    play(s, "rodent_legend", "1,2")
    assert s.food["A"] == 5


# ============================================================ deer_legend
# "Flee. Roar: draw 2 animals with Flee. Whenever one of your animals flees, give it +2 strength."

def test_deer_legend_draws_2_animals_with_flee():
    s = st(hands={"A": ["deer_legend"]}, decks={"A": ["v1", "gazelle", "v2", "deer", "v3"], "B": []})
    play(s, "deer_legend", "1,2")
    assert sorted(hand_ids(s, "A")) == ["deer", "gazelle"]


def test_deer_legend_draws_what_flee_there_is():
    s = st(hands={"A": ["deer_legend"]}, decks={"A": ["v1", "gazelle", "v2"], "B": []})
    play(s, "deer_legend", "1,2")
    assert hand_ids(s, "A") == ["gazelle"]


def test_deer_legend_grows_an_ally_that_flees_and_itself():
    s = st(current="B", hands={"B": ["v5", "v5"]})
    put(s, "4,2", "v1", "B"); put(s, "4,1", "v1", "B")
    put(s, "3,2", "deer_legend", "A")
    put(s, "3,1", "deer", "A")
    play(s, "v5", "3,1")
    deer = next(u for u in s.hands["A"] if u.card_id == "deer")
    assert deer.strength_counter == 2
    play(s, "v5", "3,2")
    me = next(u for u in s.hands["A"] if u.card_id == "deer_legend")
    assert me.strength_counter == 2


# ============================================================ bison
# "Can't be covered while grazing."

def test_bison_cant_be_covered_while_grazing():
    s = st(current="B", hands={"B": ["v9"]})
    for cr in ("1,1", "1,2", "2,2"):
        put(s, cr, "v1", "A")
    put(s, "2,1", "bison", "A")                                            # closes R1: it grazes
    put(s, "4,1", "v1", "B"); put(s, "3,1", "v1", "B")
    assert "2,1" not in place_targets(s)


def test_bison_not_grazing_can_be_covered():
    s = st(current="B", hands={"B": ["v8"]})
    put(s, "2,1", "bison", "A")
    put(s, "4,1", "v1", "B"); put(s, "3,1", "v1", "B")
    assert "2,1" in place_targets(s)


# ============================================================ deer_legend_2 (Fawn)
# "Flee. Roar: add a Young Stag to your hand."

def test_deer_legend_2_adds_a_young_stag():
    s = st(hands={"A": ["deer_legend_2"]})
    play(s, "deer_legend_2", "1,2")
    assert hand_ids(s, "A") == ["young_stag"]


def test_deer_legend_2_flees():
    s = st(current="B", hands={"B": ["v5"]})
    put(s, "4,2", "v1", "B")
    put(s, "3,2", "deer_legend_2", "A")
    play(s, "v5", "3,2")
    assert "deer_legend_2" in hand_ids(s, "A")


def test_woodpecker_second_roar_picks_a_new_target():
    s = st(hands={"A": ["woodpecker", "hawk"]})
    put(s, "2,1", "v3", "B")
    put(s, "1,2", "v3", "B")
    play(s, "woodpecker", "3,3")
    play(s, "hawk", "1,1")
    choose(s, "1,2")
    assert s.pending["options"] == ["2,1"]                                # the first Roar's target is gone
    choose(s, "2,1")
    assert s.top_unit("2,1") is None and s.top_unit("1,2") is None       # the Roar happened twice
