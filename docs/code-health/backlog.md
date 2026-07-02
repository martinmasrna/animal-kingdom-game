# Code Health — Backlog

Open items only. Top-3 summary in [`../STATUS.md`](../STATUS.md). Cross-cutting code quality across Engine + Bots + CLI + sim (subsystem-local work stays in those areas).

- [ ] **Full code-review pass across the whole repo.** The first systematic quality pass. Codebase is milestone-built (M0–M6) with a green suite (252 passing) and a deliberate architecture (data / config / effect-registry split, pure stdlib engine) — but has never been audited end-to-end.
- [ ] **Code conventions + a tech-debt register.** Write down conventions (naming, structure, testing) and start a tracked tech-debt list so known seams — e.g. the `UnitInstance` object model → struct-of-arrays switch (`../engine/backlog.md`) — are captured, not rediscovered.
