# Parallel design-session handoffs

These prompts are documentation and design only. A long-running simulation is active, so none
authorizes edits to code, card data, configuration, tests, launch scripts, or the simulation process.

| Handoff | Best for | Expected result |
|---|---|---|
| [01 — TUI design review](01-tui-design-review.md) | Improving the human-facing Textual experience | UX brief and wireframes |
| [02 — Aggro HQ-rush redesign](02-aggro-hq-rush-redesign.md) | Continuing the existing aggro redesign | Candidate deck direction |
| [03 — Card-design backlog](03-card-design-backlog.md) | Creating future card-design work | Ranked candidate slate |
| [04 — Simulation-result review](04-simulation-result-review.md) | Preparing for the active cohort's results | Decision-ready analysis template |
| [05 — Card-pool content audit](05-card-pool-content-audit.md) | Finding identity and content gaps | Evidence-backed audit |
| [06 — Game-feel north star](06-game-feel-north-star.md) | Aligning design choices around player experience | Design charter |

## Shared simulation boundary

- Do not edit `animal_kingdom/`, `configs/`, `data/cards.json`, tests, launchers, or engine configuration.
- Do not stop, restart, inspect, or compete with the active simulation. Treat its eventual files as read-only evidence.
- Start with `CLAUDE.md` and `docs/STATUS.md`. Any card, balance, or gameplay reasoning must also start with `docs/rules/mental-model.md`.
- Write only the requested session report under `docs/` (or return it in chat). A report is a proposal, not a decision or license to implement it.

