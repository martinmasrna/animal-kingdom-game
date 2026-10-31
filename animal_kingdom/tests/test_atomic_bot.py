"""AtomicBot (bots/atomic_bot.py) scores whole turns only: every turn it lists ends where the turn passes (or at a step
that reaches into the deck), and two orders that reach the same position count once."""
from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import SKIP, ChoiceAction
from animal_kingdom.engine.state import new_game
from animal_kingdom.sim.runner import make_bot
from animal_kingdom.bots.atomic_bot import AtomicBot


def _position():
    s = new_game(["lion"] * 15 + ["mouse"] * 15, ["tiger"] * 15 + ["mouse"] * 15, 7, map_id="map_b", first_player="A")
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
    bot = AtomicBot(make_bot("turn", 1, extra={"determinizations": 2}, python_only=True), turn_width=3, workers=1)
    legal = rules.legal_actions(s)
    assert bot.choose(s.view_for(me), legal, s) in legal
