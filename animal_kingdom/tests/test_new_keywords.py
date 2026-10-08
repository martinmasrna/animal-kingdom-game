"""Roam, Reach N, Poison, and Dawn/Dusk play order (keywords.md), on test-only cards: no real card carries
Roam, Reach or Poison yet.

Map A: a 4x3 grid of crossroads "col,row", orthogonal neighbours. A's den fronts column 1, B's column 4.
"""

from __future__ import annotations

import pytest

from animal_kingdom.engine import effects, rules, statics
from animal_kingdom.engine.actions import (DrawAction, PassAction, PlaceAction, RoamAction,
                                           action_from_dict)
from animal_kingdom.engine.state import EngineError, GameState

from ._helpers import apply_click, cards_with, make_state, put

CARDS = cards_with(
    {"id": "t_roamer", "base_strength": 4, "keywords": ["Roam"], "tags": ["Canine"]},
    {"id": "t_roam_cat", "base_strength": 5, "keywords": ["Roam"], "tags": ["Cat"]},
    {"id": "t_roam_apex", "base_strength": 7, "keywords": ["Roam", "Apex Predator"]},
    {"id": "t_roam_armor", "base_strength": 6, "keywords": ["Roam", "Armor"]},
    {"id": "t_poison", "base_strength": 2, "keywords": ["Poison"]},
    {"id": "t_reach2", "base_strength": 3, "keywords": ["Reach"], "reach": 2},
    {"id": "t_reach3", "base_strength": 6, "keywords": ["Reach"], "reach": 3},
    {"id": "t_dusk", "base_strength": 2},
    {"id": "t_dusk2", "base_strength": 2},
    {"id": "t_body", "base_strength": 4},
)


def state(**kw) -> GameState:
    return make_state(cards=CARDS, **kw)


def roams(s):
    return {(a.origin, a.target) for a in rules.legal_actions(s) if isinstance(a, RoamAction)}


def ids(s, cr):
    return [u.card_id for u in s.board.get(cr, [])]


def end_turn(s):
    rules.apply_action(s, PassAction())


# ===================================================================== Roam

def test_roam_moves_to_an_adjacent_crossroad_and_costs_an_action():
    s = state(hands={"A": ["t_body"]})
    u = put(s, "1,2", "t_roamer", "A")
    assert roams(s) == {("1,2", ("cr", "1,1")), ("1,2", ("cr", "1,3")), ("1,2", ("cr", "2,2"))}
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert ids(s, "2,2") == ["t_roamer"] and "1,2" not in s.board
    assert s.board["2,2"][-1] is u                       # the same animal, not a new one
    assert s.actions_taken_this_turn == 1 and s.current == "A"


def test_only_an_animal_connected_to_your_den_roams():
    s = state()
    put(s, "3,2", "t_roamer", "A")                      # stranded: no chain back to the den
    assert roams(s) == set()
    put(s, "1,2", "t_body", "A"); put(s, "2,2", "t_body", "A")
    assert ("3,2", ("cr", "3,1")) in roams(s)


def test_an_animal_without_roam_does_not_roam():
    s = state()
    put(s, "1,2", "t_body", "A")
    assert roams(s) == set()


def test_each_animal_roams_at_most_once_per_turn():
    s = state(hands={"A": ["t_body", "t_body"], "B": ["t_body"]})
    put(s, "1,2", "t_roamer", "A")
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert roams(s) == set()                            # it has roamed this turn; nothing else roams
    rules.apply_action(s, PlaceAction("t_body", ("cr", "1,2")))   # keeps it connected
    end_turn(s)                                         # B passes
    assert s.current == "A" and ("2,2", ("cr", "3,2")) in roams(s)


def test_roam_follows_the_placement_rules():
    s = state()
    put(s, "1,2", "t_roamer", "A")                      # strength 4
    put(s, "1,1", "t_dusk", "B")                        # 2: it beats it
    put(s, "1,3", "t_body", "B")                        # 4: equal, it can't
    put(s, "2,2", "t_dusk", "A")                        # its own: always
    assert roams(s) == {("1,2", ("cr", "1,1")), ("1,2", ("cr", "2,2"))}
    rules.apply_action(s, RoamAction("1,2", ("cr", "1,1")))
    assert ids(s, "1,1") == ["t_dusk", "t_roamer"]      # it covers; the cover buries, it doesn't remove


def test_an_illegal_roam_is_refused():
    s = state()
    put(s, "1,2", "t_roamer", "A")
    with pytest.raises(EngineError):
        rules.apply_action(s, RoamAction("1,2", ("cr", "3,2")))   # not adjacent
    with pytest.raises(EngineError):
        rules.apply_action(s, RoamAction("1,1", ("cr", "2,1")))   # nothing there


def test_roaming_onto_the_enemy_den_captures_it():
    s = state()
    for cr in ("1,2", "2,2", "3,2"):
        put(s, cr, "t_body", "A")
    put(s, "4,2", "t_roamer", "A")
    assert ("4,2", ("hq", "B")) in roams(s)
    rules.apply_action(s, RoamAction("4,2", ("hq", "B")))
    assert s.result is not None and s.result.winner == "A" and s.result.reason == "hq_capture"
    assert [e["e"] for e in s.events][-2:] == ["roam", "capture"]


def test_leaving_a_crossroad_uncovers_what_was_beneath():
    s = state()
    put(s, "1,2", "t_body", "B")
    put(s, "1,2", "t_roamer", "A")                      # A's roamer sits on B's animal
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert ids(s, "1,2") == ["t_body"] and s.owner_of("1,2") == "B"


def test_moving_is_not_placing_no_roar_and_no_play_reactions(monkeypatch):
    calls = []
    monkeypatch.setitem(effects.EFFECTS, "t_roamer", {"on_place": lambda st, u, cr: calls.append("roar")})
    monkeypatch.setitem(effects.EFFECTS, "t_body", {"on_friendly_play": lambda st, w, p: calls.append("play")})
    s = state()
    put(s, "1,2", "t_roamer", "A")
    put(s, "1,1", "t_body", "A")
    seq = s.board["1,2"][-1].play_seq
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert calls == []
    assert s.board["2,2"][-1].play_seq == seq           # its place in the play order stays
    assert not any(e["e"] == "place" for e in s.events)
    assert any(e["e"] == "roam" and e["cr"] == "1,2" and e["to"] == "2,2" for e in s.events)


def test_arriving_next_to_a_hippopotamus_sets_it_off():
    s = state()
    put(s, "1,2", "t_dusk", "A")
    put(s, "2,2", "t_roam_cat", "A")
    s.board["2,2"][-1].strength_counter = -2            # strength 3: within the Hippo's reach
    put(s, "3,1", "hippopotamus", "B")
    rules.apply_action(s, RoamAction("2,2", ("cr", "2,1")))
    assert "2,1" not in s.board and "t_roam_cat" in s.remove_pile


def test_covering_by_roaming_sets_off_spikes():
    s = state()
    put(s, "1,2", "t_roam_apex", "A")                   # an Apex lands on the porcupine...
    s.board["1,2"][-1].strength_counter = 1             # 8 beats 7
    put(s, "2,2", "porcupine", "B")
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert ids(s, "2,2") == ["porcupine"]               # ...and is removed by the spikes before it can eat
    assert "t_roam_apex" in s.remove_pile


def test_king_theron_watches_a_roaming_cat_cover():
    s = state()
    put(s, "1,1", "king_theron", "A")
    put(s, "1,2", "t_roam_cat", "A")
    put(s, "2,2", "t_body", "B")
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert ids(s, "2,2") == ["t_roam_cat"] and "t_body" in s.remove_pile


def test_an_apex_roams_only_onto_an_animal_and_eats_it():
    s = state()
    for cr in ("1,2", "2,2", "3,2"):
        put(s, cr, "t_body", "A")
    put(s, "4,2", "t_roam_apex", "A")
    put(s, "4,1", "t_dusk", "B")
    assert roams(s) == {("4,2", ("cr", "4,1")), ("4,2", ("cr", "3,2"))}   # no empty crossroad, no den
    rules.apply_action(s, RoamAction("4,2", ("cr", "4,1")))
    assert ids(s, "4,1") == ["t_roam_apex"] and "t_dusk" in s.remove_pile


def test_roam_hooks_fire_for_the_roamer_and_its_friends(monkeypatch):
    seen = []
    monkeypatch.setitem(effects.EFFECTS, "t_roamer",
                        {"on_roam": lambda st, u, cr, ev: seen.append(("self", cr, ev["from"], ev["onto_enemy"]))})
    monkeypatch.setitem(effects.EFFECTS, "t_body",
                        {"on_friendly_roam": lambda st, w, r, ev: seen.append(("friend", w.owner, ev["covered"]))})
    s = state()
    put(s, "1,1", "t_body", "A")
    put(s, "1,3", "t_body", "B")                        # the enemy's watcher doesn't see it
    put(s, "1,2", "t_roamer", "A")
    prey = put(s, "2,2", "t_dusk", "B")
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert sorted(seen) == [("friend", "A", prey.iid), ("self", "2,2", "1,2", True)]


def test_a_free_roam_spends_no_action_and_keeps_the_turn_open():
    s = state(hands={"A": ["t_body", "t_body"], "B": ["t_body"]})
    put(s, "1,2", "t_roamer", "A")
    s.effect_stack.append({"op": "grant_free_roam", "player": "A", "n": 1, "by_card": "t_roamer"})
    effects.resolve(s)
    rules.apply_action(s, PlaceAction("t_body", ("cr", "1,1")))
    rules.apply_action(s, PlaceAction("t_body", ("cr", "1,3")))
    assert s.current == "A"                             # both actions spent, the free roam keeps the turn open
    legal = rules.legal_actions(s)
    assert legal and all(isinstance(a, RoamAction) for a in legal)   # only the roam is left
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert s.current == "B"


def test_a_free_roam_is_spent_before_an_action():
    s = state()
    put(s, "1,2", "t_roamer", "A")
    s.turn_flags["free_roams_A"] = 1
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert s.actions_taken_this_turn == 0 and effects.free_roams_left(s, "A") == 0


def test_roam_is_serialisable_and_replays():
    a = RoamAction("1,2", ("hq", "B"))
    assert action_from_dict(a.to_dict()) == a and a.is_hq_capture
    s = state(hands={"A": ["t_body"]})
    put(s, "1,2", "t_roamer", "A")
    start = GameState.from_dict(s.to_dict(), cards=CARDS)
    log = [RoamAction("1,2", ("cr", "2,2")).to_dict(), PlaceAction("t_body", ("cr", "1,2")).to_dict()]
    for d in log:
        rules.apply_logged(s, d)
    for d in log:
        rules.apply_logged(start, d)
    assert start.to_dict() == s.to_dict()
    assert start.board["2,2"][-1].card_id == "t_roamer"


def test_a_free_roam_alone_is_not_an_idle_turn():
    s = state(hands={"B": ["t_body"]})
    put(s, "1,2", "t_roamer", "A")
    s.turn_flags["free_roams_A"] = 1
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert s.current == "B" and s.idle_turns == 0        # nothing else to do: the turn ended, and A had acted


# ===================================================================== Reach N

def test_reach_lands_up_to_n_crossroads_from_a_connected_unit_jumping_over_occupants():
    s = state(hands={"A": ["t_reach2"]})
    put(s, "1,2", "t_body", "A")
    put(s, "2,2", "t_body", "B")                        # in the way: jumped over
    targets = {a.target[1] for a in rules.legal_actions(s) if isinstance(a, PlaceAction)}
    assert "3,2" in targets                             # two steps from 1,2, over the enemy
    assert "4,2" not in targets                         # three steps
    assert "2,2" not in targets                         # 3 can't cover the 4 it jumps


def test_reach_launches_from_the_den():
    s = state(hands={"A": ["t_reach2"]})
    targets = {a.target[1] for a in rules.legal_actions(s) if isinstance(a, PlaceAction)}
    assert targets == {"1,1", "1,2", "1,3", "2,1", "2,2", "2,3"}


def test_reach_does_not_launch_from_a_stranded_unit():
    s = state(hands={"A": ["t_reach2"]})
    put(s, "3,2", "t_body", "A")                        # not connected to the den
    targets = {a.target[1] for a in rules.legal_actions(s) if isinstance(a, PlaceAction)}
    assert "4,2" not in targets and "3,1" not in targets


def test_reach_never_captures_a_den():
    s = state(hands={"A": ["t_reach3"]})
    put(s, "1,2", "t_body", "A")
    put(s, "2,2", "t_body", "A")
    acts = [a for a in rules.legal_actions(s) if isinstance(a, PlaceAction) and a.card_id == "t_reach3"]
    assert ("cr", "4,2") in {a.target for a in acts}     # it lands next to the den...
    assert not any(a.is_hq_capture for a in acts)        # ...but can't take it


def test_reach_covering_still_needs_greater_strength():
    s = state(hands={"A": ["t_reach3"]})                # strength 6
    put(s, "3,1", "t_body", "B")                        # 4: it covers
    put(s, "3,3", "porcupine", "B")                     # 7: it can't
    targets = {a.target[1] for a in rules.legal_actions(s) if isinstance(a, PlaceAction)}
    assert "3,1" in targets and "3,3" not in targets and "3,2" in targets


def test_reach_works_for_an_extra_placement_too():
    s = state(hands={"A": ["calib_extra_2", "t_reach2"]})
    rules.apply_action(s, PlaceAction("calib_extra_2", ("cr", "1,2")))
    assert s.pending and s.pending["mode"] == "place"
    assert {"card_id": "t_reach2", "target": ["cr", "3,2"]} in s.pending["placements"]


def test_reach_needs_its_number():
    from animal_kingdom.engine.cards import CardDataError
    with pytest.raises(CardDataError):
        cards_with({"id": "t_bad", "base_strength": 3, "keywords": ["Reach"]})
    with pytest.raises(CardDataError):
        cards_with({"id": "t_bad", "base_strength": 3, "keywords": ["Reach"], "reach": 1})


# ===================================================================== Poison

def _cover_poison(s, coverer="t_body", cr="2,2"):
    """B covers A's Poison animal on B's turn; returns the coverer."""
    rules.apply_action(s, PlaceAction(coverer, ("cr", cr)))
    return s.board[cr][-1]


def _poisoned_board(hand=("t_body",)):
    s = state(current="B", hands={"A": ["t_dusk"], "B": list(hand) + ["t_dusk"]})   # spare cards keep both turns open
    put(s, "1,2", "t_body", "A")
    poison = put(s, "2,2", "t_poison", "A")
    put(s, "4,2", "t_body", "B"); put(s, "3,2", "t_body", "B")
    return s, poison


def test_poison_removes_the_coverer_at_the_start_of_its_controllers_next_turn():
    s, poison = _poisoned_board()
    coverer = _cover_poison(s)
    assert s.board["2,2"][-1] is coverer and s.current == "B"   # it has the rest of its turn
    end_turn(s)                                         # A's turn starts: the poison resolves
    assert s.current == "A" and ids(s, "2,2") == ["t_poison"]   # the Poison animal resurfaces
    assert "t_body" in s.remove_pile


def test_poison_works_every_time():
    s, poison = _poisoned_board(hand=("t_body", "t_body"))
    _cover_poison(s)
    end_turn(s)
    assert ids(s, "2,2") == ["t_poison"]
    end_turn(s)                                         # A passes; B covers again
    _cover_poison(s)
    end_turn(s)
    assert ids(s, "2,2") == ["t_poison"] and s.remove_pile.count("t_body") == 2


def test_poison_resolves_even_if_the_poison_animal_is_gone():
    s, poison = _poisoned_board()
    coverer = _cover_poison(s)
    effects._remove_specific(s, "2,2", poison, by_player="B")   # gone from under the coverer
    end_turn(s)
    assert "2,2" not in s.board and coverer.card_id in s.remove_pile


def test_poison_is_cancelled_if_the_coverer_leaves_the_board_first():
    s, poison = _poisoned_board()
    coverer = _cover_poison(s)
    effects._bounce(s, "2,2", coverer)                  # back to hand: a new card, a clean one
    end_turn(s)
    assert ids(s, "2,2") == ["t_poison"] and not s.scheduled
    assert any(u.card_id == "t_body" for u in s.hands["B"])


def test_armor_resists_the_poison():
    s, poison = _poisoned_board(hand=("methuselah",))
    coverer = _cover_poison(s, "methuselah")
    end_turn(s)
    assert s.board["2,2"][-1] is coverer


def test_an_apex_landing_on_poison_eats_it_and_is_poisoned():
    s, poison = _poisoned_board(hand=("tiger",))
    tiger = _cover_poison(s, "tiger")
    assert ids(s, "2,2") == ["tiger"] and "t_poison" in s.remove_pile   # it still eats
    end_turn(s)
    assert "2,2" not in s.board and "tiger" in s.remove_pile


def test_a_friendly_cover_does_not_set_off_poison():
    s = state(hands={"A": ["t_body"]})
    put(s, "1,2", "t_poison", "A")
    rules.apply_action(s, PlaceAction("t_body", ("cr", "1,2")))
    assert not s.scheduled


def test_poison_reaches_a_buried_coverer():
    s, poison = _poisoned_board(hand=("t_body", "t_reach3"))
    coverer = _cover_poison(s)
    rules.apply_action(s, PlaceAction("t_reach3", ("cr", "2,2")))   # B buries its own coverer
    end_turn(s)
    assert ids(s, "2,2") == ["t_poison", "t_reach3"]    # the buried coverer is removed from under it


def test_covering_poison_by_roaming_sets_it_off():
    s = state(hands={"B": ["t_body"]})
    put(s, "1,2", "t_poison", "B")
    put(s, "1,1", "t_roamer", "A")
    rules.apply_action(s, RoamAction("1,1", ("cr", "1,2")))
    end_turn(s)                                         # B's turn starts: the roamer goes
    assert ids(s, "1,2") == ["t_poison"]


# ===================================================================== Dawn and Dusk

def _record(order, tag):
    return lambda st, u, cr: order.append(tag)


def test_dusk_effects_resolve_in_the_order_their_animals_were_played(monkeypatch):
    order = []
    monkeypatch.setitem(effects.EFFECTS, "t_dusk", {"on_end_of_turn": _record(order, "first")})
    monkeypatch.setitem(effects.EFFECTS, "t_dusk2", {"on_end_of_turn": _record(order, "second")})
    s = state()
    put(s, "3,3", "t_dusk", "A")                        # played first, on the crossroad that sorts last
    put(s, "1,1", "t_dusk2", "A")
    end_turn(s)
    assert order == ["first", "second"]


def test_dawn_effects_resolve_in_play_order_each_in_full_before_the_next(monkeypatch):
    order = []

    def first(st, u, cr):
        order.append("first")
        st.effect_stack.append({"op": "draw", "player": u.owner, "n": 1})   # a step it pushes resolves before the next

    def second(st, u, cr):
        order.append(("second", len(st.hands[u.owner])))

    monkeypatch.setitem(effects.EFFECTS, "t_dusk", {"on_start_of_turn": first})
    monkeypatch.setitem(effects.EFFECTS, "t_dusk2", {"on_start_of_turn": second})
    s = state(current="B", decks={"A": ["t_body"] * 3, "B": []})
    put(s, "3,3", "t_dusk", "A")
    put(s, "1,1", "t_dusk2", "A")
    end_turn(s)
    assert order == ["first", ("second", 1)]


def test_a_dusk_animal_removed_by_an_earlier_dusk_effect_does_nothing(monkeypatch):
    order = []

    def killer(st, u, cr):
        order.append("killer")
        st.effect_stack.append({"op": "remove_iid", "iid": st.board["1,1"][-1].iid, "by_player": u.owner,
                                "by_effect": True, "source_iid": None})

    monkeypatch.setitem(effects.EFFECTS, "t_dusk", {"on_end_of_turn": killer})
    monkeypatch.setitem(effects.EFFECTS, "t_dusk2", {"on_end_of_turn": _record(order, "victim")})
    s = state()
    put(s, "3,3", "t_dusk", "A")
    put(s, "1,1", "t_dusk2", "A")
    end_turn(s)
    assert order == ["killer"]


def test_play_order_survives_a_save_and_load():
    s = state()
    u = put(s, "1,1", "t_dusk", "A")
    loaded = GameState.from_dict(s.to_dict(), cards=CARDS)
    assert loaded.board["1,1"][-1].play_seq == u.play_seq and loaded.play_seq == s.play_seq
    assert s.clone().board["1,1"][-1].play_seq == u.play_seq


def test_existing_dusk_cards_still_fire():
    s = state(food={"A": 0, "B": 0})
    put(s, "1,1", "worker_wasp", "A")
    put(s, "1,3", "methuselah", "A")
    end_turn(s)
    assert s.food["A"] == s.config.worker_wasp_food + s.config.methuselah_food


# ===================================================================== bots (a sanity smoke, no balance claim)

def _keyword_decks():
    """Two premade decks with commons swapped for the test-only Roam, Reach and Poison cards."""
    from animal_kingdom.decks import load_premade_deck

    def swap(slug, new):
        out, k = [], 0
        for c in load_premade_deck(slug):
            if k < len(new) and CARDS[c].rarity == "common":
                out.append(new[k]); k += 1
            else:
                out.append(c)
        return out
    return (swap("canines", ["t_roamer", "t_roam_apex", "t_poison", "t_reach2", "t_roam_cat", "t_reach3"] * 2),
            swap("cats", ["t_roamer", "t_poison", "t_reach3", "t_roam_armor"] * 2))


def _play(kinds, seed):
    from animal_kingdom.engine.state import new_game
    from animal_kingdom.sim.runner import make_bot
    da, db = _keyword_decks()
    s = new_game(da, db, seed, cards=CARDS)
    bots = {"A": make_bot(kinds[0], seed), "B": make_bot(kinds[1], seed + 100)}
    chosen = []
    while rules.is_terminal(s) is None:
        p = s.player_to_act()
        a = bots[p].choose(s.view_for(p), rules.legal_actions(s), s)
        chosen.append(a)
        rules.apply_action(s, a)
    return chosen


def test_greedy_bots_see_and_choose_roams():
    chosen = [a for seed in range(3) for a in _play(("greedy", "greedy"), seed)]
    assert any(isinstance(a, RoamAction) for a in chosen)
    assert any(isinstance(a, PlaceAction) and CARDS[a.card_id].reach for a in chosen)


@pytest.mark.slow
@pytest.mark.parametrize("kind", ["turn", "referee"])
def test_search_bots_finish_games_with_the_new_keywords(kind):
    assert _play((kind, kind), 0)
