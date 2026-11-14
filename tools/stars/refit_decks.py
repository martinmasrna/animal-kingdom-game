"""Refit the shipped and ladder decks to the stars prototype's rules (engine/stars.py, decks.py): two copies of any
non-legendary card, at most decks.STAR_BUDGET stars (16 when the decks were refitted, 2026-11-15).

Each deck keeps its cards; a third copy goes, and the freed slots (and a short deck's missing ones) take further
non-legendary animals that fit it: the most of its own families and tags, then its habitats, within the star budget.
Placeholders, not design (Martin corrects them). Prints each deck's cuts and fills as a Markdown table.

    .venv/bin/python tools/stars/refit_decks.py [--dry-run]
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from animal_kingdom.decks import DECK_SIZE, STAR_BUDGET, deck_stars  # noqa: E402
from animal_kingdom.engine.cards import COPY_LIMITS, load_cards  # noqa: E402

DATA = ROOT / "animal_kingdom" / "data"


def refit(lst: list[str], cards) -> tuple[list[str], list[str], list[str]]:
    """The deck under the rules, the cut copies and the added cards (one id per copy)."""
    counts = collections.Counter(lst)
    out, cut = [], []
    seen = collections.Counter()
    for cid in lst:
        c = cards.get(cid)
        limit = COPY_LIMITS[c.rarity] if c else 99
        if seen[cid] >= limit:
            cut.append(cid)
            continue
        seen[cid] += 1
        out.append(cid)
    tags = collections.Counter(t for cid in out if cid in cards for t in cards[cid].tags)
    habitats = collections.Counter(cards[cid].habitat for cid in out if cid in cards and cards[cid].habitat)
    added = []

    def score(c):
        return (sum(tags[t] for t in c.tags), habitats[c.habitat], -c.stars, c.base_strength if isinstance(c.base_strength, int) else 0)

    # a deck already over the budget (it was over the old caps too) gives up its starriest non-legendary copies first
    while deck_stars(out, cards) > STAR_BUDGET:
        worst = max((cid for cid in out if cid in cards and cards[cid].rarity != "legendary" and cards[cid].stars > 0),
                    key=lambda cid: cards[cid].stars, default=None)
        if worst is None:
            break
        out.remove(worst)
        cut.append(worst)
    pool = sorted((c for c in cards.values() if c.collectible and c.rarity != "legendary" and not c.name.startswith("[")),
                  key=score, reverse=True)
    while len(out) < DECK_SIZE:
        left = STAR_BUDGET - deck_stars(out, cards)
        have = collections.Counter(out)
        pick = next((c for c in pool if have[c.id] < COPY_LIMITS[c.rarity] and c.stars <= left), None)
        if pick is None:
            break
        out.append(pick.id)
        added.append(pick.id)
    return out, cut, added


def summary(cut, added, cards) -> tuple[str, str]:
    fmt = lambda ids: ", ".join(f"{cards[i].name}{' ×' + str(n) if n > 1 else ''}{' (' + '★' * cards[i].stars + ')' if cards[i].stars > 0 else ''}"
                                for i, n in collections.Counter(ids).items()) or "—"
    return fmt(cut), fmt(added)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    cards = load_cards()
    rows = []
    shipped = json.loads((DATA / "decklists.json").read_text(encoding="utf-8"))
    for d in shipped["decks"]:
        lst = [cid for cid, n in d["cards"].items() for _ in range(n)]
        new, cut, added = refit(lst, cards)
        d["cards"] = dict(collections.Counter(new))
        rows.append((d["name"], *summary(cut, added, cards), deck_stars(new, cards)))
    ladder = json.loads((DATA / "ladder_decks.json").read_text(encoding="utf-8"))
    for d in ladder["decks"]:
        new, cut, added = refit(d["list"], cards)
        d["list"] = new
        rows.append((d["name"] + " (ladder)", *summary(cut, added, cards), deck_stars(new, cards)))
    print("| Deck | Cut | Added | Stars |\n|---|---|---|---:|")
    for r in rows:
        print("| " + " | ".join(str(x) for x in r) + " |")
    if not args.dry_run:
        (DATA / "decklists.json").write_text(json.dumps(shipped, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        (DATA / "ladder_decks.json").write_text(json.dumps(ladder, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
