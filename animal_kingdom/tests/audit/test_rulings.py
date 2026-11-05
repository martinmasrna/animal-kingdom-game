"""Rulings audit (2026-11-05): does the engine do what every ruling in docs/rules/rulings.md says?

One test (or more) per ruling bullet, named `test_<section>__<ruling>`, in the order the document gives them. Each
assertion is read off the ruling's words, never off the effect code; where a ruling names a card, that card is used,
where it is general, the simplest cards that reach it (the vanilla bodies v0..v9 and v_roam are test-only cards).

Map A (the test fixture): a 4x3 grid, A's den fronts column 1 ("1,1" "1,2" "1,3"), B's column 4; orthogonal
neighbours, so "2,2" neighbours "1,2", "3,2", "2,1", "2,3". Regions: R1 = 1,1 2,1 1,2 2,2; R3 = 3,1 4,1 3,2 4,2 (10
food each); R2 = 2,1 3,1 2,2 3,2 (20).

The record, one line per ruling, is knowledge/audit/rulings-2026-11-05.md.
"""

from __future__ import annotations

import json

import pytest

from animal_kingdom.engine import effects, rules
from animal_kingdom.engine.actions import SKIP, ChoiceAction, DrawAction, PassAction, PlaceAction, RoamAction
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.resources import load_bundled_json
from animal_kingdom.engine.state import GameState
from animal_kingdom.engine.strength import effective_strength

from .._helpers import cards_with, hand_ids, make_state, place_targets, put

CARDS = cards_with(*[{"id": f"v{n}", "base_strength": n} for n in range(0, 10)],
                   {"id": "v_roam", "base_strength": 4, "keywords": ["Roam"]},
                   {"id": "v_roam1", "base_strength": 1, "keywords": ["Roam"]},
                   {"id": "v_fishrodent", "base_strength": 2, "tags": ["Fish", "Rodent"]},
                   {"id": "v_queen", "base_strength": 2, "tags": ["Queen"]},
                   {"id": "v_canine", "base_strength": 2, "tags": ["Canine"]},
                   {"id": "v_hoofed", "base_strength": 3, "tags": ["Hoofed"]},
                   {"id": "v_hoofed_roam", "base_strength": 3, "tags": ["Hoofed"], "keywords": ["Roam"]},
                   {"id": "v_cat_roam", "base_strength": 5, "tags": ["Cat"], "keywords": ["Roam"]})


def st(**kw) -> GameState:
    kw.setdefault("decks", {"A": ["v1"] * 8, "B": ["v1"] * 8})
    return make_state(cards=CARDS, **kw)


def strength(s, u):
    return effective_strength(s, u)


def end_turn(s):
    """End the turn of whoever is to move (a pass; the idle count is reset so two passes don't end the game)."""
    s.idle_turns = 0
    rules.apply_action(s, PassAction())


def choose(s, option):
    assert s.pending is not None and option in s.pending["options"], (option, s.pending)
    rules.apply_action(s, ChoiceAction(option))


def options(s):
    return set(s.pending["options"]) if s.pending and s.pending["mode"] == "choice" else set()


def placements(s):
    """The (card, crossroad) pairs a pending extra play offers."""
    if not s.pending or s.pending["mode"] != "place":
        return set()
    return {(p["card_id"], p["target"][1]) for p in s.pending["placements"]}


def play(s, card_id, cr):
    rules.apply_action(s, PlaceAction(card_id, ("cr", cr)))


def legal(s, action):
    return action in rules.legal_actions(s)


def tops(s, card_id, owner=None):
    return [cr for cr, stack in s.board.items() if stack and stack[-1].card_id == card_id
            and (owner is None or stack[-1].owner == owner)]


def ids(s, cr):
    return [u.card_id for u in s.board.get(cr, [])]


# ============================================================================== Card identity and tags

def test_identity__every_collectible_card_name_is_unique():
    raw = load_bundled_json("cards.json")["cards"]
    names = [c["name"] for c in raw if c.get("status") == "collectible"]
    assert len(names) == len(set(names))


def test_identity__a_card_belongs_to_no_deck_and_may_sit_in_several_lists_or_none():
    raw = load_bundled_json("cards.json")["cards"]
    assert not any("deck" in c for c in raw)
    decks = load_bundled_json("decklists.json")["decks"]
    count = {}
    for d in decks:
        for cid in set(d.get("cards", [])):
            count[cid] = count.get(cid, 0) + 1
    collectible = [c["id"] for c in raw if c.get("status") == "collectible"]
    assert any(count.get(c, 0) > 1 for c in collectible) and any(count.get(c, 0) == 0 for c in collectible)


def test_identity__a_colony_queen_needs_both_tags():
    # Termite King: "draw a card for each Colony Queen you control". Queen Ant is Queen+Colony; v_queen only Queen;
    # Worker Ant only Colony.
    s = st(hands={"A": ["termite_king"]})
    put(s, "1,1", "queen_ant", "A")
    put(s, "1,3", "v_queen", "A")
    put(s, "2,1", "worker_ant", "A")
    play(s, "termite_king", "1,2")
    assert len(s.hands["A"]) == 1


def test_identity__a_card_with_several_families_counts_for_each():
    # v_fishrodent is Fish and Rodent: the Tuna ("+1 for each other Fish") and the legendary Rat ("4 food for each
    # other Rodent") both count it.
    s = st(hands={"A": ["rat_legend"]})
    put(s, "1,1", "v_fishrodent", "A")
    tuna = put(s, "3,3", "tuna", "A")
    assert strength(s, tuna) == CARDS["tuna"].base_strength + 1
    play(s, "rat_legend", "1,2")
    assert s.food["A"] == 4


def test_identity__tagless_cards_are_allowed():
    assert CARDS["dolphin"].tags == () or list(CARDS["dolphin"].tags) == []
    s = st(hands={"A": ["dolphin"]})
    play(s, "dolphin", "1,2")
    assert tops(s, "dolphin") == ["1,2"]


def test_identity__eggs_are_counted_by_unit_queries():
    s = st(hands={"A": ["worker_ant"]})
    put(s, "1,1", "snake_egg", "A")
    play(s, "worker_ant", "1,2")                # 2 animals: the Egg and the Ant
    assert s.food["A"] == 6


def test_identity__eggs_are_hit_by_unit_triggers():
    s = st(hands={"A": ["snake_egg"]})
    put(s, "1,1", "v1", "A"); put(s, "2,1", "v1", "A")
    put(s, "3,2", "hippopotamus", "B")          # "When an enemy of strength 4 or less is placed next to this, remove it"
    put(s, "2,2", "v1", "A")
    play(s, "snake_egg", "3,1")
    assert s.top_unit("3,1") is None


def test_identity__eggs_can_capture_a_den():
    s = st(hands={"A": ["snake_egg"]})
    for cr in ("1,2", "2,2", "3,2", "4,2"):
        put(s, cr, "v1", "A")
    rules.apply_action(s, PlaceAction("snake_egg", ("hq", "B")))
    assert s.result is not None and s.result.winner == "A"


# ============================================================================== Placement and actions

def test_placement__eon_that_would_shuffle_back_at_zero_is_removed_instead():
    s = st()
    put(s, "1,2", "anaconda_legend", "A")
    s.card_strength_counters["A"] = {"anaconda_legend": -9}   # nine trips round: 1 now, it would go back at 0
    end_turn(s)
    assert s.top_unit("1,2") is None
    assert "anaconda_legend" not in s.decks["A"] and "anaconda_legend" in s.pile_cards_of("A")


def test_placement__eon_above_zero_shuffles_back():
    s = st()
    put(s, "1,2", "anaconda_legend", "A")
    end_turn(s)
    assert "anaconda_legend" in s.decks["A"] or "anaconda_legend" in hand_ids(s, "A")


def test_placement__a_placed_animal_is_not_played_hare_does_not_count_it():
    # Sunfish places a Baby Fish; the Hare counts animals played from hand: Sunfish + Hare = 2, not 3.
    s = st(hands={"A": ["sunfish", "hare"]}, decks={"A": ["v1"] * 4, "B": ["v1"] * 4})
    play(s, "sunfish", "1,2")
    assert len(tops(s, "baby_fish")) == 1
    play(s, "hare", "1,1") if s.top_unit("1,1") is None else play(s, "hare", "1,3")
    assert "v1" not in hand_ids(s, "A")


def test_placement__a_placed_animal_sets_off_whenever_you_place_reactions():
    # The Worker Wasp ("Whenever you place a Colony animal, gain 3 food") pays for a Young Ant the Queen Ant lays.
    s = st()
    put(s, "1,1", "worker_wasp", "A")
    put(s, "1,2", "queen_ant", "A")
    end_turn(s)                                 # Dusk: a Young Ant on an empty neighbour
    assert len(tops(s, "young_ant")) == 1
    assert s.food["A"] == 3


def test_placement__a_placed_animal_is_seen_by_traps_beside_it():
    s = st(hands={"A": ["sunfish"]})
    put(s, "1,1", "v1", "A"); put(s, "2,1", "v1", "A"); put(s, "1,3", "v1", "A")
    put(s, "3,2", "hippopotamus", "B")
    play(s, "sunfish", "1,2")                   # its one empty neighbour is 2,2, next to the Hippopotamus
    assert s.top_unit("2,2") is None and "baby_fish" in s.remove_pile


def test_placement__a_placed_animal_does_not_roar():
    # Scarlett places Poppy and Rusty; Vesper is placed: no Roar. Kitten has a Roar ("draw a common animal"): a
    # placed Kitten would draw. Here: Vesper placed on a coverer, its owner draws nothing.
    s = st(hands={"B": ["v5"]}, current="B", decks={"A": ["hornet_legend", "v1", "v1"], "B": ["v1"] * 4})
    put(s, "1,2", "worker_ant", "A")
    for cr in ("4,2", "3,2", "2,2"):
        put(s, cr, "v1", "B")
    play(s, "v5", "1,2")
    assert s.top_unit("1,2").card_id == "hornet_legend"
    assert hand_ids(s, "A") == [] and s.decks["A"] == ["v1", "v1"]


def test_placement__extra_placement_is_a_full_placement_that_costs_no_action():
    # Ocelot: "if you control another Cat, play another Cat". Connection and covering strength still hold.
    s = st(hands={"A": ["ocelot", "lion", "lion"]})
    put(s, "1,1", "v_cat_roam", "A")
    put(s, "2,2", "lion", "B")                  # 7: a Lion can't cover it
    play(s, "ocelot", "1,2")
    offered = {cr for c, cr in placements(s)}
    assert "2,2" not in offered and "3,3" not in offered and "2,1" in offered
    rules.apply_action(s, PlaceAction("lion", ("cr", "2,1")))
    assert s.actions_taken_this_turn == 1


def test_placement__extra_placements_chain():
    s = st(hands={"A": ["ocelot", "ocelot", "lion"]})
    put(s, "1,1", "lion", "A")
    play(s, "ocelot", "1,2")
    rules.apply_action(s, PlaceAction("ocelot", ("cr", "1,3")))
    assert ("lion", "2,3") in placements(s)
    rules.apply_action(s, PlaceAction("lion", ("cr", "2,3")))
    assert s.actions_taken_this_turn == 1 and s.hands["A"] == []


def test_placement__extra_placement_is_from_hand_only_and_fizzles_when_nothing_qualifies():
    s = st(hands={"A": ["ocelot"]}, decks={"A": ["lion"] * 3, "B": ["v1"] * 3})
    put(s, "1,1", "lion", "A")
    play(s, "ocelot", "1,2")
    assert s.pending is None and s.decks["A"] == ["lion"] * 3


def test_placement__cant_beats_can():
    # Bison: "Can't be covered while grazing"; Hercules Beetle: "Can cover animals of any strength".
    s = st(hands={"A": ["hercules_beetle"]})
    put(s, "1,2", "v1", "A"); put(s, "2,2", "v1", "A")
    for cr in ("3,1", "4,1", "4,2"):
        put(s, cr, "v1", "B")
    put(s, "3,2", "bison", "B")                 # B holds R3: the Bison grazes
    put(s, "2,3", "v1", "A"); put(s, "3,3", "lion", "B")
    t = place_targets(s)
    assert "3,3" in t                           # the Beetle covers a Lion
    assert "3,2" not in t                       # but not a grazing Bison


def test_placement__next_to_the_opponents_den_means_its_front_crossroads():
    s = st(hands={"A": ["cheetah", "cheetah"]}, decks={"A": ["v1"] * 6, "B": []})
    for cr in ("1,2", "2,2", "3,2"):
        put(s, cr, "v1", "A")
    play(s, "cheetah", "3,3")                   # not a den front
    assert hand_ids(s, "A") == ["cheetah"]
    play(s, "cheetah", "4,2")                   # B's den front
    assert hand_ids(s, "A") == ["v1", "v1"]


def test_placement__sardine_fills_adjacent_empty_crossroads_from_hand_and_deck_leftovers_stay():
    s = st(hands={"A": ["sardine", "sardine", "sardine"]}, decks={"A": ["sardine", "sardine", "v1"], "B": []})
    put(s, "1,1", "v1", "A")                    # 1,2's empty neighbours: 1,3 and 2,2
    play(s, "sardine", "1,2")
    assert sorted(cr for cr in tops(s, "sardine")) == ["1,2", "1,3", "2,2"]
    left = hand_ids(s, "A").count("sardine") + s.decks["A"].count("sardine")
    assert left == 2                            # 5 copies besides the one played, 2 placed
    assert "v1" in s.decks["A"]


def test_placement__sardine_copies_do_not_roar():
    s = st(hands={"A": ["sardine", "sardine"]}, decks={"A": ["sardine"] * 4, "B": []})
    put(s, "1,1", "v1", "A"); put(s, "1,3", "v1", "A")
    play(s, "sardine", "1,2")                   # one empty neighbour, 2,2: if its copy roared, 2,1 2,3 3,2 would fill
    assert sorted(tops(s, "sardine")) == ["1,2", "2,2"]


def test_placement__sardine_copies_are_seen_by_traps():
    s = st(hands={"A": ["sardine", "sardine"]}, decks={"A": [], "B": []})
    put(s, "1,1", "v1", "A"); put(s, "1,3", "v1", "A")
    put(s, "3,2", "hippopotamus", "B")
    play(s, "sardine", "1,2")
    assert s.top_unit("2,2") is None


def test_placement__legendary_sardine_doubles_its_adjacent_fish_wherever_animals_are_counted():
    # Worker Ant: "gain 3 food for each animal you control": Sardine legend (2) + an adjacent Tuna (2) + the Ant (1).
    s = st(hands={"A": ["worker_ant"]})
    put(s, "1,1", "sardine_legend", "A")
    put(s, "1,2", "tuna", "A")
    play(s, "worker_ant", "1,3")
    assert s.food["A"] == 15


def test_placement__legendary_sardine_doubles_only_while_on_top():
    s = st(hands={"A": ["worker_ant"]})
    put(s, "1,1", "sardine_legend", "A")
    put(s, "1,1", "v5", "B")
    put(s, "1,2", "tuna", "A")
    play(s, "worker_ant", "1,3")                # the Tuna and the Ant
    assert s.food["A"] == 6


def test_placement__recurring_timed_trigger_fires_the_turn_it_was_played_and_only_on_the_owners_turn():
    s = st(hands={"A": ["tortoise_legend"]})    # Azamandulai: "Dusk: gain 5 food"
    play(s, "tortoise_legend", "1,2")
    end_turn(s)
    assert s.food["A"] == 5
    end_turn(s)                                 # B's Dusk: nothing for A
    assert s.food["A"] == 5
    end_turn(s)
    assert s.food["A"] == 10


# ============================================================================== Drawing and hidden information

def test_drawing__a_filtered_draw_takes_a_matching_card_without_reshuffling():
    s = st(hands={"A": ["mouse"]}, decks={"A": ["v1", "squirrel", "v2", "v3"], "B": []})
    play(s, "mouse", "1,2")
    assert hand_ids(s, "A") == ["squirrel"] and s.decks["A"] == ["v1", "v2", "v3"]


def test_drawing__a_filtered_draw_is_random_among_the_matches():
    seen = set()
    for seed in range(30):
        s = st(hands={"A": ["mouse"]}, decks={"A": ["squirrel", "v1", "chipmunk", "v2"], "B": []})
        s.rng.seed(seed)
        play(s, "mouse", "1,2")
        seen.add(hand_ids(s, "A")[0])
    assert seen == {"squirrel", "chipmunk"}


def test_drawing__a_filtered_draw_fizzles_with_no_match():
    s = st(hands={"A": ["mouse"]}, decks={"A": ["v1", "v2"], "B": []})
    play(s, "mouse", "1,2")
    assert hand_ids(s, "A") == [] and s.decks["A"] == ["v1", "v2"]


def test_drawing__the_designed_pair_fetches_its_sibling_from_the_deck():
    s = st(hands={"A": ["lion_legend"]}, decks={"A": ["v1", "lion_legend_2", "v2"], "B": []})
    play(s, "lion_legend", "1,2")
    if s.pending:
        rules.apply_action(s, PlaceAction("lion_legend_2", ("cr", "1,1")))
    assert tops(s, "lion_legend_2") and "lion_legend_2" not in s.decks["A"]


def _condor(own_deck, opp_deck):
    s = st(hands={"A": ["andean_condor"]}, decks={"A": list(own_deck), "B": list(opp_deck)})
    play(s, "andean_condor", "1,2")
    return s


def test_drawing__andean_condor_draws_only_when_strictly_greater():
    assert hand_ids(_condor(["v7"], ["v5"]), "A") == ["v7"]
    s = _condor(["v7"], ["v7"])
    assert hand_ids(s, "A") == [] and s.decks["A"] == ["v7"] and s.decks["B"] == ["v7"]


def test_drawing__andean_condor_counts_dynamic_strength_as_zero_and_an_empty_enemy_deck_as_zero():
    assert hand_ids(_condor(["v1"], []), "A") == ["v1"]
    assert hand_ids(_condor(["egg_eater"], ["v0"]), "A") == []


def test_drawing__andean_condor_with_an_empty_own_deck_fizzles():
    s = _condor([], ["v1"])
    assert hand_ids(s, "A") == [] and s.decks["B"] == ["v1"]


def test_drawing__nothing_else_reveals_a_hand():
    s = st(hands={"A": ["v1"], "B": ["v2"]})
    put(s, "1,2", "lion", "A")
    assert not s.hand_revealed("A") and not s.hand_revealed("B")


# ============================================================================== Remove Pile, returns and shuffles

def test_pile__raccoon_takes_only_its_owners_cards_from_the_shared_pile():
    s = st(hands={"A": ["raccoon"]})
    s.pile_add("v5", "B")
    s.pile_add("v3", "A")
    play(s, "raccoon", "1,2")
    if s.pending:
        assert options(s) <= {"v3"} | {SKIP}
        choose(s, "v3")
    assert hand_ids(s, "A") == ["v3"] and s.pile_cards_of("B") == ["v5"]


def test_pile__grimm_takes_from_the_opponents_cards_in_the_pile():
    s = st(hands={"A": ["raven_legend"]})
    s.pile_add("v3", "A")
    s.pile_add("v5", "B"); s.pile_add("v6", "B")
    play(s, "raven_legend", "1,2")
    while s.pending:
        choose(s, sorted(o for o in s.pending["options"] if o != SKIP)[0])
    assert sorted(hand_ids(s, "A")) == ["v5", "v6"] and s.pile_cards_of("A") == ["v3"]


def test_pile__a_card_removed_from_hand_is_a_remove_and_fires_remove_triggers():
    # Golden Egg: "When you draw this, remove it and draw 2 cards"; Egg Eater: "+2 strength for each removed Egg".
    s = st(decks={"A": ["v1", "v1", "golden_egg"], "B": []})
    ee = put(s, "3,3", "egg_eater", "A")
    rules.apply_action(s, DrawAction())
    assert "golden_egg" in s.pile_cards_of("A")
    assert strength(s, ee) == 2


def test_pile__fall_is_a_real_removal_a_replaced_cockroach_counts_as_removed():
    s = st()
    put(s, "2,2", "hyena", "A")                 # "Dusk: gain 3 food for each animal removed this turn"
    put(s, "1,2", "cockroach", "A")
    effects.remove_top(s, "1,2", by_player="B")
    resolve_all(s)
    assert s.top_unit("1,2").card_id == "cockroach"
    end_turn(s)
    assert s.food["A"] == 3


def resolve_all(s):
    effects.resolve(s)


@pytest.mark.xfail(strict=True, reason=(
    "Two readings of 'Fall ... is a real removal, then the effect ... It is a fresh Cockroach'. A: the removed card "
    "reaches its owner's Remove Pile and a fresh one takes its place. B (the engine): the card itself comes back, a new "
    "instance, and nothing reaches the Remove Pile. Also recorded by the City audit (test_city.py)."))
def test_pile__a_fallen_cockroach_reaches_the_remove_pile():
    s = st()
    put(s, "1,2", "cockroach", "A")
    effects.remove_top(s, "1,2", by_player="B"); resolve_all(s)
    assert s.pile_cards_of("A") == ["cockroach"]


def test_pile__a_cockroach_that_comes_back_is_not_placed_so_traps_do_not_see_it():
    s = st()
    put(s, "2,2", "hippopotamus", "B")          # would remove an enemy of strength <= 4 placed next to it
    put(s, "1,2", "cockroach", "A")
    effects.remove_top(s, "1,2", by_player="B")
    resolve_all(s)
    assert s.top_unit("1,2") is not None and s.top_unit("1,2").card_id == "cockroach"


def test_pile__the_new_cockroach_stands_at_the_same_height_in_the_stack():
    s = st()
    put(s, "3,2", "cockroach", "A")
    put(s, "3,2", "v5", "B")                    # on top of it
    low = s.board["3,2"]
    low.insert(0, low.pop(0))
    # remove the Cockroach where it lies, under the v5: the new one takes its place there
    effects._remove_specific(s, "3,2", s.board["3,2"][0], by_player="B")
    resolve_all(s)
    assert ids(s, "3,2") == ["cockroach", "v5"]


def test_pile__a_fresh_cockroach_keeps_nothing_the_old_one_was_given():
    s = st()
    c = put(s, "1,2", "cockroach", "A")
    c.strength_counter = 3
    effects.remove_top(s, "1,2", by_player="B")
    resolve_all(s)
    new = s.top_unit("1,2")
    assert new.card_id == "cockroach" and new.iid != c.iid and strength(s, new) == 1


def test_pile__roach_king_keeps_its_growth_but_not_a_loss():
    s = st()
    k = put(s, "1,2", "cockroach_legend", "A")
    effects.remove_top(s, "1,2", by_player="B"); resolve_all(s)
    assert strength(s, s.top_unit("1,2")) == 2          # grew once
    s.top_unit("1,2").strength_counter -= 4             # shrunk below 0: it dies of it
    resolve_all(s)
    king = s.top_unit("1,2")
    assert king is not None and strength(s, king) == 3  # its growth kept (1 + 2), the loss gone


def test_pile__a_shuffle_is_one_event_per_card_raven_two():
    # Rattlesnake: "Whenever you shuffle a card, gain 1 strength".
    s = st(hands={"A": ["raven"]}, decks={"A": ["v1"] * 6, "B": []})
    r = put(s, "3,3", "rattlesnake", "A")
    play(s, "raven", "1,2")
    while s.pending:
        choose(s, [o for o in s.pending["options"] if o != SKIP][0])
    assert strength(s, r) == 2


def test_pile__skunk_bounce_is_not_a_removal():
    s = st(hands={"A": ["skunk"]})
    put(s, "2,2", "earthworm", "B")             # "Fall: draw a card and place two Worms"
    py = put(s, "3,3", "python", "A")           # "Whenever an enemy is removed, gain 1 strength"
    play(s, "skunk", "1,2")
    if s.pending:
        choose(s, "2,2")
    assert s.top_unit("2,2") is None and hand_ids(s, "B") == ["earthworm"]
    assert s.remove_pile == [] and strength(s, py) == 0 and len(s.decks["B"]) == 8


def test_pile__skunk_returned_copy_is_locked_through_its_owners_next_turn_other_copies_are_not():
    s = st(hands={"A": ["skunk"], "B": ["v3"]})
    put(s, "2,2", "v3", "B")
    play(s, "skunk", "1,2")
    if s.pending:
        choose(s, "2,2")
    end_turn(s)                                 # B's next turn
    acts = [a for a in rules.legal_actions(s) if isinstance(a, PlaceAction) and a.card_id == "v3"]
    locked = [u for u in s.hands["B"] if u.card_id == "v3" and u.locked_until_turn > s.turn_counter]
    assert len(locked) == 1 and acts            # the other copy plays
    end_turn(s); end_turn(s)                    # B's turn after that
    assert all(u.locked_until_turn <= s.turn_counter for u in s.hands["B"])


def test_pile__rat_removes_an_adjacent_enemy_of_any_strength_after_three_plays_itself_included():
    s = st(hands={"A": ["mole", "v1", "rat"]})
    put(s, "2,3", "elephant", "B")
    play(s, "mole", "1,2")
    rules.apply_action(s, PlaceAction("v1", ("cr", "1,1")))   # the Mole's extra play: two animals
    play(s, "rat", "1,3")                                     # the third, itself
    if s.pending:
        choose(s, "2,3")
    assert s.top_unit("2,3") is None


def test_pile__rat_removes_nothing_before_three_plays():
    s = st(hands={"A": ["v1", "rat"]})
    put(s, "2,3", "v1", "B")
    play(s, "v1", "1,2")
    play(s, "rat", "1,3")
    assert s.pending is None and s.top_unit("2,3") is not None


def test_pile__plague_takes_the_whole_stack_both_players_and_fires_every_fall():
    s = st(hands={"A": ["rat_legend_2"]}, decks={"A": ["v1"] * 4, "B": ["v1"] * 4})
    put(s, "2,2", "worm", "A")                  # "Fall: draw a card"
    put(s, "2,2", "worm", "B")
    put(s, "2,2", "v5", "B")
    play(s, "rat_legend_2", "1,2")
    if s.pending:
        choose(s, "2,2")
    assert s.top_unit("2,2") is None
    assert len(s.hands["A"]) == 1 and len(s.hands["B"]) == 1


# ============================================================================== Specific cards


def test_specific__value_and_food_triggers_have_no_cap_and_every_cap_flag_is_off():
    cfg = Config.default()
    flags = [f for f in vars(cfg) if f.startswith("cap_")]
    assert flags and not any(getattr(cfg, f) for f in flags)
    s = st(hands={"A": ["worker_ant", "worker_ant"]})
    put(s, "3,3", "worker_wasp", "A")           # "Whenever you place a Colony animal, gain 3 food": twice a turn too
    play(s, "worker_ant", "1,2"); f1 = s.food["A"]
    play(s, "worker_ant", "1,1")
    assert f1 == 3 + 3 * 2 and s.food["A"] == f1 + 3 + 3 * 3


# ============================================================================== Roam, Reach, Poison, Dawn and Dusk

def test_engine_reading__reach_counts_from_the_den():
    s = st(hands={"A": ["caracal"]})
    t = place_targets(s)
    assert {"2,1", "2,2", "2,3"} <= t and not ({"3,1", "3,2", "3,3"} & t)


def test_engine_reading__reach_never_takes_a_den():
    s = st(hands={"A": ["caracal"]})
    put(s, "1,2", "v1", "A"); put(s, "2,2", "v1", "A"); put(s, "3,2", "v1", "A")
    assert not any(isinstance(a, PlaceAction) and a.target[0] == "hq" for a in rules.legal_actions(s))


def test_engine_reading__roam_arrival_sets_off_a_trap_it_already_stood_next_to():
    s = st(current="B")
    put(s, "2,2", "hippopotamus", "A")
    put(s, "2,1", "v_roam", "B")                # next to the Hippopotamus already
    put(s, "3,1", "v1", "B")
    rules.apply_action(s, RoamAction("2,1", ("cr", "3,2")))   # through its pack, still next to it
    assert s.top_unit("3,2") is None


def test_engine_reading__a_cover_by_roaming_sets_off_spikes():
    s = st()
    put(s, "1,2", "wolf", "A")
    put(s, "2,2", "hedgehog", "B")              # 5 < 6
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert ids(s, "2,2") == ["hedgehog"]


def test_engine_reading__a_cover_by_roaming_sets_off_poison():
    s = st()
    put(s, "1,2", "wolf", "A")
    put(s, "2,2", "toad", "B")
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    end_turn(s)                                 # B's turn starts: the poisoned Wolf is removed
    assert ids(s, "2,2") == ["toad"]


def test_engine_reading__a_cover_by_roaming_sets_off_king_theron():
    s = st()
    put(s, "1,1", "lion_legend_3", "A")
    put(s, "1,2", "v_cat_roam", "A")
    put(s, "2,2", "v3", "B")
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert ids(s, "2,2") == ["v_cat_roam"]


def test_engine_reading__an_apex_predators_eat_happens_on_a_roam():
    s = st()
    put(s, "1,2", "orca", "A")
    put(s, "2,2", "v3", "B")
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert ids(s, "2,2") == ["orca"] and "v3" in s.remove_pile


def test_engine_reading__a_roam_does_not_roar():
    # The Coyote gives a Dolphin ("Roar: draw a card") Roam; roaming it later draws nothing.
    s = st(hands={"A": ["coyote"]})
    put(s, "1,1", "dolphin", "A")
    play(s, "coyote", "1,2")
    choose(s, "1,1"); choose(s, "2,1")
    end_turn(s); end_turn(s)
    n = len(s.hands["A"])
    rules.apply_action(s, RoamAction("2,1", ("cr", "3,1")))
    assert len(s.hands["A"]) == n


def test_engine_reading__a_cover_by_roaming_does_not_fire_a_roar_printed_as_a_placement_lynx():
    # The Lynx: "Roar: if you place this on top of an enemy, draw 2 cards". Made to roam onto an enemy, it draws nothing.
    s = st(hands={"A": ["coyote"]}, decks={"A": ["v1"] * 4, "B": ["v1"] * 4})
    put(s, "1,1", "lynx", "A")
    put(s, "2,1", "v1", "B")
    play(s, "coyote", "1,2")
    choose(s, "1,1"); choose(s, "2,1")          # the Lynx roams onto the enemy
    assert ids(s, "2,1") == ["v1", "lynx"] and s.hands["A"] == []


def test_engine_reading__a_roam_sets_off_no_whenever_you_place_reaction():
    s = st(hands={"A": ["coyote"]})
    put(s, "3,3", "worker_wasp", "A")
    put(s, "1,1", "young_ant", "A")
    play(s, "coyote", "1,2")
    choose(s, "1,1"); choose(s, "2,1")          # a Colony animal roams: no food
    assert s.food["A"] == 0


def test_engine_reading__an_apex_predator_roams_only_onto_an_animal_its_own_included_and_eats_it():
    s = st()
    put(s, "1,2", "orca", "A")
    put(s, "1,1", "v1", "A")
    put(s, "2,2", "v3", "B")
    t = {a.target for a in rules.legal_actions(s) if isinstance(a, RoamAction) and a.origin == "1,2"}
    assert ("cr", "1,1") in t and ("cr", "2,2") in t and ("cr", "1,3") not in t
    rules.apply_action(s, RoamAction("1,2", ("cr", "1,1")))
    assert ids(s, "1,1") == ["orca"]


def test_engine_reading__an_apex_predator_never_roams_onto_a_den():
    s = st()
    for cr in ("1,2", "2,2", "3,2"):
        put(s, cr, "v1", "A")
    put(s, "4,2", "orca", "A")
    assert not any(isinstance(a, RoamAction) and a.target[0] == "hq" for a in rules.legal_actions(s))


def test_engine_reading__a_roam_keeps_the_animals_place_in_the_play_order():
    s = st()
    w = put(s, "1,2", "wolf", "A")
    later = put(s, "3,3", "v1", "A")
    seq = w.play_seq
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert w.play_seq == seq and w.play_seq < later.play_seq


def test_engine_reading__a_bounced_animal_played_again_is_newly_played():
    s = st(hands={"A": ["opossum"]})
    first = put(s, "1,1", "city_spider", "A")
    later = put(s, "2,2", "v3", "A")
    play(s, "opossum", "1,2")
    if s.pending:
        choose(s, "1,1")
    end_turn(s); end_turn(s)
    play(s, "city_spider", "1,1")
    assert s.top_unit("1,1").play_seq > later.play_seq


def test_engine_reading__roaming_onto_a_den_ends_the_game_where_it_stands():
    s = st()
    for cr in ("1,2", "2,2", "3,2"):
        put(s, cr, "v1", "A")
    w = put(s, "4,2", "wolf", "A")
    rules.apply_action(s, RoamAction("4,2", ("hq", "B")))
    assert s.result is not None and s.result.winner == "A"
    assert s.top_unit("4,2") is w


def test_engine_reading__a_roam_takes_the_den_only_with_a_connected_pack_on_the_den_front():
    s = st()
    put(s, "4,2", "wolf", "A")                  # stranded
    assert not legal(s, RoamAction("4,2", ("hq", "B")))
    for cr in ("1,2", "2,2", "3,2"):
        put(s, cr, "v1", "A")
    assert legal(s, RoamAction("4,2", ("hq", "B")))


def test_engine_reading__a_player_who_can_roam_has_a_move():
    s = st(decks={"A": [], "B": ["v1"] * 4})
    put(s, "1,2", "wolf", "A")
    s.actions_taken_this_turn = 0
    assert any(isinstance(a, RoamAction) for a in rules.legal_actions(s))
    s2 = st(current="B", decks={"A": [], "B": ["v1"] * 4})
    put(s2, "1,2", "wolf", "A")
    end_turn(s2)                                # A's turn opens: A has a roam, so A doesn't pass
    assert s2.current == "A"


def test_engine_reading__a_free_roam_keeps_the_turn_open_after_two_actions():
    s = st()
    put(s, "1,1", "wolf_legend_3", "A")
    put(s, "1,2", "wolf", "A")
    rules.apply_action(s, DrawAction()); rules.apply_action(s, DrawAction())
    assert s.current == "A" and legal(s, RoamAction("1,2", ("cr", "2,2")))
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert s.current == "B"


def test_engine_reading__a_free_roam_is_spent_before_an_action():
    s = st()
    put(s, "1,1", "wolf_legend_3", "A")
    put(s, "1,2", "wolf", "A")
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert s.actions_taken_this_turn == 0


def test_engine_reading__poison_ticks_under_a_cover():
    s = st(current="B")
    put(s, "2,2", "toad", "A")
    put(s, "3,2", "v1", "B"); put(s, "4,2", "v1", "B")
    s.hands["B"] = []
    s.add_to_hand("B", "lion"); s.add_to_hand("B", "elephant")
    play(s, "lion", "2,2")                      # covers the Toad: poisoned
    play(s, "elephant", "2,2")                  # B covers its own Lion
    assert s.current == "A"                     # A's turn started: the Lion is removed from under the Elephant
    assert ids(s, "2,2") == ["toad", "elephant"]


def test_engine_reading__dawn_effects_resolve_in_play_order_one_removed_does_nothing():
    s = st()
    put(s, "2,2", "city_spider", "A")           # played first
    put(s, "2,3", "city_spider", "A")           # played second: the first removes it (4 vs the v5)
    put(s, "2,1", "v5", "A")
    put(s, "3,3", "v1", "B")                    # the second spider's prey
    end_turn(s); end_turn(s)
    assert s.top_unit("2,3") is None and s.top_unit("3,3") is not None


def test_engine_reading__delayed_payouts_resolve_before_dawn_the_sloths_food_feeds_hungry():
    s = st(hands={"A": ["sloth"]})
    play(s, "sloth", "1,2")
    end_turn(s); end_turn(s); end_turn(s)       # the Sloth pays at A's second Dawn from now
    el = put(s, "3,3", "elephant", "A")         # Hungry 5, on the board for that Dawn only
    end_turn(s)
    assert s.food["A"] == 30 - 5 and strength(s, el) == 9


# ============================================================================== A unit uncovered by a removal

def test_uncovered__a_unit_uncovered_by_a_removal_does_not_react_to_it():
    # Found in play: a Tiger ate the Grizzly covering Queen Adira and she drew a card.
    s = st(hands={"A": ["tiger"]}, decks={"A": ["v1"] * 4, "B": ["v1"] * 4})
    put(s, "1,2", "lion_legend_4", "A")
    put(s, "1,2", "grizzly_bear", "B")
    s.board["1,2"][-1].strength_counter = -2    # a 6: the Tiger (7) covers it
    put(s, "1,1", "lion", "A")
    play(s, "tiger", "1,2")
    assert s.top_unit("1,2").card_id == "tiger"
    assert hand_ids(s, "A") == []


# ============================================================================== The launch decks: keywords

def test_launch_kw__hungry_with_too_little_food_eats_all_and_shrinks_for_each_food_short():
    s = st(current="B", food={"A": 4, "B": 0})
    el = put(s, "1,2", "elephant", "A")         # Hungry 5
    end_turn(s)                                 # A's Dawn
    assert s.food["A"] == 0 and strength(s, el) == 8
    end_turn(s); end_turn(s)                    # for good: 0 food now, 5 short
    assert strength(s, el) == 3


def test_launch_kw__hungry_eats_in_play_order_with_other_dawn_effects():
    # A Groundhog ("Dawn: gain 10 food") played before the Elephant feeds it; played after, it doesn't.
    s = st(current="B")
    put(s, "1,1", "groundhog", "A")
    el = put(s, "1,2", "elephant", "A")
    end_turn(s)
    assert strength(s, el) == 9 and s.food["A"] == 5
    s2 = st(current="B")
    el2 = put(s2, "1,2", "elephant", "A")
    put(s2, "1,1", "groundhog", "A")
    end_turn(s2)
    assert strength(s2, el2) == 4 and s2.food["A"] == 10


def test_launch_kw__a_buried_hungry_animal_is_skipped():
    s = st(current="B", food={"A": 7, "B": 0})
    el = put(s, "2,2", "elephant", "A")
    put(s, "2,2", "blue_whale", "B")
    end_turn(s)
    assert s.food["A"] == 7 and strength(s, el) == 9


def test_launch_kw__an_inked_animal_is_not_hungry():
    s = st(current="B", hands={"B": ["octopus"]}, food={"A": 7, "B": 0})
    el = put(s, "3,2", "elephant", "A")
    put(s, "4,3", "v1", "B")
    play(s, "octopus", "3,3")                   # inks the Elephant
    end_turn(s)
    assert s.food["A"] == 7 and strength(s, el) == 9


def test_launch_kw__titan_is_offered_only_while_two_actions_are_left():
    s = st(hands={"A": ["blue_whale"]})
    assert any(a.card_id == "blue_whale" for a in rules.legal_actions(s) if isinstance(a, PlaceAction))
    rules.apply_action(s, DrawAction())
    assert not any(isinstance(a, PlaceAction) and a.card_id == "blue_whale" for a in rules.legal_actions(s))


def test_launch_kw__titan_an_extra_action_counts():
    s = st(hands={"A": ["blue_whale"]})
    s.turn_flags["bonus_actions_A"] = 1         # the Beaver's "next turn, take 1 additional action"
    rules.apply_action(s, DrawAction())
    assert any(isinstance(a, PlaceAction) and a.card_id == "blue_whale" for a in rules.legal_actions(s))


def test_launch_kw__titan_no_free_placement_can_play_it():
    # Remora: "if this is next to an allied Fish, play another Fish"; the Whale Shark is a Titan Fish.
    s = st(hands={"A": ["remora", "whale_shark", "tuna"]})
    put(s, "1,1", "tuna", "A")
    play(s, "remora", "1,2")
    cards = {c for c, _ in placements(s)}
    assert "whale_shark" not in cards and "tuna" in cards


def test_launch_kw__flee_happens_before_an_apex_predator_eats():
    s = st(current="B", hands={"B": ["tiger"]})
    put(s, "3,2", "gazelle", "A")
    put(s, "4,2", "v1", "B")
    play(s, "tiger", "3,2")
    assert ids(s, "3,2") == ["tiger"] and hand_ids(s, "A") == ["gazelle"]
    assert "gazelle" not in s.remove_pile


def test_launch_kw__flee_happens_before_king_theron_removes():
    s = st(current="B", hands={"B": ["lion"]})
    put(s, "4,1", "lion_legend_3", "B")
    put(s, "4,2", "v1", "B")
    put(s, "3,2", "gazelle", "A")
    play(s, "lion", "3,2")
    assert hand_ids(s, "A") == ["gazelle"] and "gazelle" not in s.remove_pile


def test_launch_kw__flee_your_own_cover_of_your_fleer_is_a_plain_cover():
    s = st(hands={"A": ["v1"]})
    put(s, "1,2", "gazelle", "A")
    play(s, "v1", "1,2")
    assert ids(s, "1,2") == ["gazelle", "v1"] and hand_ids(s, "A") == []


def test_launch_kw__flee_by_a_roaming_enemy_cover():
    s = st(current="B")
    put(s, "3,2", "gazelle", "A")
    put(s, "4,2", "wolf", "B")
    rules.apply_action(s, RoamAction("4,2", ("cr", "3,2")))
    assert hand_ids(s, "A") == ["gazelle"]


def test_launch_kw__a_fled_card_is_playable_at_once_and_keeps_its_stored_strength():
    s = st(current="B", hands={"B": ["v5"]})
    g = put(s, "3,2", "gazelle", "A")
    g.strength_counter = 2
    put(s, "4,2", "v1", "B")
    play(s, "v5", "3,2")
    end_turn(s)
    back = s.hands["A"][0]
    assert back.card_id == "gazelle" and back.strength_counter == 2
    assert any(isinstance(a, PlaceAction) and a.card_id == "gazelle" for a in rules.legal_actions(s))


def test_launch_kw__the_zebras_coverer_goes_back_to_its_owners_hand_unless_it_has_armor():
    s = st(current="B", hands={"B": ["v6"]})
    put(s, "3,2", "zebra", "A")
    put(s, "4,2", "v1", "B")
    play(s, "v6", "3,2")
    assert s.top_unit("3,2") is None and "v6" in hand_ids(s, "B") and hand_ids(s, "A") == ["zebra"]
    s2 = st(current="B", hands={"B": ["tortoise"]})
    put(s2, "3,2", "zebra", "A")
    put(s2, "4,2", "v1", "B")
    play(s2, "tortoise", "3,2")
    assert ids(s2, "3,2") == ["tortoise"]


def test_launch_kw__king_theron_after_an_apex_cat_eats_nothing_left():
    s = st(hands={"A": ["tiger"]})
    put(s, "1,1", "lion_legend_3", "A")
    put(s, "1,2", "v3", "B")
    play(s, "tiger", "1,2")
    assert ids(s, "1,2") == ["tiger"]


def test_launch_kw__king_theron_removes_what_is_left_after_a_cat_was_removed_by_spikes():
    s = st(hands={"A": ["lion"]})
    put(s, "1,1", "lion_legend_3", "A")
    put(s, "1,2", "hedgehog", "B")
    play(s, "lion", "1,2")
    assert s.top_unit("1,2") is None and "lion" in s.pile_cards_of("A") and "hedgehog" in s.pile_cards_of("B")


def test_launch_kw__king_theron_the_legendary_leopard_grows_for_its_eat_first():
    s = st(hands={"A": ["leopard_legend"]})
    put(s, "1,1", "lion_legend_3", "A")
    put(s, "1,2", "v1", "B")
    put(s, "1,2", "v3", "B")
    play(s, "leopard_legend", "1,2")
    leo = s.top_unit("1,2")
    assert leo.card_id == "leopard_legend" and strength(s, leo) == 6   # it ate the v3: +1
    assert ids(s, "1,2") == ["v1", "leopard_legend"]                    # Theron: the eaten v3 already gone


def test_launch_kw__octopus_inks_a_stealth_enemy_for_good():
    s = st(hands={"A": ["octopus", "jaguar"]})
    put(s, "1,1", "v1", "A")
    sti = put(s, "2,2", "stick_insect", "B")
    play(s, "octopus", "1,2")
    effects.remove_top(s, "1,2", by_player="B"); effects.resolve(s)   # the Octopus gone: the ink stays
    sti.strength_counter = -2                   # a 4: in the Jaguar's reach ("an adjacent enemy of strength 4 or less")
    play(s, "jaguar", "2,1")
    if s.pending:
        assert "2,2" in s.pending["options"]
        choose(s, "2,2")
    assert s.top_unit("2,2") is None


def test_launch_kw__an_inked_animal_loses_armor_and_its_triggered_effects():
    s = st(hands={"A": ["octopus", "rhinoceros_legend"]})
    put(s, "1,1", "v1", "A")
    put(s, "2,2", "tortoise", "B")
    put(s, "1,3", "earthworm", "B")             # "Fall: draw a card ..."
    play(s, "octopus", "1,2")
    effects.remove_top(s, "1,3", by_player="A"); effects.resolve(s)
    assert len(s.hands["B"]) == 0 and s.top_unit("1,3") is None
    play(s, "rhinoceros_legend", "2,1")         # "Roar: remove an adjacent enemy": Armor is gone
    if s.pending:
        choose(s, "2,2")
    assert s.top_unit("2,2") is None


def test_launch_kw__an_inked_dynamic_strength_is_its_printed_zero_and_counters_stay():
    s = st(hands={"A": ["octopus"]})
    s.pile_add("snake_egg", "B"); s.pile_add("bird_egg", "A")
    ee = put(s, "2,2", "egg_eater", "B")
    ee.strength_counter = 1
    put(s, "1,1", "v1", "A")
    assert strength(s, ee) == 5
    play(s, "octopus", "1,2")
    assert strength(s, ee) == 1


def test_launch_kw__an_inked_animal_has_no_aura_but_still_gets_others_auras():
    s = st(hands={"A": ["octopus"]})
    put(s, "1,1", "v1", "A")
    mm = put(s, "2,2", "mahi_mahi", "B")        # "Your other Fish have +1"
    t1 = put(s, "3,2", "tuna", "B")             # +1 per other Fish too
    mm2 = put(s, "2,3", "mahi_mahi", "B")
    base = strength(s, t1)
    play(s, "octopus", "1,2")                   # inks 2,2 only (1,2's neighbours: 1,1 1,3 2,2)
    assert strength(s, t1) == base - 1          # the inked Mahi-mahi's aura gone, the other one's stays
    assert strength(s, mm) == CARDS["mahi_mahi"].base_strength + 1     # it gets the other Mahi-mahi's +1
    assert mm2


def test_launch_kw__a_timer_an_inked_animal_already_started_still_runs():
    s = st(hands={"A": ["black_bear"]}, decks={"A": ["v1"] * 4, "B": ["v1"] * 4})
    put(s, "1,2", "v1", "A"); put(s, "2,2", "v1", "A")
    play(s, "black_bear", "3,2")                # "Roar: in 2 turns, draw 2 cards"
    end_turn(s)
    s.hands["B"] = []; s.add_to_hand("B", "octopus")
    put(s, "4,3", "v1", "B")
    play(s, "octopus", "3,3")                   # inks the Black Bear
    assert s.current == "B"
    end_turn(s); end_turn(s); end_turn(s)
    assert len(s.hands["A"]) == 2


def test_launch_kw__keyword_aura_reaches_adjacent_allies_and_judges_on_the_burying_cover():
    s = st(current="B", hands={"B": ["v5"]})
    put(s, "2,2", "porcupine", "A")
    put(s, "3,2", "v3", "A")
    put(s, "4,2", "v1", "B")
    play(s, "v5", "3,2")
    assert ids(s, "3,2") == ["v3"]              # the v3 had Spikes as it was covered


def test_launch_kw__keyword_aura_never_reaches_an_enemy():
    s = st(hands={"A": ["v5"]})
    put(s, "3,3", "armadillo", "B")
    put(s, "2,2", "v1", "A"); put(s, "1,2", "v1", "A")
    put(s, "2,3", "v3", "B")
    play(s, "v5", "2,3")
    assert ids(s, "2,3") == ["v3", "v5"]


def test_launch_kw__armadillo_gives_armor_to_its_adjacent_allies():
    s = st(current="B", hands={"B": ["rhinoceros_legend"]})
    put(s, "2,2", "armadillo", "A")
    put(s, "3,2", "v3", "A")
    put(s, "4,3", "v1", "B")
    play(s, "rhinoceros_legend", "3,3")         # "Roar: remove an adjacent enemy": the v3 has Armor
    assert s.pending is None or "3,2" not in s.pending["options"]
    assert s.top_unit("3,2").card_id == "v3"


def test_launch_kw__grazing_wildebeest_gains_only_on_a_corner_of_a_held_region():
    s = st()
    for cr in ("1,1", "2,1", "1,2"):
        put(s, cr, "v1", "A")
    put(s, "2,2", "wildebeest", "A")            # R1 held: grazing
    end_turn(s)
    assert s.food["A"] == 6 + 10
    s2 = st()
    put(s2, "2,2", "wildebeest", "A")
    end_turn(s2)
    assert s2.food["A"] == 0


# ============================================================================== The launch decks: cards

def test_launch_cards__unnamed_legendaries_show_their_species_and_keep_fixed_ids():
    assert CARDS["bat_legend"].name == "[BAT]" and CARDS["rodent_legend"].name == "[RODENT]"
    raw = load_bundled_json("cards.json")["cards"]
    for c in raw:
        if c.get("rarity") == "legendary" and c["name"].startswith("["):
            assert "_legend" in c["id"] or c["id"] == "rodent_legend" or c["id"].startswith(("cairn", "scout_bee")), c["id"]


def test_launch_cards__legendary_cuckoo_must_remove_and_then_must_play_another():
    s = st(hands={"A": ["cuckoo_legend", "lion"]})
    put(s, "1,1", "v3", "A")                    # the only animal of strength 4 or less next to it
    put(s, "2,2", "v5", "B")
    play(s, "cuckoo_legend", "1,2")
    assert options(s) == {"1,1"} and not s.pending["optional"]
    choose(s, "1,1")
    assert s.top_unit("1,1") is None
    assert s.pending and s.pending["mode"] == "place" and not s.pending["optional"]


def test_launch_cards__legendary_sloth_runs_each_dusk_effect_twice():
    s = st()
    put(s, "1,1", "sloth_legend", "A")
    put(s, "1,2", "tortoise_legend", "A")       # "Dusk: gain 5 food"
    end_turn(s)
    assert s.food["A"] == 10


def test_launch_cards__a_roars_cost_is_never_declined_mantis():
    s = st(hands={"A": ["praying_mantis"]})
    put(s, "1,1", "v3", "A")
    play(s, "praying_mantis", "1,2")
    if s.pending:
        assert not s.pending["optional"]
        choose(s, "1,1")
    assert s.top_unit("1,1") is None and len(s.hands["A"]) == 2


def test_launch_cards__a_roars_cost_is_never_declined_hornet():
    s = st(hands={"A": ["hornet", "hornet"]})
    put(s, "2,2", "v5", "B")
    play(s, "hornet", "2,1")
    if s.pending:
        assert not s.pending["optional"]
        choose(s, "2,2")
    assert s.top_unit("2,2") is None and hand_ids(s, "A") == []


def test_launch_cards__a_roars_cost_that_cannot_be_paid_does_nothing():
    s = st(hands={"A": ["hornet"]}, decks={"A": ["v1"], "B": []})
    put(s, "2,2", "v5", "B")
    play(s, "hornet", "2,1")
    assert s.pending is None and s.top_unit("2,2").card_id == "v5"


def test_launch_cards__a_roars_cost_is_never_declined_pestis_next_to_only_its_own():
    s = st(hands={"A": ["rat_legend_2"]})
    put(s, "1,1", "v3", "A")
    play(s, "rat_legend_2", "1,2")
    if s.pending:
        assert not s.pending["optional"]
        choose(s, "1,1")
    assert s.top_unit("1,1") is None


def test_launch_cards__tarantula_eats_the_weakest_either_side_armor_excluded_and_keeps_its_strength():
    cards = cards_with({"id": "v_armor1", "base_strength": 1, "keywords": ["Armor"]},
                       *[{"id": f"v{n}", "base_strength": n} for n in range(1, 8)])
    s = make_state(cards=cards, decks={"A": ["v1"] * 4, "B": ["v1"] * 4})
    t = put(s, "2,2", "tarantula", "A")
    put(s, "1,2", "v_armor1", "B")              # weakest, but Armor
    ally = put(s, "2,1", "v2", "A")             # an ally: weakest of the rest
    ally.strength_counter = 1                   # it shows 3
    put(s, "3,2", "v4", "B")
    end_turn(s)
    assert s.top_unit("2,1") is None and s.top_unit("1,2").card_id == "v_armor1"
    assert strength(s, t) == 5 + 3
    effects.remove_top(s, "3,2", by_player="A")
    assert strength(s, t) == 8                  # for good


def test_launch_cards__queen_ant_lays_on_a_random_adjacent_empty_crossroad():
    s = st()
    put(s, "1,2", "queen_ant", "A")
    put(s, "1,1", "v1", "A"); put(s, "2,2", "v1", "B")
    end_turn(s)
    assert tops(s, "young_ant", "A") == ["1,3"]


def test_launch_cards__sea_turtles_baby_turtle_goes_to_hand():
    s = st()
    put(s, "1,2", "sea_turtle", "A")
    end_turn(s)
    assert hand_ids(s, "A") == ["baby_turtle"] and not tops(s, "baby_turtle")


def test_launch_cards__an_ally_removed_this_turn_counts_whoever_removed_it():
    # Hammerhead: "if an ally was removed this turn, remove an adjacent animal". Here the opponent's effect removed it.
    s = st(hands={"A": ["hammerhead"]})
    put(s, "3,3", "v1", "A")
    effects.remove_top(s, "3,3", by_player="B"); effects.resolve(s)
    put(s, "2,2", "v5", "B")
    play(s, "hammerhead", "1,2")
    if s.pending:
        choose(s, "2,2")
    assert s.top_unit("2,2") is None


def test_launch_cards__an_enemy_removed_is_not_an_ally_removed():
    s = st(hands={"A": ["hammerhead"]})
    put(s, "3,3", "v1", "B")
    effects.remove_top(s, "3,3", by_player="A"); effects.resolve(s)
    put(s, "2,2", "v5", "B")
    play(s, "hammerhead", "1,2")
    assert s.pending is None and s.top_unit("2,2").card_id == "v5"


def test_launch_cards__hyena_counts_both_players_removals_and_not_discards():
    s = st(hands={"A": ["hornet", "hornet"]})
    put(s, "3,3", "hyena", "A")
    put(s, "1,3", "v1", "A")
    effects.remove_top(s, "1,3", by_player="B"); effects.resolve(s)   # one of A's
    put(s, "2,2", "v5", "B")
    play(s, "hornet", "2,1")                    # discards a Hornet (not a removal), removes the v5
    if s.pending:
        choose(s, "2,2")
    end_turn(s)
    assert s.food["A"] == 6


def test_launch_cards__vulture_counts_both_players_animals_removed():
    s = st(decks={"A": ["vulture"], "B": []})
    for cr in ("1,1", "1,2", "1,3"):
        put(s, cr, "v1", "B")
        effects.remove_top(s, cr, by_player="A")
    effects.resolve(s)
    end_turn(s)                                 # A's Dusk: three of B's animals removed, the Vulture flies in
    assert tops(s, "vulture")


def test_launch_cards__city_spiders_dawn_kill_counts_as_removed_this_turn():
    s = st(current="B")
    put(s, "2,2", "city_spider", "A")
    put(s, "3,2", "v1", "B")
    put(s, "1,1", "hyena", "A")
    end_turn(s)                                 # A's Dawn: the spider removes the v1
    assert s.top_unit("3,2") is None
    end_turn(s)
    assert s.food["A"] == 3


def test_launch_cards__earthworm_worms_land_only_on_an_empty_or_own_crossroad():
    s = st()
    put(s, "1,2", "earthworm", "A")
    effects.remove_top(s, "1,2", by_player="B"); effects.resolve(s)
    assert ids(s, "1,2") == ["worm", "worm"]
    s2 = st()
    ew = put(s2, "2,2", "earthworm", "A")
    put(s2, "2,2", "v5", "B")
    effects._remove_specific(s2, "2,2", ew, by_player="B"); effects.resolve(s2)
    assert ids(s2, "2,2") == ["v5"]


def test_launch_cards__clarion_one_free_roam_per_clarion_each_turn():
    s = st()
    put(s, "1,1", "wolf_legend_3", "A"); put(s, "2,1", "wolf_legend_3", "A")
    put(s, "1,2", "wolf", "A"); put(s, "1,3", "wolf", "A")
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    rules.apply_action(s, RoamAction("1,3", ("cr", "2,3")))
    assert s.actions_taken_this_turn == 0


def test_launch_cards__warthogs_flanker_must_be_another_hoofed():
    s = st(hands={"A": ["warthog"]})
    put(s, "2,2", "v5", "B")
    play(s, "warthog", "1,2")                   # the Warthog itself is next to the v5: not a flanker
    assert s.pending is None and s.top_unit("2,2").card_id == "v5"
    s2 = st(hands={"A": ["warthog"]})
    put(s2, "2,2", "v5", "B")
    put(s2, "1,1", "v1", "A"); put(s2, "2,1", "v_hoofed", "A")
    play(s2, "warthog", "1,2")
    if s2.pending:
        choose(s2, "2,2")
    assert s2.top_unit("2,2") is None


def test_launch_cards__jackal_removes_one_adjacent_enemy_weaker_than_it_where_it_lands_never_the_covered():
    s = st()
    j = put(s, "1,2", "jackal", "A")
    j.strength_counter = 2                      # a 5 now (a Dingo's gift)
    put(s, "2,2", "v2", "B")
    put(s, "3,2", "v4", "B")                    # weaker than 5
    put(s, "2,3", "v6", "B")
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert options(s) == {"3,2"} and "2,2" not in options(s)
    choose(s, "3,2")
    assert s.top_unit("3,2") is None and ids(s, "2,2") == ["v2", "jackal"]


def test_launch_cards__it_roams_is_not_the_animals_one_roam():
    s = st(hands={"A": ["street_dog"]})
    put(s, "1,1", "v1", "A")
    w = put(s, "1,3", "wolf", "A")
    rules.apply_action(s, RoamAction("1,3", ("cr", "2,3")))   # its roam of the turn
    put(s, "1,3", "v1", "A")
    play(s, "street_dog", "1,2")                # picks the Wolf, +3, it roams
    if s.pending and "2,3" in s.pending.get("options", []):
        choose(s, "2,3")
    choose(s, "3,3")
    assert s.top_unit("3,3") is w and strength(s, w) == 9


def test_launch_cards__an_animal_moved_by_it_roams_can_still_roam():
    s = st(hands={"A": ["coyote"]})
    put(s, "1,1", "v3", "A")
    play(s, "coyote", "1,2")
    choose(s, "1,1"); choose(s, "2,1")
    assert legal(s, RoamAction("2,1", ("cr", "3,1")))


def test_launch_cards__it_roams_may_take_the_den():
    s = st(hands={"A": ["coyote"]})
    for cr in ("1,1", "2,1", "3,1"):
        put(s, cr, "v1", "A")
    put(s, "4,1", "v3", "A")
    play(s, "coyote", "1,2")
    choose(s, "4,1")
    choose(s, "den")
    assert s.result is not None and s.result.winner == "A"


def test_launch_cards__street_dog_offers_only_connected_allies_with_roam():
    s = st(hands={"A": ["street_dog"]})
    put(s, "1,1", "wolf", "A")
    put(s, "1,3", "v3", "A")                    # no Roam
    play(s, "street_dog", "1,2")
    assert "1,3" not in options(s)


def test_launch_cards__coyote_roam_lasts_while_covered_and_is_lost_when_it_leaves_the_board():
    s = st(hands={"A": ["coyote"]})
    a = put(s, "1,1", "v3", "A")
    play(s, "coyote", "1,2")
    choose(s, "1,1"); choose(s, "2,1")
    end_turn(s)
    put(s, "2,1", "v5", "B")                    # covered
    effects.remove_top(s, "2,1", by_player="A"); effects.resolve(s)   # resurfaces
    end_turn(s)
    assert s.top_unit("2,1") is a and legal(s, RoamAction("2,1", ("cr", "3,1")))
    s.hands["A"] = []; s.add_to_hand("A", "opossum")
    put(s, "1,1", "v1", "A")
    rules.apply_action(s, PlaceAction("opossum", ("cr", "2,2")))     # "Roar: return an adjacent ally to your hand"
    if s.pending:
        choose(s, "2,1")
    assert hand_ids(s, "A") == ["v3"]
    end_turn(s); end_turn(s)
    rules.apply_action(s, PlaceAction("v3", ("cr", "2,1")))
    assert not any(isinstance(x, RoamAction) and x.origin == "2,1" for x in rules.legal_actions(s))


def test_launch_cards__connected_to_this_is_a_chain_from_this_animal_not_from_the_den():
    s = st(hands={"A": ["coyote"]})
    put(s, "1,1", "v3", "A")                    # on the den front, connected home, but not to a Coyote on 1,3
    put(s, "2,3", "v3", "A"); put(s, "3,3", "v3", "A")
    play(s, "coyote", "1,3")
    assert options(s) == {"2,3", "3,3"}


def test_launch_cards__lands_the_legendary_elephant_sweeps_when_placed_and_when_it_roams():
    s = st(hands={"A": ["elephant_legend"]})
    put(s, "1,1", "v3", "B")
    play(s, "elephant_legend", "1,2")
    assert s.top_unit("1,1") is None
    put(s, "3,2", "v2", "B")
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert s.top_unit("3,2") is None


def test_launch_cards__fox_draws_after_an_it_roams():
    s = st(hands={"A": ["coyote", "fox"]})
    put(s, "1,1", "v3", "A")
    play(s, "coyote", "1,2")
    choose(s, "1,1"); choose(s, "2,1")
    play(s, "fox", "1,1")
    assert len(s.hands["A"]) == 2


def test_launch_cards__fox_draws_after_a_free_roam():
    s = st(hands={"A": ["fox"]})
    put(s, "1,1", "wolf_legend_3", "A")
    put(s, "1,2", "v_roam", "A")
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    play(s, "fox", "1,2")
    assert len(s.hands["A"]) == 2


def test_launch_cards__african_wild_dog_a_canine_played_next_to_it_roams():
    s = st(hands={"A": ["v_canine"]})
    put(s, "1,1", "african_wild_dog", "A")
    play(s, "v_canine", "1,2")
    assert s.pending is not None


def test_launch_cards__african_wild_dog_a_placed_canine_does_not_roam():
    s = st(hands={"A": ["fox_legend"]})
    put(s, "2,1", "african_wild_dog", "A")
    put(s, "1,3", "v1", "A")
    play(s, "fox_legend", "1,2")                # Poppy and Rusty placed on 1,1 and 2,2, both next to the Wild Dog
    assert sorted(tops(s, "baby_fox") + tops(s, "baby_fox_2")) == ["1,1", "2,2"]
    assert s.pending is None


@pytest.mark.xfail(strict=True, reason=(
    "Engine follows a later call: the ruling puts the Pup down only on an empty crossroad (an animal that resurfaces "
    "leaves no Pup); the engine places it on top of the resurfaced animal, citing Martin 2026-10-31 in "
    "effects._bush_dog_roam. Not fixed: the ruling looks stale, and changing it changes how the Bush Dog plays."))
def test_launch_cards__bush_dog_leaves_a_pup_only_on_an_empty_crossroad():
    s = st()
    put(s, "1,2", "bush_dog", "A")
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert ids(s, "1,2") == ["pup"]
    s2 = st()
    put(s2, "1,2", "v1", "A")
    put(s2, "1,2", "bush_dog", "A")
    rules.apply_action(s2, RoamAction("1,2", ("cr", "2,2")))
    assert ids(s2, "1,2") == ["v1"]


def test_launch_cards__dhole_draws_when_it_covers_a_lone_enemy_by_placement_or_roam():
    s = st(hands={"A": ["dhole"]})
    put(s, "2,2", "v3", "B"); put(s, "1,1", "v1", "A")
    play(s, "dhole", "1,2")
    assert len(s.hands["A"]) == 0
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert len(s.hands["A"]) == 2
    s2 = st(hands={"A": ["dhole"]})
    put(s2, "1,2", "v3", "B"); put(s2, "2,2", "v1", "B")
    play(s2, "dhole", "1,2")                    # another enemy beside it
    assert len(s2.hands["A"]) == 0


def test_launch_cards__dhole_gives_no_equal_strength_cover():
    s = st(hands={"A": ["dhole", "v_canine"]})
    put(s, "1,2", "v5", "B")
    put(s, "1,1", "dhole", "A")
    assert "1,2" not in place_targets(s)


def test_launch_cards__wolverine_removes_only_a_lone_adjacent_enemy_and_stealth_armor_protect():
    s = st(hands={"A": ["wolverine"]})
    put(s, "2,2", "v5", "B"); put(s, "3,2", "v1", "B")      # not lone
    put(s, "1,1", "stick_insect", "B")                       # lone but Stealth
    put(s, "1,3", "tortoise", "B")                           # lone but Armor
    play(s, "wolverine", "1,2")
    assert s.pending is None
    s2 = st(hands={"A": ["wolverine"]})
    put(s2, "2,2", "v5", "B")
    play(s2, "wolverine", "1,2")
    if s2.pending:
        choose(s2, "2,2")
    assert s2.top_unit("2,2") is None


def test_launch_cards__black_wolf_grows_and_draws_when_it_roams_itself():
    s = st()
    bw = put(s, "1,1", "wolf_legend_2", "A")
    rules.apply_action(s, RoamAction("1,1", ("cr", "2,1")))
    assert bw.strength_counter == 1 and len(s.hands["A"]) == 1


def test_launch_cards__okapi_draws_at_dawn_and_dusk_while_grazing_sloth_doubles_only_dusk():
    s = st()
    for cr in ("1,1", "2,1", "1,2"):
        put(s, cr, "v1", "A")
    put(s, "2,2", "okapi", "A")
    put(s, "1,3", "sloth_legend", "A")
    end_turn(s)
    assert len(s.hands["A"]) == 2               # Dusk, twice
    end_turn(s)
    assert len(s.hands["A"]) == 3               # Dawn, once


def test_launch_cards__placing_and_roaming_cover_by_one_rule_leopard():
    s = st(hands={"A": ["v_cat_roam"]})
    put(s, "3,3", "leopard", "A")
    put(s, "1,2", "v5", "B")
    assert "1,2" in place_targets(s)            # a Cat covers an equal enemy
    put(s, "1,1", "v_cat_roam", "A")
    assert legal(s, RoamAction("1,1", ("cr", "1,2")))


def test_launch_cards__piranha_counts_the_fish_you_control_now_itself_included():
    # "Your Fish can cover enemies of strength up to the number of your Fish."
    s = st(hands={"A": ["baby_fish"]})          # a 0
    put(s, "3,3", "piranha", "A")               # 1 Fish, itself: the Baby Fish covers an enemy of strength 1
    put(s, "1,2", "v1", "B")
    put(s, "1,1", "v2", "B")
    t = place_targets(s)
    assert "1,2" in t and "1,1" not in t


def test_launch_cards__swordfish_removes_different_random_enemies_stealth_hit_armor_stays():
    s = st(hands={"A": ["swordfish"]})
    put(s, "1,2", "tuna", "A"); put(s, "2,1", "tuna", "A")
    put(s, "3,2", "stick_insect", "B"); put(s, "2,3", "tortoise", "B")
    play(s, "swordfish", "2,2")
    assert s.top_unit("3,2") is None and s.top_unit("2,3").card_id == "tortoise"


def test_launch_cards__barracuda_counts_itself_among_your_fish():
    s = st(hands={"A": ["barracuda"]})
    put(s, "2,2", "v1", "B")
    play(s, "barracuda", "1,2")
    if s.pending:
        choose(s, "2,2")
    assert s.top_unit("2,2") is None


def test_launch_cards__the_repeat_legend_repeats_each_adjacent_allied_rodents_roar():
    s = st(hands={"A": ["capybara_legend"]})
    put(s, "1,1", "squirrel", "A")              # "Roar: gain 10 food"
    put(s, "1,3", "flying_squirrel", "A")       # "Roar: gain 10 food and draw a card"
    put(s, "2,2", "squirrel", "B")              # not an ally
    play(s, "capybara_legend", "1,2")
    assert s.food["A"] == 20 and len(s.hands["A"]) == 1


def test_launch_cards__the_legendary_squirrel_pays_three_times_in_two_turns():
    s = st(hands={"A": ["squirrel_legend"]}, food={"A": 10, "B": 0})
    play(s, "squirrel_legend", "1,2")
    assert s.food["A"] == 0
    for _ in range(4):
        end_turn(s)
    assert s.food["A"] == 30


def test_launch_cards__the_legendary_squirrels_timer_pauses_while_covered():
    s = st(hands={"A": ["squirrel_legend"]}, food={"A": 10, "B": 0})
    play(s, "squirrel_legend", "1,2")
    end_turn(s)
    put(s, "1,2", "v5", "B")
    for _ in range(4):
        end_turn(s)
    assert s.food["A"] == 0
    effects.remove_top(s, "1,2", by_player="A"); effects.resolve(s)
    for _ in range(4):
        end_turn(s)
    assert s.food["A"] == 30


def test_launch_cards__the_legendary_squirrel_removed_loses_the_stake():
    s = st(hands={"A": ["squirrel_legend"]}, food={"A": 10, "B": 0})
    play(s, "squirrel_legend", "1,2")
    effects.remove_top(s, "1,2", by_player="B"); effects.resolve(s)
    for _ in range(6):
        end_turn(s)
    assert s.food["A"] == 0


def test_launch_cards__chameleon_becomes_the_copy_for_good_without_its_roar_and_the_card_stays_in_hand():
    s = st(hands={"A": ["chameleon", "dolphin"]})
    play(s, "chameleon", "1,2")
    if s.pending:
        choose(s, s.pending["options"][0])
    c = s.top_unit("1,2")
    assert c.card_id == "dolphin" and strength(s, c) == 5
    assert hand_ids(s, "A") == ["dolphin"]      # no draw: the Roar never made
    effects.remove_top(s, "1,2", by_player="B"); effects.resolve(s)
    assert s.pile_cards_of("A") == ["dolphin"]


def test_launch_cards__chameleon_copy_keeps_the_copied_cards_counter():
    s = st(hands={"A": ["chameleon"]})
    d = s.add_to_hand("A", "dolphin"); d.strength_counter = 2
    play(s, "chameleon", "1,2")
    if s.pending:
        choose(s, s.pending["options"][0])
    assert strength(s, s.top_unit("1,2")) == 7


def test_launch_cards__iris_copies_an_ally_or_a_choosable_enemy_and_adds_a_plain_copy():
    s = st(hands={"A": ["chameleon_legend"]})
    put(s, "1,1", "stick_insect", "B")          # Stealth: not choosable
    d = put(s, "1,3", "dolphin", "A"); d.strength_counter = 2
    put(s, "2,2", "v4", "B")
    play(s, "chameleon_legend", "1,2")
    assert options(s) == {"1,3", "2,2"}
    choose(s, "1,3")
    assert s.top_unit("1,2").card_id == "dolphin"
    added = [u for u in s.hands["A"] if u.card_id == "dolphin"]
    assert len(added) == 1 and added[0].strength_counter == 0


def test_launch_cards__hamster_pays_five_per_card_its_owner_draws_not_the_opponents_not_a_burned_one():
    s = st()
    put(s, "1,2", "hamster", "A")
    rules.apply_action(s, DrawAction())
    assert s.food["A"] == 10
    s.hands["A"] = []
    for _ in range(9):
        s.add_to_hand("A", "v1")
    rules.apply_action(s, DrawAction())         # one fits, one burns
    assert s.food["A"] == 15
    end_turn(s)
    rules.apply_action(s, DrawAction())         # B draws
    assert s.food["A"] == 15


def test_launch_cards__marmot_counts_food_in_hand_and_on_the_board():
    s = st(food={"A": 25, "B": 0})
    m = put(s, "1,2", "marmot", "A")
    h = s.add_to_hand("A", "marmot")
    from animal_kingdom.engine.strength import placement_strength
    assert strength(s, m) == 5 and placement_strength(s, h) == 5


def test_launch_cards__vole_offers_only_adjacent_allied_rodents_with_a_roar_never_a_repeater():
    s = st(hands={"A": ["vole"]})
    put(s, "1,1", "squirrel", "A")              # a Roar
    put(s, "1,3", "chinchilla", "A")            # a Rodent with no Roar
    put(s, "2,2", "capybara_legend", "A")       # a repeater
    play(s, "vole", "1,2")
    if s.pending:
        assert options(s) == {"1,1"}
        choose(s, "1,1")
    assert s.food["A"] == 10


def test_launch_cards__the_repeat_legend_skips_a_vole():
    s = st(hands={"A": ["capybara_legend"]})
    put(s, "1,1", "vole", "A")
    put(s, "1,3", "squirrel", "A")
    play(s, "capybara_legend", "1,2")
    assert s.food["A"] == 10 and s.pending is None


def test_launch_cards__macaw_repeats_the_last_roar_the_opponent_played_and_a_macaw_repeats_what_it_repeated():
    s = st(current="B", hands={"B": ["squirrel"], "A": ["macaw"]})
    put(s, "4,2", "v1", "B")
    play(s, "squirrel", "3,2")
    end_turn(s)
    play(s, "macaw", "2,2")
    assert s.food["A"] == 10
    end_turn(s)
    s.hands["B"] = []; s.add_to_hand("B", "macaw")
    food_b = s.food["B"]
    play(s, "macaw", "3,3")
    assert s.food["B"] == food_b + 10


def test_launch_cards__macaw_does_nothing_before_the_opponent_has_roared():
    s = st(hands={"A": ["macaw"]})
    play(s, "macaw", "2,2")
    assert s.pending is None and s.food["A"] == 0 and hand_ids(s, "A") == []


def test_launch_cards__greywhisker_must_play_another_and_the_discard_is_the_players_choice():
    s = st(hands={"A": ["mole_legend", "v1", "v2"]})
    play(s, "mole_legend", "1,2")
    assert s.pending["mode"] == "place" and not s.pending["optional"]
    rules.apply_action(s, PlaceAction("v1", ("cr", "1,1")))
    assert s.pending and s.pending["mode"] == "choice" and s.pending["chooser"] == "A"
    assert len(s.pending["options"]) == len(s.hands["A"])


def test_launch_cards__hare_counts_the_animals_played_from_hand_itself_included():
    s = st(hands={"A": ["mole", "v1", "hare"]})
    play(s, "mole", "1,2")
    rules.apply_action(s, PlaceAction("v1", ("cr", "1,1")))   # the Mole's extra play
    play(s, "hare", "1,3")
    assert len(s.hands["A"]) == 2


def test_launch_cards__macaque_counts_the_hand_after_it_left():
    s = st(hands={"A": ["macaque"] + ["v1"] * 4})
    put(s, "2,2", "v9", "B")
    play(s, "macaque", "1,2")
    assert s.top_unit("2,2") is not None        # 4 left: not 5


def test_launch_cards__peacock_covers_with_the_strength_it_shows_then_has_one_less():
    s = st(hands={"A": ["peacock", "v1", "v1", "v1"]})       # 1 + 4 in hand
    put(s, "1,2", "v4", "B")
    assert "1,2" in place_targets(s)
    play(s, "peacock", "1,2")
    assert strength(s, s.top_unit("1,2")) == 4


def test_launch_cards__legendary_butterfly_evolves_at_dawn_in_hand_too():
    s = st(current="B", hands={"A": ["butterfly_legend"]})
    end_turn(s)
    assert hand_ids(s, "A")[0] == "butterfly_legend_caterpillar"


def test_launch_cards__legendary_butterfly_evolving_on_the_board_fires_no_roar_and_buried_doesnt_evolve():
    s = st(current="B")
    put(s, "1,2", "butterfly_legend", "A")
    b = put(s, "2,2", "butterfly_legend", "A")
    put(s, "2,2", "v5", "B")
    end_turn(s)
    assert s.top_unit("1,2").card_id == "butterfly_legend_caterpillar" and hand_ids(s, "A") == []
    assert b.card_id == "butterfly_legend"


def test_launch_cards__legendary_butterfly_each_gain_moves_one_stage_and_keeps_the_points():
    s = st(hands={"A": ["gorilla_legend", "butterfly_legend"]})   # "give all animals in your hand +1"
    play(s, "gorilla_legend", "1,2")
    b = s.hands["A"][0]
    assert b.card_id == "butterfly_legend_caterpillar" and b.strength_counter == 1


def test_launch_cards__legendary_butterfly_stops_at_monarch():
    s = st(current="B")
    put(s, "1,2", "butterfly_legend_monarch", "A")
    end_turn(s)
    assert s.top_unit("1,2").card_id == "butterfly_legend_monarch"


def test_launch_cards__caterpillar_becomes_the_pools_butterfly_and_keeps_its_counter():
    s = st(hands={"A": ["gorilla_legend", "caterpillar"]})
    play(s, "gorilla_legend", "1,2")
    bf = [u for u in s.hands["A"] if u.card_id == "butterfly"]
    assert len(bf) == 1 and bf[0].strength_counter == 1 and len(s.hands["A"]) == 2   # and it drew a card


def test_launch_cards__the_legendary_eagle_brings_its_mate_when_drawn_one_at_a_time():
    s = st(decks={"A": ["v1", "eagle_legend"], "B": []})
    rules.apply_action(s, DrawAction())
    assert sorted(hand_ids(s, "A")) == ["eagle_legend", "eagle_legend_2", "v1"]


def test_launch_cards__the_eagles_share_a_buff_while_both_in_hand():
    s = st(hands={"A": ["baboon"]}, decks={"A": ["v1", "eagle_legend"], "B": []})
    rules.apply_action(s, DrawAction())
    play(s, "baboon", "1,2")
    while s.pending:
        opts = [o for o in s.pending["options"] if o != SKIP]
        eagle = next(u.iid for u in s.hands["A"] if u.card_id == "eagle_legend")
        choose(s, eagle if eagle in opts else opts[0])
    e = {u.card_id: u.strength_counter for u in s.hands["A"]}
    assert e["eagle_legend"] >= 1 and e["eagle_legend_2"] == e["eagle_legend"]


def test_launch_cards__the_legendary_eagle_brings_its_mate_when_returned_but_one_mate_at_a_time():
    s = st(hands={"A": ["opossum"]})
    put(s, "1,1", "eagle_legend", "A")
    play(s, "opossum", "1,2")
    if s.pending:
        choose(s, "1,1")
    assert sorted(hand_ids(s, "A")) == ["eagle_legend", "eagle_legend_2"]
    s2 = st(hands={"A": ["opossum", "eagle_legend_2"]})
    put(s2, "1,1", "eagle_legend", "A")
    play(s2, "opossum", "1,2")
    if s2.pending:
        choose(s2, "1,1")
    assert sorted(hand_ids(s2, "A")) == ["eagle_legend", "eagle_legend_2"]


def test_launch_cards__the_mate_never_brings_the_eagle_back():
    s = st(decks={"A": ["eagle_legend_2"], "B": []})
    rules.apply_action(s, DrawAction())
    assert hand_ids(s, "A") == ["eagle_legend_2"]


def test_launch_cards__orangutans_copy_keeps_the_originals_counter():
    s = st(hands={"A": ["orangutan"]})
    p = s.add_to_hand("A", "tarsier"); p.strength_counter = 2
    play(s, "orangutan", "1,2")
    if s.pending:
        choose(s, s.pending["options"][0])
    assert sorted(u.strength_counter for u in s.hands["A"]) == [2, 2]


def test_launch_cards__baboon_the_player_picks_two_different_cards():
    s = st(hands={"A": ["baboon", "v1", "v2", "v3"]})
    play(s, "baboon", "1,2")
    first = [o for o in s.pending["options"] if o != SKIP][0]
    choose(s, first)
    assert first not in s.pending["options"]
    choose(s, [o for o in s.pending["options"] if o != SKIP][0])
    assert sorted(u.strength_counter for u in s.hands["A"]) == [0, 1, 1]


def test_launch_cards__legendary_baboon_two_random_cards():
    s = st(current="B", hands={"A": ["v1", "v2", "v3"]})
    put(s, "1,2", "baboon_legend", "A")
    end_turn(s)
    assert s.pending is None and sorted(u.strength_counter for u in s.hands["A"]) == [0, 1, 1]


def test_launch_cards__stork_two_different_younglings():
    for seed in range(10):
        s = st(hands={"A": ["stork"]})
        s.rng.seed(seed)
        play(s, "stork", "2,2")
        h = hand_ids(s, "A")
        assert len(h) == 2 and h[0] != h[1]


def test_launch_cards__gorilla_reads_its_strength_as_it_lands():
    s = st(hands={"A": []})
    g = s.add_to_hand("A", "gorilla"); g.strength_counter = 2
    play(s, "gorilla", "1,2")
    assert len(s.hands["A"]) == 1


def test_launch_cards__anteater_gains_the_drawn_cards_strength_as_it_would_be_played_now():
    s = st(hands={"A": ["anteater"]}, decks={"A": ["marmot"], "B": []}, food={"A": 20, "B": 0})
    play(s, "anteater", "1,2")
    assert s.food["A"] == 20 + 5


def test_launch_cards__rabbit_plays_a_bunny_on_a_neighbour_of_the_owners_choice_and_it_counts_as_a_play():
    s = st(hands={"A": ["rabbit", "rat"]})
    put(s, "2,2", "v1", "B")                    # 1 = 1: the Bunny can't cover it
    play(s, "rabbit", "1,2")
    offered = {cr for c, cr in placements(s)}
    assert offered == {"1,1", "1,3"}
    rules.apply_action(s, PlaceAction("bunny", ("cr", "1,1")))
    assert s.actions_taken_this_turn == 1
    play(s, "rat", "2,1")                       # the third animal played this turn
    if s.pending:
        choose(s, "2,2")
    assert s.top_unit("2,2") is None


def test_launch_cards__rabbit_with_no_legal_neighbour_the_bunny_is_gone():
    s = st(hands={"A": ["rabbit"]})
    for cr in ("1,1", "1,3", "2,2"):
        put(s, cr, "v5", "B")
    play(s, "rabbit", "1,2")
    assert s.pending is None and "bunny" not in hand_ids(s, "A") and not tops(s, "bunny")


def test_launch_cards__rabbit_hare_and_bunny_are_rodents():
    assert all("Rodent" in CARDS[c].tags for c in ("rabbit", "hare", "bunny"))


def test_launch_cards__impala_plays_its_calf_with_its_roar_drawing_only_if_grazing():
    s = st(hands={"A": ["impala"]})
    put(s, "1,1", "v1", "A"); put(s, "2,1", "v1", "A")
    play(s, "impala", "1,2")
    assert s.pending and s.pending["mode"] == "place"
    rules.apply_action(s, PlaceAction("baby_impala", ("cr", "2,2")))    # completes R1: it grazes
    assert s.actions_taken_this_turn == 1 and len(s.hands["A"]) == 1


def test_launch_cards__impala_calf_not_grazing_draws_nothing():
    s = st(hands={"A": ["impala"]})
    play(s, "impala", "1,2")
    rules.apply_action(s, PlaceAction("baby_impala", ("cr", "2,2")))
    assert s.hands["A"] == []


def test_launch_cards__legendary_deer_grows_a_fleeing_ally_and_itself():
    s = st(current="B", hands={"B": ["v5", "v6"]})
    put(s, "1,1", "deer_legend", "A")
    put(s, "3,2", "gazelle", "A")
    put(s, "4,2", "v1", "B")
    play(s, "v5", "3,2")
    g = next(u for u in s.hands["A"] if u.card_id == "gazelle")
    assert g.strength_counter == 2


def test_launch_cards__legendary_deer_must_be_on_top_to_grow_others_its_own_flight_grows_itself():
    s = st(current="B", hands={"B": ["v5", "v6"]})
    put(s, "1,1", "deer_legend", "A"); put(s, "1,1", "v5", "B")
    put(s, "3,2", "gazelle", "A")
    put(s, "4,2", "v1", "B")
    play(s, "v5", "3,2")
    assert next(u for u in s.hands["A"] if u.card_id == "gazelle").strength_counter == 0
    s2 = st(current="B", hands={"B": ["v5"]})
    put(s2, "3,2", "deer_legend", "A")
    put(s2, "4,2", "v1", "B")
    play(s2, "v5", "3,2")
    assert next(u for u in s2.hands["A"] if u.card_id == "deer_legend").strength_counter == 2


def test_launch_cards__legendary_wildebeest_and_boar_move_each_region_by_five_per_copy_never_below_nothing():
    s = st()
    for cr in ("1,1", "2,1", "1,2", "2,2"):
        put(s, cr, "v1", "A")
    put(s, "3,3", "wildebeest_legend", "A"); put(s, "1,3", "wildebeest_legend", "A")
    assert rules.region_income(s, "A") == 10 + 10
    s2 = st()
    for cr in ("1,1", "2,1", "1,2", "2,2"):
        put(s2, cr, "v1", "A")
    put(s2, "4,3", "boar_legend", "B"); put(s2, "3,3", "boar_legend", "B")
    assert rules.region_income(s2, "A") == 0


def test_launch_cards__legendary_giraffe_reveals_the_opponents_hand():
    s = st(hands={"B": ["v1"]})
    put(s, "1,2", "giraffe_legend", "A")
    assert s.hand_revealed("B") and not s.hand_revealed("A")


def test_launch_cards__great_white_shark_has_reach_after_any_animal_left_the_board():
    s = st(hands={"A": ["great_white_shark"]})
    put(s, "1,2", "v1", "A")
    put(s, "3,2", "v1", "B")
    assert "3,2" not in place_targets(s)
    put(s, "3,3", "v1", "B")
    effects.remove_top(s, "3,3", by_player="A"); effects.resolve(s)   # the opponent's animal left
    assert "3,2" in place_targets(s)


def test_launch_cards__cuckoos_eggs_count_as_the_cuckoo_players_shuffles():
    s = st(hands={"A": ["cuckoo"]})
    mine = put(s, "1,1", "rattlesnake", "A")
    theirs = put(s, "4,3", "rattlesnake", "B")
    play(s, "cuckoo", "2,2")
    assert strength(s, mine) == 2 and strength(s, theirs) == 0


def test_launch_cards__opossum_must_return_an_ally_that_can_be_returned_armor_cannot():
    s = st(hands={"A": ["opossum"]})
    put(s, "1,1", "tortoise", "A")
    put(s, "1,3", "v3", "A")
    play(s, "opossum", "1,2")
    if s.pending:
        assert options(s) == {"1,3"} and not s.pending["optional"]
        choose(s, "1,3")
    assert hand_ids(s, "A") == ["v3"]


# ============================================================================== The fit and rarity passes

def _vesper_state(**kw):
    """B to move, with a chain to 2,2; A's Colony animal (a Young Ant, 1) on 2,2's neighbour 1,2."""
    kw.setdefault("decks", {"A": ["v1"] * 4, "B": ["v1"] * 4})
    s = st(current="B", **kw)
    for cr in ("4,2", "3,2", "2,2"):
        put(s, cr, "v1", "B")
    return s


def test_vesper__comes_from_hand_onto_an_enemy_that_covers_a_colony_ally():
    s = _vesper_state(hands={"A": ["hornet_legend"], "B": ["v5"]})
    put(s, "1,2", "young_ant", "A")
    play(s, "v5", "1,2")
    assert ids(s, "1,2") == ["young_ant", "v5", "hornet_legend"] and hand_ids(s, "A") == []


def test_vesper__comes_from_the_deck_if_not_in_hand():
    s = _vesper_state(hands={"B": ["v5"]}, decks={"A": ["v1", "hornet_legend", "v1"], "B": []})
    put(s, "1,2", "young_ant", "A")
    play(s, "v5", "1,2")
    assert s.top_unit("1,2").card_id == "hornet_legend" and "hornet_legend" not in s.decks["A"]


def test_vesper__on_the_board_does_nothing():
    s = _vesper_state(hands={"B": ["v5"]}, decks={"A": [], "B": []})
    put(s, "1,1", "hornet_legend", "A")
    put(s, "1,2", "young_ant", "A")
    play(s, "v5", "1,2")
    assert ids(s, "1,2") == ["young_ant", "v5"] and tops(s, "hornet_legend") == ["1,1"]


def test_vesper__your_own_cover_does_not_count():
    s = st(hands={"A": ["hornet_legend", "v5"]})
    put(s, "1,2", "young_ant", "A")
    play(s, "v5", "1,2")
    assert hand_ids(s, "A") == ["hornet_legend"]


def test_vesper__answers_a_cover_by_roaming():
    s = st(current="B", hands={"A": ["hornet_legend"]})
    put(s, "1,2", "young_ant", "A")
    put(s, "2,2", "wolf", "B")
    rules.apply_action(s, RoamAction("2,2", ("cr", "1,2")))
    assert s.top_unit("1,2").card_id == "hornet_legend"


def test_vesper__lands_with_no_strength_check_no_action_no_roar_not_a_play():
    s = _vesper_state(hands={"A": ["hornet_legend"], "B": ["blue_whale"]})
    put(s, "1,2", "young_ant", "A")
    play(s, "blue_whale", "1,2")                # 12
    assert s.top_unit("1,2").card_id == "hornet_legend"
    assert s.current == "A" and s.actions_taken_this_turn == 0


@pytest.mark.xfail(strict=True, reason=(
    "Two readings of 'It resolves with the other reactions to the cover, after the coverer's Roar (as Spikes does), and "
    "only if that enemy is still on the crossroad by then'. A: Vesper waits for the other reactions, so when a Soldier "
    "Bee's Spikes remove the coverer, Vesper stays home. B: Vesper is one of those reactions, in no set order; the "
    "engine resolves it before the Spikes, so Vesper lands on the coverer, the Spikes then remove the coverer from "
    "under it, and Vesper is left standing on its own Soldier Bee."))
def test_vesper__comes_only_if_the_enemy_is_still_there_after_the_other_reactions():
    # A Soldier Bee (Colony, Spikes) covered: the Spikes remove the coverer first, so Vesper stays home.
    s = _vesper_state(hands={"A": ["hornet_legend"], "B": ["v5"]})
    put(s, "1,2", "guard_bee", "A")
    play(s, "v5", "1,2")
    assert ids(s, "1,2") == ["guard_bee"] and hand_ids(s, "A") == ["hornet_legend"]


def test_vesper__landing_is_a_cover_spikes_remove_it_and_a_fleer_runs():
    s = _vesper_state(hands={"A": ["hornet_legend"], "B": ["hedgehog"]})
    put(s, "1,2", "young_ant", "A")
    play(s, "hedgehog", "1,2")
    assert ids(s, "1,2") == ["young_ant", "hedgehog"] and "hornet_legend" in s.pile_cards_of("A")
    s2 = _vesper_state(hands={"A": ["hornet_legend"], "B": ["gazelle"]})
    put(s2, "1,2", "young_ant", "A")
    play(s2, "gazelle", "1,2")
    assert ids(s2, "1,2") == ["young_ant", "hornet_legend"] and "gazelle" in hand_ids(s2, "B")


def test_vesper__an_apex_predator_still_eats_under_vesper():
    s = _vesper_state(hands={"A": ["hornet_legend"], "B": ["tiger"]})
    put(s, "1,2", "young_ant", "A")
    play(s, "tiger", "1,2")
    assert ids(s, "1,2") == ["tiger", "hornet_legend"] and "young_ant" in s.remove_pile


def test_vesper__several_colony_animals_covered_at_once_it_goes_to_the_one_played_first():
    s = st(current="B", hands={"A": ["hornet_legend"], "B": ["locust_legend"]})
    put(s, "1,3", "young_ant", "A")             # played first
    put(s, "1,1", "young_ant", "A")
    put(s, "4,2", "v1", "B")
    play(s, "locust_legend", "3,2")
    assert s.top_unit("1,3").card_id == "hornet_legend" and s.top_unit("1,1").card_id != "hornet_legend"


def _methuselah(**kw):
    s = st(**kw)
    put(s, "3,3", "tortoise_legend", "A")       # Azamandulai: "Each player gains at most 20 food per turn. Dusk: gain 5"
    return s


def test_methuselah__the_cap_counts_every_source_and_food_over_it_is_lost():
    s = _methuselah(hands={"A": ["squirrel", "squirrel", "squirrel"]})
    play(s, "squirrel", "1,2"); play(s, "squirrel", "1,1")
    assert s.food["A"] == 20


def test_methuselah__its_own_dusk_counts_and_comes_before_region_income():
    s = _methuselah(hands={"A": ["squirrel"]})
    for cr in ("1,1", "2,1", "2,2"):
        put(s, cr, "v1", "A")
    play(s, "squirrel", "1,2")                  # 10, completes R1 (10 income)
    end_turn(s)                                 # Dusk 5, then income 10: 25 asked, 20 allowed
    assert s.food["A"] == 20


def test_methuselah__food_paid_or_eaten_doesnt_make_room():
    s = _methuselah(hands={"A": ["squirrel", "squirrel", "squirrel"]})
    s.turn_flags["bonus_actions_A"] = 1         # three actions this turn
    play(s, "squirrel", "1,2")                  # 10
    effects.lose_food(s, "A", 10)               # paid
    play(s, "squirrel", "1,1")                  # 10 more: 20 gained
    play(s, "squirrel", "1,3")                  # over the cap: nothing
    assert s.food["A"] == 10


def test_methuselah__caps_the_opponent_on_its_turn_too():
    s = _methuselah(current="B", hands={"B": ["squirrel", "squirrel", "squirrel"]})
    s.turn_flags["bonus_actions_B"] = 1
    play(s, "squirrel", "4,2"); play(s, "squirrel", "4,1"); play(s, "squirrel", "4,3")
    assert s.food["B"] == 20


def test_methuselah__buried_caps_nothing():
    s = _methuselah(hands={"A": ["squirrel", "squirrel", "squirrel"]})
    s.turn_flags["bonus_actions_A"] = 1
    put(s, "3,3", "blue_whale", "B")
    play(s, "squirrel", "1,2"); play(s, "squirrel", "1,1"); play(s, "squirrel", "1,3")
    assert s.food["A"] == 30


# ============================================================================== After the launch

def test_after_launch__gale_counts_itself():
    s = st(hands={"A": ["falcon_legend"]})
    for cr in ("1,2", "2,2", "3,2"):
        put(s, cr, "v1", "A")
    put(s, "4,1", "v1", "A")                    # one ally already next to B's den
    play(s, "falcon_legend", "4,3")
    assert len(s.hands["A"]) == 2


def test_after_launch__wolf_legend_counts_only_your_adjacent_canines():
    s = st()
    w = put(s, "2,2", "wolf_legend", "A")
    put(s, "1,2", "v_canine", "A")
    put(s, "3,2", "v_canine", "B")
    put(s, "2,1", "v_canine", "B")
    end_turn(s)
    assert w.strength_counter == 1


def test_after_launch__python_grows_only_when_an_animal_leaves_the_board_not_on_a_discard():
    s = st(current="B", decks={"A": ["v1"] * 4, "B": ["swan_legend"]}, hands={"A": ["v1", "v2"]})
    py = put(s, "1,2", "python", "B")
    rules.apply_action(s, DrawAction())         # B draws the Black Swan: A discards a random card
    assert len(s.hands["A"]) == 1
    assert strength(s, py) == 0
    put(s, "3,3", "v1", "A")
    effects.remove_top(s, "3,3", by_player="B"); effects.resolve(s)
    assert strength(s, py) == 1


def test_after_launch__spikes_are_spent_by_the_first_enemy_cover_even_when_armor_keeps_the_coverer():
    s = st(current="B", hands={"B": ["tortoise", "v6"]})
    put(s, "3,2", "hedgehog", "A")
    put(s, "4,2", "v1", "B")
    play(s, "tortoise", "3,2")
    assert ids(s, "3,2") == ["hedgehog", "tortoise"]
    effects.remove_top(s, "3,2", by_player="A"); effects.resolve(s)   # Armor: by the rules, a test lifts it off
    if s.top_unit("3,2").card_id != "hedgehog":
        s.board["3,2"].pop()
    play(s, "v6", "3,2")
    assert ids(s, "3,2") == ["hedgehog", "v6"]
