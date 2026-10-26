"""The Meta tab's numbers (web/meta.py): games and card facts summed by hour, rating band and list, answered by archetype."""

import sqlite3
import time

from animal_kingdom.decks import load_premade_deck
from animal_kingdom.web.meta import Meta, archetype_map


def _meta():
    return Meta(sqlite3.connect(":memory:"), lambda s: load_premade_deck(s) if s in ("cats", "fish", "canines") else None)


def _game(winner, ra=1500, rb=1500, t=None):
    cats, fish = load_premade_deck("cats"), load_premade_deck("fish")
    a = {"seen": cats[:4] + ["not_in_list"], "back": [cats[0]], "cards": [[cats[1], 0, 1], [cats[4], 0, None], [cats[8], 2, 3]]}
    b = {"seen": fish[:4], "back": [], "cards": [[fish[0], 0, 2], [fish[9], 3, None]]}
    return {"t": t or time.time(), "a": "bot:expert:cats", "b": "bot:normal:fish", "winner": winner, "ra": ra, "rb": rb, "A": a, "B": b}


def test_games_count_by_archetype_with_shares_win_rates_and_the_matrix():
    m = _meta()
    assert m.add([_game("A"), _game("A"), _game("B"), _game(None), {"a": "bot:expert:cats", "b": "bot:expert:fish", "winner": "A"}]) == 3
    o = m.overview({"cats": "Cats", "fish": "Fish"}, {"Cats": "Cats", "Fish": "Fish"}, 0, 10000, 0)
    rows = {r["id"]: r for r in o["archetypes"]}
    assert o["games"] == 3 and rows["Cats"]["wins"] == 2 and rows["Fish"]["wins"] == 1 and rows["Cats"]["share"] == 0.5
    assert o["matrix"]["Cats"]["Fish"] == [3, 2] and o["matrix"]["Fish"]["Cats"] == [3, 1]
    cats, fish = load_premade_deck("cats"), load_premade_deck("fish")
    cards = {c["card"]: c for c in o["cards"]}                                   # every card's impacts over every list running it
    assert cards[cats[0]]["o"] == {"yes": [3, 2], "no": [0, 0], "i": None}      # dealt in every game: nothing to compare with
    assert cards[cats[0]]["k"]["no"] == [3, 2] and cards[cats[0]]["k"]["i"] is None   # offered and sent back every time
    assert cards[fish[0]]["o"]["yes"] == [3, 1]


def test_the_rating_range_and_the_days_filter_the_games():
    m = _meta()
    m.add([_game("A", 1500, 1500), _game("B", 1900, 2000), _game("A", 1500, 1500, t=time.time() - 10 * 86400)])
    arch, names = {"cats": "C", "fish": "F"}, {"C": "C", "F": "F"}
    assert m.overview(arch, names, 1900, 2100, 0)["games"] == 1                 # the mean of 1900 and 2000 sits in the 1900 band
    assert m.overview(arch, names, 0, 10000, 3)["games"] == 2                   # the game ten days old is outside the last three days
    assert m.overview(arch, names, 0, 10000, 0)["bands"] == [1500, 1900]


def test_the_last_day_is_the_last_24_hours_not_the_calendar_day():
    m = _meta()
    m.add([_game("A", t=time.time() - 23 * 3600), _game("A", t=time.time() - 26 * 3600)])
    assert m.overview({"cats": "C", "fish": "F"}, {"C": "C", "F": "F"}, 0, 10000, 1)["games"] == 1


def test_rows_counted_by_the_day_before_hours_still_load():
    db = sqlite3.connect(":memory:")
    Meta(db, lambda s: None)
    day = time.strftime("%Y-%m-%d", time.gmtime())
    db.execute("INSERT INTO meta_games VALUES (?, 1500, 'cats', 'fish', 2, 1)", (day,))
    assert Meta(db, lambda s: None).overview({"cats": "C", "fish": "F"}, {"C": "C", "F": "F"}, 0, 10000, 0)["games"] == 1


def test_card_figures_count_each_event_once_a_game_and_only_the_lists_own_cards():
    m = _meta()
    m.add([_game("A"), _game("B")])
    cats = load_premade_deck("cats")
    r = m.archetype("C", {"cats": "C", "fish": "F"}, 0, 10000, 0, vs="F")
    by = {c["card"]: c for c in r["cards"]}
    assert r["games"] == 2 and r["lists"][0]["slug"] == "cats"
    assert by[cats[0]]["k"] == {"yes": [0, 0], "no": [2, 1], "i": None}        # seen in the mulligan, sent back: never kept
    assert by[cats[1]]["k"]["yes"] == [2, 1]                                     # kept
    assert by[cats[8]]["o"]["yes"] == [0, 0] and by[cats[8]]["k"]["yes"] == [0, 0]   # drawn on turn 2: never offered, never kept
    assert "not_in_list" not in by and r["list"] == "cats"
    fish = load_premade_deck("fish")
    opp = {c["card"]: c for c in r["opp"]}
    assert opp[fish[0]]["p"] == [2, 1]                                          # the opponent's played card, with the opponent's wins


def test_impact_is_against_the_lists_own_games():
    from animal_kingdom.web.meta import impacts, pooled
    i = impacts({"m": [10, 5], "k": [6, 4], "d": [8, 6], "p": [0, 0]}, [20, 10])
    assert i["k"] == {"yes": [6, 4], "no": [4, 1], "i": 4 / 6 - 1 / 4}           # kept 4 of 6, sent back and won 1 of 4
    assert i["o"]["no"] == [10, 5] and i["o"]["i"] == 0                          # dealt in 10 games, won 5; not dealt, 5 of 10
    big = {"k": {"yes": [90, 0], "no": [90, 0], "i": .1}, "o": {"yes": [0, 0], "no": [0, 0], "i": None}}
    small = {"k": {"yes": [10, 0], "no": [10, 0], "i": -.1}, "o": {"yes": [0, 0], "no": [0, 0], "i": None}}
    assert abs(pooled([big, small])["k"]["i"] - .08) < 1e-9 and pooled([big, small])["o"]["i"] is None   # the bigger list weighs more


def test_card_figures_are_one_lists_the_most_played_unless_another_is_picked():
    m = _meta()
    m.add([_game("A"), _game("A"), {**_game("B"), "a": "bot:expert:canines"}])
    arch = {"cats": "C", "canines": "C", "fish": "F"}
    r = m.archetype("C", arch, 0, 10000, 0)
    assert r["games"] == 3 and r["list"] == "cats" and [l["slug"] for l in r["lists"]] == ["cats", "canines"]
    assert {c["card"] for c in r["cards"]} == set(load_premade_deck("cats"))
    r = m.archetype("C", arch, 0, 10000, 0, pick="canines")
    assert r["list"] == "canines" and {c["card"] for c in r["cards"]} == set(load_premade_deck("canines"))


def test_counts_survive_a_restart_and_a_child_list_joins_its_parents_archetype(tmp_path):
    db = sqlite3.connect(tmp_path / "m.db")
    lists = lambda s: load_premade_deck(s) if s in ("cats", "fish") else None
    Meta(db, lists).add([_game("A")])
    again = Meta(db, lists)
    assert again.overview({"cats": "C", "fish": "F"}, {"C": "C", "F": "F"}, 0, 10000, 0)["games"] == 1
    arch, names = archetype_map({"tinker_x": {"parent": "tinker_y"}, "tinker_y": {"parent": "cats"}}, ["tinker_x", "cats"])
    assert arch["tinker_x"] == arch["cats"] and names[arch["cats"]] == "Cats"


def test_a_changed_card_forgets_the_games_of_every_list_holding_it_and_only_those(tmp_path):
    db = sqlite3.connect(str(tmp_path / "m.db"))
    lists = lambda s: load_premade_deck(s) if s in ("cats", "fish", "canines") else None
    m = Meta(db, lists)
    canines = {**_game("A"), "b": "bot:expert:canines", "B": {"seen": [], "back": [], "cards": []}}
    fish_canines = {**_game("A"), "a": "bot:expert:fish", "b": "bot:expert:canines", "A": {"seen": [], "back": [], "cards": []},
                    "B": {"seen": [], "back": [], "cards": []}}
    m.add([_game("A"), canines, fish_canines])
    prints = {c: "1" for s in ("cats", "fish", "canines") for c in load_premade_deck(s)}
    assert m.track(prints) == set()                                   # the first prints are the baseline
    only_cats = next(c for c in load_premade_deck("cats") if c not in load_premade_deck("fish") + load_premade_deck("canines"))
    assert m.track({**prints, only_cats: "2"}) == {"cats"}
    assert {k[2:4] for k in m.games} == {("fish", "canines"), ("canines", "fish")}   # cats' games gone, both sides
    m2 = Meta(db, lists)                                              # and gone from the database
    assert {k[2:4] for k in m2.games} == {("fish", "canines"), ("canines", "fish")} and m2.track({**prints, only_cats: "2"}) == set()
