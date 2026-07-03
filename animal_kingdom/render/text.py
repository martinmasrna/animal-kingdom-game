"""ASCII renderer for sanity-checking the engine in the terminal.

Pure: takes a GameState, returns a string (no printing) - a plain string carrying Rich
markup tags (`[style]...[/style]`), not an ANSI-encoded one. Callers print it through a
`rich.console.Console` (markup interpretation on by default); the module itself has no
dependency on rich, so it stays trivially usable without a terminal.

Draws the board as a graph of crossroad nodes wired by the map's actual edges, with each
region's food value + current holder printed in the block it sits on, and stack depth
shown per node (full stack composition listed below the board). Also renders food / hand
/ deck counts, the turn, the seat to act, and the result. Optionally renders the full hand
(card boxes) for seats passed in `reveal_hands` - callers must only pass a seat whose hand
isn't hidden (a human player's own seat), never an opponent's.

A card-selection UI can pass `highlight_crs`/`highlight_hq` to mark legal placement
targets on the board (a green box border) while the player picks one.
"""

from __future__ import annotations

import shutil
import textwrap
from dataclasses import dataclass
from typing import Collection

from ..engine import strength as strength_mod

# Shared with cli.py so the interactive picker's prompts match the board's colors.
SEAT_STYLE = {"A": "bold cyan", "B": "bold red"}
HIGHLIGHT_STYLE = "bold green"          # a legal target the player is currently choosing among
FOCUS_STYLE = "bold yellow"             # keyboard-focused target within the legal targets
RARITY_STYLE = {"legendary": "bold gold3", "rare": "bold blue"}  # common: unstyled
EMPTY_STYLE = "grey42"                  # unoccupied crossroads / unheld regions: recede into the board
# A held region is drawn as a filled chip in the holder's seat color, so controlled
# territory reads at a glance against the dimmed empty blocks.
REGION_HELD_STYLE = {"A": "bold white on cyan", "B": "bold white on red"}

_MIN_WIDTH = 72    # floor so wrapping stays sane when a terminal reports something tiny

# Board node/gap geometry (characters). A node is a bordered box; gaps hold the edges
# between adjacent crossroads and, at each 2x2 block centre, the region food label.
_NODE_W = 9        # node box width incl. borders
_NODE_H = 4        # node box height incl. borders (border, coord, occupancy, border)
_GAP_W = 7         # horizontal gap between node columns
_GAP_H = 3         # vertical gap between node rows
_HQ_W = 8          # HQ box width incl. borders
_HQ_GAP = _GAP_H   # HQ<->front-column gap; == _GAP_H so the fan-out diagonals sit at 45 deg


@dataclass(frozen=True)
class Hitbox:
    """A visible rectangular target in rendered board coordinates."""

    x: int
    y: int
    width: int
    height: int

    def contains(self, x: int, y: int) -> bool:
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height


@dataclass(frozen=True)
class BoardRender:
    """Rich markup plus mouse hitboxes keyed by engine target tuples."""

    markup: str
    hitboxes: dict[tuple[str, str], Hitbox]
    width: int
    height: int


def _terminal_width() -> int:
    return max(_MIN_WIDTH, shutil.get_terminal_size(fallback=(100, 24)).columns)


def parse_cr(cr: str) -> tuple[int, int]:
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


def _style(text: str, style: str | None) -> str:
    """Wrap already-final (padded/centered) plain text in a Rich markup span.

    Callers must finish all width-sensitive formatting (center/ljust/truncate) on the
    *plain* text first - wrapping adds characters that would throw off further padding.
    """
    return f"[{style}]{text}[/{style}]" if style else text


def _blit(canvas: list[list[str]], style_grid: list[list[str | None]],
          row: int, col: int, text: str, style: str | None = None) -> None:
    """Write `text` into the plain-character canvas, and record `style` per cell.

    The canvas itself stays one-character-per-cell throughout construction (later edge/
    label drawing indexes into it by exact column), so color is tracked in a parallel
    `style_grid` and only turned into markup once the whole board is laid out - see
    `_canvas_to_lines`.
    """
    for i, ch in enumerate(text):
        canvas[row][col + i] = ch
        style_grid[row][col + i] = style


def _canvas_to_lines(canvas: list[list[str]], style_grid: list[list[str | None]]) -> list[str]:
    """Flatten the canvas to strings, wrapping each contiguous same-style run in markup."""
    lines = []
    for row_chars, row_styles in zip(canvas, style_grid):
        parts, i, n = [], 0, len(row_chars)
        while i < n:
            style = row_styles[i]
            j = i
            while j < n and row_styles[j] == style:
                j += 1
            parts.append(_style("".join(row_chars[i:j]), style))
            i = j
        lines.append("".join(parts).rstrip())
    return lines


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


def _render_diagonal_board(
    state,
    *,
    perspective_player: str,
    highlight_crs: Collection[str],
    highlight_hq: str | None,
    focus_target: tuple[str, str] | None,
    max_width: int | None,
    max_height: int | None,
) -> BoardRender:
    """Player-relative square projection: own HQ bottom-left, opponent top-right."""
    gm = state.game_map
    if perspective_player not in gm.hq_connects:
        raise ValueError(f"unknown perspective player {perspective_player!r}")
    coords = [parse_cr(c) for c in gm.crossroads]
    xs = sorted({x for x, _ in coords})
    ys_top_first = sorted({y for _, y in coords}, reverse=True)
    ci = {x: i for i, x in enumerate(xs)}
    ri = {y: i for i, y in enumerate(ys_top_first)}

    front_xs = {parse_cr(cr)[0] for cr in gm.hq_front(perspective_player)}
    own_on_left = front_xs == {min(xs)}
    if not own_on_left and front_xs != {max(xs)}:
        raise ValueError("diagonal projection requires an HQ on a vertical map edge")

    slots = len(xs) + len(ys_top_first) - 1
    compact_nodes = max_height is not None and max_height < 22
    node_w, node_h = _NODE_W, 3 if compact_nodes else _NODE_H
    if max_width is None:
        col_step = 10
    else:
        col_step = max(node_w, min(10, (max_width - node_w) // max(1, slots - 1)))
    if compact_nodes:
        row_step = 2
    elif max_height is None or max_height >= (slots - 1) * 4 + node_h:
        row_step = 4
    elif max_height >= (slots - 1) * 3 + node_h:
        row_step = 3
    else:
        row_step = 2
    width = (slots - 1) * col_step + node_w
    height = (slots - 1) * row_step + node_h
    canvas = [[" "] * width for _ in range(height)]
    style_grid: list[list[str | None]] = [[None] * width for _ in range(height)]
    hitboxes: dict[tuple[str, str], Hitbox] = {}

    positions: dict[str, tuple[int, int]] = {}
    for x, y in coords:
        forward = ci[x] if own_on_left else len(xs) - 1 - ci[x]
        lateral = ri[y] if own_on_left else len(ys_top_first) - 1 - ri[y]
        slot_col = forward + lateral
        slot_row = (len(xs) - 1 - forward) + lateral
        positions[f"{x},{y}"] = (slot_row * row_step, slot_col * col_step)

    players = tuple(sorted(gm.hq_connects))
    opponent = next(player for player in players if player != perspective_player)
    hq_positions = {
        perspective_player: (height - node_h, 0),
        opponent: (0, width - _HQ_W),
    }

    # Connections go down first, then labels and boxes overwrite their interiors.
    for a, b in gm.edges:
        ar, ac = positions[a]
        br, bc = positions[b]
        _draw_conn(
            canvas,
            ar + node_h // 2,
            ac + node_w // 2,
            br + node_h // 2,
            bc + node_w // 2,
        )
    for player, fronts in gm.hq_connects.items():
        hr, hc = hq_positions[player]
        for cr in fronts:
            nr, nc = positions[cr]
            _draw_conn(
                canvas,
                hr + node_h // 2,
                hc + _HQ_W // 2,
                nr + node_h // 2,
                nc + node_w // 2,
            )

    # Region value/holder chips stay at the projected centre of their four corners.
    for region in gm.regions.values():
        centres = [
            (positions[cr][0] + node_h // 2, positions[cr][1] + node_w // 2)
            for cr in region.corners
        ]
        row = sum(r for r, _ in centres) // len(centres)
        col = sum(c for _, c in centres) // len(centres)
        holder = _region_holder(state, region)
        token = f"{region.food}{holder or '·'}"
        style = REGION_HELD_STYLE[holder] if holder else EMPTY_STYLE
        col = max(0, min(width - len(token), col - len(token) // 2))
        _blit(canvas, style_grid, row, col, token, style)

    for cr, (r0, c0) in positions.items():
        hitboxes[("cr", cr)] = Hitbox(c0, r0, node_w, node_h)
        x, y = parse_cr(cr)
        inner = node_w - 2
        box_style = (
            FOCUS_STYLE if focus_target == ("cr", cr)
            else HIGHLIGHT_STYLE if cr in highlight_crs
            else None
        )
        stack = state.board.get(cr)
        occ_style = SEAT_STYLE.get(stack[-1].owner) if stack else EMPTY_STYLE
        if compact_nodes:
            _blit(
                canvas,
                style_grid,
                r0,
                c0,
                "┌" + f"{x},{y}".center(inner, "─") + "┐",
                box_style,
            )
            _blit(canvas, style_grid, r0 + 1, c0, "│", box_style)
            _blit(canvas, style_grid, r0 + 1, c0 + 1, _occupancy(state, cr).center(inner), occ_style)
            _blit(canvas, style_grid, r0 + 1, c0 + 1 + inner, "│", box_style)
            _blit(canvas, style_grid, r0 + 2, c0, "└" + "─" * inner + "┘", box_style)
        else:
            _blit(canvas, style_grid, r0, c0, "┌" + "─" * inner + "┐", box_style)
            _blit(canvas, style_grid, r0 + 1, c0, "│" + f"{x},{y}".center(inner) + "│", box_style)
            _blit(canvas, style_grid, r0 + 2, c0, "│", box_style)
            _blit(canvas, style_grid, r0 + 2, c0 + 1, _occupancy(state, cr).center(inner), occ_style)
            _blit(canvas, style_grid, r0 + 2, c0 + 1 + inner, "│", box_style)
            _blit(canvas, style_grid, r0 + 3, c0, "└" + "─" * inner + "┘", box_style)

    for player, (r0, c0) in hq_positions.items():
        hitboxes[("hq", player)] = Hitbox(c0, r0, _HQ_W, node_h)
        inner = _HQ_W - 2
        hq_style = (
            FOCUS_STYLE if focus_target == ("hq", player)
            else HIGHLIGHT_STYLE if player == highlight_hq
            else SEAT_STYLE.get(player)
        )
        _blit(canvas, style_grid, r0, c0, "┌" + "─" * inner + "┐", hq_style)
        if compact_nodes:
            _blit(canvas, style_grid, r0 + 1, c0, "│" + f"HQ {player}".center(inner) + "│", hq_style)
            _blit(canvas, style_grid, r0 + 2, c0, "└" + "─" * inner + "┘", hq_style)
        else:
            _blit(canvas, style_grid, r0 + 1, c0, "│" + " " * inner + "│", hq_style)
            _blit(canvas, style_grid, r0 + 2, c0, "│" + f"HQ {player}".center(inner) + "│", hq_style)
            _blit(canvas, style_grid, r0 + 3, c0, "└" + "─" * inner + "┘", hq_style)

    # A raw backslash immediately before a Rich/Textual tag escapes the opening bracket.
    # Box-drawing diagonals avoid that markup ambiguity and read better in this projection.
    for row in canvas:
        for index, char in enumerate(row):
            if char == "\\":
                row[index] = "╲"
            elif char == "/":
                row[index] = "╱"

    return BoardRender(
        markup="\n".join(_canvas_to_lines(canvas, style_grid)),
        hitboxes=hitboxes,
        width=width,
        height=height,
    )


def render_board(state, highlight_crs: Collection[str] = (),
                 highlight_hq: str | None = None,
                 focus_target: tuple[str, str] | None = None,
                 max_width: int | None = None,
                 vertical_gap: int = _GAP_H,
                 perspective_player: str | None = None,
                 max_height: int | None = None) -> BoardRender:
    """Render the board and expose target hitboxes for mouse-driven clients.

    Horizontal gaps shrink from seven to one cell when necessary, allowing Map B to fit
    an 80-column terminal without changing node size or truncating state.
    """
    if perspective_player is not None:
        return _render_diagonal_board(
            state,
            perspective_player=perspective_player,
            highlight_crs=highlight_crs,
            highlight_hq=highlight_hq,
            focus_target=focus_target,
            max_width=max_width,
            max_height=max_height,
        )
    gm = state.game_map
    if vertical_gap < 1:
        raise ValueError("vertical_gap must be at least 1")
    coords = [parse_cr(c) for c in gm.crossroads]
    xs = sorted({x for x, _ in coords})
    ys_top_first = sorted({y for _, y in coords}, reverse=True)  # highest y drawn at the top
    ci = {x: i for i, x in enumerate(xs)}          # grid x -> screen column index
    ri = {y: i for i, y in enumerate(ys_top_first)}  # grid y -> screen row index (0 = top)
    mid_y = ys_top_first[len(ys_top_first) // 2]      # vertically-central row (HQ height)

    # Which players' HQs sit on the left (min column) / right (max column) edge.
    hq_side = {}  # player -> "L"/"R"
    for player, fronts in gm.hq_connects.items():
        fx = {parse_cr(c)[0] for c in fronts}
        if fx == {min(xs)}:
            hq_side[player] = "L"
        elif fx == {max(xs)}:
            hq_side[player] = "R"
    left = _HQ_W + _HQ_GAP if "L" in hq_side.values() else 0
    right = _HQ_W + _HQ_GAP if "R" in hq_side.values() else 0

    gap_w = _GAP_W
    if max_width is not None and len(xs) > 1:
        fixed = left + right + len(xs) * _NODE_W
        gap_w = max(1, min(_GAP_W, (max_width - fixed) // (len(xs) - 1)))

    height = len(ys_top_first) * _NODE_H + (len(ys_top_first) - 1) * vertical_gap
    grid_w = len(xs) * _NODE_W + (len(xs) - 1) * gap_w
    width = left + grid_w + right
    canvas = [[" "] * width for _ in range(height)]
    style_grid: list[list[str | None]] = [[None] * width for _ in range(height)]
    hitboxes: dict[tuple[str, str], Hitbox] = {}

    def box_col(x: int) -> int:
        return left + ci[x] * (_NODE_W + gap_w)

    def box_row(y: int) -> int:
        return ri[y] * (_NODE_H + vertical_gap)

    # Nodes: a bordered box with the coordinate and the current occupancy. The border is
    # highlighted green when this crossroad is a legal target; the occupancy text is
    # colored by whichever seat owns the top unit, independent of the highlight.
    for x, y in coords:
        cr = f"{x},{y}"
        r0, c0 = box_row(y), box_col(x)
        hitboxes[("cr", cr)] = Hitbox(c0, r0, _NODE_W, _NODE_H)
        inner = _NODE_W - 2
        box_style = (
            FOCUS_STYLE if focus_target == ("cr", cr)
            else HIGHLIGHT_STYLE if cr in highlight_crs
            else None
        )
        stack = state.board.get(cr)
        occ_style = SEAT_STYLE.get(stack[-1].owner) if stack else EMPTY_STYLE

        _blit(canvas, style_grid, r0, c0, "┌" + "─" * inner + "┐", box_style)
        _blit(canvas, style_grid, r0 + 1, c0, "│" + f"{x},{y}".center(inner) + "│", box_style)
        _blit(canvas, style_grid, r0 + 2, c0, "│", box_style)
        _blit(canvas, style_grid, r0 + 2, c0 + 1, _occupancy(state, cr).center(inner), occ_style)
        _blit(canvas, style_grid, r0 + 2, c0 + 1 + inner, "│", box_style)
        _blit(canvas, style_grid, r0 + 3, c0, "└" + "─" * inner + "┘", box_style)

    # Edges from the map's real adjacency: orthogonal ones use tees + a straight run;
    # diagonal neighbours are wired corner-to-corner with / or \. Each undirected edge is
    # drawn once (skipped from the higher-coordinate endpoint).
    for x, y in coords:
        for b in gm.neighbors(f"{x},{y}"):
            bx, by = parse_cr(b)
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
        rcoords = [parse_cr(c) for c in region.corners]
        cx = sum(box_col(x) + _NODE_W // 2 for x, _ in rcoords) // len(rcoords)
        cy = sum(box_row(y) + _NODE_H // 2 for _, y in rcoords) // len(rcoords)
        holder = _region_holder(state, region)
        token = f"{region.food}{holder or '·'}"
        style = REGION_HELD_STYLE[holder] if holder else EMPTY_STYLE
        _blit(canvas, style_grid, cy, cx - len(token) // 2, token, style)

    # HQ boxes on the edge, each fanning out to every front crossroad: a horizontal edge to
    # the one on its own row and a 45-degree / or \ diagonal to the ones above and below.
    # Always tinted by owning seat; green overrides while it's a legal capture target.
    for player, side in hq_side.items():
        edge_col = 0 if side == "L" else width - _HQ_W        # HQ box's left column
        inner = _HQ_W - 2
        r0 = box_row(mid_y)
        hitboxes[("hq", player)] = Hitbox(edge_col, r0, _HQ_W, _NODE_H)
        hq_style = (
            FOCUS_STYLE if focus_target == ("hq", player)
            else HIGHLIGHT_STYLE if player == highlight_hq
            else SEAT_STYLE.get(player)
        )
        _blit(canvas, style_grid, r0, edge_col, "┌" + "─" * inner + "┐", hq_style)
        _blit(canvas, style_grid, r0 + 1, edge_col, "│" + " " * inner + "│", hq_style)
        _blit(canvas, style_grid, r0 + 2, edge_col, "│" + f"HQ {player}".center(inner) + "│", hq_style)
        _blit(canvas, style_grid, r0 + 3, edge_col, "└" + "─" * inner + "┘", hq_style)

        hq_edge = edge_col + _HQ_W - 1 if side == "L" else edge_col  # HQ side facing the grid
        for cr in gm.hq_connects[player]:
            fx, fy = parse_cr(cr)
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

    return BoardRender(
        markup="\n".join(_canvas_to_lines(canvas, style_grid)),
        hitboxes=hitboxes,
        width=width,
        height=height,
    )


def _render_board(state, highlight_crs: Collection[str] = (),
                  highlight_hq: str | None = None,
                  max_width: int | None = None) -> list[str]:
    """Compatibility wrapper used by the complete terminal renderer."""
    return render_board(
        state,
        highlight_crs=highlight_crs,
        highlight_hq=highlight_hq,
        max_width=max_width,
    ).markup.splitlines()


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


_RARITY_GLYPH = {"legendary": "★", "rare": "◆"}  # printed even without color (accessibility)


def _card_box(state, unit, inner: int, body_h: int) -> list[str]:
    """One card as a bordered box: centred name header, wrapped text body, STR/tags footer.

    `inner` is the text width inside the borders; `body_h` is the shared number of text
    rows on this shelf, so every box's footer lines up along the bottom. The border and
    name are tinted by rarity (legendary/rare); common cards are left unstyled.
    """
    card = state.cards[unit.card_id]
    eff = strength_mod.placement_strength(state, unit)
    base = card.base_strength
    strength = f"STR {eff}" + (f" (base {base})" if isinstance(base, int) and eff != base else "")
    style = RARITY_STYLE.get(card.rarity)
    glyph = _RARITY_GLYPH.get(card.rarity, "")
    name = f"{glyph} {card.name}" if glyph else card.name

    header = _style(_truncate(name, inner).center(inner), style)
    body = textwrap.wrap(card.text, inner) if card.text else []
    body += [""] * (body_h - len(body))
    footer = _fit_lr(strength, "/".join(sorted(card.tags)), inner)

    top = _style("┌" + "─" * (inner + 2) + "┐", style)
    bottom = _style("└" + "─" * (inner + 2) + "┘", style)
    # One blank row below the name and one above the STR/tag footer give the card air
    # without the old double gap that left tall cards mostly empty.
    rows = [header, ""] + body + ["", footer]
    return [top] + [f"│ {r.ljust(inner)} │" for r in rows] + [bottom]


def _format_stacks(state) -> list[str]:
    """List every multi-unit stack bottom->top (the board only shows the top unit)."""
    lines = []
    for cr in sorted(state.board, key=parse_cr):
        stack = state.board[cr]
        if len(stack) > 1:
            parts = " / ".join(
                _style(f"{u.owner} {state.cards[u.card_id].name} "
                       f"({strength_mod.effective_strength(state, u)})", SEAT_STYLE.get(u.owner))
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


def _cell(text: str, width: int, style: str | None = None) -> str:
    """Left-pad `text` to `width` on its plain length, then style the padded chunk.

    Padding first (then styling) keeps the visible column width correct - `_style` only
    wraps text that's already done with width-sensitive formatting.
    """
    return _style(text.ljust(width), style)


_BAR_W = 16     # food progress-bar width in cells


def _food_bar(food: int, win: int, fill_style: str | None) -> str:
    """A `_BAR_W`-cell progress bar toward `win` food; overfill clamps to full."""
    frac = max(0.0, min(1.0, food / win)) if win else 0.0
    filled = round(frac * _BAR_W)
    return _style("█" * filled, fill_style) + _style("░" * (_BAR_W - filled), EMPTY_STYLE)


def _status_panel(state) -> list[str]:
    """A per-seat scoreboard: a food progress bar toward the win, then hand / deck counts.

    The bar fills in the seat's color and flips to green once a seat is within striking
    distance of the win (the same 75% threshold the old numeric readout highlighted).
    """
    win = state.game_map.win_food
    lines = []
    for seat in ("A", "B"):
        food = state.food[seat]
        near = food >= win * 0.75
        fill_style = "bold green" if near else SEAT_STYLE[seat]
        count = _style(f"{food}/{win}".rjust(7), "bold green" if near else None)
        lines.append(
            "   " + _cell(f"seat {seat}", 8, SEAT_STYLE[seat])
            + _food_bar(food, win, fill_style) + "  " + count
            + _cell(f"   hand {len(state.hands[seat])}", 12)
            + f"deck {len(state.decks[seat])}"
        )
    return lines


def render(state, reveal_hands: Collection[str] = (),
           highlight_crs: Collection[str] = (), highlight_hq: str | None = None) -> str:
    """`highlight_crs`/`highlight_hq` are passed straight to `_render_board` - used by a
    card-selection UI to mark that card's legal targets while the player picks one."""
    width = _terminal_width()
    lines = []

    if state.result is not None:
        winner = state.result.winner
        style = SEAT_STYLE.get(winner) if winner else "bold yellow"
        lines.append(_style(f"RESULT: {winner or 'draw'} ({state.result.reason})", style))
        lines.append("")
    lines.extend(_render_board(
        state,
        highlight_crs=highlight_crs,
        highlight_hq=highlight_hq,
        max_width=width,
    ))
    lines.extend(_format_stacks(state))
    lines.append("")
    lines.extend(_status_panel(state))

    for seat in sorted(reveal_hands):
        lines.append("")
        lines.extend(_format_hand(state, seat, width))
    return "\n".join(lines)
