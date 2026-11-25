"""The rules: mana, the board and its bases, covering, the den raid, food, the keywords, the cards' effects, the leaders."""

import random
from itertools import combinations

from dataclasses import replace

from animal_kingdom import game as rules    # the rules, answered by the Rust engine
from animal_kingdom.decks import deck_problems
from animal_kingdom.game import (ANGEL, ASSASSIN, ELF, LEADERS, MANA_EATER, MAP_ID, PYROMANCER, RAIDER, RENO, SAGE, SKIP, WARLORD, WEAKENS, ChoiceAction, Config,
                                 GameState, LeaderAction, PassAction, PlaceAction, UnitInstance, effective_strength,
                                 load_cards, load_map, mana_cost, new_game)

effects = rules

CARDS = load_cards()
# Poison, Armor and Stealth are on no card right now (Martin, 2026-11-21, his paper cards); the rules keep them, tested on
# stand-ins.
for _kw in ("Poison", "Armor", "Stealth"):
    CARDS[f"test_{_kw.lower()}"] = replace(CARDS["wisp_1"], id=f"test_{_kw.lower()}", keywords=frozenset({_kw}))
CARDS["test_reserve"] = replace(CARDS["wisp_1"], id="test_reserve", status="reserve")
CARDS["test_one"] = replace(CARDS["wisp_1"], id="test_one", base_strength=1)
CARDS["test_three"] = replace(CARDS["wisp_1"], id="test_three", base_strength=3)
CARDS["test_five"] = replace(CARDS["wisp_1"], id="test_five", base_strength=5)   # a plain 1, for a board that needs one
# A strength that is a count is on no card since the Shades left (Martin, 2026-11-21); the engine keeps it, tested here.
for _n in ("hand", "ally", "region", "played"):
    CARDS[f"test_{_n}_count"] = replace(CARDS["wisp_1"], id=f"test_{_n}_count", base_strength="dynamic", dynamic_strength=f"{_n}_count")
CFG = Config()
BOARD = load_map(MAP_ID)
BASE = {"A": {"1,1", "1,2", "1,3"}, "B": {"5,1", "5,2", "5,3"}}
DECK = ([f"wisp_{n}" for n in range(1, 7) for _ in range(2)] + [f"flight_{n}" for n in (1, 3, 6) for _ in range(2)]
        + ["spikes_1", "spikes_1", "cantrip_2", "cantrip_2", "spikes_3", "spikes_3", "warlord_legend"])


def state(*, turn=0, current="A", hands=None, decks=None, food=None, leaders=None, config=CFG) -> GameState:
    """A bare position: turn_counter `turn` (A's Nth own turn is turn 2N-2), nothing pending."""
    s = GameState(BOARD, CARDS, config, board={}, hands={"A": [], "B": []},
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


def test_a_turn_the_cap_ends_leaves_no_animal_buried():
    # the cap ends the turn while the Hunter's Roar still waits for its target: the animal it covered goes all the same
    s = state(turn=11, hands={"A": ["hunter_4"]}, config=CFG.sweep(max_actions_per_turn=1))
    put(s, "1,1", "wisp_1", "B")
    put(s, "2,1", "wisp_2", "B")
    rules.apply_action(s, PlaceAction("hunter_4", ("cr", "1,1")))
    assert s.current == "B" and s.pending is None and [c["cap"] for c in s.caps] == ["actions"]
    assert [u.card_id for u in s.board["1,1"]] == ["hunter_4"] and s.remove_pile == ["wisp_1"]


def test_the_turn_limit_ends_the_game_on_food_and_nothing_is_legal_after():
    s = state(turn=0, food={"A": 4, "B": 3}, config=CFG.sweep(max_turns=2))
    rules.apply_action(s, PassAction())
    assert s.result is None
    rules.apply_action(s, PassAction())
    assert (s.result.winner, s.result.reason) == ("A", "max_turns") and rules.is_terminal(s) == s.result
    assert rules.legal_actions(s) == [] and not rules.can_pass(s)
    try:
        rules.apply_action(s, PassAction())
    except rules.EngineError:
        pass
    else:
        raise AssertionError("an action after the game's end was accepted")


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


def test_the_porcupine_gives_adjacent_allies_spikes():
    s = state(turn=21, hands={"A": ["wisp_3", "wisp_4"]})
    put(s, "1,1", "wisp_1", "A")
    ally = put(s, "2,1", "wisp_1", "B")
    put(s, "3,1", "porcupine", "B")                                  # adjacent to 2,1
    put(s, "1,2", "wisp_1", "B")                                     # not adjacent to the Porcupine
    rules.apply_action(s, PlaceAction("wisp_3", ("cr", "2,1")))
    assert s.board["2,1"] == [ally] and "wisp_3" in s.remove_pile    # its Spikes removed the coverer
    rules.apply_action(s, PlaceAction("wisp_4", ("cr", "1,2")))
    assert [u.card_id for u in s.board["1,2"]] == ["wisp_4"]         # no Spikes out of its reach


def test_poison_removes_its_coverer_at_the_start_of_its_owners_turn():
    s = state(turn=11, hands={"A": ["wisp_6"]})
    put(s, "1,1", "wisp_1", "A")
    put(s, "2,1", "test_poison", "B")
    rules.apply_action(s, PlaceAction("wisp_6", ("cr", "2,1")))
    assert [u.card_id for u in s.board["2,1"]] == ["wisp_6"]
    rules.apply_action(s, PassAction())
    assert "2,1" not in s.board and "wisp_6" in s.remove_pile


def test_armor_stops_a_bite_and_stealth_hides_from_one():
    s = state(turn=11, hands={"A": ["giant_hunter"]})
    put(s, "2,1", "test_armor", "B")
    put(s, "2,2", "test_stealth", "B")
    rules.apply_action(s, PlaceAction("giant_hunter", ("cr", "1,1")))   # "Roar: remove an adjacent enemy."
    assert s.pending is None and s.remove_pile == []                    # neither may be chosen: nothing is asked


def test_hungry_lands_only_on_an_enemy_it_beats_and_its_kill_feeds():
    s = state(turn=11, hands={"A": ["hungry_3"]})             # strength 5
    put(s, "1,1", "wisp_1", "A")
    put(s, "2,1", "wisp_1", "B")                                # strength 2
    put(s, "2,2", "wisp_3", "B")                                # strength 6
    assert places(s, "hungry_3") == {"2,1"} and not raids(s)
    rules.apply_action(s, PlaceAction("hungry_3", ("cr", "2,1")))
    assert s.food["A"] == CFG.hungry_food and "wisp_1" in s.remove_pile


# ------------------------------------------------------------------ the cards

def test_hunters_give_an_adjacent_enemy_minus_n_strength_for_good():
    for cid, n in WEAKENS.items():
        assert CARDS[cid].text.endswith(f"Roar: give an adjacent enemy -{n} strength.")
    s = state(turn=11, hands={"A": ["hunter_4", "test_one"]})
    put(s, "2,1", "wisp_2", "B")                                # strength 4
    put(s, "2,2", "wisp_1", "B")
    rules.apply_action(s, PlaceAction("hunter_4", ("cr", "1,1")))
    assert s.pending["options"] == ["2,1", "2,2"] and s.pending["chooser"] == "A"
    rules.apply_action(s, ChoiceAction("2,1"))
    assert effective_strength(s, s.board["2,1"][0]) == 1        # stays, weaker: the test_one (1) can't cover it
    assert "2,1" not in places(s, "test_one")


def test_gorrak_one_eye_is_hungry_and_gains_food_equal_to_the_strength_of_the_enemy_he_removes():
    assert CARDS["warlord_legend"].name == "Gorrak One-Eye" and CARDS["warlord_legend"].keywords == {"Hungry"}
    s = state(turn=12, hands={"A": ["warlord_legend"]})
    assert places(s, "warlord_legend") == set()                 # Hungry: nothing to eat
    put(s, "1,1", "wisp_3", "B")                                # strength 6
    put(s, "2,1", "wisp_1", "B")
    food = s.food["A"]
    rules.apply_action(s, PlaceAction("warlord_legend", ("cr", "1,1")))
    assert s.pending is None and [u.card_id for u in s.board["1,1"]] == ["warlord_legend"] and "2,1" in s.board
    assert s.food["A"] == food + CARDS["wisp_3"].base_strength + CFG.hungry_food     # the 6 he ate, and Hungry's own
    s = state(turn=14, hands={"A": ["warlord_legend"]})
    put(s, "1,1", "spikes_3", "B")                              # Spikes removes him: his prey stays, so no food
    food = s.food["A"]
    rules.apply_action(s, PlaceAction("warlord_legend", ("cr", "1,1")))
    assert [u.card_id for u in s.board["1,1"]] == ["spikes_3"] and s.food["A"] == food


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
    s = state(turn=11, hands={"A": ["test_hand_count", "test_one"]})
    rules.apply_action(s, PlaceAction("test_hand_count", ("cr", "1,1")))
    assert effective_strength(s, s.board["1,1"][0]) == CFG.shade_growth   # one card left in hand
    rules.apply_action(s, PlaceAction("test_one", ("cr", "1,2")))
    assert "1,1" not in s.board                                 # the hand emptied: it is at 0, removed


def test_the_giant_hunter_removes_any_adjacent_enemy():
    s = state(turn=11, hands={"A": ["giant_hunter"]})
    put(s, "2,1", "wisp_6", "B")
    rules.apply_action(s, PlaceAction("giant_hunter", ("cr", "1,1")))
    rules.apply_action(s, ChoiceAction("2,1"))
    assert "2,1" not in s.board


def test_a_chosen_target_is_an_aim_event_from_its_source_before_the_effect():
    for card, kind in (("hunter_4", "strength"), ("giant_hunter", "remove")):
        s = state(turn=11, hands={"A": [card]})
        put(s, "2,1", "wisp_6", "B")
        rs = s._sync()
        rs.record_events(True)
        rs.apply_action(PlaceAction(card, ("cr", "1,1")).to_dict())
        source = rs.to_dict()["board"]["1,1"][-1]["iid"]
        rs.take_events()
        rs.apply_action(ChoiceAction("2,1").to_dict())
        ev = rs.take_events()
        aim = ev[0]
        assert aim["e"] == "aim" and aim["cr"] == "2,1" and aim["player"] == "A" and aim["card"] == "wisp_6"
        assert aim["cause"] == card and aim["cause_iid"] == source and ev[1]["e"] == kind


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
    assert s.food["B"] == 14 and [u.card_id for u in s.hands["A"]] == ["wisp_1"]


def test_nightmare_raids_at_double_strength():
    cid = "raider_legend"
    assert CARDS[cid].name == "Nightmare" and CARDS[cid].text == "Double strength when raiding."
    s = state(turn=11, hands={"A": [cid]}, food={"A": 15, "B": 15})
    for cr in ("1,1", "2,1", "3,1", "4,1", "5,1"):
        put(s, cr, "test_one", "A")
    rules.apply_action(s, PlaceAction(cid, ("hq", "B")))
    assert s.food["B"] == 15 - CARDS[cid].base_strength * CFG.double_raid_factor


def test_scout_takes_one_of_three_cards_from_anywhere_in_the_deck_and_the_rest_stay_where_they_were():
    deck = [c for c in CARDS if c.startswith(("wisp_", "spikes_", "cantrip_"))][:12]
    assert len(deck) == 12
    shown_sets = set()
    for seed in range(12):
        s = state(turn=11, hands={"A": ["scout_3"]}, decks={"A": list(deck)})
        version, internal, gauss = random.Random(seed).getstate()
        s._rng = {"version": version, "state": list(internal), "gauss": gauss}
        rules.apply_action(s, PlaceAction("scout_3", ("cr", "1,1")))
        assert s.pending["chooser"] == "A" and s.pending["options"] == ["deck:0", "deck:1", "deck:2"]
        shown = s.decks["A"][-3:]                                      # while she looks, they lie on top
        assert sorted(s.decks["A"]) == sorted(deck)
        t = GameState.from_dict(s.to_dict())                           # the look, saved and restored
        for g in (s, t):
            rules.apply_action(g, ChoiceAction("deck:1"))              # the middle one of the three
            assert [u.card_id for u in g.hands["A"]] == [shown[1]]
            assert g.decks["A"] == [c for c in deck if c != shown[1]]  # nothing else moved
        shown_sets.add(tuple(shown))
    assert len(shown_sets) > 6 and any(set(sh) != set(deck[-3:]) for sh in shown_sets)   # from anywhere, not the top


def test_duplicating_spore_places_a_spore_on_a_random_adjacent_empty_crossroad():
    around = sorted(BOARD.neighbors("2,2"))                          # 1,1 among them, which connects 2,2
    empty, taken = [cr for cr in around if cr != "1,1"][:2], [cr for cr in around if cr != "1,1"][2:]
    landed = set()
    for seed in range(12):
        s = state(turn=11, hands={"A": ["duplicating_spore"]})
        s._rng = new_game(["wisp_1"] * 25, ["wisp_1"] * 25, seed)._rng
        put(s, "1,1", "wisp_1", "A")
        for cr in taken:
            put(s, cr, "wisp_1", "B" if cr == taken[-1] else "A")   # yours or an enemy's: never covered
        rules.apply_action(s, PlaceAction("duplicating_spore", ("cr", "2,2")))
        assert s.pending is None                                      # no choice: the game picks
        spores = [cr for cr in around if [u.card_id for u in s.board.get(cr, [])] == ["spore"]]
        assert len(spores) == 1 and spores[0] in empty
        landed.add(spores[0])
        assert rules.mana_left(s, "A") == 6 - CARDS["duplicating_spore"].cost   # the Spore came free
    assert landed == set(empty)                                       # either empty one
    s = state(turn=11, hands={"A": ["duplicating_spore"]})
    put(s, "1,1", "wisp_1", "A")
    for cr in around:
        put(s, cr, "wisp_1", "A")
    rules.apply_action(s, PlaceAction("duplicating_spore", ("cr", "2,2")))
    assert "spore" not in [u.card_id for st in s.board.values() for u in st]   # none empty: no Spore


def test_mama_spore_puts_two_spores_into_your_hand_and_they_play():
    s = state(turn=11, hands={"A": ["mama_spore"]})
    rules.apply_action(s, PlaceAction("mama_spore", ("cr", "1,1")))
    assert [u.card_id for u in s.hands["A"]] == ["spore", "spore"]
    assert not CARDS["spore"].collectible and CARDS["spore"].cost == 1 and CARDS["spore"].base_strength == 1
    rules.apply_action(s, PlaceAction("spore", ("cr", "1,2")))       # a token in hand plays like any card
    assert rules.mana_left(s, "A") == 6 - CARDS["mama_spore"].cost - CARDS["spore"].cost


def test_rhino_and_albatross_remove_every_adjacent_enemy_of_five_or_less():
    for cid in ("rhino", "albatross"):
        s = state(turn=19, hands={"A": [cid]})                        # 10 mana
        put(s, "1,1", "wisp_1", "A")                                  # connects 2,1 and 2,2
        put(s, "1,2", "wisp_2", "B")                                  # 4: removed
        put(s, "2,3", "wisp_3", "B")                                  # 6: stays
        put(s, "3,2", "test_stealth", "B")                            # Stealth doesn't hide from "all"
        put(s, "3,3", "test_armor", "B")                              # Armor holds
        rules.apply_action(s, PlaceAction(cid, ("cr", "2,2")))
        assert "1,2" not in s.board and "3,2" not in s.board and "2,3" in s.board and "3,3" in s.board
        assert "1,1" in s.board                                       # its own side untouched
    assert CARDS["albatross"].keywords == {"Flight"} and (CARDS["albatross"].cost, CARDS["albatross"].base_strength) == (8, 4)
    assert CARDS["rhino"].text.endswith("5 or less.") and CARDS["albatross"].text.endswith("4 or less.")
    s = state(turn=19, hands={"A": ["rhino", "albatross"]})          # an enemy of 5: the Rhino's, not the Albatross's
    put(s, "1,1", "wisp_1", "A"); put(s, "3,1", "test_five", "B"); put(s, "3,2", "wisp_2", "B")   # 5 and 4, both next to 2,1
    rules.apply_action(s, PlaceAction("albatross", ("cr", "2,1")))
    assert "3,1" in s.board and "3,2" not in s.board


def test_the_young_rhino_and_albatross_remove_adjacent_enemies_up_to_three_and_two():
    for cid, limit in (("young_rhino", 3), ("young_albatross", 2)):
        assert CARDS[cid].text.endswith(f"remove all adjacent enemies with strength {limit} or less.")
        s = state(turn=19, hands={"A": [cid]})
        put(s, "1,1", "wisp_1", "A")
        put(s, "1,2", "test_one", "B")                                # 1: removed by both
        put(s, "2,1", "test_three", "B")                              # 3: the Rhino's, not the Albatross's
        put(s, "2,3", "wisp_2", "B")                                  # 4: stays
        rules.apply_action(s, PlaceAction(cid, ("cr", "2,2")))
        assert "1,2" not in s.board and "2,3" in s.board and ("2,1" in s.board) == (limit < 3)
    assert [(CARDS[c].cost, CARDS[c].base_strength) for c in ("young_rhino", "young_albatross")] == [(4, 6), (4, 2)]


def test_djinn_cost_less_for_each_of_their_count():
    s = state(turn=19, hands={"A": ["djinn_hand", "djinn_ally", "djinn_combo", "djinn_region", "wisp_1", "wisp_1"]})
    for cr in ("1,1", "1,2", "2,2"):                                  # three allies, one region of A's
        put(s, cr, "wisp_1", "A")
    assert {cid: mana_cost(s, cid) for cid in ("djinn_hand", "djinn_ally", "djinn_combo", "djinn_region")} == \
        {"djinn_hand": 6, "djinn_ally": 9, "djinn_combo": 12, "djinn_region": 12}   # no food produced yet
    rules.apply_action(s, PlaceAction("wisp_1", ("cr", "1,3"))); rules.apply_action(s, PlaceAction("wisp_1", ("cr", "2,3")))
    assert mana_cost(s, "djinn_combo") == 12 - 2 * CFG.combo_djinn_discount   # two cards played this turn
    assert mana_cost(s, "djinn_combo", "B") == 12                     # B played none: it isn't their turn


def test_food_djinn_costs_less_for_each_food_your_regions_produced_this_game():
    s = state(turn=11, hands={"A": ["djinn_region"]}, food={"A": 5, "B": 5}, leaders={"A": ELF})
    for cr in ("1,1", "1,2", "2,2"):                                  # one region, its food 1, and 1 more from the Elf
        put(s, cr, "wisp_1", "A")
    assert mana_cost(s, "djinn_region") == 12
    rules.apply_action(s, PassAction())                               # A's regions produce 2
    rules.apply_action(s, PassAction())
    assert s.food_produced == {"A": 2, "B": 0} and mana_cost(s, "djinn_region") == 10
    rules.apply_action(s, PassAction()); rules.apply_action(s, PassAction())
    assert mana_cost(s, "djinn_region") == 8                          # it adds up over the game


def test_burn_djinn_costs_less_for_each_food_the_opponent_lost_this_game():
    s = state(turn=11, hands={"A": ["flight_5", "djinn_burn"], "B": ["djinn_burn"]}, food={"A": 15, "B": 15})
    assert mana_cost(s, "djinn_burn") == 12
    rules.apply_action(s, PlaceAction("flight_5", ("hq", "B")))      # the raid destroys 5 of B's food
    assert s.food["B"] == 10 and mana_cost(s, "djinn_burn") == 7
    assert mana_cost(s, "djinn_burn", "B") == 12                      # A lost none
    rules.apply_action(s, PassAction())                               # a new turn: what was lost still counts
    assert mana_cost(s, "djinn_burn", "A") == 7


def test_sky_maw_lands_only_on_a_weaker_enemy_anywhere_and_never_raids():
    s = state(turn=2, hands={"A": ["sky_maw_2"]})                    # Flight. Hungry. (2 mana, 3)
    put(s, "4,2", "wisp_1", "B")                                     # strength 2, far from A's base
    put(s, "4,3", "wisp_2", "B")                                     # strength 4: too strong
    assert places(s, "sky_maw_2") == {"4,2"} and not raids(s)


def test_bird_egg_falls_into_two_flight_1():
    s = state(turn=11, hands={"A": ["wisp_1"]})
    put(s, "1,1", "bird_egg", "B")
    rules.apply_action(s, PlaceAction("wisp_1", ("cr", "1,1")))      # covered: it falls from the board
    resolve_choices(s)
    assert [u.card_id for u in s.hands["B"]] == ["flight_1", "flight_1"]


def test_golden_egg_draws_a_card_when_drawn():
    s = state(turn=11, decks={"A": ["wisp_1"] * 3, "B": ["wisp_2", "wisp_3", "golden_egg"]})
    rules.apply_action(s, PassAction())                               # B's turn card is the egg: it draws the next
    assert [u.card_id for u in s.hands["B"]] == ["golden_egg", "wisp_3"]


def test_a_dynamic_strength_is_its_count():
    s = state(turn=19, hands={"A": ["wisp_1", "wisp_1", "wisp_1", "test_played_count"]})
    shades = {k: put(s, cr, f"test_{k}_count", "A") for k, cr in (("hand", "1,1"), ("ally", "1,2"), ("region", "2,2"))}
    assert rules.region_income(s, "A") == 1                          # 1,1 1,2 2,2: one region
    g = CFG.shade_growth
    assert {k: effective_strength(s, u) for k, u in shades.items()} == {"hand": 4 * g, "ally": 3 * g, "region": g}
    rules.apply_action(s, PlaceAction("wisp_1", ("cr", "1,3")))
    rules.apply_action(s, PlaceAction("test_played_count", ("cr", "2,3")))  # the second card this turn
    assert effective_strength(s, s.board["2,3"][-1]) == 2 * g


# ------------------------------------------------------------------ the leaders (Martin's list of 2026-11-25)

def test_the_nine_leaders_and_their_cards():
    assert list(LEADERS) == [RAIDER, ELF, ANGEL, ASSASSIN, SAGE, RENO, PYROMANCER, WARLORD, MANA_EATER]
    assert all(passive and power for passive, power in LEADERS.values())
    assert {l: (CARDS[l].name, CARDS[l].cost, CARDS[l].base_strength) for l in LEADERS} == {
        RAIDER: ("Nightmare", 2, 2), ELF: ("Mother Nature", 5, 5), ANGEL: ("Angel Warrior", 6, 8), ASSASSIN: ("Rogue", 3, 3),
        SAGE: ("Mage", 4, 6), RENO: ("Reno", 5, 7), PYROMANCER: ("Pyromancer", 3, 3), WARLORD: ("Gorrak One-Eye", 7, 8),
        MANA_EATER: ("Mana Eater", 10, 14)}
    assert {l: rules.power_price(l) for l in LEADERS} == {RAIDER: 1, ELF: 2, ANGEL: 1, ASSASSIN: 1, SAGE: 3, RENO: 3, PYROMANCER: 2,
                                                          WARLORD: 2, MANA_EATER: 1}
    assert [CARDS[f].name for f in ("flight_1", "flight_3", "flight_6", "flight_10")] == ["Baby Fireball", "Young Fireball", "Adult Fireball", "Elder Fireball"]


def test_nightmare_starts_on_the_bottom_grows_at_every_dusk_and_his_power_swaps_him_up_then_draws_him():
    deck = DECK[:-1] + [RAIDER]
    for seed in range(6):
        s = new_game(deck, DECK, seed, leaders={"A": RAIDER, "B": WARLORD})
        assert s.decks["A"][0] == RAIDER and all(u.card_id != RAIDER for u in s.hands["A"])   # the bottom is the start
        returned = False
        while s.pending and s.pending.get("kind") == "mulligan":
            if s.pending["chooser"] == "A" and not returned:
                rules.apply_action(s, ChoiceAction(s.hands["A"][0].iid)); returned = True   # one back: the deck is shuffled
            else:
                rules.apply_action(s, ChoiceAction(SKIP))
        assert s.decks["A"][0] == RAIDER                                # a mulligan's shuffle leaves him there
    base = CARDS[RAIDER].base_strength
    s = state(turn=19, hands={"A": ["wisp_1"]}, decks={"A": ["wisp_3", RAIDER, "wisp_5", "wisp_6"], "B": ["wisp_1"] * 4},
              leaders={"A": RAIDER}, food={"A": 15, "B": 15})
    assert rules.power_text(s, "A") == "Swap Nightmare with the card above."
    rules.apply_action(s, LeaderAction())                              # the deck's top is its end: he swaps with Wisp 5
    assert s.decks["A"] == ["wisp_3", "wisp_5", RAIDER, "wisp_6"] and rules.mana_left(s, "A") == 10 - CFG.raider_power_cost
    rules.apply_action(s, PassAction())                                # Dusk: he grows
    assert s.leeroy_growth["A"] == CFG.leeroy_growth
    rules.apply_action(s, PassAction())                                # B's Dusk doesn't grow him
    assert s.leeroy_growth["A"] == CFG.leeroy_growth and s.decks["A"][-1] == RAIDER
    assert rules.power_text(s, "A") == "Draw Nightmare." and rules.power_cost(s, "A") == CFG.raider_power_cost
    rules.apply_action(s, LeaderAction())                              # on top, the power draws him
    nm = next(u for u in s.hands["A"] if u.card_id == RAIDER)
    assert LeaderAction() not in rules.legal_actions(s)
    rules.apply_action(s, PassAction()); rules.apply_action(s, PassAction())
    assert effective_strength(s, nm) == base + CFG.leeroy_growth       # out of the deck, he grows no more
    assert not rules.leader_usable(s, "A")                             # in hand, the power has nothing to do
    rules.apply_action(s, PlaceAction(RAIDER, ("cr", "1,1")))
    rules.apply_action(s, PassAction()); rules.apply_action(s, PassAction())
    assert effective_strength(s, s.board["1,1"][-1]) == base + CFG.leeroy_growth       # nor on the board
    assert GameState.from_dict(s.to_dict()).leeroy_growth == s.leeroy_growth
    other = state(turn=19, decks={"A": [RAIDER]}, leaders={"A": SAGE})
    rules.apply_action(other, PassAction())
    assert other.leeroy_growth["A"] == 0                                # under another leader he doesn't grow


def test_mother_nature_one_more_food_a_region_her_power_and_her_card_doubling_its_regions():
    for leader, income in ((ELF, 3 * (1 + CFG.elf_region_bonus)), (SAGE, 3)):
        s = state(turn=10, leaders={"A": leader})
        for cr in ("1,1", "1,2", "2,2", "1,3", "2,3"):                # three regions (1,2 2,2 2,3 is one too)
            put(s, cr, "wisp_1", "A")
        assert rules.region_income(s, "A") == income
    s = state(turn=10, leaders={"A": ELF}, food={"A": 15, "B": 15})
    for cr in ("1,1", "1,2", "2,2"):
        put(s, cr, "wisp_1", "A")
    rules.apply_action(s, LeaderAction())                              # "Gain 1 food for each region you control."
    assert s.food["A"] == 15 + CFG.elf_power_food_per_region and rules.mana_left(s, "A") == 6 - CFG.elf_power_cost
    s = state(turn=10, leaders={"A": ELF})
    for cr in ("1,1", "1,2", "2,2", "1,3", "2,3"):
        put(s, cr, "wisp_1", "A")
    s.board["1,1"][-1].card_id = ELF                                   # her card on 1,1: only the region 1,1 1,2 2,2 holds it
    f = 1 + CFG.elf_region_bonus
    assert rules.region_income(s, "A") == f * CFG.elf_card_region_factor + 2 * f    # +1 first, then doubled: 1 becomes 4
    t = state(turn=10, leaders={"A": SAGE})
    for cr in ("1,1", "1,2", "2,2"):
        put(t, cr, "wisp_1", "A")
    t.board["1,1"][-1].card_id = ELF
    assert rules.region_income(t, "A") == CFG.elf_card_region_factor   # her card doubles under any leader


def test_the_angel_warriors_power_his_passive_on_a_removal_and_his_card_at_dawn():
    s = state(turn=19, hands={"A": ["wisp_3"]}, leaders={"A": ANGEL}, food={"A": 15, "B": 15})
    assert not rules.leader_usable(s, "A")                             # no ally to give +2
    put(s, "1,1", "wisp_1", "A"); put(s, "1,2", "wisp_1", "A")
    rules.apply_action(s, LeaderAction())
    assert sorted(s.pending["options"]) == ["1,1", "1,2"]
    rules.apply_action(s, ChoiceAction("1,2"))
    assert effective_strength(s, s.board["1,2"][-1]) == CARDS["wisp_1"].base_strength + CFG.angel_power_buff
    put(s, "2,1", "wisp_1", "B")
    rules.apply_action(s, PlaceAction("wisp_3", ("cr", "2,1")))       # it covers an enemy: removed, +1
    assert effective_strength(s, s.board["2,1"][-1]) == CARDS["wisp_3"].base_strength + CFG.angel_removal_buff
    assert "leader_trigger" in [e["e"] for e in s.events]
    s = state(turn=19, hands={"A": ["hunter_3"]}, leaders={"A": ANGEL}, food={"A": 15, "B": 15})   # a Roar's removal counts too
    put(s, "1,2", "wisp_1", "A"); put(s, "2,1", "test_one", "B")
    rules.apply_action(s, PlaceAction("hunter_3", ("cr", "1,1")))     # -2 on an enemy of 1: the rules remove it
    if s.pending:
        rules.apply_action(s, ChoiceAction("2,1"))
    assert "2,1" not in s.board and effective_strength(s, s.board["1,1"][-1]) == CARDS["hunter_3"].base_strength + CFG.angel_removal_buff
    s = state(turn=19, current="B", leaders={"A": SAGE}, decks={"A": ["wisp_1"] * 5, "B": ["wisp_1"] * 5})
    put(s, "1,1", ANGEL, "A"); put(s, "1,2", "wisp_1", "A"); put(s, "1,3", "wisp_1", "A"); put(s, "3,3", "wisp_1", "A")
    rules.apply_action(s, PassAction())                                # A's Dawn
    w = CARDS["wisp_1"].base_strength
    assert [effective_strength(s, s.board[c][-1]) for c in ("1,2", "1,3", "3,3")] == [w + CFG.angel_dawn_buff] * 2 + [w]
    assert effective_strength(s, s.board["1,1"][-1]) == CARDS[ANGEL].base_strength    # not himself


def test_the_rogues_third_card_costs_less_her_power_and_her_card():
    s = state(turn=19, hands={"A": ["wisp_2"] * 4 + ["wisp_3", "wisp_5"]}, leaders={"A": ASSASSIN}, decks={"A": ["wisp_1"] * 5})
    costs = []
    for cr in ("1,1", "1,2", "1,3", "2,1"):
        costs.append(mana_cost(s, "wisp_2"))
        rules.apply_action(s, PlaceAction("wisp_2", ("cr", cr)))
    assert costs == [2, 2, 2 - CFG.rogue_discount, 2]                  # the third
    assert rules.mana_left(s, "A") == 10 - 8 + CFG.rogue_discount
    rules.apply_action(s, LeaderAction())                              # four cards played: +4 to a card in her hand, hers to pick
    assert s.pending["options"] == [u.iid for u in s.hands["A"]] and not s.pending["optional"]
    rules.apply_action(s, ChoiceAction(s.hands["A"][1].iid))
    assert [effective_strength(s, u) for u in s.hands["A"]] == [CARDS["wisp_3"].base_strength, CARDS["wisp_5"].base_strength + 4 * CFG.rogue_power_per_card]
    assert rules.mana_left(s, "A") == 10 - 8 + CFG.rogue_discount - CFG.rogue_power_cost
    assert not any(isinstance(a, LeaderAction) for a in rules.legal_actions(s))                 # once a turn
    s = state(turn=19, hands={"A": ["wisp_2"]}, leaders={"A": ASSASSIN}, decks={"A": ["wisp_1"] * 5})
    assert not any(isinstance(a, LeaderAction) for a in rules.legal_actions(s))                 # no card played yet: nothing to give
    s = state(turn=19, hands={"A": ["wisp_1", "wisp_1", ASSASSIN]}, decks={"A": ["wisp_1"] * 5})
    rules.apply_action(s, PlaceAction("wisp_1", ("cr", "1,1"))); rules.apply_action(s, PlaceAction("wisp_1", ("cr", "1,2")))
    rules.apply_action(s, PlaceAction(ASSASSIN, ("cr", "1,3")))       # the third: she counts herself
    assert len(s.hands["A"]) == CFG.rogue_card_draws
    s = state(turn=19, hands={"A": ["wisp_1", ASSASSIN]}, decks={"A": ["wisp_1"] * 5})
    rules.apply_action(s, PlaceAction("wisp_1", ("cr", "1,1"))); rules.apply_action(s, PlaceAction(ASSASSIN, ("cr", "1,3")))
    assert len(s.hands["A"]) == 0


def test_the_mage_draws_his_fatigue_feeds_him_and_his_card_transforms_once_the_deck_is_empty():
    s = state(turn=10, leaders={"A": SAGE})                            # 6 mana
    rules.apply_action(s, LeaderAction())
    assert len(s.hands["A"]) == 1 and rules.mana_left(s, "A") == 3 and LeaderAction() not in rules.legal_actions(s)
    s = state(turn=10, leaders={"A": SAGE}, decks={"A": [], "B": ["wisp_1"]}, food={"A": 15, "B": 15})
    rules.apply_action(s, LeaderAction())                              # fatigue: food gained, not lost
    assert s.food["A"] == 16 and s.fatigue["A"] == 1
    s = state(turn=19, hands={"A": [SAGE]}, decks={"A": ["wisp_1"], "B": ["wisp_1"] * 3}, leaders={"A": RENO}, food={"A": 12, "B": 15})
    put(s, "1,1", SAGE, "A")
    assert s.hands["A"][0].card_id == SAGE
    rules.apply_action(s, LeaderAction())                              # the last card: Reno Scouts it, the deck is empty
    if s.pending:
        rules.apply_action(s, ChoiceAction(s.pending["options"][0]))
    assert s.decks["A"] == [] and s.hands["A"][0].card_id == "mage_transformed" and s.board["1,1"][-1].card_id == "mage_transformed"
    assert s.food["A"] == 12                                           # on the board it transforms without a Roar
    s = state(turn=19, hands={"A": ["mage_transformed"]}, food={"A": 12, "B": 15})
    rules.apply_action(s, PlaceAction("mage_transformed", ("cr", "1,3")))   # "Roar: double your food."
    assert s.food["A"] == 24


def test_reno_scouts_his_draws_while_his_deck_holds_no_duplicates():
    s = state(turn=10, leaders={"A": RENO}, decks={"A": ["wisp_1", "wisp_2", "wisp_3", "wisp_4"], "B": ["wisp_1"] * 3})
    rules.apply_action(s, LeaderAction())                              # "Draw a card.": a Scout
    assert s.pending["options"] == ["deck:0", "deck:1", "deck:2"]
    third = s.decks["A"][-3]
    rules.apply_action(s, ChoiceAction("deck:2"))
    assert [u.card_id for u in s.hands["A"]] == [third] and len(s.decks["A"]) == 3
    rules.apply_action(s, PassAction())
    rules.apply_action(s, PassAction())                                # his turn's free card: a Scout too
    assert s.pending and s.pending["chooser"] == "A" and len(s.pending["options"]) == 3
    t = GameState.from_dict(s.to_dict())                               # waiting on the stack, saved
    assert t.pending == s.pending
    s = state(turn=10, leaders={"A": RENO}, decks={"A": ["wisp_1", "wisp_1", "wisp_3"], "B": ["wisp_1"] * 3})
    rules.apply_action(s, LeaderAction())                              # a duplicate: a plain draw
    assert s.pending is None and [u.card_id for u in s.hands["A"]] == ["wisp_3"]
    s = state(turn=19, hands={"A": [RENO]}, decks={"A": ["wisp_1", "wisp_1", "wisp_2", "wisp_3", "wisp_4"], "B": ["wisp_1"] * 3})
    rules.apply_action(s, PlaceAction(RENO, ("cr", "1,1")))           # "Roar: Scout 2 cards."
    for _ in range(CFG.reno_scouts):
        rules.apply_action(s, ChoiceAction("deck:0"))
    assert len(s.hands["A"]) == 2 and s.pending is None


def test_the_pyromancers_power_upgrades_after_three_uses_and_his_card_upgrades_the_fireballs_in_hand():
    s = state(turn=19, leaders={"A": PYROMANCER}, decks={"A": ["wisp_1"] * 20, "B": ["wisp_1"] * 20}, food={"A": 15, "B": 15})
    got, gives = [], ["flight_1"] * 3 + ["flight_3"] * 3 + ["flight_6"]
    for i in range(7):
        assert rules.power_text(s, "A") == f"Add a {CARDS[gives[i]].name} to your hand."
        rules.apply_action(s, LeaderAction())
        got.append(s.hands["A"][-1].card_id)
        rules.apply_action(s, PassAction()); rules.apply_action(s, PassAction())
        s.hands["A"].clear()
    assert got == gives and s.power_uses["A"] == 7
    s = state(turn=19, hands={"A": [PYROMANCER, "flight_1", "flight_6", "flight_10", "wisp_1"]})
    rules.apply_action(s, PlaceAction(PYROMANCER, ("cr", "1,1")))
    assert sorted((u.card_id, rules.unit_cost(s, u)) for u in s.hands["A"]) == [
        ("flight_10", 6), ("flight_10", 10), ("flight_3", 1), ("wisp_1", CARDS["wisp_1"].cost)]   # Baby to Young, Adult to Elder; each its cost
    assert sorted(rules.unit_cost(s, u) for u in s.hands["A"] if u.card_id == "flight_10") == [6, 10]   # an Elder stays one


def test_gorraks_hungry_allies_cost_one_more_and_have_three_more_strength_and_his_delicious_food():
    b = CFG.warlord_hungry_bonus
    for leader, bonus, tax in ((WARLORD, b, CFG.warlord_hungry_tax), (SAGE, 0, 0)):
        s = state(turn=11, hands={"A": ["hungry_3"]}, leaders={"A": leader}, food={"A": 15, "B": 15})
        put(s, "1,1", "wisp_1", "A")
        put(s, "2,1", "wisp_3", "B")                                  # 6: only a Hungry 3 with the bonus eats it
        put(s, "1,2", "hungry_1", "A")
        assert effective_strength(s, s.board["1,2"][-1]) == CARDS["hungry_1"].base_strength + bonus   # on the board
        assert places(s, "hungry_3") == ({"2,1"} if bonus else set())                                 # from hand
        assert mana_cost(s, "hungry_3") == CARDS["hungry_3"].cost + tax
    s = state(turn=11, leaders={"A": WARLORD}, food={"A": 15, "B": 15})
    rules.apply_action(s, LeaderAction())                              # Delicious Food, his, on a random empty crossroad
    (cr, stack), = s.board.items()
    assert stack[-1].card_id == "delicious_food" and stack[-1].owner == "A" and rules.mana_left(s, "A") == 6 - CFG.warlord_power_cost
    put(s, "5,3", "wisp_1", "B")
    s.board[cr][-1].strength_mod = -1                                  # down to 0: removed, "Fall: gain 1 food."
    rules.apply_action(s, PassAction())
    assert cr not in s.board and s.food["A"] == 15 + CFG.delicious_food_food


def test_the_mana_eater_starts_with_no_cards_and_three_crystals_banks_mana_and_eats_his_crystals():
    deck = DECK[:-1] + [MANA_EATER]
    s = new_game(deck, DECK, 3, leaders={"A": MANA_EATER, "B": WARLORD}, first_player="A")
    assert s.pending and s.pending["chooser"] == "B"                   # no hand for A, so no mulligan of his
    rules.apply_action(s, ChoiceAction(SKIP))
    assert len(s.hands["A"]) == 1 and rules.mana_left(s, "A") == 4     # the turn's card; 3 crystals and his first
    assert rules.mana_left(s, "B") == 1
    s = state(turn=18, leaders={"A": MANA_EATER})                      # his 10th turn's mana is 10 crystals
    s.crystals = {"A": 10, "B": 9}
    rules.apply_action(s, LeaderAction())
    rules.apply_action(s, PassAction())
    assert rules.mana_left(s, "A") == 10 + CFG.mana_eater_power_mana   # next turn: past 10
    rules.apply_action(s, PassAction())
    assert rules.mana_left(s, "A") == 12 and s.crystals["A"] == 10
    s = state(turn=19, hands={"A": [MANA_EATER]}, leaders={"A": MANA_EATER}, food={"A": 10, "B": 15})
    assert CARDS[MANA_EATER].keywords == {"Hungry"} and places(s, MANA_EATER) == set()
    put(s, "1,1", "wisp_1", "B")                                       # Hungry: he lands on an enemy he beats
    rules.apply_action(s, PlaceAction(MANA_EATER, ("cr", "1,1")))      # 10 crystals destroyed: 10 food, and his prey's
    assert s.crystals["A"] == 0 and s.food["A"] == 20 + CFG.hungry_food and rules.mana_left(s, "A") == 0
    rules.apply_action(s, PassAction()); rules.apply_action(s, PassAction())
    assert rules.mana_left(s, "A") == 1                                # and they grow back from one
    assert GameState.from_dict(s.to_dict()).crystals == s.crystals


def test_deck_rules():
    assert deck_problems(DECK, "warlord_legend") == []
    assert deck_problems(DECK, None) == ["a deck needs a leader"]
    assert deck_problems(DECK[:-1], "warlord_legend")
    assert any("at most 2" in p for p in deck_problems(DECK[:-2] + ["wisp_1", "warlord_legend"], "warlord_legend"))
    assert any("collectible" in p for p in deck_problems(DECK[:-2] + ["test_reserve", "warlord_legend"], "warlord_legend", cards=CARDS))


def test_the_first_player_draws_on_their_first_turn_too():
    s = new_game(DECK, DECK, 7, leaders={"A": "warlord_legend", "B": "warlord_legend"})
    while s.pending is not None:
        rules.apply_action(s, ChoiceAction(SKIP))                      # both keep their hands
    first = s.current
    assert len(s.hands[first]) == CFG.first_player_opening_draw + CFG.turn_draw_count


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
    from animal_kingdom.bot import GreedyBot
    wins = 0
    for seed in range(10):
        rng, bot = random.Random(seed), GreedyBot(seed)
        s = new_game(DECK, DECK, seed, leaders={"A": "warlord_legend", "B": "warlord_legend"})
        while not rules.is_terminal(s):
            legal = rules.legal_actions(s)
            p = s.player_to_act()
            rules.apply_action(s, bot.choose(s) if p == "A" else rng.choice(legal))
        wins += s.result.winner == "A"
    assert wins >= 8


def test_the_practice_bot_plans_its_turn_and_beats_the_greedy_bot():
    """The Practice opponent is the engine's whole-turn search: it ends a turn holding a play when that is better, which
    the greedy bot cannot, and it wins most games against it from both seats."""
    from animal_kingdom.bot import GreedyBot, SearchBot
    from animal_kingdom.web.match import PRACTICE_BOT
    wins, games, held = 0, 0, 0
    for seed in range(5):
        for seat in "AB":
            bots = {seat: SearchBot(PRACTICE_BOT, seed), rules.other_player(seat): GreedyBot(seed)}
            s = new_game(DECK, DECK, seed, leaders={"A": "warlord_legend", "B": "warlord_legend"})
            while not rules.is_terminal(s):
                p = s.player_to_act()
                a = bots[p].choose(s)
                if p == seat and isinstance(a, PassAction) and rules.legal_actions(s) != [PassAction()]:
                    held += 1
                rules.apply_action(s, a)
            wins += s.result.winner == seat
            games += 1
            assert bots[seat].failures == 0
    assert wins >= 7 and held > 0, (wins, games, held)


def test_a_search_bot_that_fails_plays_the_greedy_bots_move():
    from animal_kingdom.bot import SearchBot
    s = new_game(DECK, DECK, 5, leaders={"A": "warlord_legend", "B": "warlord_legend"})
    unknown = SearchBot("no-such-bot", 5)                              # a spec the engine does not know
    assert unknown.choose(s) in rules.legal_actions(s)

    class Broken:
        def choose(self, state):
            raise RuntimeError("the engine panicked: test")
    bot = SearchBot("turn:budget=2000", 5)
    bot._bot = Broken()
    assert bot.choose(s) in rules.legal_actions(s) and bot.failures == 1


def test_the_mana_blob_gains_2_mana_past_the_cap_too():
    s = state(turn=2, hands={"A": ["mana_blob", "wisp_1"]})            # A's 2nd turn: 2 mana
    rules.apply_action(s, PlaceAction("mana_blob", ("cr", "1,1")))
    assert rules.mana_left(s, "A") == CFG.mana_blob_mana               # paid 2, gained 2
    s = state(turn=19, hands={"A": ["mana_blob"]})
    rules.apply_action(s, PlaceAction("mana_blob", ("cr", "1,1")))
    assert rules.mana_left(s, "A") == 10 - 2 + CFG.mana_blob_mana and CARDS["mana_blob"].cost == 2 == CARDS["mana_blob"].base_strength


# ------------------------------------------------------------------ fatigue (Martin, 2026-11-22)

def test_the_turns_card_from_an_empty_deck_costs_food_instead_one_more_each_time():
    s = state(turn=10, decks={"A": [], "B": []}, food={"A": 15, "B": 15})
    rules.apply_action(s, PassAction())                               # B's turn starts: no card to draw
    assert s.food == {"A": 15, "B": 14} and s.fatigue == {"A": 0, "B": 1} and not s.hands["B"]
    rules.apply_action(s, PassAction())                               # A's
    assert s.food == {"A": 14, "B": 14} and s.fatigue == {"A": 1, "B": 1}
    rules.apply_action(s, PassAction())                               # B's second empty draw costs 2
    assert s.food == {"A": 14, "B": 12} and s.fatigue == {"A": 1, "B": 2}
    assert GameState.from_dict(s.to_dict()).fatigue == s.fatigue      # the count is part of the position


def test_a_cards_draw_from_an_empty_deck_costs_food_too():
    s = state(turn=10, hands={"A": ["cantrip_2"]}, decks={"A": [], "B": ["wisp_1"]}, food={"A": 15, "B": 15})
    rules.apply_action(s, PlaceAction("cantrip_2", ("cr", "1,2")))
    assert s.food["A"] == 14 and s.fatigue["A"] == 1 and not s.hands["A"]
    s = state(turn=10, leaders={"A": RENO}, decks={"A": [], "B": ["wisp_1"]}, food={"A": 15, "B": 15})
    rules.apply_action(s, LeaderAction())                             # Reno's power draws: no card to Scout, so fatigue
    assert s.food["A"] == 14 and s.fatigue["A"] == 1


def test_a_draw_of_two_with_one_card_left_draws_it_and_pays_for_the_other():
    s = state(turn=10, decks={"A": [], "B": ["wisp_1"]}, food={"A": 15, "B": 15}, config=Config(turn_draw_count=2))
    rules.apply_action(s, PassAction())                               # B's turn: two cards, one in the deck
    assert [u.card_id for u in s.hands["B"]] == ["wisp_1"] and s.food["B"] == 14 and s.fatigue["B"] == 1
    rules.apply_action(s, PassAction()); rules.apply_action(s, PassAction())   # B again: both draws empty, 2 then 3
    assert s.food["B"] == 14 - 2 - 3 and s.fatigue["B"] == 3


def test_fatigue_at_no_food_loses_at_once_on_your_own_turn_too():
    s = state(turn=10, hands={"A": ["cantrip_2"]}, decks={"A": [], "B": ["wisp_1"]}, food={"A": 1, "B": 15})
    rules.apply_action(s, PlaceAction("cantrip_2", ("cr", "1,2")))
    assert s.food["A"] == 0 and s.result.winner == "B" and s.result.reason == "starved" and rules.legal_actions(s) == []
    s = state(turn=10, decks={"A": ["wisp_1"], "B": []}, food={"A": 15, "B": 1})
    rules.apply_action(s, PassAction())                               # B's turn starts on an empty deck with 1 food
    assert s.food["B"] == 0 and s.result.winner == "A" and s.result.reason == "starved"


def test_fatigue_is_not_income_and_not_a_raid_and_only_a_draw_brings_it():
    s = state(turn=10, hands={"A": ["scout_3", "mama_spore"]}, decks={"A": [], "B": ["wisp_1"]}, food={"A": 15, "B": 15},
              leaders={"A": WARLORD, "B": RAIDER})
    rules.apply_action(s, PlaceAction("scout_3", ("cr", "1,1")))      # Scout on an empty deck: nothing happens
    rules.apply_action(s, PlaceAction("mama_spore", ("cr", "1,2")))   # cards an effect puts into the hand are not draws
    assert s.food["A"] == 15 and s.fatigue == {"A": 0, "B": 0} and len(s.hands["A"]) == CFG.mama_spores
    rs = s._sync()
    rs.record_events(True)
    rs.apply_action(PassAction().to_dict()); rs.apply_action(PassAction().to_dict())    # B's turn, then A's: A's empty draw
    lost = [e for e in rs.take_events() if e["e"] == "food" and e["n"] < 0]
    assert lost == [{"e": "food", "player": "A", "n": -1, "fatigue": 1}]                # the food-change event, negative
    assert rs.to_dict()["food"] == {"A": 14, "B": 15}                                   # the Raider's 1 more is a raid's


def test_a_leaders_passive_says_when_it_fires():
    # the Rogue: as her third card, the cheaper one, is played, a raid's included
    s = state(turn=19, hands={"A": ["wisp_1", "wisp_1", "flight_1"]}, leaders={"A": ASSASSIN}, decks={"A": ["wisp_1"] * 5}, food={"A": 15, "B": 15})
    rules.apply_action(s, PlaceAction("wisp_1", ("cr", "1,1"))); rules.apply_action(s, PlaceAction("wisp_1", ("cr", "1,2")))
    assert not [e for e in s.events if e["e"] == "leader_trigger"]
    n = len(s.events)
    rules.apply_action(s, PlaceAction("flight_1", ("hq", "B")))
    assert "leader_trigger" in [e["e"] for e in s.events[n:]]
    # the Elf: at the end of a turn its regions produce in, before the food
    s = state(turn=10, leaders={"A": ELF})
    for cr in ("1,1", "1,2", "2,2"):
        put(s, cr, "wisp_1", "A")
    n = len(s.events)
    rules.apply_action(s, PassAction())
    kinds = [e["e"] for e in s.events[n:]]
    assert kinds.index("leader_trigger") < kinds.index("food")


def test_a_golden_egg_taken_by_scout_is_drawn_and_draws_a_card():
    s = state(turn=11, hands={"A": ["scout_3"]}, decks={"A": ["wisp_1", "golden_egg", "wisp_4"]})
    rules.apply_action(s, PlaceAction("scout_3", ("cr", "1,1")))
    assert s.pending["options"] == ["deck:0", "deck:1", "deck:2"]
    rules.apply_action(s, ChoiceAction(f"deck:{2 - s.decks['A'].index('golden_egg')}"))   # the Golden Egg
    hand = sorted(u.card_id for u in s.hands["A"])
    assert len(hand) == 2 and "golden_egg" in hand and len(s.decks["A"]) == 1


def test_scorch_eats_burns_its_neighbours_and_its_regions_produce_no_food_for_the_rest_of_the_game():
    assert CARDS["scorch"].keywords == {"Flight", "Hungry"} and (CARDS["scorch"].cost, CARDS["scorch"].base_strength) == (4, 5)
    reg = next(iter(BOARD.regions.values()))
    a, b, c = reg.corners
    s = state(turn=11, hands={"A": ["scorch"]}, food={"A": 15, "B": 15})
    put(s, a, "wisp_1", "A"); put(s, b, "wisp_1", "A"); put(s, c, "wisp_1", "B")   # an enemy of 2 on its last tile
    assert places(s, "scorch") == {c}                                  # Flight and Hungry: only onto an enemy it beats
    rules.apply_action(s, PlaceAction("scorch", ("cr", c)))
    assert s.board[c][-1].card_id == "scorch" and reg.id in s.scorched
    others = [r for r in BOARD.regions.values() if c in r.corners]
    assert sorted(s.scorched) == sorted(r.id for r in others)          # every region its tile is part of
    assert rules.region_income(s, "A") == 0                            # held, and it pays nothing
    t = GameState.from_dict(s.to_dict())
    assert sorted(t.scorched) == sorted(s.scorched) and rules.region_income(t, "A") == 0
    s = state(turn=11, hands={"A": ["scorch"]}, food={"A": 15, "B": 15})
    put(s, a, "wisp_1", "A"); put(s, c, "wisp_1", "B")
    around = [n for n in BOARD.neighbors(c) if n != a]
    put(s, around[0], "wisp_2", "B"); put(s, around[1], "test_one", "B")   # 4 and 1: down to 3, and to 0 (gone)
    rules.apply_action(s, PlaceAction("scorch", ("cr", c)))
    assert effective_strength(s, s.board[around[0]][-1]) == CARDS["wisp_2"].base_strength - 1 and around[1] not in s.board
    assert effective_strength(s, s.board[a][-1]) == CARDS["wisp_1"].base_strength - 1   # its own side burns too


def test_the_rogues_count_shows_on_her_leader():
    from animal_kingdom.web.match import leader_view
    s = state(turn=19, hands={"A": ["wisp_1"] * 2}, leaders={"A": ASSASSIN, "B": RAIDER})
    assert leader_view(s, "A")["count"] == {"n": 0, "of": CFG.rogue_nth_card}
    rules.apply_action(s, PlaceAction("wisp_1", ("cr", "1,1")))
    assert leader_view(s, "A")["count"]["n"] == 1
    assert "count" not in leader_view(s, "B")


def test_the_plunderer_draws_a_card_for_each_raid_while_it_stands():
    assert (CARDS["plunderer"].cost, CARDS["plunderer"].base_strength) == (3, 3)
    s = state(turn=19, hands={"A": ["flight_1", "flight_1"]}, decks={"A": ["wisp_1"] * 5}, food={"A": 15, "B": 15})
    rules.apply_action(s, PlaceAction("flight_1", ("hq", "B")))
    assert len(s.hands["A"]) == 1                                     # no Plunderer: no draw
    put(s, "1,1", "plunderer", "A"); put(s, "1,2", "plunderer", "A")
    rules.apply_action(s, PlaceAction("flight_1", ("hq", "B")))
    assert len(s.hands["A"]) == 2                                     # one card for each Plunderer
    put(s, "1,1", "wisp_5", "B"); put(s, "1,2", "wisp_5", "B")        # covered: gone from the board's tops
    s.hands["A"].append(UnitInstance("flight_1", "A", s.new_iid()))
    n = len(s.hands["A"])
    rules.apply_action(s, PlaceAction("flight_1", ("hq", "B")))
    assert len(s.hands["A"]) == n - 1
