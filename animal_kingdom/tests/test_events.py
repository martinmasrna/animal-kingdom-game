"""The engine says what happened, in order (state.events): nothing downstream diffs positions to guess it."""

from animal_kingdom.decks import load_premade_deck
from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import ChoiceAction, PlaceAction, SKIP
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.state import UnitInstance, new_game
from animal_kingdom.web.match import Match, Seat, public_event


def _fresh():
    s = new_game(load_premade_deck("cats_midrange"), load_premade_deck("ramp"), 5, config=Config(mulligan=False))
    s.events = []
    return s


def test_an_apex_covering_an_enemy_places_covers_then_eats_naming_itself():
    s = _fresh()
    me, them = s.current, "B" if s.current == "A" else "A"
    # an Apex must land on an occupant: put an enemy on a crossroad the player can reach, then the bear onto it
    cr = next(a.target[1] for a in rules.legal_actions(s) if isinstance(a, PlaceAction) and a.target[0] == "cr")
    prey = UnitInstance("lynx", them, s.new_iid())
    s.board[cr] = [prey]
    bear = s.add_to_hand(me, "borealis")
    assert PlaceAction("borealis", ("cr", cr)) in rules.legal_actions(s)
    s.events = []
    rules.apply_action(s, PlaceAction("borealis", ("cr", cr)))
    while s.pending:
        rules.apply_action(s, ChoiceAction(SKIP))
    kinds = [(e["e"], e.get("iid"), e.get("cause")) for e in s.events if e["e"] in ("place", "cover", "remove")]
    assert kinds[:3] == [("place", bear.iid, None), ("cover", prey.iid, None), ("remove", prey.iid, "borealis")]


def test_the_opponent_sees_how_many_cards_were_drawn_not_which():
    m = Match("EV", Seat("ta", "A", deck="cats_midrange"))
    m.join(Seat("tb", "B", deck="ramp"))
    m._start_game()
    while m.state.pending:
        m.act(m.to_act(), ChoiceAction(SKIP))
    p = m.to_act()
    m.act(p, {"kind": "draw"})
    draw = next(e for e in reversed(m.events) if e["e"] == "draw")
    assert len(draw["cards"]) == 2 and draw["seq"] > 0
    other = "B" if p == "A" else "A"
    assert public_event(draw, p)["cards"] == draw["cards"]
    assert "cards" not in public_event(draw, other) and public_event(draw, other)["n"] == 2
    assert m.view(other)["game"]["events"][-1]["seq"] == draw["seq"]


def test_the_events_alone_rebuild_the_board_after_every_action():
    """Completeness: a board rebuilt only from the events (place puts a unit on top, remove and bounce take that exact unit
    off) equals the real board after every action of random games over every deck pairing. Food and hands likewise."""
    import itertools
    from animal_kingdom.decks import PREMADE_DECKS
    from animal_kingdom.sim.runner import make_bot
    decks = sorted(d for d in PREMADE_DECKS if d != "goodstuff")
    for (a, b), seed in itertools.product(itertools.product(decks, decks), range(4)):
        s = new_game(load_premade_deck(a), load_premade_deck(b), 8100 + seed)
        board = {cr: [u.iid for u in st] for cr, st in s.board.items() if st}
        food = dict(s.food)
        hands = {q: {u.iid for u in s.hands[q]} for q in "AB"}
        s.events = []
        bots = {p: make_bot("random", seed * 2 + i) for i, p in enumerate("AB")}
        for _ in range(300):
            if rules.is_terminal(s) is not None:
                break
            p = s.pending["chooser"] if s.pending else s.current
            rules.apply_action(s, bots[p].choose(s.clone().view_for(p), rules.legal_actions(s), s.clone()))
            for e in s.events:
                if e["e"] == "place":
                    board.setdefault(e["cr"], []).append(e["iid"])
                elif e["e"] in ("remove", "bounce", "to_deck") and e.get("cr"):
                    board[e["cr"]].remove(e["iid"])
                    if not board[e["cr"]]:
                        del board[e["cr"]]
                elif e["e"] == "food":
                    food[e["player"]] += e["n"]
                elif e["e"] == "pay":
                    food[e["player"]] -= e["n"]
                if e["e"] in ("place", "capture"):
                    for q in "AB":
                        hands[q].discard(e["iid"])
                elif e["e"] == "draw":
                    hands[e["player"]] |= {iid for iid, _ in e["cards"]}
                elif e["e"] == "to_hand":
                    hands[e["player"]].add(e["iid"])
                elif e["e"] in ("remove", "leave_hand") and e.get("zone") == "hand":
                    hands[e["owner"]].discard(e["iid"])
                elif e["e"] == "steal":
                    hands[e["victim"]].discard(e["iid"]); hands[e["player"]].add(e["new"])
                elif e["e"] == "mulligan":
                    hands[e["player"]].discard(e["returned"]); hands[e["player"]].add(e["drawn"][0])
            last = s.events
            s.events = []
            real = {cr: [u.iid for u in st] for cr, st in s.board.items() if st}
            assert board == real, f"{a} vs {b}: the events missed a board change"
            assert food == s.food, f"{a} vs {b}: the events missed food"
            assert hands == {q: {u.iid for u in s.hands[q]} for q in "AB"}, f"{a} vs {b}: the events missed a hand change {last}"
