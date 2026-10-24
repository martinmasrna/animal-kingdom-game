"""Tinkering (docs/league.md): a list changes one card the way a player does, when its own games say a card is losing.

From the runner's log (every bot game with the cards each side drew), each Expert pairing's last `WINDOW` games give, per
card in its list, the win rate of games where the card was drawn against games where it was not. A card whose gap sits
outside the noise ("I keep losing when I draw this": z below -Z) is the one to replace. The replacement is what wins in
lists around this rating: over the Expert pairings within `BAND` of it, the collectible card with the largest lift in win
rate when drawn, among cards the list can legally take one more of. The child, one copy swapped, is a new player: born
with its parent's rating as its start, under all three pilots, named after its parent with a numeral. At most `--births`
a day, so the pool changes at a ladder's pace.
"""

from __future__ import annotations

import collections
import hashlib
import json
import math
from pathlib import Path
from typing import Optional

from ..decks import decklist_problems
from ..engine.cards import COPY_LIMITS, load_cards

WINDOW = 200        # a pairing's games read
MIN_DRAWN = 25      # games with the card drawn before its gap means anything
Z = 2.5             # the gap outside the noise
BAND = 150          # the rating band whose lists suggest the replacement
MIN_LIFT_N = 30     # games with a candidate drawn before its lift counts
ROMAN = ["", " II", " III", " IV", " V", " VI", " VII", " VIII", " IX", " X", " XI", " XII"]


def read_log(path: Path, limit: int = 200_000) -> list[dict]:
    """The runner's games with draws, newest last (the file is append-only)."""
    if not path.is_file():
        return []
    lines = path.read_text().splitlines()[-limit:]
    out = []
    for line in lines:
        try:
            g = json.loads(line)
        except ValueError:
            continue
        if "drawn_a" in g and g.get("winner") in ("A", "B"):
            out.append(g)
    return out


def games_of(games: list[dict], lid: str) -> list[tuple[bool, set[str]]]:
    """(won, drawn) for every game `lid` played, newest last."""
    out = []
    for g in games:
        if g["a"] == lid:
            out.append((g["winner"] == "A", set(g["drawn_a"])))
        elif g["b"] == lid:
            out.append((g["winner"] == "B", set(g["drawn_b"])))
    return out


def _z(w1: int, n1: int, w0: int, n0: int) -> float:
    """Two-proportion z of (win rate drawn) - (win rate not drawn)."""
    if n1 == 0 or n0 == 0:
        return 0.0
    p1, p0, p = w1 / n1, w0 / n0, (w1 + w0) / (n1 + n0)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n0)) or 1e-9
    return (p1 - p0) / se


def losing_card(lst: list[str], played: list[tuple[bool, set[str]]]) -> Optional[tuple[str, float, int]]:
    """The card of `lst` whose drawn games are lost most clearly: (card, z, games drawn), or None."""
    recent = played[-WINDOW:]
    if len(recent) < WINDOW // 2:
        return None
    worst = None
    for cid in sorted(set(lst)):
        drawn = [w for w, d in recent if cid in d]
        not_drawn = [w for w, d in recent if cid not in d]
        if len(drawn) < MIN_DRAWN or not not_drawn:
            continue
        z = _z(sum(drawn), len(drawn), sum(not_drawn), len(not_drawn))
        if z <= -Z and (worst is None or z < worst[1]):
            worst = (cid, z, len(drawn))
    return worst


def lift_table(games: list[dict], players: dict[str, float], centre: float) -> dict[str, tuple[float, int]]:
    """Per card: (win-rate lift when drawn, games drawn) over the Expert pairings within BAND of `centre`."""
    band = {lid for lid, r in players.items() if lid.startswith("bot:expert:") and abs(r - centre) <= BAND}
    won: collections.Counter = collections.Counter(); n: collections.Counter = collections.Counter()
    base_w = base_n = 0
    for g in games:
        for seat, lid in (("A", g["a"]), ("B", g["b"])):
            if lid not in band:
                continue
            w = g["winner"] == seat
            base_w += w; base_n += 1
            for cid in g["drawn_a" if seat == "A" else "drawn_b"]:
                won[cid] += w; n[cid] += 1
    base = base_w / base_n if base_n else 0.5
    return {cid: (won[cid] / n[cid] - base, n[cid]) for cid in n if n[cid] >= MIN_LIFT_N}


def replacement(lst: list[str], bad: str, lifts: dict[str, tuple[float, int]], cards: dict) -> Optional[str]:
    """The card with the largest lift that the list may legally take one more of, instead of `bad`."""
    counts = collections.Counter(lst)
    trial = list(lst); trial.remove(bad)
    for cid, (lift, _) in sorted(lifts.items(), key=lambda kv: -kv[1][0]):
        card = cards.get(cid)
        if card is None or not card.collectible or cid == bad or counts[cid] >= COPY_LIMITS[card.rarity]:
            continue
        if lift <= 0:
            return None
        if not decklist_problems(trial + [cid], cards=cards):
            return cid
    return None


def child_name(parent_name: str, taken: set[str]) -> str:
    base = parent_name
    for suffix in ROMAN[1:]:
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    for i in range(1, 40):
        name = base + (ROMAN[i] if i < len(ROMAN) else f" {i + 1}")
        if name not in taken:
            return name
    return base + " +"


def propose(games: list[dict], pool: dict, births_today: int, births: int, log=print) -> list[dict]:
    """The children to post this pass: [{slug, name, list, source, parent, start}], at most `births - births_today`."""
    if births_today >= births:
        return []
    cards = load_cards()
    decks = {d["slug"]: d for d in pool["decks"]}
    names = {d["name"] for d in pool["decks"]}
    lists = {tuple(sorted(d["list"])) for d in pool["decks"]}
    players = {p["id"]: p["rating"] for p in pool["players"]}
    candidates = []
    for lid, rating in players.items():
        if not lid.startswith("bot:expert:"):
            continue
        slug = lid.split(":", 2)[2]
        if slug not in decks:
            continue
        found = losing_card(decks[slug]["list"], games_of(games, lid))
        if found:
            candidates.append((found[1], lid, slug, found))
    out = []
    for z, lid, slug, (bad, _, n_drawn) in sorted(candidates)[: births - births_today]:
        lifts = lift_table(games, players, players[lid])
        new = replacement(decks[slug]["list"], bad, lifts, cards)
        if not new:
            log(f"{slug}: {bad} loses when drawn (z {z:.1f}, {n_drawn} games) but nothing in the band lifts; left alone")
            continue
        child = sorted(decks[slug]["list"]); child.remove(bad); child.append(new); child.sort()
        if tuple(child) in lists:
            continue
        name = child_name(decks[slug]["name"], names); names.add(name)
        out.append({"slug": "tinker_" + hashlib.sha1(",".join(child).encode()).hexdigest()[:10], "name": name, "list": child,
                    "source": "tinker", "parent": slug, "start": players[lid],
                    "why": f"{cards[bad].name} loses when drawn (z {z:.1f}, {n_drawn} games); {cards[new].name} lifts the band by {lifts[new][0]:+.2f}"})
        log(f"{slug} -> {name}: {out[-1]['why']}")
    return out
