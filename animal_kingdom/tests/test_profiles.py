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


def test_a_deck_keeps_its_chosen_cover(db, tmp_path):
    _, p = db.create()
    db.save_decks(p["id"], [{"id": "x", "name": "Rats", "cards": {"rat": 3}, "cover": "rat"}, {"id": "y", "name": "Bees", "cards": {}}])
    assert [d.get("cover") for d in db.decks(p["id"])] == ["rat", None]


def test_a_database_from_before_covers_gains_the_column(tmp_path):
    import sqlite3
    path = tmp_path / "old.db"
    old = sqlite3.connect(path)
    old.executescript("CREATE TABLE decks (profile TEXT NOT NULL, id TEXT NOT NULL, name TEXT NOT NULL, cards TEXT NOT NULL, pos INTEGER NOT NULL, PRIMARY KEY (profile, id));"
                      "INSERT INTO decks VALUES ('p', 'x', 'Rats', '{\"rat\": 3}', 0);")
    old.commit(); old.close()
    assert Profiles(str(path)).decks("p") == [{"id": "x", "name": "Rats", "cards": {"rat": 3}}]


def test_a_profile_gets_the_starter_decks_once(monkeypatch):
    db = Profiles(":memory:")
    monkeypatch.setattr(server, "profiles", db)
    _, p = db.create()
    decks = server.profile_view(p)["decks"]
    assert [d["name"] for d in decks][:3] == ["Cats", "Canines", "Aggro"] and len(decks) == 7
    assert all(sum(d["cards"].values()) == 30 for d in decks)
    db.save_decks(p["id"], decks[:1])                                   # the player deletes six
    assert len(server.profile_view(p)["decks"]) == 1                    # and they stay deleted


def test_an_untouched_starter_copy_follows_its_starter(db):
    _, p = db.create()
    v1 = {"borealis": 1, "elephant": 2}
    db.seed_decks(p["id"], [{"id": "ramp", "name": "Ramp", "cards": v1}])
    assert db.decks(p["id"], {"ramp": v1})[0]["cards"] == v1
    v2 = {"borealis": 1, "elephant": 1, "cairn": 1}                     # the starter's list changes
    assert db.decks(p["id"], {"ramp": v2})[0]["cards"] == v2            # the untouched copy follows it
    assert db.decks(p["id"])[0]["cards"] == v1, "with no starter to resolve against, what was last saved"


def test_editing_a_starter_copys_cards_detaches_it_for_good(db):
    _, p = db.create()
    v1 = {"lion": 3, "tiger": 2}
    db.seed_decks(p["id"], [{"id": "cats_midrange", "name": "Cats", "cards": v1}])
    edited = {"lion": 2, "tiger": 2}                                    # the player takes a copy out: it's theirs now
    db.save_decks(p["id"], [{"id": "cats_midrange", "name": "Cats", "cards": edited}], {"cats_midrange": v1})
    new_starter = {"lion": 3, "panther": 2}                             # the starter changes
    assert db.decks(p["id"], {"cats_midrange": new_starter})[0]["cards"] == edited, "detached: it doesn't follow"
    # editing it back to match a past starter list doesn't relink it
    db.save_decks(p["id"], [{"id": "cats_midrange", "name": "Cats", "cards": v1}], {"cats_midrange": new_starter})
    assert db.decks(p["id"], {"cats_midrange": new_starter})[0]["cards"] == v1, "shown as saved"
    even_newer = {"lion": 1, "panther": 1, "lynx": 1}
    assert db.decks(p["id"], {"cats_midrange": even_newer})[0]["cards"] == v1, "still detached, not following"


def test_renaming_or_recovering_a_starter_copy_does_not_detach_it(db):
    _, p = db.create()
    cards = {"rat": 3}
    db.seed_decks(p["id"], [{"id": "food_otk", "name": "Food", "cards": cards}])
    db.save_decks(p["id"], [{"id": "food_otk", "name": "My Food", "cards": cards, "cover": "rat_king"}], {"food_otk": cards})
    renamed = db.decks(p["id"], {"food_otk": cards})[0]
    assert renamed["name"] == "My Food" and renamed.get("cover") == "rat_king"
    changed = {"rat": 2, "mouse": 1}                                    # the starter changes
    assert db.decks(p["id"], {"food_otk": changed})[0]["cards"] == changed, "still follows it"


def test_a_deleted_starter_copy_stays_deleted_even_when_the_starter_changes(db):
    _, p = db.create()
    cards = {"lobo": 3}
    db.seed_decks(p["id"], [{"id": "canine_buff_tempo", "name": "Canines", "cards": cards}])
    db.save_decks(p["id"], [], {"canine_buff_tempo": cards})            # the player deletes it
    changed = {"lobo": 2, "clarion": 1}
    assert db.decks(p["id"], {"canine_buff_tempo": changed}) == []


def test_link_starters_backfills_old_rows_leaving_mismatches_alone(tmp_path):
    import sqlite3
    path = tmp_path / "old.db"
    old = sqlite3.connect(path)
    old.executescript(
        "CREATE TABLE decks (profile TEXT NOT NULL, id TEXT NOT NULL, name TEXT NOT NULL, cards TEXT NOT NULL, pos INTEGER NOT NULL, PRIMARY KEY (profile, id));"
        "INSERT INTO decks VALUES ('p', 'ramp', 'Ramp', '{\"borealis\": 1}', 0);"
        "INSERT INTO decks VALUES ('p', 'egg_control', 'Egg', '{\"eagle\": 2}', 1);")
    old.commit(); old.close()
    db = Profiles(str(path))
    assert db.link_starters({"ramp": {"borealis": 1}, "egg_control": {"eon": 1}}) == (1, 1)
    decks = {d["id"]: d for d in db.decks("p", {"ramp": {"borealis": 2}, "egg_control": {"eon": 1}})}
    assert decks["ramp"]["cards"] == {"borealis": 2}, "matched the current starter: now follows it"
    assert decks["egg_control"]["cards"] == {"eagle": 2}, "differed: left alone, still its old list"
    assert db.link_starters({"ramp": {"borealis": 2}, "egg_control": {"eon": 1}}) == (0, 0), "a second run reclassifies nothing"


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
        ("bot", "Cats", "Bot (Easy)", "Ramp", 2, 0)


def test_a_finished_match_saves_the_replay_its_player_saw(monkeypatch, tmp_path):
    import gzip, json
    from animal_kingdom.web import replay
    from animal_kingdom.web.match import bot_for
    db = Profiles(":memory:")
    monkeypatch.setattr(server, "profiles", db)
    monkeypatch.setattr(server, "REPLAY_DIR", tmp_path)
    monkeypatch.delenv("AK_NO_GAME_LOGS", raising=False)
    monkeypatch.setattr(server, "save_game", lambda *a: None)
    _, p = db.create("Martin")
    m = Match("M2", Seat("ta", "Martin#1", deck="cats_midrange", profile=p["id"]))
    m.join(Seat("tb", "Bot", bot="easy", deck="ramp"))
    m.on_match_end = server.record_match
    m.ready("A")
    m.bots["A"] = bot_for("easy", 7)       # a bot plays the human seat
    live = [m.view("A")["game"]]
    while m.phase == "playing":
        m.act(m.to_act(), m.bot_move())
        live.append(m.view("A")["game"])
    (h,) = db.history(p["id"])
    assert h["my_cover"] == "king_theron" and h["opp_cover"] == "borealis"
    views = json.loads(gzip.decompress(replay.load(tmp_path, h["match"], "A")))
    assert {v["you"] for v in views} == {"A"} and views[0]["game"]["history"] == []
    assert views[-1]["game"]["result"]["winner"] == m.results[-1]["winner"]
    hands = [v["game"].pop("oppHand") for v in views]
    assert [v["game"] for v in views] == live       # exactly what the browser was sent, plus
    assert [len(h) for h in hands] == [g["handCount"]["B"] for g in live]      # the opponent's hand
    assert [h["id"] for h in hands[-1]] == [u.card_id for u in m.state.hands["B"]]
    # rebuilt from the game log, the same views
    rebuilt = replay.game_views(m.last_log, "A", {"A": "Martin#" + p["tag"], "B": "Bot"})
    assert [v["game"].pop("oppHand") for v in rebuilt] == hands and rebuilt == views


def test_a_match_against_a_person_keeps_their_deck_name_private(monkeypatch):
    from animal_kingdom.engine.state import Result
    db = Profiles(":memory:")
    monkeypatch.setattr(server, "profiles", db)
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")
    _, p = db.create("Martin")
    m = Match("M4", Seat("ta", "Martin#1", deck="cats_midrange", profile=p["id"]))
    m.join(Seat("tb", "Ana#1234", deck="ramp"))
    m.on_match_end = server.record_match
    m._start_game()
    m.state.result = Result("A", "food")
    m._check_end()
    (h,) = db.history(p["id"])
    assert (h["kind"], h["opp"], h["opp_deck"], h["opp_cover"]) == ("friend", "Ana#1234", "", "borealis")
    assert "deckName" not in m.view("A")["seats"]["B"] and m.view("A")["seats"]["A"]["deckName"] == "Cats"


def test_the_gauntlet_stays_out_of_the_history(monkeypatch):
    db = Profiles(":memory:")
    monkeypatch.setattr(server, "profiles", db)
    _, p = db.create("Martin")
    m = Match("M3", Seat("ta", "Martin#1", deck="cats_midrange", profile=p["id"]))
    m.join(Seat("tb", "Bot", bot="easy", deck="ramp"))
    m.make_gauntlet(["ramp", "egg_control"], per_seat=1)
    server.record_match(m)
    assert db.history(p["id"]) == []


def test_every_match_left_in_a_history_has_its_replay(monkeypatch, tmp_path):
    """Matches from before replays were saved get theirs from the game log; any that can't be replayed are dropped."""
    import json
    from animal_kingdom.web import replay
    from animal_kingdom.web.match import bot_for
    logs, replays = tmp_path / "logs", tmp_path / "replays"
    logs.mkdir()
    db = Profiles(":memory:")
    _, p = db.create("Martin")
    m = Match("OLD1", Seat("ta", "Martin#1", deck="cats_midrange"))
    m.join(Seat("tb", "Bot", bot="easy", deck="ramp"))
    m.ready("A")
    m.bots["A"] = bot_for("easy", 3)
    while m.phase == "playing":
        m.act(m.to_act(), m.bot_move())
    log = {k: v for k, v in m.last_log.items() if k not in ("series", "lists")}   # a log from before replays
    (logs / "web_20260101T000000_OLD1.jsonl").write_text(json.dumps(log) + "\n")
    for key in ("OLD1-0", "GONE-0", "KEPT-0"):     # GONE was never recorded; KEPT neither, but has a replay from before
        db.record(p["id"], key, kind="bot", my_deck="Cats", opp="Bot (Easy)", opp_deck="Ramp", won=1, lost=0, seat="A")
    replays.mkdir()
    (replays / "OLD1-0-A.json.gz").write_bytes(b"old")
    (replays / "KEPT-0-A.json.gz").write_bytes(b"old")
    replay.backfill(db, logs, replays)
    assert sorted(h["match"] for h in db.history(p["id"])) == ["KEPT-0", "OLD1-0"]
    assert replay.load(replays, "OLD1-0", "A") != b"old" and not (replays / "OLD1-0-A.json.gz").exists()   # upgraded
    assert replay.load(replays, "KEPT-0", "A") == b"old"
    replay.backfill(db, logs, replays)      # a second start changes nothing
    assert sorted(h["match"] for h in db.history(p["id"])) == ["KEPT-0", "OLD1-0"]


def test_a_bot_named_the_old_way_reads_the_new_way(tmp_path):
    db = Profiles(str(tmp_path / "web.db"))
    _, p = db.create("Martin")
    db.record(p["id"], "M-0", kind="bot", my_deck="Cats", opp="Bot · Normal", opp_deck="Ramp", won=1, lost=0)
    assert Profiles(str(tmp_path / "web.db")).history(p["id"])[0]["opp"] == "Bot (Normal)"


def test_a_deck_record_sums_every_match_with_it(db):
    _, p = db.create("Martin")
    db.record(p["id"], "M-0", kind="bot", my_deck="Cats", opp="Bot (Easy)", opp_deck="Ramp", won=1, lost=0, my_cover="king_theron")
    db.record(p["id"], "N-0", kind="bot", my_deck="Cats", opp="Bot (Easy)", opp_deck="Egg", won=0, lost=1, my_cover="king_theron")
    db.record(p["id"], "O-0", kind="friend", my_deck="Rats", opp="Ana#1234", opp_deck="Cats", won=1, lost=0)
    assert [(r["deck"], r["cover"], r["won"], r["lost"]) for r in db.records(p["id"])] == \
        [("Cats", "king_theron", 1, 1), ("Rats", "", 1, 0)]


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
    db.record(second["id"], "M-0", kind="bot", my_deck="Rats", opp="Bot (Easy)", opp_deck="Ramp", won=2, lost=1)
    again = db.sign_in("discord", "d-1", "martin", second["id"])
    assert again["id"] == account["id"]
    assert [d["name"] for d in db.decks(account["id"])] == ["Cats", "Rats"]
    assert [h["match"] for h in db.history(account["id"])] == ["M-0"]
    assert db.get(second["id"]) is None                                   # the guest is gone


def test_signing_in_brings_no_second_copy_of_the_starters(db, tmp_path):
    starters = [{"id": "cats", "name": "Cats", "cards": {"lion": 3}}, {"id": "ramp", "name": "Ramp", "cards": {"elephant": 3}}]
    _, first = db.create("Martin")
    db.seed_decks(first["id"], starters)
    account = db.sign_in("discord", "d-1", "martin", first["id"])
    for n in range(2):   # two more devices, each a guest with the starters, one with a deck of its own
        _, guest = db.create("Player")
        db.seed_decks(guest["id"], starters)
        if n:
            db.save_decks(guest["id"], db.decks(guest["id"]) + [{"id": "mine", "name": "Rats", "cards": {"rat": 3}}], {d["id"]: d["cards"] for d in starters})
        db.sign_in("discord", "d-1", "martin", guest["id"])
    assert [d["name"] for d in db.decks(account["id"])] == ["Cats", "Ramp", "Rats"]


def test_duplicate_untouched_starters_from_old_sign_ins_are_cleared(tmp_path):
    from animal_kingdom.web.profiles import Profiles
    path = str(tmp_path / "p.db"); a = Profiles(path)
    _, p = a.create("Martin")
    with a.db:   # what an old sign-in left: the starter twice, untouched, and an edited copy
        for i, (did, edited) in enumerate([("cats", 0), ("cats-ab12", 0), ("cats-cd34", 1)]):
            a.db.execute("INSERT INTO decks (profile, id, name, cards, pos, cover, starter, edited) VALUES (?, ?, 'Cats', '{}', ?, '', 'cats', ?)", (p["id"], did, i, edited))
    b = Profiles(path)
    assert [r[0] for r in b.db.execute("SELECT id FROM decks WHERE profile = ? ORDER BY pos", (p["id"],))] == ["cats", "cats-cd34"]


def test_the_server_serves_your_replay_and_only_yours(monkeypatch, tmp_path):
    import asyncio
    from aiohttp.test_utils import TestClient, TestServer
    from animal_kingdom.web import replay
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")
    monkeypatch.setattr(server, "REPLAY_DIR", tmp_path)

    async def run():
        async with TestClient(TestServer(server.make_app())) as c:
            me, other = [await (await c.post("/api/profile", json={})).json() for _ in range(2)]
            server.profiles.record(me["profile"]["id"], "M-0", kind="bot", my_deck="Cats", opp="Bot (Easy)", opp_deck="Ramp",
                                   won=1, lost=0, seat="B")
            replay.save(tmp_path, "M-0", "B", [{"you": "B"}, {"you": "B"}])
            r = await c.get("/api/replay/M-0", headers={"X-AK-Key": me["code"]})
            assert r.status == 200 and await r.json() == [{"you": "B"}, {"you": "B"}]
            assert (await c.get("/api/replay/M-0", headers={"X-AK-Key": other["code"]})).status == 404
            assert (await c.get("/api/replay/M-0/lists", headers={"X-AK-Key": me["code"]})).status == 404   # saved before lists were kept
            # its decklists alone, yours (seat B) and theirs, for the match history
            server.profiles.record(me["profile"]["id"], "N-0", kind="bot", my_deck="Cats", opp="Bot (Easy)", opp_deck="Ramp",
                                   won=1, lost=0, seat="B")
            replay.save(tmp_path, "N-0", "B", [{"you": "B", "lists": {"A": {"owl": 3}, "B": {"lion": 2}}}])
            r = await c.get("/api/replay/N-0/lists", headers={"X-AK-Key": me["code"]})
            assert r.status == 200 and await r.json() == {"mine": {"lion": 2}, "theirs": {"owl": 3}}
            assert (await c.get("/api/replay/N-0/lists", headers={"X-AK-Key": other["code"]})).status == 404
    asyncio.run(run())


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
