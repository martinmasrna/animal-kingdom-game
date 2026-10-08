"""The browser tests' view recorder plays whole matches through the real Match and yields what a seat receives."""
import json

from animal_kingdom.web.test.record_views import record


def test_a_recorded_match_runs_to_its_end_in_both_seats():
    for seat in "AB":
        views = record("cats", "giants", 7, seat)
        assert views[-1]["phase"] == "match_over"
        assert all(v["you"] == seat for v in views)
        json.dumps(views)   # exactly what goes over the socket


def test_recording_is_deterministic():
    assert record("egg_control", "food_otk", 3) == record("egg_control", "food_otk", 3)
