"""The launch decks' mechanics and cards, one scenario each (the card workbench's twelve decks, 2026-10-08).

Map A (the test fixture): a 4x3 grid, A's den fronts column 1, B's column 4; "2,2" neighbours "1,2", "3,2", "2,1",
"2,3". Regions: R1 = 1,1 2,1 1,2 2,2 (10 food), R4 = 1,2 2,2 1,3 2,3 (10), R2/R5 the middle ones (20).
"""

from __future__ import annotations

import pytest

from animal_kingdom.engine import effects, rules, statics
from animal_kingdom.engine.actions import SKIP, ChoiceAction, DrawAction, PassAction, PlaceAction, RoamAction
from animal_kingdom.engine.state import EngineError, UnitInstance
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.strength import effective_strength, placement_strength

from animal_kingdom.engine.cards import load_cards

from ._helpers import apply_click, hand_ids, make_state, put

CFG = Config.default()


def end_turn(s):
    """End the turn of whoever is to move (a pass; two in a row would end the game, so the count is reset)."""
    s.idle_turns = 0
    rules.apply_action(s, PassAction())


def choose(s, option):
    assert s.pending is not None and option in s.pending["options"], (option, s.pending)
    rules.apply_action(s, ChoiceAction(option))


def hand_inst(s, player, card_id):
    return next(u for u in s.hands[player] if u.card_id == card_id)


def removed(s, card_id):
    return card_id in s.remove_pile


# ================================================================================ keywords

def test_hungry_eats_the_food_there_is_and_shrinks_for_good_by_the_rest():
    s = make_state(food={"A": 7, "B": 0}, decks={"A": ["lion"] * 4, "B": ["lion"] * 4})
    ele = put(s, "1,2", "elephant", "A")                       # Hungry 5
    end_turn(s); end_turn(s)                                   # A's next turn starts: it eats 5
    assert s.food["A"] == 2 and effective_strength(s, ele) == 9
    end_turn(s); end_turn(s)                                   # 2 food: it eats both, 3 short
    assert s.food["A"] == 0 and effective_strength(s, ele) == 9 - 3


def test_an_animal_starved_below_0_dies():
    s = make_state(food={"A": 0, "B": 0}, decks={"A": ["lion"] * 4, "B": ["lion"] * 4})
    put(s, "1,2", "elephant", "A")                             # a 9, Hungry 5
    end_turn(s); end_turn(s)                                   # 9 -> 4
    end_turn(s); end_turn(s)                                   # 4 -> -1: it dies
    assert s.top_unit("1,2") is None and removed(s, "elephant")


def test_a_bite_below_0_kills_even_through_armor():
    s = make_state(hands={"A": ["viper", "viper"]})
    put(s, "2,1", "stag_beetle", "B")                          # a 4 with Armor
    apply_click(s, PlaceAction("viper", ("cr", "1,1")))        # 4 -> 1
    apply_click(s, PlaceAction("viper", ("cr", "1,1")))        # 1 -> -2: dying is a rule, not an ability
    assert s.top_unit("2,1") is None and removed(s, "stag_beetle")


def test_a_crocodile_shrunk_below_3_dies_when_the_opponents_turn_starts():
    s = make_state(decks={"A": ["lion"] * 4, "B": ["lion"] * 4})
    croc = put(s, "1,2", "crocodile", "A")
    croc.strength_counter = -6                                 # an 8 bitten twice: a 2 on its own turn
    effects.resolve(s)
    assert s.top_unit("1,2") is croc
    end_turn(s)                                                # their turn: -3 more
    assert removed(s, "crocodile")


def test_a_cockroach_bitten_below_0_falls_once_and_a_fresh_one_replaces_it():
    s = make_state(hands={"A": ["viper"]})
    put(s, "2,1", "cockroach", "B")                            # a 1
    apply_click(s, PlaceAction("viper", ("cr", "1,1")))        # 1 -> -2: it falls
    back = s.top_unit("2,1")
    assert back.card_id == "cockroach" and effective_strength(s, back) == 1


def test_roach_king_bitten_below_0_comes_back_once_with_only_its_growth():
    s = make_state(hands={"A": ["viper"]}, decks={"A": [], "B": ["lion"] * 3})
    put(s, "2,1", "cockroach_legend", "B")                     # a 1
    apply_click(s, PlaceAction("viper", ("cr", "1,1")))        # 1 -> -2: it falls
    back = s.top_unit("2,1")
    assert back.card_id == "cockroach_legend" and effective_strength(s, back) == 1 + CFG.cockroach_legend_growth
    assert hand_ids(s, "B") == ["lion"]                        # one fall, one card


def test_the_legendary_dung_beetle_evolves_by_the_food_its_hungry_animals_ate():
    """"Evolves at 10 food eaten by your Hungry animals": in hand as they eat, in the deck as it's drawn."""
    s = make_state(hands={"A": ["dung_beetle_legend"]}, decks={"A": ["dung_beetle_legend"], "B": []}, food={"A": 30, "B": 0})
    rhino = put(s, "1,1", "rhinoceros", "A")
    for _ in range(4):
        assert hand_ids(s, "A") == ["dung_beetle_legend"]
        effects._eat(s, rhino, "1,1")                           # 3 a meal: 3, 6, 9, then 12
    assert s.hungry_eaten["A"] == 12 and hand_ids(s, "A") == ["dung_beetle_legend_form2"]
    s.hungry_eaten["A"] = CFG.dung_beetle_legend_play_at
    s.draw("A", 1)
    assert sorted(hand_ids(s, "A")) == ["dung_beetle_legend_form2", "dung_beetle_legend_form4"]


def test_the_legendary_dung_beetle_forms_roar():
    def roar(form):
        s = make_state(hands={"A": [form, "lion"]}, decks={"A": ["mouse"] * 3, "B": []}, food={"A": 0, "B": 0})
        rules.apply_action(s, PlaceAction(form, ("cr", "1,2")))
        return s
    s = roar("dung_beetle_legend")
    assert hand_ids(s, "A") == ["lion"] and s.food["A"] == 0 and s.pending is None   # the first form: nothing
    s = roar("dung_beetle_legend_form2")
    assert sorted(hand_ids(s, "A")) == ["lion", "mouse"] and s.food["A"] == 0
    s = roar("dung_beetle_legend_form3")
    assert len(s.hands["A"]) == 2 and s.food["A"] == CFG.dung_beetle_legend_food and s.pending is None
    s = roar("dung_beetle_legend_form4")
    assert s.food["A"] == CFG.dung_beetle_legend_food and s.pending is not None    # and another animal to play
    rules.apply_action(s, PlaceAction("lion", ("cr", "1,1")))
    assert s.top_unit("1,1").card_id == "lion"


def test_hungry_animals_count_what_they_eat_for_the_game():
    s = make_state(food={"A": 3, "B": 0}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,2", "elephant", "A")                             # Hungry 5, with 3 food to eat
    end_turn(s); end_turn(s)                                   # A's next Dawn
    assert s.hungry_eaten["A"] == 3


def test_the_legendary_oxpecker_draws_when_your_big_animal_covers_an_enemy():
    s = make_state(hands={"A": ["elephant", "lion"]}, decks={"A": ["mouse"] * 4, "B": []})
    put(s, "3,3", "oxpecker_legend", "A")                      # anywhere on the board
    put(s, "1,1", "mouse", "A")
    put(s, "2,1", "lion", "B"); put(s, "1,2", "mouse", "B")
    rules.apply_action(s, PlaceAction("lion", ("cr", "1,2")))      # a 7 covers: no draw
    assert sorted(hand_ids(s, "A")) == ["elephant"]
    rules.apply_action(s, PlaceAction("elephant", ("cr", "2,1")))  # a 9 covers: a card
    assert hand_ids(s, "A") == ["mouse"]


def test_a_sloths_food_arrives_before_the_hungry_eat():
    # The delayed payouts resolve before Dawn (Martin, 2026-10-24): the Sloth's food feeds an Elephant the turn it lands.
    s = make_state(food={"A": 0, "B": 0}, hands={"A": ["sloth"]}, decks={"A": ["lion"] * 6, "B": ["lion"] * 6})
    ele = put(s, "1,2", "elephant", "A")                       # Hungry 5
    rules.apply_action(s, PlaceAction("sloth", ("cr", "1,1")))
    while s.current == "A":
        end_turn(s)
    end_turn(s)                                                # A's next turn: no food yet, it shrinks
    assert effective_strength(s, ele) == 9 - 5
    end_turn(s); end_turn(s)                                   # the Sloth pays 30, then the Elephant eats 5
    assert s.food["A"] == CFG.sloth_food - 5 and effective_strength(s, ele) == 9 - 5


def test_titan_costs_two_actions_and_no_free_placement_pays_for_it():
    s = make_state(hands={"A": ["blue_whale", "lion"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    assert PlaceAction("blue_whale", ("cr", "1,2")) in rules.legal_actions(s)
    rules.apply_action(s, PlaceAction("blue_whale", ("cr", "1,2")))
    assert s.current == "B"                                    # both actions spent
    s2 = make_state(hands={"A": ["lion", "blue_whale"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    rules.apply_action(s2, PlaceAction("lion", ("cr", "1,1")))  # one action left
    assert not [a for a in rules.legal_actions(s2) if getattr(a, "card_id", None) == "blue_whale"]
    s3 = make_state(hands={"A": ["greywhisker", "blue_whale"]})
    rules.apply_action(s3, PlaceAction("greywhisker", ("cr", "1,1")))   # Roar "play another animal": a free placement
    assert s3.pending is None or all(p["card_id"] != "blue_whale" for p in s3.pending.get("placements", []))


def test_flee_returns_the_covered_animal_to_its_owners_hand():
    s = make_state(current="B", hands={"B": ["lion"]})
    put(s, "4,2", "lion", "B")
    put(s, "3,2", "gazelle", "A")                              # Flee, 3
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))
    assert "gazelle" in hand_ids(s, "A") and [u.card_id for u in s.board["3,2"]] == ["lion"]
    assert not removed(s, "gazelle")                           # a return, not a removal


def test_flee_runs_before_an_apex_predator_can_eat():
    s = make_state(current="B", hands={"B": ["tiger"]})
    put(s, "4,2", "lion", "B")
    put(s, "3,2", "gazelle", "A")
    rules.apply_action(s, PlaceAction("tiger", ("cr", "3,2")))
    assert "gazelle" in hand_ids(s, "A") and s.top_unit("3,2").card_id == "tiger"


def test_the_zebra_gains_food_for_each_hoofed_neighbour_and_flees():
    s = make_state(hands={"A": ["zebra"]})
    put(s, "1,1", "deer", "A"); put(s, "1,3", "okapi", "A"); put(s, "2,2", "lion", "A")   # the Giraffe is Hungry now: it would eat
    before = s.food["A"]
    rules.apply_action(s, PlaceAction("zebra", ("cr", "1,2")))       # two Hoofed neighbours; the Lion isn't one
    assert s.food["A"] - before == 2 * CFG.zebra_food
    s2 = make_state(current="B", hands={"B": ["lion"]})
    put(s2, "4,2", "lion", "B")
    put(s2, "3,2", "zebra", "A")
    rules.apply_action(s2, PlaceAction("lion", ("cr", "3,2")))
    assert "zebra" in hand_ids(s2, "A") and s2.top_unit("3,2").card_id == "lion"


def test_octopus_ink_switches_every_adjacent_enemys_effects_off_for_good():
    s = make_state(hands={"A": ["octopus", "lion"]}, decks={"A": ["lion"] * 4, "B": ["lion"] * 4})
    put(s, "1,2", "caracal", "A")
    porc = put(s, "3,2", "porcupine", "B")                     # Spikes, 7
    py = put(s, "2,3", "egg_eater", "B")                      # dynamic strength
    badger = put(s, "2,1", "honey_badger_legend", "B")       # Stealth and Armor don't keep the ink out
    s.pile_add("bird_egg", "A")
    assert effective_strength(s, py) == 2
    rules.apply_action(s, PlaceAction("octopus", ("cr", "2,2")))
    assert all(statics.inked(s, u) for u in (porc, py, badger)) and effective_strength(s, py) == 0
    assert "Spikes" not in statics.unit_keywords(s, porc) and not statics.unit_keywords(s, badger)
    assert not statics.inked(s, s.top_unit("1,2"))             # an ally isn't inked
    for _ in range(4):
        end_turn(s)
    assert statics.inked(s, porc) and statics.inked(s, badger)


def test_an_inked_animal_back_in_hand_is_a_fresh_card():
    s = make_state(hands={"A": ["octopus"]}, decks={"A": ["lion"] * 4, "B": ["lion"] * 4})
    put(s, "1,2", "caracal", "A")
    porc = put(s, "3,2", "porcupine", "B")
    rules.apply_action(s, PlaceAction("octopus", ("cr", "2,2")))
    effects._bounce(s, "3,2", porc)
    assert not statics.inked(s, s.hands["B"][-1])


def test_the_armadillo_gives_its_neighbours_armor():
    s2 = make_state(current="B", hands={"B": ["jaguar"]})
    put(s2, "3,3", "armadillo", "A")
    sq = put(s2, "3,2", "squirrel", "A")
    assert not statics.can_be_removed(s2, sq)
    put(s2, "4,3", "lion", "B")
    rules.apply_action(s2, PlaceAction("jaguar", ("cr", "4,2")))   # beside the Squirrel: no target it may remove
    assert s2.top_unit("3,2") is sq and s2.pending is None


def test_an_apex_cannot_eat_what_an_armadillo_armors():
    # The eat resolves after the cover, when the prey is already buried and out of the aura's reach;
    # it is judged as the prey stood on top, so the Squirrel is covered, not eaten.
    s = make_state(hands={"A": ["tiger"]}, food={"A": 50, "B": 0})
    put(s, "2,2", "armadillo", "B")
    sq = put(s, "1,2", "squirrel", "B")
    rules.apply_action(s, PlaceAction("tiger", ("cr", "1,2")))
    assert s.board["1,2"][0] is sq and "squirrel" not in s.remove_pile


def test_the_jellyfish_poisons_its_adjacent_animals():
    s = make_state(current="B", hands={"B": ["lion"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "4,2", "lion", "B")
    put(s, "3,3", "jellyfish", "A")
    put(s, "3,2", "squirrel", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))  # covers the poisoned Squirrel
    end_turn(s)                                                 # A's turn starts: the coverer dies
    assert s.top_unit("3,2").card_id == "squirrel" and removed(s, "lion")


# ============================================================================= Aristocrats

def test_the_legendary_cuckoo_removes_an_ally_and_plays_another_animal():
    s = make_state(hands={"A": ["cuckoo_legend", "lion"]})
    put(s, "1,1", "cockroach", "A")
    rules.apply_action(s, PlaceAction("cuckoo_legend", ("cr", "1,2")))
    choose(s, "1,1")
    assert s.pending and s.pending["mode"] == "place"         # it was yours: play another animal
    s2 = make_state(hands={"A": ["cuckoo_legend", "lion"]})
    put(s2, "2,2", "squirrel", "B")
    rules.apply_action(s2, PlaceAction("cuckoo_legend", ("cr", "1,2")))
    choose(s2, "2,2")
    assert s2.pending is None and removed(s2, "squirrel")


def test_the_legendary_sloth_makes_dusk_effects_happen_twice():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,1", "sloth_legend", "A")
    put(s, "1,2", "tortoise_legend", "A")
    end_turn(s)
    assert s.food["A"] == 2 * CFG.tortoise_legend_food


def test_praying_mantis_must_remove_an_ally_to_draw_two():
    # The cost cannot be declined (Martin, 2026-10-21): with an ally adjacent the Mantis eats; with none, nothing happens.
    s = make_state(hands={"A": ["praying_mantis"]}, decks={"A": ["lion"] * 3, "B": []})
    put(s, "1,1", "cockroach", "A")
    rules.apply_action(s, PlaceAction("praying_mantis", ("cr", "1,2")))
    assert not s.pending["optional"]
    with pytest.raises(EngineError):
        rules.apply_action(s, ChoiceAction(SKIP))
    choose(s, "1,1")
    assert hand_ids(s, "A").count("lion") == CFG.mantis_draw
    assert s.top_unit("1,1").card_id == "cockroach"            # the Cockroach came back where it was


def test_tarantula_eats_an_adjacent_ally_at_dusk_and_grows():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    t = put(s, "1,2", "tarantula", "A")
    put(s, "1,1", "lion", "A")
    end_turn(s)                                                # A's Dusk
    assert s.top_unit("1,1") is None and effective_strength(s, t) == 5 + 7


def test_the_city_spider_eats_the_cockroach_every_dawn_and_the_turn_sees_the_death():
    s = make_state(hands={"A": ["hammerhead"]}, decks={"A": ["lion"] * 5, "B": ["lion"] * 5})
    put(s, "1,2", "city_spider", "A")
    put(s, "1,1", "cockroach", "A")
    put(s, "2,1", "lion", "B")
    end_turn(s); end_turn(s)                                   # to A's next turn: Dawn
    assert s.top_unit("1,1").card_id == "cockroach"            # the weakest beside it: eaten, and back where it was
    assert hand_ids(s, "A") == ["hammerhead"]                     # it draws nothing now
    rules.apply_action(s, PlaceAction("hammerhead", ("cr", "2,2")))   # the Dawn death arms the Hammerhead
    choose(s, "2,1")
    assert s.top_unit("2,1") is None


def test_the_city_spider_eats_the_weakest_animal_beside_it_yours_or_theirs():
    s = make_state(decks={"A": ["lion"] * 5, "B": ["lion"] * 5})
    put(s, "1,2", "city_spider", "A")
    put(s, "1,1", "tiger", "A")
    put(s, "2,2", "mouse", "B")
    end_turn(s); end_turn(s)
    assert s.top_unit("2,2") is None and s.top_unit("1,1").card_id == "tiger"


def test_the_tiger_legend_eats_its_prey_then_removes_an_adjacent_enemy_of_7_but_not_8():
    for neighbour, removed in (("lion", True), ("rhinoceros_legend", False)):
        s = make_state(hands={"A": ["tiger_legend"]}, decks={"A": ["lion"] * 5, "B": ["lion"] * 5})
        put(s, "1,1", "lion", "A")
        put(s, "2,1", "mouse", "B")                            # the prey it lands on
        put(s, "2,2", neighbour, "B")
        apply_click(s, PlaceAction("tiger_legend", ("cr", "2,1")))
        assert s.top_unit("2,1").card_id == "tiger_legend" and "mouse" in s.remove_pile
        assert (s.top_unit("2,2") is None) == removed


def test_the_alley_cat_draws_two_common_cats():
    s = make_state(hands={"A": ["alley_cat"]},
                   decks={"A": ["lion_legend_3", "jaguar", "lion", "mouse", "serval"], "B": ["lion"] * 5})
    rules.apply_action(s, PlaceAction("alley_cat", ("cr", "1,2")))
    assert sorted(hand_ids(s, "A")) == ["lion", "serval"]


def test_sea_turtle_adds_a_baby_turtle_to_your_hand_at_dusk():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,2", "sea_turtle", "A")
    end_turn(s)
    assert hand_ids(s, "A") == ["baby_turtle"] and s.top_unit("1,3") is None


def test_raccoon_returns_only_your_own_removed_animal():
    s = make_state(hands={"A": ["raccoon"]})
    s.pile_add("tiger", "B"); s.pile_add("lion", "A")
    rules.apply_action(s, PlaceAction("raccoon", ("cr", "1,2")))
    assert s.pending["options"] == ["lion"]
    choose(s, "lion")
    assert "lion" in hand_ids(s, "A") and s.remove_pile == ["tiger"]


def test_the_hammerhead_needs_an_ally_removed_this_turn():
    s = make_state(hands={"A": ["hammerhead", "hammerhead"]})
    put(s, "2,2", "lion", "B")
    apply_click(s, PlaceAction("hammerhead", ("cr", "1,2")))
    assert s.top_unit("2,2") is not None                       # no blood in the water
    put(s, "1,1", "cockroach", "A")
    effects.remove_top(s, "1,1", by_player="B")
    rules.apply_action(s, PlaceAction("hammerhead", ("cr", "1,2")))   # on top of the first one, beside the Lion
    assert set(s.pending["options"]) >= {"1,1", "2,2"}         # any animal beside it, the Cockroach too
    choose(s, "2,2")
    assert s.top_unit("2,2") is None


def test_hyena_gains_food_for_each_animal_removed_this_turn_either_players():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,2", "hyena", "A")
    for cr, owner in (("1,1", "A"), ("1,3", "A"), ("3,2", "B")):
        put(s, cr, "lion", owner)
        effects.remove_top(s, cr, by_player="B" if owner == "A" else "A")
    end_turn(s)
    assert s.food["A"] == 3 * CFG.hyena_food_per


def test_earthworm_leaves_two_worms_and_a_worm_draws_when_removed():
    s = make_state(decks={"A": ["lion"] * 3, "B": []})
    put(s, "1,2", "earthworm", "A")
    effects.remove_top(s, "1,2", by_player="B")
    assert [u.card_id for u in s.board["1,2"]] == ["worm", "worm"] and hand_ids(s, "A") == ["lion"]
    effects.remove_top(s, "1,2", by_player="B")
    assert hand_ids(s, "A") == ["lion", "lion"]


def test_cockroach_comes_back_where_it_was_and_spreads_a_roach():
    s = make_state(decks={"A": ["lion"], "B": []})
    put(s, "1,2", "cockroach", "A")
    effects.remove_top(s, "1,2", by_player="B")
    assert not removed(s, "cockroach") and hand_ids(s, "A") == []
    assert s.top_unit("1,2").card_id == "cockroach" and s.top_unit("1,2").owner == "A"
    roaches = [cr for cr in ("1,1", "1,3", "2,2") if (t := s.top_unit(cr)) and t.card_id == "roach" and t.owner == "A"]
    assert len(roaches) == 1


def test_a_cockroach_with_no_empty_neighbour_spreads_nothing():
    s = make_state(decks={"A": ["lion"], "B": []})
    put(s, "1,1", "cockroach", "A")
    put(s, "1,2", "lion", "B"); put(s, "2,1", "lion", "B")
    effects.remove_top(s, "1,1", by_player="B")
    assert s.top_unit("1,1").card_id == "cockroach" and "roach" not in {st[-1].card_id for st in s.board.values()}


def test_roach_king_comes_back_stronger_and_draws():
    s = make_state(decks={"A": ["lion"], "B": []})
    put(s, "1,2", "cockroach_legend", "A")
    effects.remove_top(s, "1,2", by_player="B")
    king = s.top_unit("1,2")
    assert king.card_id == "cockroach_legend" and effective_strength(s, king) == 1 + CFG.cockroach_legend_growth
    assert hand_ids(s, "A") == ["lion"] and "cockroach_legend" not in s.decks["A"]


def test_the_dart_frog_takes_everything_beside_it_when_removed():
    s = make_state(hands={"A": ["praying_mantis"]}, decks={"A": ["lion"] * 3, "B": []})
    put(s, "1,2", "dart_frog", "A")
    put(s, "2,2", "tiger", "B"); put(s, "1,1", "lion", "A")
    rules.apply_action(s, PlaceAction("praying_mantis", ("cr", "1,3")))
    choose(s, "1,2")                                           # the Mantis eats the Frog: everything beside it goes
    assert all(s.top_unit(cr) is None for cr in ("1,1", "1,2", "1,3", "2,2"))


def test_the_toad_has_poison_and_nothing_more():
    assert set(load_cards()["toad"].keywords) == {"Poison"} and load_cards()["toad"].text == "Poison."


def test_vultures_land_from_hand_and_deck_after_three_removals():
    s = make_state(hands={"A": ["vulture"]}, decks={"A": ["vulture", "lion"], "B": ["lion"] * 3})
    for cr in ("1,1", "1,2", "1,3"):
        put(s, cr, "mouse", "B")
    for cr in ("1,1", "1,2"):
        effects.remove_top(s, cr, by_player="A")
    assert CFG.vulture_removals == 3                           # two removed: they stay put
    probe = s.clone(); end_turn(probe)
    assert not any(st[-1].card_id == "vulture" for st in probe.board.values())
    effects.remove_top(s, "1,3", by_player="A")
    end_turn(s)
    assert sum(st[-1].card_id == "vulture" and st[-1].owner == "A" for st in s.board.values()) == 2
    assert hand_ids(s, "A") == [] and s.decks["A"] == ["lion"]


def test_a_buried_cockroach_comes_back_buried_at_the_same_height():
    s = make_state(decks={"A": ["lion"], "B": []})
    put(s, "1,2", "mouse", "A")
    put(s, "1,2", "cockroach", "A")
    put(s, "1,2", "lion", "B")                                 # covered by an enemy
    roach = s.board["1,2"][1]
    effects._remove_specific(s, "1,2", roach, by_player="B")
    assert [u.card_id for u in s.board["1,2"]] == ["mouse", "cockroach", "lion"]


# ================================================================================= Canines

def test_clarion_gives_a_free_roam_to_any_ally():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,1", "wolf_legend_3", "A")
    put(s, "1,2", "wolf", "A")                            # Wolf: Roam
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,1")))
    assert s.actions_taken_this_turn == 0                      # the free roam paid
    s2 = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s2, "1,1", "wolf_legend_3", "A")
    put(s2, "1,2", "orca", "A")                                # Roam, not a Canine
    put(s2, "2,1", "squirrel", "A")
    rules.apply_action(s2, RoamAction("1,2", ("cr", "2,1")))
    assert s2.actions_taken_this_turn == 0


def test_the_black_wolf_grows_and_draws_for_every_canine_that_roams_itself_included():
    s = make_state(decks={"A": ["lion"] * 3, "B": []})
    put(s, "1,1", "wolf_legend_2", "A")
    w = put(s, "1,2", "wolf", "A")
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,1")))             # onto an empty crossroad: any roam counts
    assert (w.strength_counter, hand_ids(s, "A")) == (CFG.black_wolf_grant, ["lion"] * CFG.black_wolf_draw)
    s = make_state(decks={"A": ["lion"] * 3, "B": []})
    me = put(s, "1,1", "wolf_legend_2", "A")
    rules.apply_action(s, RoamAction("1,1", ("cr", "2,1")))             # its own roam triggers it too
    assert (me.strength_counter, hand_ids(s, "A")) == (CFG.black_wolf_grant, ["lion"] * CFG.black_wolf_draw)
    s = make_state(decks={"A": ["lion"] * 3, "B": []})
    put(s, "1,1", "wolf_legend_2", "A")
    orca = put(s, "1,2", "orca", "A")                                  # Roam, not a Canine
    put(s, "2,1", "squirrel", "B")
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,1")))
    assert (orca.strength_counter, hand_ids(s, "A")) == (0, [])


def test_the_legendary_wolf_grows_at_dusk_by_its_adjacent_canines():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    w = put(s, "1,2", "wolf_legend", "A")
    put(s, "1,1", "wolf", "A"); put(s, "1,3", "jackal", "A")    # two Canines beside it
    put(s, "2,2", "squirrel", "A")                             # not a Canine: doesn't count
    end_turn(s)
    assert w.strength_counter == 2 * CFG.wolf_legend_grant


def test_the_bush_dog_leaves_a_pup_on_the_crossroad_it_left_unless_an_animal_resurfaced():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,2", "bush_dog", "A")
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    pup = s.top_unit("1,2")
    assert pup is not None and pup.card_id == "pup" and pup.owner == "A" and s.top_unit("2,2").card_id == "bush_dog"
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,2", "lion", "A")
    put(s, "1,2", "bush_dog", "A")                             # it stands on a Lion
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert [u.card_id for u in s.board["1,2"]] == ["lion"]


def test_the_fox_draws_two_only_if_an_ally_roamed_this_turn():
    def play(roamer, target):
        s = make_state(hands={"A": ["fox"]}, decks={"A": ["lion"] * 4, "B": []})
        put(s, "1,1", roamer, "A")
        if target:
            put(s, target, "squirrel", "B")
        rules.apply_action(s, RoamAction("1,1", ("cr", target or "2,1")))
        rules.apply_action(s, PlaceAction("fox", ("cr", "1,2")))
        return hand_ids(s, "A")
    assert play("wolf", None) == ["lion"] * CFG.fox_draw       # a Canine roamed
    assert play("orca", "2,1") == ["lion"] * CFG.fox_draw      # so does any other ally
    s = make_state(hands={"A": ["fox"]}, decks={"A": ["lion"] * 4, "B": []})
    rules.apply_action(s, PlaceAction("fox", ("cr", "1,2")))
    assert hand_ids(s, "A") == []                              # nobody roamed


def test_the_fox_counts_a_roam_a_free_roam_paid():
    s = make_state(hands={"A": ["fox"]}, decks={"A": ["lion"] * 4, "B": []})
    put(s, "1,1", "wolf_legend_3", "A")                        # Clarion: a free roam each turn
    put(s, "1,2", "wolf", "A")
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,1")))
    assert s.actions_taken_this_turn == 0
    rules.apply_action(s, PlaceAction("fox", ("cr", "1,3")))
    assert hand_ids(s, "A") == ["lion"] * CFG.fox_draw


def test_wolverine_removes_an_adjacent_enemy_only_if_no_other_enemy_is_next_to_it():
    s = make_state(hands={"A": ["wolverine"]})
    put(s, "1,1", "lion", "A")
    put(s, "2,2", "lion", "B")
    apply_click(s, PlaceAction("wolverine", ("cr", "1,2")))
    assert s.top_unit("2,2") is None
    s = make_state(hands={"A": ["wolverine"]})
    put(s, "1,1", "lion", "A")
    put(s, "2,2", "lion", "B")
    put(s, "3,2", "squirrel", "B")                             # another enemy beside the Lion
    rules.apply_action(s, PlaceAction("wolverine", ("cr", "1,2")))
    assert s.pending is None and s.top_unit("2,2") is not None


def test_jackal_removes_only_an_enemy_another_canine_flanks():
    s = make_state(hands={"A": ["jackal"]})
    put(s, "1,1", "lion", "A")
    put(s, "2,2", "lion", "B")
    rules.apply_action(s, PlaceAction("jackal", ("cr", "1,2")))
    assert s.pending is None                                   # nobody flanks the Lion
    s2 = make_state(hands={"A": ["jackal"]})
    put(s2, "2,1", "wolf", "A")
    put(s2, "1,1", "lion", "A")
    put(s2, "2,2", "lion", "B")
    apply_click(s2, PlaceAction("jackal", ("cr", "1,2")))
    assert s2.top_unit("2,2") is None


def test_the_dhole_has_no_equal_strength_cover_for_anyone():
    s = make_state(hands={"A": ["wolf"]})
    put(s, "1,1", "dhole", "A")
    put(s, "1,2", "wolf", "A")                                 # a 6 with Roam
    put(s, "2,1", "caracal", "B")                              # a 6
    assert RoamAction("1,2", ("cr", "2,1")) not in rules.legal_actions(s)
    assert PlaceAction("wolf", ("cr", "2,1")) not in rules.legal_actions(s)


def test_the_dhole_draws_two_when_it_covers_an_enemy_with_no_other_enemy_next_to_it():
    s = make_state(hands={"A": ["dhole"]}, decks={"A": ["lion"] * 4, "B": []})
    put(s, "1,1", "lion", "A")
    put(s, "2,1", "squirrel", "B")
    rules.apply_action(s, PlaceAction("dhole", ("cr", "2,1")))     # placed: alone, so it draws
    assert hand_ids(s, "A") == ["lion"] * CFG.dhole_draw
    s = make_state(hands={"A": ["dhole"]}, decks={"A": ["lion"] * 4, "B": []})
    put(s, "1,1", "lion", "A")
    put(s, "2,1", "squirrel", "B")
    put(s, "2,2", "squirrel", "B")                             # another enemy beside it
    rules.apply_action(s, PlaceAction("dhole", ("cr", "2,1")))
    assert hand_ids(s, "A") == []
    s = make_state(decks={"A": ["lion"] * 4, "B": []})
    put(s, "1,1", "dhole", "A")
    put(s, "2,1", "squirrel", "B")
    rules.apply_action(s, RoamAction("1,1", ("cr", "2,1")))        # roaming covers too
    assert hand_ids(s, "A") == ["lion"] * CFG.dhole_draw
    s = make_state(decks={"A": ["lion"] * 4, "B": []})
    put(s, "1,1", "dhole", "A")
    put(s, "2,1", "squirrel", "B")
    rules.apply_action(s, RoamAction("1,1", ("cr", "1,2")))        # onto an empty crossroad: nothing covered
    assert hand_ids(s, "A") == []


def test_coyote_gives_a_connected_ally_roam_and_it_roams_now():
    s = make_state(hands={"A": ["coyote"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    ally = put(s, "1,1", "lion", "A")
    put(s, "2,2", "squirrel", "A")
    put(s, "3,2", "squirrel", "A")                             # connected through 2,2
    put(s, "4,3", "squirrel", "A")                             # no chain of your animals to it
    put(s, "1,3", "squirrel", "B")                             # an enemy is never chosen
    rules.apply_action(s, PlaceAction("coyote", ("cr", "1,2")))
    assert s.pending["options"] == ["1,1", "2,2", "3,2"]
    assert not statics.can_roam(s, ally)
    choose(s, "1,1")
    assert ally.strength_counter == 0 and statics.can_roam(s, ally)
    assert "2,1" in s.pending["options"]                       # it roams now: you pick where it lands
    choose(s, "2,1")
    assert s.pending is None and s.top_unit("2,1") is ally and s.actions_taken_this_turn == 1
    assert RoamAction("2,1", ("cr", "1,1")) in rules.legal_actions(s)   # its own roam of the turn is still there


def test_the_coyotes_roam_goes_when_the_animal_leaves_the_board():
    s = make_state(hands={"A": ["coyote"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    ally = put(s, "1,1", "lion", "A")
    rules.apply_action(s, PlaceAction("coyote", ("cr", "1,2")))
    choose(s, "1,1")
    choose(s, "2,1")
    assert ally.granted_roam and s.clone().top_unit("2,1").granted_roam    # a clone keeps it
    assert UnitInstance.from_dict(ally.to_dict()).granted_roam              # so does a saved game
    effects._bounce(s, "2,1", ally)
    assert not hand_inst(s, "A", "lion").granted_roam


def test_coyote_with_no_connected_ally_just_lands():
    s = make_state(hands={"A": ["coyote"]})
    put(s, "4,3", "lion", "A")
    rules.apply_action(s, PlaceAction("coyote", ("cr", "1,2")))
    assert s.pending is None


def test_street_dog_gives_a_connected_ally_with_roam_plus_three_and_it_roams_now():
    s = make_state(hands={"A": ["street_dog"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    wolf = put(s, "1,1", "wolf", "A")
    put(s, "2,2", "squirrel", "A")                             # connected, but no Roam
    put(s, "3,2", "wolf", "A")                                 # connected through 2,2
    put(s, "4,3", "wolf", "A")                                 # no chain of your animals to it
    rules.apply_action(s, PlaceAction("street_dog", ("cr", "1,2")))
    assert s.pending["options"] == ["1,1", "3,2"]
    choose(s, "1,1")
    assert wolf.strength_counter == CFG.street_dog_grant
    choose(s, "2,1")
    assert s.pending is None and s.top_unit("2,1") is wolf and s.actions_taken_this_turn == 1
    assert {a.origin for a in rules.legal_actions(s) if isinstance(a, RoamAction)} == {"2,1", "3,2", "4,3"}   # the free roam left nothing behind


def test_it_roams_takes_the_den():
    s = make_state(hands={"A": ["street_dog"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    for cr in ("1,1", "2,1", "3,1"):
        put(s, cr, "squirrel", "A")                            # a chain from your den to the enemy's den front
    put(s, "4,1", "wolf", "A")
    rules.apply_action(s, PlaceAction("street_dog", ("cr", "1,2")))
    choose(s, "4,1")
    assert "den" in s.pending["options"]
    choose(s, "den")
    assert s.result is not None and s.result.winner == "A"


def test_street_dog_moves_an_animal_that_already_roamed():
    s = make_state(hands={"A": ["street_dog"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,1", "bush_dog", "A")
    rules.apply_action(s, RoamAction("1,1", ("cr", "2,1")))    # its own roam of the turn (it leaves a Pup)
    rules.apply_action(s, PlaceAction("street_dog", ("cr", "1,2")))
    choose(s, "2,1")
    assert s.pending is not None and s.pending["options"]      # it roams again (Martin's game of 2026-10-28, turn 7)


def test_street_dog_with_no_connected_roamer_just_lands():
    s = make_state(hands={"A": ["street_dog"]})
    put(s, "1,1", "lion", "A")
    rules.apply_action(s, PlaceAction("street_dog", ("cr", "1,2")))
    assert s.pending is None


def test_african_wild_dog_makes_a_canine_played_next_to_it_roam():
    s = make_state(hands={"A": ["jackal"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,1", "african_wild_dog", "A")
    rules.apply_action(s, PlaceAction("jackal", ("cr", "1,2")))   # a Canine without Roam of its own
    jackal = s.top_unit("1,2")
    assert "2,2" in s.pending["options"]
    choose(s, "2,2")
    assert s.pending is None and s.top_unit("2,2") is jackal and s.actions_taken_this_turn == 1


def test_african_wild_dog_ignores_what_isnt_a_canine_played_next_to_it():
    s = make_state(hands={"A": ["lion", "wolf"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,1", "african_wild_dog", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "1,2")))      # not a Canine
    assert s.pending is None
    rules.apply_action(s, PlaceAction("wolf", ("cr", "1,3")))      # a Canine, but not next to it
    assert s.pending is None


def test_african_wild_dog_does_not_move_a_token_or_a_roamer():
    s = make_state(hands={"A": ["bush_dog"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,1", "african_wild_dog", "A")
    rules.apply_action(s, PlaceAction("bush_dog", ("cr", "1,2")))
    choose(s, "2,2")                                          # the Bush Dog roams, leaving a Pup next to the Wild Dog
    assert s.top_unit("1,2").card_id == "pup" and s.pending is None   # a placed token isn't played


def test_badger_draws_an_animal_with_roam():
    s = make_state(hands={"A": ["badger"]}, decks={"A": ["lion", "orca", "squirrel"], "B": []})
    rules.apply_action(s, PlaceAction("badger", ("cr", "1,2")))
    assert hand_ids(s, "A") == ["orca"]


# ==================================================================================== Cats

def test_serval_removes_an_adjacent_enemy_of_any_strength_only_after_another_cat_this_turn():
    # A Cat already on the board isn't enough: it has to be played this turn.
    s = make_state(hands={"A": ["serval"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,1", "lion", "A")
    put(s, "2,2", "elephant", "B")
    apply_click(s, PlaceAction("serval", ("cr", "1,2")))
    assert s.top_unit("2,2").card_id == "elephant"
    s = make_state(hands={"A": ["lion", "serval"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "2,2", "elephant", "B")
    apply_click(s, PlaceAction("lion", ("cr", "1,1")))
    apply_click(s, PlaceAction("serval", ("cr", "1,2")))
    assert s.top_unit("2,2") is None and "elephant" in s.remove_pile


def test_a_serval_played_alone_does_not_count_itself():
    s = make_state(hands={"A": ["serval", "serval"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "2,2", "elephant", "B")
    apply_click(s, PlaceAction("serval", ("cr", "1,2")))
    assert s.top_unit("2,2").card_id == "elephant"


def test_lynx_draws_only_when_placed_on_an_enemy():
    s = make_state(hands={"A": ["lynx", "lynx"]}, decks={"A": ["lion"] * 3, "B": []})
    rules.apply_action(s, PlaceAction("lynx", ("cr", "1,2")))
    assert hand_ids(s, "A") == ["lynx"]
    put(s, "2,2", "squirrel", "B")
    rules.apply_action(s, PlaceAction("lynx", ("cr", "2,2")))
    assert hand_ids(s, "A") == ["lion"] * CFG.lynx_draw          # the rare draws 2 (2026-10-21)


# ================================================================================ Den Rush

def test_legendary_mole_gains_draws_plays_then_discards():
    s = make_state(hands={"A": ["mole_legend", "lion", "tiger"]}, decks={"A": ["squirrel"], "B": []})
    rules.apply_action(s, PlaceAction("mole_legend", ("cr", "1,2")))
    assert s.food["A"] == CFG.greywhisker_food and "squirrel" in hand_ids(s, "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "1,1")))      # play another animal
    assert s.pending["mode"] == "choice"                           # then discard a card of your choice
    choose(s, hand_inst(s, "A", "tiger").iid)
    assert hand_ids(s, "A") == ["squirrel"] and removed(s, "tiger")


def test_hare_draws_after_three_animals_this_turn():
    s = make_state(hands={"A": ["hare"]}, decks={"A": ["lion"] * 3, "B": []})
    s.units_placed_this_turn = 2
    rules.apply_action(s, PlaceAction("hare", ("cr", "1,2")))
    assert hand_ids(s, "A") == ["lion"] * CFG.hare_draw


def test_the_rat_removes_only_as_the_third_animal_of_a_turn_and_discards_nothing():
    s = make_state(hands={"A": ["rat", "lion"]})
    put(s, "2,2", "tiger", "B")
    s.units_placed_this_turn = 1                                 # the Rat is the second: no swarm
    rules.apply_action(s, PlaceAction("rat", ("cr", "1,2")))
    assert not s.pending and s.top_unit("2,2").card_id == "tiger" and hand_ids(s, "A") == ["lion"]
    s2 = make_state(hands={"A": ["rat", "lion"]})
    put(s2, "2,2", "tiger", "B")
    s2.units_placed_this_turn = 2
    rules.apply_action(s2, PlaceAction("rat", ("cr", "1,2")))
    choose(s2, "2,2")
    assert s2.top_unit("2,2") is None and hand_ids(s2, "A") == ["lion"]


# ============================================================================= Egg Control

def test_the_legendary_raven_takes_two_from_the_opponents_remove_pile():
    s = make_state(hands={"A": ["raven_legend"]})
    s.pile_add("tiger", "B"); s.pile_add("eagle", "B"); s.pile_add("lion", "A")
    rules.apply_action(s, PlaceAction("raven_legend", ("cr", "1,2")))
    assert s.pending["options"] == ["eagle", "tiger"]
    choose(s, "tiger")
    assert s.pending["options"] == ["eagle"]                 # asked afresh: the Tiger is gone
    choose(s, "eagle")
    assert sorted(hand_ids(s, "A")) == ["eagle", "tiger"] and hand_inst(s, "A", "tiger").owner == "A"
    assert s.remove_pile == ["lion"]


def test_the_legendary_raven_takes_what_there_is():
    s = make_state(hands={"A": ["raven_legend"]})
    s.pile_add("tiger", "B")
    rules.apply_action(s, PlaceAction("raven_legend", ("cr", "1,2")))
    choose(s, "tiger")
    assert s.pending is None and hand_ids(s, "A") == ["tiger"]


def test_mosquito_drains_two():
    s = make_state(hands={"A": ["mosquito"]})
    t = put(s, "2,2", "tiger", "B")
    apply_click(s, PlaceAction("mosquito", ("cr", "1,2")))
    assert effective_strength(s, t) == 7 - CFG.mosquito_drain


def test_black_swan_discards_on_every_draw():
    s = make_state(decks={"A": ["swan_legend", "swan_legend"], "B": []})
    for _ in range(2):
        s.add_to_hand("B", "lion")
    effects.draw_cards(s, "A", 2)
    assert s.hands["B"] == []


# ==================================================================================== Fish

def test_the_legendary_tuna_pays_per_region():
    s = make_state(hands={"A": ["tuna_legend"]}, decks={"A": ["lion"] * 3, "B": []})
    for cr in ("1,1", "2,1", "2,2"):
        put(s, cr, "sardine", "A")
    rules.apply_action(s, PlaceAction("tuna_legend", ("cr", "1,2")))   # closes R1
    assert s.food["A"] == CFG.tuna_legend_food and len(s.hands["A"]) == 1


def test_the_legendary_manta_ray_draws_two_at_dusk_with_two_regions():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    for cr in ("1,1", "2,1", "2,2", "1,3", "2,3"):
        put(s, cr, "sardine", "A")
    put(s, "1,2", "manta_ray_legend", "A")                # R1 and R4
    end_turn(s)
    assert len(s.hands["A"]) == CFG.manta_legend_draw == 2


def test_the_piranha_lets_fish_cover_up_to_the_school_size():
    s = make_state(hands={"A": ["sardine"]})
    for cr in ("1,1", "1,3"):
        put(s, cr, "sardine", "A")
    put(s, "2,1", "piranha", "A")                  # 3 Fish on the board
    put(s, "1,2", "lion", "B")                                 # a 7: too big
    put(s, "2,2", "chameleon", "B")
    assert PlaceAction("sardine", ("cr", "1,2")) not in rules.legal_actions(s)
    s.board["1,2"][-1].strength_counter = -4                   # now a 3
    assert PlaceAction("sardine", ("cr", "1,2")) in rules.legal_actions(s)


def test_swordfish_removes_a_random_enemy_per_adjacent_allied_fish():
    s = make_state(hands={"A": ["swordfish"]})
    put(s, "1,1", "sardine", "A")
    put(s, "2,2", "lion", "B"); put(s, "1,3", "lion", "B")
    rules.apply_action(s, PlaceAction("swordfish", ("cr", "1,2")))
    assert s.remove_pile == ["lion"]                           # one Fish beside it: one enemy


def test_barracuda_removes_up_to_the_number_of_your_fish():
    s = make_state(hands={"A": ["barracuda"]})
    put(s, "1,1", "sardine", "A")
    put(s, "2,2", "baby_turtle", "B")
    put(s, "1,3", "squirrel", "B")                             # 3 > 2 Fish
    apply_click(s, PlaceAction("barracuda", ("cr", "1,2")))
    assert removed(s, "baby_turtle") and s.top_unit("1,3") is not None


def test_the_legendary_sardine_counts_each_fish_twice():
    s = make_state(hands={"A": ["barracuda"]})
    put(s, "1,1", "sardine_legend", "A")
    tuna = put(s, "2,1", "tuna", "A")
    assert effective_strength(s, tuna) == 3 + 2                # one other Fish, counted twice
    put(s, "1,3", "squirrel", "B")                             # 3 <= 3 Fish counted as 6
    apply_click(s, PlaceAction("barracuda", ("cr", "1,2")))
    assert removed(s, "squirrel")


def test_a_covered_legendary_sardine_stops_counting_double():
    s = make_state()
    put(s, "1,1", "sardine_legend", "A")
    tuna = put(s, "2,1", "tuna", "A")
    put(s, "1,1", "lion", "B")
    assert effective_strength(s, tuna) == 3


def test_the_legendary_piranha_removes_each_enemy_next_to_two_of_your_fish():
    s = make_state(hands={"A": ["piranha_legend"]})
    put(s, "2,1", "sardine", "A")
    put(s, "2,2", "lion", "B")                                 # next to the Sardine and the Piranha
    put(s, "3,1", "squirrel", "B")                             # next to the Sardine only
    rules.apply_action(s, PlaceAction("piranha_legend", ("cr", "1,2")))
    assert removed(s, "lion") and s.top_unit("3,1").card_id == "squirrel"


def test_the_legendary_piranha_with_the_legendary_sardine_needs_one_fish():
    s = make_state(hands={"A": ["piranha_legend"]})
    put(s, "2,1", "sardine_legend", "A")
    put(s, "3,1", "squirrel", "B")                             # one Fish, counted twice
    rules.apply_action(s, PlaceAction("piranha_legend", ("cr", "1,2")))
    assert removed(s, "squirrel")


def test_manta_ray_draws_when_the_opponent_covers_an_adjacent_allied_fish():
    s = make_state(current="B", hands={"B": ["lion"]}, decks={"A": ["lion"], "B": []})
    put(s, "4,2", "lion", "B")
    put(s, "3,3", "manta_ray", "A")
    put(s, "3,2", "sardine", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))
    assert hand_ids(s, "A") == ["lion"]


def test_manta_ray_ignores_a_fish_covered_away_from_it():
    s = make_state(current="B", hands={"B": ["lion"]}, decks={"A": ["lion"], "B": []})
    put(s, "4,2", "lion", "B")
    put(s, "1,1", "manta_ray", "A")
    put(s, "3,2", "sardine", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))
    assert hand_ids(s, "A") == []


def test_cod_draws_per_adjacent_allied_fish_and_remora_plays_a_fish():
    s = make_state(hands={"A": ["cod"]}, decks={"A": ["lion"] * 3, "B": []})
    put(s, "1,1", "sardine", "A"); put(s, "1,3", "tuna", "A")
    rules.apply_action(s, PlaceAction("cod", ("cr", "1,2")))
    assert len(s.hands["A"]) == 2
    s2 = make_state(hands={"A": ["remora", "lion", "sardine"]})
    rules.apply_action(s2, PlaceAction("remora", ("cr", "1,2")))     # no Fish beside it: no extra play
    assert not s2.pending
    s3 = make_state(hands={"A": ["remora", "lion", "sardine"]})
    put(s3, "1,1", "tuna", "A")
    rules.apply_action(s3, PlaceAction("remora", ("cr", "1,2")))
    assert {p["card_id"] for p in s3.pending["placements"]} == {"sardine"}


def test_sardines_fill_adjacent_empty_crossroads_from_hand_and_deck_without_roaring():
    s = make_state(hands={"A": ["sardine", "sardine"]}, decks={"A": ["sardine", "lion"], "B": []})
    rules.apply_action(s, PlaceAction("sardine", ("cr", "1,2")))   # neighbours 1,1 1,3 2,2: three spots
    assert sum(u.card_id == "sardine" for st in s.board.values() for u in st) == 3
    assert s.decks["A"] == ["lion"] and hand_ids(s, "A") == []


def test_mahi_mahi_mackerel_and_tuna_grow_the_school():
    s = make_state(hands={"A": ["mahi_mahi"]})
    sar = put(s, "1,1", "sardine", "A")
    tuna = put(s, "1,3", "tuna", "A")
    assert effective_strength(s, tuna) == 3 + 1                # one other Fish
    rules.apply_action(s, PlaceAction("mahi_mahi", ("cr", "1,2")))
    assert sar.strength_counter == CFG.mahi_mahi_grant
    put(s, "2,2", "mackerel", "A")
    assert effective_strength(s, sar) == load_cards()["sardine"].base_strength + CFG.mahi_mahi_grant + CFG.mackerel_anthem


def test_sunfish_places_a_baby_fish_on_a_random_adjacent_empty_crossroad():
    s = make_state(hands={"A": ["sunfish"]})
    put(s, "1,1", "lion", "B"); put(s, "1,3", "lion", "A")    # 2,2 is its only empty neighbour
    rules.apply_action(s, PlaceAction("sunfish", ("cr", "1,2")))
    assert not s.effect_stack                                  # no choice asked
    assert s.top_unit("2,2").card_id == "baby_fish" and s.top_unit("2,2").owner == "A"


def test_deer_places_a_fawn_and_the_gazelle_draws_and_feeds():
    s = make_state(hands={"A": ["deer"]})
    put(s, "1,1", "lion", "B"); put(s, "1,3", "lion", "A")
    rules.apply_action(s, PlaceAction("deer", ("cr", "1,2")))
    assert s.top_unit("2,2").card_id == "fawn" and s.top_unit("2,2").owner == "A"
    s2 = make_state(hands={"A": ["gazelle"]}, decks={"A": ["lion"] * 3, "B": []})
    before = s2.food["A"]
    rules.apply_action(s2, PlaceAction("gazelle", ("cr", "1,2")))
    assert hand_ids(s2, "A") == ["lion"] and s2.food["A"] - before == CFG.gazelle_food


# ============================================================================= Food Aggro

def test_the_repeat_legend_roars_its_adjacent_rodents_again():
    s = make_state(hands={"A": ["capybara_legend"]})
    put(s, "1,1", "squirrel", "A"); put(s, "2,2", "squirrel", "A")
    put(s, "1,3", "lion", "A")                                 # not a Rodent
    rules.apply_action(s, PlaceAction("capybara_legend", ("cr", "1,2")))
    assert s.food["A"] == 2 * CFG.squirrel_food


def test_the_repeat_legend_absorbs_the_roars_so_they_happen_where_it_stands():
    s = make_state(hands={"A": ["capybara_legend"]})
    put(s, "1,3", "lion", "A"); put(s, "2,3", "lion", "A")    # the path from the den
    put(s, "3,2", "gopher", "A")
    put(s, "4,3", "lion", "B")                                 # next to Big Gus's 3,3, not to the Gopher
    s.turn_flags["food_gained_A"] = CFG.fed_threshold
    rules.apply_action(s, PlaceAction("capybara_legend", ("cr", "3,3")))
    choose(s, "4,3")                                           # the Gopher's repeat reaches the enemy next to Big Gus
    assert s.owner_of("4,3") is None


def test_two_repeat_legends_side_by_side_do_not_repeat_each_other_for_ever():
    s = make_state(hands={"A": ["capybara_legend"]})
    put(s, "1,1", "capybara_legend", "A")             # a mimic Octopus's copy, say
    put(s, "2,2", "squirrel", "A")
    rules.apply_action(s, PlaceAction("capybara_legend", ("cr", "1,2")))
    assert s.food["A"] == CFG.squirrel_food


def test_the_refill_legend_draws_up_to_the_opponents_hand():
    s = make_state(hands={"A": ["macaque_legend"], "B": ["lion"] * 4}, decks={"A": ["lion"] * 9, "B": []})
    rules.apply_action(s, PlaceAction("macaque_legend", ("cr", "1,2")))
    assert len(s.hands["A"]) == 4


def test_meerkat_draws_when_an_enemy_lands_beside_it():
    s = make_state(current="B", hands={"B": ["lion"]}, decks={"A": ["lion"], "B": []})
    put(s, "4,2", "lion", "B")
    put(s, "2,2", "meerkat", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))
    assert hand_ids(s, "A") == ["lion"]


def test_the_dormouse_draws_at_dusk_after_a_food_turn_and_region_income_never_counts():
    s = make_state(hands={"A": ["squirrel"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,2", "dormouse", "A")
    end_turn(s)                                                  # no food this turn: no card
    assert hand_ids(s, "A") == ["squirrel"]
    s2 = make_state(hands={"A": ["squirrel"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s2, "1,2", "dormouse", "A")
    rules.apply_action(s2, PlaceAction("squirrel", ("cr", "2,2")))    # 10 food from a Roar
    end_turn(s2)
    assert hand_ids(s2, "A") == ["lion"]
    s4 = make_state(hands={"A": []}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s4, "1,2", "dormouse", "A")
    s4.turn_flags["food_gained_A"] = 29                              # a card for each whole 10
    end_turn(s4)
    assert hand_ids(s4, "A") == ["lion", "lion"]
    s3 = make_state(hands={"A": []}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    for cr in ("1,1", "1,2", "2,1", "2,2"):                          # a held region pays at the end of the turn
        put(s3, cr, "lion", "A")
    put(s3, "1,3", "dormouse", "A")
    end_turn(s3)
    assert hand_ids(s3, "A") == []


def test_groundhog_feeds_you_at_dawn_and_the_turn_starts_fed():
    s = make_state(hands={"A": ["groundhog", "lion"], "B": ["lion"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    rules.apply_action(s, PlaceAction("groundhog", ("cr", "1,2")))
    assert s.food["A"] == 0                                          # nothing when it is played
    end_turn(s)
    end_turn(s)                                                      # the opponent's turn: nothing either
    assert s.current == "A" and s.food["A"] == Config.default().groundhog_food
    assert effects._food_gained_this_turn(s, "A") == Config.default().fed_threshold   # Gopher and Mara are armed from the first action


def test_the_hamster_grows_with_your_food_in_hand_and_on_the_board():
    s = make_state(hands={"A": ["hamster"]}, food={"A": 39, "B": 0})
    assert placement_strength(s, hand_inst(s, "A", "hamster")) == 3 + 3     # 39 is three whole tens
    put(s, "1,2", "squirrel", "B")                                          # a 3: the 5 covers it
    rules.apply_action(s, PlaceAction("hamster", ("cr", "1,2")))
    assert s.board["1,2"][-1].card_id == "hamster"


# ================================================================================ Food OTK

def test_the_legendary_squirrel_stakes_your_food_and_triples_it_in_two_turns():
    s = make_state(hands={"A": ["squirrel_legend"]}, food={"A": 20, "B": 0},
                   decks={"A": ["lion"] * 8, "B": ["lion"] * 8})
    rules.apply_action(s, PlaceAction("squirrel_legend", ("cr", "1,2")))
    assert s.food["A"] == 0
    end_turn(s); end_turn(s); end_turn(s)
    assert s.food["A"] == 0
    end_turn(s)                                                 # the second of A's turns
    assert s.food["A"] == 20 * CFG.otk_squirrel_multiplier


def test_covering_the_legendary_squirrel_pauses_its_timer():
    s = make_state(hands={"A": ["squirrel_legend"]}, food={"A": 20, "B": 0},
                   decks={"A": ["lion"] * 8, "B": ["lion"] * 8})
    rules.apply_action(s, PlaceAction("squirrel_legend", ("cr", "1,2")))
    put(s, "1,2", "lion", "B")
    for _ in range(4):
        end_turn(s)
    assert s.food["A"] == 0


def test_iris_becomes_a_copy_of_an_adjacent_animal_but_not_its_roar_and_adds_another_to_your_hand():
    s = make_state(hands={"A": ["chameleon_legend"]})
    por = put(s, "2,2", "porcupine", "B")
    por.strength_counter = 1
    rules.apply_action(s, PlaceAction("chameleon_legend", ("cr", "1,2")))
    choose(s, "2,2")
    me = s.top_unit("1,2")
    base = s.cards["porcupine"].base_strength
    assert me.card_id == "porcupine" and effective_strength(s, me) == base + 1 and "Spikes" in statics.unit_keywords(s, me)
    assert [(u.card_id, u.owner, u.strength_counter) for u in s.hands["A"]] == [("porcupine", "A", 0)]   # a plain card
    s2 = make_state(hands={"A": ["chameleon_legend"]})
    put(s2, "2,2", "squirrel", "A")
    rules.apply_action(s2, PlaceAction("chameleon_legend", ("cr", "1,2")))
    choose(s2, "2,2")
    assert s2.food["A"] == 0                                   # copying the Squirrel doesn't gain its Roar's food...
    rules.apply_action(s2, PlaceAction("squirrel", ("cr", "1,1")))
    assert s2.food["A"] == CFG.squirrel_food                   # ...the copy in hand does, when it is played


def test_a_copy_on_the_board_keeps_the_copied_cards_dawn_and_dusk():
    s = make_state(hands={"A": ["chameleon_legend"]}, decks={"A": ["lion"] * 4, "B": ["lion"] * 4})
    put(s, "2,2", "whale_shark", "A")                          # Dusk: draw a card
    rules.apply_action(s, PlaceAction("chameleon_legend", ("cr", "1,2")))
    choose(s, "2,2")
    hand = len(s.hands["A"])                                   # the Whale Shark Iris added
    end_turn(s)
    assert len(s.hands["A"]) == hand + 2                       # both Whale Sharks draw at Dusk


def test_the_legendary_krill_makes_titans_cost_ten_food_and_one_action():
    whale = PlaceAction("blue_whale", ("cr", "1,1"))
    s = make_state(hands={"A": ["blue_whale"]}, decks={"A": ["lion"] * 4, "B": ["lion"] * 4},
                   food={"A": CFG.krill_legend_food - 1, "B": 0})
    put(s, "1,2", "krill_legend", "A")
    assert whale not in rules.legal_actions(s)                                 # one food short
    s.food["A"] = CFG.krill_legend_food
    rules.apply_action(s, DrawAction())                                       # one action left is enough now
    assert whale in rules.legal_actions(s)
    rules.apply_action(s, whale)
    assert s.top_unit("1,1").card_id == "blue_whale" and s.food["A"] == 0 and s.current == "B"


def test_the_krill_makes_the_next_titan_cost_one_action():
    s = make_state(hands={"A": ["krill", "blue_whale", "blue_whale"]}, decks={"A": ["lion"] * 4, "B": ["lion"] * 4})
    rules.apply_action(s, PlaceAction("krill", ("cr", "1,2")))
    assert PlaceAction("blue_whale", ("cr", "1,1")) in rules.legal_actions(s)      # one action left pays for it
    rules.apply_action(s, PlaceAction("blue_whale", ("cr", "1,1")))
    assert s.top_unit("1,1").card_id == "blue_whale" and s.current == "B"
    end_turn(s)
    rules.apply_action(s, DrawAction())                                            # spent: the next whale costs two again
    assert not any(isinstance(a, PlaceAction) and a.card_id == "blue_whale" for a in rules.legal_actions(s))


def test_iris_copies_an_enemy_timer_for_herself_as_far_along_as_it_is():
    s = make_state(hands={"A": ["chameleon_legend"]}, decks={"A": ["lion"] * 6, "B": ["lion"] * 6})
    sloth = put(s, "2,2", "sloth", "B")
    effects._sloth_place(s, sloth, "2,2")                      # B's Sloth: its food two of B's turns away
    rules.apply_action(s, PlaceAction("chameleon_legend", ("cr", "1,2")))
    choose(s, "2,2")
    for _ in range(4):
        end_turn(s)
    assert s.food["A"] == CFG.sloth_food and s.food["B"] == CFG.sloth_food


def test_iris_copying_a_poisoned_animal_is_poisoned_too():
    s = make_state(hands={"A": ["chameleon_legend"]}, decks={"A": ["lion"] * 4, "B": ["lion"] * 4})
    put(s, "2,2", "lion", "A")
    effects._op_venom(s, {"chooser": "B", "options": ["2,2"], "choice": "2,2"})   # B's Cottonmouth bit it
    rules.apply_action(s, PlaceAction("chameleon_legend", ("cr", "1,2")))
    choose(s, "2,2")
    end_turn(s)
    assert s.top_unit("2,2") is None and s.top_unit("1,2") is None


def test_the_chameleon_becomes_a_copy_of_an_animal_in_your_hand_which_stays_there():
    s = make_state(hands={"A": ["chameleon", "lion", "squirrel"]})
    rules.apply_action(s, PlaceAction("chameleon", ("cr", "1,2")))
    choose(s, hand_inst(s, "A", "lion").iid)
    me = s.top_unit("1,2")
    assert me.card_id == "lion" and effective_strength(s, me) == 7
    assert sorted(hand_ids(s, "A")) == ["lion", "squirrel"] and s.food["A"] == 0


def test_golden_orb_weaver_catches_a_flyer_landing_beside_it():
    s = make_state(current="B", hands={"B": ["pigeon"]})
    put(s, "2,2", "golden_orb_weaver", "A")
    rules.apply_action(s, PlaceAction("pigeon", ("cr", "2,1")))
    assert removed(s, "pigeon")


def test_golden_orb_weaver_catches_a_roamer_placed_or_roaming_beside_it():
    s = make_state(hands={"A": ["wolf"]})
    put(s, "2,2", "golden_orb_weaver", "B")
    rules.apply_action(s, PlaceAction("wolf", ("cr", "1,2")))     # placed beside it
    assert removed(s, "wolf")
    s = make_state()
    put(s, "2,2", "golden_orb_weaver", "B")
    put(s, "1,1", "wolf", "A")
    rules.apply_action(s, RoamAction("1,1", ("cr", "1,2")))       # roams beside it
    assert removed(s, "wolf")


def test_stag_beetle_counts_armor_including_an_armadillos_gift():
    s = make_state(hands={"A": ["stag_beetle"]})
    put(s, "1,1", "armadillo", "A")
    put(s, "2,2", "squirrel", "A")                                     # beside the Beetle's crossroad, not the Armadillo's
    rules.apply_action(s, PlaceAction("stag_beetle", ("cr", "1,2")))   # the Beetle (printed, and the aura) and the Armadillo
    assert s.food["A"] == 2 * CFG.stag_beetle_per_armor


def test_royal_jelly_makes_your_animals_five_wherever_they_are():
    from animal_kingdom.engine.strength import effective_strength
    s = make_state(hands={"A": ["bee_legend_2", "raven", "lion"]}, decks={"A": ["snake_egg", "lion", "raven"], "B": []})
    on_board = put(s, "1,1", "worker_bee", "A")
    enemy = put(s, "4,2", "worker_bee", "B")
    rules.apply_action(s, PlaceAction("bee_legend_2", ("cr", "1,2")))
    five = CFG.jelly_strength
    assert effective_strength(s, s.top_unit("1,2")) == five                     # itself
    assert effective_strength(s, on_board) == five and effective_strength(s, enemy) == 1   # yours on the board, not theirs
    assert {u.card_id: effective_strength(s, u) for u in s.hands["A"]} == {"raven": five, "lion": five}   # a 7 too
    drawn = s.draw("A", 3)
    assert [effective_strength(s, u) for u in drawn] == [five] * 3              # the deck's copies come out at it
    s.decks["A"].append("lion")                                                 # shuffled in later: untouched
    assert effective_strength(s, s.draw("A", 1)[0]) == 7


def test_royal_jelly_sets_five_at_the_roar_and_a_pythons_growth_in_the_deck_stays():
    """Martin's game HFMRHG (2026-10-22): two Pythons drawn after the Roar showed 7 and 5, each set to 5 when drawn, which
    erased the growth it had in the deck. Both are 5 at the Roar, and every removal since grows both."""
    from animal_kingdom.engine.effects import remove_top
    from animal_kingdom.engine.strength import effective_strength
    s = make_state(hands={"A": ["bee_legend_2"]}, decks={"A": ["python", "python"], "B": []})
    rules.apply_action(s, PlaceAction("bee_legend_2", ("cr", "1,2")))
    for cr in ("4,1", "4,3"):
        put(s, cr, "worker_ant", "B"); remove_top(s, cr, by_player="A")
    first = s.draw("A", 1)[0]
    put(s, "4,2", "worker_ant", "B"); remove_top(s, "4,2", by_player="A")
    second = s.draw("A", 1)[0]
    assert effective_strength(s, first) == effective_strength(s, second) == CFG.jelly_strength + 3


def test_the_capybara_is_a_nine_when_the_rest_of_the_starting_deck_is_small():
    from animal_kingdom.engine.strength import effective_strength
    small = make_state(hands={"A": ["capybara"]})
    small.starting_decks = {"A": ("capybara", "capybara", "raven", "snake_egg", "magpie"), "B": ()}
    big = make_state(hands={"A": ["capybara"]})
    big.starting_decks = {"A": ("capybara", "raven", "lynx"), "B": ()}       # the Lynx is a 5
    assert effective_strength(small, small.hands["A"][0]) == 2 + CFG.capybara_bonus == 9
    assert effective_strength(big, big.hands["A"][0]) == 2


def test_the_legendary_honey_badger_has_every_keyword():
    s = make_state()
    hb = put(s, "1,2", "honey_badger_legend", "A")
    assert statics.unit_keywords(s, hb) >= {"Armor", "Stealth", "Poison", "Spikes"}


# ================================================================================== Giants

def test_mocha_removes_the_strongest_adjacent_enemy_at_dusk():
    s = make_state(decks={"A": ["lion"] * 5, "B": ["lion"] * 5})
    put(s, "1,2", "sperm_whale_legend", "A")
    put(s, "1,1", "lion", "B")
    put(s, "2,2", "mouse", "B")
    put(s, "1,3", "rhinoceros_legend", "A")                    # an ally: never removed
    end_turn(s)                                                # A's Dusk
    assert s.top_unit("1,1") is None and s.top_unit("2,2").card_id == "mouse"
    assert s.top_unit("1,3").card_id == "rhinoceros_legend"


def test_dung_beetle_feeds_on_hungry_animals_and_anteater_eats_the_drawn_cards_strength():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,1", "dung_beetle", "A")
    put(s, "1,2", "elephant", "A"); put(s, "1,3", "rhinoceros", "A")
    end_turn(s)
    assert s.food["A"] == 2 * CFG.dung_beetle_per
    s2 = make_state(hands={"A": ["anteater"]}, decks={"A": ["tiger"], "B": []})
    rules.apply_action(s2, PlaceAction("anteater", ("cr", "1,2")))
    assert s2.food["A"] == 7 and hand_ids(s2, "A") == ["tiger"]


def test_whale_shark_draws_a_card_at_the_end_of_your_turn():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,2", "whale_shark", "A")
    end_turn(s)
    assert len(s.hands["A"]) == 1


# ================================================================================ Handlock

def test_silverback_trains_the_whole_hand():
    s = make_state(hands={"A": ["gorilla_legend", "lion"]})
    rules.apply_action(s, PlaceAction("gorilla_legend", ("cr", "1,2")))
    assert hand_inst(s, "A", "lion").strength_counter == CFG.gorilla_legend_grant


def test_the_grizzly_is_an_eight_that_gives_its_opponent_a_card():
    s = make_state(hands={"A": ["grizzly_bear"], "B": []}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    rules.apply_action(s, PlaceAction("grizzly_bear", ("cr", "1,2")))
    assert effective_strength(s, s.top_unit("1,2")) == 8 and hand_ids(s, "B") == ["lion"]


def test_the_legendary_butterfly_moves_one_stage_per_buff():
    s = make_state(hands={"A": ["butterfly_legend", "gorilla_legend", "gorilla_legend"]}, decks={"A": ["lion"] * 9, "B": ["lion"] * 9})
    bf = hand_inst(s, "A", "butterfly_legend")
    rules.apply_action(s, PlaceAction("gorilla_legend", ("cr", "1,1")))
    assert bf.card_id == "butterfly_legend_caterpillar" and placement_strength(s, bf) == CFG.gorilla_legend_grant
    rules.apply_action(s, PlaceAction("gorilla_legend", ("cr", "1,3")))
    assert bf.card_id == "butterfly_legend_chrysalis"         # one buff, one stage
    end_turn(s)                                                 # the opponent's turn passes: A's Dawn
    assert bf.card_id == "butterfly_legend_butterfly"         # Dawn: evolve, in the hand
    rules.apply_action(s, PlaceAction("butterfly_legend_butterfly", ("cr", "1,2")))   # Roar: draw, then all +1
    assert s.board["1,2"][-1].card_id == "butterfly_legend_butterfly"   # the Roar buffs the hand, not itself
    end_turn(s); end_turn(s)
    assert s.board["1,2"][-1].card_id == "butterfly_legend_monarch"     # Dawn: evolve, on the board too


def test_the_legendary_butterfly_evolves_when_it_gains_strength_on_the_board():
    s = make_state()
    put(s, "1,2", "butterfly_legend_caterpillar", "A")
    bf = s.board["1,2"][-1]
    effects._grant(s, [bf.iid], 1)
    effects.resolve(s)
    assert bf.card_id == "butterfly_legend_chrysalis"


def test_the_caterpillar_turns_into_a_butterfly_and_draws_when_trained():
    s = make_state(hands={"A": ["caterpillar", "gorilla_legend"]}, decks={"A": ["lion"], "B": []})
    cat = hand_inst(s, "A", "caterpillar")
    rules.apply_action(s, PlaceAction("gorilla_legend", ("cr", "1,2")))
    assert cat.card_id == "butterfly" and "lion" in hand_ids(s, "A")


def test_the_legendary_eagle_brings_its_mate_and_they_share_every_buff():
    s = make_state(decks={"A": ["eagle_legend"], "B": []})
    effects.draw_cards(s, "A", 1)
    assert sorted(hand_ids(s, "A")) == ["eagle_legend", "eagle_legend_2"]
    s.add_to_hand("A", "baboon")
    eagle, mate = hand_inst(s, "A", "eagle_legend"), hand_inst(s, "A", "eagle_legend_2")
    effects._grant(s, [eagle.iid], 3)
    effects.resolve(s)
    assert eagle.strength_counter == mate.strength_counter == 3


def test_a_buff_to_both_eagles_reaches_each_twice():
    """The legendary Baboon's Dawn on both Eagles: each +1 is shared, so 2 becomes 4, not 3 (Martin, 2026-10-21)."""
    s = make_state(decks={"A": ["eagle_legend"], "B": []})
    effects.draw_cards(s, "A", 1)
    eagle, mate = hand_inst(s, "A", "eagle_legend"), hand_inst(s, "A", "eagle_legend_2")
    effects._grant(s, [eagle.iid, mate.iid], 1)
    effects.resolve(s)
    assert eagle.strength_counter == mate.strength_counter == 2


def test_the_mate_comes_only_when_the_eagle_itself_enters_the_hand():
    s = make_state(decks={"A": ["lion", "lion", "eagle_legend"], "B": []})
    effects.draw_cards(s, "A", 1)
    s.hands["A"].remove(hand_inst(s, "A", "eagle_legend_2"))     # the mate played, the Eagle kept
    effects.draw_cards(s, "A", 2)                                            # other cards arrive: no new mate
    assert sorted(hand_ids(s, "A")) == ["eagle_legend", "lion", "lion"]


def test_orangutan_duplicates_a_primate_and_tarsier_draws_one_and_trains_a_chosen_primate():
    s = make_state(hands={"A": ["orangutan", "gorilla", "lion"]})
    rules.apply_action(s, PlaceAction("orangutan", ("cr", "1,2")))
    assert s.pending["options"] == [hand_inst(s, "A", "gorilla").iid]
    choose(s, hand_inst(s, "A", "gorilla").iid)
    assert hand_ids(s, "A").count("gorilla") == 2
    s2 = make_state(hands={"A": ["tarsier", "chimpanzee", "lion"]}, decks={"A": ["lion", "gorilla", "lion"], "B": []})
    rules.apply_action(s2, PlaceAction("tarsier", ("cr", "1,2")))       # draws the Gorilla, then asks which Primate
    assert sorted(s2.pending["options"]) == sorted([hand_inst(s2, "A", "chimpanzee").iid, hand_inst(s2, "A", "gorilla").iid])
    choose(s2, hand_inst(s2, "A", "chimpanzee").iid)
    assert hand_inst(s2, "A", "chimpanzee").strength_counter == CFG.tarsier_grant
    assert hand_inst(s2, "A", "gorilla").strength_counter == 0


def test_baboon_trains_two_different_cards_and_the_legend_two_random_ones_at_dawn():
    s = make_state(hands={"A": ["baboon", "lion", "tiger", "squirrel"]})
    rules.apply_action(s, PlaceAction("baboon", ("cr", "1,2")))
    choose(s, hand_inst(s, "A", "lion").iid)
    assert hand_inst(s, "A", "lion").iid not in s.pending["options"]
    choose(s, hand_inst(s, "A", "tiger").iid)
    assert [u.strength_counter for u in s.hands["A"]] == [1, 1, 0]
    s2 = make_state(hands={"A": ["lion", "tiger", "squirrel"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s2, "1,2", "baboon_legend", "A")
    end_turn(s2)                                                     # A's Dusk: nothing yet
    assert sum(u.strength_counter for u in s2.hands["A"]) == 0
    end_turn(s2)                                                     # B's turn ends; A's Dawn
    assert sum(u.strength_counter for u in s2.hands["A"]) == CFG.baboon_legend_count


def test_stork_adds_two_different_younglings():
    s = make_state(hands={"A": ["stork"]})
    rules.apply_action(s, PlaceAction("stork", ("cr", "1,2")))
    young = hand_ids(s, "A")
    assert len(young) == 2 and len(set(young)) == 2 and all(c in effects.YOUNGLINGS for c in young)


def test_gorilla_and_macaque_gate_on_their_thresholds():
    s = make_state(hands={"A": ["gorilla"]}, decks={"A": ["lion"], "B": []})
    hand_inst(s, "A", "gorilla").strength_counter = 2
    rules.apply_action(s, PlaceAction("gorilla", ("cr", "1,2")))
    assert hand_ids(s, "A") == ["lion"]
    s2 = make_state(hands={"A": ["macaque"] + ["lion"] * 5})
    put(s2, "2,2", "tiger", "B")
    apply_click(s2, PlaceAction("macaque", ("cr", "1,2")))
    assert s2.top_unit("2,2") is None


# ================================================================================== Hoofed

def test_the_legendary_wildebeest_and_boar_move_region_income():
    s = make_state()
    for cr in ("1,1", "2,1", "2,2"):
        put(s, cr, "squirrel", "A")
    put(s, "1,2", "wildebeest_legend", "A")             # R1 (10)
    assert rules.region_income(s, "A") == 10 + CFG.migration_bonus
    put(s, "4,3", "boar_legend", "B")
    assert rules.region_income(s, "A") == 10 + CFG.migration_bonus - CFG.boar_penalty
    r1 = s.game_map.regions["R1"]
    assert rules.region_yield(s, "A", r1) == 10 + CFG.migration_bonus - CFG.boar_penalty   # what its stone shows
    assert rules.region_yield(s, "B", r1) == 10                 # the Wildebeest is A's, the Boar works on A


def test_the_legendary_giraffe_reveals_the_opponents_hand():
    s = make_state(hands={"B": ["lion"]})
    assert s.view_for("A").opponent_hand is None
    put(s, "1,2", "giraffe_legend", "A")
    assert s.view_for("A").opponent_hand == ("lion",) and s.view_for("B").opponent_hand is None


def test_the_legendary_zebra_draws_per_different_other_hoofed_animal_you_control_anywhere():
    s = make_state(hands={"A": ["zebra_legend"]}, decks={"A": ["lion"] * 5, "B": []})
    put(s, "1,2", "gazelle", "A"); put(s, "4,3", "gazelle", "A")   # two copies count once; far away counts
    put(s, "3,1", "deer", "A")
    put(s, "3,2", "boar", "B")                                  # an enemy's Hoofed animal doesn't count
    put(s, "1,1", "lion", "A")                                  # nor an ally that isn't Hoofed
    rules.apply_action(s, PlaceAction("zebra_legend", ("cr", "2,2")))
    assert len(s.hands["A"]) == 2                               # Gazelle and Deer, not the Zebra itself


def test_grazing_okapi_draws_and_wildebeest_feeds():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,1", "okapi", "A"); put(s, "2,1", "wildebeest", "A"); put(s, "2,2", "squirrel", "A")
    deer = put(s, "1,2", "deer", "A")                           # closes R1: all four graze
    assert statics.grazing(s, deer)
    end_turn(s)
    assert len(s.hands["A"]) == 1 and s.food["A"] == CFG.wildebeest_food + 10   # Wildebeest, then R1's income


def test_giraffe_and_cape_buffalo_are_bigger_on_the_opponents_turn():
    s = make_state()
    g = put(s, "1,2", "giraffe", "A"); put(s, "1,1", "cape_buffalo", "A")
    assert effective_strength(s, g) == 6
    s.current = "B"
    assert effective_strength(s, g) == 6 + CFG.giraffe_bonus + CFG.buffalo_anthem


def test_the_crocodile_covers_a_lion_on_its_turn_and_is_a_five_on_the_opponents():
    s = make_state(hands={"A": ["crocodile"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,1", "caracal", "A"); put(s, "1,2", "lion", "B")
    rules.apply_action(s, PlaceAction("crocodile", ("cr", "1,2")))
    croc = s.top_unit("1,2")
    assert croc.card_id == "crocodile" and effective_strength(s, croc) == 8
    s.current = "B"
    assert effective_strength(s, croc) == 8 - CFG.crocodile_penalty


def test_the_moose_is_a_hungry_eight_that_does_not_roam():
    card = load_cards()["moose"]
    assert (card.base_strength, card.hungry, card.rarity) == (8, 3, "common") and "Roam" not in card.keywords


def test_the_moose_does_not_eat_while_it_is_grazing():
    def food_after_one_round(moose_at):
        s = make_state(food={"A": 0, "B": 0}, decks={"A": ["lion"] * 4, "B": ["lion"] * 4})
        for cr in ("1,1", "2,1", "2,2"):
            put(s, cr, "lion", "A")                            # with a Moose on 1,2, all four corners of R1 are A's
        if moose_at != "1,2":
            put(s, "1,2", "lion", "A")
        moose = put(s, moose_at, "moose", "A")
        end_turn(s); end_turn(s)                               # A's turn ends (R1 pays), then A's next turn starts
        return s.food["A"], effective_strength(s, moose)
    grazing, fed = food_after_one_round("1,2"), food_after_one_round("3,2")
    assert grazing[1] == fed[1] == 8                           # fed: enough food, so no strength lost either way
    assert fed[0] == grazing[0] - 3                            # only the one off the corner ate Hungry 3


def test_the_albatross_sweeps_the_small_enemies_where_it_lands():
    s = make_state(hands={"A": ["albatross"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    for cr, cid in (("2,1", "sardine"), ("3,2", "mackerel"), ("2,3", "mouse")):
        put(s, cr, cid, "B")
    rules.apply_action(s, PlaceAction("albatross", ("cr", "2,2")))   # Flight: no connection needed
    assert s.top_unit("2,1") is None and s.top_unit("3,2") is None and s.top_unit("2,3").card_id == "mouse"


def test_the_dolphin_is_a_five_that_draws_a_card():
    s = make_state(hands={"A": ["dolphin"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    rules.apply_action(s, PlaceAction("dolphin", ("cr", "1,2")))
    assert effective_strength(s, s.top_unit("1,2")) == 5 and hand_ids(s, "A") == ["lion"]


def test_the_tortoise_is_a_common_with_armor_and_nothing_else():
    card = load_cards()["tortoise"]
    assert card.rarity == "common" and card.text == "Armor." and "Armor" in card.keywords


def test_the_peacock_counts_every_card_in_your_hand_itself_included_until_it_lands():
    """It covers with the number it shows, then has one less (Martin, 2026-10-21: the text taken literally)."""
    s = make_state(hands={"A": ["peacock", "lion", "lion", "lion"]})
    assert placement_strength(s, hand_inst(s, "A", "peacock")) == 1 + 4 * CFG.hand_per_card
    peacock = hand_inst(s, "A", "peacock")
    s.hands["A"].remove(peacock); s.board["2,1"] = [peacock]
    assert effective_strength(s, peacock) == 1 + 3 * CFG.hand_per_card


def test_warthog_removes_the_enemy_covering_an_allied_hoofed():
    s = make_state(hands={"A": ["warthog"]})
    put(s, "2,2", "gazelle", "A"); put(s, "2,2", "lion", "B")
    put(s, "1,1", "lion", "B")                                  # covering nothing of A's
    apply_click(s, PlaceAction("warthog", ("cr", "1,2")))
    assert [u.card_id for u in s.board["2,2"]] == ["gazelle"] and s.top_unit("1,1").owner == "B"


def test_boar_removes_an_adjacent_enemy_covering_nothing():
    s = make_state(hands={"A": ["boar"]})
    put(s, "1,1", "lion", "B")                                  # alone on its crossroad: the target
    put(s, "2,2", "squirrel", "B"); put(s, "2,2", "lion", "B")  # on top of its own animal: safe
    apply_click(s, PlaceAction("boar", ("cr", "1,2")))
    assert "1,1" not in s.board and [u.card_id for u in s.board["2,2"]] == ["squirrel", "lion"]


def test_related_cards_are_real_cards_and_follow_the_engine():
    cards = load_cards()
    assert list(cards["butterfly_legend"].related) == effects.BUTTERFLY_STAGES[1:]
    assert list(cards["stork"].related) == effects.YOUNGLINGS
    assert cards["eagle_legend"].mate == cards["eagle_legend"].related[0]
    for c in cards.values():
        assert all(r in cards for r in c.related), c.id


# ==================================================================================== Pool

def test_great_white_shark_has_reach_after_a_removal():
    s = make_state(hands={"A": ["great_white_shark"]}, decks={"A": ["lion"] * 3, "B": []})
    put(s, "2,2", "lion", "B").strength_counter = -1           # a 6, two crossroads out: the shark (7) eats it
    assert PlaceAction("great_white_shark", ("cr", "2,2")) not in rules.legal_actions(s)
    put(s, "4,3", "squirrel", "B")
    effects.remove_top(s, "4,3", by_player="A")
    assert PlaceAction("great_white_shark", ("cr", "2,2")) in rules.legal_actions(s)


def test_cuckoo_eggs_clog_the_opponents_deck_and_feed_you():
    s = make_state(hands={"A": ["cuckoo"]}, decks={"A": ["lion"] * 3, "B": []})
    rules.apply_action(s, PlaceAction("cuckoo", ("cr", "1,2")))
    assert s.decks["B"] == ["cuckoo_egg"] * CFG.cuckoo_eggs
    effects.draw_cards(s, "B", 1)
    assert hand_ids(s, "B") == ["cuckoo_egg"] and hand_ids(s, "A") == ["lion"]


def test_aurum_lays_two_golden_eggs_that_each_pay_two_cards_when_drawn():
    s = make_state(current="A", decks={"A": ["lion"] * 8, "B": ["lynx"] * 8})
    put(s, "1,2", "goose_legend", "A")
    while s.current == "A":
        rules.apply_action(s, DrawAction())              # A's turn
    while s.current == "B":
        rules.apply_action(s, DrawAction())              # B's turn, then A's Dawn: an egg into A's deck
    assert s.decks["A"].count("golden_egg") == CFG.aurum_eggs == 2
    s.decks["A"] = ["tiger", "lion", "fox", "golden_egg"]   # the egg on top
    hand = len(s.hands["A"])
    effects.draw_cards(s, "A", 1)                        # draws the egg: it goes, two cards come
    assert len(s.hands["A"]) == hand + 2 and "golden_egg" not in hand_ids(s, "A")
    assert "golden_egg" in s.remove_pile                 # a removed Egg, for the Egg Eater


def test_opossum_returns_an_adjacent_ally_to_hand():
    s = make_state(hands={"A": ["opossum"]})
    put(s, "1,1", "squirrel", "A")
    apply_click(s, PlaceAction("opossum", ("cr", "1,2")))
    assert "squirrel" in hand_ids(s, "A") and not removed(s, "squirrel")


def test_every_launch_card_can_be_played_by_the_bots_without_crashing():
    """A smoke: a few random games over every pairing of the twelve decks (the full fuzz runs in the slow tier)."""
    import random
    from animal_kingdom.decks import load_premade_deck
    from animal_kingdom.engine.cards import DECK_SLUGS
    from animal_kingdom.engine.state import new_game
    decks = sorted(DECK_SLUGS)
    for i, a in enumerate(decks):
        b = decks[(i + 5) % len(decks)]
        s, rng = new_game(load_premade_deck(a), load_premade_deck(b), 77 + i), random.Random(i)
        for _ in range(600):
            if rules.is_terminal(s) is not None:
                break
            rules.apply_action(s, rng.choice(rules.legal_actions(s)))


def test_the_woodpecker_makes_the_next_roar_this_turn_happen_twice():
    s = make_state(hands={"A": ["woodpecker", "squirrel", "squirrel"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    rules.apply_action(s, PlaceAction("woodpecker", ("cr", "1,2")))
    rules.apply_action(s, PlaceAction("squirrel", ("cr", "1,1")))
    assert s.food["A"] == 2 * s.config.squirrel_food
    assert "A" not in s.roar_twice                              # spent by that Roar


def test_a_played_roar_is_remembered_for_the_macaw():
    s = make_state(hands={"A": ["squirrel"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    rules.apply_action(s, PlaceAction("squirrel", ("cr", "1,2")))
    assert s.last_roar == {"A": "squirrel"}


def test_the_macaw_repeats_the_last_roar_its_opponent_played():
    s = make_state(hands={"A": ["macaw"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    s.last_roar["B"] = "squirrel"
    rules.apply_action(s, PlaceAction("macaw", ("cr", "1,2")))
    assert s.food["A"] == s.config.squirrel_food
    assert s.last_roar["A"] == "squirrel"                       # a Macaw repeating this Macaw repeats the Squirrel


def test_the_macaw_repeats_a_removal_next_to_itself():
    s = make_state(hands={"A": ["macaw"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,2", "caracal", "A")
    put(s, "3,2", "mouse", "B")                                 # 4, next to where the Macaw lands
    s.last_roar["B"] = "jaguar"                                # remove an adjacent enemy of strength 4 or less
    rules.apply_action(s, PlaceAction("macaw", ("cr", "2,2")))
    if s.pending:
        choose(s, "3,2")
    assert s.top_unit("3,2") is None


def test_the_macaw_does_nothing_before_its_opponent_roars():
    s = make_state(hands={"A": ["macaw"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    rules.apply_action(s, PlaceAction("macaw", ("cr", "1,2")))
    assert s.food["A"] == 0 and "A" not in s.last_roar


# ================================================================================ 2026-10-09: the fit and rarity passes

def test_the_fox_and_the_african_wild_dog_ids_follow_their_animals():
    cards = load_cards()
    fox, dog = cards["fox"], cards["african_wild_dog"]
    assert (fox.name, fox.rarity, "Roam" in fox.keywords) == ("Fox", "common", False)
    assert (dog.name, dog.rarity, "Roam" in dog.keywords) == ("African Wild Dog", "rare", True)


def test_the_african_wild_dog_has_no_dusk_effect_any_more():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "2,2", "african_wild_dog", "A")
    ally = put(s, "1,2", "lion", "A")
    end_turn(s)
    assert ally.strength_counter == 0


def test_the_legendary_elephant_sweeps_small_enemies_where_it_is_placed_and_where_it_roams():
    s = make_state(hands={"A": ["elephant_legend"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,1", "squirrel", "B"); put(s, "1,3", "mackerel", "B")
    big = put(s, "2,2", "lion", "B")
    rules.apply_action(s, PlaceAction("elephant_legend", ("cr", "1,2")))
    assert s.top_unit("1,1") is None and s.top_unit("1,3") is None and s.top_unit("2,2") is big
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,2", "elephant_legend", "A")
    put(s, "2,1", "squirrel", "B"); put(s, "3,2", "lion", "B"); put(s, "2,3", "mackerel", "B")
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))    # arriving by a roam is landing too
    assert s.top_unit("2,1") is None and s.top_unit("2,3") is None and s.top_unit("3,2").card_id == "lion"
    assert CFG.elephant_legend_max == 3


def test_the_legendary_elephant_leaves_armor_standing():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,2", "elephant_legend", "A")
    shell = put(s, "2,1", "stag_beetle", "B")                  # Armor
    shell.strength_counter = -2                                # a 2: small enough to be swept, were it not armored
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert s.top_unit("2,1") is shell


def test_the_eagle_is_a_flying_apex_predator_and_the_pigeon_a_flier():
    cards = load_cards()
    assert cards["eagle"].keywords == {"Flight", "Apex Predator"} and cards["eagle"].base_strength == 6
    assert cards["pigeon"].keywords == {"Flight"} and cards["pigeon"].base_strength == 5
    s = make_state(hands={"A": ["eagle", "pigeon"]})
    put(s, "4,3", "squirrel", "B")
    targets = {a.target[1] for a in rules.legal_actions(s) if isinstance(a, PlaceAction) and a.card_id == "eagle"}
    assert targets == {"4,3"}                                  # Flight skips the connection; an Apex lands on an animal only
    assert "1,1" in {a.target[1] for a in rules.legal_actions(s) if isinstance(a, PlaceAction) and a.card_id == "pigeon"}
    assert "4,1" in {a.target[1] for a in rules.legal_actions(s) if isinstance(a, PlaceAction) and a.card_id == "pigeon"}
    rules.apply_action(s, PlaceAction("eagle", ("cr", "4,3")))
    assert [u.card_id for u in s.board["4,3"]] == ["eagle"]    # it ate the Squirrel


def test_the_termite_king_draws_a_card_for_each_colony_queen():
    s = make_state(hands={"A": ["termite_king"]}, decks={"A": ["lion"] * 3, "B": []})
    put(s, "1,1", "termite_queen", "A")
    put(s, "1,3", "queen_bee", "A")
    rules.apply_action(s, PlaceAction("termite_king", ("cr", "1,2")))
    assert len(s.hands["A"]) == 2


def test_the_legendary_leopard_is_five_and_grows():
    # 8 until 2026-10-20; then 6 with "gain 1 strength" on every kill (Martin: a leopard is no lion, and the Lion is the vanilla 7);
    # 5 from 2026-10-21, so he lands within the Black Mamba's reach and the opponent has a window before he grows.
    assert load_cards()["leopard_legend"].base_strength == 5


def test_the_lemming_is_a_plain_one_now():
    s = make_state(hands={"A": ["lemming", "lemming"]}, decks={"A": ["lemming"], "B": []})
    rules.apply_action(s, PlaceAction("lemming", ("cr", "1,2")))
    assert sum(len(st) for st in s.board.values()) == 1 and hand_ids(s, "A") == ["lemming"]


def test_the_legendary_cuckoo_is_a_bird():
    assert "Bird" in load_cards()["cuckoo_legend"].tags


# --- Vesper: "Flight. When an enemy covers an allied Queen, place Vesper on it from your hand or deck." -------------

def _queen_covered_by(coverer, *, b_hand=(), b_deck=(), extra=None):
    """A's `coverer` covers B's Nurse Bumblebee on 2,2 (A holds 1,2, so 2,2 is in reach)."""
    s = make_state(hands={"A": [coverer], "B": list(b_hand)}, decks={"A": ["lion"] * 3, "B": list(b_deck)})
    put(s, "1,2", "lion", "A")
    put(s, "2,2", "nurse_bumblebee", "B")
    if extra:
        extra(s)
    rules.apply_action(s, PlaceAction(coverer, ("cr", "2,2")))
    return s


def test_vesper_is_placed_from_hand_on_the_enemy_that_covers_an_allied_colony_animal():
    s = _queen_covered_by("lion", b_hand=["hornet_legend", "lion"])
    assert [u.card_id for u in s.board["2,2"]] == ["nurse_bumblebee", "lion", "hornet_legend"]
    assert hand_ids(s, "B") == ["lion"] and s.board["2,2"][-1].owner == "B"
    place = next(e for e in s.events if e["e"] == "place" and e["card"] == "hornet_legend")
    assert place["from_hand"] and place["reveal"] and place["cause"] == "hornet_legend"
    assert s.current == "A" and s.actions_taken_this_turn == 1   # B spent nothing; A's turn goes on


def test_vesper_is_placed_from_the_deck_too():
    s = _queen_covered_by("lion", b_deck=["lion", "hornet_legend", "lion"])
    assert s.board["2,2"][-1].card_id == "hornet_legend" and s.decks["B"] == ["lion", "lion"]
    place = next(e for e in s.events if e["e"] == "place" and e["card"] == "hornet_legend")
    assert not place["from_hand"]


def test_vesper_lands_on_any_strength_and_skips_connection():
    s = _queen_covered_by("blue_whale", b_hand=["hornet_legend"])   # a 3 on a 12, far from B's den
    assert [u.card_id for u in s.board["2,2"]] == ["nurse_bumblebee", "blue_whale", "hornet_legend"]


def test_vesper_on_the_board_or_in_the_remove_pile_does_nothing():
    s = _queen_covered_by("lion", extra=lambda s: put(s, "4,1", "hornet_legend", "B"))
    assert [u.card_id for u in s.board["2,2"]] == ["nurse_bumblebee", "lion"]
    s = _queen_covered_by("lion", extra=lambda s: s.pile_add("hornet_legend", "B"))
    assert [u.card_id for u in s.board["2,2"]] == ["nurse_bumblebee", "lion"]


def test_vesper_answers_any_colony_ally_but_not_another_animal_or_a_friendly_cover():
    """Any Colony animal, not only a Queen (Martin, 2026-10-24: Queens only was incredibly useless)."""
    s = make_state(hands={"A": ["lion"], "B": ["hornet_legend"]}, decks={"A": [], "B": []})
    put(s, "1,2", "lion", "A")
    put(s, "2,2", "worker_bee", "B")                            # Colony, no Queen
    rules.apply_action(s, PlaceAction("lion", ("cr", "2,2")))
    assert s.board["2,2"][-1].card_id == "hornet_legend"
    s = make_state(hands={"A": ["lion"], "B": ["hornet_legend"]}, decks={"A": [], "B": []})
    put(s, "1,2", "lion", "A")
    put(s, "2,2", "squirrel", "B")                              # not Colony
    rules.apply_action(s, PlaceAction("lion", ("cr", "2,2")))
    assert s.board["2,2"][-1].card_id == "lion" and hand_ids(s, "B") == ["hornet_legend"]
    s = make_state(current="B", hands={"B": ["lion", "hornet_legend"]}, decks={"A": [], "B": []})
    put(s, "4,2", "lion", "B"); put(s, "3,2", "nurse_bumblebee", "B")
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))      # B covers its own Nurse Bumblebee
    assert s.board["3,2"][-1].card_id == "lion" and hand_ids(s, "B") == ["hornet_legend"]


def test_vesper_answers_a_roaming_cover_too():
    s = make_state(decks={"A": [], "B": []}, hands={"B": ["hornet_legend"]})
    put(s, "1,2", "wolf", "A"); put(s, "1,3", "nurse_bumblebee", "B")
    rules.apply_action(s, RoamAction("1,2", ("cr", "1,3")))
    assert [u.card_id for u in s.board["1,3"]] == ["nurse_bumblebee", "wolf", "hornet_legend"]


def test_vesper_resolves_after_the_coverers_roar():
    """The Dolphin's Roar draws first; Vesper comes after it, without an action."""
    s = _queen_covered_by("dolphin", b_hand=["hornet_legend"])
    order = [e["e"] for e in s.events if e["e"] in ("draw", "place")]
    assert order == ["place", "draw", "place"] and s.board["2,2"][-1].card_id == "hornet_legend"


def test_vesper_fires_identically_from_any_determinized_world():
    """Honesty: the bots' sampled worlds re-deal B's hand and deck, but Vesper is in one or the other in every world,
    so a search that covers B's Nurse Bumblebee sees the same answer whatever it may not know."""
    import random
    from animal_kingdom.bots.determinize import determinize
    s = make_state(hands={"A": ["lion"], "B": ["lion", "lion"]}, decks={"A": [], "B": ["hornet_legend", "lion", "lion"]})
    put(s, "1,2", "lion", "A"); put(s, "2,2", "nurse_bumblebee", "B")
    for seed in range(6):
        w = determinize(s, "A", random.Random(seed))
        rules.apply_action(w, PlaceAction("lion", ("cr", "2,2")), validate=False)
        assert w.board["2,2"][-1].card_id == "hornet_legend"


# --- Methuselah: "Armor. Each player gains at most 20 food per turn. Dusk: gain 5 food." --------------------------

def test_methuselah_caps_each_players_food_per_turn_from_any_source():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "4,3", "tortoise_legend", "B")
    effects.gain_food(s, "A", 15); effects.gain_food(s, "A", 15)
    effects.gain_food(s, "B", 30)                               # the opponent's gains this turn are capped too
    assert (s.food["A"], s.food["B"]) == (CFG.tortoise_legend_food_cap, CFG.tortoise_legend_food_cap) == (20, 20)
    end_turn(s)                                                  # a new turn: a fresh 20
    effects.gain_food(s, "A", 30)
    assert s.food["A"] == 40


def test_methuselahs_own_dusk_counts_toward_the_cap_before_region_income():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    for cr in ("1,1", "2,1", "2,2", "1,3", "2,3"):
        put(s, cr, "lion", "A")
    put(s, "1,2", "tortoise_legend", "A")                            # R1 and R4: 20 food of income
    assert rules.region_income(s, "A") == 20
    end_turn(s)
    assert s.food["A"] == 20                                    # Dusk's 5, then 15 of the 20


def test_a_buried_methuselah_caps_nothing():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "2,2", "tortoise_legend", "A"); put(s, "2,2", "lion", "B")
    effects.gain_food(s, "A", 30)
    assert s.food["A"] == 30


def test_vesper_landing_is_a_cover_spikes_remove_it_and_an_apex_still_eats_the_nurse():
    s = _queen_covered_by("hedgehog", b_hand=["hornet_legend"])           # Spikes: the first enemy to cover it is removed
    assert [u.card_id for u in s.board["2,2"]] == ["nurse_bumblebee", "hedgehog"] and removed(s, "hornet_legend")
    s = _queen_covered_by("polar_bear", b_hand=["hornet_legend"])
    assert [u.card_id for u in s.board["2,2"]] == ["polar_bear", "hornet_legend"] and removed(s, "nurse_bumblebee")


def test_a_weaker_copy_in_hand_can_be_played_by_naming_it():
    s = make_state(hands={"A": ["lion", "lion", "lion"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    strong, weak, weak2 = s.hands["A"]
    strong.strength_counter = 1
    copies = {a.iid for a in rules.legal_actions(s) if isinstance(a, PlaceAction)}
    assert copies == {strong.iid, weak.iid}                     # one choice per strength, named by its first copy
    target = next(a.target for a in rules.legal_actions(s) if isinstance(a, PlaceAction))
    rules.apply_action(s, PlaceAction("lion", target, weak2.iid))   # any copy of that strength will do
    assert [u.strength_counter for u in s.hands["A"]] == [1, 0]     # the buffed one stays in hand
    assert s.board[target[1]][-1].strength_counter == 0


def test_alike_copies_need_no_naming():
    s = make_state(hands={"A": ["lion", "lion"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    acts = [a for a in rules.legal_actions(s) if isinstance(a, PlaceAction)]
    assert acts and all(a.iid is None for a in acts)
    rules.apply_action(s, PlaceAction("lion", acts[0].target, s.hands["A"][1].iid))   # a client naming one is fine
    assert len(s.hands["A"]) == 1


def test_the_anaconda_swallows_what_it_eats_and_grows_by_its_strength():
    s = make_state(hands={"A": ["anaconda"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,2", "lion", "A")
    put(s, "2,2", "squirrel", "B")                             # 3: an Anaconda (5) can land on it
    rules.apply_action(s, PlaceAction("anaconda", ("cr", "2,2")))
    a = s.top_unit("2,2")
    assert a.card_id == "anaconda" and [u.card_id for u in s.board["2,2"]] == ["anaconda"]
    assert effective_strength(s, a) == 5 + 3


def test_the_legendary_leopard_grows_with_every_kill():
    # "Whenever this removes an animal, gain 1 strength": each prey it eats, placed or roamed onto, adds one.
    s = make_state(hands={"A": ["leopard_legend"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,2", "lion", "A")
    put(s, "2,2", "squirrel", "B")
    put(s, "3,2", "squirrel", "B")
    base = s.cards["leopard_legend"].base_strength
    rules.apply_action(s, PlaceAction("leopard_legend", ("cr", "2,2")))
    leo = s.top_unit("2,2")
    assert leo.card_id == "leopard_legend" and [u.card_id for u in s.board["2,2"]] == ["leopard_legend"]
    assert effective_strength(s, leo) == base + CFG.leopard_legend_growth
    rules.apply_action(s, RoamAction("2,2", ("cr", "3,2")))   # it roams onto the next prey and eats that too
    leo = s.top_unit("3,2")
    assert leo.card_id == "leopard_legend" and effective_strength(s, leo) == base + 2 * CFG.leopard_legend_growth



def test_the_legendary_leopard_still_eats_and_grows_under_king_theron():
    # King Theron removes what a Cat covers only after the Cat has acted: the Leopard eats first and grows (Martin,
    # 2026-10-24: under Theron it didn't grow, Theron's removal took the prey first).
    s = make_state(hands={"A": ["leopard_legend"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,1", "lion_legend_3", "A")
    put(s, "1,2", "lion", "A")
    put(s, "2,2", "squirrel", "B")
    put(s, "3,2", "squirrel", "B")
    base = s.cards["leopard_legend"].base_strength
    rules.apply_action(s, PlaceAction("leopard_legend", ("cr", "2,2")))
    leo = s.top_unit("2,2")
    assert [u.card_id for u in s.board["2,2"]] == ["leopard_legend"] and effective_strength(s, leo) == base + CFG.leopard_legend_growth
    rules.apply_action(s, RoamAction("2,2", ("cr", "3,2")))
    leo = s.top_unit("3,2")
    assert [u.card_id for u in s.board["3,2"]] == ["leopard_legend"] and effective_strength(s, leo) == base + 2 * CFG.leopard_legend_growth


# ==================================================================================== the hand limit

def test_cards_made_past_the_hand_limit_burn():
    # Nine cards left in hand after the Stork: the first youngling fills it to ten, the second burns.
    s = make_state(hands={"A": ["stork"] + ["lion"] * 9}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    apply_click(s, PlaceAction("stork", ("cr", "1,2")))
    assert len(s.hands["A"]) == CFG.hand_limit
    assert sum(1 for c in s.remove_pile if c not in ("lion", "stork")) == 1


def test_an_animal_returned_to_a_full_hand_burns():
    s = make_state(hands={"A": ["skunk"], "B": ["lion"] * 10}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "2,2", "elephant", "B")
    apply_click(s, PlaceAction("skunk", ("cr", "1,2")))
    assert len(s.hands["B"]) == CFG.hand_limit and "elephant" in s.remove_pile


def test_a_mate_brought_into_a_full_hand_burns():
    s = make_state(hands={"A": ["lion"] * 9}, decks={"A": ["eagle_legend"], "B": ["lion"] * 3})
    rules.apply_action(s, DrawAction())
    assert len(s.hands["A"]) == CFG.hand_limit and "eagle_legend_2" in s.remove_pile


def test_an_aura_reaches_the_top_animal_not_one_buried():
    s = make_state(current="B", hands={"B": ["rat_legend_2"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,2", "capybara", "A"); put(s, "2,2", "lynx", "A"); put(s, "2,2", "lion", "B")
    for c in ("4,2", "3,2", "3,1", "3,3"):
        put(s, c, "lion", "B")
    assert "Armor" not in statics.unit_keywords(s, s.board["2,2"][0])   # buried under the enemy Lion: out of reach
    rules.apply_action(s, PlaceAction("rat_legend_2", ("cr", "2,1")))
    choose(s, "2,2")
    assert s.board.get("2,2", []) == []                                 # Pestis wipes the whole stack, the Lynx too
