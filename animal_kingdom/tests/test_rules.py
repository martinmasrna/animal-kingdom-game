"""The rules: mana, the board and its bases, covering, the den raid, food, the keywords, the cards' effects, the leaders."""

import random
from itertools import combinations

from animal_kingdom.decks import deck_problems
from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import SKIP, ChoiceAction, LeaderAction, PassAction, PlaceAction
from dataclasses import replace

from animal_kingdom.engine.cards import load_cards
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.effects import WEAKENS, _adjacent_enemy_targets, mana_cost
from animal_kingdom.engine.leaders import ASSASSIN, ELF, LEADERS, RAIDER, SAGE, WARLORD
from animal_kingdom.engine.maps import load_map
from animal_kingdom.engine.state import MAP_ID, GameState, UnitInstance, new_game
from animal_kingdom.engine.strength import effective_strength

CARDS = load_cards()
# Poison, Armor and Stealth are on no card right now (Martin, 2026-11-21, his paper cards); the rules keep them, tested on
# stand-ins.
for _kw in ("Poison", "Armor", "Stealth"):
    CARDS[f"test_{_kw.lower()}"] = replace(CARDS["wisp_1"], id=f"test_{_kw.lower()}", keywords=frozenset({_kw}))
CARDS["test_reserve"] = replace(CARDS["wisp_1"], id="test_reserve", status="reserve")
CARDS["test_one"] = replace(CARDS["wisp_1"], id="test_one", base_strength=1)   # a plain 1, for a board that needs one
CFG = Config()
BOARD = load_map(MAP_ID)
BASE = {"A": {"1,1", "1,2", "1,3"}, "B": {"5,1", "5,2", "5,3"}}
DECK = ([f"wisp_{n}" for n in range(1, 7) for _ in range(2)] + [f"flight_{n}" for n in (1, 2, 3, 5) for _ in range(2)]
        + ["cantrip_2", "cantrip_2", "spikes_3", "spikes_3", "warlord_legend"])


def state(*, turn=0, current="A", hands=None, decks=None, food=None, leaders=None) -> GameState:
    """A bare position: turn_counter `turn` (A's Nth own turn is turn 2N-2), nothing pending."""
    s = GameState(BOARD, CARDS, CFG, board={}, hands={"A": [], "B": []},
                  decks={p: list((decks or {}).get(p, ["wisp_1"] * 5)) for p in "AB"},
                  remove_pile=[], food=food or {"A": 0, "B": 0}, current=current, first_player="A", turn_counter=turn,
                  leaders={p: {"id": lid} for p, lid in (leaders or {}).items()})
    for p, ids in (hands or {}).items():
        for cid in ids:
            s.hands[p].append(UnitInstance(cid, p, s.new_iid()))
    return s


def put(s, cr, cid, owner):
    u = UnitInstance(cid, owner, s.new_iid())
    s.board.setdefault(cr, []).append(u)
    return u


def places(s, cid=None):
    return {a.target[1] for a in rules.legal_actions(s)
            if isinstance(a, PlaceAction) and (cid is None or a.card_id == cid) and a.target[0] == "cr"}


def raids(s):
    return [a for a in rules.legal_actions(s) if isinstance(a, PlaceAction) and a.target[0] == "hq"]


def resolve_choices(s):
    while s.pending is not None and s.result is None:
        rules.apply_action(s, rules.legal_actions(s)[0])


def random_game(seed):
    rng = random.Random(seed)
    s = new_game(DECK, DECK, seed, leaders={"A": "warlord_legend", "B": "warlord_legend"})
    for _ in range(3000):
        if rules.is_terminal(s):
            break
        rules.apply_action(s, rng.choice(rules.legal_actions(s)))
    return s


# ------------------------------------------------------------------ mana

def test_mana_grows_one_a_turn_to_ten():
    for n in range(1, 13):
        s = state(turn=2 * (n - 1))
        assert rules.mana_left(s, "A") == min(n, 10)
        assert rules.mana_left(s, "B") == min(n, 10)         # B's next turn is their Nth


def test_a_card_costs_its_mana_and_what_the_mana_cannot_pay_is_refused():
    s = state(turn=4, hands={"A": ["wisp_3", "wisp_2"]})      # A's third turn: 3 mana
    assert places(s, "wisp_3") and places(s, "wisp_2")
    rules.apply_action(s, PlaceAction("wisp_2", ("cr", "1,1")))
    assert rules.mana_left(s, "A") == 1 and not places(s, "wisp_3")
    assert rules.legal_actions(s) == [PassAction()]          # nothing payable: ending the turn is the move, never automatic
    assert s.current == "A"


def test_opening_hands_are_three_and_four_and_the_turn_card_comes():
    s = new_game(DECK, DECK, 1, first_player="A", leaders={"A": "warlord_legend", "B": "warlord_legend"})
    assert len(s.hands["A"]) == 3 and len(s.hands["B"]) == 4
    while s.pending is not None:
        rules.apply_action(s, ChoiceAction(SKIP))
    rules.apply_action(s, PassAction())
    assert len(s.hands["B"]) == 5


def test_ending_turns_unplayed_never_ends_the_game():
    s = state(turn=11, hands={"A": ["wisp_1"], "B": ["wisp_1"]})
    for _ in range(4):
        rules.apply_action(s, PassAction())
    assert s.result is None


# ------------------------------------------------------------------ the board

def test_the_board_is_nineteen_tiles_in_rows_of_three_four_five_four_three():
    rows = {}
    for cr in BOARD.crossroads:
        rows.setdefault(int(cr.split(",")[0]), []).append(cr)
    assert [len(rows[r]) for r in sorted(rows)] == [3, 4, 5, 4, 3]
    assert {p: set(t) for p, t in BOARD.hq_connects.items()} == BASE


def test_twenty_four_regions_of_three_mutually_adjacent_tiles():
    triangles = {frozenset(t) for t in combinations(sorted(BOARD.crossroads), 3)
                 if all(BOARD.adjacent(a, b) for a, b in combinations(t, 2))}
    assert {frozenset(r.corners) for r in BOARD.regions.values()} == triangles and len(triangles) == 24
    assert all(r.food == 1 for r in BOARD.regions.values())


def test_connection_starts_from_the_base_and_either_base_is_open():
    s = state(turn=4, hands={"A": ["wisp_1"]})
    assert places(s, "wisp_1") == BASE["A"]
    put(s, "1,1", "wisp_1", "A")
    assert places(s, "wisp_1") == BASE["A"] | {"2,1", "2,2"}
    for cr in ("2,1", "3,1", "4,1"):
        put(s, cr, "wisp_1", "A")
    assert "5,1" in places(s, "wisp_1")                        # the opponent's base, reached along the chain


def test_region_income_is_paid_at_the_end_of_the_turn():
    s = state(turn=4, food={"A": 15, "B": 15})
    for cr in ("1,1", "1,2", "2,2"):
        put(s, cr, "wisp_1", "A")
    assert rules.region_income(s, "A") == 1
    rules.apply_action(s, PassAction())
    assert s.food["A"] == 16


def test_reaching_thirty_food_wins():
    assert BOARD.win_food == 30 and CFG.start_food == 15        # Martin, 2026-11-20
    s = state(turn=4, food={"A": 29, "B": 15})
    for cr in ("1,1", "1,2", "2,2"):
        put(s, cr, "wisp_1", "A")
    rules.apply_action(s, PassAction())
    assert s.result is not None and s.result.winner == "A" and s.result.reason == "food"


# ------------------------------------------------------------------ covering and the raid

def test_a_cover_needs_more_strength_and_removes_what_it_covered():
    s = state(turn=11, hands={"A": ["wisp_3", "wisp_2"]})
    put(s, "1,1", "wisp_1", "A")
    put(s, "2,1", "wisp_3", "B")
    assert "2,1" not in places(s, "wisp_2") and "2,1" not in places(s, "wisp_3")
    s.hands["A"].append(UnitInstance("wisp_4", "A", s.new_iid()))
    rules.apply_action(s, PlaceAction("wisp_4", ("cr", "2,1")))
    assert [u.card_id for u in s.board["2,1"]] == ["wisp_4"] and "wisp_3" in s.remove_pile


def test_covering_your_own_animal_removes_it_too():
    s = state(turn=11, hands={"A": ["wisp_1"]})
    put(s, "1,1", "wisp_5", "A")
    rules.apply_action(s, PlaceAction("wisp_1", ("cr", "1,1")))
    assert [u.card_id for u in s.board["1,1"]] == ["wisp_1"] and "wisp_5" in s.remove_pile


def test_random_games_keep_one_animal_a_tile_and_end():
    for seed in range(20):
        s = random_game(seed)
        assert s.result is not None and s.result.reason in ("food", "starved"), seed
        if not s.effect_stack:
            assert all(len(st) == 1 for st in s.board.values()), seed


def _a_chain_to_b_base(s):
    for cr in ("1,1", "2,1", "3,1", "4,1"):
        put(s, cr, "wisp_1", "A")


def test_the_den_is_raided_only_through_its_base():
    s = state(turn=11, hands={"A": ["wisp_3"]}, food={"A": 15, "B": 10})
    _a_chain_to_b_base(s)
    assert not raids(s)
    put(s, "5,1", "wisp_1", "A")
    assert {a.target for a in raids(s)} == {("hq", "B")}
    rules.apply_action(s, PlaceAction("wisp_3", ("hq", "B")))       # a 6: destroyed, not stolen
    assert s.food == {"A": 15, "B": 4} and "wisp_3" in s.remove_pile
    assert all(u.card_id != "wisp_3" for st in s.board.values() for u in st)


def test_a_raid_that_empties_the_den_wins():
    s = state(turn=11, hands={"A": ["wisp_6"]}, food={"A": 15, "B": 4})
    _a_chain_to_b_base(s)
    put(s, "5,1", "wisp_1", "A")
    rules.apply_action(s, PlaceAction("wisp_6", ("hq", "B")))
    assert s.food["B"] == 0 and s.result.winner == "A" and s.result.reason == "starved"


def test_a_flier_lands_anywhere_and_drops_straight_into_the_enemy_den():
    s = state(turn=11, hands={"A": ["flight_5", "wisp_5"]}, food={"A": 15, "B": 15})
    assert places(s, "flight_5") == set(BOARD.crossroads)
    acts = rules.legal_actions(s)
    assert PlaceAction("flight_5", ("hq", "B")) in acts and PlaceAction("wisp_5", ("hq", "B")) not in acts
    rules.apply_action(s, PlaceAction("flight_5", ("hq", "B")))
    assert s.food["B"] == 15 - CARDS["flight_5"].base_strength


# ------------------------------------------------------------------ the keywords

def test_spikes_removes_the_first_enemy_that_covers_it_and_stays():
    s = state(turn=21, hands={"A": ["wisp_3", "wisp_4"]})
    put(s, "1,1", "wisp_1", "A")
    spikes = put(s, "2,1", "spikes_1", "B")
    rules.apply_action(s, PlaceAction("wisp_3", ("cr", "2,1")))
    assert s.board["2,1"] == [spikes] and spikes.retaliation_used and "wisp_3" in s.remove_pile
    rules.apply_action(s, PlaceAction("wisp_4", ("cr", "2,1")))     # spent: the next cover takes it
    assert [u.card_id for u in s.board["2,1"]] == ["wisp_4"]


def test_poison_removes_its_coverer_at_the_start_of_its_owners_turn():
    s = state(turn=11, hands={"A": ["wisp_6"]})
    put(s, "1,1", "wisp_1", "A")
    put(s, "2,1", "test_poison", "B")
    rules.apply_action(s, PlaceAction("wisp_6", ("cr", "2,1")))
    assert [u.card_id for u in s.board["2,1"]] == ["wisp_6"]
    rules.apply_action(s, PassAction())
    assert "2,1" not in s.board and "wisp_6" in s.remove_pile


def test_armor_stops_a_bite_and_stealth_hides_from_one():
    s = state(turn=11)
    me = put(s, "1,1", "giant_hunter", "A")
    put(s, "2,1", "test_armor", "B")
    put(s, "2,2", "test_stealth", "B")
    assert _adjacent_enemy_targets(s, me, "1,1") == []


def test_hungry_lands_only_on_an_enemy_it_beats_and_its_kill_feeds():
    s = state(turn=11, hands={"A": ["hungry_2"]})             # strength 3
    put(s, "1,1", "wisp_1", "A")
    put(s, "2,1", "wisp_1", "B")                                # strength 2
    put(s, "2,2", "wisp_2", "B")                                # strength 4
    assert places(s, "hungry_2") == {"2,1"} and not raids(s)
    rules.apply_action(s, PlaceAction("hungry_2", ("cr", "2,1")))
    assert s.food["A"] == CFG.hungry_food and "wisp_1" in s.remove_pile


# ------------------------------------------------------------------ the cards

def test_hunters_give_an_adjacent_enemy_minus_n_strength_for_good():
    for cid, n in WEAKENS.items():
        assert CARDS[cid].text == f"Roar: give an adjacent enemy -{n} strength."
    s = state(turn=11, hands={"A": ["hunter_3", "test_one"]})
    put(s, "2,1", "wisp_2", "B")                                # strength 4
    put(s, "2,2", "wisp_1", "B")
    rules.apply_action(s, PlaceAction("hunter_3", ("cr", "1,1")))
    assert s.pending["options"] == ["2,1", "2,2"] and s.pending["chooser"] == "A"
    rules.apply_action(s, ChoiceAction("2,1"))
    assert effective_strength(s, s.board["2,1"][0]) == 1        # stays, weaker: the test_one (1) can't cover it
    assert "2,1" not in places(s, "test_one")


def test_an_animal_at_zero_strength_is_removed_armor_or_not():
    s = state(turn=11, hands={"A": ["hunter_3"]})
    put(s, "2,1", "death_draw_1", "B")                          # strength 1
    rules.apply_action(s, PlaceAction("hunter_3", ("cr", "1,1")))
    rules.apply_action(s, ChoiceAction("2,1"))
    assert "2,1" not in s.board and len(s.hands["B"]) == 1      # removed, and its Death fires
    s = state(turn=11, hands={"A": ["hunter_3"]})
    put(s, "2,1", "test_armor", "B")
    rules.apply_action(s, PlaceAction("hunter_3", ("cr", "1,1")))
    rules.apply_action(s, ChoiceAction("2,1"))
    assert "2,1" not in s.board                                 # the rules' removal: Armor doesn't hold
    s = state(turn=11, hands={"A": ["shade_hand", "test_one"]})
    rules.apply_action(s, PlaceAction("shade_hand", ("cr", "1,1")))
    assert effective_strength(s, s.board["1,1"][0]) == 1        # one card left in hand
    rules.apply_action(s, PlaceAction("test_one", ("cr", "1,2")))
    assert "1,1" not in s.board                                 # the hand emptied: the Hand Shade is at 0, removed


def test_the_giant_hunter_removes_any_adjacent_enemy():
    s = state(turn=11, hands={"A": ["giant_hunter"]})
    put(s, "2,1", "wisp_6", "B")
    rules.apply_action(s, PlaceAction("giant_hunter", ("cr", "1,1")))
    rules.apply_action(s, ChoiceAction("2,1"))
    assert "2,1" not in s.board


def test_a_cantrip_draws_a_card():
    s = state(turn=11, hands={"A": ["cantrip_2"]})
    rules.apply_action(s, PlaceAction("cantrip_2", ("cr", "1,2")))
    assert [u.card_id for u in s.hands["A"]] == ["wisp_1"]


def test_death_draw_draws_when_it_is_removed_by_anything():
    s = state(turn=11, hands={"A": ["wisp_1"]})
    put(s, "1,1", "wisp_1", "A")
    put(s, "2,1", "death_draw_1", "B")
    rules.apply_action(s, PlaceAction("wisp_1", ("cr", "2,1")))     # covered: removed by the rules
    assert len(s.hands["B"]) == 1 and len(s.hands["A"]) == 0
    s = state(turn=11, hands={"A": ["giant_hunter"]})
    put(s, "2,1", "death_draw_1", "B")
    rules.apply_action(s, PlaceAction("giant_hunter", ("cr", "1,1")))
    rules.apply_action(s, ChoiceAction("2,1"))                      # removed by an ability
    assert len(s.hands["B"]) == 1


def test_kill_draw_draws_only_when_it_removes_an_enemy():
    s = state(turn=11, hands={"A": ["kill_draw_2"]})                # strength 2
    put(s, "1,1", "test_one", "A")
    put(s, "2,1", "test_one", "B")                                    # strength 1
    rules.apply_action(s, PlaceAction("kill_draw_2", ("cr", "1,2")))
    assert s.hands["A"] == []                                       # an empty tile: nothing removed
    s.hands["A"].append(UnitInstance("kill_draw_2", "A", s.new_iid()))
    rules.apply_action(s, PlaceAction("kill_draw_2", ("cr", "2,1")))
    assert "test_one" in s.remove_pile and [u.card_id for u in s.hands["A"]] == ["wisp_1"]
    s = state(turn=11, hands={"A": ["kill_draw_2"]})
    put(s, "1,1", "test_one", "A")
    put(s, "2,1", "spikes_1", "B")                                  # Spikes removes it first: its prey stands
    rules.apply_action(s, PlaceAction("kill_draw_2", ("cr", "2,1")))
    assert s.hands["A"] == [] and [u.card_id for u in s.board["2,1"]] == ["spikes_1"]


def test_raid_draw_flies_into_the_den_then_draws():
    s = state(turn=11, hands={"A": ["raid_draw_5"]}, food={"A": 15, "B": 15})
    assert CARDS["raid_draw_5"].keywords == {"Flight"}
    rules.apply_action(s, PlaceAction("raid_draw_5", ("hq", "B")))   # a flier: no connection needed
    assert s.food["B"] == 10 and [u.card_id for u in s.hands["A"]] == ["wisp_1"]


def test_double_raid_destroys_double_its_strength():
    for cid in ("double_raid_2", "double_raid_4"):
        assert CARDS[cid].text == "Its raids destroy double food."
        s = state(turn=11, hands={"A": [cid]}, food={"A": 15, "B": 15})
        for cr in ("1,1", "2,1", "3,1", "4,1", "5,1"):
            put(s, cr, "test_one", "A")
        rules.apply_action(s, PlaceAction(cid, ("hq", "B")))
        assert s.food["B"] == 15 - CARDS[cid].base_strength * CFG.double_raid_factor


def test_scout_takes_one_of_the_top_three_and_shuffles_the_rest_back():
    s = state(turn=11, hands={"A": ["scout_3"]}, decks={"A": ["wisp_1", "wisp_2", "wisp_3", "wisp_4", "wisp_5"]})
    rules.apply_action(s, PlaceAction("scout_3", ("cr", "1,1")))
    assert s.pending["chooser"] == "A" and s.pending["options"] == ["deck:0", "deck:1", "deck:2"]   # the top is the end
    rules.apply_action(s, ChoiceAction("deck:1"))                    # the second from the top: wisp_4
    assert [u.card_id for u in s.hands["A"]] == ["wisp_4"]
    assert sorted(s.decks["A"]) == ["wisp_1", "wisp_2", "wisp_3", "wisp_5"]


def test_duplicating_spore_places_a_spore_on_an_adjacent_tile_it_could_be_placed_on():
    s = state(turn=11, hands={"A": ["duplicating_spore"]})
    put(s, "1,2", "wisp_1", "A")                                     # yours: offered, and covered
    put(s, "2,1", "wisp_1", "B")                                     # an enemy of 2: the Spore's 1 can't cover it
    rules.apply_action(s, PlaceAction("duplicating_spore", ("cr", "1,1")))
    assert "1,2" in s.pending["options"] and "2,1" not in s.pending["options"]
    rules.apply_action(s, ChoiceAction("1,2"))
    assert [u.card_id for u in s.board["1,2"]] == ["spore"] and "wisp_1" in s.remove_pile
    assert rules.mana_left(s, "A") == 6 - 1                          # the Spore came free


def test_mama_spore_puts_two_spores_into_your_hand_and_they_play():
    s = state(turn=11, hands={"A": ["mama_spore"]})
    rules.apply_action(s, PlaceAction("mama_spore", ("cr", "1,1")))
    assert [u.card_id for u in s.hands["A"]] == ["spore", "spore"]
    assert not CARDS["spore"].collectible and CARDS["spore"].cost == 1 and CARDS["spore"].base_strength == 1
    rules.apply_action(s, PlaceAction("spore", ("cr", "1,2")))       # a token in hand plays like any card
    assert rules.mana_left(s, "A") == 6 - 2


def test_djinn_cost_less_for_each_of_their_count():
    s = state(hands={"A": ["djinn_hand", "djinn_ally", "djinn_enemy", "djinn_food", "djinn_removed"]}, food={"A": 20, "B": 9})
    s.food_gained = {"A": 4, "B": 9}                              # the Food Djinn counts what was gained, not what is held
    put(s, "1,1", "wisp_1", "A"); put(s, "1,2", "wisp_1", "A"); put(s, "3,3", "wisp_1", "B")
    s.remove_pile.extend(["wisp_1", "wisp_1", "wisp_2"]); s.pile_owners.extend(["B", "B", "A"])
    assert {cid: mana_cost(s, cid) for cid in ("djinn_hand", "djinn_ally", "djinn_enemy", "djinn_food", "djinn_removed")} == \
        {"djinn_hand": 5, "djinn_ally": 8, "djinn_enemy": 9, "djinn_food": 6, "djinn_removed": 8}
    s.food_gained["A"] = 15
    assert mana_cost(s, "djinn_food") == 0 and mana_cost(s, "djinn_food", "B") == 1


def test_food_gained_counts_every_gain_and_not_the_start():
    s = state(turn=4, food={"A": 15, "B": 15})
    for cr in ("1,1", "1,2", "2,2"):
        put(s, cr, "wisp_1", "A")
    rules.apply_action(s, PassAction())                         # a region's income
    assert s.food_gained == {"A": 1, "B": 0}


def test_shade_strength_is_its_count():
    s = state(hands={"A": ["wisp_1", "wisp_1", "wisp_1"]}, food={"A": 20, "B": 2})
    s.food_gained = {"A": 7, "B": 2}
    shades = {k: put(s, cr, f"shade_{k}", "A") for k, cr in
              (("hand", "1,1"), ("ally", "1,2"), ("enemy", "1,3"), ("food", "2,1"), ("removed", "2,2"))}
    put(s, "4,1", "wisp_1", "B"); put(s, "4,2", "wisp_1", "B")
    s.remove_pile.extend(["wisp_1", "wisp_2"]); s.pile_owners.extend(["B", "A"])
    assert {k: effective_strength(s, u) for k, u in shades.items()} == {"hand": 3, "ally": 5, "enemy": 2, "food": 7, "removed": 1}


# ------------------------------------------------------------------ the leaders

def test_the_warlord_gains_a_food_for_each_cover_of_an_enemy():
    s = state(turn=11, hands={"A": ["wisp_5"]}, leaders={"A": WARLORD})
    put(s, "1,1", "wisp_1", "A")
    put(s, "2,1", "wisp_1", "B")
    rules.apply_action(s, PlaceAction("wisp_5", ("cr", "2,1")))
    assert s.food["A"] == CFG.warlord_leader_food


def test_the_raiders_raids_destroy_two_more():
    s = state(turn=11, hands={"A": ["flight_1"]}, food={"A": 15, "B": 15}, leaders={"A": RAIDER})
    rules.apply_action(s, PlaceAction("flight_1", ("hq", "B")))
    assert s.food["B"] == 15 - 1 - CFG.raider_leader_bonus


def test_the_elfs_regions_produce_one_more_food_each():
    s = state(turn=4, food={"A": 15, "B": 15}, leaders={"A": ELF})
    for cr in ("1,1", "1,2", "2,2"):
        put(s, cr, "wisp_1", "A")
    assert rules.region_income(s, "A") == 1 + CFG.elf_region_bonus


def test_the_assassin_draws_after_the_third_card_of_a_turn_only():
    s = state(turn=11, hands={"A": ["wisp_1", "wisp_1", "wisp_1", "wisp_1"]}, leaders={"A": ASSASSIN})
    for i, cr in enumerate(("1,1", "1,2", "1,3", "2,1")):
        rules.apply_action(s, PlaceAction("wisp_1", ("cr", cr)))
        assert len(s.hands["A"]) == [3, 2, 2, 1][i]                  # the third card draws one; the fourth doesn't
    assert all(CARDS[l].cost == 5 and CARDS[l].base_strength == 10 for l in LEADERS)


def test_the_sages_power_draws_a_card_for_three_mana_and_again():
    s = state(turn=10, leaders={"A": SAGE})                       # 6 mana
    assert LEADERS[SAGE][0] == "power"
    rules.apply_action(s, LeaderAction())
    rules.apply_action(s, LeaderAction())
    assert len(s.hands["A"]) == 2 and rules.mana_left(s, "A") == 0 and LeaderAction() not in rules.legal_actions(s)


# ------------------------------------------------------------------ decks and the game as a whole

def test_deck_rules():
    assert deck_problems(DECK, "warlord_legend") == []
    assert deck_problems(DECK, None) == ["a deck needs a leader"]
    assert deck_problems(DECK[:-1], "warlord_legend")
    assert any("at most 2" in p for p in deck_problems(DECK[:-2] + ["wisp_1", "warlord_legend"], "warlord_legend"))
    assert any("collectible" in p for p in deck_problems(DECK[:-2] + ["test_reserve", "warlord_legend"], "warlord_legend", cards=CARDS))


def test_a_game_replays_from_its_seed_and_actions():
    rng = random.Random(3)
    s = new_game(DECK, DECK, 3, leaders={"A": "warlord_legend", "B": "warlord_legend"})
    actions = []
    while not rules.is_terminal(s):
        a = rng.choice(rules.legal_actions(s))
        actions.append(a.to_dict())
        rules.apply_action(s, a)
    again = new_game(DECK, DECK, 3, leaders={"A": "warlord_legend", "B": "warlord_legend"})
    for a in actions:
        rules.apply_logged(again, a)
    assert again.food == s.food and again.result == s.result
    assert GameState.from_dict(s.to_dict()).to_dict() == s.to_dict()


def test_the_bot_beats_random_play():
    from animal_kingdom.bots.greedy import GreedyBot
    wins = 0
    for seed in range(10):
        rng, bot = random.Random(seed), GreedyBot(seed)
        s = new_game(DECK, DECK, seed, leaders={"A": "warlord_legend", "B": "warlord_legend"})
        while not rules.is_terminal(s):
            legal = rules.legal_actions(s)
            p = s.player_to_act()
            rules.apply_action(s, bot.choose(s.view_for(p), legal, s) if p == "A" else rng.choice(legal))
        wins += s.result.winner == "A"
    assert wins >= 8
