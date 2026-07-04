# CLI / App — Backlog

Open items only. Top-3 summary in [`../STATUS.md`](../STATUS.md). Code: `animal_kingdom/cli.py`,
`render/`, and `tui/`.

- [ ] **Continue the recorder UI/UX polish in small passes.**
  - [x] Composition: centre the board, preserve mouse hitboxes, add player/turn bands, and keep
    the 80×24 compact layout working.
  - [x] Make the current decision unmistakable with a contextual action prompt.
  - [x] Turn the right rail into a contextual inspector (selection/hover, stack, recent actions).
  - [x] Show the completed game's JSONL path as a terminal hyperlink.
  - [ ] Refine the hand shelf and reduce specialist recorder noise in the footer.
- [ ] **Decide whether the recorder becomes the general game TUI.** It already has mouse board
  targeting, keyboard navigation, persistent panes, background bots, scheduled cohorts, and
  durable decision-level JSONL. The old “full TUI rewrite” description is obsolete; what remains
  is product scope and incremental polish.
