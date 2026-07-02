# CLI / App — Backlog

Open items only. Top-3 summary in [`../STATUS.md`](../STATUS.md). Code: `animal_kingdom/cli.py`, `render/`.

- [ ] **One more `rich` visual-polish pass.** A round of board/UX refinement on the current stdin/stdout loop before committing to a full TUI. (Current: color by seat/rarity, in-place redraw on a human's turn, card-first-then-highlighted-target selection.)
- [ ] **Full TUI rewrite (parked).** A real terminal app (`textual`): mouse clicks on the board, arrow-key navigation, persistent panes, live updates. Bigger lift (new dependency, a different interaction model to build/test). Revisit after the polish pass, when `rich` feels limiting.
