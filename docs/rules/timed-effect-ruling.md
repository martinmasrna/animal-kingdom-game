# Ruling: timed effects and the stack ("in N turns")

_Ruled 2026-07-15. Canonical text is [`overview.md`](overview.md) §9.1 — if this doc and that
disagree, that wins. This file holds the evidence, the blast radius, and the engine work implied._

## The ruling in three lines

1. A pending timer **advances only while its unit is the topmost unit of its crossroad.** Buried =
   suspended, not lost; it resumes if the unit becomes visible again.
2. **Removal cancels** the pending effect outright.
3. **Bounce resets** it — a replayed unit starts a fresh timer.

## Why (it isn't a new rule)

`overview.md` §7.1 already says only the topmost unit occupies, connects, is selectable, and owns
the crossroad; `mental-model.md` says covered units "aren't dead — they **wait** under the stack."
§9 already fizzles a queued *reaction* whose unit has left the board. Nobody had written down what
that implies for *timed* effects, so the engine went its own way. This ruling just applies the
existing principle to the case it never covered.

## What the code actually does today (surveyed 2026-07-15)

`schedule(state, owner, owner_turn_delay, step)` books an **absolute fire-turn** and, in most cases,
forgets the unit entirely. `_op_*_payout` handlers that *do* carry an `iid` resolve it with
`_find_unit`, **which scans the whole stack** (`effects.py:263`) — so it finds buried units and pays
them out. Three tiers result:

| tier | cards | behaviour today | correct? |
|---|---|---|---|
| **no `iid` at all** | Chipmunk (`1473`), Black Bear (`1551`), Chinchilla (`1591`) | pays out **even if the unit was destroyed** | no — broken on any reading |
| **`iid` + existence check** | Grizzly Bear (`1556`) | fires **while buried** (it isn't Fragile) | no |
| **`iid` + existence check** | Bird/Snake Egg (`1047`/`1052`), Fig Tree (`1131`), Watering Hole (`1136`) | denied when covered | **right, but only by accident** — these are all Fragile, so covering *removes* them; the guard never had to handle burial |

`_op_fig_tree_payout`'s comment claims the check denies the payoff "if the landmark was covered" —
true only because Fig Tree is Fragile. The same guard on a non-Fragile card does nothing.

**Provenance:** suspected in [`../balance/card-balance-todo.md`](../balance/card-balance-todo.md)
2026-07-12 ("chipmunk works when covered as well?", commit `5749c60`); mechanism found 2026-07-15
while pricing a replacement for Fig Tree. The companion Skunk note in that file ("makes all the
instances unplayable, not just the one that was returned") is a **separate** bug, not covered here.

## Blast radius

**Four live cards** — the Fragile ones (Eggs, Fig Tree, Watering Hole) are unaffected, since
covering already removes them:

| card | deck(s) | change under the ruling |
|---|---|---|
| **Black Bear** | ramp, **the baseline ruler** | draw-2 no longer fires when destroyed; suspends while buried |
| **Grizzly Bear** | ramp, **the baseline ruler** | strike no longer fires from under a stack |
| **Chipmunk** | food_otk | second 10 food no longer fires when destroyed/buried |
| **Chinchilla** | food_otk | bonus action no longer fires when destroyed/buried |

⚠ **Black Bear and Grizzly Bear are in `sim/benchmark_set.py`'s `DECKLIST`** — i.e. *inside the
card-power ruler* the baseline-deck arc is calibrating. Any benchmark run made before this fix
prices the ruler with both cards cheating, and every matchup uses the ruler. See
[`../balance/baseline-deck-arc.md`](../balance/baseline-deck-arc.md).

**Balance note (do not act on it here):** this is a *correctness* fix and it is a **nerf** to all
four cards. Two of them are food_otk's, already the weakest deck (~38%). Fix the rule first, then
re-balance — never bend the ruling to protect a deck's number.

## Engine work implied

The scheduler is built the wrong way round for this: it needs **turns-remaining tracked per unit**,
decremented at the start of the owner's turn *only if that unit is currently the top of its
crossroad* — not an absolute fire-turn booked once. Also:

- give Chipmunk / Black Bear / Chinchilla an `iid` (they have none);
- `_find_unit` is the wrong primitive for this — it answers "does this unit exist anywhere",
  where the question is "is this unit on top". Callers that want the latter need a `top_unit` check
  (or a new helper) rather than existence;
- bounce-to-hand must clear any pending timer for that unit;
- regression tests per tier: destroyed → cancelled; buried → suspended; uncovered → resumes;
  bounced+replayed → fresh timer; Fragile+covered → cancelled (unchanged).

Then re-baseline the ruler (the arc's step 2) before locking it.
