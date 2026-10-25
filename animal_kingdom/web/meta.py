"""The Meta tab's numbers (docs/meta-tab.md): every league game's card facts summed as it arrives, answered by rating and days.

A game comes in with its facts (league/facts.py: both lists' mulligans, every card's draw and play turn, both ratings as it
began). It is counted under its day, its rating band (the two ratings' mean, in steps of BAND), both lists and, for each
side, every card of its own list that was seen in the mulligan (m), kept in the starting hand (k), drawn at any point (d)
and played (p), each with that side's wins. A list is an exact 30 cards that never changes, so archetypes are only a
mapping over lists, applied when asked: Martin's (data/archetypes.json), a later list joining its parent's.
"""

from __future__ import annotations

import collections
import json
import time
from pathlib import Path
from typing import Callable, Iterable, Optional

BAND = 100
KEEP_DAYS = 45
EVENTS = ("m", "k", "d", "p")
ARCHETYPES = Path(__file__).resolve().parents[1] / "data" / "archetypes.json"

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta_games (day TEXT, band INTEGER, a TEXT, b TEXT, n INTEGER, w INTEGER, PRIMARY KEY (day, band, a, b));
CREATE TABLE IF NOT EXISTS meta_cards (day TEXT, band INTEGER, a TEXT, b TEXT, card TEXT, ev TEXT, n INTEGER, w INTEGER,
    PRIMARY KEY (day, band, a, b, card, ev));
"""


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
        cutoff = time.strftime("%Y-%m-%d", time.gmtime(time.time() - KEEP_DAYS * 86400))
        with db:
            db.execute("DELETE FROM meta_games WHERE day < ?", (cutoff,)); db.execute("DELETE FROM meta_cards WHERE day < ?", (cutoff,))
        for day, band, a, b, n, w in db.execute("SELECT day, band, a, b, n, w FROM meta_games"):
            self.games[(day, band, a, b)] = [n, w]
        for day, band, a, b, card, ev, n, w in db.execute("SELECT day, band, a, b, card, ev, n, w FROM meta_cards"):
            self.cards[(day, band, a, b, card, ev)] = [n, w]
        self._cache: dict[tuple, tuple[float, dict]] = {}

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
            day = time.strftime("%Y-%m-%d", time.gmtime(g.get("t") or time.time()))
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
    def _keep(self, day: str, band: int, lo: int, hi: int, since: str) -> bool:
        return day >= since and lo <= band < hi

    def overview(self, arch: dict[str, str], names: dict[str, str], lo: int, hi: int, days: int) -> dict:
        """The meta in a rating range over the last `days` days: each archetype's share of games and win rate, the matchup matrix."""
        key = ("o", lo, hi, days, tuple(sorted(arch.items())))
        hit = self._cache.get(key)
        if hit and time.time() - hit[0] < 120:
            return hit[1]
        since = time.strftime("%Y-%m-%d", time.gmtime(time.time() - (days - 1) * 86400)) if days else ""
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
        games = sum(t[0] for t in tot.values())
        out = {"games": games // 2, "bands": sorted(bands), "band": BAND,
               "archetypes": sorted(({"id": x, "name": names.get(x, x), "games": t[0], "wins": t[1], "decided": t[2], "share": t[0] / games if games else 0}
                                     for x, t in tot.items()), key=lambda r: -r["games"]),
               "matrix": {x: {y: v for y, v in row.items()} for x, row in mx.items()}}
        self._cache[key] = (time.time(), out)
        return out

    def archetype(self, x: str, arch: dict[str, str], lo: int, hi: int, days: int, vs: Optional[str] = None) -> dict:
        """One archetype in a range: its lists with their games, every card's figures, and against `vs` the opponent's cards."""
        since = time.strftime("%Y-%m-%d", time.gmtime(time.time() - (days - 1) * 86400)) if days else ""
        ok = lambda day, band: (days == 0 or day >= since) and lo <= band < hi
        mine = {s for s, g in arch.items() if g == x}
        opp_ok = (lambda b: arch.get(b) == vs) if vs else (lambda b: b in arch and b not in mine)   # the mirror left out, as in the overview
        per_list: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
        for (day, band, a, b), (n, w) in self.games.items():
            if a in mine and opp_ok(b) and ok(day, band):
                per_list[a][0] += n; per_list[a][1] += w
        ev: dict[str, dict[str, list[int]]] = collections.defaultdict(lambda: {e: [0, 0] for e in EVENTS})
        opp: dict[str, dict[str, list[int]]] = collections.defaultdict(lambda: {e: [0, 0] for e in EVENTS})
        for (day, band, a, b, c, e), (n, w) in self.cards.items():
            if not ok(day, band):
                continue
            if a in mine and opp_ok(b):
                ev[c][e][0] += n; ev[c][e][1] += w
            elif vs and arch.get(a) == vs and b in mine:     # the opponent's cards in this matchup, counted from their side
                opp[c][e][0] += n; opp[c][e][1] += w
        lists = {s: self.lists(s) or [] for s in per_list}
        total = sum(v[0] for v in per_list.values())
        cards = []
        for c in sorted({c for l in lists.values() for c in l}):
            inn = [s for s, l in lists.items() if c in l]
            with_ = [sum(per_list[s][0] for s in inn), sum(per_list[s][1] for s in inn)]
            without = [total - with_[0], sum(v[1] for v in per_list.values()) - with_[1]]
            copies = sum(lists[s].count(c) * per_list[s][0] for s in inn) / with_[0] if with_[0] else 0
            cards.append({"card": c, "play": with_[0] / total if total else 0, "copies": round(copies, 2),
                          "with": with_, "without": without, **ev[c]})
        return {"id": x, "games": total, "wins": sum(v[1] for v in per_list.values()),
                "lists": sorted(({"slug": s, "list": lists[s], "games": v[0], "wins": v[1]} for s, v in per_list.items()), key=lambda r: -r["games"]),
                "cards": cards,
                "opp": [{"card": c, **v} for c, v in opp.items()] if vs else None}


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
