"""The First of Many (Martin, 2026-10-22): "Roar: cover the board with Locusts." Each Locust is Wild, no one's, with
"In 2 turns, remove this and the animal under it": the opponent's turn, then the caster's, since a Wild animal's timer
ticks every turn (keywords.md, Wild)."""
from __future__ import annotations

from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import PassAction, PlaceAction
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.state import WILD

from ._helpers import make_state, put

CFG = Config.default()


def end_turn(s):
    s.idle_turns = 0
    rules.apply_action(s, PassAction())


def swarm(**kw):
    """A's turn: the legendary lands on 1,2 and covers the board."""
    s = make_state(hands={"A": ["locust_legend", "lion"], "B": ["lion", "tiger"]},
                   decks={"A": ["lion"] * 9, "B": ["lion"] * 9}, **kw)
    return s


def test_the_roar_covers_every_crossroad_with_a_wild_locust_the_legendary_included():
    s = swarm()
    lion = put(s, "2,2", "lion", "B")
    rules.apply_action(s, PlaceAction("locust_legend", ("cr", "1,2")))
    assert all(s.board[c][-1].card_id == "locust_swarm" and s.board[c][-1].owner == WILD for c in s.game_map.crossroads)
    assert s.board["2,2"][-2] is lion and s.board["1,2"][-2].card_id == "locust_legend"
    assert s.owner_of("2,2") == WILD


def test_the_swarm_eats_at_the_start_of_the_casters_next_turn_and_what_was_buried_comes_back():
    s = swarm()
    buried = put(s, "2,2", "fox", "B")
    put(s, "2,2", "lion", "B")
    rules.apply_action(s, PlaceAction("locust_legend", ("cr", "1,2")))
    end_turn(s)                                              # A's turn ends: nothing eaten yet
    assert s.board["2,2"][-1].card_id == "locust_swarm"
    end_turn(s)                                              # B's whole turn passes; A's Dawn: the swarm eats
    assert s.current == "A"
    assert s.board["2,2"] == [buried]                        # the Locust and the Lion went, the Fox resurfaced
    assert "1,2" not in s.board                              # the legendary went with its swarm
    assert not any(u.card_id == "locust_swarm" for st in s.board.values() for u in st)


def test_covering_a_locust_spares_that_crossroad():
    s = swarm()
    lion = put(s, "2,2", "lion", "B")
    rules.apply_action(s, PlaceAction("locust_legend", ("cr", "1,2")))
    end_turn(s)
    cover = next(u for u in s.hands["B"] if u.card_id == "lion")
    front = sorted(s.game_map.hq_front("B"))[0]              # B can still place next to its den
    rules.apply_action(s, PlaceAction("lion", ("cr", front)))
    assert s.board[front][-1] is cover                       # any animal covers a Wild 0
    end_turn(s)
    assert s.board[front][-1] is cover and s.board[front][-2].card_id == "locust_swarm"   # buried: it waits
    assert lion not in s.board.get("2,2", [])                # the uncovered one ate


def test_an_apex_predator_on_a_locust_eats_it_and_sits_on_the_animal_beneath():
    s = swarm()
    front = sorted(s.game_map.hq_front("B"))[0]
    mouse = put(s, front, "mouse", "B")
    rules.apply_action(s, PlaceAction("locust_legend", ("cr", "1,2")))
    end_turn(s)
    rules.apply_action(s, PlaceAction("tiger", ("cr", front)))   # any Apex: it covers, then eats what it covered
    assert [u.card_id for u in s.board[front]] == ["mouse", "tiger"] and s.board[front][0] is mouse


def test_a_wild_animal_connects_no_one_and_holds_no_region():
    s = swarm()
    spot = sorted(s.game_map.hq_front("A"))[0]
    for c in s.game_map.crossroads - {spot}:
        put(s, c, "lion", "B")                               # B holds everything but one crossroad by A's den
    assert rules.regions_controlled(s, "B")
    rules.apply_action(s, PlaceAction("locust_legend", ("cr", spot)))
    assert not rules.regions_controlled(s, "A") and not rules.regions_controlled(s, "B")
    assert not s.connected_occupied("A") and not s.connected_occupied("B")
