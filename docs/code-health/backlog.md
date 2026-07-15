# Code Health — Backlog

Open items only. The first systematic pass is complete; see the [review](review-2026-07-15.md), durable [tech-debt register](tech-debt-register.md), observed [conventions](conventions.md), and [effect/data inventory](effect-data-inventory-2026-07-15.md). Cross-cutting quality work lives here; subsystem fixes proposed by the review belong in their owning area backlogs.

- [ ] **Close the cross-cutting text/config consistency gap.** Establish and enforce one representation/guard policy for every printed numeric card effect; the review found hard-coded non-food values outside the guard.
- [ ] **Define the engine purity boundary and add boundary-level contracts.** Decide the loader-I/O exception (or move it), then prioritize action-validation, checkpoint-identity, and CLI/analysis smoke coverage with the owning areas.
