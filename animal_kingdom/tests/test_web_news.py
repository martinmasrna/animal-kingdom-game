"""News (web/news.py): every release file reads cleanly, names real cards, keeps the group order; a player's dot and
"Since you last played" follow what they've opened and seen, and never show a release from before they came."""

import datetime
import sqlite3

import pytest

from animal_kingdom.engine.cards import load_cards
from animal_kingdom.web import news


def test_every_shipped_release_parses():
    rels = news.releases()
    assert rels and [r["id"] for r in rels] == sorted((r["id"] for r in rels), reverse=True)
    for r in rels:
        assert r["groups"] and all(g["items"] for g in r["groups"])


def _release(tmp_path, name, body):
    p = tmp_path / name
    p.write_text(body)
    return p


def test_a_release_names_only_real_cards_and_keeps_the_group_order(tmp_path):
    cards = load_cards()
    with pytest.raises(news.NewsError, match="no card named"):
        news.parse(_release(tmp_path, "2026-10-05.md", "# x\n\n## Rules\n\n- A change.\n  Cards: Tigger\n"), cards)
    with pytest.raises(news.NewsError, match="the groups go"):
        news.parse(_release(tmp_path, "2026-10-06.md", "# x\n\n## New\n\n- One.\n\n## Rules\n\n- Two.\n"), cards)


def _rels():
    return [{"id": "2026-10-03", "groups": [{"name": "New", "items": [{"text": "A screen.", "cards": []}]},
                                           {"name": "Cards", "items": [{"text": "Lemming is 2.", "cards": ["lemming"]}]}]},
            {"id": "2026-10-01", "groups": [{"name": "Rules", "items": [{"text": "A rule.", "cards": []}]}]}]


def test_since_you_last_played_shows_rules_and_your_cards_once():
    db = sqlite3.connect(":memory:")
    joined = datetime.datetime(2026, 10, 1, 12).timestamp()
    p = {"id": "p1", "created": joined}
    decks = [{"name": "Rodents", "cards": {"lemming": 3}}]
    s = news.state(db, p, decks, _rels())
    assert s["unread"] and [x["text"] for x in s["since"]] == ["Lemming is 2.", "A rule."]
    assert s["since"][0]["decks"] == ["Rodents"]
    news.mark(db, "p1", shown="2026-10-03", opened="2026-10-03")
    s = news.state(db, p, decks, _rels())
    assert not s["unread"] and s["since"] == []


def test_a_new_player_sees_nothing_from_before_they_came_nor_cards_they_dont_hold():
    db = sqlite3.connect(":memory:")
    p = {"id": "p2", "created": datetime.datetime(2026, 10, 2, 9).timestamp()}
    s = news.state(db, p, [{"name": "Cats", "cards": {"tiger": 3}}], _rels())
    assert s["since"] == [] and s["unread"]
