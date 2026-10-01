"""Every choice names the card asking it (effects.REQUIRE_SOURCE): random bots play every deck against every other, which
reaches the choices a curated test would forget, and a choice without its card fails loudly instead of being guessed."""

import itertools
import random

import pytest

from animal_kingdom.decks import PREMADE_DECKS, load_premade_deck
from animal_kingdom.engine import effects, rules
from animal_kingdom.engine.state import new_game
from animal_kingdom.sim.runner import make_bot

DECKS = sorted(d for d in PREMADE_DECKS if d != "goodstuff")


@pytest.mark.parametrize("a,b", list(itertools.product(DECKS, DECKS)))
def test_every_choice_names_its_card(monkeypatch, a, b):
    monkeypatch.setattr(effects, "REQUIRE_SOURCE", True)
    for seed in range(3):
        s = new_game(load_premade_deck(a), load_premade_deck(b), 7000 + seed)
        bots = {p: make_bot("random", seed * 2 + i) for i, p in enumerate("AB")}
        for _ in range(400):
            if rules.is_terminal(s) is not None:
                break
            if s.pending is not None and s.pending.get("kind") != "mulligan":
                step = s.effect_stack[-1]
                assert step.get("by_card") in s.cards, f"{step['op']} asks with no card"
            p = s.pending["chooser"] if s.pending else s.current
            rules.apply_action(s, bots[p].choose(s.clone().view_for(p), rules.legal_actions(s), s.clone()))
