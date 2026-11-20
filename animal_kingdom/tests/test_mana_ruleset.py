"""The mana ruleset (the prototype Martin asked for on 2026-11-20): mana instead of actions, card costs, no Draw action,
hands of 3 and 4, the map_hex19 board with its bases, no den capture, and the three text readings (Beaver, Cheetah,
Falcon). The default ruleset stays exactly as it was (the last tests here, and the rest of the suite)."""

import json
import random
from itertools import combinations

import pytest

from animal_kingdom.decks import deck_problems, load_premade_deck
from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import (SKIP, ActAction, ChoiceAction, DrawAction, LeaderAction, PassAction,
                                           PlaceAction, RoamAction)
from animal_kingdom.engine.cards import load_cards
from animal_kingdom.engine.config import RULESET_TEXT, RULESETS, Config
from animal_kingdom.engine.leaders import leader_state
from animal_kingdom.engine.maps import load_map
from animal_kingdom.engine.state import EngineError, GameState, UnitInstance, new_game
from animal_kingdom.web.match import Match, Seat

CARDS = load_cards()
MANA = Config.default().for_ruleset("mana")
HEX19 = load_map("map_hex19")
BASE = {"A": {"1,1", "1,2", "1,3"}, "B": {"5,1", "5,2", "5,3"}}


def state(*, turn=0, current="A", hands=None, decks=None, food=None) -> GameState:
    """A bare mana position on map_hex19: turn_counter `turn` (A's Nth own turn is turn 2N-2), nothing pending."""
    s = GameState(HEX19, CARDS, MANA, board={}, hands={"A": [], "B": []},
                  decks={p: list((decks or {}).get(p, ["squirrel"] * 5)) for p in "AB"},
                  remove_pile=[], food=food or {"A": 0, "B": 0}, current=current, first_player="A", turn_counter=turn)
    for p, ids in (hands or {}).items():
        for cid in ids:
            s.add_to_hand(p, cid)
    return s


def put(s, cr, cid, owner):
    u = UnitInstance(cid, owner, s.new_iid(), placed_on_turn=s.turn_counter - 2)
    s.stamp_played(u)
    s.board.setdefault(cr, []).append(u)
    return u


def places(s, cid=None):
    return {a.target[1] for a in rules.legal_actions(s)
            if isinstance(a, PlaceAction) and (cid is None or a.card_id == cid) and a.target[0] == "cr"}


def resolve_choices(s, rng=None):
    """Answer whatever is pending with its first option (or skip), until nothing is."""
    while s.pending is not None and s.result is None:
        legal = rules.legal_actions(s)
        rules.apply_action(s, (rng.choice(legal) if rng else legal[0]))


# ------------------------------------------------------------------ mana

def test_mana_grows_one_a_turn_to_six_for_both_players():
    s = state()
    for turn in range(16):
        s.turn_counter, s.current = turn, "AB"[turn % 2]
        assert rules.mana_total(s, s.current) == min(turn // 2 + 1, 6)
        assert rules.turn_actions(s) == min(turn // 2 + 1, 6)


def test_unspent_mana_is_lost_and_a_real_game_counts_its_turns():
    s = new_game(load_premade_deck("pool_1"), load_premade_deck("pool_3"), 7, map_id="map_hex19", config=MANA,
                 first_player="A")
    resolve_choices(s)                                       # both keep
    seen = []
    while len(seen) < 14 and s.result is None:
        seen.append((s.turn_counter, s.current, rules.mana_total(s, s.current), rules.mana_left(s, s.current)))
        turn = s.turn_counter
        cheap = [a for a in rules.legal_actions(s) if isinstance(a, PlaceAction)]
        if cheap:                                            # spend one card's worth, leave the rest unspent
            rules.apply_action(s, min(cheap, key=lambda a: (CARDS[a.card_id].cost, a.card_id, a.target)))
            resolve_choices(s)
        if s.result is None and s.turn_counter == turn:
            rules.apply_action(s, PassAction())
    assert len(seen) == 14 and s.result is None             # turns the mana couldn't pay for are skipped, not passed
    for turn, p, total, left in seen:                        # each turn opens with its full mana, never last turn's rest
        assert p == "AB"[turn % 2] and total == left == min(turn // 2 + 1, 6)


def test_a_skipped_turn_says_so_on_its_end_and_a_turn_ended_by_hand_does_not():
    """The client shows a skipped turn only from the server's word: `skipped` on the turn's turn_end event."""
    s = state(hands={"A": ["lion"], "B": ["lion"]}, decks={"A": ["lion"] * 5, "B": ["lion"] * 5})   # lions cost 3
    rules.apply_action(s, PassAction())                      # A ends their first turn by hand, nothing played
    assert s.current == "A" and s.turn_counter == 4          # B's 1 and A's 2 and B's 2 mana paid for nothing: skipped
    ends = [e for e in s.events if e["e"] == "turn_end"]
    assert [(e["player"], bool(e.get("skipped"))) for e in ends] == [("A", False), ("B", True), ("A", True), ("B", True)]
    assert all(e.get("skipped") is None for e in new_game(load_premade_deck("pool_1"), load_premade_deck("pool_3"), 7).events)


def test_a_card_costs_its_mana_and_a_card_the_mana_left_cannot_pay_is_refused():
    s = state(turn=4, hands={"A": ["lion", "squirrel", "kitten"]})   # A's third turn: 3 mana
    assert CARDS["lion"].cost == 3 and CARDS["squirrel"].cost == 1
    assert places(s, "lion") == BASE["A"]
    rules.apply_action(s, PlaceAction("squirrel", ("cr", "1,2")))
    assert rules.mana_left(s, "A") == 2
    assert not places(s, "lion")                                   # 2 left: the Lion is not offered...
    with pytest.raises(EngineError):                               # ...and refused
        rules.apply_action(s, PlaceAction("lion", ("cr", "1,1")))


def test_the_turn_ends_when_nothing_can_be_paid():
    s = state(turn=2, hands={"A": ["kitten", "lion"]}, decks={"A": ["lion"] * 3, "B": ["squirrel"] * 3})
    rules.apply_action(s, PlaceAction("kitten", ("cr", "1,2")))    # 2 mana: the Kitten (1) draws a Lion; 1 left, no Lion
    resolve_choices(s)
    assert s.turn_counter == 3 and s.current == "B"                # nothing payable is left: the turn ended


def test_echo_costs_three_mana():
    s = state(turn=4)
    put(s, "1,1", "chipmunk", "A")
    assert ActAction("1,1") in rules.legal_actions(s)
    rules.apply_action(s, ActAction("1,1"))
    resolve_choices(s)
    assert s.food["A"] == 10
    s = state(turn=2)                                              # 2 mana: no Echo
    put(s, "1,1", "chipmunk", "A")
    assert ActAction("1,1") not in rules.legal_actions(s)
    with pytest.raises(EngineError):
        rules.apply_action(s, ActAction("1,1"))


def test_a_roam_costs_three_mana():
    s = state(turn=6, hands={"A": ["kitten"]})                     # 4 mana
    put(s, "1,1", "wolf", "A")
    roams = [a for a in rules.legal_actions(s) if isinstance(a, RoamAction)]
    assert roams
    rules.apply_action(s, roams[0])
    assert rules.mana_left(s, "A") == 1
    assert not any(isinstance(a, RoamAction) for a in rules.legal_actions(s))
    s = state(turn=2, hands={"A": ["kitten"]})                     # 2 mana: no roam
    put(s, "1,1", "wolf", "A")
    assert not any(isinstance(a, RoamAction) for a in rules.legal_actions(s))
    with pytest.raises(EngineError):
        rules.apply_action(s, RoamAction("1,1", ("cr", "2,1")))


def test_a_leader_power_costs_three_mana_and_keeps_its_rules():
    s = state(turn=4)
    s.leaders["A"] = leader_state("raven_legend")                  # Grimm: "Draw 2 animals."
    assert LeaderAction() in rules.legal_actions(s)
    rules.apply_action(s, LeaderAction())
    resolve_choices(s)
    assert len(s.hands["A"]) == 2
    s = state(turn=2)
    s.leaders["A"] = leader_state("raven_legend")
    assert LeaderAction() not in rules.legal_actions(s)
    with pytest.raises(EngineError):
        rules.apply_action(s, LeaderAction())


def test_what_an_effect_puts_into_play_is_free():
    s = state(turn=10, hands={"A": ["mole", "lion", "squirrel"]})  # 6 mana; the Mole costs 5, the Lion 3
    put(s, "1,2", "squirrel", "A")
    rules.apply_action(s, PlaceAction("mole", ("cr", "2,2")))
    assert s.pending is not None and s.pending["mode"] == "place"   # "play another animal next to this"
    lion = next(a for a in rules.legal_actions(s) if isinstance(a, PlaceAction) and a.card_id == "lion")
    rules.apply_action(s, lion)
    resolve_choices(s)
    assert s.top_unit(lion.target[1]).card_id == "lion"
    assert s.current == "A" and rules.mana_left(s, "A") == 1       # only the Mole was paid for


def test_opening_hands_are_three_and_four_and_the_mulligan_follows_them():
    for first in "AB":
        s = new_game(load_premade_deck("pool_1"), load_premade_deck("pool_2"), 3, map_id="map_hex19", config=MANA,
                     first_player=first)
        second = "B" if first == "A" else "A"
        assert len(s.hands[first]) == 3 and len(s.hands[second]) == 4
        assert MANA.mulligan_cap(first, first) == 3 and MANA.mulligan_cap(second, first) == 4


def test_there_is_no_draw_action_and_the_turn_card_still_comes():
    s = state(turn=4, hands={"A": ["lion"]})
    assert not any(isinstance(a, DrawAction) for a in rules.legal_actions(s))
    with pytest.raises(EngineError):
        rules.apply_action(s, DrawAction())
    before = len(s.hands["B"])
    rules.apply_action(s, PassAction())
    assert s.current == "B" and len(s.hands["B"]) == before + 1


# ------------------------------------------------------------------ the board: bases and connection

def test_the_board_is_nineteen_tiles_in_rows_of_three_four_five_four_three():
    rows = {}
    for cr in HEX19.crossroads:
        r, c = map(int, cr.split(","))
        rows.setdefault(r, []).append(c)
    assert {r: len(cs) for r, cs in rows.items()} == {1: 3, 2: 4, 3: 5, 4: 4, 5: 3}
    assert HEX19.bases == {p: frozenset(t) for p, t in BASE.items()}
    assert set(HEX19.hq_front("A")) == BASE["A"] and set(HEX19.hq_front("B")) == BASE["B"]
    assert len(HEX19.neighbors("3,3")) == 6                       # the middle tile touches six


def test_connection_starts_from_the_base():
    s = state(turn=4, hands={"A": ["lion"]})
    assert places(s, "lion") == BASE["A"]                         # an empty board: the base, nothing else
    put(s, "1,2", "squirrel", "A")
    assert places(s, "lion") == BASE["A"] | {"2,2", "2,3"}
    put(s, "3,3", "squirrel", "A")                               # cut off from the base: it connects nothing
    assert places(s, "lion") == BASE["A"] | {"2,2", "2,3"}


def _b_chain(s):
    for cr in ("5,2", "4,2", "3,2", "2,1"):                       # B's animals, connected from B's base to A's
        put(s, cr, "squirrel", "B")


def test_no_card_of_the_opponent_lands_on_a_base_from_hand():
    s = state(turn=11, current="B", hands={"B": ["lion", "tiger"]})
    put(s, "1,1", "mongoose", "A")                                # a 1 the Lion would cover anywhere else
    _b_chain(s)
    assert not places(s) & BASE["A"]
    assert "2,2" in places(s, "lion")
    with pytest.raises(EngineError):
        rules.apply_action(s, PlaceAction("lion", ("cr", "1,2")))
    with pytest.raises(EngineError):
        rules.apply_action(s, PlaceAction("tiger", ("cr", "1,1")))   # nor an Apex Predator onto an animal there


def test_flight_and_reach_never_land_on_the_opponents_base():
    s = state(turn=11, current="B", hands={"B": ["pigeon", "caracal", "eagle"]})
    put(s, "1,1", "mongoose", "A")
    for cr in ("5,2", "4,2", "3,2"):
        put(s, cr, "squirrel", "B")
    assert places(s, "pigeon") == set(HEX19.crossroads) - BASE["A"] - {"5,2", "4,2", "3,2"} | {"5,2", "4,2", "3,2"}
    assert "2,1" in places(s, "caracal") and not places(s, "caracal") & BASE["A"]   # Reach jumps two, never onto it
    assert not places(s, "eagle") & BASE["A"]                     # a flying Apex can't eat what stands there


def test_a_roam_never_lands_on_the_opponents_base():
    s = state(turn=11, current="B")
    _b_chain(s)
    put(s, "2,2", "wolf", "B")                                    # next to A's 1,2 and 1,3
    targets = {a.target[1] for a in rules.legal_actions(s) if isinstance(a, RoamAction) and a.origin == "2,2"}
    assert targets and not targets & BASE["A"]
    assert not any(a.target[0] == "hq" for a in rules.legal_actions(s) if isinstance(a, RoamAction))


def test_an_effect_never_puts_an_animal_on_the_opponents_base():
    s = state(turn=11, current="B", hands={"B": ["mole", "lion"]})
    _b_chain(s)
    rules.apply_action(s, PlaceAction("mole", ("cr", "2,2")))     # "play another animal next to this"
    extra = {a.target[1] for a in rules.legal_actions(s) if isinstance(a, PlaceAction)}
    assert extra and not extra & BASE["A"]
    s = state(turn=11, current="B", hands={"B": ["sardine", "sardine"]}, decks={"B": ["sardine"] * 2})
    _b_chain(s)
    rules.apply_action(s, PlaceAction("sardine", ("cr", "2,2")))  # fills its empty neighbours, the base's excepted
    resolve_choices(s)
    assert any(s.top_unit(cr) and s.top_unit(cr).card_id == "sardine" for cr in ("2,3", "3,3"))
    assert not any(s.top_unit(cr) for cr in BASE["A"])


def test_effects_reach_across_the_base_line():
    s = state(turn=11, current="B", hands={"B": ["weasel"]})       # Weasel: "Roar: Bite 3."
    _b_chain(s)
    put(s, "1,1", "mongoose", "A")
    rules.apply_action(s, PlaceAction("weasel", ("cr", "2,2")))
    assert s.top_unit("2,2").card_id == "weasel"
    s2 = state(turn=11, current="B", hands={"B": ["weasel"]})
    _b_chain(s2)
    put(s2, "1,2", "mongoose", "A")
    rules.apply_action(s2, PlaceAction("weasel", ("cr", "2,2")))  # 1,2 is next to 2,2: the Bite takes it
    resolve_choices(s2)
    assert s2.top_unit("1,2") is None


# ------------------------------------------------------------------ regions, the den, food

def test_twenty_four_regions_of_three_mutually_adjacent_tiles():
    regs = list(HEX19.regions.values())
    assert len(regs) == 24 and all(r.food == 5 for r in regs)
    triangles = {frozenset(t) for t in combinations(sorted(HEX19.crossroads), 3)
                 if all(HEX19.adjacent(a, b) for a, b in combinations(t, 2))}
    assert {frozenset(r.corners) for r in regs} == triangles
    for p in "AB":
        touching = [r for r in regs if set(r.corners) & BASE[p]]
        assert len(touching) == 5
        # the opponent never holds one, and breaks it by taking its second-row tile
        assert all(set(r.corners) - BASE[p] for r in touching)


def test_region_owners_and_income():
    s = state(turn=4)
    for cr in HEX19.crossroads:
        put(s, cr, "squirrel", "A")
    assert len(rules.regions_controlled(s, "A")) == 24 and rules.region_income(s, "A") == 120
    s = state(turn=4)
    for cr in ("1,1", "1,2", "2,2"):
        put(s, cr, "squirrel", "A")
    for cr in ("4,3", "5,2", "5,3"):
        put(s, cr, "squirrel", "B")
    assert [set(r.corners) for r in rules.regions_controlled(s, "A")] == [{"1,1", "1,2", "2,2"}]
    assert [set(r.corners) for r in rules.regions_controlled(s, "B")] == [{"4,3", "5,2", "5,3"}]


def test_no_animal_enters_or_captures_a_den():
    s = state(turn=11, current="B", hands={"B": ["lion", "kitten"]})
    _b_chain(s)
    put(s, "1,1", "wolf", "B")                                    # put there by hand (no rule puts it there): its pack
    for a in rules.legal_actions(s):                              # stands on A's den front, as a capture would need
        assert not (isinstance(a, (PlaceAction, RoamAction)) and a.target[0] == "hq")
    rng = random.Random(1)
    for seed in range(20):                                        # and no game ends on a den
        r = _random_game(seed)
        assert r.result is None or r.result.reason != "hq_capture"


def test_reaching_one_hundred_food_wins():
    s = state(turn=4, food={"A": 95, "B": 0})
    for cr in ("1,1", "1,2", "2,2"):
        put(s, cr, "squirrel", "A")
    rules.apply_action(s, PassAction())
    assert s.result is not None and s.result.winner == "A" and s.result.reason == "food"


# ------------------------------------------------------------------ decks

def test_deck_rules_in_the_mana_ruleset():
    costed = sorted(c.id for c in CARDS.values() if c.collectible and c.cost is not None and c.rarity != "legendary")
    deck = ["mole_legend"] + [cid for cid in costed for _ in range(2)][:24]
    assert deck_problems(deck, "mole_legend", ruleset="mana") == []
    big = ["mole_legend", "honey_badger_legend", "gorilla_legend_2", "tiger_legend", "lion_legend_3", "lion_legend_4",
           "baboon_legend", "chameleon_legend", "raven_legend", "squirrel_legend", "macaque_legend", "butterfly_legend"]
    stars = big + [cid for cid in costed for _ in range(2)][:13]
    assert deck_problems(stars, "mole_legend", ruleset="mana") == []       # no star budget...
    assert any("stars" in p for p in deck_problems(stars, "mole_legend"))  # ...which the default ruleset keeps
    assert deck_problems(deck[:24], "mole_legend", ruleset="mana")         # 25 cards exactly
    assert deck_problems(deck[:-1] + [deck[1]], "mole_legend", ruleset="mana")   # at most 2 of an animal
    assert deck_problems(deck[:-1] + ["mole_legend"], "mole_legend", ruleset="mana")   # 1 of a legendary
    reserve = next(c.id for c in CARDS.values() if c.cost is None and c.status != "planned")
    assert deck_problems(deck[:-1] + [reserve], "mole_legend", ruleset="mana")   # no cost: not in a mana deck
    assert all(CARDS[c].cost is not None for c in CARDS if CARDS[c].collectible)   # every collectible card has one


# ------------------------------------------------------------------ the three readings

def test_beaver_next_turn_three_more_mana():
    s = state(turn=6, hands={"A": ["beaver"]}, decks={"A": ["squirrel"] * 5, "B": []})   # 4 mana, the Beaver costs 4
    put(s, "1,2", "squirrel", "A")
    rules.apply_action(s, PlaceAction("beaver", ("cr", "1,1")))
    resolve_choices(s)
    if s.current == "A":
        rules.apply_action(s, PassAction())
    if s.current == "B":
        rules.apply_action(s, PassAction())
    assert s.current == "A" and s.turn_counter == 8
    assert rules.mana_total(s, "A") == 5 + 3


def test_cheetah_and_falcon_draw_next_to_the_opponents_base():
    def cheetah_at(cr):
        s = state(turn=11, current="A", hands={"A": ["cheetah"]}, decks={"A": ["squirrel"] * 5, "B": ["squirrel"] * 5})
        for c in ("1,2", "2,2", "3,2"):
            put(s, c, "squirrel", "A")
        rules.apply_action(s, PlaceAction("cheetah", ("cr", cr)))
        resolve_choices(s)
        return len(s.hands["A"])
    assert HEX19.next_to_base("B", "4,1") and not HEX19.next_to_base("B", "3,3")
    assert cheetah_at("4,1") == 2 and cheetah_at("3,3") == 0
    for cr, drawn in (("4,4", 1), ("3,5", 0)):
        s = state(turn=11, current="A", hands={"A": ["falcon"]})
        rules.apply_action(s, PlaceAction("falcon", ("cr", cr)))    # Flight: anywhere but B's base
        resolve_choices(s)
        assert len(s.hands["A"]) == drawn


def test_the_readings_have_their_own_text_and_the_stored_text_stays():
    assert set(RULESET_TEXT["mana"]) == {"beaver", "cheetah", "falcon"}
    assert "base" in RULESET_TEXT["mana"]["cheetah"] and "3 more mana" in RULESET_TEXT["mana"]["beaver"]
    assert "den" in CARDS["cheetah"].text and "action" in CARDS["beaver"].text


# ------------------------------------------------------------------ the match, the log, the replay

def _random_game(seed: int) -> GameState:
    rng = random.Random(seed)
    s = new_game(load_premade_deck("pool_1"), load_premade_deck("pool_5"), seed, map_id="map_hex19", config=MANA,
                 leaders={"A": "lion_legend_4", "B": "gorilla_legend_2"})
    for _ in range(3000):
        if rules.is_terminal(s):
            break
        rules.apply_action(s, rng.choice(rules.legal_actions(s)))
    return s


def _mana_match() -> Match:
    m = Match("MANA01", Seat("ta", "Ann", deck="pool_1"))
    m.set_ruleset("mana")
    m.join(Seat("tb", "Bob", deck="pool_3"))
    return m


def test_a_mana_match_plays_to_its_end_logs_its_ruleset_and_replays():
    m = _mana_match()
    assert m.map_id == "map_hex19" and m.state.config.mana and not m.state.config.draw_action
    rng = random.Random(2)
    while m.phase == "playing":
        s = m.to_act()
        v = m.view(s)["game"]
        assert v["mana"][m.state.current]["left"] == rules.mana_left(m.state, m.state.current)
        m.act(s, rng.choice(rules.legal_actions(m.state)).to_dict())
    log = m.game_log()
    assert log["ruleset"] == "mana" and log["draw_action"] is False
    cfg = Config.default().for_log(json.loads(json.dumps(log)))
    assert cfg.mana and cfg.first_player_opening_draw == 3 and cfg.second_player_opening_draw == 4
    from animal_kingdom.sim.replay import replay
    steps, result, _ = replay(log)
    assert len(steps) == len(log["actions"]) and result == m.state.result
    s = new_game(log["lists"][0], log["lists"][1], log["seed"], map_id=log["map_id"], config=cfg,
                 first_player=log["first_player"], leaders=log.get("leaders"))
    for a in log["actions"]:
        rules.apply_logged(s, a)
    assert s.food == m.state.food and (rules.is_terminal(s) or s.result) == m.state.result


def test_a_mana_match_survives_a_restart():
    m = _mana_match()
    back = Match.from_dict(json.loads(json.dumps(m.to_dict())))
    assert back.ruleset == "mana" and back.state.config.mana and back.map_id == "map_hex19"


def test_a_mana_match_against_the_bot_plays_to_the_end():
    """The simple Python greedy bot plays the mana rules, whatever level is asked (the Rust bots know only the default)."""
    m = Match("MANA02", Seat("ta", "Ann", deck="pool_1"))
    m.set_ruleset("mana")
    m.join(Seat("tb", "Bot", bot="easy", deck="pool_3"))
    m.ready("A")
    if m.state is None:
        m.ready("B")
    for _ in range(2000):
        if m.state.result is not None:
            break
        s = m.to_act()
        m.act(s, (m.bot_move() if m.seats[s].is_bot else rules.legal_actions(m.state)[0]).to_dict())
    assert m.state.result is not None and m.state.config.mana


def test_the_view_carries_mana_costs_and_the_board():
    m = _mana_match()
    while m.mulliganing():
        for p in "AB":
            if rules.early_mulligan(m.state, p) is not None or m.to_act() == p:
                m.act(p, ChoiceAction(SKIP).to_dict())
                break
    s = m.to_act()
    v = m.view(s)
    g = v["game"]
    assert v["ruleset"] == "mana" and set(v["texts"]) == {"beaver", "cheetah", "falcon"} and "Echo" in v["keywords"]
    n = min(m.state.turn_counter // 2 + 1, 6)                     # an opening turn with nothing payable is skipped
    assert g["mana"][s] == {"left": n, "total": n} and g["abilityCost"] == 3
    assert {p: set(t) for p, t in g["bases"].items()} == BASE
    assert all({"cost", "affordable"} <= set(h) for h in g["hand"])
    assert all(h["affordable"] == (h["cost"] <= n) for h in g["hand"])
    assert g["legal"]["draw"] is False and "freeRoam" in g["legal"]


# ------------------------------------------------------------------ the default ruleset is untouched

def test_the_default_ruleset_is_unchanged():
    d = Config.default()
    assert not d.mana and d.draw_action and d.ruleset == "default" and RULESETS["default"] == {}
    assert d.first_player_opening_draw == 4 and d.second_player_opening_draw == 4
    assert not d.for_log({"first_turn_actions": 1, "first_player_opening_draw": 4}).mana
    for mid in ("map_a", "map_b", "map_hex"):
        assert load_map(mid).bases == {} and load_map(mid).closed_to("A") == frozenset()
    s = new_game(load_premade_deck("pool_1"), load_premade_deck("pool_2"), 3, map_id="map_hex", first_player="A")
    assert len(s.hands["A"]) == 4 and len(s.hands["B"]) == 4
    resolve_choices(s)
    assert rules.turn_actions(s) == 1 and any(isinstance(a, DrawAction) for a in rules.legal_actions(s))
    m = Match("PLAIN1", Seat("ta", "Ann", deck="pool_1"))
    m.join(Seat("tb", "Bob", deck="pool_3"))
    assert m.ruleset == "default" and "ruleset" not in m.state.config.__dict__.get("_x", {}) and not m.state.config.mana
    assert "mana" not in m.view("A")["game"]
