"""Where a unit's strength comes from: its base, its own growth raising the base, and each buff or loss with the card that
gave it (Martin, 2026-11-05: as Hearthstone shows a card's buffs). The Roach King comes back at its printed strength plus
1 for every fall; what other cards gave it or took from it is gone."""

from __future__ import annotations

import random

from animal_kingdom.engine import effects, rules
from animal_kingdom.engine.actions import PlaceAction
from animal_kingdom.engine.cards import load_cards
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.state import GameState, new_game
from animal_kingdom.engine.strength import effective_strength, raw_strength, strength_breakdown

from ._helpers import apply_click, make_state, put

CFG = Config.default()


def _grant(s, unit, n, source):
    s.cause = source
    effects._op_grant_strength(s, {"amount": n, "iids": [unit.iid]})
    s.cause = None


def _fall(s, cr):
    effects.remove_top(s, cr, by_player="A")
    effects.resolve(s)
    return s.top_unit(cr)


def test_a_buffed_roach_king_comes_back_at_its_printed_strength_plus_one():
    s = make_state(decks={"A": [], "B": ["lion"] * 3})
    king = put(s, "2,1", "cockroach_legend", "B")              # printed 1
    _grant(s, king, 2, "dingo")
    assert effective_strength(s, king) == 3
    back = _fall(s, "2,1")
    assert back.card_id == "cockroach_legend" and effective_strength(s, back) == 1 + CFG.cockroach_legend_growth


def test_a_roach_king_fallen_once_then_bitten_below_0_comes_back_with_both_falls():
    s = make_state(hands={"A": ["viper"]}, decks={"A": [], "B": ["lion"] * 3})
    put(s, "2,1", "cockroach_legend", "B")
    once = _fall(s, "2,1")
    assert effective_strength(s, once) == 2
    apply_click(s, PlaceAction("viper", ("cr", "1,1")))        # 2 -> -1: it falls again
    back = s.top_unit("2,1")
    assert back.card_id == "cockroach_legend" and effective_strength(s, back) == 1 + 2 * CFG.cockroach_legend_growth


def test_a_cockroach_comes_back_fresh():
    s = make_state()
    roach = put(s, "2,1", "cockroach", "B")
    _grant(s, roach, 2, "dingo")
    back = _fall(s, "2,1")
    assert effective_strength(s, back) == 1 and s.strength_sources.get(back.iid) is None


def test_the_breakdown_names_each_part_and_adds_up():
    s = make_state(hands={"A": ["viper"]}, decks={"A": [], "B": ["lion"] * 3})
    put(s, "2,1", "cockroach_legend", "B")
    king = _fall(s, "2,1")                                     # 1 printed, +1 from the fall
    _grant(s, king, 2, "dingo")
    apply_click(s, PlaceAction("viper", ("cr", "1,1")))        # -3
    b = strength_breakdown(s, king)
    assert b == {"printed": 1, "base": 1, "base_bonus": 1, "growth": 0, "changes": [["dingo", 2], ["viper", -3]],
                 "auras": [], "total": 1}


def test_the_breakdown_shows_an_allys_aura_and_a_cards_own():
    s = make_state(current="A")
    tuna = put(s, "2,2", "tuna", "A")                          # +1 for each other Fish
    put(s, "1,2", "mahi_mahi", "A")                            # your other Fish have +1
    b = strength_breakdown(s, tuna)
    assert sorted(b["auras"]) == sorted([["tuna", CFG.tuna_per_fish], ["mahi_mahi", CFG.mahi_mahi_anthem]])
    assert b["base"] + sum(n for _, n in b["auras"]) == b["total"] == raw_strength(s, tuna)


def test_sources_survive_a_save():
    s = make_state()
    king = put(s, "2,1", "cockroach_legend", "B")
    _grant(s, king, 2, "dingo")
    again = GameState.from_dict(s.to_dict())
    assert again.strength_sources[king.iid] == (("dingo", 2, False),)
    assert s.to_dict()["strength_sources"] == {str(king.iid): [["dingo", 2, False]]}


def _parts(b):
    return b["base"] + b["base_bonus"] + b["growth"] + sum(n for _, n in b["changes"]) + sum(n for _, n in b["auras"])


def test_in_random_games_every_stored_change_has_its_source():
    """Every way a counter changes records where it came from: the sources add up to the counter, nothing unattributed."""
    cards = load_cards()
    pool = sorted(c for c, card in cards.items() if card.collectible)
    rng = random.Random(7)
    for g in range(25):
        deck = lambda: [rng.choice(pool) for _ in range(30)]
        s = new_game(deck(), deck(), g, map_id="map_b", cards=cards)
        for _ in range(300):
            if rules.is_terminal(s) is not None:
                break
            rules.apply_action(s, rng.choice(rules.legal_actions(s)))
            for u in [u for st in s.board.values() for u in st] + [u for h in s.hands.values() for u in h]:
                assert sum(n for _, n, _ in s.strength_sources.get(u.iid, ())) == u.strength_counter, (g, u)
                if u in [x for st in s.board.values() for x in st]:
                    b = strength_breakdown(s, u)
                    assert _parts(b) == b["total"], (g, u, b)
