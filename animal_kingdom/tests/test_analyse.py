"""The position analyser (web/analyse.py) watches the Expert's search through `TurnSearcher._observer`; watching must not
change what the search does, and what it reports must name the moves the way the move list does."""
from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import SKIP, ChoiceAction
from animal_kingdom.engine.state import new_game
from animal_kingdom.sim.runner import make_bot
from animal_kingdom.web import analyse


def _position():
    s = new_game(["lion"] * 15 + ["mouse"] * 15, ["tiger"] * 15 + ["mouse"] * 15, 7, map_id="map_b", first_player="A")
    while s.pending is not None:                       # through the mulligans
        rules.apply_action(s, ChoiceAction(SKIP))
    rules.apply_action(s, next(a for a in rules.legal_actions(s) if a.kind == "place"))   # the first turn's one action
    while s.pending is not None:
        rules.apply_action(s, ChoiceAction(SKIP))
    return s


def test_watching_the_search_does_not_change_its_choice():
    s = _position()
    me, legal = s.player_to_act(), rules.legal_actions(s)
    plain = make_bot("turn", 3, extra={"determinizations": 2, "beam_width": 3}, python_only=True).choose(s.view_for(me), legal, s)
    watched, seen = make_bot("turn", 3, extra={"determinizations": 2, "beam_width": 3}, python_only=True), []
    watched._observer = lambda path, score, compare: seen.append((path, score, compare))
    assert watched.choose(s.view_for(me), legal, s) == plain
    assert seen and all(isinstance(path, tuple) and path for path, _, _ in seen)


def test_texts_name_what_a_choice_touches():
    s = _position()
    place = next(a for a in rules.legal_actions(s) if a.kind == "place")
    assert analyse.texts(s, [place.to_dict()]) == [analyse.describe(place.to_dict())]
    assert analyse.describe({"kind": "draw"}) == "draw"
