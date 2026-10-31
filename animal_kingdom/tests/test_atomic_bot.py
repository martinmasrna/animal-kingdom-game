"""AtomicBot (bots/atomic_bot.py) scores whole turns only: every turn it lists ends where the turn passes (or at a step
that reaches into the deck), and two orders that reach the same position count once."""
from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import SKIP, ChoiceAction
from animal_kingdom.engine.state import new_game
from animal_kingdom.sim.runner import make_bot
from animal_kingdom.bots.atomic_bot import AtomicBot


def _position(theirs=("elephant",) * 30):
    s = new_game(["lion"] * 15 + ["mouse"] * 15, list(theirs), 7, map_id="map_b", first_player="A")
    while s.pending is not None:
        rules.apply_action(s, ChoiceAction(SKIP))
    rules.apply_action(s, next(a for a in rules.legal_actions(s) if a.kind == "place"))
    while s.pending is not None:
        rules.apply_action(s, ChoiceAction(SKIP))
    return s


def test_whole_turns_end_where_the_turn_passes_and_merge_orders():
    s = _position()
    me = s.player_to_act()
    bot = AtomicBot(make_bot("turn", 1, extra={"determinizations": 2}, python_only=True), workers=1)
    turns = bot.turns(s, me, through_draws=False)
    assert turns
    for path, end in turns:
        stopped_at_deck = path[-1].kind == "draw" or len(end.decks[me]) != len(s.decks[me])
        assert stopped_at_deck or end.player_to_act() != me or rules.is_terminal(end) is not None
    two_place = [p for p, _ in turns if len(p) == 2 and all(a.kind == "place" for a in p)]
    orders = {tuple(sorted((a.card_id, a.target) for a in p)) for p in two_place}
    assert len(orders) == len(two_place)          # the same two placements in either order: one turn


def test_it_plays_a_legal_turn():
    s = _position()
    me = s.player_to_act()
    bot = AtomicBot(make_bot("turn", 1, extra={"determinizations": 2}, python_only=True), widths=(3,), workers=1)
    legal = rules.legal_actions(s)
    assert bot.choose(s.view_for(me), legal, s) in legal


def test_drawing_first_never_scores_below_playing_and_then_drawing():
    """Martin, 2026-10-31: 'if you're going to draw anyway, you might as well do it first'. In one imagined hand "draw,
    then X" reaches the position "X, then draw" does, so the draw-first turn, finished by its best continuation, scores
    at least as well."""
    s = _position()
    me = s.player_to_act()
    bot = AtomicBot(make_bot("turn", 1, extra={"determinizations": 2}, python_only=True), widths=(400,), workers=1)
    rows = bot.rank(s, me)
    draw_first = next(r for r in rows if r["turn"][0].kind == "draw")
    then_draw = [r for r in rows if len(r["turn"]) > 1 and r["turn"][-1].kind == "draw" and r["levels"][0] is not None]
    assert then_draw and all(draw_first["levels"][0] >= r["levels"][0] - 1e-9 for r in then_draw)


def test_the_rust_search_gives_the_python_numbers(monkeypatch):
    """The Rust port (engine_rs/src/bots/atomic.rs) ranks the same whole turns in the same order with the same scores."""
    import pytest
    from animal_kingdom.bots import rust_bot
    monkeypatch.setenv("AK_RUST_BOTS", "1")
    monkeypatch.delenv("AK_PY_BOTS", raising=False)
    if not rust_bot.available():
        pytest.skip("the Rust engine is not built")
    s = _position(["elephant"] * 15 + ["lion"] * 15)     # several hands the opponent may hold, at different odds
    me = s.player_to_act()
    spec = "atomic_learned:eval=wave2_slot_r4_10_live,decisive=500,rounds=2,width1=4,width2=2,inner=2,draws=2,threads=2"
    rust = make_bot(spec, 4).ranking(s)
    py = make_bot(spec + ",workers=1", 4, python_only=True).rank(s, me)
    assert [r["turn"] for r in rust] == [[a.to_dict() for a in r["turn"]] for r in py]
    for a, b in zip(py, rust):
        assert abs(a["board"] - b["board"]) < 1e-9
        assert all((x is None) == (y is None) and (x is None or abs(x - y) < 1e-9) for x, y in zip(a["levels"], b["levels"]))


def test_the_hands_are_every_hand_the_opponent_may_hold_at_its_odds():
    """With few enough of them, the imagined hands are every distinct hand the opponent's unseen cards make, each
    weighted by the number of ways it can be dealt (Martin's game PXPR6W, turn 28: five random hands missed the double
    Alley Cat that was the only way to survive, and every turn tied at a sure loss)."""
    from math import comb
    s = _position(["elephant"] * 15 + ["lion"] * 15)
    me = s.player_to_act()
    opp = "B" if me == "A" else "A"
    assert len({u.card_id for u in s.hands[opp]} | set(s.decks[opp])) == 2
    bot = AtomicBot(make_bot("turn", 1, python_only=True), workers=1)
    worlds, weights = bot.spread(s, me)
    pool = [u.card_id for u in s.hands[opp]] + list(s.decks[opp])
    kind = pool[0]
    n, e = len(s.hands[opp]), pool.count(kind)
    held = [sum(u.card_id == kind for u in w.hands[opp]) for w in worlds]
    assert sorted(held) == [k for k in range(n + 1) if k <= e and n - k <= len(pool) - e]
    for k, w in zip(held, weights):
        assert abs(w - comb(e, k) * comb(len(pool) - e, n - k) / comb(len(pool), n)) < 1e-12
