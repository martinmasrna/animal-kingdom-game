"""The meta report (league/report.py): movers from snapshots, births with their reasons, card impact, the meta by band."""

import json
import time

from animal_kingdom.decks import load_premade_deck
from animal_kingdom.league import report


def test_the_report_reads_snapshots_births_and_draws(tmp_path):
    lst = load_premade_deck("cats"); fish = load_premade_deck("fish")
    pool = {"decks": [{"slug": "cats", "name": "Cats", "list": lst}, {"slug": "fish", "name": "Fish", "list": fish}],
            "players": [{"id": "bot:expert:cats", "rating": 2100, "rd": 50, "games": 60}, {"id": "bot:expert:fish", "rating": 2000, "rd": 50, "games": 60},
                        {"id": "bot:normal:cats", "rating": 1500, "rd": 50, "games": 20}]}
    now = time.time()
    folder = tmp_path / "snapshots"
    yesterday = time.strftime("%Y-%m-%d", time.localtime(now - 86400))
    folder.mkdir(); (folder / f"{yesterday}.json").write_text(json.dumps({"day": yesterday, "players": {"bot:expert:cats": [2050, 60, 40], "bot:expert:fish": [2030, 60, 40]}}))
    report.snapshot(pool, folder, time.strftime("%Y-%m-%d", time.localtime(now)))
    games = []
    for i in range(100):
        drawn = sorted(set(lst[:8])) + (["lion"] if i % 2 else [])
        games.append({"a": "bot:expert:cats", "b": "bot:expert:fish", "winner": "A" if i % 2 else "B", "drawn_a": drawn, "drawn_b": sorted(set(fish[:8]))})
    births = [{"t": now - 3600, "slug": "tinker_x", "name": "Cats II", "parent": "cats", "why": "Lynx loses when drawn; Lion lifts", "added": True}]
    r = report.build(pool, folder, births, games, now)
    assert r["movers_day"][0]["name"] == "Cats (expert)" and r["movers_day"][0]["delta"] == 50 and r["movers_day"][0]["games"] == 20
    assert r["movers_week"] == []                       # no snapshot a week old
    assert r["births"][0]["name"] == "Cats II" and r["births"][0]["parent"] == "Cats" and r["births"][0]["parent_rating"] == 2100
    lion = next(c for c in r["cards_up"] if c["card"] == "lion")
    assert lion["drawn_win"] == 100 and lion["lift"] > 0 and lion["games"] == 50
    assert r["meta"]["2100"][0]["pairings"] == 1 and r["meta"]["1500"][0]["pairings"] == 1   # Expert Cats at 2100; Normal Cats at 1500
    assert r["top"][0]["name"] == "Cats (expert)"
    md = report.to_markdown(r)
    assert "## Movers, last day" in md and "Cats II from Cats" in md and "Lion" in md
