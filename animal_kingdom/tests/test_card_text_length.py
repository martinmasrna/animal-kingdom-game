"""Card text is at most 80 characters: three lines on the full card (docs/design/principles.md)."""

from __future__ import annotations

from animal_kingdom.engine.cards import load_cards

LIMIT = 80

# Over the limit while their redesign is open with Martin; remove an entry once its card fits.
PENDING = {
    "magpie": "steals and shuffles, two actions in one Battlecry",
    "hornet": "conditional sacrifice plus removal",
}


def test_card_text_fits_three_lines():
    over = {cid: len(c.text) for cid, c in load_cards().items() if c.text and len(c.text) > LIMIT and cid not in PENDING}
    assert not over, f"card text over {LIMIT} characters: {over}"


def test_pending_cards_are_still_over():
    cards = load_cards()
    fixed = [cid for cid in PENDING if len(cards[cid].text or "") <= LIMIT]
    assert not fixed, f"now within the limit, drop from PENDING: {fixed}"
