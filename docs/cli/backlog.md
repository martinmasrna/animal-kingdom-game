# CLI / App — Backlog

Open items only. Top-3 summary in [`../STATUS.md`](../STATUS.md). Code: `animal_kingdom/cli.py`, `render/`.

- [ ] **Board overflows the terminal on `map_b`.** The 5-column game map renders ~95 cols wide. On an 80-col terminal it wraps and the board shatters — and since map_b is the only map, `./run` looks broken out of the box. The renderer draws at fixed geometry and never checks terminal width. Fix: compress node/gap geometry (e.g. `_GAP_W` 7→3 saves 16 cols) or make the board responsive. (Found during the polish pass; deferred.)
- [ ] **Full TUI rewrite (parked).** A real terminal app (`textual`): mouse clicks on the board, arrow-key navigation, persistent panes, live updates. Bigger lift (new dependency, a different interaction model to build/test). Revisit after the polish pass, when `rich` feels limiting.
- [x] **Human benchmark recorder.** Added a deliberately narrow Textual app (`./record`):
  persistent compact state, click-card/click-target and keyboard controls, background bots,
  scheduled cohorts, and durable decision-level JSONL. This is a data-collection tool; it
  does not replace the parked general-purpose TUI rewrite.
