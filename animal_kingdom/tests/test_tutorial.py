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
    assert [u.card_id for u in m.state.hands["A"]] == ["lion", "dire_wolf"]


def test_the_opponent_never_wins_and_never_takes_food():
    for seed in range(60):
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


def _lesson2() -> Match:
    m = Match("T", Seat("ta", "You", deck="tutorial2_you"))
    m.join(Seat("tb", "Wild dogs", bot="tutorial2", deck="tutorial2_them"))
    m.ready("A")
    return m


def test_lesson_2_walls_the_den_flies_the_falcon_onto_the_squirrel_and_is_won_on_food():
    for seed in range(40):
        rng, m, flown = random.Random(seed), _lesson2(), False
        m.act("A", PlaceAction("lion", ("cr", "1,2"))); m.act("A", PlaceAction("lynx", ("cr", "2,2")))   # the Lynx draws the Squirrel
        while m.phase == "playing":
            if m.to_act() == "B":
                m.act("B", m.bot_move()); continue
            legal = rules.legal_actions(m.state)
            squirrel = [a for a in legal if isinstance(a, PlaceAction) and a.card_id == "squirrel" and not m.state.board.get(a.crossroad)]
            choices = [a for a in legal if isinstance(a, ChoiceAction)]
            places = [a for a in legal if isinstance(a, PlaceAction)   # as the client offers: never onto your own animal
                      and not (a.target[0] == "cr" and m.state.board.get(a.crossroad) and m.state.board[a.crossroad][-1].owner == "A")]
            m.act("A", squirrel[0] if squirrel and not flown else
                  rng.choice([c for c in choices if c.choice != SKIP] or choices) if choices else
                  rng.choice(places) if places else DrawAction() if DrawAction() in legal else PassAction())
            flown = flown or any(len(st) > 1 and st[-1].card_id == "falcon" for st in m.state.board.values())
        assert flown, seed
        assert [m.state.board[cr][0].card_id for cr in ("5,1", "5,2", "5,3")] == ["dire_wolf", "cape_buffalo", "lion"]
        assert m.results[-1]["winner"] == "A" and m.results[-1]["reason"] in ("food", "exhaustion"), (seed, m.results[-1])
        assert m.state.food["B"] == 0
