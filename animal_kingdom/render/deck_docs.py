"""Regenerate the card tables in docs/cards/decks/<deck>.md from cards.json.

Each deck doc is hand-written prose (identity, plan, design notes) plus one generated block
between CARDS_BEGIN and CARDS_END. cards.json is the only source of card numbers and text; this
keeps the docs from drifting away from it. `test_deck_docs.py` fails when a block is stale.

    .venv/bin/python -m animal_kingdom.render.deck_docs
"""

from __future__ import annotations

from pathlib import Path

from ..engine.cards import COPY_LIMITS, DECK_SLUGS, Card, load_cards

DOCS_DIR = Path(__file__).resolve().parents[2] / "docs" / "cards" / "decks"
CARDS_BEGIN = "<!-- cards:begin (generated from cards.json by animal_kingdom.render.deck_docs) -->"
CARDS_END = "<!-- cards:end -->"


def doc_path(deck: str) -> Path:
    return DOCS_DIR / f"{deck.replace('_', '-')}.md"


def cards_block(deck: str, cards: dict[str, Card]) -> str:
    lines = [CARDS_BEGIN]
    for rarity in ("legendary", "rare", "common"):
        rows = [c for c in cards.values() if c.deck == deck and c.rarity == rarity]
        lines += ["", f"### {rarity.title()}", "",
                  "| Card | × | Tags | Str | Text |", "|---|---:|---|---:|---|"]
        for c in rows:
            copies = c.copies if c.copies is not None else COPY_LIMITS[rarity]
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


def main() -> None:
    cards = load_cards()
    for deck in sorted(DECK_SLUGS):
        path = doc_path(deck)
        path.write_text(render(path.read_text(), cards_block(deck, cards)))
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
