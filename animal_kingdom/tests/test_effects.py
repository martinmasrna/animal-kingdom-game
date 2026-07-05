"""Phase 2 golden tests: one focused scenario per reworked card / mechanism.

Grows stage by stage (the module-wide skip was dropped in Stage 2.1). Map A geometry used
below: A's HQ fronts are column 1 ("1,1"/"1,2"/"1,3"), B's are column 4; crossroads are a
4x3 grid with orthogonal neighbours, so "2,2" is adjacent to "1,2","3,2","2,1","2,3".
"""

from __future__ import annotations

from animal_kingdom.engine import effects, rules
from animal_kingdom.engine.actions import SKIP, ChoiceAction, DrawAction, PlaceAction
from animal_kingdom.engine.cards import load_cards
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.maps import load_map
from animal_kingdom.engine.state import GameState, UnitInstance
from animal_kingdom.engine.strength import card_strength, effective_strength, placement_strength

CFG = Config.default()
CARDS = load_cards()


def hand_ids(state, player):
    return [u.card_id for u in state.hands[player]]


def make_state(*, current="A", hands=None, decks=None, food=None) -> GameState:
    state = GameState(
        load_map("map_a"), load_cards(), Config.default(),
        board={}, hands={"A": [], "B": []}, decks=decks or {"A": [], "B": []},
        remove_pile=[], food=food or {"A": 0, "B": 0}, current=current, first_player="A",
    )
    for player, ids in (hands or {}).items():
        for card_id in ids:
            state.add_to_hand(player, card_id)
    return state


def put(state: GameState, cr: str, card_id: str, owner: str) -> UnitInstance:
    u = UnitInstance(card_id, owner, state.new_iid(), placed_on_turn=state.turn_counter)
    state.board.setdefault(cr, []).append(u)
    return u


def hand_inst(state, player, card_id):
    return next(u for u in state.hands[player] if u.card_id == card_id)


def place_targets(state):
    return {a.target[1] for a in rules.legal_actions(state)
            if isinstance(a, PlaceAction) and a.target[0] == "cr"}


def advance_to(state, target_tc):
    """Advance by drawing each turn until turn_counter reaches target_tc (or terminal)."""
    while state.turn_counter < target_tc and rules.is_terminal(state) is None:
        rules.apply_action(state, DrawAction())


# ============================================================== anthems ("has +X", live)

def test_lobo_scales_with_other_canines():
    s = make_state()
    lobo = put(s, "1,1", "lobo", "A")
    assert effective_strength(s, lobo) == 4              # base, no other Canines
    put(s, "1,2", "coyote", "A")
    assert effective_strength(s, lobo) == 6              # +2 per other Canine


def test_raksha_buffs_other_canines_but_not_itself():
    s = make_state()
    raksha = put(s, "1,1", "raksha", "A")
    coyote = put(s, "1,2", "coyote", "A")
    assert effective_strength(s, coyote) == 5            # 3 + 2 aura
    assert effective_strength(s, raksha) == 4            # aura excludes itself


def test_african_wild_dog_counts_itself():
    s = make_state()
    awd = put(s, "1,1", "african_wild_dog", "A")
    assert effective_strength(s, awd) == 3               # 2 + 1 (itself)
    put(s, "1,2", "fox", "A")
    assert effective_strength(s, awd) == 4               # + another friendly Canine


def test_verminus_counts_any_other_unit():
    s = make_state()
    verm = put(s, "1,1", "verminus", "A")
    assert effective_strength(s, verm) == 3
    put(s, "1,2", "lion", "A")                           # a Cat still counts (any unit)
    assert effective_strength(s, verm) == 4


def test_guard_hornet_anthem_gated_on_five_colony():
    s = make_state()
    gh = put(s, "1,1", "guard_hornet", "A")
    assert effective_strength(s, gh) == 3
    for cr in ("1,2", "1,3", "2,1", "2,2"):              # four more Colony -> 5 incl. self
        put(s, cr, "worker_ant", "A")
    assert effective_strength(s, gh) == 8                # +5 anthem


# ============================================== counters ("give +X", stored on instance)

def test_dhole_buffs_adjacent_friendly_canine_and_fires_reactor():
    s = make_state(hands={"A": ["dhole"]}, decks={"A": ["lion", "tiger"], "B": []})
    fox = put(s, "1,2", "fox", "A")                      # adjacent to 2,2; has on_gain reactor
    rules.apply_action(s, PlaceAction("dhole", ("cr", "2,2")))
    assert fox.strength_counter == 2
    assert len(s.hands["A"]) == 1                        # Fox drew 1 on gaining strength


def test_clarion_buffs_other_canines_in_hand_and_on_board():
    s = make_state(hands={"A": ["clarion", "gray_wolf"]})
    coyote = put(s, "1,2", "coyote", "A")
    rules.apply_action(s, PlaceAction("clarion", ("cr", "2,2")))
    assert coyote.strength_counter == 1
    assert hand_inst(s, "A", "gray_wolf").strength_counter == 1


def test_red_wolf_buffs_only_hand_canines():
    s = make_state(hands={"A": ["red_wolf", "gray_wolf", "lion"]})
    rules.apply_action(s, PlaceAction("red_wolf", ("cr", "1,2")))
    assert hand_inst(s, "A", "gray_wolf").strength_counter == 1
    assert hand_inst(s, "A", "lion").strength_counter == 0    # not a Canine


def test_hand_counter_travels_onto_the_board():
    s = make_state(hands={"A": ["gray_wolf"]})
    hand_inst(s, "A", "gray_wolf").strength_counter = 2
    iid = hand_inst(s, "A", "gray_wolf").iid
    rules.apply_action(s, PlaceAction("gray_wolf", ("cr", "1,1")))
    placed = s.top_unit("1,1")
    assert placed.iid == iid and placed.strength_counter == 2  # same instance moved
    assert effective_strength(s, placed) == 6                  # base 4 + counter


def test_dingo_buffs_adjacent_canine_at_end_of_turn():
    s = make_state(current="A", decks={"A": ["lion"], "B": ["lynx"]})
    put(s, "2,2", "dingo", "A")
    fox = put(s, "1,2", "fox", "A")
    s.actions_taken_this_turn = s.config.actions_per_turn - 1
    rules.apply_action(s, DrawAction())                  # ends A's turn -> Dingo fires
    assert fox.strength_counter == 1


def test_shuck_returns_a_removed_canine_with_counter():
    s = make_state(hands={"A": ["shuck"]})
    s.remove_pile.append("gray_wolf")
    rules.apply_action(s, PlaceAction("shuck", ("cr", "1,2")))
    assert "gray_wolf" not in s.remove_pile
    assert hand_inst(s, "A", "gray_wolf").strength_counter == CFG.shuck_grant


# =================================================================== Canine removal/draw

def test_gray_wolf_removes_enemy_up_to_its_buffed_strength():
    s = make_state(hands={"A": ["gray_wolf"]})
    hand_inst(s, "A", "gray_wolf").strength_counter = 2  # buffed body 6
    put(s, "1,2", "lion", "A")                           # connects 2,2
    put(s, "3,2", "snow_leopard", "B")                   # enemy str 6, adjacent to 2,2
    put(s, "2,3", "lion", "B")                            # enemy str 7, adjacent to 2,2
    rules.apply_action(s, PlaceAction("gray_wolf", ("cr", "2,2")))
    assert s.owner_of("3,2") is None                     # 6 <= 6 removed
    assert s.owner_of("2,3") == "B"                       # 7 > 6 survives


def test_coyote_draws_only_when_buffed_to_threshold():
    s = make_state(hands={"A": ["coyote"]}, decks={"A": ["lion"], "B": []})
    hand_inst(s, "A", "coyote").strength_counter = 2     # body 5 >= threshold
    rules.apply_action(s, PlaceAction("coyote", ("cr", "1,2")))
    assert len(s.hands["A"]) == 1                         # drew


def test_coyote_does_not_draw_below_threshold():
    s = make_state(hands={"A": ["coyote"]}, decks={"A": ["lion"], "B": []})
    rules.apply_action(s, PlaceAction("coyote", ("cr", "1,2")))  # body 3 < 5
    assert s.hands["A"] == []


# ===================================================================== Group A statics

def test_porcupine_cannot_be_covered_by_enemy():
    s = make_state(current="B", hands={"B": ["king_theron"]})
    put(s, "4,2", "caracal", "B")                        # B front connects 3,2
    put(s, "3,2", "porcupine", "A")                      # A porcupine (str 7)
    # king_theron (8) is strictly greater than porcupine (7) - if the static block weren't
    # there, this cover would otherwise be legal by strength alone.
    assert PlaceAction("king_theron", ("cr", "3,2")) not in rules.legal_actions(s)


def test_chameleon_covers_anything_and_is_covered_by_anything():
    cover = make_state(hands={"A": ["chameleon"]})
    put(cover, "1,2", "caracal", "A")
    put(cover, "2,2", "lion", "B")                       # str 7 enemy
    assert PlaceAction("chameleon", ("cr", "2,2")) in rules.legal_actions(cover)

    covered = make_state(current="B", hands={"B": ["house_cat"]})
    put(covered, "4,2", "caracal", "B")
    put(covered, "3,2", "chameleon", "A")                # str 1 house_cat may cover it
    assert PlaceAction("house_cat", ("cr", "3,2")) in rules.legal_actions(covered)


def test_goliath_strength_equals_remove_pile_size():
    s = make_state()
    g = put(s, "1,1", "goliath", "A")
    assert effective_strength(s, g) == 0
    s.remove_pile.extend(["lion", "fox", "rat"])
    assert effective_strength(s, g) == 3


def test_immovable_survives_removal_effect():
    s = make_state(hands={"A": ["gray_wolf"]})
    hand_inst(s, "A", "gray_wolf").strength_counter = 3  # body 7 - clears Armadillo's str 5
    put(s, "1,2", "lion", "A")
    put(s, "3,2", "armadillo", "B")                      # str 5 but Immovable
    rules.apply_action(s, PlaceAction("gray_wolf", ("cr", "2,2")))
    assert s.owner_of("3,2") == "B"


def test_snow_leopard_lets_other_cats_cover_equal_strength():
    s = make_state(hands={"A": ["caracal"]})
    put(s, "1,2", "snow_leopard", "A")                   # connects 2,2; the anthem source
    put(s, "2,2", "caracal", "B")                        # enemy str 4
    assert PlaceAction("caracal", ("cr", "2,2")) in rules.legal_actions(s)  # 4 >= 4


def test_cougar_places_adjacent_to_a_cat_ignoring_connection():
    s = make_state(hands={"A": ["cougar"]})
    put(s, "3,3", "lion", "A")                           # a Cat, disconnected from HQ
    assert "3,2" in place_targets(s)                     # a neighbour of the Cat


def test_black_panther_untargetable_by_enemy_effect():
    s = make_state(current="B", hands={"B": ["gray_wolf"]})
    hand_inst(s, "B", "gray_wolf").strength_counter = 3  # body 7
    put(s, "4,3", "caracal", "B")                        # B front connects 3,3
    put(s, "3,2", "black_panther", "A")                  # str 6, adjacent to 3,3
    rules.apply_action(s, PlaceAction("gray_wolf", ("cr", "3,3")))
    assert s.owner_of("3,2") == "A"                      # untargetable -> survives


# =============================================================== shared (kept from M2a)

def test_gale_returns_first_enemy_coverer_then_stops_reacting():
    s = make_state(current="A", hands={"A": ["lion"]})
    put(s, "1,2", "caracal", "A")                        # connects 2,2
    gale = put(s, "2,2", "gale", "B")                    # enemy Gale
    rules.apply_action(s, PlaceAction("lion", ("cr", "2,2")))   # lion (7) covers it
    assert s.owner_of("2,2") == "B"                      # Gale is revealed again on top
    assert "lion" in hand_ids(s, "A") and "lion" not in s.remove_pile  # bounced, not removed
    assert gale.retaliation_used is True

    rules.apply_action(s, PlaceAction("lion", ("cr", "2,2")))   # covers again: charge already used
    assert s.owner_of("2,2") == "A" and "lion" not in hand_ids(s, "A")


def test_gale_does_not_react_to_a_friendly_cover():
    s = make_state(current="A", hands={"A": ["lion"]})
    put(s, "1,2", "caracal", "A")
    gale = put(s, "2,2", "gale", "A")                    # friendly Gale
    rules.apply_action(s, PlaceAction("lion", ("cr", "2,2")))
    assert s.owner_of("2,2") == "A"                      # lion just covers normally
    assert gale.retaliation_used is False


def test_gale_cannot_bounce_an_immovable_coverer():
    s = make_state(current="A", hands={"A": ["armadillo"]})
    put(s, "1,2", "caracal", "A")
    gale = put(s, "2,2", "gale", "B")
    rules.apply_action(s, PlaceAction("armadillo", ("cr", "2,2")))
    assert s.owner_of("2,2") == "A"                      # Immovable resists the bounce
    assert gale.retaliation_used is True                 # but the charge is still consumed


# ===================================================================== clone w/ counters

def test_clone_is_independent_with_strength_counters():
    s = make_state()
    put(s, "1,1", "fox", "A")
    c = s.clone()
    c.board["1,1"][0].strength_counter = 5
    assert s.board["1,1"][0].strength_counter == 0       # original untouched


# ======================================== Stage 2.2: draw / shuffle / remove event engine

def test_eon_gains_on_draw_shuffle_and_remove():
    s = make_state(decks={"A": ["lion", "fox"], "B": []})
    put(s, "1,1", "eon", "A")
    effects.draw_cards(s, "A", 1)
    assert s.food["A"] == CFG.eon_food                   # a draw
    effects.shuffle_back(s, "A", ["rat"])
    assert s.food["A"] == 2 * CFG.eon_food               # a shuffle
    victim = put(s, "2,2", "rat", "B")
    effects._remove_specific(s, "2,2", victim, by_player="A")
    assert s.food["A"] == 3 * CFG.eon_food               # a removal


def test_rattlesnake_gains_strength_per_own_card_shuffled_in_every_zone():
    s = make_state(hands={"A": ["rattlesnake"]},
                   decks={"A": ["rattlesnake"], "B": []})
    buried = put(s, "1,1", "rattlesnake", "A")
    put(s, "1,1", "lion", "A")                        # Rattlesnake is covered/inactive
    effects.shuffle_back(s, "A", ["lion", "fox"])         # two cards = two events
    assert effective_strength(s, buried) == 2
    assert placement_strength(s, hand_inst(s, "A", "rattlesnake")) == 2
    assert card_strength(s, "rattlesnake", "A") == 2       # also applies to the deck copy
    effects.shuffle_back(s, "B", ["mouse"])                # only your shuffles count
    assert card_strength(s, "rattlesnake", "A") == 2


def test_egg_eater_only_fires_on_egg_removal():
    s = make_state()
    put(s, "1,1", "egg_eater", "A")
    rat = put(s, "2,2", "rat", "B")
    effects._remove_specific(s, "2,2", rat, by_player="A")
    assert s.food["A"] == 0                               # not an Egg
    egg = put(s, "3,3", "bird_egg", "B")
    effects._remove_specific(s, "3,3", egg, by_player="A", by_effect=False)
    assert s.food["A"] == CFG.egg_eater_food


def test_jackal_only_fires_on_adjacent_removal():
    s = make_state()
    put(s, "2,2", "jackal", "A")
    near = put(s, "3,2", "rat", "B")                     # adjacent to 2,2
    effects._remove_specific(s, "3,2", near, by_player="A")
    assert s.food["A"] == CFG.jackal_food
    far = put(s, "4,3", "rat", "B")                      # not adjacent to 2,2
    effects._remove_specific(s, "4,3", far, by_player="A")
    assert s.food["A"] == CFG.jackal_food                # unchanged


def test_black_swan_when_drawn_discards_from_opponents_hand_only():
    s = make_state(current="A", decks={"A": ["black_swan"], "B": []})
    s.add_to_hand("A", "lion")
    s.add_to_hand("B", "fox")
    effects.draw_cards(s, "A", 1)                        # draws Black Swan
    assert sorted(hand_ids(s, "A")) == ["black_swan", "lion"]
    assert len(s.hands["B"]) == 0                        # lost its only card
    assert s.remove_pile == ["fox"]


def test_black_swan_hard_cap_fires_once_per_turn():
    s = make_state(current="A")
    s.add_to_hand("B", "fox")
    s.add_to_hand("B", "lion")
    first = UnitInstance("black_swan", "A", s.new_iid())
    s.hands["A"].append(first)
    effects._black_swan_drawn(s, first)
    assert len(s.hands["B"]) == 1                        # first trigger this turn: discards one

    second = UnitInstance("black_swan", "A", s.new_iid())  # a fresh instance (e.g. reshuffled+redrawn)
    s.hands["A"].append(second)
    effects._black_swan_drawn(s, second)
    assert len(s.hands["B"]) == 1                        # capped: no second discard this turn

    s.turn_flags = {}                                    # simulate rules._end_turn's reset
    third = UnitInstance("black_swan", "A", s.new_iid())
    s.hands["A"].append(third)
    effects._black_swan_drawn(s, third)
    assert len(s.hands["B"]) == 0                         # cap reset -> fires again next turn


def test_ember_deathrattle_shuffles_itself_back_to_deck():
    s = make_state(decks={"A": [], "B": []})
    e = put(s, "2,2", "ember", "A")
    effects._remove_specific(s, "2,2", e, by_player="A", by_effect=False)
    assert "ember" not in s.remove_pile                 # relocated out of the pile
    assert "ember" in s.decks["A"]


def test_mouse_draws_a_rodent_at_random():
    s = make_state(hands={"A": ["mouse"]}, decks={"A": ["lion", "squirrel", "eagle"], "B": []})
    rules.apply_action(s, PlaceAction("mouse", ("cr", "1,2")))
    assert "squirrel" in hand_ids(s, "A")               # the only Rodent in the deck
    assert "squirrel" not in s.decks["A"]


def test_fathom_draws_a_legendary():
    s = make_state(hands={"A": ["fathom"]}, decks={"A": ["lion", "eon", "eagle"], "B": []})
    rules.apply_action(s, PlaceAction("fathom", ("cr", "1,2")))
    assert "eon" in hand_ids(s, "A")                    # the only legendary in the deck


def test_bird_egg_schedules_and_hatches_into_two_birds():
    s = make_state(hands={"A": ["bird_egg"]}, decks={"A": ["eagle", "owl", "raven", "lion"], "B": []})
    rules.apply_action(s, PlaceAction("bird_egg", ("cr", "1,2")))
    assert any(x["step"]["op"] == "egg_hatch" for x in s.scheduled)
    egg = s.top_unit("1,2")
    effects._op_egg_hatch(s, {"op": "egg_hatch", "iid": egg.iid, "n": 2, "spec": "tag:Bird"})
    assert s.owner_of("1,2") is None                    # egg removed on hatch
    assert sum(1 for c in hand_ids(s, "A") if "Bird" in CARDS[c].tags) == 2


def test_owl_peeks_draws_one_and_shuffles_the_rest():
    s = make_state(current="A", hands={"A": ["owl"]},
                   decks={"A": ["lion", "fox", "rat", "eagle"], "B": []})
    rules.apply_action(s, PlaceAction("owl", ("cr", "1,2")))
    assert s.pending is not None                        # choose among the top 3
    rules.apply_action(s, ChoiceAction("fox"))
    assert "fox" in hand_ids(s, "A")
    assert sorted(s.decks["A"]) == ["eagle", "lion", "rat"]   # the other two shuffled back


def test_raven_draws_three_then_shuffles_two_cards_from_hand():
    s = make_state(current="A", hands={"A": ["raven"]},
                   decks={"A": ["lion", "fox", "rat", "eagle", "owl"], "B": []})
    rules.apply_action(s, PlaceAction("raven", ("cr", "1,2")))
    assert len(s.hands["A"]) == 3                        # drew 3; must choose 2 to shuffle
    first = s.hands["A"][0]
    rules.apply_action(s, ChoiceAction(first.iid))
    second = s.hands["A"][0]
    rules.apply_action(s, ChoiceAction(second.iid))
    assert len(s.hands["A"]) == 1                        # net +1 card
    assert len(s.decks["A"]) == 4


def test_deck_reveal_choices_are_tagged_from_deck_reveal():
    # Owl/Raven selections are over cards revealed from the hidden deck. The generic
    # `from_deck_reveal` provenance tag is the contract search bots rely on to collapse these
    # noise-in-lookahead choices (bots/turn_search.py); other choices must NOT carry it.
    owl = make_state(current="A", hands={"A": ["owl"]},
                     decks={"A": ["lion", "fox", "rat"], "B": []})
    rules.apply_action(owl, PlaceAction("owl", ("cr", "1,2")))
    assert owl.pending["from_deck_reveal"] is True

    raven = make_state(current="A", hands={"A": ["raven"]},
                       decks={"A": ["lion", "fox", "rat", "eagle"], "B": []})
    rules.apply_action(raven, PlaceAction("raven", ("cr", "1,2")))
    assert raven.pending["from_deck_reveal"] is True


# =================================================== Stage 2.3: Apex Predator (decision D)

def test_apex_eats_a_weaker_enemy_and_occupies():
    s = make_state(hands={"A": ["tiger"]})
    put(s, "1,2", "lion", "A")                          # connects 2,2
    put(s, "2,2", "coyote", "B")                        # enemy str 3 < tiger 7
    rules.apply_action(s, PlaceAction("tiger", ("cr", "2,2")))
    assert s.top_unit("2,2").card_id == "tiger"          # occupies (not stacks)
    assert "coyote" in s.remove_pile                     # the prey was eaten


def test_apex_cannot_land_on_empty_or_capture_hq():
    s = make_state(hands={"A": ["tiger"]})
    for cr in ("1,2", "2,2", "3,2", "4,2"):             # chain to B's front
        put(s, cr, "caracal", "A")
    legal = rules.legal_actions(s)
    assert all(not (a.target == ("cr", "1,1")) for a in legal if a.card_id == "tiger")  # no empty
    assert PlaceAction("tiger", ("hq", "B")) not in legal                                # no HQ


def test_apex_may_eat_its_own_unit():
    eats_own = make_state(hands={"A": ["tiger"]})
    put(eats_own, "1,2", "house_cat", "A")
    rules.apply_action(eats_own, PlaceAction("tiger", ("cr", "1,2")))
    assert eats_own.top_unit("1,2").card_id == "tiger" and "house_cat" in eats_own.remove_pile


def test_apex_covers_but_does_not_eat_an_immovable():
    # Immovable can't be eaten, but the predator may still land on it under normal covering
    # rules (strictly-greater) and simply bury it.
    s = make_state(hands={"A": ["tiger"]})
    put(s, "1,2", "armadillo", "A")                    # own Immovable (str 5)
    assert PlaceAction("tiger", ("cr", "1,2")) in rules.legal_actions(s)
    rules.apply_action(s, PlaceAction("tiger", ("cr", "1,2")))
    assert s.top_unit("1,2").card_id == "tiger"         # tiger on top
    assert s.board["1,2"][0].card_id == "armadillo"    # armadillo buried, not eaten
    assert "armadillo" not in s.remove_pile


def test_apex_covers_but_does_not_eat_an_enemy_untargetable():
    # The reported case: Anaconda (7) vs an enemy Black Panther (6) - can't eat it (enemy
    # Untargetable), but 7 > 6 so it covers/buries it instead of being unplayable there.
    s = make_state(current="A", hands={"A": ["anaconda"]})
    put(s, "1,2", "lion", "A")                          # connects 2,2
    put(s, "2,2", "black_panther", "B")                 # enemy str 6, untargetable
    assert PlaceAction("anaconda", ("cr", "2,2")) in rules.legal_actions(s)
    rules.apply_action(s, PlaceAction("anaconda", ("cr", "2,2")))
    assert s.top_unit("2,2").card_id == "anaconda"      # anaconda on top
    assert s.board["2,2"][0].card_id == "black_panther"  # panther buried, not removed
    assert "black_panther" not in s.remove_pile


def test_apex_destroys_an_egg():
    s = make_state(current="A", hands={"A": ["tiger"]})
    put(s, "1,2", "caracal", "A")
    put(s, "2,2", "bird_egg", "B")
    rules.apply_action(s, PlaceAction("tiger", ("cr", "2,2")))
    assert s.top_unit("2,2").card_id == "tiger" and "bird_egg" in s.remove_pile


# ====================================================== Stage 2.3: "Costs X food" (dec. F)

def test_food_cost_gates_placement_and_is_paid():
    s = make_state(hands={"A": ["elephant"]}, food={"A": 19, "B": 0})
    assert not [a for a in rules.legal_actions(s) if a.card_id == "elephant"]   # 19 < 20
    s.food["A"] = 20
    assert [a for a in rules.legal_actions(s) if a.card_id == "elephant"]       # now affordable
    rules.apply_action(s, PlaceAction("elephant", ("cr", "1,2")))
    assert s.food["A"] == 0                              # 20 paid on placement


# ========================================================= Stage 2.3: Landmarks (dec. C)

def test_fig_tree_is_a_landmark_that_schedules_food_and_cannot_capture_hq():
    s = make_state(hands={"A": ["fig_tree"]})
    rules.apply_action(s, PlaceAction("fig_tree", ("cr", "1,2")))
    assert s.top_unit("1,2").card_id == "fig_tree"
    assert any(x["step"]["op"] == "fig_tree_payout" and x["step"]["amount"] == CFG.fig_tree_food
               for x in s.scheduled)

    hq = make_state(hands={"A": ["fig_tree"]})
    for cr in ("1,2", "2,2", "3,2", "4,2"):
        put(hq, cr, "caracal", "A")
    assert PlaceAction("fig_tree", ("hq", "B")) not in rules.legal_actions(hq)


def test_fig_tree_payoff_fires_normally_if_not_covered():
    s = make_state(hands={"A": ["fig_tree"]})
    rules.apply_action(s, PlaceAction("fig_tree", ("cr", "1,2")))
    fig_tree = s.top_unit("1,2")
    food_before = s.food["A"]
    effects._op_fig_tree_payout(s, {"op": "fig_tree_payout", "iid": fig_tree.iid,
                                    "player": "A", "amount": CFG.fig_tree_food})
    assert s.food["A"] == food_before + CFG.fig_tree_food


def test_fig_tree_payoff_denied_once_covered_off_the_board():
    s = make_state(hands={"A": ["fig_tree"]})
    rules.apply_action(s, PlaceAction("fig_tree", ("cr", "1,2")))
    fig_tree = s.top_unit("1,2")
    food_before = s.food["A"]
    s.board["1,2"] = []                                  # simulate the Fragile removal on cover
    effects._op_fig_tree_payout(s, {"op": "fig_tree_payout", "iid": fig_tree.iid,
                                    "player": "A", "amount": CFG.fig_tree_food})
    assert s.food["A"] == food_before                    # denied: fig_tree is no longer on board


def test_watering_hole_payoff_draws_only_a_strong_unit():
    s = make_state(decks={"A": ["lion", "squirrel", "eagle"], "B": []})  # 7 / 3 / 5
    effects.draw_filtered_random(s, "A", 1, "strength_min:6")
    assert hand_ids(s, "A") == ["lion"]                 # only base strength >= 6


def test_watering_hole_payoff_denied_once_covered_off_the_board():
    s = make_state(hands={"A": ["watering_hole"]}, decks={"A": ["lion"], "B": []})
    rules.apply_action(s, PlaceAction("watering_hole", ("cr", "1,2")))
    wh = s.top_unit("1,2")
    s.board["1,2"] = []                                  # simulate the Fragile removal on cover
    effects._op_watering_hole_payout(s, {"op": "watering_hole_payout", "iid": wh.iid,
                                         "player": "A", "n": 1, "spec": "strength_min:6"})
    assert "lion" not in hand_ids(s, "A")                # denied: landmark is no longer on board


# ====================================== Stage 2.3: extra placements (decision F1) + twins

def test_jerboa_plays_another_unit():
    s = make_state(current="A", hands={"A": ["jerboa", "lion"]})
    rules.apply_action(s, PlaceAction("jerboa", ("cr", "1,2")))
    assert s.pending is not None and s.pending["mode"] == "place"
    rules.apply_action(s, PlaceAction("lion", ("cr", "1,1")))
    assert s.owner_of("1,2") == "A" and s.owner_of("1,1") == "A" and s.hands["A"] == []


def test_house_cat_extra_play_is_gated_on_another_cat():
    with_cat = make_state(current="A", hands={"A": ["house_cat", "lion"]})
    put(with_cat, "1,3", "caracal", "A")                # already control another Cat
    rules.apply_action(with_cat, PlaceAction("house_cat", ("cr", "1,2")))
    assert with_cat.pending is not None                 # may play one more Cat

    no_cat = make_state(current="A", hands={"A": ["house_cat", "lion"]})
    rules.apply_action(no_cat, PlaceAction("house_cat", ("cr", "1,2")))
    assert no_cat.pending is None and "lion" in hand_ids(no_cat, "A")   # no extra play


def test_termite_queen_extra_play_is_optional():
    s = make_state(current="A", hands={"A": ["termite_queen", "worker_ant"]})
    rules.apply_action(s, PlaceAction("termite_queen", ("cr", "1,2")))
    assert s.pending is not None
    rules.apply_action(s, ChoiceAction(SKIP))           # decline the optional extra play
    assert "worker_ant" in hand_ids(s, "A")


def test_prince_leo_plays_the_twin_from_deck():
    s = make_state(current="A", hands={"A": ["prince_leo"]},
                   decks={"A": ["princess_lea", "lion"], "B": []})
    rules.apply_action(s, PlaceAction("prince_leo", ("cr", "1,2")))
    assert s.pending is not None                         # may immediately play Princess Lea
    rules.apply_action(s, PlaceAction("princess_lea", ("cr", "1,1")))
    assert s.top_unit("1,1").card_id == "princess_lea"
    assert "princess_lea" not in s.decks["A"]            # fetched from the deck


# ============================== Stage 2.3: HQ-adjacency draw (F6) + start-of-turn (aurum)

def test_cheetah_draws_when_placed_next_to_enemy_base():
    s = make_state(current="A", hands={"A": ["cheetah"]}, decks={"A": ["lion"], "B": []})
    for cr in ("1,2", "2,2", "3,2"):                    # chain up to B's front column
        put(s, cr, "caracal", "A")
    rules.apply_action(s, PlaceAction("cheetah", ("cr", "4,2")))   # 4,2 is HQ_B's front
    assert len(s.hands["A"]) == 1


def test_aurum_draws_at_the_start_of_its_owners_turn():
    s = make_state(current="A", decks={"A": ["lion", "fox", "rat"], "B": ["lynx", "lynx"]})
    put(s, "1,2", "aurum", "A")
    rules.apply_action(s, DrawAction())                 # A's turn ends
    hand_a = len(s.hands["A"])
    rules.apply_action(s, DrawAction())                 # B's turn ends -> start of A's turn
    assert len(s.hands["A"]) == hand_a + 1              # Aurum drew


# ============================================ Stage 2.4: removal battlecries / reactive

def test_jaguar_and_serval_respect_strength_bounds():
    jag = make_state(hands={"A": ["jaguar"]})
    put(jag, "1,2", "lion", "A")
    put(jag, "3,2", "coyote", "B")                      # str 3 <= 5
    rules.apply_action(jag, PlaceAction("jaguar", ("cr", "2,2")))
    assert jag.owner_of("3,2") is None

    srv = make_state(hands={"A": ["serval"]})
    put(srv, "1,2", "lion", "A")
    put(srv, "3,2", "lion", "B")                        # str 7 >= 6 (Serval's only legal target)
    put(srv, "2,3", "coyote", "B")                      # str 3 < 6: survives
    rules.apply_action(srv, PlaceAction("serval", ("cr", "2,2")))
    assert srv.owner_of("3,2") is None and srv.owner_of("2,3") == "B"


def test_soldier_ant_removal_gated_on_five_colony():
    few = make_state(hands={"A": ["soldier_ant"]})
    put(few, "1,2", "worker_ant", "A")
    put(few, "3,2", "coyote", "B")
    rules.apply_action(few, PlaceAction("soldier_ant", ("cr", "2,2")))   # only 2 Colony
    assert few.owner_of("3,2") == "B"

    many = make_state(hands={"A": ["soldier_ant"]})
    for cr in ("1,1", "1,2", "1,3", "2,1"):
        put(many, cr, "worker_ant", "A")               # 4 + Soldier = 5 Colony
    put(many, "3,2", "coyote", "B")
    rules.apply_action(many, PlaceAction("soldier_ant", ("cr", "2,2")))
    assert many.owner_of("3,2") is None


def test_rhinoceros_aoe_removes_weak_adjacent_enemies():
    s = make_state(hands={"A": ["rhinoceros"]})
    put(s, "1,2", "lion", "A")
    put(s, "3,2", "coyote", "B")                        # 3
    put(s, "2,3", "squirrel", "B")                      # 3
    put(s, "2,1", "lion", "B")                          # 7 (survives)
    rules.apply_action(s, PlaceAction("rhinoceros", ("cr", "2,2")))
    assert s.owner_of("3,2") is None and s.owner_of("2,3") is None and s.owner_of("2,1") == "B"


def test_bulwark_pays_cost_and_clears_all_adjacent_enemies():
    s = make_state(hands={"A": ["bulwark"]}, food={"A": 20, "B": 0})
    put(s, "1,2", "caracal", "A")
    put(s, "3,2", "lion", "B")                          # 7 - removed (uncapped)
    rules.apply_action(s, PlaceAction("bulwark", ("cr", "2,2")))
    assert s.food["A"] == 0 and s.owner_of("3,2") is None


def test_hippopotamus_removes_a_weak_enemy_placed_adjacent():
    s = make_state(current="B", hands={"B": ["coyote"]})
    put(s, "3,2", "hippopotamus", "A")
    put(s, "4,1", "caracal", "B")                       # B front, connects 3,1
    rules.apply_action(s, PlaceAction("coyote", ("cr", "3,1")))  # str 3 <= 3, adjacent to hippo
    assert s.owner_of("3,1") is None


# =================================================== Stage 2.4: hand-cost / sacrifice removal

def test_rat_pays_a_hand_card_to_destroy_any_enemy():
    s = make_state(hands={"A": ["rat", "lion"]})
    put(s, "1,2", "caracal", "A")
    put(s, "3,2", "lion", "B")                          # str 7 - any strength
    rules.apply_action(s, PlaceAction("rat", ("cr", "2,2")))
    rules.apply_action(s, ChoiceAction("3,2"))
    assert s.owner_of("3,2") is None and "lion" in s.remove_pile and s.hands["A"] == []


def test_hornet_saccs_a_spare_copy_to_destroy_an_enemy():
    s = make_state(hands={"A": ["hornet", "hornet"]})
    put(s, "1,2", "caracal", "A")
    put(s, "3,2", "lion", "B")
    rules.apply_action(s, PlaceAction("hornet", ("cr", "2,2")))
    rules.apply_action(s, ChoiceAction("3,2"))
    assert s.owner_of("3,2") is None and s.owner_of("2,2") == "A"   # hornet itself survives
    assert s.remove_pile == ["hornet", "lion"] and hand_ids(s, "A") == []  # spare paid, target killed


def test_hornet_has_no_effect_without_a_spare_copy():
    s = make_state(hands={"A": ["hornet"]})
    put(s, "1,2", "caracal", "A")
    put(s, "3,2", "lion", "B")
    rules.apply_action(s, PlaceAction("hornet", ("cr", "2,2")))
    assert s.pending is None                            # no spare in hand or deck -> no offer
    assert s.owner_of("3,2") == "B"


# ================================================================ Stage 2.4: mass effects

def test_pestis_wipes_an_entire_adjacent_stack():
    s = make_state(hands={"A": ["pestis"]})
    put(s, "1,2", "caracal", "A")
    put(s, "3,2", "lion", "B")                          # bottom
    put(s, "3,2", "coyote", "B")                        # top (same owner stacks freely)
    rules.apply_action(s, PlaceAction("pestis", ("cr", "2,2")))
    rules.apply_action(s, ChoiceAction("3,2"))
    assert s.board.get("3,2") is None
    assert s.remove_pile.count("lion") == 1 and s.remove_pile.count("coyote") == 1


def test_sirocco_bounces_all_adjacent_enemies_to_hand():
    s = make_state(hands={"A": ["sirocco"]})
    put(s, "1,2", "caracal", "A")
    put(s, "3,2", "coyote", "B")
    put(s, "2,3", "fox", "B")
    rules.apply_action(s, PlaceAction("sirocco", ("cr", "2,2")))
    assert s.owner_of("3,2") is None and s.owner_of("2,3") is None
    assert {"coyote", "fox"} <= set(hand_ids(s, "B")) and "coyote" not in s.remove_pile


def test_skunk_bounces_and_locks_the_card():
    s = make_state(current="A", hands={"A": ["skunk"]})
    put(s, "1,2", "caracal", "A")
    put(s, "3,2", "coyote", "B")
    rules.apply_action(s, PlaceAction("skunk", ("cr", "2,2")))
    coyote = next(u for u in s.hands["B"] if u.card_id == "coyote")
    assert coyote.locked_until_turn == 2                # locked through B's next turn
    assert "coyote" not in {a.card_id for a in rules.legal_actions(s) if isinstance(a, PlaceAction)}


def test_lemming_floods_empty_adjacent_crossroads():
    s = make_state(current="A", hands={"A": ["lemming", "lemming", "lemming"]})
    rules.apply_action(s, PlaceAction("lemming", ("cr", "1,2")))
    placed = sum(1 for st in s.board.values() for u in st if u.card_id == "lemming")
    assert placed == 3 and s.hands["A"] == []


def test_lemming_also_pulls_lemmings_from_deck():
    s = make_state(current="A", hands={"A": ["lemming"]},
                    decks={"A": ["lemming", "lemming"], "B": []})
    rules.apply_action(s, PlaceAction("lemming", ("cr", "1,2")))
    placed = sum(1 for st in s.board.values() for u in st if u.card_id == "lemming")
    assert placed == 3 and s.hands["A"] == [] and "lemming" not in s.decks["A"]


# ============================================================= Stage 2.4: team triggers

def test_king_theron_and_queen_adira_combo_on_a_cat_cover():
    s = make_state(current="A", hands={"A": ["lion"]}, decks={"A": ["fox", "rat"], "B": []})
    put(s, "1,1", "king_theron", "A")
    put(s, "1,3", "queen_adira", "A")
    put(s, "1,2", "caracal", "A")                       # connects 2,2
    put(s, "2,2", "coyote", "B")                        # a Cat (lion) will cover this enemy
    rules.apply_action(s, PlaceAction("lion", ("cr", "2,2")))
    assert s.owner_of("2,2") == "A" and "coyote" in s.remove_pile    # Theron removed it
    assert len(s.hands["A"]) == 1                       # Adira drew off the Cat removal


# =============================================== Stage 2.4: food gains / play & food riders

def test_queen_honoria_and_falstaff_riders_stack():
    s = make_state(current="A", hands={"A": ["worker_ant"]})
    put(s, "1,1", "queen_honoria", "A")                 # +5 when you play a Colony unit
    put(s, "1,3", "falstaff", "A")                      # +3 whenever you gain food
    put(s, "1,2", "caracal", "A")
    rules.apply_action(s, PlaceAction("worker_ant", ("cr", "2,2")))
    # Honoria +5 (+3 rider) then Worker Ant +8 (+3 rider) = 19
    assert s.food["A"] == 19


def test_queen_marabunta_scales_with_other_colony():
    s = make_state(hands={"A": ["queen_marabunta"]})
    put(s, "1,1", "worker_ant", "A")
    put(s, "1,3", "worker_bee", "A")
    rules.apply_action(s, PlaceAction("queen_marabunta", ("cr", "1,2")))
    assert s.food["A"] == 2 * CFG.queen_marabunta_per_colony   # two other Colony units


def test_chipmunk_pays_now_and_next_turn():
    s = make_state(current="A", hands={"A": ["chipmunk"]},
                   decks={"A": ["lion"], "B": ["lynx", "lynx"]})
    s.actions_taken_this_turn = s.config.actions_per_turn - 1  # Place ends A's turn
    rules.apply_action(s, PlaceAction("chipmunk", ("cr", "1,2")))
    assert s.food["A"] == CFG.chipmunk_food_now
    s.actions_taken_this_turn = s.config.actions_per_turn - 1  # Draw ends B's turn -> start of A's next
    rules.apply_action(s, DrawAction())                 # B's turn -> start of A's next turn
    assert s.food["A"] == CFG.chipmunk_food_now + CFG.chipmunk_food_later


def test_methuselah_gains_food_at_end_of_turn():
    s = make_state(current="A", decks={"A": ["lion"], "B": ["lynx"]})
    put(s, "1,1", "methuselah", "A")
    s.actions_taken_this_turn = s.config.actions_per_turn - 1
    rules.apply_action(s, DrawAction())
    assert s.food["A"] == CFG.methuselah_food


# ===================================================== Stage 2.4: conditional / delayed / reveal

def test_lynx_draws_only_with_another_cat():
    s = make_state(current="A", hands={"A": ["lynx"]}, decks={"A": ["lion"], "B": []})
    put(s, "1,1", "caracal", "A")                       # another Cat
    rules.apply_action(s, PlaceAction("lynx", ("cr", "1,2")))
    assert len(s.hands["A"]) == 1


def test_black_bear_schedules_a_delayed_draw():
    s = make_state(hands={"A": ["black_bear"]}, decks={"A": ["lion"], "B": []})
    rules.apply_action(s, PlaceAction("black_bear", ("cr", "1,2")))
    sched = [x for x in s.scheduled if x["step"]["op"] == "draw" and x["owner"] == "A"]
    assert sched                                        # a delayed draw was queued
    effects._op_draw(s, sched[0]["step"])               # fire it: pulls from the deck
    assert "lion" in hand_ids(s, "A")


def test_grizzly_bear_strikes_a_random_adjacent_enemy_later():
    s = make_state(hands={"A": ["grizzly_bear"]})
    put(s, "1,2", "caracal", "A")
    rules.apply_action(s, PlaceAction("grizzly_bear", ("cr", "2,2")))
    sched = [x for x in s.scheduled if x["step"]["op"] == "grizzly_strike"]
    assert sched
    put(s, "3,2", "lion", "B")                          # an adjacent enemy to strike
    effects._op_grizzly_strike(s, sched[0]["step"])
    assert s.owner_of("3,2") is None


def test_scrooge_doubles_this_turns_haul():
    # Reworked 2026-07-05: Battlecry gains again whatever you gained this turn (no banking).
    s = make_state(current="A", hands={"A": ["scrooge"]}, food={"A": 20, "B": 0})
    s.turn_flags["food_gained_A"] = 20                  # 20 already gained this turn
    rules.apply_action(s, PlaceAction("scrooge", ("cr", "1,2")))
    assert s.food["A"] == 20 + 20 * CFG.scrooge_gain_multiplier


def test_andean_condor_draws_only_when_its_top_is_stronger():
    win = make_state(hands={"A": ["andean_condor"]}, decks={"A": ["lion"], "B": ["coyote"]})
    rules.apply_action(win, PlaceAction("andean_condor", ("cr", "1,2")))
    assert "lion" in hand_ids(win, "A")

    lose = make_state(hands={"A": ["andean_condor"]}, decks={"A": ["coyote"], "B": ["lion"]})
    rules.apply_action(lose, PlaceAction("andean_condor", ("cr", "1,2")))
    assert lose.hands["A"] == []


def test_oxpecker_counts_strong_units_in_the_starting_deck():
    s = make_state(hands={"A": ["oxpecker"]})
    s.starting_decks["A"] = ("lion", "lion", "squirrel", "eagle", "goliath")  # 7,7 qualify; 3,5,dyn don't
    rules.apply_action(s, PlaceAction("oxpecker", ("cr", "1,2")))
    assert s.food["A"] == 2
