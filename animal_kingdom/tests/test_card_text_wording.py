"""Card-text conventions (docs/rules/keywords.md). The three-line limit is measured in the browser: web/test/cardtext.test.mjs."""

from __future__ import annotations

import re

from animal_kingdom.engine.cards import load_cards


def test_the_other_player_is_your_opponent():
    """Card text names the other player "your opponent", never they/their/them."""
    bad = {cid: c.text for cid, c in load_cards().items() if c.text and re.search(r"\b(they|their|them)\b", c.text, re.I)}
    assert not bad, bad
