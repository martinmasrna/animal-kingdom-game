"""The Meta tab's numbers (web/meta.py): games and card facts summed by day, rating band and list, answered by archetype."""

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


def test_the_rating_range_and_the_days_filter_the_games():
    m = _meta()
    m.add([_game("A", 1500, 1500), _game("B", 1900, 2000), _game("A", 1500, 1500, t=time.time() - 10 * 86400)])
    arch, names = {"cats": "C", "fish": "F"}, {"C": "C", "F": "F"}
    assert m.overview(arch, names, 1900, 2100, 0)["games"] == 1                 # the mean of 1900 and 2000 sits in the 1900 band
    assert m.overview(arch, names, 0, 10000, 3)["games"] == 2                   # the game ten days old is outside the last three days
    assert m.overview(arch, names, 0, 10000, 0)["bands"] == [1500, 1900]


def test_card_figures_count_each_event_once_a_game_and_only_the_lists_own_cards():
    m = _meta()
    m.add([_game("A"), _game("B")])
    cats = load_premade_deck("cats")
    r = m.archetype("C", {"cats": "C", "fish": "F"}, 0, 10000, 0, vs="F")
    by = {c["card"]: c for c in r["cards"]}
    assert r["games"] == 2 and r["lists"][0]["slug"] == "cats"
    assert by[cats[0]]["m"] == [2, 1] and by[cats[0]]["k"] == [0, 0]           # seen in the mulligan, sent back: never kept
    assert by[cats[1]]["k"] == [2, 1] and by[cats[1]]["p"] == [2, 1]           # kept and played
    assert by[cats[8]]["d"] == [2, 1] and by[cats[8]]["k"] == [0, 0]           # drawn on turn 2: not in the starting hand
    assert "not_in_list" not in by and by[cats[0]]["with"] == [2, 1] and by[cats[0]]["play"] == 1
    fish = load_premade_deck("fish")
    opp = {c["card"]: c for c in r["opp"]}
    assert opp[fish[0]]["p"] == [2, 1]                                          # the opponent's played card, with the opponent's wins


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
