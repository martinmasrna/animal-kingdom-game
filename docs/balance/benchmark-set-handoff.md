# Handoff: A trustworthy way to judge card power

_Written 2026-07-11 as a cold-start brief. This states a **problem** and a **goal**. The **approach
is deliberately left open** — designing the solution is the job, not something this doc prescribes._

## The problem

New cards keep getting designed **top-down from intent** ("what effect serves the plan?") and never
checked **bottom-up against the existing pool's power level**. So cards ship that are strictly
dominated by — or plainly weaker/stronger than — cards already in the pool, and it isn't caught
until someone eyeballs it later.

Root cause: there is **no known-fair reference to compare against**, and **no step that forces the
comparison** to happen.

## What makes this genuinely hard (so the approach isn't naive)

The game has **no mana and no cost system**. **Read [`../rules/mental-model.md`](../rules/mental-model.md)
first.** Three consequences shape the problem — worth internalizing before designing a solution:

- **Strength is the ruler, not something you benchmark.** Vanilla bodies are strictly ordered (a 7
  beats a 5, always) — there is nothing to "balance" among them. Any approach that tries to is a
  dead end.
- **The non-obvious question is the value of an *effect*** — "what strength is effect E worth?" That
  is not answerable from the armchair; it needs measurement, and it is **contextual** (an effect can
  be fair in one deck and broken in another).
- **So it cannot be a fixed pricing formula.** ("Effect X always costs Y strength" is the mana-cost
  thinking this game rejects.) Whatever gets built can catch *gross* mistakes; it cannot *certify*
  balance — only sim-in-context does that.

## The goal

A **trustworthy, repeatable way to answer**, for any proposed or changed card: *"is this fairly
powered relative to what's already in the pool?"* — trustworthy enough that card design **can't skip
it**. Success looks like:

- A **known-fair reference** to measure against — one that is *not* just an anointed existing pool
  card, since much of the pool is itself mis-costed (that's the underlying balance problem).
- A **discipline that forces the comparison up front**, before a card is proposed rather than after.

The *form* of the reference, how it's validated, and how the check is enforced are all yours to
decide.

## Resources

- **Rules:** [`../rules/mental-model.md`](../rules/mental-model.md) (read first),
  `../rules/overview.md`, `../rules/keywords.md`.
- **Card data:** `animal_kingdom/data/cards.json`. **Strength/balance constants:**
  `animal_kingdom/engine/config.py` (tuned there, never hard-coded in effect logic).
- **Sim methodology:** the `balance-eval` skill; `./report`; `sim/measure_deck.py`.
- **Background** (why the project needs many new cards):
  [`goodstuff-investigation.md`](goodstuff-investigation.md) — read for context, not for card-design
  direction. **Project map:** `docs/STATUS.md`. **Memory:** `no-mana-power-calibration` (Lion 7 =
  vanilla baseline).

## Scope

- This is the **measuring instrument** only — do **not** redesign any deck or design cards for a
  specific archetype.
- Beyond the three example misses above, don't pull in other in-flight card designs — build the
  benchmark **unbiased**.
