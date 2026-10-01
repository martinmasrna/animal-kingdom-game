"""What players do is kept as plain facts (web/events.py): each game's start and end for every person in it, tutorials
included, whoever ends it; a client's batch only as well-formed events within the hourly cap."""

import json
import sqlite3

from animal_kingdom.engine.actions import ChoiceAction
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
    m = Match("EVT", Seat("ta", "A", deck="cats_midrange", profile="p1"))
    m.join(Seat("tb", "Bot", bot="easy", deck="ramp"))
    m._start_game()
    hub.note(m)
    hub.note(m)                                   # nothing new: nothing recorded twice
    while m.state.pending:
        m.act(m.to_act(), ChoiceAction("__skip__"))
    m.concede("A")
    hub.note(m)
    rows = _rows(server.profiles.db)
    assert [k for k, _ in rows] == ["game_start", "game_end"]
    assert rows[0][1]["opp"] == "bot:easy" and rows[0][1]["lesson"] == 0
    assert rows[1][1] == {**rows[1][1], "won": False, "reason": "concede", "match": "EVT"}


def test_a_client_batch_keeps_only_well_formed_events():
    db = sqlite3.connect(":memory:")
    kept = events.record_client(db, "p1", [{"kind": "screen", "data": {"route": "/"}}, {"kind": "Bad Kind"},
                                           {"kind": "big", "data": {"x": "y" * 5000}}, "not an event"])
    assert kept == 1
    assert _rows(db) == [("c_screen", {"route": "/"})]
