"""The tutorial (web/tutorial.py): the fixed deal the client's lessons are written for, and an opponent that never wins."""
import random

from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import SKIP, ChoiceAction, DrawAction, PassAction, PlaceAction
from animal_kingdom.web.match import Match, Seat


def _tutorial() -> Match:
    m = Match("T", Seat("ta", "You", deck="tutorial_you"))
    m.join(Seat("tb", "Wild dogs", bot="tutorial", deck="tutorial_them"))
    m.ready("A")
    return m


def _board(m):
    return {cr: [(u.owner, u.card_id) for u in st] for cr, st in m.state.board.items() if st}


def test_the_deal_is_fixed_the_player_goes_first_and_there_is_no_mulligan():
    m = _tutorial()
    assert m.tutorial and m.phase == "playing" and m.state.current == "A" and m.state.pending is None
    assert [u.card_id for u in m.state.hands["A"]] == ["lion", "cape_buffalo", "dire_wolf"]


def test_the_forced_turns_play_out_as_the_lessons_say():
    m = _tutorial()
    for a in [PlaceAction("lion", ("cr", "1,2")), PlaceAction("cape_buffalo", ("cr", "2,2"))]:
        m.act("A", a)
    while m.to_act() == "B":
        m.act("B", m.bot_move())
    assert _board(m)["5,2"] == [("B", "cape_buffalo")] and _board(m)["4,2"] == [("B", "pup")]
    m.act("A", PlaceAction("dire_wolf", ("cr", "1,1"))); m.act("A", DrawAction())
    assert [u.card_id for u in m.state.hands["A"]] == ["jaguar", "lion"]


def test_the_opponent_never_wins_and_never_takes_food():
    for seed in range(20):
        rng, m = random.Random(seed), _tutorial()
        while m.phase == "playing":
            if m.to_act() == "B":
                m.act("B", m.bot_move()); continue
            legal = rules.legal_actions(m.state)
            choices = [a for a in legal if isinstance(a, ChoiceAction)]
            places = [a for a in legal if isinstance(a, PlaceAction)]
            m.act("A", rng.choice([c for c in choices if c.choice != SKIP] or choices) if choices else
                  rng.choice(places) if places else DrawAction() if DrawAction() in legal else PassAction())
        assert m.results[-1]["winner"] == "A", (seed, m.results[-1])
        assert m.state.food["B"] == 0
