"""Card-text conventions (docs/rules/keywords.md). The three-line limit is measured in the browser: web/test/cardtext.test.mjs."""

from __future__ import annotations

import re

from animal_kingdom.engine.cards import load_cards


# Cards whose they/their names animals, not the other player ("adjacent enemies lose their keywords"), and texts the
# workbench holds that break the rule until Martin rewords them there (the converter copies text verbatim).
PRONOUNS_FOR_ANIMALS = {"octopus", "handlock_legend_eagle_mate"}
WORKBENCH_WORDING_TO_FIX = {"hoofed_legend_giraffe"}   # "Your opponent plays with their hand revealed."


def test_the_other_player_is_your_opponent():
    """Card text names the other player "your opponent", never they/their/them."""
    bad = {cid: c.text for cid, c in load_cards().items() if c.text and re.search(r"\b(they|their|them)\b", c.text, re.I)}
    assert set(bad) == PRONOUNS_FOR_ANIMALS | WORKBENCH_WORDING_TO_FIX, bad
