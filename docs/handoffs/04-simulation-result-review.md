# Handoff 04 — Simulation-result review template

You are a balance analyst preparing for a simulation that is **currently running**. Do not modify,
stop, restart, monitor, or compete with the run. Produce a read-only analysis template and rubric.

## Read first

1. `CLAUDE.md`
2. `docs/STATUS.md` — Balance and Bots
3. `docs/balance/baseline-deck-arc.md`
4. `docs/balance/simulation-results-5.md`
5. `docs/balance/backlog.md`
6. `docs/bots/pilot-ratings.md` and `docs/bots/backlog.md`
7. `docs/rules/timed-effect-ruling.md`
8. `docs/rules/mental-model.md`

## Evidence constraints

All benchmark data from before 2026-07-15 is superseded: the baseline ruler contained timed-effect
bugs, Draw now draws 2, and Ramp changed after the Landmark cut. The re-run is baseline versus all
seven field decks at RefereeBot quality, both seats. Baseline-versus-synergy still risks pilot bias,
especially Egg Control and Ramp. Never tune a card to compensate for a bot blind spot.

## Required output

Write `docs/balance/simulation-review-template-YYYY-MM-DD.md` containing:

- A preflight checklist: ruleset, commit/data identity, decklists, pilot, games, seats, seeds,
  incomplete-run check, and result provenance.
- A matchup table template: both-seat win rate, CI, sample size, baseline comparison, caveats.
- A per-card template by rarity using within-deck/same-rarity impact and a resolution floor.
- A decision tree: valid signal; pilot artifact; insufficient evidence; data/rig problem; rules discontinuity.
- A one-page readout format: maximum three proposed actions plus a "do not act" section.
- Specific checks for scaling decks and the row-1/3 HQ-lane blind spot.

Do not fill it with guessed outcomes. Cite project docs for validity rules and identify any metrics
the result format cannot supply.

## Done when

A fresh agent can issue a defensible first read without rerunning games or treating bot weakness as balance.

