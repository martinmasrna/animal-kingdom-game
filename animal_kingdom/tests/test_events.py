"""The engine says what happened, in order (state.events): nothing downstream diffs positions to guess it."""

from animal_kingdom.decks import load_premade_deck
from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import ChoiceAction, PlaceAction, SKIP
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.state import UnitInstance, new_game
from animal_kingdom.web.match import Match, Seat, public_event


def _fresh():
    s = new_game(load_premade_deck("cats"), load_premade_deck("giants"), 5, config=Config(mulligan=False))
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
    m = Match("EV", Seat("ta", "A", deck="cats"))
    m.join(Seat("tb", "B", deck="giants"))
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
                elif e["e"] == "roam" and e.get("to"):            # Roam: the unit moves (a den capture doesn't)
                    board[e["cr"]].remove(e["iid"])
                    if not board[e["cr"]]:
                        del board[e["cr"]]
                    board.setdefault(e["to"], []).append(e["iid"])
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


def test_a_stored_gain_is_an_event_and_what_reacts_comes_after_it():
    """Strength a card stores (a grant) is an event, in order before what reacts to it (a Caterpillar in hand turns into
    a Butterfly and draws); an aura is not one."""
    from animal_kingdom.engine import effects
    s = _fresh()
    me = s.current
    cat = s.add_to_hand(me, "caterpillar")
    s.events = []
    s.effect_stack.append({"op": "grant_strength", "iids": [cat.iid], "amount": 1, "by_card": "baboon"})
    effects.resolve(s)
    kinds = [(e["e"], e.get("iid"), e.get("cause")) for e in s.events if e["e"] in ("strength", "transform", "draw")]
    assert kinds[0] == ("strength", cat.iid, "baboon")
    assert kinds[1] == ("transform", cat.iid, "caterpillar") and kinds[2][0] == "draw" and kinds[2][2] == "caterpillar"


def test_a_den_capture_carries_the_strength_it_was_played_at():
    """The capture event names the animal and its strength as played (a buffed or poisoned one included): the screen
    draws it from that, not from the printed card."""
    from animal_kingdom.engine.strength import placement_strength
    s = _fresh()
    me, them = s.current, "B" if s.current == "A" else "A"
    # walk an animal of ours up to the enemy den's front, then take it with a hand card given +3
    front = sorted(s.game_map.hq_front(them))[0]
    path = []
    from collections import deque
    starts = [cr for cr in s.game_map.crossroads if s.is_connected(me, cr, s.connected_occupied(me))]
    prev, q = {c: None for c in starts}, deque(starts)
    while q:
        c = q.popleft()
        if c == front: break
        for nb in s.game_map.neighbors(c):
            if nb not in prev: prev[nb] = c; q.append(nb)
    while front: path.append(front); front = prev[front]
    for cr in path:
        s.board[cr] = [UnitInstance("lion", me, s.new_iid())]
    taker = s.add_to_hand(me, "lynx", strength_counter=3)
    s.events = []
    legal = [a for a in rules.legal_actions(s) if isinstance(a, PlaceAction) and a.card_id == "lynx" and a.target[0] == "hq"]
    assert legal, "the den is open to it"
    shown = placement_strength(s, taker)
    rules.apply_action(s, legal[0])
    cap = next(e for e in s.events if e["e"] == "capture")
    assert cap["str"] == shown and cap["str"] == s.cards["lynx"].base_strength + 3 and cap["card"] == "lynx"


def test_a_removal_names_the_very_unit_that_did_it_when_two_of_that_card_are_out():
    """Of two Honey Badgers beside the same enemy, the one just placed roared: its removal says which (`cause_iid`), so
    the screen strikes from that one, never the nearest copy (Martin, 2026-10-02: the wrong Serval struck)."""
    s = _fresh()
    me, them = s.current, "B" if s.current == "A" else "A"
    m = s.game_map
    spots = [a.target[1] for a in rules.legal_actions(s) if isinstance(a, PlaceAction) and a.target[0] == "cr"]
    cr, prey_cr, old_cr = next((c, p, o) for c in spots for p in m.neighbors(c) for o in m.neighbors(p)
                               if o not in (c, p) and not s.board.get(p) and not s.board.get(o))
    s.board[prey_cr] = [UnitInstance("rhinoceros", them, s.new_iid())]
    old = UnitInstance("honey_badger", me, s.new_iid())
    s.board[old_cr] = [old]
    s.add_to_hand(me, "honey_badger")
    s.events = []
    rules.apply_action(s, PlaceAction("honey_badger", ("cr", cr)))
    new = s.board[cr][-1]
    while s.pending:
        rules.apply_action(s, ChoiceAction(next(o for o in s.pending["options"] if o != SKIP)))
    rm = next(e for e in s.events if e["e"] == "remove")
    assert (rm["cause"], rm["cause_iid"]) == ("honey_badger", new.iid) and new.iid != old.iid
