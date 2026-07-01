"""ASCII renderer for sanity-checking the engine in the terminal.

Pure: takes a GameState, returns a string (no printing). Draws the board as a graph of
crossroad nodes wired by the map's actual edges, with each region's food value + current
holder printed in the block it sits on, and stack depth shown per node (full stack
composition listed below the board). Also renders food / hand / deck counts, the turn,
the seat to act, and the result. Optionally renders the full hand (card boxes) for seats
passed in `reveal_hands` - callers must only pass a seat whose hand isn't hidden (a human
player's own seat), never an opponent's.
"""

from __future__ import annotations

import shutil
import textwrap
from typing import Collection

from ..engine import strength as strength_mod

_MIN_WIDTH = 72    # floor so wrapping stays sane when a terminal reports something tiny

# Board node/gap geometry (characters). A node is a bordered box; gaps hold the edges
# between adjacent crossroads and, at each 2x2 block centre, the region food label.
_NODE_W = 9        # node box width incl. borders
_NODE_H = 4        # node box height incl. borders (border, coord, occupancy, border)
_GAP_W = 7         # horizontal gap between node columns
_GAP_H = 3         # vertical gap between node rows
_HQ_W = 8          # HQ box width incl. borders
_HQ_GAP = _GAP_H   # HQ<->front-column gap; == _GAP_H so the fan-out diagonals sit at 45 deg


def _terminal_width() -> int:
    return max(_MIN_WIDTH, shutil.get_terminal_size(fallback=(100, 24)).columns)


def _parse_cr(cr: str) -> tuple[int, int]:
    x, y = cr.split(",")
    return int(x), int(y)


def _occupancy(state, cr: str) -> str:
    """Top unit as `owner+strength`, `·` if empty, with `▾N` when N units are stacked."""
    stack = state.board.get(cr)
    if not stack:
        return "·"
    top = stack[-1]
    label = f"{top.owner}{strength_mod.effective_strength(state, top)}"
    return label + (f"▾{len(stack)}" if len(stack) > 1 else "")


def _region_holder(state, region) -> str | None:
    """The player controlling every corner of `region`, or None if contested/empty."""
    owners = {state.owner_of(c) for c in region.corners}
    return owners.pop() if len(owners) == 1 and None not in owners else None


def _blit(canvas: list[list[str]], row: int, col: int, text: str) -> None:
    for i, ch in enumerate(text):
        canvas[row][col + i] = ch


def _draw_conn(canvas: list[list[str]], r0: int, c0: int, r1: int, c1: int) -> None:
    """Wire (r0,c0)->(r1,c1) with box/diagonal glyphs, skipping the endpoints (box borders).

    Horizontal runs use ─, vertical │, and diagonals / or \\ by direction; the endpoints are
    left untouched so callers can put their own tees/corners on the boxes they connect.
    """
    dr, dc = r1 - r0, c1 - c0
    steps = max(abs(dr), abs(dc))
    for i in range(1, steps):
        r, c = round(r0 + dr * i / steps), round(c0 + dc * i / steps)
        if dr == 0:
            ch = "─"
        elif dc == 0:
            ch = "│"
        else:
            ch = "/" if (dr < 0) == (dc > 0) else "\\"
        if canvas[r][c] == " ":
            canvas[r][c] = ch


def _render_board(state) -> list[str]:
    gm = state.game_map
    coords = [_parse_cr(c) for c in gm.crossroads]
    xs = sorted({x for x, _ in coords})
    ys_top_first = sorted({y for _, y in coords}, reverse=True)  # highest y drawn at the top
    ci = {x: i for i, x in enumerate(xs)}          # grid x -> screen column index
    ri = {y: i for i, y in enumerate(ys_top_first)}  # grid y -> screen row index (0 = top)
    mid_y = ys_top_first[len(ys_top_first) // 2]      # vertically-central row (HQ height)

    # Which players' HQs sit on the left (min column) / right (max column) edge.
    hq_side = {}  # player -> "L"/"R"
    for player, fronts in gm.hq_connects.items():
        fx = {_parse_cr(c)[0] for c in fronts}
        if fx == {min(xs)}:
            hq_side[player] = "L"
        elif fx == {max(xs)}:
            hq_side[player] = "R"
    left = _HQ_W + _HQ_GAP if "L" in hq_side.values() else 0
    right = _HQ_W + _HQ_GAP if "R" in hq_side.values() else 0

    height = len(ys_top_first) * _NODE_H + (len(ys_top_first) - 1) * _GAP_H
    grid_w = len(xs) * _NODE_W + (len(xs) - 1) * _GAP_W
    width = left + grid_w + right
    canvas = [[" "] * width for _ in range(height)]

    def box_col(x: int) -> int:
        return left + ci[x] * (_NODE_W + _GAP_W)

    def box_row(y: int) -> int:
        return ri[y] * (_NODE_H + _GAP_H)

    # Nodes: a bordered box with the coordinate and the current occupancy.
    for x, y in coords:
        r0, c0 = box_row(y), box_col(x)
        inner = _NODE_W - 2
        _blit(canvas, r0, c0, "┌" + "─" * inner + "┐")
        _blit(canvas, r0 + 1, c0, "│" + f"{x},{y}".center(inner) + "│")
        _blit(canvas, r0 + 2, c0, "│" + _occupancy(state, f"{x},{y}").center(inner) + "│")
        _blit(canvas, r0 + 3, c0, "└" + "─" * inner + "┘")

    # Edges from the map's real adjacency: orthogonal ones use tees + a straight run;
    # diagonal neighbours are wired corner-to-corner with / or \. Each undirected edge is
    # drawn once (skipped from the higher-coordinate endpoint).
    for x, y in coords:
        for b in gm.neighbors(f"{x},{y}"):
            bx, by = _parse_cr(b)
            if (bx, by) < (x, y):
                continue  # this edge is drawn from its lower-coordinate endpoint
            if by == y:                        # horizontal
                row = box_row(y) + 2
                lo, hi = sorted((x, bx))
                lc, rc = box_col(lo) + _NODE_W - 1, box_col(hi)
                canvas[row][lc], canvas[row][rc] = "├", "┤"
                for c in range(lc + 1, rc):
                    canvas[row][c] = "─"
            elif bx == x:                      # vertical
                col = box_col(x) + _NODE_W // 2
                hi_y, lo_y = (y, by) if ri[y] < ri[by] else (by, y)  # hi_y is higher on screen
                top, bottom = box_row(hi_y) + _NODE_H - 1, box_row(lo_y)
                canvas[top][col], canvas[bottom][col] = "┴", "┬"
                for rr in range(top + 1, bottom):
                    canvas[rr][col] = "│"
            else:                              # diagonal: wire the two facing box corners
                up, rightward = ri[by] < ri[y], ci[bx] > ci[x]
                ar = box_row(y) + (0 if up else _NODE_H - 1)
                ac = box_col(x) + (_NODE_W - 1 if rightward else 0)
                br = box_row(by) + (_NODE_H - 1 if up else 0)
                bc = box_col(bx) + (0 if rightward else _NODE_W - 1)
                _draw_conn(canvas, ar, ac, br, bc)

    # Region labels at each block centre: `<food><holder>` (holder owns all 4 corners).
    for region in gm.regions.values():
        rcoords = [_parse_cr(c) for c in region.corners]
        cx = sum(box_col(x) + _NODE_W // 2 for x, _ in rcoords) // len(rcoords)
        cy = sum(box_row(y) + _NODE_H // 2 for _, y in rcoords) // len(rcoords)
        token = f"{region.food}{_region_holder(state, region) or '·'}"
        _blit(canvas, cy, cx - len(token) // 2, token)

    # HQ boxes on the edge, each fanning out to every front crossroad: a horizontal edge to
    # the one on its own row and a 45-degree / or \ diagonal to the ones above and below.
    for player, side in hq_side.items():
        edge_col = 0 if side == "L" else width - _HQ_W        # HQ box's left column
        inner = _HQ_W - 2
        r0 = box_row(mid_y)
        _blit(canvas, r0, edge_col, "┌" + "─" * inner + "┐")
        _blit(canvas, r0 + 1, edge_col, "│" + " " * inner + "│")
        _blit(canvas, r0 + 2, edge_col, "│" + f"HQ {player}".center(inner) + "│")
        _blit(canvas, r0 + 3, edge_col, "└" + "─" * inner + "┘")

        hq_edge = edge_col + _HQ_W - 1 if side == "L" else edge_col  # HQ side facing the grid
        for cr in gm.hq_connects[player]:
            fx, fy = _parse_cr(cr)
            tgt = box_col(fx) if side == "L" else box_col(fx) + _NODE_W - 1  # target's near side
            if fy == mid_y:                                   # horizontal spur
                row = r0 + 2
                canvas[row][hq_edge] = "├" if side == "L" else "┤"
                canvas[row][tgt] = "┤" if side == "L" else "├"
                _draw_conn(canvas, row, hq_edge, row, tgt)
            elif ri[fy] < ri[mid_y]:                          # front crossroad above -> corner up
                _draw_conn(canvas, r0, hq_edge, box_row(fy) + _NODE_H - 1, tgt)
            else:                                             # front crossroad below -> corner down
                _draw_conn(canvas, r0 + _NODE_H - 1, hq_edge, box_row(fy), tgt)

    return ["".join(row).rstrip() for row in canvas]


_BOX_GAP = 1        # blank columns between adjacent card boxes on a shelf
_BOX_TARGET = 22    # preferred outer box width; columns-per-shelf is derived from this
_BOX_MIN_INNER = 16  # don't shrink a card's text area below this
_BOX_MAX_INNER = 24  # ...and don't stretch it past this (wide terminals get more/narrow cards)
_MAX_COLS = 6       # cap cards-per-shelf so boxes stay readable on very wide terminals


def _truncate(s: str, width: int) -> str:
    return s if len(s) <= width else s[: width - 1] + "…"


def _fit_lr(left: str, right: str, width: int) -> str:
    """Left- and right-justify two labels within `width`, truncating right then left to fit."""
    if len(left) + 1 + len(right) > width:
        right = _truncate(right, max(0, width - len(left) - 1))
    if len(left) + len(right) > width:
        left = _truncate(left, max(0, width - len(right)))
    return left + " " * (width - len(left) - len(right)) + right


def _card_box(state, unit, inner: int, body_h: int) -> list[str]:
    """One card as a bordered box: centred name header, wrapped text body, STR/tags footer.

    `inner` is the text width inside the borders; `body_h` is the shared number of text
    rows on this shelf, so every box's footer lines up along the bottom.
    """
    card = state.cards[unit.card_id]
    eff = strength_mod.placement_strength(state, unit)
    base = card.base_strength
    strength = f"STR {eff}" + (f" (base {base})" if isinstance(base, int) and eff != base else "")

    header = _truncate(card.name, inner).center(inner)
    body = textwrap.wrap(card.text, inner) if card.text else []
    body += [""] * (body_h - len(body))
    footer = _fit_lr(strength, "/".join(sorted(card.tags)), inner)

    top = "┌" + "─" * (inner + 2) + "┐"
    bottom = "└" + "─" * (inner + 2) + "┘"
    # Two blank rows below the name and two above the STR/tag footer give the card air.
    rows = [header, "", ""] + body + ["", ""] + [footer]
    return [top] + [f"│ {r.ljust(inner)} │" for r in rows] + [bottom]


def _format_stacks(state) -> list[str]:
    """List every multi-unit stack bottom->top (the board only shows the top unit)."""
    lines = []
    for cr in sorted(state.board, key=_parse_cr):
        stack = state.board[cr]
        if len(stack) > 1:
            parts = " / ".join(
                f"{u.owner} {state.cards[u.card_id].name} ({strength_mod.effective_strength(state, u)})"
                for u in stack
            )
            lines.append(f"  stack {cr}:  {parts}   (bottom→top)")
    if lines:
        lines.insert(0, "")
    return lines


def _format_hand(state, seat: str, width: int) -> list[str]:
    hand = state.hands[seat]
    lines = [f"HAND — seat {seat} ({len(hand)} card{'s' if len(hand) != 1 else ''})"]
    if not hand:
        lines.append("(empty)")
        return lines

    cols = max(1, min(len(hand), _MAX_COLS, (width + _BOX_GAP) // (_BOX_TARGET + _BOX_GAP)))
    inner = (width - _BOX_GAP * (cols - 1)) // cols - 4
    inner = min(_BOX_MAX_INNER, max(_BOX_MIN_INNER, inner))

    for start in range(0, len(hand), cols):
        shelf = hand[start : start + cols]
        body_h = max(len(textwrap.wrap(state.cards[u.card_id].text, inner)) if state.cards[u.card_id].text else 0
                     for u in shelf)
        boxes = [_card_box(state, u, inner, body_h) for u in shelf]
        for row in zip(*boxes):
            lines.append((" " * _BOX_GAP).join(row))
    return lines


def _status_panel(state) -> list[str]:
    """A small aligned scoreboard: each seat's food (toward the win), hand size, deck size."""
    win = state.game_map.win_food
    row = "   {who:<10}{food:<12}{hand:<8}{deck}"
    lines = [
        row.format(who="", food="FOOD", hand="HAND", deck="DECK"),
        "   " + "─" * 30,
    ]
    for seat in ("A", "B"):
        lines.append(row.format(
            who=f"seat {seat}",
            food=f"{state.food[seat]} / {win}",
            hand=str(len(state.hands[seat])),
            deck=str(len(state.decks[seat])),
        ))
    return lines


def render(state, reveal_hands: Collection[str] = ()) -> str:
    width = _terminal_width()
    lines = []

    if state.result is not None:
        lines.append(f"RESULT: {state.result.winner or 'draw'} ({state.result.reason})")
        lines.append("")
    lines.extend(_render_board(state))
    lines.extend(_format_stacks(state))
    lines.append("")
    lines.extend(_status_panel(state))

    for seat in sorted(reveal_hands):
        lines.append("")
        lines.extend(_format_hand(state, seat, width))
    return "\n".join(lines)
