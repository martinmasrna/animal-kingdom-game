"""The meta report (Martin, 2026-10-24): what is happening on the bot ladder, built on the Mac each morning and served by the game.

The Mac is the one place that has everything: the live ratings (the pool), a daily snapshot of them (`snapshots/`), every
bot game with the cards each side drew (the runner's log) and every birth with its reason. From those: the movers over a
day and a week; the births and what changed; card impact, the win rate when drawn against not drawn across the Expert
pairings; the meta by band, what a person at a given rating meets; the top pairings. The server adds the people when it
serves it (`/api/league/report`), and the Ladder screen shows it on its Meta tab.
"""

from __future__ import annotations

import collections
import json
import time
from pathlib import Path

from ..engine.cards import load_cards
from ..sim.ladder_decks import content_name
from ..web.ladder import MATCH_WINDOW, PROVISIONAL, parse_bot
from .tinker import games_of, read_log

MIN_CARD_GAMES = 40
BANDS = (1300, 1500, 1700, 1900, 2100)


def snapshot(pool: dict, folder: Path, day: str) -> Path:
    """Today's ratings on disk, once a day (the runner calls this every pass; the file is written once)."""
    folder.mkdir(parents=True, exist_ok=True)
    p = folder / f"{day}.json"
    if not p.is_file():
        p.write_text(json.dumps({"day": day, "players": {x["id"]: [x["rating"], x["rd"], x["games"]] for x in pool["players"]}}))
    return p


def _snapshot_before(folder: Path, days: int, now: float) -> dict:
    """The newest snapshot at least `days` old, as {id: [rating, rd, games]}; empty when there is none."""
    cutoff = time.strftime("%Y-%m-%d", time.localtime(now - days * 86400))
    files = sorted(p for p in folder.glob("*.json") if p.stem <= cutoff) if folder.is_dir() else []
    return json.loads(files[-1].read_text())["players"] if files else {}


def archetype(lst: list[str], cards: dict) -> str:
    return content_name(lst, cards).split(" ", 1)[1] if " " in content_name(lst, cards) else content_name(lst, cards)


def build(pool: dict, folder: Path, births: list[dict], games: list[dict], now: float | None = None) -> dict:
    now = now or time.time()
    cards = load_cards()
    decks = {d["slug"]: d for d in pool["decks"]}
    players = {p["id"]: p for p in pool["players"]}
    name = lambda lid: f"{decks.get(parse_bot(lid)[1], {}).get('name', parse_bot(lid)[1])} ({parse_bot(lid)[0]})"
    day, week = _snapshot_before(folder, 1, now), _snapshot_before(folder, 7, now)

    def movers(before: dict) -> list[dict]:
        rows = []
        for lid, p in players.items():
            if lid in before and p["games"] >= PROVISIONAL:
                rows.append({"id": lid, "name": name(lid), "rating": round(p["rating"]), "delta": round(p["rating"] - before[lid][0]),
                             "games": p["games"] - before[lid][2]})
        return sorted(rows, key=lambda r: -abs(r["delta"]))

    # card impact within each Expert pairing: a card's lift is the win rate of that pairing's games where it was drawn
    # against the pairing's own win rate, so a card in a strong deck is not credited with the deck's strength; pooled over
    # pairings by games. The '[LEGEND]' placeholders of unnamed legends read as their species.
    by_pair: dict[str, list[tuple[bool, set[str]]]] = collections.defaultdict(list)
    for g in games:
        for seat, lid, drawn in (("A", g["a"], g["drawn_a"]), ("B", g["b"], g["drawn_b"])):
            if lid.startswith("bot:expert:"):
                by_pair[lid].append((g["winner"] == seat, set(drawn)))
    lift_sum: collections.Counter = collections.Counter(); n: collections.Counter = collections.Counter(); won: collections.Counter = collections.Counter()
    for lid, rows in by_pair.items():
        base = sum(w for w, _ in rows) / len(rows)
        for w, drawn in rows:
            for cid in drawn:
                lift_sum[cid] += (1.0 if w else 0.0) - base; n[cid] += 1; won[cid] += w
    card_name = lambda cid: (cards[cid].name.strip("[]").replace("_", " ").title() if cards[cid].name.startswith("[") else cards[cid].name) if cid in cards else cid   # an unnamed legend's placeholder reads as its animal
    impact = [{"card": cid, "name": card_name(cid), "drawn_win": round(100 * won[cid] / n[cid]),
               "lift": round(100 * lift_sum[cid] / n[cid]), "games": n[cid]} for cid in n if n[cid] >= MIN_CARD_GAMES]
    impact.sort(key=lambda r: -r["lift"])

    # the meta by band: what a person at that rating meets (the Expert pilot preferred within the window, else all pilots)
    meta = {}
    for centre in BANDS:
        near = [lid for lid, p in players.items() if abs(p["rating"] - centre) <= MATCH_WINDOW and p["games"] >= PROVISIONAL and parse_bot(lid)[1] in decks]
        experts = [lid for lid in near if lid.startswith("bot:expert:")] or near
        share = collections.Counter(archetype(decks[parse_bot(lid)[1]]["list"], cards) for lid in experts)
        meta[str(centre)] = [{"archetype": a, "share": round(100 * c / len(experts)), "pairings": c} for a, c in share.most_common(6)] if experts else []

    births_out = []
    for b in births[-30:]:
        child = players.get(f"bot:expert:{b['slug']}"); parent = players.get(f"bot:expert:{b.get('parent')}")
        births_out.append({"when": time.strftime("%Y-%m-%d %H:%M", time.localtime(b["t"])), "name": b["name"], "parent": decks.get(b.get("parent"), {}).get("name", b.get("parent")),
                           "why": b.get("why", ""), "added": b.get("added", True),
                           "child_rating": round(child["rating"]) if child else None, "child_games": child["games"] if child else 0,
                           "parent_rating": round(parent["rating"]) if parent else None})
    top = sorted((p for p in players.values() if parse_bot(p["id"])[1] in decks and p["games"] >= PROVISIONAL), key=lambda p: -p["rating"])[:12]
    day_games = sum(1 for g in games if g.get("t", 0) >= now - 86400)
    cover = lambda slug: (decks.get(slug, {}).get("list") or [""])[0]
    return {"generated": time.strftime("%Y-%m-%d %H:%M", time.localtime(now)), "games_logged": len(games), "games_day": day_games,
            "pairings": sum(1 for p in players.values() if parse_bot(p["id"])[1] in decks), "births_day": sum(1 for b in births if b["t"] >= now - 86400),
            "movers_day": movers(day)[:12], "movers_week": movers(week)[:12],
            "births": births_out[::-1], "cards_up": impact[:10], "cards_down": impact[-10:][::-1], "meta": meta,
            "top": [{"name": name(p["id"]), "deck": parse_bot(p["id"])[1], "cover": cover(parse_bot(p["id"])[1]), "rating": round(p["rating"]), "games": p["games"]} for p in top]}


def to_markdown(r: dict) -> str:
    out = [f"# Bot ladder, {r['generated']}", "", f"{r['games_logged']} bot games with draws in the log.", "", "## Movers, last day"]
    out += [f"- {m['name']}: {m['rating']} ({m['delta']:+d} in {m['games']} games)" for m in r["movers_day"]] or ["- no snapshot a day old yet"]
    out += ["", "## Movers, last week"] + ([f"- {m['name']}: {m['rating']} ({m['delta']:+d} in {m['games']} games)" for m in r["movers_week"]] or ["- no snapshot a week old yet"])
    out += ["", "## Births"] + ([f"- {b['when']} {b['name']} from {b['parent']}: {b['why']}; now {b['child_rating']} after {b['child_games']} games (parent {b['parent_rating']})" for b in r["births"]] or ["- none yet"])
    out += ["", "## Cards that win when drawn"] + [f"- {c['name']}: {c['drawn_win']}% when drawn, {c['lift']:+d} on the field, {c['games']} games" for c in r["cards_up"]]
    out += ["", "## Cards that lose when drawn"] + [f"- {c['name']}: {c['drawn_win']}% when drawn, {c['lift']:+d} on the field, {c['games']} games" for c in r["cards_down"]]
    out += ["", "## What a person meets"] + [f"- at {band}: " + (", ".join(f"{m['archetype']} {m['share']}%" for m in ms) or "nobody within the window") for band, ms in r["meta"].items()]
    out += ["", "## Top pairings"] + [f"- {t['name']}: {t['rating']} ({t['games']} games)" for t in r["top"]]
    return "\n".join(out) + "\n"
