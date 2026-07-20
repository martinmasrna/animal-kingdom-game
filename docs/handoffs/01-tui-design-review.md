# Handoff 01 — TUI design review

You are a product/interaction designer reviewing the human-facing terminal UI for *Animal Kingdom*.
Produce a design brief only. The goal is to make the existing Textual UI clearer and more pleasant;
do not implement or edit code.

## Read first

1. `CLAUDE.md`
2. `docs/STATUS.md` — especially CLI / App
3. `docs/cli/backlog.md`
4. `docs/rules/mental-model.md`
5. `animal_kingdom/tui/` and its tests, as read-only reference

## Current state

The recorder Textual UI received a pass on 2026-07-04: centered board with stable hitboxes,
contextual action prompt and inspector rail, responsive hand shelf, deck trackers, food bars,
in-app JSONL link, and a `?` help overlay. It must remain usable at 80×24. The agreed future
direction is a general game UI, but implementation is parked while the simulation runs.

## Answer these questions

1. What are the highest-value player tasks in a first game, a repeat game, and replay review?
2. What must remain visible, what should be contextual, and what belongs in progressive disclosure?
3. Where will players misunderstand legal placement, stacks/covering, connection, food, or actions?
4. How should the interface degrade from wide terminals to 80×24?
5. What should a general launcher add or rename while retaining recorder/replay usefulness?

## Required output

Write `docs/cli/tui-design-review-YYYY-MM-DD.md` with:

- A one-paragraph UX objective.
- No more than eight prioritized improvements. For each: player problem, proposed behavior/layout,
  why it matters, terminal-size impact, and implementation-risk estimate.
- One wide and one compact ASCII wireframe; label information groups, not widgets.
- Brief flows for empty placement, covering an enemy, and help/inspection.
- Non-goals and unanswered questions.

Separate evidence from hypothesis, and cite a source file or read-only interaction observation for
every high-priority recommendation. Do not prescribe code.

## Done when

Another agent could select one item to implement later without rediscovering the player problem,
layout intent, compact behavior, or risk.

