"""A game's card facts for the Meta tab (league/facts.py), replayed from its action log."""

from animal_kingdom.decks import load_premade_deck
from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import SKIP, ChoiceAction
from animal_kingdom.engine.state import new_game
from animal_kingdom.league.facts import game_facts
from animal_kingdom.sim.runner import make_bot


def _game(seed: int, send_back: bool):
    """A greedy game; with `send_back` the first player to mulligan returns their first card, then keeps."""
    a, b = load_premade_deck("cats"), load_premade_deck("canines")
    state = new_game(list(a), list(b), seed)
    bots = {"A": make_bot("greedy", seed=1), "B": make_bot("greedy", seed=2)}
    actions, returned = [], []
    while rules.is_terminal(state) is None:
        actor = state.player_to_act()
        legal = rules.legal_actions(state)
        req = state.pending
        if send_back and req is not None and req.get("kind") == "mulligan" and not returned:
            action = ChoiceAction(req["options"][0])
            returned.append(next(u.card_id for u in state.hands[actor] if u.iid == req["options"][0]))
        else:
            action = bots[actor].choose(state.view_for(actor), legal, state)
        actions.append(action.to_dict())
        rules.apply_action(state, action)
    return a, b, state, actions, returned


def test_every_card_that_reached_a_hand_is_counted_once_with_its_turns():
    a, b, state, actions, _ = _game(5, send_back=False)
    f = game_facts(a, b, 5, state.first_player, actions)
    for seat in "AB":
        cards = f[seat]["cards"]
        assert [c for c, d, _ in cards if d == 0] == f[seat]["seen"]      # nothing sent back: the dealt hand is the starting hand
        assert all(p is None or p >= d for _, d, p in cards)               # played on or after the turn it was drawn
        assert len(cards) >= len(f[seat]["seen"])


def test_a_card_sent_back_leaves_the_starting_hand_and_its_replacement_joins_it():
    a, b, state, actions, returned = _game(7, send_back=True)
    f = game_facts(a, b, 7, state.first_player, actions)
    seat = next(s for s in "AB" if f[s]["back"])
    assert f[seat]["back"] == returned
    start = [c for c, d, _ in f[seat]["cards"] if d == 0]
    assert len(start) == len(f[seat]["seen"]) - 1                         # dealt hand plus one replacement, less the card returned
    assert f[seat]["seen"][-1] in start
