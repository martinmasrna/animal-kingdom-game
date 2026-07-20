# Handoff 05 — Card-pool content audit

You are conducting a design/content audit of the seven-deck shipped pool. Find unclear identity,
redundancy, generic-value risks, missing interaction, rules-text inconsistency, and flavor collisions.
This is audit-only: do not edit data, code, rules, or the active simulation.

## Read first

1. `CLAUDE.md`
2. `docs/STATUS.md`
3. `docs/rules/mental-model.md`, `docs/rules/overview.md`, and `docs/rules/keywords.md`
4. `docs/cards/backlog.md`
5. `docs/cards/decks/README.md`
6. Every file in `docs/cards/decks/`
7. `docs/cards/decks/flavor-review.md`
8. `docs/cards/card-candidates.md` only after the shipped pool is understood

## Audit lens

The intended identities are Cats midrange tempo, Egg control, Colony food swarm, Ramp, Food OTK,
Aggro HQ rush, and Canine buff tempo. Narrow cards can be correct when they pay for archetype
commitment; broadly useful body-plus-draw/removal/reach cards are risky in open construction.

Landmarks have been removed. Treat Landmark candidates and dependencies as re-casting/retirement
questions, not live cards.

## Required output

Write `docs/cards/card-pool-audit-YYYY-MM-DD.md` with:

- An identity map for all seven decks: win condition, commitment, deliberate weakness, counterplay.
- At most fifteen findings classified as redundancy, generic-value risk, missing role, text issue,
  flavor/name issue, or stale documentation.
- For each finding: concrete references, confidence, why it matters, and disposition (keep,
  investigate, redesign later, wording-only, reskin, or retire).
- Cross-deck overlap: distinguish healthy bridge cards from identity erosion.
- A non-mechanical flavor/text cleanup queue, including legendary names and species collisions.
- The five best post-results priorities, and whether each is balance-gated.

Do not recommend balance numbers without valid current data. Deck files and `cards.json`, not legacy
parts of `docs/cards/cards.md`, are the pool source of truth.

## Done when

The project can separate harmless cleanup from genuine identity and balance risks.

