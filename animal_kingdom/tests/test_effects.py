"""M2a golden tests: one focused scenario per slice card / mechanism.

Slice: Squirrel/Chipmunk (gain_food), Gray Wolf (choice removal), Wild Dogs (play_extra
chain), Pufferfish (on_covered trap + decision-8 ordering), Egg (delayed + Fragile),
Hibernating Bear (delayed payout), Golden Eagle (Flight), Honey Badger (cover-rule),
Nile Crocodile (dynamic strength), Vulture (once/turn reactive draw).
"""

from __future__ import annotations

from animal_kingdom.engine import effects, rules
from animal_kingdom.engine.actions import ChoiceAction, PlaceAction, DrawAction
from animal_kingdom.engine.cards import load_cards
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.maps import load_map
from animal_kingdom.engine.state import GameState, UnitInstance
from animal_kingdom.engine.strength import card_strength

CFG = Config.default()


def make_state(*, current="A", hands=None, decks=None, food=None) -> GameState:
    return GameState(
        load_map("map_a"), load_cards(), Config.default(),
        board={}, hands=hands or {"A": [], "B": []}, decks=decks or {"A": [], "B": []},
        discard=[], food=food or {"A": 0, "B": 0}, current=current, first_player="A",
    )


def put(state: GameState, cr: str, card_id: str, owner: str) -> None:
    state.board.setdefault(cr, []).append(
        UnitInstance(card_id, owner, state.new_iid(), placed_on_turn=state.turn_counter))


def play_draws_until(state: GameState, target_tc: int) -> None:
    """Advance by drawing each turn until turn_counter reaches target_tc (or terminal)."""
    while state.turn_counter < target_tc and rules.is_terminal(state) is None:
        rules.apply_action(state, DrawAction())


# ------------------------------------------------------------------- battlecries

def test_squirrel_gains_food_on_place():
    s = make_state(hands={"A": ["squirrel"], "B": []})
    rules.apply_action(s, PlaceAction("squirrel", ("cr", "1,2")))
    assert s.food["A"] == CFG.f_high  # 8


def test_gray_wolf_removes_a_chosen_adjacent_enemy():
    s = make_state(hands={"A": ["gray_wolf"], "B": []})
    put(s, "1,2", "baboon", "A")        # connects (2,2)
    put(s, "3,2", "rat", "B")           # str 1, adjacent to (2,2)
    put(s, "2,1", "army_ant", "B")      # str 1, adjacent to (2,2)
    rules.apply_action(s, PlaceAction("gray_wolf", ("cr", "2,2")))
    assert s.pending is not None        # two legal targets ⇒ a choice
    rules.apply_action(s, ChoiceAction("3,2"))
    assert s.owner_of("3,2") is None    # removed
    assert s.owner_of("2,1") == "B"     # the other survives


def test_wild_dogs_plays_an_extra_unit():
    s = make_state(hands={"A": ["wild_dogs", "lion"], "B": []})
    rules.apply_action(s, PlaceAction("wild_dogs", ("cr", "1,2")))
    assert s.pending is not None and s.pending["mode"] == "place"
    rules.apply_action(s, PlaceAction("lion", ("cr", "1,1")))
    assert s.owner_of("1,2") == "A" and s.owner_of("1,1") == "A"
    assert s.hands["A"] == []           # both played in one turn


# --------------------------------------------------- decision-8 ordering (trap)

def test_pufferfish_battlecry_resolves_before_trap():
    s = make_state(current="A", hands={"A": ["chipmunk"], "B": []})
    put(s, "1,2", "baboon", "A")        # connects (2,2)
    put(s, "2,2", "pufferfish", "B")    # str 2 enemy trap
    rules.apply_action(s, PlaceAction("chipmunk", ("cr", "2,2")))  # str 3 covers it
    assert s.food["A"] == CFG.f_med     # Chipmunk got paid (battlecry first)...
    assert s.owner_of("2,2") is None    # ...then both it and the Pufferfish are removed
    assert s.discard.count("chipmunk") == 1 and s.discard.count("pufferfish") == 1


# ---------------------------------------------------------------- delayed effects

def test_egg_hatches_after_delay_and_draws():
    s = make_state(current="A", hands={"A": ["egg"], "B": []},
                   decks={"A": ["lion", "baboon", "owl", "rat", "coyote"], "B": ["lynx"] * 5})
    rules.apply_action(s, PlaceAction("egg", ("cr", "1,2")))   # schedules hatch at tc 4
    assert s.owner_of("1,2") == "A" and len(s.scheduled) == 1
    play_draws_until(s, 4)              # advance to A's turn where it hatches
    assert s.owner_of("1,2") is None   # egg removed on hatch
    assert "egg" in s.discard
    assert "egg" not in [st["step"]["op"] for st in s.scheduled]  # schedule consumed


def test_egg_is_fragile_removed_when_covered():
    s = make_state(current="B", hands={"B": ["lion"], "A": []})
    put(s, "2,2", "egg", "A")           # A's egg
    put(s, "4,2", "baboon", "B")        # B front
    put(s, "3,2", "baboon", "B")        # B chain to (2,2)
    rules.apply_action(s, PlaceAction("lion", ("cr", "2,2")))  # B covers the egg
    assert s.owner_of("2,2") == "B"     # lion stands here
    assert "egg" in s.discard           # Fragile: egg removed, not buried


def test_hibernating_bear_pays_out_doubled_after_delay():
    s = make_state(current="A", hands={"A": ["hibernating_bear"], "B": []},
                   decks={"A": ["lion"] * 6, "B": ["lynx"] * 6}, food={"A": 30, "B": 0})
    rules.apply_action(s, PlaceAction("hibernating_bear", ("cr", "1,2")))
    assert s.food["A"] == 0             # lost all stored food immediately
    play_draws_until(s, 4)             # two of A's turns later
    assert s.food["A"] == 30 * CFG.hibernating_bear_multiplier  # 60


# ----------------------------------------------------------------- static modifiers

def test_golden_eagle_flight_ignores_connection():
    s = make_state(hands={"A": ["golden_eagle"], "B": []})
    targets = {a.target[1] for a in rules.legal_actions(s)
               if isinstance(a, PlaceAction) and a.target[0] == "cr"}
    assert "3,2" in targets and "4,1" in targets  # deep crossroads, no connection needed


def test_honey_badger_covers_equal_strength():
    s = make_state(hands={"A": ["honey_badger", "owl"], "B": []})
    put(s, "1,2", "baboon", "A")        # connects (2,2)
    put(s, "2,2", "coyote", "B")        # str 3 enemy
    legal = rules.legal_actions(s)
    assert PlaceAction("honey_badger", ("cr", "2,2")) in legal      # 3 ≥ 3 ✓
    assert PlaceAction("owl", ("cr", "2,2")) not in legal           # plain 3 > 3 ✗


def test_nile_crocodile_strength_tracks_units_controlled():
    s = make_state(hands={"A": ["nile_crocodile"], "B": []})
    put(s, "1,2", "baboon", "A")
    put(s, "1,1", "rat", "A")
    assert card_strength(s, "nile_crocodile", "A") == 2
    put(s, "2,2", "army_ant", "B")      # enemy str 1
    assert PlaceAction("nile_crocodile", ("cr", "2,2")) in rules.legal_actions(s)  # 2 > 1
    put(s, "1,3", "baboon", "A")
    assert card_strength(s, "nile_crocodile", "A") == 3


# ------------------------------------------------------------ once/turn reactive

def test_vulture_draws_once_per_turn_on_enemy_removal():
    s = make_state(current="A", decks={"A": ["lion", "baboon", "owl"], "B": []})
    put(s, "1,1", "vulture", "A")       # A controls a Vulture
    put(s, "2,2", "rat", "B")           # two enemy units to remove
    put(s, "3,3", "army_ant", "B")
    effects._remove_specific(s, "2,2", s.top_unit("2,2"), by_player="A")
    assert len(s.hands["A"]) == 1       # Vulture drew once
    effects._remove_specific(s, "3,3", s.top_unit("3,3"), by_player="A")
    assert len(s.hands["A"]) == 1       # second enemy removal: no extra draw this turn
    s.turn_flags = {}                   # new turn resets the flag
    put(s, "2,3", "rat", "B")
    effects._remove_specific(s, "2,3", s.top_unit("2,3"), by_player="A")
    assert len(s.hands["A"]) == 2       # draws again next turn
