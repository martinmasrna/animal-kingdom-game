"""Smoke tests for the terminal renderer (render/text.py).

The renderer emits Rich-markup strings; these guard that it (a) runs on both maps and a
populated board without raising, and (b) produces *well-formed* markup — a stray or
unbalanced tag would only surface when a Console tries to print it, so we render through a
real Console into a buffer and let Rich validate the markup.
"""

from __future__ import annotations

import random
from io import StringIO

import pytest
from rich.console import Console

from animal_kingdom.bots.random_bot import RandomBot
from animal_kingdom.decks import load_premade_deck
from animal_kingdom.engine import rules
from animal_kingdom.engine.state import new_game
from animal_kingdom.render.text import render


def _advance(state, plies: int, seed: int) -> None:
    """Play up to `plies` random legal actions so the board has units/stacks/regions."""
    bots = {"A": RandomBot(seed=seed + 1), "B": RandomBot(seed=seed + 2)}
    for _ in range(plies):
        if rules.is_terminal(state) is not None:
            break
        actor = state.player_to_act()
        action = bots[actor].choose(state.view_for(actor), rules.legal_actions(state), state)
        rules.apply_action(state, action)


def _assert_valid_markup(markup: str) -> str:
    """Render `markup` through a Rich Console; a malformed tag raises here. Returns plain text."""
    console = Console(file=StringIO(), width=120, highlight=False, force_terminal=False)
    console.print(markup)
    return console.file.getvalue()


@pytest.mark.parametrize("map_id", ["map_a", "map_b"])
def test_render_runs_and_emits_valid_markup(map_id: str) -> None:
    state = new_game(load_premade_deck("cats_midrange"), load_premade_deck("aggro_hq_rush"),
                     seed=7, map_id=map_id)
    _advance(state, plies=30, seed=7)

    out = render(state, reveal_hands={"A"})
    assert out.strip()
    plain = _assert_valid_markup(out)
    # Board, scoreboard, and the revealed hand are all present.
    assert "HQ A" in plain and "HQ B" in plain
    assert "seat A" in plain and "seat B" in plain
    assert "HAND — seat A" in plain


def test_render_highlights_and_result() -> None:
    """Selection highlights and a terminal result banner both stay well-formed."""
    state = new_game(load_premade_deck("ramp"), load_premade_deck("egg_control"), seed=3)
    _advance(state, plies=4, seed=3)

    legal = rules.legal_actions(state)
    place_targets = {a.crossroad for a in legal if getattr(a, "crossroad", None)}
    out = render(state, reveal_hands={state.current},
                 highlight_crs=place_targets, highlight_hq="B")
    _assert_valid_markup(out)

    # Drive to game over and render the result line.
    drng = random.Random(3)
    while rules.is_terminal(state) is None:
        actor = state.player_to_act()
        legal = rules.legal_actions(state)
        rules.apply_action(state, drng.choice(legal))
    final = render(state)
    assert "RESULT:" in _assert_valid_markup(final)
