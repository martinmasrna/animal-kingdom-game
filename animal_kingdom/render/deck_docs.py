"""Regenerate the card tables in docs/cards/decks/<deck>.md and docs/design/societies/*.md from cards.json.

Each deck doc is hand-written prose (identity, plan, design notes) plus one generated block
between CARDS_BEGIN and CARDS_END. A society page (a family's behaviours, playstyle and namer,
concept only) ends with one generated block of every card carrying the family's tag, planned
and reserve designs included, opened by a FAMILY_BEGIN marker naming the tag. cards.json is the
only source of card numbers and text; this keeps the docs from drifting away from it.
`test_deck_docs.py` fails when a block is stale.

    .venv/bin/python -m animal_kingdom.render.deck_docs
"""

from __future__ import annotations

import re
from pathlib import Path

from ..engine.cards import DECKLISTS, DECK_SLUGS, Card, load_bundled_json, load_cards

DOCS_DIR = Path(__file__).resolve().parents[2] / "docs" / "cards" / "decks"
SOCIETIES_DIR = Path(__file__).resolve().parents[2] / "docs" / "design" / "societies"
CARDS_BEGIN = "<!-- cards:begin (generated from cards.json by animal_kingdom.render.deck_docs) -->"
CARDS_END = "<!-- cards:end -->"
FAMILY_BEGIN = re.compile(r"<!-- cards:begin family=(\w+) \(generated from cards\.json by animal_kingdom\.render\.deck_docs\) -->")


def doc_path(deck: str) -> Path:
    return DOCS_DIR / f"{deck.replace('_', '-')}.md"


def cards_block(deck: str, cards: dict[str, Card]) -> str:
    counts = next(d["cards"] for d in DECKLISTS if d["slug"] == deck)
    lines = [CARDS_BEGIN]
    for rarity in ("legendary", "rare", "common"):
        rows = [cards[cid] for cid in counts if cards[cid].rarity == rarity]
        lines += ["", f"### {rarity.title()}", "",
                  "| Card | × | Tags | Str | Text |", "|---|---:|---|---:|---|"]
        for c in rows:
            copies = counts[c.id]
            tags = ", ".join(sorted(c.tags)) or "—"
            text = c.text.replace("|", "\\|") or "—"
            lines.append(f"| **{c.name}** | {copies} | {tags} | {c.base_strength} | {text} |")
    lines += ["", CARDS_END]
    return "\n".join(lines)


def render(doc: str, block: str) -> str:
    """`doc` with its generated block replaced by `block`."""
    head, sep, rest = doc.partition(CARDS_BEGIN)
    _, sep2, tail = rest.partition(CARDS_END)
    if not (sep and sep2):
        raise ValueError("deck doc is missing its generated-cards markers")
    return head + block + tail


_RARITY_ORDER = {"legendary": 0, "rare": 1, "common": 2, "": 3}
_STATUS_ORDER = {"collectible": 0, "reserve": 1, "planned": 2, "token": 3, "tutorial": 4}


def family_block(tag: str, raw: dict | None = None) -> str:
    """Every design in cards.json carrying `tag` (tokens and the tutorial's cards left out), as one
    table: the card, its rarity, strength and full text, and its habitat. A reserve or planned design
    says so after its name."""
    records = (raw or load_bundled_json("cards.json"))["cards"]
    rows = [r for r in records if tag in (r.get("tags") or []) and r.get("status") not in ("token", "tutorial")]
    rows.sort(key=lambda r: (_RARITY_ORDER.get(r.get("rarity", ""), 9),
                             _STATUS_ORDER.get(r.get("status", ""), 9), r.get("name", "")))
    lines = [f"<!-- cards:begin family={tag} (generated from cards.json by animal_kingdom.render.deck_docs) -->", "",
             "| Card | Rarity | Str | Text | Habitat |", "|---|---|---:|---|---|"]
    for r in rows:
        strength = "" if r.get("base_strength") is None else r["base_strength"]
        text = (r.get("text") or "").replace("|", "\\|")
        name = r.get("name", "") + ("" if r.get("status") == "collectible" else f" ({r.get('status', '')})")
        lines.append(f"| **{name}** | {r.get('rarity', '')} | {strength} | {text} | {r.get('habitat', '')} |")
    lines += ["", CARDS_END]
    return "\n".join(lines)


def family_of(doc: str) -> str | None:
    """The tag a society page's generated block is for, or None when the page has no block."""
    m = FAMILY_BEGIN.search(doc)
    return m.group(1) if m else None


def render_family(doc: str, block: str) -> str:
    """`doc` with its family block replaced by `block`."""
    m = FAMILY_BEGIN.search(doc)
    if not m:
        raise ValueError("society page is missing its generated-cards marker")
    _, sep, tail = doc[m.end():].partition(CARDS_END)
    if not sep:
        raise ValueError("society page is missing its generated-cards end marker")
    return doc[:m.start()] + block + tail


def society_pages() -> list[Path]:
    if not SOCIETIES_DIR.is_dir():
        return []
    return sorted(p for p in SOCIETIES_DIR.glob("*.md") if family_of(p.read_text(encoding="utf-8")))


def main() -> None:
    cards = load_cards()
    for deck in sorted(DECK_SLUGS):
        path = doc_path(deck)
        path.write_text(render(path.read_text(encoding="utf-8"), cards_block(deck, cards)), encoding="utf-8")
        print(f"wrote {path}")
    raw = load_bundled_json("cards.json")
    for path in society_pages():
        doc = path.read_text(encoding="utf-8")
        path.write_text(render_family(doc, family_block(family_of(doc), raw)), encoding="utf-8")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
