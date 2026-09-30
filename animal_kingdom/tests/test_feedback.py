"""Player feedback (web/feedback.py): kept with its moment, checked for length and rate, mailed only with credentials."""

import json
import sqlite3

import pytest

from animal_kingdom.web import feedback


def test_a_message_is_kept_with_its_moment_and_view():
    db = sqlite3.connect(":memory:")
    feedback.keep(db, "p1", "Martin#1234", "  the Mamba hit the wrong dog  ", {"match": "ABC", "turn": 7}, {"game": {"round": 7}})
    sent, profile, sender, text, context, view = db.execute("SELECT * FROM feedback").fetchone()
    assert (profile, sender, text) == ("p1", "Martin#1234", "the Mamba hit the wrong dog")
    assert json.loads(context) == {"match": "ABC", "turn": 7} and json.loads(view) == {"game": {"round": 7}}
    assert feedback.subject(sender, json.loads(context)) == "Feedback: Martin#1234, turn 7 of match ABC"


def test_empty_long_and_too_many_messages_are_refused():
    db = sqlite3.connect(":memory:")
    for bad in ("", "   ", "x" * (feedback.TEXT_MAX + 1)):
        with pytest.raises(feedback.FeedbackError):
            feedback.keep(db, "p1", "A#1", bad, {}, None)
    for _ in range(feedback.PER_HOUR):
        feedback.keep(db, "p1", "A#1", "hi", {}, None)
    with pytest.raises(feedback.FeedbackError):
        feedback.keep(db, "p1", "A#1", "one more", {}, None)
    feedback.keep(db, "p2", "B#2", "someone else still can", {}, None)


def test_no_credentials_no_mail(monkeypatch):
    monkeypatch.setattr(feedback, "_credentials", lambda: None)
    assert feedback.mail("A#1", "hi", {}, None) is False
