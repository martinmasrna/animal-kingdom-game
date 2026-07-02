# Meta — Backlog

Open items only. Top-3 summary in [`../STATUS.md`](../STATUS.md). Meta = the dashboard, roadmap/milestones, conventions.

- [x] **Project-level `CLAUDE.md`** — repo `CLAUDE.md` at root (orientation, commands, invariants, workflow). Done.
- **Project skills** — reusable procedures (loaded on demand; a skill is a *procedure with judgment*, not a one-liner — commands live in `CLAUDE.md`):
  - [x] **Balance-change evaluation skill** — built: `.claude/skills/balance-eval/`. "Does this change help?" procedure: paired-seed, both-seat run at ≥200/matchup → deltas + CIs → read vs targets (deck 40–60%, card ±10%) → triage (real card signal → Balance / bot artifact → Bots) → never nerf-to-fix-a-bot → record with provenance. Bot-change validation folded in as a branch.
  - [ ] **Flavor-review pass skill** — audit card + legendary names against `../cards/cards.md` §2.1: evoke-don't-cite, real species, effect↔name fit, no collisions, one-species rule, register consistency; plus the stricter legendary pass. Pairs with the Cards flavor backlog.
  - [ ] **Card-design skill** — power calibration (no mana; strength *is* the body; Lion 7 baseline), 4-4-6 rarity shape, keyword conventions, one-species rule, numbers as `engine/config.py` placeholders. Lower priority (pool is content-complete).
- Docs reorg (STATUS.md dashboard + this per-area backlog split) — **done**; `todo.md` retired. Keep `STATUS.md` the session entry point.
