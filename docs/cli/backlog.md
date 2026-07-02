# CLI / App — Backlog

Open items only. Top-3 summary in [`../STATUS.md`](../STATUS.md). Code: `animal_kingdom/cli.py`, `render/`.

- [x] **One more `rich` visual-polish pass.** Done (commit `7d1b961`): dimmed empty crossroads, held-region chips in the seat color, per-seat food progress bars in the scoreboard, tighter card boxes. Added `test_render.py` (first renderer coverage: runs on both maps, validates the emitted markup).
- [ ] **Board overflows the terminal on `map_b`.** The 5-column map renders ~95 cols wide; `map_a` is 79. On an 80-col terminal `map_b` wraps and the board shatters — and `./run`'s default is map_b + 2-actions, so the *default* looks broken. The renderer draws at fixed geometry and never checks terminal width. Fix: compress node/gap geometry (e.g. `_GAP_W` 7→3 saves 16 cols) or make the board responsive. (Found during the polish pass; deferred.)
- [ ] **Full TUI rewrite (parked).** A real terminal app (`textual`): mouse clicks on the board, arrow-key navigation, persistent panes, live updates. Bigger lift (new dependency, a different interaction model to build/test). Revisit after the polish pass, when `rich` feels limiting.
