"""The deck docs' card tables must match cards.json (regenerate with render.deck_docs)."""

from __future__ import annotations

import pytest

from animal_kingdom.engine.cards import DECK_SLUGS, load_cards
from animal_kingdom.render.deck_docs import cards_block, doc_path, render, render_family, society_pages


@pytest.mark.parametrize("deck", sorted(DECK_SLUGS))
def test_deck_doc_card_table_matches_cards_json(deck):
    doc = doc_path(deck).read_text(encoding="utf-8")
    assert render(doc, cards_block(deck, load_cards())) == doc, (
        f"{doc_path(deck).name} is stale: run `.venv/bin/python -m animal_kingdom.render.deck_docs`")


@pytest.mark.parametrize("page", society_pages(), ids=lambda p: p.stem)
def test_society_page_card_table_matches_cards_json(page):
    doc = page.read_text(encoding="utf-8")
    assert render_family(doc) == doc, (
        f"{page.name} is stale: run `.venv/bin/python -m animal_kingdom.render.deck_docs`")
