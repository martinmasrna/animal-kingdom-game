"""The web client's match model: series flow, seat checks, and what each seat's view may show."""

import json
import random

import pytest

from animal_kingdom.engine import rules
from animal_kingdom.engine.state import EngineError
from animal_kingdom.web.match import Match, Seat


def _match(bots=("easy", "easy"), decks=("cats_midrange", "egg_control")) -> Match:
    m = Match("T", Seat("ta", "A", bot=bots[0], deck=decks[0]))
    m.join(Seat("tb", "B", bot=bots[1], deck=decks[1]))
    return m


def _play_out_game(m: Match, rng: random.Random) -> None:
    while m.phase == "playing":
        s = m.to_act()
        m.act(s, rng.choice(rules.legal_actions(m.state)).to_dict())


def test_a_match_starts_as_soon_as_both_seats_are_filled():
    m = Match("T", Seat("ta", "A", deck="ramp"))
    assert m.phase == "lobby"
    m.join(Seat("tb", "B", deck="ramp"))
    assert m.phase == "playing"
    m.ready("A")                          # an older client's Ready changes nothing
    assert m.phase == "playing"


def test_a_match_is_one_game_and_a_rematch_lets_the_loser_go_first():
    rng = random.Random(3)
    m = _match()
    _play_out_game(m, rng)
    assert m.phase == "match_over" and len(m.results) == 1
    last = m.results[-1]
    m.rematch()
    m.ready("A")                          # bot seats are ready on their own
    assert m.phase == "playing" and m.results == []
    if last["winner"]:
        assert m.state.first_player != last["winner"]


def test_conceding_loses_the_game_and_ends_the_match():
    m = Match("T", Seat("ta", "A", deck="ramp"))
    m.join(Seat("tb", "B", deck="ramp")); m.ready("A"); m.ready("B")
    m.concede("A")
    assert m.results[-1]["winner"] == "B" and m.results[-1]["reason"] == "concede"
    assert m.phase == "match_over" and m.view("A")["game"]["result"]["reason"] == "concede"
    with pytest.raises(EngineError):
        m.concede("A")                    # nothing left to concede
    m.rematch(); m.ready("A"); m.ready("B")
    assert m.state.first_player == "A"    # the loser goes first, as after any loss


def test_the_view_marks_units_the_enemy_cannot_choose():
    """An Armadillo's neighbours have Stealth; the board must say so, or a Viper or Taipan that finds no
    target looks broken (Martin's game 2026-09-30: Groundhog and Scrooge next to Armadillos)."""
    from animal_kingdom.engine.state import UnitInstance
    m = Match("T", Seat("ta", "A", deck="ramp"))
    m.join(Seat("tb", "B", deck="ramp")); m.ready("A"); m.ready("B")
    st = m.state
    st.board = {"4,2": [UnitInstance("armadillo", "B", 901)], "4,1": [UnitInstance("groundhog", "B", 902)],
                "2,1": [UnitInstance("groundhog", "B", 903)]}
    board = m.view("A")["game"]["board"]
    assert board["4,1"][0].get("hidden") and not board["2,1"][0].get("hidden")


def test_rejects_the_wrong_seat_and_illegal_moves():
    m = _match()
    s = m.to_act()
    other = "B" if s == "A" else "A"
    with pytest.raises(EngineError):
        m.act(other, {"kind": "draw"})
    with pytest.raises(EngineError):
        m.act(s, {"kind": "place", "card_id": "lion", "target": ["hq", other]})


def test_view_hides_the_opponents_hand_and_deck_order():
    rng = random.Random(7)
    m = _match()
    for _ in range(12):
        m.act(m.to_act(), rng.choice(rules.legal_actions(m.state)).to_dict())
    view = m.view("A")
    game = view["game"]
    assert [h["iid"] for h in game["hand"]] == [u.iid for u in m.state.hands["A"]]
    b_hand_iids = {u.iid for u in m.state.hands["B"]}
    assert not b_hand_iids & {h["iid"] for h in game["hand"]}
    assert "decks" not in game and "hands" not in json.dumps(game)
    # The opponent's unseen cards are a multiset, which open decklists make public anyway.
    assert sum(game["unseen"].values()) == len(m.state.decks["B"]) + len(m.state.hands["B"])


def test_every_view_is_json_and_offers_legal_choices():
    rng = random.Random(11)
    m = _match(decks=("egg_control", "food_otk"))
    while m.phase == "playing":
        s = m.to_act()
        game = json.loads(json.dumps(m.view(s)))["game"]
        legal = rules.legal_actions(m.state)
        if game["pending"] and game["pending"]["mode"] == "choice":
            offered = {json.dumps(o["v"]) for o in game["pending"]["options"]}
            assert offered == {json.dumps(a.choice) for a in legal if a.kind == "choice" and a.choice != "__skip__"}
        m.act(s, rng.choice(legal).to_dict())


def test_game_log_replays_to_the_same_result():
    from animal_kingdom.sim.replay import replay
    rng = random.Random(5)
    logs = []
    m = _match(decks=("food_otk", "aggro_hq_rush"))
    m.on_game_end = lambda match, rec: logs.append(json.loads(json.dumps(rec)))
    _play_out_game(m, rng)
    _, result, _ = replay(logs[0])
    assert (result.winner, result.reason) == (logs[0]["winner"], logs[0]["reason"])


def test_the_game_log_times_every_action():
    rng = random.Random(9)
    logs = []
    m = _match()
    m.on_game_end = lambda match, rec: logs.append(rec)
    _play_out_game(m, rng)
    assert len(logs[0]["action_times"]) == len(logs[0]["actions"])


def test_gauntlet_runs_its_schedule_opponent_by_opponent_alternating_who_starts():
    from animal_kingdom.engine.state import Result
    m = Match("G", Seat("ta", "You", deck="egg_control"))
    m.join(Seat("tb", "Bot", bot="easy", deck="aggro_hq_rush"))
    m.make_gauntlet(["aggro_hq_rush", "ramp"], per_seat=1)
    m._start_game()
    seen = []
    for i in range(4):
        seen.append((m.seats["B"].deck, m.state.first_player))
        m.state.result = Result("A" if i % 2 else "B", "hq_capture")
        m._check_end()
        if i < 3:
            assert m.phase == "game_over"
            m.next_game()
    assert seen == [("aggro_hq_rush", "A"), ("aggro_hq_rush", "B"), ("ramp", "A"), ("ramp", "B")]
    assert m.phase == "match_over"
    g = m.view("A")["gauntlet"]
    assert g["played"] == 4 and g["next"] is None
    assert [(r["w"], r["l"]) for r in g["record"]] == [(1, 1), (1, 1)]


def test_a_saved_match_resumes_mid_game_after_a_restart():
    m = _match()
    rng = random.Random(3)
    for _ in range(12):                                  # into the game, some moves made
        s = m.to_act()
        m.act(s, rng.choice(rules.legal_actions(m.state)))
    saved = json.loads(json.dumps(m.to_dict()))          # through JSON, as on disk
    r = Match.from_dict(saved)
    assert r.view("A")["game"] == m.view("A")["game"]
    assert r.to_act() == m.to_act() and set(r.bots) == set(m.bots)
    s = r.to_act()
    r.act(s, rules.legal_actions(r.state)[0])            # and it plays on


def test_decklist_problems_follow_the_deck_rules():
    from animal_kingdom.decks import PREMADE_DECKS, decklist_problems
    cats = PREMADE_DECKS["cats_midrange"]
    assert decklist_problems(cats) == []
    assert decklist_problems(cats[:-1])                                   # 29 cards
    two_kings = [c for c in cats if c != "prince_leo"] + ["king_theron"]
    assert any("King Theron" in p for p in decklist_problems(two_kings))
    reserve = [c for c in cats if c != "prince_leo"] + ["unnamed_giant"]
    assert any("collectible" in p for p in decklist_problems(reserve))
    bench = list(cats)
    bench[bench.index("lion")] = "eagle"                                  # a common for a common
    assert decklist_problems(bench) == []                                 # the bench is collectible


def test_custom_deck_resolves_to_a_playable_slug(tmp_path, monkeypatch):
    from animal_kingdom.decks import PREMADE_DECKS, load_premade_deck
    from animal_kingdom.engine.state import EngineError
    from animal_kingdom.web import custom_decks
    from animal_kingdom.web.match import DECK_NAMES
    monkeypatch.setattr(custom_decks, "DECKS_FILE", tmp_path / "decks.json")
    cats = PREMADE_DECKS["cats_midrange"]
    slug = custom_decks.resolve({"name": "My cats", "list": cats})
    assert slug.startswith("custom_") and DECK_NAMES[slug] == "My cats"
    assert sorted(load_premade_deck(slug)) == sorted(cats)
    assert custom_decks.resolve("ramp") == "ramp"
    import pytest
    with pytest.raises(EngineError):
        custom_decks.resolve({"name": "bad", "list": cats[:-1]})


def test_reverse_gauntlet_rotates_the_players_deck_against_the_bots_fixed_one():
    from animal_kingdom.engine.state import Result
    m = Match("R", Seat("ta", "You", deck="aggro_hq_rush"))
    m.join(Seat("tb", "Bot", bot="easy", deck="goodstuff"))
    m.make_gauntlet(["aggro_hq_rush", "ramp"], per_seat=1, rotating="A")
    m._start_game()
    seen = []
    for i in range(4):
        seen.append((m.seats["A"].deck, m.seats["B"].deck, m.state.first_player))
        m.state.result = Result("A" if i < 3 else "B", "food")
        m._check_end()
        if i < 3:
            assert m.view("A")["gauntlet"]["next"]["yours"]
            m.next_game()
    assert seen == [("aggro_hq_rush", "goodstuff", "A"), ("aggro_hq_rush", "goodstuff", "B"),
                    ("ramp", "goodstuff", "A"), ("ramp", "goodstuff", "B")]
    g = m.view("A")["gauntlet"]
    assert [(r["deckName"], r["w"], r["l"]) for r in g["record"]] == [("Aggro", 2, 0), ("Ramp", 1, 1)]


# ----------------------------------------------------------------- turn clock
def _two_humans(monkeypatch, t0=1000.0):
    from animal_kingdom.web import match as M
    now = [t0]
    monkeypatch.setattr(M.time, "time", lambda: now[0])
    m = Match("C", Seat("ta", "A", deck="cats_midrange"))
    m.join(Seat("tb", "B", deck="ramp"))
    m._start_game()
    return m, now


def test_bot_games_have_no_clock():
    m = _match()
    assert m.clock is None and m.clock_deadline() is None


def test_the_free_window_is_lost_then_the_bank_drains(monkeypatch):
    from animal_kingdom.web.match import CLOCK_BANK, CLOCK_FREE
    m, now = _two_humans(monkeypatch)
    from animal_kingdom.engine.actions import ChoiceAction
    while m.state.pending is not None:                  # the mulligan's shared window touches no bank
        m.act(m.to_act(), ChoiceAction("__skip__"))
    assert m.clock["bank"] == {"A": CLOCK_BANK, "B": CLOCK_BANK}
    s = m.to_act()
    now[0] += CLOCK_FREE + 12                           # 12 s past the free window
    m.act(s, rules.legal_actions(m.state)[0])
    assert m.clock["bank"][s] == CLOCK_BANK - 12


def test_out_of_time_declines_the_choice_then_ends_the_turn(monkeypatch):
    from animal_kingdom.web.match import CLOCK_BANK, CLOCK_FREE
    m, now = _two_humans(monkeypatch)
    from animal_kingdom.engine.actions import ChoiceAction
    while m.state.pending is not None:                  # both keep their opening hands
        m.act(m.to_act(), ChoiceAction("__skip__"))
    s, turn = m.to_act(), m.state.turn_counter
    assert not m.time_out()                             # nobody is out of time yet
    now[0] += CLOCK_FREE + CLOCK_BANK + 1
    assert m.time_out()
    assert m.state.turn_counter == turn + 1 and m.to_act() != s
    assert m.clock["bank"][s] == 0 and m.history == []  # an ended turn is not a move


def test_ending_a_turn_by_hand_is_not_recorded_as_a_draw(monkeypatch):
    from animal_kingdom.engine.actions import ChoiceAction, PassAction
    m, _ = _two_humans(monkeypatch)
    while m.state.pending is not None:
        m.act(m.to_act(), ChoiceAction("__skip__"))
    m.act(m.to_act(), PassAction())
    assert m.history == []


def test_bot_levels_are_the_configurations_the_simulations_measure():
    from animal_kingdom.sim.runner import make_bot
    from animal_kingdom.web.match import BOT_LEVELS, bot_for
    for level, kind in BOT_LEVELS.items():
        assert vars(bot_for(level, 7)).keys() == vars(make_bot(kind, 7)).keys()
        web, sim = bot_for(level, 7), make_bot(kind, 7)
        for attr in ("determinizations", "beam_width", "root_width", "reply_width", "max_search_nodes"):
            assert getattr(web, attr, None) == getattr(sim, attr, None), (level, attr)


def test_a_bot_waits_for_the_watching_players_screen_never_longer_than_the_cap(monkeypatch):
    """The bot's next move waits until each person watching has played the events out (their 'played' report), and no
    longer than BOT_WAIT_MAX if a screen never reports (server._watched)."""
    import asyncio, time
    from animal_kingdom.web import server
    m = Match("WAT", Seat("ta", "A", deck="cats_midrange"))
    m.join(Seat("tb", "Bot", bot="easy", deck="ramp"))
    m._start_game()
    m.seq = 7
    hub = server.Hub()
    hub.sockets[m.id] = {(object(), "A")}            # player A watches
    monkeypatch.setattr(server, "BOT_WAIT_MAX", 0.4)
    async def run():
        t0 = time.time(); await hub._watched(m); waited = time.time() - t0
        assert 0.35 < waited < 0.8, f"a silent screen holds the bot only to the cap ({waited:.2f} s)"
        m.played["A"] = 7
        t0 = time.time(); await hub._watched(m)
        assert time.time() - t0 < 0.1, "a screen that has played everything lets it go at once"
        hub.sockets[m.id] = set()                    # nobody watching: no wait at all
        m.played.clear(); t0 = time.time(); await hub._watched(m)
        assert time.time() - t0 < 0.1
    asyncio.run(run())


def test_every_view_states_the_decision_and_the_clock():
    """Who decides what, and the clock, are always in the view (never a missing field read as 'no')."""
    m = Match("DEC", Seat("ta", "A", deck="cats_midrange"))
    m.join(Seat("tb", "Bot", bot="easy", deck="ramp"))
    m._start_game()
    v = m.view("A")["game"]
    assert v["decision"] == "mulligan" and v["clock"] == {"on": False}   # a bot game has no clock, and says so
    from animal_kingdom.engine.actions import ChoiceAction
    while m.state.pending:
        m.act(m.to_act(), ChoiceAction("__skip__"))
    me = m.to_act(); them = "B" if me == "A" else "A"
    assert m.view(me)["game"]["decision"] == "yours" and m.view(them)["game"]["decision"] == "theirs"


def test_a_pick_from_your_own_hand_names_what_it_does():
    """Magpie's discard and Raven's shuffle say so in the view, so the client can head them (feedback 2026-10-01: a lit hand read as 'play one')."""
    from animal_kingdom.engine.actions import ChoiceAction, PlaceAction
    from animal_kingdom.engine.state import UnitInstance
    m = Match("ASK", Seat("ta", "A", deck="cats_midrange"))
    m.join(Seat("tb", "Bot", bot="easy", deck="ramp"))
    m._start_game()
    while m.state.pending:
        m.act(m.to_act(), ChoiceAction("__skip__"))
    me = m.to_act()
    m.state.hands[me] = [UnitInstance(c, me, m.state.new_iid()) for c in ("magpie", "mouse", "lion")]
    target = m.view(me)["game"]["legal"]["place"]["magpie"][0]
    m.act(me, PlaceAction("magpie", tuple(target)))
    p = m.view(me)["game"]["pending"]
    assert p["kind"] == "discard" and {o["kind"] for o in p["options"]} == {"hand"}


def test_a_spikes_animal_wears_its_badge_until_its_spikes_are_used():
    """Spikes fire once: the view marks the animal until then, so the board shows the danger only while it's real."""
    from animal_kingdom.engine.actions import ChoiceAction
    from animal_kingdom.engine.state import UnitInstance
    m = Match("SPK", Seat("ta", "A", deck="cats_midrange"))
    m.join(Seat("tb", "Bot", bot="easy", deck="ramp"))
    m._start_game()
    while m.state.pending:
        m.act(m.to_act(), ChoiceAction("__skip__"))
    hog = UnitInstance("hedgehog", "B", m.state.new_iid())
    m.state.board["3,2"] = [hog]
    top = lambda: m.view("A")["game"]["board"]["3,2"][-1]
    assert top().get("spikes") is True
    hog.retaliation_used = True
    assert "spikes" not in top()
