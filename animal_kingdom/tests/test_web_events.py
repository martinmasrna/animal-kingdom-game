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


def test_the_rogues_power_asks_for_a_card_in_her_hand_and_reads_as_her_power():
    """A pick from the hand inside a leader's power: the options are the hand's cards with their numbers (laid out in the
    middle by the client) and the prompt is marked as the leader's, so it reads the power and not the leader's card."""
    from animal_kingdom.game import ASSASSIN, LeaderAction, PlaceAction
    from animal_kingdom.tests.test_rules import state
    m = Match("ROGUE", Seat("ta", "A", deck=SLUG))
    m.join(Seat("tb", "B", deck=SLUG))
    m._start_game()
    m.state = state(turn=11, hands={"A": ["wisp_1", "wisp_2", "wisp_3"]}, leaders={"A": ASSASSIN})
    assert not m.view("A")["game"]["legal"]["leader"]                  # nothing played yet
    m.act("A", PlaceAction("wisp_1", ("cr", "1,1")))
    m.act("A", LeaderAction())
    pending = m.view("A")["game"]["pending"]
    assert (pending["kind"], pending["leader"], pending["source"], pending["optional"]) == ("effect", True, ASSASSIN, False)
    assert [(o["kind"], o["id"]) for o in pending["options"]] == [("hand", "wisp_2"), ("hand", "wisp_3")]
    before = {h["id"]: h["str"] for h in m.view("A")["game"]["hand"]}
    m.act("A", ChoiceAction(pending["options"][1]["v"]))
    after = {h["id"]: h["str"] for h in m.view("A")["game"]["hand"]}
    assert after == {"wisp_2": before["wisp_2"], "wisp_3": before["wisp_3"] + 1} and m.view("A")["game"]["pending"] is None
