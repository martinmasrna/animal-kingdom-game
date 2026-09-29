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


# ----------------------------------------------------------------- sign in with Google / Discord
def test_signing_in_turns_the_guest_into_the_account(db):
    _, guest = db.create("Martin")
    p = db.sign_in("google", "g-123", "m@example.com", guest["id"])
    assert p["id"] == guest["id"]
    assert db.identities(p["id"]) == [{"provider": "google", "label": "m@example.com"}]
    key = db.new_session(p["id"])
    assert db.by_code(key)["id"] == p["id"]
    db.end_session(key)
    assert db.by_code(key) is None


def test_signing_in_on_a_second_device_moves_that_guests_work_into_the_account(db):
    _, first = db.create("Martin")
    account = db.sign_in("discord", "d-1", "martin", first["id"])
    db.save_decks(account["id"], [{"id": "a", "name": "Cats", "cards": {"lion": 3}}])
    _, second = db.create("Player")
    db.save_decks(second["id"], [{"id": "a", "name": "Rats", "cards": {"rat": 3}}])
    db.record(second["id"], "M-0", kind="bot", my_deck="Rats", opp="Bot · Easy", opp_deck="Ramp", won=2, lost=1)
    again = db.sign_in("discord", "d-1", "martin", second["id"])
    assert again["id"] == account["id"]
    assert [d["name"] for d in db.decks(account["id"])] == ["Cats", "Rats"]
    assert [h["match"] for h in db.history(account["id"])] == ["M-0"]
    assert db.get(second["id"]) is None                                   # the guest is gone


def test_the_server_round_trip_signs_the_browser_in(monkeypatch):
    import asyncio
    from aiohttp.test_utils import TestClient, TestServer
    from animal_kingdom.web import oauth

    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")
    monkeypatch.setenv("AK_GOOGLE_ID", "id")
    monkeypatch.setenv("AK_GOOGLE_SECRET", "secret")

    async def fake_identify(provider, code, redirect_uri):
        assert (provider, code) == ("google", "the-code") and redirect_uri.endswith("/auth/google/callback")
        return "g-42", "m@example.com"
    monkeypatch.setattr(oauth, "identify", fake_identify)

    async def run():
        async with TestClient(TestServer(server.make_app())) as c:
            guest = await (await c.post("/api/profile", json={})).json()
            hdr = {"X-AK-Key": guest["code"]}
            url = (await (await c.post("/api/auth/google", headers=hdr)).json())["url"]
            state = dict(p.split("=", 1) for p in url.split("?", 1)[1].split("&"))["state"]
            r = await c.get(f"/auth/google/callback?code=the-code&state={state}", allow_redirects=False)
            code = r.headers["Location"].rsplit("/", 1)[1]
            signed = await (await c.post("/api/auth/redeem", json={"code": code})).json()
            assert signed["profile"]["id"] == guest["profile"]["id"]
            assert signed["profile"]["logins"] == [{"provider": "google", "label": "m@example.com"}]
            assert (await c.post("/api/auth/redeem", json={"code": code})).status == 404   # one use only
            me = await (await c.get("/api/me", headers={"X-AK-Key": signed["key"]})).json()
            assert me["id"] == guest["profile"]["id"]
            await c.post("/api/signout", headers={"X-AK-Key": signed["key"]})
            assert (await c.get("/api/me", headers={"X-AK-Key": signed["key"]})).status == 401
            bad = await c.get("/auth/google/callback?code=x&state=forged", allow_redirects=False)
            assert bad.headers["Location"] == "/#/auth/failed"
    asyncio.run(run())
