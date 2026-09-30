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
    assert [u.card_id for u in m.state.hands["A"]] == ["lion", "cape_buffalo", "dire_wolf", "cape_buffalo"]


def test_the_forced_turns_play_out_as_the_lessons_say():
    m = _tutorial()
    for a in [PlaceAction("lion", ("cr", "1,2")), PlaceAction("cape_buffalo", ("cr", "2,2"))]:
        m.act("A", a)
    while m.to_act() == "B":
        m.act("B", m.bot_move())
    assert _board(m)["5,2"] == [("B", "cape_buffalo")] and _board(m)["4,2"] == [("B", "pup")]
    m.act("A", PlaceAction("dire_wolf", ("cr", "1,1"))); m.act("A", PlaceAction("cape_buffalo", ("cr", "2,1")))   # the region, closed
    assert m.state.food["A"] == 10, "it pays as the turn ends"
    while m.to_act() == "B":
        m.act("B", m.bot_move())
    m.act("A", DrawAction())
    assert [u.card_id for u in m.state.hands["A"]] == ["dire_wolf", "lion"]
    assert any(isinstance(a, PlaceAction) and _board(m).get(a.crossroad, [("A",)])[-1][0] == "B" for a in rules.legal_actions(m.state)), "a Pup to cover"


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


def _adj(cr):
    c, r = map(int, cr.split(","))
    return {f"{a},{b}" for a, b in ((c - 1, r), (c + 1, r), (c, r - 1), (c, r + 1))}


def eagle_at(m):
    return next(cr for cr, st in m.state.board.items() if st and st[-1].owner == "A" and st[-1].card_id == "eagle")


def _lesson2() -> Match:
    m = Match("T", Seat("ta", "You", deck="tutorial2_you"))
    m.join(Seat("tb", "Wild dogs", bot="tutorial2", deck="tutorial2_them"))
    m.ready("A")
    return m


def test_lesson_2_plays_out_as_its_script_says_and_is_won_on_food():
    for seed in range(20):
        rng, m = random.Random(seed), _lesson2()
        legal = lambda: rules.legal_actions(m.state)
        top = lambda cr: m.state.board[cr][-1].card_id if m.state.board.get(cr) else None

        def a(action):
            assert action in legal(), (seed, action)
            m.act("A", action)
            while m.state.pending is not None and m.to_act() == "A":   # a Roar's target: the first offered
                m.act("A", next(x for x in legal() if isinstance(x, ChoiceAction) and x.choice != SKIP))

        def their_turn():
            while m.phase == "playing" and m.to_act() == "B":
                m.act("B", m.bot_move())

        a(PlaceAction("lion", ("cr", "1,2"))); a(PlaceAction("lynx", ("cr", "2,2")))   # the Lynx draws the Eagle
        their_turn()
        assert (top("5,2"), top("5,1")) == ("cape_buffalo", "dire_wolf")
        eagle = [x for x in legal() if isinstance(x, PlaceAction) and x.card_id == "eagle" and not m.state.board.get(x.crossroad)
                 and x.crossroad in ("4,1", "4,3")]   # as the lesson offers: nothing reachable beside it
        a(rng.choice(eagle))
        assert not any(isinstance(x, PlaceAction) and x.card_id == "cape_buffalo" and x.crossroad in _adj(eagle_at(m)) for x in legal()), \
            "nothing may go next to the lone Eagle"
        a(PlaceAction("cape_buffalo", ("cr", "2,1")))
        their_turn()
        a(DrawAction()); a(PlaceAction("squirrel", ("cr", "3,2")))
        their_turn()
        assert top("5,3") == "lion" and top("3,2") == "eagle", "the wall is complete and the Eagle covers the Squirrel"
        a(PlaceAction("black_mamba", ("cr", "3,1")))
        assert top("3,2") == "squirrel", "the Black Mamba removed the Eagle"
        a(DrawAction())
        their_turn()
        prey = [x for x in legal() if isinstance(x, PlaceAction) and x.card_id == "tiger" and m.state.board.get(x.crossroad)
                and m.state.board[x.crossroad][-1].owner == "B"]
        assert prey, "a Pup for the Tiger"
        a(rng.choice(prey))
        while m.phase == "playing":
            if m.to_act() == "B":
                their_turn(); continue
            places = [x for x in legal() if isinstance(x, PlaceAction) and not x.is_hq_capture and not (
                m.state.board.get(x.crossroad) and m.state.board[x.crossroad][-1].owner == "A")]
            a(rng.choice(places) if places else DrawAction() if DrawAction() in legal() else PassAction())
        assert m.results[-1]["winner"] == "A" and m.results[-1]["reason"] == "food", (seed, m.results[-1])
        assert m.state.food["B"] == 0
