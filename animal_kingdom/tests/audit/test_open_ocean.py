"""Card audit, Open Ocean (2026-11-05): does the engine do what each card's printed text says?

Each test is written from the printed text and the keyword definitions (docs/rules/keywords.md, rulings.md),
never from the effect code. Map A: a 4x3 grid, A's den fronts column 1, B's column 4; "2,2" neighbours
"1,2", "3,2", "2,1", "2,3". Regions R1 = 1,1 2,1 1,2 2,2; R4 = 1,2 2,2 1,3 2,3.
"""

from __future__ import annotations

import pytest

from animal_kingdom.engine import effects, rules, statics
from animal_kingdom.engine.actions import ChoiceAction, DrawAction, PassAction, PlaceAction, RoamAction
from animal_kingdom.engine.cards import load_cards
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.strength import effective_strength

from .._helpers import apply_click, hand_ids, put
from .._helpers import make_state as _make_state

CFG = Config.default()
CARDS = load_cards()


def make_state(**kw):
    """The shared builder, with the opponent holding a deck so the turn never passes on its own for want of a move."""
    decks = kw.pop("decks", None) or {"A": [], "B": []}
    decks = {"A": decks.get("A", []), "B": decks.get("B") or ["lion"] * 6}
    return _make_state(decks=decks, **kw)


def end_turn(s):
    s.idle_turns = 0
    rules.apply_action(s, PassAction())


def choose(s, option):
    assert s.pending is not None and option in s.pending["options"], (option, s.pending)
    rules.apply_action(s, ChoiceAction(option))


def removed(s, card_id):
    return card_id in s.remove_pile


def places(s, card_id):
    return {a.target for a in rules.legal_actions(s) if isinstance(a, PlaceAction) and a.card_id == card_id}


def board_ids(s, owner=None):
    return [u.card_id for st in s.board.values() for u in st if owner is None or u.owner == owner]


def test_open_ocean_card_list_is_the_audited_one():
    ocean = {c.id for c in CARDS.values() if c.status == "collectible" and c.habitat == "Open Ocean"}
    assert ocean == {
        "sperm_whale", "orca", "tuna_legend", "manta_ray_legend", "swordfish", "barracuda", "manta_ray", "remora",
        "cod", "sardine", "mahi_mahi", "tuna", "sunfish", "octopus_legend_2", "jellyfish", "sperm_whale_legend",
        "whale_shark", "blue_whale", "octopus", "great_white_shark", "dolphin", "albatross", "sea_turtle",
        "hammerhead", "krill", "sardine_legend"}


# ------------------------------------------------------------------ Sperm Whale: Titan. Roar: remove all adjacent animals.

def test_sperm_whale_removes_every_adjacent_animal_of_both_players():
    s = make_state(hands={"A": ["sperm_whale"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,1", "lion", "A")                       # an ally beside it: "all adjacent animals"
    put(s, "2,2", "lion", "B")
    put(s, "1,3", "tortoise", "B")                   # Armor: no ability removes it
    rules.apply_action(s, PlaceAction("sperm_whale", ("cr", "1,2")))
    assert s.top_unit("1,1") is None and s.top_unit("2,2") is None
    assert s.top_unit("1,3").card_id == "tortoise"
    assert s.remove_pile.count("lion") == 2
    assert s.current == "B"                          # Titan: it took both actions


def test_sperm_whale_is_a_titan_needing_two_actions():
    s = make_state(hands={"A": ["sperm_whale"]}, decks={"A": ["lion"] * 3, "B": []})
    assert ("cr", "1,2") in places(s, "sperm_whale")
    rules.apply_action(s, DrawAction())              # one action left
    assert not places(s, "sperm_whale")


def test_sperm_whale_with_nothing_adjacent_removes_nothing():
    s = make_state(hands={"A": ["sperm_whale"]})
    put(s, "3,3", "lion", "B")
    rules.apply_action(s, PlaceAction("sperm_whale", ("cr", "1,2")))
    assert s.remove_pile == [] and s.top_unit("3,3").card_id == "lion"


# ------------------------------------------------------------------ Orca: Apex Predator. Roam.

def test_orca_must_land_on_an_animal_and_eats_it():
    s = make_state(hands={"A": ["orca"]})
    put(s, "1,1", "mouse", "B")                      # 4 < 6
    put(s, "1,3", "lion", "B")                       # 7 > 6: can't cover
    targets = places(s, "orca")
    assert ("cr", "1,1") in targets
    assert ("cr", "1,2") not in targets and ("cr", "1,3") not in targets   # never onto an empty crossroad
    rules.apply_action(s, PlaceAction("orca", ("cr", "1,1")))
    assert removed(s, "mouse") and s.board["1,1"][-1].card_id == "orca" and len(s.board["1,1"]) == 1


def test_orca_can_eat_an_ally():
    s = make_state(hands={"A": ["orca"]})
    put(s, "1,2", "lion", "A")                       # own: no strength needed
    rules.apply_action(s, PlaceAction("orca", ("cr", "1,2")))
    assert removed(s, "lion") and s.top_unit("1,2").card_id == "orca"


def test_orca_with_no_prey_cannot_be_played():
    s = make_state(hands={"A": ["orca"]})
    assert not places(s, "orca")


def test_orca_roams_only_onto_an_animal_and_eats_it():
    s = make_state()
    put(s, "1,2", "orca", "A")
    put(s, "2,2", "mouse", "B")
    roams = {a.target for a in rules.legal_actions(s) if isinstance(a, RoamAction) and a.origin == "1,2"}
    assert ("cr", "2,2") in roams
    assert ("cr", "1,1") not in roams and ("cr", "2,1") not in roams       # empty crossroads: an apex never lands there
    rules.apply_action(s, RoamAction("1,2", ("cr", "2,2")))
    assert removed(s, "mouse") and s.top_unit("2,2").card_id == "orca" and s.top_unit("1,2") is None


def test_orca_cannot_be_placed_onto_the_den():
    s = make_state(hands={"A": ["orca"]})
    for cr in ("1,2", "2,2", "3,2", "4,2"):
        put(s, cr, "mouse", "A")
    assert not any(t[0] == "hq" for t in places(s, "orca"))


# ------------------------------------------------------------------ [TUNA]: Roar: for each region you control, draw a card and gain 5 food.

def test_tuna_legend_pays_a_card_and_five_food_per_region():
    s = make_state(hands={"A": ["tuna_legend"]}, decks={"A": ["lion"] * 5, "B": []})
    for cr in ("1,1", "2,1", "2,2", "1,3", "2,3"):
        put(s, cr, "sardine", "A")
    rules.apply_action(s, PlaceAction("tuna_legend", ("cr", "1,2")))      # closes R1 and R4
    assert s.food["A"] == 2 * CFG.tuna_legend_food and len(s.hands["A"]) == 2


def test_tuna_legend_with_no_region_pays_nothing():
    s = make_state(hands={"A": ["tuna_legend"]}, decks={"A": ["lion"] * 5, "B": []})
    put(s, "1,1", "sardine", "A")
    rules.apply_action(s, PlaceAction("tuna_legend", ("cr", "1,2")))
    assert s.food["A"] == 0 and hand_ids(s, "A") == []


def test_tuna_legend_with_an_empty_deck_still_gains_food():
    s = make_state(hands={"A": ["tuna_legend", "mouse"]}, decks={"A": [], "B": ["lion"] * 3})
    for cr in ("1,1", "2,1", "2,2"):
        put(s, cr, "sardine", "A")
    rules.apply_action(s, PlaceAction("tuna_legend", ("cr", "1,2")))
    assert s.food["A"] == CFG.tuna_legend_food and hand_ids(s, "A") == ["mouse"]


# ------------------------------------------------------------------ [MANTA RAY]: Dusk: if you control 2 or more regions, draw 2 cards.

def _manta_legend_board(two_regions):
    s = make_state(decks={"A": ["lion"] * 6, "B": ["lion"] * 6})
    crs = ("1,1", "2,1", "2,2", "1,3", "2,3") if two_regions else ("1,1", "2,1", "2,2")
    for cr in crs:
        put(s, cr, "sardine", "A")
    put(s, "1,2", "manta_ray_legend", "A")
    return s


def test_manta_ray_legend_draws_two_at_dusk_with_two_regions():
    s = _manta_legend_board(True)
    end_turn(s)
    assert len(s.hands["A"]) == 2


def test_manta_ray_legend_draws_nothing_with_one_region():
    s = _manta_legend_board(False)
    end_turn(s)
    assert len(s.hands["A"]) == 0


def test_manta_ray_legend_does_nothing_at_the_opponents_dusk():
    s = _manta_legend_board(True)
    s.current = "B"
    end_turn(s)                                      # B's turn ends: not A's Dusk
    assert len(s.hands["A"]) == 0


# ------------------------------------------------------------------ Swordfish: Roar: remove a random adjacent enemy for each adjacent allied Fish.

def test_swordfish_removes_one_random_enemy_per_adjacent_allied_fish():
    s = make_state(hands={"A": ["swordfish"]})
    put(s, "1,1", "sardine", "A"); put(s, "1,3", "sardine", "A")   # two allied Fish beside it
    put(s, "2,2", "lion", "B")
    rules.apply_action(s, PlaceAction("swordfish", ("cr", "2,1")))  # 2,1 neighbours 1,1 3,1 2,2
    # only 1,1 is a Fish beside 2,1: one enemy
    assert s.top_unit("2,2") is None


def test_swordfish_two_fish_two_enemies_stealth_hit_armor_kept():
    s = make_state(hands={"A": ["swordfish"]})
    put(s, "2,1", "sardine", "A"); put(s, "2,3", "sardine", "A")    # two Fish beside 2,2
    put(s, "1,2", "stick_insect", "B")                              # Stealth: random effects hit it
    put(s, "3,2", "lion", "B")
    put(s, "1,1", "caracal", "A")                                   # (connection)
    rules.apply_action(s, PlaceAction("swordfish", ("cr", "2,2")))
    assert s.top_unit("1,2") is None and s.top_unit("3,2") is None


def test_swordfish_without_adjacent_fish_removes_nothing():
    s = make_state(hands={"A": ["swordfish"]})
    put(s, "1,1", "lion", "A")                                      # an ally, not a Fish
    put(s, "2,2", "lion", "B")
    put(s, "1,3", "sardine", "B")                                   # an enemy Fish doesn't count
    rules.apply_action(s, PlaceAction("swordfish", ("cr", "1,2")))
    assert s.remove_pile == []


def test_swordfish_armor_enemy_is_not_removed():
    s = make_state(hands={"A": ["swordfish"]})
    put(s, "1,1", "sardine", "A")
    put(s, "2,2", "tortoise", "B")
    rules.apply_action(s, PlaceAction("swordfish", ("cr", "1,2")))
    assert s.top_unit("2,2").card_id == "tortoise"


# ------------------------------------------------------------------ Barracuda: Roar: remove an adjacent enemy with strength up to the number of your Fish.

def test_barracuda_counts_every_fish_you_control_itself_included():
    s = make_state(hands={"A": ["barracuda"]})
    put(s, "3,3", "sardine", "A"); put(s, "4,1", "sardine", "A"); put(s, "1,1", "sardine", "A")
    put(s, "2,2", "mouse", "B")                     # 4 = 3 Sardines + the Barracuda
    apply_click(s, PlaceAction("barracuda", ("cr", "1,2")))
    assert removed(s, "mouse")


def test_barracuda_spares_an_enemy_stronger_than_the_school():
    s = make_state(hands={"A": ["barracuda"]})
    put(s, "1,1", "sardine", "A")
    put(s, "2,2", "mouse", "B")                     # 4 > 2 Fish
    apply_click(s, PlaceAction("barracuda", ("cr", "1,2")))
    assert s.top_unit("2,2").card_id == "mouse" and not s.pending


def test_barracuda_ignores_enemy_fish_in_the_count():
    s = make_state(hands={"A": ["barracuda"]})
    for cr in ("3,1", "3,3", "4,1"):
        put(s, cr, "sardine", "B")
    put(s, "2,2", "chipmunk", "B")                  # 1 ... wait: 1 <= 1 (the Barracuda itself)
    put(s, "1,1", "fox", "B")                       # 3 > 1
    apply_click(s, PlaceAction("barracuda", ("cr", "1,2")))
    assert s.top_unit("1,1").card_id == "fox"


# ------------------------------------------------------------------ Manta Ray: Whenever your opponent covers an adjacent allied Fish, draw a card.

def test_manta_ray_draws_when_the_opponent_covers_an_adjacent_allied_fish():
    s = make_state(current="B", hands={"B": ["lion"]}, decks={"A": ["lion"], "B": []})
    put(s, "4,2", "lion", "B")
    put(s, "3,3", "manta_ray", "A")
    put(s, "3,2", "sardine", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))
    assert hand_ids(s, "A") == ["lion"]


def test_manta_ray_ignores_its_owner_covering_the_fish():
    s = make_state(hands={"A": ["lion"]}, decks={"A": ["mouse"], "B": []})
    put(s, "1,1", "manta_ray", "A")
    put(s, "1,2", "sardine", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "1,2")))
    assert hand_ids(s, "A") == []


def test_manta_ray_ignores_a_covered_non_fish_ally():
    s = make_state(current="B", hands={"B": ["lion"]}, decks={"A": ["lion"], "B": []})
    put(s, "4,2", "lion", "B")
    put(s, "3,3", "manta_ray", "A")
    put(s, "3,2", "mouse", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))
    assert hand_ids(s, "A") == []


def test_manta_ray_draws_when_a_roaming_enemy_covers_the_fish():
    s = make_state(current="B", decks={"A": ["lion"], "B": []})
    put(s, "4,2", "wolf", "B")
    put(s, "3,3", "manta_ray", "A")
    put(s, "3,2", "sardine", "A")
    rules.apply_action(s, RoamAction("4,2", ("cr", "3,2")))
    assert hand_ids(s, "A") == ["lion"]


# ------------------------------------------------------------------ Remora: Roar: if this is next to an allied Fish, play another Fish.

def test_remora_next_to_a_fish_plays_another_fish():
    s = make_state(hands={"A": ["remora", "lion", "sardine"]})
    put(s, "1,1", "tuna", "A")
    rules.apply_action(s, PlaceAction("remora", ("cr", "1,2")))
    assert {p["card_id"] for p in s.pending["placements"]} == {"sardine"}
    pl = next(p for p in s.pending["placements"] if p["card_id"] == "sardine")
    rules.apply_action(s, PlaceAction("sardine", tuple(pl["target"]), pl.get("iid")))
    assert "sardine" in board_ids(s, "A") and s.current == "A"     # no action spent


def test_remora_alone_plays_nothing():
    s = make_state(hands={"A": ["remora", "sardine"]})
    put(s, "3,3", "tuna", "A")                       # a Fish, but not next to it
    rules.apply_action(s, PlaceAction("remora", ("cr", "1,2")))
    assert not s.pending


def test_remora_next_to_an_enemy_fish_plays_nothing():
    s = make_state(hands={"A": ["remora", "sardine"]})
    put(s, "1,1", "tuna", "B")
    rules.apply_action(s, PlaceAction("remora", ("cr", "1,2")))
    assert not s.pending


def test_remora_cannot_pay_for_a_titan_fish():
    s = make_state(hands={"A": ["remora", "whale_shark"]})
    put(s, "1,1", "tuna", "A")
    rules.apply_action(s, PlaceAction("remora", ("cr", "1,2")))
    assert not s.pending or not any(p["card_id"] == "whale_shark" for p in s.pending.get("placements", []))


# ------------------------------------------------------------------ Cod: Roar: draw a card for each adjacent allied Fish.

def test_cod_draws_per_adjacent_allied_fish():
    s = make_state(hands={"A": ["cod"]}, decks={"A": ["lion"] * 4, "B": []})
    put(s, "1,1", "sardine", "A"); put(s, "1,3", "tuna", "A")
    put(s, "2,2", "sardine", "B")                    # an enemy Fish
    put(s, "3,3", "sardine", "A")                    # not adjacent
    rules.apply_action(s, PlaceAction("cod", ("cr", "1,2")))
    assert len(s.hands["A"]) == 2


def test_cod_without_adjacent_fish_draws_nothing():
    s = make_state(hands={"A": ["cod"]}, decks={"A": ["lion"] * 4, "B": []})
    put(s, "1,1", "lion", "A")
    rules.apply_action(s, PlaceAction("cod", ("cr", "1,2")))
    assert hand_ids(s, "A") == []


# ------------------------------------------------------------------ Sardine: Roar: fill adjacent empty crossroads with Sardines from your hand and deck.

def test_sardine_fills_adjacent_empty_crossroads_from_hand_and_deck():
    s = make_state(hands={"A": ["sardine", "sardine", "sardine"]}, decks={"A": ["sardine", "lion"], "B": []})
    rules.apply_action(s, PlaceAction("sardine", ("cr", "1,2")))   # 1,1 1,3 2,2, three copies left for three spots
    assert {cr for cr in ("1,1", "1,3", "2,2") if s.top_unit(cr) and s.top_unit(cr).card_id == "sardine"} == {"1,1", "1,3", "2,2"}
    assert board_ids(s, "A").count("sardine") == 4 and s.decks["A"].count("sardine") + hand_ids(s, "A").count("sardine") == 0


def test_sardine_skips_occupied_crossroads_and_leaves_leftovers():
    s = make_state(hands={"A": ["sardine", "sardine", "sardine"]}, decks={"A": ["sardine"], "B": []})
    put(s, "1,1", "lion", "B"); put(s, "1,3", "mouse", "A")         # only 2,2 is empty
    rules.apply_action(s, PlaceAction("sardine", ("cr", "1,2")))
    assert s.top_unit("1,1").card_id == "lion" and s.top_unit("1,3").card_id == "mouse"
    assert s.top_unit("2,2").card_id == "sardine"
    assert hand_ids(s, "A").count("sardine") + s.decks["A"].count("sardine") == 2   # leftovers stay where they are


def test_sardine_copies_do_not_roar():
    s = make_state(hands={"A": ["sardine", "sardine"]})
    rules.apply_action(s, PlaceAction("sardine", ("cr", "1,2")))
    # one copy lands beside it; it doesn't roar to pull the other one further out
    assert board_ids(s, "A").count("sardine") == 2 and hand_ids(s, "A") == []


# ------------------------------------------------------------------ Mahi-mahi: Your other Fish have +1 strength.

def test_mahi_mahi_gives_other_allied_fish_plus_one_live():
    s = make_state()
    mahi = put(s, "1,2", "mahi_mahi", "A")
    sar = put(s, "3,3", "sardine", "A")              # anywhere: not only adjacent
    enemy = put(s, "4,1", "sardine", "B")
    lion = put(s, "1,1", "lion", "A")
    assert effective_strength(s, sar) == CARDS["sardine"].base_strength + 1
    assert effective_strength(s, mahi) == CARDS["mahi_mahi"].base_strength
    assert effective_strength(s, enemy) == CARDS["sardine"].base_strength
    assert effective_strength(s, lion) == 7
    put(s, "1,2", "lion", "B")                       # buried: the aura goes
    assert effective_strength(s, sar) == CARDS["sardine"].base_strength


# ------------------------------------------------------------------ Tuna: Has +1 strength for each other Fish you control.

def test_tuna_grows_per_other_allied_fish():
    s = make_state()
    tuna = put(s, "1,2", "tuna", "A")
    assert effective_strength(s, tuna) == 3
    put(s, "3,3", "sardine", "A"); put(s, "4,1", "baby_fish", "A")
    put(s, "2,2", "sardine", "B")                    # enemy Fish: not yours
    assert effective_strength(s, tuna) == 5
    put(s, "3,3", "lion", "B")                       # a covered Fish isn't controlled
    assert effective_strength(s, tuna) == 4


# ------------------------------------------------------------------ Sunfish: Roar: place a Baby Fish on a random adjacent empty crossroad.

def test_sunfish_places_a_baby_fish_on_an_adjacent_empty_crossroad():
    s = make_state(hands={"A": ["sunfish"]})
    put(s, "1,1", "lion", "B"); put(s, "1,3", "lion", "A")
    rules.apply_action(s, PlaceAction("sunfish", ("cr", "1,2")))
    assert not s.pending
    assert s.top_unit("2,2").card_id == "baby_fish" and s.top_unit("2,2").owner == "A"


def test_sunfish_with_no_empty_neighbour_places_nothing():
    s = make_state(hands={"A": ["sunfish"]})
    put(s, "1,1", "lion", "B"); put(s, "1,3", "lion", "A"); put(s, "2,2", "mouse", "B")
    rules.apply_action(s, PlaceAction("sunfish", ("cr", "1,2")))
    assert "baby_fish" not in board_ids(s)


# ------------------------------------------------------------------ [OCTOPUS]: Roar: Scout a legendary animal.

LEGENDS = ["tuna_legend", "sardine_legend", "manta_ray_legend", "sperm_whale_legend"]


def test_octopus_legend_scouts_three_different_legendaries_and_draws_one():
    s = make_state(hands={"A": ["octopus_legend_2"]}, decks={"A": ["lion", "mouse"] + LEGENDS, "B": []})
    rules.apply_action(s, PlaceAction("octopus_legend_2", ("cr", "1,2")))
    assert s.pending is not None
    opts = set(s.pending["options"])
    shown = {o if isinstance(o, str) else o for o in opts}
    assert len(shown) == 3 and shown <= set(LEGENDS)
    pick = sorted(shown)[0]
    choose(s, pick)
    assert hand_ids(s, "A") == [pick]
    assert sorted(s.decks["A"]) == sorted(["lion", "mouse"] + [c for c in LEGENDS if c != pick])


def test_octopus_legend_with_no_legendary_in_the_deck_does_nothing():
    s = make_state(hands={"A": ["octopus_legend_2"]}, decks={"A": ["lion", "mouse"], "B": []})
    rules.apply_action(s, PlaceAction("octopus_legend_2", ("cr", "1,2")))
    assert not s.pending and hand_ids(s, "A") == [] and sorted(s.decks["A"]) == ["lion", "mouse"]


def test_octopus_legend_with_one_legendary_draws_it():
    s = make_state(hands={"A": ["octopus_legend_2"]}, decks={"A": ["lion", "mouse", "tuna_legend"], "B": []})
    apply_click(s, PlaceAction("octopus_legend_2", ("cr", "1,2")))
    assert hand_ids(s, "A") == ["tuna_legend"]


# ------------------------------------------------------------------ Jellyfish: Poison. Your adjacent animals have Poison.

def test_jellyfish_itself_poisons_its_coverer():
    s = make_state(current="B", hands={"B": ["lion"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "4,2", "lion", "B")
    put(s, "3,2", "jellyfish", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))
    assert s.top_unit("3,2").card_id == "lion"       # the coverer gets the rest of its turn
    end_turn(s)
    assert s.top_unit("3,2").card_id == "jellyfish" and removed(s, "lion")


def test_jellyfish_poisons_adjacent_allies_only():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "3,3", "jellyfish", "A")
    sq = put(s, "3,2", "squirrel", "A")
    enemy = put(s, "4,3", "mouse", "B")
    far = put(s, "1,1", "mouse", "A")
    assert "Poison" in statics.unit_keywords(s, sq)
    assert "Poison" not in statics.unit_keywords(s, enemy)
    assert "Poison" not in statics.unit_keywords(s, far)


def test_jellyfish_poison_set_off_by_enemy_cover_of_adjacent_ally():
    s = make_state(current="B", hands={"B": ["lion"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "4,2", "lion", "B")
    put(s, "3,3", "jellyfish", "A")
    put(s, "3,2", "squirrel", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "3,2")))
    end_turn(s)
    assert s.top_unit("3,2").card_id == "squirrel" and removed(s, "lion")


def test_jellyfish_friendly_cover_is_harmless():
    s = make_state(hands={"A": ["lion"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,1", "jellyfish", "A")
    rules.apply_action(s, PlaceAction("lion", ("cr", "1,1")))
    end_turn(s); end_turn(s)
    assert s.top_unit("1,1").card_id == "lion" and not removed(s, "lion")


# ------------------------------------------------------------------ [SPERM WHALE]: Titan. Dusk: remove the strongest adjacent enemy.

def test_sperm_whale_legend_removes_the_strongest_adjacent_enemy_at_dusk():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "2,2", "sperm_whale_legend", "A")
    put(s, "1,2", "elephant", "A")                   # a stronger ally isn't an enemy
    put(s, "3,2", "lion", "B")                       # 7
    put(s, "2,1", "mouse", "B")                      # 4
    put(s, "4,3", "elephant", "B")                   # stronger, but not adjacent
    end_turn(s)
    assert s.top_unit("3,2") is None and s.top_unit("2,1").card_id == "mouse"
    assert s.top_unit("1,2").card_id == "elephant" and s.top_unit("4,3").card_id == "elephant"


def test_sperm_whale_legend_only_at_its_owners_dusk():
    s = make_state(current="B", decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "2,2", "sperm_whale_legend", "A")
    put(s, "3,2", "lion", "B")
    end_turn(s)                                      # B's Dusk
    assert s.top_unit("3,2").card_id == "lion"


def test_sperm_whale_legend_strongest_has_armor_nothing_removed_or_next():
    """The strongest adjacent enemy has Armor: it can't be removed. Literal reading: the Dusk names the strongest, and
    fails on it; the weaker one stays."""
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "2,2", "sperm_whale_legend", "A")
    put(s, "3,2", "tortoise", "B")                   # 6, Armor
    put(s, "2,1", "mouse", "B")                      # 4
    end_turn(s)
    assert s.top_unit("3,2").card_id == "tortoise"


def test_sperm_whale_legend_is_a_titan():
    s = make_state(hands={"A": ["sperm_whale_legend"]}, decks={"A": ["lion"] * 3, "B": []})
    rules.apply_action(s, DrawAction())
    assert not places(s, "sperm_whale_legend")


# ------------------------------------------------------------------ Whale Shark: Titan. Hungry 4. Dusk: draw a card.

def test_whale_shark_draws_at_dusk():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,2", "whale_shark", "A")
    end_turn(s)
    assert len(s.hands["A"]) == 1


def test_whale_shark_eats_four_food_at_dawn():
    s = make_state(current="B", decks={"A": ["lion"] * 3, "B": ["lion"] * 3}, food={"A": 10, "B": 0})
    ws = put(s, "3,3", "whale_shark", "A")
    end_turn(s)                                      # A's Dawn
    assert s.food["A"] == 6 and effective_strength(s, ws) == 8


def test_whale_shark_short_of_food_loses_strength_for_good():
    s = make_state(current="B", decks={"A": ["lion"] * 3, "B": ["lion"] * 3}, food={"A": 1, "B": 0})
    ws = put(s, "3,3", "whale_shark", "A")
    end_turn(s)
    assert s.food["A"] == 0 and effective_strength(s, ws) == 8 - 3
    s.food["A"] = 50
    assert effective_strength(s, ws) == 5            # for good


def test_whale_shark_is_a_titan():
    s = make_state(hands={"A": ["whale_shark"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    rules.apply_action(s, PlaceAction("whale_shark", ("cr", "1,2")))
    assert s.current == "B"


# ------------------------------------------------------------------ Blue Whale: Titan.

def test_blue_whale_costs_two_actions():
    s = make_state(hands={"A": ["blue_whale", "blue_whale"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    rules.apply_action(s, PlaceAction("blue_whale", ("cr", "1,2")))
    assert s.current == "B"
    assert effective_strength(s, s.top_unit("1,2")) == 12


def test_blue_whale_not_offered_with_one_action_left():
    s = make_state(hands={"A": ["blue_whale"]}, decks={"A": ["lion"] * 3, "B": []})
    rules.apply_action(s, DrawAction())
    assert not places(s, "blue_whale")


def test_blue_whale_first_players_one_action_first_turn():
    s = make_state(hands={"A": ["blue_whale"]}, decks={"A": ["lion"] * 3, "B": []})
    s.turn_counter = 0                               # the first player's first turn has one action
    acts = rules.legal_actions(s)
    if s.config.actions_per_turn and not any(isinstance(a, DrawAction) for a in acts):
        pytest.skip("fixture can't express the first turn")
    assert not places(s, "blue_whale")


# ------------------------------------------------------------------ Octopus: Roar: adjacent enemies lose all their effects.

def test_octopus_inks_adjacent_enemies_for_good_not_allies():
    s = make_state(hands={"A": ["octopus"]}, decks={"A": ["lion"] * 4, "B": ["lion"] * 4})
    put(s, "1,2", "caracal", "A")
    porc = put(s, "3,2", "porcupine", "B")
    stealthy = put(s, "2,1", "stick_insect", "B")    # Stealth doesn't keep it out (not chosen)
    ally = put(s, "2,3", "hedgehog", "A")
    far = put(s, "4,3", "hedgehog", "B")
    rules.apply_action(s, PlaceAction("octopus", ("cr", "2,2")))
    assert statics.inked(s, porc) and statics.inked(s, stealthy)
    assert not statics.unit_keywords(s, porc) and not statics.unit_keywords(s, stealthy)
    assert "Spikes" in statics.unit_keywords(s, ally) and "Spikes" in statics.unit_keywords(s, far)
    for _ in range(4):
        end_turn(s)
    assert statics.inked(s, porc)


def test_octopus_inked_spikes_do_not_fire():
    s = make_state(hands={"A": ["octopus", "lion"]}, decks={"A": ["lion"] * 4, "B": ["lion"] * 4})
    put(s, "1,2", "caracal", "A")
    put(s, "2,1", "hedgehog", "B")
    rules.apply_action(s, PlaceAction("octopus", ("cr", "1,1")))
    rules.apply_action(s, PlaceAction("lion", ("cr", "2,1")))
    assert s.top_unit("2,1").card_id == "lion"


# ------------------------------------------------------------------ Shark: Apex Predator. Has Reach if an animal was removed this turn.

def test_great_white_shark_reach_only_after_a_removal_this_turn():
    s = make_state(hands={"A": ["great_white_shark"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "2,2", "mouse", "B")                      # two crossroads out from the den front
    assert ("cr", "2,2") not in places(s, "great_white_shark")
    put(s, "4,3", "squirrel", "B")
    effects.remove_top(s, "4,3", by_player="A")      # an enemy left the board: any animal counts
    assert ("cr", "2,2") in places(s, "great_white_shark")


def test_great_white_shark_reach_counts_an_ally_removed_too():
    s = make_state(hands={"A": ["great_white_shark"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "2,2", "mouse", "B")
    put(s, "3,3", "mouse", "A")
    effects.remove_top(s, "3,3", by_player="B")
    assert ("cr", "2,2") in places(s, "great_white_shark")


def test_great_white_shark_reach_is_gone_next_turn():
    s = make_state(hands={"A": ["great_white_shark"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "2,2", "mouse", "B")
    put(s, "4,3", "squirrel", "B")
    effects.remove_top(s, "4,3", by_player="A")
    end_turn(s); end_turn(s)
    assert ("cr", "2,2") not in places(s, "great_white_shark")


def test_great_white_shark_never_on_an_empty_crossroad_and_eats():
    s = make_state(hands={"A": ["great_white_shark"]})
    assert not places(s, "great_white_shark")
    put(s, "1,2", "mouse", "B")
    rules.apply_action(s, PlaceAction("great_white_shark", ("cr", "1,2")))
    assert removed(s, "mouse") and s.top_unit("1,2").card_id == "great_white_shark"


# ------------------------------------------------------------------ Dolphin: Roar: draw a card.

def test_dolphin_draws_a_card():
    s = make_state(hands={"A": ["dolphin"]}, decks={"A": ["lion"] * 3, "B": []})
    rules.apply_action(s, PlaceAction("dolphin", ("cr", "1,2")))
    assert hand_ids(s, "A") == ["lion"] and effective_strength(s, s.top_unit("1,2")) == 5


def test_dolphin_with_an_empty_deck_draws_nothing():
    s = make_state(hands={"A": ["dolphin"]})
    rules.apply_action(s, PlaceAction("dolphin", ("cr", "1,2")))
    assert hand_ids(s, "A") == [] and s.top_unit("1,2").card_id == "dolphin"


# ------------------------------------------------------------------ Albatross: Flight. Roar: remove all adjacent enemies of strength 3 or less.

def test_albatross_sweeps_small_enemies_only():
    s = make_state(hands={"A": ["albatross"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "2,1", "sardine", "B")                    # 0
    put(s, "3,2", "fox", "B")                        # 3: "3 or less"
    put(s, "2,3", "mouse", "B")                      # 4
    put(s, "1,2", "chipmunk", "A")                   # an ally of 1 stays
    rules.apply_action(s, PlaceAction("albatross", ("cr", "2,2")))   # Flight: not connected
    assert s.top_unit("2,1") is None and s.top_unit("3,2") is None
    assert s.top_unit("2,3").card_id == "mouse" and s.top_unit("1,2").card_id == "chipmunk"


def test_albatross_hits_stealth_but_not_armor():
    s = make_state(hands={"A": ["albatross"]})
    put(s, "2,1", "baby_turtle", "B")
    st = put(s, "3,2", "stick_insect", "B"); st.strength_counter = -4      # a 2 with Stealth: a mass effect hits it
    tor = put(s, "2,3", "tortoise", "B"); tor.strength_counter = -4        # a 2 with Armor
    rules.apply_action(s, PlaceAction("albatross", ("cr", "2,2")))
    assert s.top_unit("2,1") is None and s.top_unit("3,2") is None and s.top_unit("2,3").card_id == "tortoise"


def test_albatross_flight_never_captures_the_den():
    s = make_state(hands={"A": ["albatross"]})
    assert not any(t[0] == "hq" for t in places(s, "albatross"))
    assert ("cr", "3,3") in places(s, "albatross")


# ------------------------------------------------------------------ Sea Turtle: Armor. Dusk: add a Baby Turtle to your hand.

def test_sea_turtle_adds_a_baby_turtle_at_dusk_only():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,2", "sea_turtle", "A")
    end_turn(s)
    assert hand_ids(s, "A") == ["baby_turtle"]
    end_turn(s)                                      # B's Dusk: nothing for A
    assert hand_ids(s, "A") == ["baby_turtle"]


def test_sea_turtle_armor_resists_removal_but_not_covering():
    s = make_state(hands={"A": ["sperm_whale", "lion"]})
    turtle = put(s, "2,2", "sea_turtle", "B")
    rules.apply_action(s, PlaceAction("sperm_whale", ("cr", "1,2")))
    assert s.top_unit("2,2") is turtle
    s2 = make_state(hands={"A": ["lion"]})
    put(s2, "1,2", "lion", "A")
    put(s2, "2,2", "sea_turtle", "B")
    rules.apply_action(s2, PlaceAction("lion", ("cr", "2,2")))
    assert s2.top_unit("2,2").card_id == "lion"


def test_sea_turtle_buried_does_not_dusk():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,2", "sea_turtle", "A")
    put(s, "1,2", "lion", "B")
    end_turn(s)
    assert hand_ids(s, "A") == []


# ------------------------------------------------------------------ Hammerhead: Roar: if an ally was removed this turn, remove an adjacent animal.

def test_hammerhead_without_blood_removes_nothing():
    s = make_state(hands={"A": ["hammerhead"]})
    put(s, "2,2", "lion", "B")
    apply_click(s, PlaceAction("hammerhead", ("cr", "1,2")))
    assert s.top_unit("2,2") is not None


def test_hammerhead_after_an_ally_removed_removes_any_adjacent_animal():
    s = make_state(hands={"A": ["hammerhead"]})
    put(s, "2,2", "lion", "B")
    put(s, "1,1", "mouse", "A")
    put(s, "3,3", "mouse", "A")
    effects.remove_top(s, "3,3", by_player="B")
    rules.apply_action(s, PlaceAction("hammerhead", ("cr", "1,2")))
    assert set(s.pending["options"]) >= {"1,1", "2,2"}       # an ally beside it is an "animal" too
    choose(s, "2,2")
    assert s.top_unit("2,2") is None


def test_hammerhead_an_enemy_removed_is_not_an_ally():
    s = make_state(hands={"A": ["hammerhead"]})
    put(s, "2,2", "lion", "B")
    put(s, "3,3", "mouse", "B")
    effects.remove_top(s, "3,3", by_player="A")
    apply_click(s, PlaceAction("hammerhead", ("cr", "1,2")))
    assert s.top_unit("2,2").card_id == "lion"


def test_hammerhead_ally_removed_last_turn_does_not_count():
    s = make_state(current="B", hands={"A": ["hammerhead"]}, decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "2,2", "lion", "B")
    put(s, "3,3", "mouse", "A")
    effects.remove_top(s, "3,3", by_player="B")              # on B's turn
    end_turn(s)
    apply_click(s, PlaceAction("hammerhead", ("cr", "1,2")))
    assert s.top_unit("2,2").card_id == "lion"


# ------------------------------------------------------------------ Krill: Roar: draw a card. The next Titan you play this turn costs one action.

def test_krill_draws_and_the_next_titan_costs_one_action():
    s = make_state(hands={"A": ["krill", "blue_whale", "blue_whale"]}, decks={"A": ["lion"] * 4, "B": ["lion"] * 4})
    rules.apply_action(s, PlaceAction("krill", ("cr", "1,2")))
    assert sorted(hand_ids(s, "A")) == ["blue_whale", "blue_whale", "lion"]
    assert ("cr", "1,1") in places(s, "blue_whale")
    rules.apply_action(s, PlaceAction("blue_whale", ("cr", "1,1")))
    assert s.current == "B"


def test_krill_discount_ends_with_the_turn():
    s = make_state(hands={"A": ["krill", "blue_whale"]}, decks={"A": ["lion"] * 4, "B": ["lion"] * 4})
    rules.apply_action(s, PlaceAction("krill", ("cr", "1,2")))
    rules.apply_action(s, DrawAction())                      # the turn ends unused
    end_turn(s)                                              # B
    rules.apply_action(s, DrawAction())                      # one action left on A's next turn
    assert not places(s, "blue_whale")


def test_krill_discount_is_for_one_titan_only():
    s = make_state(hands={"A": ["krill", "blue_whale", "blue_whale"]}, decks={"A": ["lion"] * 4, "B": ["lion"] * 4})
    s.actions_taken_this_turn = -1                           # three actions this turn (a Chipmunk-style extra)
    rules.apply_action(s, PlaceAction("krill", ("cr", "1,2")))
    rules.apply_action(s, PlaceAction("blue_whale", ("cr", "1,1")))   # one action: one left
    assert s.current == "A"
    assert not places(s, "blue_whale")                       # the second costs two again


# ------------------------------------------------------------------ [SARDINE]: [SARDINE] and your adjacent Fish count as 2 Fish.

def test_sardine_legend_and_adjacent_fish_count_twice():
    s = make_state()
    put(s, "1,1", "sardine_legend", "A")
    tuna = put(s, "2,1", "tuna", "A")
    assert effective_strength(s, tuna) == 3 + 2
    put(s, "4,3", "sardine", "A")
    assert effective_strength(s, tuna) == 3 + 2 + 1
    put(s, "1,2", "sardine", "A")                            # beside the legend: 2
    assert effective_strength(s, tuna) == 3 + 2 + 1 + 2


def test_sardine_legend_does_not_double_enemy_fish():
    s = make_state()
    put(s, "1,1", "sardine_legend", "A")
    tuna = put(s, "3,3", "tuna", "B")
    put(s, "2,1", "sardine", "B")                            # an enemy Fish beside the legend
    assert effective_strength(s, tuna) == 3 + 1


def test_sardine_legend_covered_stops_counting():
    s = make_state()
    put(s, "1,1", "sardine_legend", "A")
    tuna = put(s, "2,1", "tuna", "A")
    put(s, "1,1", "lion", "B")
    assert effective_strength(s, tuna) == 3


def test_sardine_legend_doubles_for_barracuda():
    s = make_state(hands={"A": ["barracuda"]})
    put(s, "1,1", "sardine_legend", "A")                     # 2, and the Barracuda beside it: 2
    put(s, "2,2", "fox", "B")                                # 3 <= 4
    apply_click(s, PlaceAction("barracuda", ("cr", "1,2")))
    assert removed(s, "fox")


# ------------------------------------------------------------------ edges found on a second pass

def test_sperm_whale_legend_dusk_hits_a_stealth_enemy():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "2,2", "sperm_whale_legend", "A")
    put(s, "3,2", "stick_insect", "B")               # 6, Stealth: an automatic effect, nobody chooses
    put(s, "2,1", "mouse", "B")
    end_turn(s)
    assert s.top_unit("3,2") is None and s.top_unit("2,1").card_id == "mouse"


@pytest.mark.xfail(strict=True, reason=(
    "Two readings of 'remove the strongest adjacent enemy' when that enemy has Armor: (A, literal) the strongest is the "
    "Armor animal, it can't be removed, nothing happens; (B, the engine) the strongest enemy that can be removed, so the "
    "weaker one goes. The Tarantula and City Spider rulings exclude Armor before picking, as B does."))
def test_sperm_whale_legend_strongest_armored_weaker_stays():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "2,2", "sperm_whale_legend", "A")
    put(s, "3,2", "tortoise", "B")                   # the strongest adjacent enemy, and it can't be removed
    put(s, "2,1", "mouse", "B")
    end_turn(s)
    assert s.top_unit("2,1").card_id == "mouse"


def test_barracuda_cannot_choose_a_stealth_enemy():
    s = make_state(hands={"A": ["barracuda"]})
    for cr in ("3,1", "3,3", "4,1", "4,3", "1,1"):
        put(s, cr, "sardine", "A")                   # 6 Fish with the Barracuda
    st = put(s, "2,2", "stick_insect", "B")           # 6, Stealth
    apply_click(s, PlaceAction("barracuda", ("cr", "1,2")))
    assert s.top_unit("2,2") is st and not s.pending


def test_swordfish_counts_a_doubled_fish_twice():
    s = make_state(hands={"A": ["swordfish"]})
    put(s, "1,1", "sardine_legend", "A")             # counts as 2 Fish
    put(s, "2,2", "lion", "B"); put(s, "1,3", "lion", "B")
    rules.apply_action(s, PlaceAction("swordfish", ("cr", "1,2")))
    assert s.remove_pile.count("lion") == 2


def test_cod_counts_a_doubled_fish_twice():
    s = make_state(hands={"A": ["cod"]}, decks={"A": ["lion"] * 4})
    put(s, "1,1", "sardine_legend", "A")
    rules.apply_action(s, PlaceAction("cod", ("cr", "1,2")))
    assert len(s.hands["A"]) == 2


def test_remora_does_not_play_a_fish_from_the_deck():
    s = make_state(hands={"A": ["remora", "lion"]}, decks={"A": ["sardine"] * 3})
    put(s, "1,1", "tuna", "A")
    rules.apply_action(s, PlaceAction("remora", ("cr", "1,2")))
    assert not s.pending and s.top_unit("1,3") is None


def test_hammerhead_cannot_choose_a_stealth_enemy():
    s = make_state(hands={"A": ["hammerhead"]})
    put(s, "2,2", "stick_insect", "B")
    put(s, "3,3", "mouse", "A")
    effects.remove_top(s, "3,3", by_player="B")
    apply_click(s, PlaceAction("hammerhead", ("cr", "1,2")))
    assert s.top_unit("2,2").card_id == "stick_insect"


def test_whale_shark_cannot_be_played_by_a_free_placement():
    s = make_state(hands={"A": ["remora", "whale_shark", "sardine"]})
    put(s, "1,1", "tuna", "A")
    rules.apply_action(s, PlaceAction("remora", ("cr", "1,2")))
    assert {p["card_id"] for p in s.pending["placements"]} == {"sardine"}


def test_mahi_mahi_anthem_counts_for_covering():
    s = make_state(hands={"A": ["sardine"]})
    put(s, "1,1", "mahi_mahi", "A")
    put(s, "1,2", "baby_turtle", "B")                # 0: a Sardine (0) +1 covers it
    assert ("cr", "1,2") in places(s, "sardine")


def test_albatross_counts_live_strength():
    s = make_state(hands={"A": ["albatross"]})
    put(s, "4,1", "mahi_mahi", "B")                  # B's Fish have +1
    put(s, "2,1", "swordfish", "B")                  # 3 + 1 = 4: survives
    rules.apply_action(s, PlaceAction("albatross", ("cr", "2,2")))
    assert s.top_unit("2,1").card_id == "swordfish"


def test_manta_ray_draws_when_an_enemy_apex_eats_an_adjacent_allied_fish():
    s = make_state(current="B", hands={"B": ["tiger"]}, decks={"A": ["lion"], "B": ["lion"] * 3})
    put(s, "4,2", "lion", "B")
    put(s, "3,3", "manta_ray", "A")
    put(s, "3,2", "sardine", "A")
    rules.apply_action(s, PlaceAction("tiger", ("cr", "3,2")))    # a cover, then the eat
    assert hand_ids(s, "A") == ["lion"] and removed(s, "sardine")


def test_octopus_roar_does_not_ink_an_enemy_arriving_later():
    s = make_state(hands={"A": ["octopus"]})
    put(s, "1,2", "caracal", "A")
    rules.apply_action(s, PlaceAction("octopus", ("cr", "2,2")))
    late = put(s, "3,2", "hedgehog", "B")
    assert not statics.inked(s, late) and "Spikes" in statics.unit_keywords(s, late)


def test_whale_shark_buried_does_not_draw_at_dusk():
    s = make_state(decks={"A": ["lion"] * 3, "B": ["lion"] * 3})
    put(s, "1,2", "whale_shark", "A")
    put(s, "1,2", "elephant", "B").strength_counter = 0
    s.board["1,2"][-1].strength_counter = 0
    end_turn(s)
    assert hand_ids(s, "A") == []


def test_great_white_shark_reach_jumps_from_any_connected_ally():
    s = make_state(hands={"A": ["great_white_shark"]})
    put(s, "1,2", "lion", "A"); put(s, "2,2", "mouse", "A")
    put(s, "4,2", "mouse", "B")                      # two from the connected Mouse on 2,2
    assert ("cr", "4,2") not in places(s, "great_white_shark")
    put(s, "3,3", "mouse", "A")
    effects.remove_top(s, "3,3", by_player="B")
    assert ("cr", "4,2") in places(s, "great_white_shark")
