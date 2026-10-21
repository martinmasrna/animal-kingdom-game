"""The web client's match model: series flow, seat checks, and what each seat's view may show."""

import json
import random

import pytest

from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import SKIP
from animal_kingdom.engine.state import EngineError
from animal_kingdom.web.match import Match, Seat


def _match(bots=("easy", "easy"), decks=("cats", "egg_control")) -> Match:
    m = Match("T", Seat("ta", "A", bot=bots[0], deck=decks[0]))
    m.join(Seat("tb", "B", bot=bots[1], deck=decks[1]))
    return m


def _play_out_game(m: Match, rng: random.Random) -> None:
    while m.phase == "playing":
        s = m.to_act()
        m.act(s, rng.choice(rules.legal_actions(m.state)).to_dict())


def test_a_match_starts_as_soon_as_both_seats_are_filled():
    m = Match("T", Seat("ta", "A", deck="giants"))
    assert m.phase == "lobby"
    m.join(Seat("tb", "B", deck="giants"))
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
    m = Match("T", Seat("ta", "A", deck="giants"))
    m.join(Seat("tb", "B", deck="giants")); m.ready("A"); m.ready("B")
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
    m = Match("T", Seat("ta", "A", deck="giants"))
    m.join(Seat("tb", "B", deck="giants")); m.ready("A"); m.ready("B")
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
    while m.state.pending:               # a choice in progress also counts the cards it holds (a Raven's put-back)
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
    m = _match(decks=("food_otk", "den_rush"))
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
    m.join(Seat("tb", "Bot", bot="easy", deck="den_rush"))
    m.make_gauntlet(["den_rush", "giants"], per_seat=1)
    m._start_game()
    seen = []
    for i in range(4):
        seen.append((m.seats["B"].deck, m.state.first_player))
        m.state.result = Result("A" if i % 2 else "B", "hq_capture")
        m._check_end()
        if i < 3:
            assert m.phase == "game_over"
            m.next_game()
    assert seen == [("den_rush", "A"), ("den_rush", "B"), ("giants", "A"), ("giants", "B")]
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
    cats = PREMADE_DECKS["cats"]
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
    cats = PREMADE_DECKS["cats"]
    slug = custom_decks.resolve({"name": "My cats", "list": cats})
    assert slug.startswith("custom_") and DECK_NAMES[slug] == "My cats"
    assert sorted(load_premade_deck(slug)) == sorted(cats)
    assert custom_decks.resolve("giants") == "giants"
    import pytest
    with pytest.raises(EngineError):
        custom_decks.resolve({"name": "bad", "list": cats[:-1]})


def test_reverse_gauntlet_rotates_the_players_deck_against_the_bots_fixed_one():
    from animal_kingdom.engine.state import Result
    m = Match("R", Seat("ta", "You", deck="den_rush"))
    m.join(Seat("tb", "Bot", bot="easy", deck="goodstuff"))
    m.make_gauntlet(["den_rush", "giants"], per_seat=1, rotating="A")
    m._start_game()
    seen = []
    for i in range(4):
        seen.append((m.seats["A"].deck, m.seats["B"].deck, m.state.first_player))
        m.state.result = Result("A" if i < 3 else "B", "food")
        m._check_end()
        if i < 3:
            assert m.view("A")["gauntlet"]["next"]["yours"]
            m.next_game()
    assert seen == [("den_rush", "goodstuff", "A"), ("den_rush", "goodstuff", "B"),
                    ("giants", "goodstuff", "A"), ("giants", "goodstuff", "B")]
    g = m.view("A")["gauntlet"]
    assert [(r["deckName"], r["w"], r["l"]) for r in g["record"]] == [("Den Rush", 2, 0), ("Giants", 1, 1)]


# ----------------------------------------------------------------- turn clock
def _two_humans(monkeypatch, t0=1000.0):
    from animal_kingdom.web import match as M
    now = [t0]
    monkeypatch.setattr(M.time, "time", lambda: now[0])
    m = Match("C", Seat("ta", "A", deck="cats"))
    m.join(Seat("tb", "B", deck="giants"))
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


def test_a_turns_clock_waits_for_its_player_to_see_the_opponents_moves(monkeypatch):
    """The turn's clock starts once the player's screen has played out what led to it (played_out), at most
    CLOCK_CATCHUP_MAX later; a screen that never says so is charged from the turn's start."""
    from animal_kingdom.engine.actions import ChoiceAction, PassAction
    from animal_kingdom.web.match import CLOCK_BANK, CLOCK_FREE, CLOCK_CATCHUP_MAX
    m, now = _two_humans(monkeypatch)
    while m.state.pending is not None:
        m.act(m.to_act(), ChoiceAction("__skip__"))
    s = m.to_act(); m.act(s, PassAction())
    o = m.to_act()
    now[0] += 5                                         # the opponent's moves play out on o's screen for 5 s
    assert m.played_out(o, m.seq)
    now[0] += CLOCK_FREE + 12
    m.act(o, rules.legal_actions(m.state)[0])
    assert m.clock["bank"][o] == CLOCK_BANK - 12        # the 5 s of watching cost nothing
    while m.to_act() == o:
        m.act(o, PassAction() if m.state.pending is None else ChoiceAction("__skip__"))
    now[0] += 30                                        # a screen that took 30 s gets CLOCK_CATCHUP_MAX back
    assert m.played_out(s, m.seq)
    assert m.clock["since"] == now[0] - 30 + CLOCK_CATCHUP_MAX
    assert not m.played_out(s, m.seq)                   # once only


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


def test_the_bots_play_the_bot_pool_only():
    """Bots are opponents for people (Martin, 2026-10-18): ranked, the ladder seed and the benchmark panel use decks.BOT_DECKS,
    nine premades the bots pilot well; the other premades stay player decks (a bot losing with one teaches it is bad)."""
    import sqlite3
    from animal_kingdom.decks import BOT_DECKS, PANEL_OPPONENTS, PREMADE_DECKS
    from animal_kingdom.sim.ladder_seed import bots
    from animal_kingdom.web import ladder as ranking
    from animal_kingdom.web.server import bot_rungs
    assert set(BOT_DECKS) < set(PREMADE_DECKS) and set(PANEL_OPPONENTS) <= set(BOT_DECKS)
    assert {deck for _, deck in bots()} == set(BOT_DECKS)
    lad = ranking.Ladder(sqlite3.connect(":memory:"), sorted(BOT_DECKS))
    lad.seed_bots({ranking.bot_id("expert", "egg_control"): 1500.0})   # a retired deck's row from an older seed
    assert "egg_control" not in {ranking.parse_bot(lad.nearest_bot(1500, __import__("random").Random(i)))[1] for i in range(50)}
    assert bot_rungs(lad.table()) == bot_rungs([(lid, r) for lid, r in lad.table() if "egg_control" not in lid])


def test_the_expert_is_the_deepened_referee():
    """The Expert (shipped 2026-10-20) is the referee with two turns of sight, den sense, the reply as a turn and the
    target-aware weights, deepening under a time budget below BOT_THINK_MAX; since 2026-10-21 it values food as the race
    on a curve, with no net-food term. Normal is the TurnBot."""
    from animal_kingdom.web.match import bot_for
    from animal_kingdom.web.server import BOT_THINK_MAX
    bot = bot_for("expert", 7)
    assert bot.depth == 1 and bot.den_sense and bot.reply_turns == 3 and 0 < bot.time_budget < BOT_THINK_MAX
    assert bot.weights.pending_target > 0 and bot.weights.buried_presence > 0
    assert bot.weights.food_progress == 0 and bot.weights.food_curve > 1 and bot.weights.food_race
    normal = bot_for("normal", 7)
    assert normal.__class__.__name__ == "TurnBot" and normal.weights.hq_threat_reach > 0   # the den-front reach term (2026-10-21)
    assert bot.weights.hq_threat_reach == 0                                                 # the Expert's reply search covers it


def test_a_bot_waits_for_the_watching_players_screen_never_longer_than_the_cap(monkeypatch):
    """The bot's next move waits until each person watching has played the events out (their 'played' report), and no
    longer than BOT_WAIT_MAX if a screen never reports (server._watched)."""
    import asyncio, time
    from animal_kingdom.web import server
    m = Match("WAT", Seat("ta", "A", deck="cats"))
    m.join(Seat("tb", "Bot", bot="easy", deck="giants"))
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
    m = Match("DEC", Seat("ta", "A", deck="cats"))
    m.join(Seat("tb", "Bot", bot="easy", deck="giants"))
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
    m = Match("ASK", Seat("ta", "A", deck="cats"))
    m.join(Seat("tb", "Bot", bot="easy", deck="giants"))
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
    m = Match("SPK", Seat("ta", "A", deck="cats"))
    m.join(Seat("tb", "Bot", bot="easy", deck="giants"))
    m._start_game()
    while m.state.pending:
        m.act(m.to_act(), ChoiceAction("__skip__"))
    hog = UnitInstance("hedgehog", "B", m.state.new_iid())
    m.state.board["3,2"] = [hog]
    top = lambda: m.view("A")["game"]["board"]["3,2"][-1]
    assert top().get("spikes") is True
    hog.retaliation_used = True
    assert "spikes" not in top()


def test_a_poison_animal_wears_its_badge_printed_or_from_the_legendary_jellyfish():
    from animal_kingdom.engine.actions import ChoiceAction
    from animal_kingdom.engine.state import UnitInstance
    m = Match("PSN", Seat("ta", "A", deck="cats"))
    m.join(Seat("tb", "Bot", bot="easy", deck="fish"))
    m._start_game()
    while m.state.pending:
        m.act(m.to_act(), ChoiceAction("__skip__"))
    m.state.board["3,2"] = [UnitInstance("jellyfish", "B", m.state.new_iid())]
    m.state.board["4,2"] = [UnitInstance("sunfish", "B", m.state.new_iid())]
    board = lambda: m.view("A")["game"]["board"]
    assert board()["3,2"][-1].get("poison") is True and "poison" not in board()["4,2"][-1]
    m.state.board["4,1"] = [UnitInstance("jellyfish_legend", "B", m.state.new_iid())]   # next to the Sunfish
    assert board()["4,2"][-1].get("poison") is True

def test_the_opponents_mulligan_never_shows_in_their_unseen_cards():
    """A card the opponent sends back in their mulligan is set aside until they're done: their 'unseen' cards still count
    it, or the decklist panel would show which cards they threw back (Martin, 2026-10-02)."""
    from collections import Counter
    from animal_kingdom.engine.actions import ChoiceAction
    m = Match("MUL", Seat("ta", "A", deck="cats"))
    m.join(Seat("tb", "B", deck="giants"))
    m._start_game()
    m.act("B", ChoiceAction(m.state.hands["B"][0].iid))
    v = m.view("A")
    assert Counter(v["game"]["unseen"]) == Counter(v["lists"]["B"])


def test_a_choice_holding_the_opponents_cards_never_shows_in_their_unseen_cards():
    """A Scout's three cards and a Raven's put-back sit outside the deck and hand while the opponent chooses: their
    'unseen' cards still count them, or the decklist panel shows what they're looking at (Martin, 2026-10-02)."""
    from collections import Counter
    m = Match("SCO", Seat("ta", "A", deck="cats"))
    m.join(Seat("tb", "B", deck="giants"))
    m._start_game()
    st = m.state
    st.effect_stack.append({"op": "scout", "player": "B", "spec": None, "pulled": [st.decks["B"].pop() for _ in range(3)]})
    v = m.view("A")
    assert Counter(v["game"]["unseen"]) == Counter(v["lists"]["B"])
    st.decks["B"] += st.effect_stack.pop()["pulled"]
    st.effect_stack.append({"op": "raven_dig", "player": "B", "remaining": 1, "shuffled": [st.hands["B"].pop().card_id]})
    v = m.view("A")
    assert Counter(v["game"]["unseen"]) == Counter(v["lists"]["B"])


def test_a_roam_is_offered_taken_and_written_into_the_history():
    """Roam (keywords.md) on a test-only card: the view lists where each roaming animal may go, the seat sends the roam
    as a dict, and the history records it as the animal that roamed."""
    from animal_kingdom.engine.state import UnitInstance
    from ._helpers import cards_with
    m = Match("T", Seat("ta", "A", deck="giants"))
    m.join(Seat("tb", "B", deck="giants"))
    st = m.state
    st.cards = cards_with({"id": "t_roamer", "base_strength": 4, "keywords": ["Roam"]})
    st.pending, st.effect_stack, st.current = None, [], "A"
    st.board = {"1,2": [UnitInstance("t_roamer", "A", 901)]}
    legal = m.view("A")["game"]["legal"]
    assert legal["roam"] == {"1,2": [["cr", "1,1"], ["cr", "1,3"], ["cr", "2,2"]]}
    m.act("A", {"kind": "roam", "from": "1,2", "target": ["cr", "1,1"]})
    assert [u.card_id for u in st.board["1,1"]] == ["t_roamer"]
    move = m.view("A")["game"]["history"][-1]
    assert (move["kind"], move["card"], move["target"]) == ("roam", "t_roamer", ["cr", "1,1"])
    assert m.actions[-1] == {"kind": "roam", "from": "1,2", "target": ["cr", "1,1"]}
    json.dumps(m.view("B"))


def test_copies_of_a_card_that_differ_in_strength_each_get_their_places_and_the_clicked_one_plays():
    m = Match("T", Seat("ta", "A", deck="giants"))
    m.join(Seat("tb", "B", deck="giants"))
    st = m.state
    while st.pending:                                   # past the mulligans
        m.act(st.pending["chooser"], {"kind": "choice", "choice": SKIP})
    s = st.current
    st.hands[s].clear()
    for _ in range(3):
        st.add_to_hand(s, "elephant")
    strong, weak, weak2 = st.hands[s]
    strong.strength_counter = 2
    legal, _ = m._decision(s)
    assert set(legal["copies"]) == {str(strong.iid), str(weak.iid), str(weak2.iid)}
    target = legal["copies"][str(weak2.iid)][0]
    m.act(s, {"kind": "place", "card_id": "elephant", "target": target, "iid": weak2.iid})
    assert [u.strength_counter for u in st.hands[s]] == [2, 0]


def test_a_gauntlet_leaves_out_the_premade_your_custom_deck_copies(monkeypatch, tmp_path):
    """The play screen can send a premade as a custom list; that premade is still the mirror, not an opponent. The gauntlet's
    field is the starter decks (the bots' other decks are opponents on the ladder, not in the gauntlet)."""
    import asyncio
    from aiohttp.test_utils import TestClient, TestServer
    from animal_kingdom.decks import PREMADE_DECKS
    from animal_kingdom.engine.cards import DECK_SLUGS
    from animal_kingdom.web import custom_decks, server
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")
    monkeypatch.setattr(custom_decks, "DECKS_FILE", tmp_path / "web_decks.json")

    async def run():
        async with TestClient(TestServer(server.make_app())) as c:
            a = await (await c.post("/api/profile", json={})).json()
            deck = {"name": "My Cats", "list": list(PREMADE_DECKS["cats"])}
            m = await (await c.post("/api/match", json={"deck": deck, "gauntlet": {"level": "easy", "per_seat": 1}},
                                    headers={"X-AK-Key": a["code"]})).json()
            field = {g["deck"] for g in server.hub.matches[m["id"]].schedule}
            assert "cats" not in field and field == set(DECK_SLUGS) - {"cats"}
    asyncio.run(run())


def test_the_remove_pile_and_a_card_choice_show_each_card_at_its_strength_now():
    """A Python in the Remove Pile has grown like any Python: the pile and the Raccoon's choice show that, not its 0."""
    from animal_kingdom.engine import effects
    from animal_kingdom.engine.strength import card_strength
    from ._helpers import put
    m = _match(decks=("aristocrats", "cats"))
    m._start_game()
    st = m.state
    for cid, owner in (("python", "A"), ("lion", "B"), ("mouse", "A")):
        put(st, "3,2", cid, owner)
        effects.remove_top(st, "3,2", by_player="B")   # each removal grows A's Pythons, the one in the pile too
    grown = card_strength(st, "python", "A")
    assert grown > 0
    pile = m.view("A")["game"]["pile"]
    assert {"id": "python", "owner": "A", "str": grown} in pile and {"id": "lion", "owner": "B", "str": 7} in pile
    assert m._describe_option("python", "A") == {"v": "python", "kind": "card", "id": "python", "str": grown}


def test_play_from_here_seats_you_in_the_other_chair_at_that_round(monkeypatch, tmp_path):
    """Martin, 2026-10-21: "what would you do as the bot here?" asked on the real board. From a replay, 'Play from here'
    rebuilds the logged game at the start of the other seat's turn in the round shown, seats you there with the Expert on
    your old deck, and the game is neither logged nor rated. The log here is his game GMIDKA (the Falcons in the front)."""
    import asyncio, shutil
    from aiohttp.test_utils import TestClient, TestServer
    from animal_kingdom.web import custom_decks, server
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")
    monkeypatch.setattr(custom_decks, "DECKS_FILE", tmp_path / "web_decks.json")
    logs = tmp_path / "logs"; logs.mkdir()
    src = next(p for p in (server.LOG_DIR).glob("web_*_GMIDKA.jsonl"))
    shutil.copy(src, logs / src.name)
    monkeypatch.setattr(server, "LOG_DIR", logs)

    async def run():
        async with TestClient(TestServer(server.make_app())) as c:
            a = await (await c.post("/api/profile", json={})).json()
            monkeypatch.setattr(server.profiles, "match", lambda pid, key: {"seat": "A"} if key == "GMIDKA-0" else None)   # his match
            r = await c.post("/api/match", json={"from": {"match": "GMIDKA", "series": 0, "round": 4, "seat": "B"}}, headers={"X-AK-Key": a["code"]})
            assert r.status == 200, await r.text()
            m = await r.json()
            assert m["seat"] == "B"
            match = server.hub.matches[m["id"]]
            st = match.state
            assert match.takeover and match.on_game_end is None and match.phase == "playing"
            assert st.turn_counter // 2 + 1 == 4 and st.player_to_act() == "B" and st.pending is None
            assert not match.seats["B"].is_bot and match.seats["A"].bot == "expert" and "A" in match.bots
            assert {c.card_id for c in st.hands["B"]} == {"leopard_legend", "orca", "honey_badger", "locust"}
            view = match.view("B")
            assert view["you"] == "B" and view["phase"] == "playing"
            # a round with no turn of that seat is refused; a stranger's match is not found
            r = await c.post("/api/match", json={"from": {"match": "GMIDKA", "series": 0, "round": 40, "seat": "B"}}, headers={"X-AK-Key": a["code"]})
            assert r.status == 400
            r = await c.post("/api/match", json={"from": {"match": "GMIDKA", "series": 1, "round": 6}}, headers={"X-AK-Key": a["code"]})
            assert r.status == 404
            # the flag survives a restart
            again = type(match).from_dict(match.to_dict())
            assert again.takeover
    asyncio.run(run())


def test_a_study_lists_its_positions_from_the_logs(monkeypatch, tmp_path):
    """#/study/<name> (Martin, 2026-10-21): the positions of studies/<name>.json, each with the decks and the round, only
    those whose game is in the logs; an unknown study is 404."""
    import asyncio, json, shutil
    from aiohttp.test_utils import TestClient, TestServer
    from animal_kingdom.web import server
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")
    logs = tmp_path / "logs"; logs.mkdir()
    src = next(p for p in server.LOG_DIR.glob("web_*_GMIDKA.jsonl"))
    shutil.copy(src, logs / src.name)
    monkeypatch.setattr(server, "LOG_DIR", logs)
    studies = tmp_path / "studies"; studies.mkdir()
    (studies / "falcons.json").write_text(json.dumps({"title": "Falcons", "positions": [
        {"match": "GMIDKA", "round": 4, "seat": "B"}, {"match": "NOPE00", "round": 2, "seat": "A"}]}))
    monkeypatch.setattr(server, "STUDY_DIR", studies); monkeypatch.setattr(server, "STUDY_DATA_DIR", tmp_path / "none")

    async def run():
        async with TestClient(TestServer(server.make_app())) as c:
            a = await (await c.post("/api/profile", json={})).json()
            r = await c.get("/api/study/falcons", headers={"X-AK-Key": a["code"]})
            assert r.status == 200, await r.text()
            s = await r.json()
            assert s["title"] == "Falcons" and len(s["positions"]) == 1
            p = s["positions"][0]
            assert p["match"] == "GMIDKA" and p["round"] == 4 and p["seat"] == "B" and p["botDeck"] == "Teeth and Claws" and p["rounds"] == 4
            assert (await c.get("/api/study/nothing", headers={"X-AK-Key": a["code"]})).status == 404
    asyncio.run(run())


def test_the_studies_list_shows_a_player_only_their_own(monkeypatch, tmp_path):
    """Settings lists the studies (GET /api/studies) whose owner is you, or that name no owner; another player's is not shown."""
    import asyncio, json
    from aiohttp.test_utils import TestClient, TestServer
    from animal_kingdom.web import server
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")
    studies = tmp_path / "studies"; studies.mkdir()
    (studies / "open.json").write_text(json.dumps({"title": "Open", "positions": []}))
    (studies / "theirs.json").write_text(json.dumps({"title": "Theirs", "owner": "someone-else", "positions": []}))
    monkeypatch.setattr(server, "STUDY_DIR", studies); monkeypatch.setattr(server, "STUDY_DATA_DIR", tmp_path / "none")

    async def run():
        async with TestClient(TestServer(server.make_app())) as c:
            a = await (await c.post("/api/profile", json={})).json()
            names = [s["name"] for s in await (await c.get("/api/studies", headers={"X-AK-Key": a["code"]})).json()]
            assert names == ["open"]
            (studies / "mine.json").write_text(json.dumps({"title": "Mine", "owner": a["profile"]["id"], "positions": []}))
            names = [s["name"] for s in await (await c.get("/api/studies", headers={"X-AK-Key": a["code"]})).json()]
            assert names == ["mine", "open"]
    asyncio.run(run())


def test_a_gauntlet_can_name_its_field(monkeypatch, tmp_path):
    """#/gauntlet?decks=a,b (Martin, 2026-10-21: his deck against the three piles): the field is exactly those decks, the bots'
    own included; an unknown deck is refused."""
    import asyncio
    from aiohttp.test_utils import TestClient, TestServer
    from animal_kingdom.web import custom_decks, server
    monkeypatch.setenv("AK_NO_GAME_LOGS", "1")
    monkeypatch.setattr(custom_decks, "DECKS_FILE", tmp_path / "web_decks.json")

    async def run():
        async with TestClient(TestServer(server.make_app())) as c:
            a = await (await c.post("/api/profile", json={})).json()
            body = {"deck": "cats", "gauntlet": {"level": "expert", "per_seat": 1, "decks": ["bot_optimized", "optimizer_1", "optimizer_4"]}}
            m = await (await c.post("/api/match", json=body, headers={"X-AK-Key": a["code"]})).json()
            sched = server.hub.matches[m["id"]].schedule
            assert [g["deck"] for g in sched] == ["bot_optimized"] * 2 + ["optimizer_1"] * 2 + ["optimizer_4"] * 2
            body["gauntlet"]["decks"] = ["nope"]
            assert (await c.post("/api/match", json=body, headers={"X-AK-Key": a["code"]})).status == 400
    asyncio.run(run())
