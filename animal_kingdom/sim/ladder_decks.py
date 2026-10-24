"""The ladder's deck pool beyond the shipped decks: the decks people built and played, as bot decks.

Martin, 2026-10-24: the bots should play many more decks than the fifteen hand-picked ones, every pilot-and-deck pairing
being a player of its own on the ladder. This builds `data/ladder_decks.json` from the decks people played under their own
names (`deploy/deploy.sh pull`: results/web_decks.json) and the decks saved on profiles (`deploy/deploy.sh players`:
results/players.json): each list in today's card ids, legal under the deck rules, distinct from every shipped deck and from
each other, named by what it is made of (its commonest habitat and tag, "Jungle Cats"; a repeated name gets a numeral),
with the builder's own name kept beside it as `given` for Martin to prefer. A deck played keeps the slug it was played
under, so its games in the logs and its ladder rows stay its own.

    .venv/bin/python -m animal_kingdom.sim.ladder_decks [--web results/web_decks.json] [--players results/players.json]
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path

from ..decks import _expand, decklist_problems
from ..engine.cards import DECKLISTS, load_cards
from ..web.renamed import renamed

OUT = Path(__file__).resolve().parents[1] / "data" / "ladder_decks.json"
ROMAN = ["", " II", " III", " IV", " V", " VI", " VII", " VIII", " IX", " X"]


def content_name(lst: list[str], cards: dict) -> str:
    """A deck named by its commonest habitat and, when a tag covers a third of it, its commonest tag."""
    habitats = collections.Counter(cards[c].habitat for c in lst if cards[c].habitat)
    tags = collections.Counter(t for c in lst for t in cards[c].tags)
    habitat = habitats.most_common(1)[0][0] if habitats else "Mixed"
    tag, n = tags.most_common(1)[0] if tags else ("", 0)
    return f"{habitat} {tag}s" if n * 3 >= len(lst) and not tag.endswith("s") else (f"{habitat} {tag}" if n * 3 >= len(lst) else f"{habitat} Mix")


def build(web: dict, saved: list[dict]) -> tuple[list[dict], collections.Counter]:
    cards = load_cards()
    shipped = {tuple(sorted(_expand(d))) for d in DECKLISTS}   # the shipped decks only: a rebuild keeps every ladder deck
    seen: set[tuple[str, ...]] = set(shipped)
    out, skipped = [], collections.Counter()
    sources = [(slug, d["name"], list(d["list"]), "played") for slug, d in web.items()]
    for d in saved:
        held = json.loads(d["cards"]) if isinstance(d["cards"], str) else d["cards"]
        lst = held if isinstance(held, list) else [cid for cid, n in held.items() for _ in range(int(n))]
        sources.append((None, d["name"], lst, "saved"))
    for slug, name, lst, source in sources:
        lst = renamed(lst)
        key = tuple(sorted(lst))
        if key in seen:
            skipped["duplicate or shipped"] += 1
            continue
        if decklist_problems(lst):
            skipped["illegal today"] += 1
            continue
        seen.add(key)
        slug = slug or "deck_" + hashlib.sha1(",".join(key).encode()).hexdigest()[:10]
        out.append({"slug": slug, "name": content_name(lst, cards), "given": " ".join(str(name or "").split())[:40],
                    "list": lst, "source": source})
    out.sort(key=lambda d: (d["name"].lower(), d["slug"]))
    counts: collections.Counter = collections.Counter()
    for d in out:
        n = counts[d["name"].lower()]; counts[d["name"].lower()] += 1
        d["name"] = d["name"] + (ROMAN[n] if n < len(ROMAN) else f" {n + 1}")
    return out, skipped


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--web", default="results/web_decks.json")
    ap.add_argument("--players", default="results/players.json")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    web = json.loads(Path(a.web).read_text()) if Path(a.web).is_file() else {}
    players = json.loads(Path(a.players).read_text()) if Path(a.players).is_file() else {}
    decks, skipped = build(web, players.get("decks", []))
    Path(a.out).write_text(json.dumps({
        "_comment": "The ladder's deck pool beyond decklists.json: the decks people built and played, as the bots play them "
                    "(sim/ladder_decks.py rebuilds this from deploy/deploy.sh pull and players). slug, name (the builder's), "
                    "list (30 card ids), source (played under that slug, or saved on a profile).",
        "decks": decks}, indent=1) + "\n")
    print(f"{len(decks)} ladder decks written to {a.out}; skipped {dict(skipped)}")


if __name__ == "__main__":
    main()
