"""The Meta tab's numbers (docs/meta-tab.md): every league game's card facts summed as it arrives, answered by rating and the last so many days, counted back from now in whole hours.

A game comes in with its facts (league/facts.py: both lists' mulligans, every card's draw and play turn, both ratings as it
began). It is counted under its hour (UTC), its rating band (the two ratings' mean, in steps of BAND), both lists and, for each
side, every card of its own list that was seen in the mulligan (m), kept in the starting hand (k), drawn at any point (d)
and played (p), each with that side's wins. A list is an exact 30 cards that never changes, so archetypes are only a
mapping over lists, applied when asked: Martin's (data/archetypes.json), a later list joining its parent's.

Only games on the current cards count (Martin, 2026-10-25): the server keeps each card's print (its rules, not its name or
habitat) and, starting with cards changed since the last start, forgets every game of a list holding a changed card, both
sides of it, so that list counts again from its new cards while lists untouched by the change keep theirs.
"""

from __future__ import annotations

import collections
import hashlib
import json
import time
from pathlib import Path
from typing import Callable, Iterable, Optional

BAND = 100
KEEP_DAYS = 45
EVENTS = ("m", "k", "d", "p")
HOUR = "%Y-%m-%dT%H"   # a game's key in time: its hour, so "the last day" is the last 24 hours
ARCHETYPES = Path(__file__).resolve().parents[1] / "data" / "archetypes.json"

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta_games (day TEXT, band INTEGER, a TEXT, b TEXT, n INTEGER, w INTEGER, PRIMARY KEY (day, band, a, b));
CREATE TABLE IF NOT EXISTS meta_cards (day TEXT, band INTEGER, a TEXT, b TEXT, card TEXT, ev TEXT, n INTEGER, w INTEGER,
    PRIMARY KEY (day, band, a, b, card, ev));
CREATE TABLE IF NOT EXISTS meta_prints (card TEXT PRIMARY KEY, h TEXT);
"""
NOT_RULES = {"name", "species", "habitat", "related", "unnamed"}   # what a card is called and where it lives, not how it plays


def card_prints(cards: Iterable[dict]) -> dict[str, str]:
    """Each card's print: a hash of everything on it that plays (the card data's entries)."""
    return {c["id"]: hashlib.sha1(json.dumps({k: v for k, v in c.items() if k not in NOT_RULES}, sort_keys=True).encode()).hexdigest()
            for c in cards}


def slug_of(lid: str) -> str:
    """A ladder id's list: 'bot:expert:cats' is 'cats'."""
    return lid.split(":", 2)[2] if lid.startswith("bot:") else lid


def side_events(facts: dict, lst: set[str]) -> dict[str, set[str]]:
    """Which cards of the side's own list each event touched, once a card per game (tokens and fetched cards are not the list's)."""
    cards = facts.get("cards", [])
    return {"m": set(facts.get("seen", [])) & lst,
            "k": {c for c, d, _ in cards if d == 0} & lst,
            "d": {c for c, _, _ in cards} & lst,
            "p": {c for c, _, p in cards if p is not None} & lst}


class Meta:
    def __init__(self, db, lists: Callable[[str], Optional[list[str]]]):
        """`lists(slug)` gives a list's 30 cards (None when unknown)."""
        self.db, self.lists = db, lists
        db.executescript(SCHEMA)
        self.games: dict[tuple, list[int]] = {}
        self.cards: dict[tuple, list[int]] = {}
        cutoff = time.strftime(HOUR, time.gmtime(time.time() - KEEP_DAYS * 86400))
        with db:
            for t in ("meta_games", "meta_cards"):   # rows counted by the day before hours: under that day's first hour
                db.execute(f"UPDATE {t} SET day = day || 'T00' WHERE length(day) = 10")
            db.execute("DELETE FROM meta_games WHERE day < ?", (cutoff,)); db.execute("DELETE FROM meta_cards WHERE day < ?", (cutoff,))
        for day, band, a, b, n, w in db.execute("SELECT day, band, a, b, n, w FROM meta_games"):
            self.games[(day, band, a, b)] = [n, w]
        for day, band, a, b, card, ev, n, w in db.execute("SELECT day, band, a, b, card, ev, n, w FROM meta_cards"):
            self.cards[(day, band, a, b, card, ev)] = [n, w]
        self._cache: dict[tuple, tuple[float, dict]] = {}

    # ------------------------------------------------------------------ current cards
    def track(self, prints: dict[str, str]) -> set[str]:
        """Forget the games of every list holding a card whose print changed since the last call; the lists forgotten."""
        old = dict(self.db.execute("SELECT card, h FROM meta_prints"))
        changed = {c for c in old.keys() | prints.keys() if old.get(c) != prints.get(c)} if old else set()
        stale = {s for key in self.games for s in key[2:4] if changed & set(self.lists(s) or ())}
        self.forget(stale)
        with self.db:
            self.db.execute("DELETE FROM meta_prints")
            self.db.executemany("INSERT INTO meta_prints VALUES (?, ?)", prints.items())
        return stale

    def forget(self, slugs: Iterable[str]) -> None:
        """Every game a list played, both sides of it, gone."""
        slugs = set(slugs)
        if not slugs:
            return
        self.games = {k: v for k, v in self.games.items() if k[2] not in slugs and k[3] not in slugs}
        self.cards = {k: v for k, v in self.cards.items() if k[2] not in slugs and k[3] not in slugs}
        marks = ",".join("?" * len(slugs))
        with self.db:
            for t in ("meta_games", "meta_cards"):
                self.db.execute(f"DELETE FROM {t} WHERE a IN ({marks}) OR b IN ({marks})", (*slugs, *slugs))
        self._cache.clear()

    # ------------------------------------------------------------------ counting
    def add(self, games: Iterable[dict]) -> int:
        """Count finished games: {t, a, b, winner, ra, rb, A: facts, B: facts}; a game without facts or a winner is skipped."""
        g_up: dict[tuple, list[int]] = collections.defaultdict(lambda: [0, 0])
        c_up: dict[tuple, list[int]] = collections.defaultdict(lambda: [0, 0])
        n = 0
        for g in games:
            if g.get("winner") not in ("A", "B") or "A" not in g or "B" not in g:
                continue
            a, b = slug_of(g["a"]), slug_of(g["b"])
            la, lb = self.lists(a), self.lists(b)
            if not la or not lb:
                continue
            day = time.strftime(HOUR, time.gmtime(g.get("t") or time.time()))
            band = int((float(g.get("ra") or 1500) + float(g.get("rb") or 1500)) / 2 // BAND * BAND)
            for me, opp, seat, lst in ((a, b, "A", la), (b, a, "B", lb)):
                won = int(g["winner"] == seat)
                k = g_up[(day, band, me, opp)]; k[0] += 1; k[1] += won
                for ev, cs in side_events(g[seat], set(lst)).items():
                    for c in cs:
                        k = c_up[(day, band, me, opp, c, ev)]; k[0] += 1; k[1] += won
            n += 1
        with self.db:
            for key, (dn, dw) in g_up.items():
                cur = self.games.setdefault(key, [0, 0]); cur[0] += dn; cur[1] += dw
                self.db.execute("INSERT INTO meta_games VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT DO UPDATE SET n = n + excluded.n, w = w + excluded.w", (*key, dn, dw))
            for key, (dn, dw) in c_up.items():
                cur = self.cards.setdefault(key, [0, 0]); cur[0] += dn; cur[1] += dw
                self.db.execute("INSERT INTO meta_cards VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO UPDATE SET n = n + excluded.n, w = w + excluded.w", (*key, dn, dw))
        if n:
            self._cache.clear()
        return n

    # ------------------------------------------------------------------ asking
    def overview(self, arch: dict[str, str], names: dict[str, str], lo: int, hi: int, days: int) -> dict:
        """The meta in a rating range over the last `days` days: each archetype's share of games and win rate, the matchup
        matrix, and every card's impacts pooled over every list that runs it (mirrors left out, as in the win rates)."""
        key = ("o", lo, hi, days, tuple(sorted(arch.items())))
        hit = self._cache.get(key)
        if hit and time.time() - hit[0] < 120:
            return hit[1]
        since = time.strftime(HOUR, time.gmtime(time.time() - days * 86400)) if days else ""
        tot: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0, 0])   # games, wins outside the mirror, games outside it
        mx: dict[str, dict[str, list[int]]] = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
        bands: set[int] = set()
        for (day, band, a, b), (n, w) in self.games.items():
            if not (days == 0 or day >= since):
                continue
            bands.add(band)
            if not lo <= band < hi or a not in arch or b not in arch:
                continue
            x, y = arch[a], arch[b]
            tot[x][0] += n                                   # share counts every deck met, mirrors too
            if x != y:                                       # a win rate leaves the mirror out, as tier lists do
                tot[x][1] += w; tot[x][2] += n
                mx[x][y][0] += n; mx[x][y][1] += w
        inside = lambda day, band, a, b: (days == 0 or day >= since) and lo <= band < hi and a in arch and b in arch and arch[a] != arch[b]
        lg: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])          # each list's games outside the mirror
        for (day, band, a, b), (n, w) in self.games.items():
            if inside(day, band, a, b):
                lg[a][0] += n; lg[a][1] += w
        lc: dict[tuple, dict[str, list[int]]] = collections.defaultdict(lambda: {e: [0, 0] for e in EVENTS})
        for (day, band, a, b, c, e), (n, w) in self.cards.items():
            if inside(day, band, a, b):
                lc[(a, c)][e][0] += n; lc[(a, c)][e][1] += w
        by_card: dict[str, list[dict]] = collections.defaultdict(list)
        for a, g in lg.items():
            for c in set(self.lists(a) or []):
                by_card[c].append(impacts(lc[(a, c)], g))
        games = sum(t[0] for t in tot.values())
        out = {"games": games // 2, "bands": sorted(bands), "band": BAND,
               "archetypes": sorted(({"id": x, "name": names.get(x, x), "games": t[0], "wins": t[1], "decided": t[2], "share": t[0] / games if games else 0}
                                     for x, t in tot.items()), key=lambda r: -r["games"]),
               "matrix": {x: {y: v for y, v in row.items()} for x, row in mx.items()},
               "cards": [{"card": c, **pooled(v)} for c, v in sorted(by_card.items())]}
        self._cache[key] = (time.time(), out)
        return out

    def archetype(self, x: str, arch: dict[str, str], lo: int, hi: int, days: int, vs: Optional[str] = None,
                  pick: Optional[str] = None) -> dict:
        """One archetype in a range: its lists with their games, and one list's card figures (`pick`, else its most played
        list), against `vs` with the opponent's cards. A card's figures are one exact list's: a player plays a list, and
        a card's numbers depend on the other 29 (Martin, 2026-10-26)."""
        since = time.strftime(HOUR, time.gmtime(time.time() - days * 86400)) if days else ""
        ok = lambda day, band: (days == 0 or day >= since) and lo <= band < hi
        mine = {s for s, g in arch.items() if g == x}
        opp_ok = (lambda b: arch.get(b) == vs) if vs else (lambda b: b in arch and b not in mine)   # the mirror left out, as in the overview
        per_list: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
        for (day, band, a, b), (n, w) in self.games.items():
            if a in mine and opp_ok(b) and ok(day, band):
                per_list[a][0] += n; per_list[a][1] += w
        if pick not in per_list:
            pick = max(per_list, key=lambda s: per_list[s][0], default=None)
        ev: dict[str, dict[str, list[int]]] = collections.defaultdict(lambda: {e: [0, 0] for e in EVENTS})
        opp: dict[str, dict[str, list[int]]] = collections.defaultdict(lambda: {e: [0, 0] for e in EVENTS})
        for (day, band, a, b, c, e), (n, w) in self.cards.items():
            if not ok(day, band):
                continue
            if a == pick and opp_ok(b):
                ev[c][e][0] += n; ev[c][e][1] += w
            elif vs and arch.get(a) == vs and b == pick:     # the opponent's cards in this matchup, counted from their side
                opp[c][e][0] += n; opp[c][e][1] += w
        lists = {s: self.lists(s) or [] for s in per_list}
        return {"id": x, "games": sum(v[0] for v in per_list.values()), "wins": sum(v[1] for v in per_list.values()),
                "lists": sorted(({"slug": s, "list": lists[s], "games": v[0], "wins": v[1]} for s, v in per_list.items()), key=lambda r: -r["games"]),
                "list": pick, "cards": [{"card": c, **impacts(ev[c], per_list[pick])} for c in sorted(set(lists.get(pick) or []))],
                "opp": [{"card": c, **v} for c, v in opp.items()] if vs else None}


def _rate(v: list[int]) -> Optional[float]:
    return v[1] / v[0] if v[0] else None


def impacts(ev: dict[str, list[int]], games: list[int]) -> dict[str, dict]:
    """A card's impact in one list (Martin, 2026-10-26: against its own list, never against 50%, so a strong deck's
    cards don't look strong for the deck's sake): dealt (`o`), the list's win rate when the opening hand offered it
    against when it didn't, which only the shuffle decides; kept (`k`), when it was kept against when it was offered and
    sent back. Not "drawn at all": a card goes undrawn mostly in short games, which are mostly losses, so drawn against
    not drawn credits every card with the game's length (+20 for the Fish list's Remora where dealt says +5). Each with
    both sides' [games, wins] and the difference in win rate (`i`), None while a side has no games."""
    def one(yes: list[int], no: list[int]) -> dict:
        a, b = _rate(yes), _rate(no)
        return {"yes": yes, "no": no, "i": a - b if a is not None and b is not None else None}
    k, m = ev["k"], ev["m"]
    no = lambda all_, yes: [max(0, all_[0] - yes[0]), max(0, all_[1] - yes[1])]   # a starting hand is all seen; never below none
    return {"o": one(m, no(games, m)), "k": one(k, no(m, k))}


def pooled(per_list: list[dict[str, dict]]) -> dict[str, dict]:
    """A card's impacts over every list that runs it: the sides' games summed, the differences averaged, each list
    weighted by how much its difference can be trusted (yes * no / (yes + no), the inverse of its variance's scale)."""
    out = {}
    for e in ("o", "k"):
        yes = [sum(x[e]["yes"][j] for x in per_list) for j in (0, 1)]
        no = [sum(x[e]["no"][j] for x in per_list) for j in (0, 1)]
        h = [(x[e]["yes"][0] * x[e]["no"][0] / (x[e]["yes"][0] + x[e]["no"][0]), x[e]["i"]) for x in per_list if x[e]["i"] is not None]
        tot = sum(w for w, _ in h)
        out[e] = {"yes": yes, "no": no, "i": sum(w * i for w, i in h) / tot if tot else None}
    return out


def archetype_map(pool_rows: dict[str, dict], known: Iterable[str]) -> tuple[dict[str, str], dict[str, str]]:
    """Each list's archetype and each archetype's name: Martin's file first; a list born from a parent takes its parent's
    (through the chain); anything else is left out until Martin places it."""
    data = json.loads(ARCHETYPES.read_text()) if ARCHETYPES.is_file() else {"archetypes": []}
    arch, names = {}, {}
    for a in data["archetypes"]:
        aid = a.get("id") or a["name"].lower().replace(" ", "_")
        names[aid] = a["name"]
        for s in a["lists"]:
            arch[s] = aid
    for s in known:
        seen, p = set(), s
        while p not in arch and p in pool_rows and pool_rows[p].get("parent") and p not in seen:
            seen.add(p); p = pool_rows[p]["parent"]
        if p in arch and s not in arch:
            arch[s] = arch[p]
    return arch, names
