# CLI / App — Backlog

Open items only. Top-3 summary in [`../STATUS.md`](../STATUS.md). Code: `animal_kingdom/cli.py`,
`render/`, and `tui/`.

- [ ] **Promote the recorder to the general game TUI — decision: yes (2026-07-04).** Preserve
  automatic JSONL recording while making scheduled cohorts an optional workflow rather than the
  app's identity.
  1. Rename the app and user-facing copy from “recorder” to the general game UI.
  2. Make `./run` launch the Textual UI for human games; preserve its headless bot-game path.
  3. Retire or alias `./record` once the general launcher covers ad-hoc and scheduled play.
- [ ] **Persist game settings between games** — the launcher/UI should remember the last-used
  settings rather than resetting each game.
- [ ] **Drop crossroad coordinates** — coordinate labels on crossroads are no longer needed in the
  render.
