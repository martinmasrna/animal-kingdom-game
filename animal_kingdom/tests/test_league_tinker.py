"""Tinkering (league/tinker.py): a card that loses when drawn is found, a replacement that wins in the band is chosen, the
child is a legal distinct list born at its parent's rating."""

import random

from animal_kingdom.decks import decklist_problems, load_premade_deck
from animal_kingdom.engine.cards import load_cards
from animal_kingdom.league import tinker


def _games(lid, opp, lst, bad, n, rng, p_win_drawn=0.25, p_win_not=0.6, lifted=None):
    out = []
    for i in range(n):
        drawn = set(rng.sample(sorted(set(lst)), 8))
        if lifted and rng.random() < 0.5:
            drawn.add(lifted)
        won = rng.random() < ((0.9 if lifted in drawn else (p_win_drawn if bad in drawn else p_win_not)))
        a, b = (lid, opp) if i % 2 else (opp, lid)
        winner = ("A" if a == lid else "B") if won else ("B" if a == lid else "A")
        out.append({"a": a, "b": b, "winner": winner, "drawn_a": sorted(drawn) if a == lid else ["lion"], "drawn_b": sorted(drawn) if b == lid else ["lion"]})
    return out


def test_the_losing_card_is_found_and_a_lifting_card_replaces_it():
    rng = random.Random(5)
    lst = load_premade_deck("cats")
    bad = lst[0]
    cards = load_cards()
    lifted = next(cid for cid, c in cards.items() if c.collectible and cid not in lst and c.rarity == "common")
    lid, opp = "bot:expert:cats", "bot:expert:fish"
    games = _games(lid, opp, lst, bad, 240, rng, lifted=lifted)
    found = tinker.losing_card(lst, tinker.games_of(games, lid))
    assert found and found[0] == bad and found[1] < -tinker.Z
    pool = {"decks": [{"slug": "cats", "name": "Cats", "list": lst}, {"slug": "fish", "name": "Fish", "list": load_premade_deck("fish")}],
            "players": [{"id": lid, "rating": 2000}, {"id": opp, "rating": 1990}]}
    children = tinker.propose(games, pool, 0, 3, log=lambda m: None)
    assert len(children) == 1
    c = children[0]
    assert c["parent"] == "cats" and c["start"] == 2000 and c["name"] == "Cats II" and c["source"] == "tinker"
    assert sorted(c["list"]) != sorted(lst) and c["list"].count(bad) == lst.count(bad) - 1 and lifted in c["list"]
    assert not decklist_problems(c["list"])
    assert tinker.propose(games, pool, 3, 3) == [], "the day's births are spent"


def test_too_few_games_or_no_clear_loser_means_no_child():
    rng = random.Random(6)
    lst = load_premade_deck("cats")
    lid, opp = "bot:expert:cats", "bot:expert:fish"
    few = _games(lid, opp, lst, lst[0], 40, rng)
    assert tinker.losing_card(lst, tinker.games_of(few, lid)) is None
    even = _games(lid, opp, lst, lst[0], 240, rng, p_win_drawn=0.5, p_win_not=0.5)
    assert tinker.losing_card(lst, tinker.games_of(even, lid)) is None


def test_child_names_follow_the_lineage():
    assert tinker.child_name("Savanna Cats", {"Savanna Cats"}) == "Savanna Cats II"
    assert tinker.child_name("Savanna Cats II", {"Savanna Cats", "Savanna Cats II"}) == "Savanna Cats III"
    assert tinker.child_name("Savanna Cats III", {"Savanna Cats", "Savanna Cats II", "Savanna Cats III", "Savanna Cats IV"}) == "Savanna Cats V"
