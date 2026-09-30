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
    assert _board(m)["5,2"] == [("B", "rusty")] and _board(m)["4,2"] == [("B", "pup")]
    m.act("A", PlaceAction("dire_wolf", ("cr", "1,1"))); m.act("A", PlaceAction("cape_buffalo", ("cr", "2,1")))   # the region, closed
    assert m.state.food["A"] == 10, "it pays as the turn ends"
    while m.to_act() == "B":
        m.act("B", m.bot_move())
    m.act("A", DrawAction())
    assert [u.card_id for u in m.state.hands["A"]] == ["dire_wolf", "pup"]
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


def test_lesson_1_guided_to_regions_always_ends_on_100_food():
    """After the Roar the client offers the open corners of the regions where the player holds the most (feed): with any
    choice among them, lesson 1 always ends on food, and before turn 12."""
    regions = [[f"{x},{y}", f"{x + 1},{y}", f"{x},{y + 1}", f"{x + 1},{y + 1}"] for x in range(1, 5) for y in (1, 2)]
    for seed in range(60):
        rng, m = random.Random(seed), _tutorial()
        while m.phase == "playing":
            if m.to_act() == "B":
                m.act("B", m.bot_move()); continue
            legal = rules.legal_actions(m.state)
            b = m.state.board
            own = lambda cr: b[cr][-1].owner if b.get(cr) else None
            places = [a for a in legal if isinstance(a, PlaceAction) and not a.is_hq_capture and own(a.crossroad) != "A"]
            take = {a.crossroad for a in places}   # empty, or an enemy a card can cover
            cand = [(sum(own(q) == "A" for q in r), r) for r in regions if not all(own(q) == "A" for q in r)
                    and all(own(q) == "A" or not own(q) or q in take for q in r) and any(q in take for q in r)]
            top = max((n for n, _ in cand), default=None)
            feed = {q for n, r in cand if n == top for q in r if q in take} or take
            pick = [a for a in places if a.crossroad in feed]
            choices = [a for a in legal if isinstance(a, ChoiceAction)]
            m.act("A", choices[0] if choices else rng.choice(pick) if pick else DrawAction() if DrawAction() in legal else PassAction())
        r = m.results[-1]
        assert r["winner"] == "A" and r["reason"] == "food" and r["turns"] < 12, (seed, r)


def test_lesson_2_can_always_be_finished_wherever_the_player_puts_its_animals():
    """From the set-up board: the Lynx anywhere legal; the Eagle, Squirrel and Black Mamba where the lesson rings them (the same
    rules as static/tutorial.js); the opponent's Eagle covers the Squirrel, the Mamba frees it, the Polar Bear breaks the
    wall, the den falls."""
    adj = lambda cr: {f"{c},{r}" for c, r in ((int(cr[0]) - 1, int(cr[2])), (int(cr[0]) + 1, int(cr[2])),
                                              (int(cr[0]), int(cr[2]) - 1), (int(cr[0]), int(cr[2]) + 1)) if 1 <= c <= 5 and 1 <= r <= 3}
    for seed in range(300):
        rng, m = random.Random(seed), _lesson2()
        legal = lambda: rules.legal_actions(m.state)
        own = lambda cr: m.state.board[cr][-1].owner if m.state.board.get(cr) else None
        empty = lambda card: [x.crossroad for x in legal() if isinstance(x, PlaceAction) and x.card_id == card
                              and not x.is_hq_capture and not m.state.board.get(x.crossroad)]

        def a(action):
            assert action in legal(), (seed, action)
            m.act("A", action)
            while m.state.pending is not None and m.to_act() == "A":
                m.act("A", next(x for x in legal() if isinstance(x, ChoiceAction) and x.choice != SKIP))

        def their_turn():
            moves = []
            while m.phase == "playing" and m.to_act() == "B":
                moves.append(m.bot_move()); m.act("B", moves[-1])
            return moves

        place = lambda card, crs: a(PlaceAction(card, ("cr", rng.choice(crs))))
        assert [u.card_id for u in m.state.hands["A"]] == ["lynx"] and own("1,2") == "A" and own("5,2") == "B", "the set-up board"
        place("lynx", empty("lynx"))   # its Roar draws the Eagle
        reach = set(x.crossroad for x in legal() if isinstance(x, PlaceAction) and not x.is_hq_capture and x.card_id != "eagle") | {
            n for cr in m.state.board if own(cr) == "A" for n in adj(cr) if not m.state.board.get(n)} | {"1,1", "1,3"} - set(m.state.board)
        unreached = [cr for cr in empty("eagle") if cr not in reach]
        alone = [cr for cr in unreached if not any(n in reach or own(n) == "A" for n in adj(cr))]
        place("eagle", alone or unreached or empty("eagle"))
        eagle = next(cr for cr in m.state.board if own(cr) == "A" and m.state.board[cr][-1].card_id == "eagle")
        their_turn()
        a(DrawAction())
        safe = [cr for cr in empty("squirrel") if any(not own(n) and (n[0] == "1" or any(q != cr and q != eagle and own(q) == "A" for q in adj(n)))
                                                     for n in adj(cr))]
        place("squirrel", safe or empty("squirrel")); moves = their_turn()
        assert [type(x).__name__ for x in moves][:2] == ["DrawAction", "PlaceAction"] and moves[1].card_id == "eagle", (seed, "it draws, then the Eagle's cover ends its turn", moves)
        sq = next(cr for cr, st in m.state.board.items() if any(u.card_id == "squirrel" and u.owner == "A" for u in st))
        assert own(sq) == "B", (seed, "the Eagle covers the Squirrel")
        beside = [x.crossroad for x in legal() if isinstance(x, PlaceAction) and x.card_id == "black_mamba" and x.crossroad in adj(sq)]
        rescue = [cr for cr in beside if not own(cr)] or [cr for cr in beside if own(cr) == "A"]   # else on top of your own
        assert rescue, (seed, "a crossroad for the Black Mamba beside the Squirrel")
        place("black_mamba", rescue)
        assert own(sq) == "A", (seed, "the Squirrel is back on top")
        for _ in range(12):   # draw, get next to the wall, the Polar Bear eats a 7, the den
            if m.phase != "playing":
                break
            if m.to_act() == "B":
                their_turn(); continue
            hq = [x for x in legal() if isinstance(x, PlaceAction) and x.is_hq_capture]
            bear = [x for x in legal() if isinstance(x, PlaceAction) and x.card_id == "polar_bear" and x.crossroad[0] == "5"]
            moves = [x for x in legal() if isinstance(x, PlaceAction) and x.card_id != "polar_bear" and not x.is_hq_capture
                     and own(x.crossroad) != "A"]
            ahead = [x for x in moves if x.crossroad[0] == max(y.crossroad[0] for y in moves)] if moves else []   # the lesson's 'near': the furthest
            a(hq[0] if hq else bear[0] if bear else ahead[0] if ahead and any(u.card_id == "polar_bear" for u in m.state.hands["A"])
              else DrawAction() if DrawAction() in legal() else PassAction())
        assert m.results and m.results[-1]["reason"] == "hq_capture", (seed, m.results[-1] if m.results else m.phase)
