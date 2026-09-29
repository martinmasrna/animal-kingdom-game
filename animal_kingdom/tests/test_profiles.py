"""Player profiles: guest creation, sign-in codes, name#tag, decks, and match history."""
import pytest

from animal_kingdom.web import server
from animal_kingdom.web.match import Match, Seat
from animal_kingdom.web.profiles import ProfileError, Profiles


@pytest.fixture
def db():
    return Profiles(":memory:")


def test_a_guest_signs_in_anywhere_with_its_code(db):
    code, p = db.create("Martin")
    assert p["name"] == "Martin" and len(p["tag"]) == 4
    assert db.by_code(code)["id"] == p["id"]
    assert db.by_code(code.lower().replace("-", " "))["id"] == p["id"]   # typed by hand
    assert db.by_code("AAAA-AAAA-AAAA-AAAA") is None


def test_the_same_name_gets_a_different_tag(db):
    _, a = db.create("Martin")
    _, b = db.create("martin")
    assert a["tag"] != b["tag"]
    renamed = db.rename(b["id"], "MARTIN")
    assert renamed["name"] == "MARTIN" and renamed["tag"] == b["tag"]    # its own name#tag is no clash
    with pytest.raises(ProfileError):
        db.rename(a["id"], "   ")


def test_decks_are_saved_in_order_and_checked_for_shape(db):
    _, p = db.create()
    decks = [{"id": "x", "name": "Rats", "cards": {"rat": 3}}, {"id": "y", "name": "", "cards": {}}]
    assert [d["name"] for d in db.save_decks(p["id"], decks)] == ["Rats", "New deck"]
    with pytest.raises(ProfileError):
        db.save_decks(p["id"], [{"id": "z", "cards": {"rat": 4}}])
    assert len(db.decks(p["id"])) == 2                                   # a refused save changes nothing


def test_a_finished_bot_match_lands_in_the_players_history(monkeypatch):
    from animal_kingdom.engine.state import Result
    db = Profiles(":memory:")
    monkeypatch.setattr(server, "profiles", db)
    _, p = db.create("Martin")
    m = Match("M1", Seat("ta", "Martin#1", deck="cats_midrange", profile=p["id"]))
    m.join(Seat("tb", "Bot", bot="easy", deck="ramp"))
    m.on_match_end = server.record_match
    m._start_game()
    for _ in range(2):
        m.state.result = Result("A", "food")
        m._check_end()
        if m.phase == "game_over":
            m.next_game()
    assert m.phase == "match_over"
    (h,) = db.history(p["id"])
    assert (h["kind"], h["my_deck"], h["opp"], h["opp_deck"], h["won"], h["lost"]) == \
        ("bot", "Cats", "Bot · Easy", "Ramp", 2, 0)
