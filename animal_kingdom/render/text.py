"""ASCII renderer for sanity-checking the engine in the terminal.

Pure: takes a GameState, returns a string (no printing). Shows the 4x3 board with the
top unit per crossroad (owner + strength, `+` if a stack), plus food / hand / deck
counts, the turn, the seat to act, and the result if the game is over.
"""

from __future__ import annotations

_COLS = (1, 2, 3, 4)
_ROWS = (3, 2, 1)  # render top row first
_W = 8             # cell width


def _cell(state, cr: str) -> str:
    stack = state.board.get(cr)
    if not stack:
        return "·"
    top = stack[-1]
    s = state.cards[top.card_id].base_strength
    s = s if isinstance(s, int) else "?"
    suffix = "+" if len(stack) > 1 else ""
    return f"{top.owner}{s}{suffix}"


def render(state) -> str:
    lines = []

    head = f"{state.game_map.name}   turn {state.turn_counter}   to act: {state.player_to_act()}"
    if state.result is not None:
        head += f"   RESULT: {state.result.winner or 'draw'} ({state.result.reason})"
    lines.append(head)
    lines.append(
        f"food  A:{state.food['A']:<4} B:{state.food['B']:<4}   "
        f"hand  A:{len(state.hands['A'])} B:{len(state.hands['B'])}   "
        f"deck  A:{len(state.decks['A'])} B:{len(state.decks['B'])}"
    )
    lines.append("")

    for r in _ROWS:
        coords = "".join(f"({c},{r})".center(_W) for c in _COLS)
        cells = "".join(_cell(state, f"{c},{r}").center(_W) for c in _COLS)
        # HQ labels sit on the unit line of the middle row only.
        cell_left, cell_right = ("HQ_A  ", "  HQ_B") if r == 2 else ("      ", "")
        lines.append("      " + coords)
        lines.append(cell_left + cells + cell_right)
    return "\n".join(lines)
