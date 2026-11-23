"""What players do is kept as plain facts (web/events.py): each game's start and end for every person in it, tutorials
included, whoever ends it; a client's batch only as well-formed events within the hourly cap."""

import json
import sqlite3
from animal_kingdom.tests._helpers import DECK, SLUG  # noqa: F401

from animal_kingdom.game import ChoiceAction
from animal_kingdom.web import events, server
from animal_kingdom.web.match import Match, Seat


class _Profiles:
    def __init__(self):
        self.db = sqlite3.connect(":memory:")


def _rows(db):
    return [(k, json.loads(d)) for k, d in db.execute("SELECT kind, data FROM events ORDER BY rowid")]


def test_a_game_start_and_end_are_recorded_for_the_person_in_it(monkeypatch):
    monkeypatch.setattr(server, "profiles", _Profiles())
    hub = server.Hub()
    m = Match("EVT", Seat("ta", "A", deck=SLUG, profile="p1"))
    m.join(Seat("tb", "Bot", bot=True, deck=SLUG))
    m._start_game()
    hub.note(m)
    hub.note(m)                                   # nothing new: nothing recorded twice
    while m.state.pending:
        m.act(m.to_act(), ChoiceAction("__skip__"))
    m.concede("A")
    hub.note(m)
    rows = _rows(server.profiles.db)
    assert [k for k, _ in rows] == ["game_start", "game_end"]
    assert rows[0][1]["opp"] == "bot"
    assert rows[1][1] == {**rows[1][1], "won": False, "reason": "concede", "match": "EVT"}


def test_a_client_batch_keeps_only_well_formed_events():
    db = sqlite3.connect(":memory:")
    kept = events.record_client(db, "p1", [{"kind": "screen", "data": {"route": "/"}}, {"kind": "Bad Kind"},
                                           {"kind": "big", "data": {"x": "y" * 5000}}, "not an event"])
    assert kept == 1
    assert _rows(db) == [("c_screen", {"route": "/"})]


def test_a_target_prompt_names_its_source_unit_and_the_other_seat_sees_the_aim():
    """The target arrow (static/aim.js) starts at the very unit asking (`sourceIid`) and plays the opponent's choice from
    the engine's `aim` event, before the effect."""
    from animal_kingdom.game import PlaceAction
    from animal_kingdom.tests.test_rules import put, state
    m = Match("AIM", Seat("ta", "A", deck=SLUG))
    m.join(Seat("tb", "B", deck=SLUG))
    m._start_game()
    m.state = state(turn=11, hands={"A": ["hunter_4"]})
    put(m.state, "2,1", "wisp_6", "B")
    m.act("A", PlaceAction("hunter_4", ("cr", "1,1")))
    pending = m.view("A")["game"]["pending"]
    assert (pending["kind"], pending["source"], pending["sourceIid"]) == ("effect", "hunter_4", m.state.board["1,1"][-1].iid)
    m.act("A", ChoiceAction("2,1"))
    seen = [(e["e"], e.get("cause"), e.get("cr")) for e in m.view("B")["game"]["events"]][-2:]
    assert seen == [("aim", "hunter_4", "2,1"), ("strength", "hunter_4", None)]
