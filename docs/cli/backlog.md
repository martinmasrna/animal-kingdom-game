# CLI / App — Backlog

Open items only. Top-3 summary in [`../STATUS.md`](../STATUS.md). Code: `animal_kingdom/cli.py`,
`render/`, and `tui/`.

- [x] **Recorder UI/UX polish.**
  - [x] Composition: centre the board, preserve mouse hitboxes, add player/turn bands, and keep
    the 80×24 compact layout working.
  - [x] Make the current decision unmistakable with a contextual action prompt.
  - [x] Turn the right rail into a contextual inspector (selection/hover, stack, recent actions).
  - [x] Show the completed game's JSONL path as a clickable in-app file link.
  - [x] Refine the hand shelf with responsive centring and explicit action states.
  - [x] Move specialist recorder controls into a `?` help overlay.
  - [x] Add responsive deck trackers: exact remaining deck for the human, public
    deck-plus-hand deduction for the opponent, with no hidden-zone reads.
- [ ] **Promote the recorder to the general game TUI — decision: yes (2026-07-04).** Preserve
  automatic JSONL recording while making scheduled cohorts an optional workflow rather than the
  app's identity.
  1. Rename the app and user-facing copy from “recorder” to the general game UI.
  2. Make `./run` launch the Textual UI for human games; preserve its headless bot-game path.
  3. Retire or alias `./record` once the general launcher covers ad-hoc and scheduled play.
