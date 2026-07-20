# Negative result — rung-1 learned evaluator is a regression (do not promote)

**Date:** 2026-07-20 (Session-1 follow-up). **Verdict:** rung-1 (`rung1_v1`, 300k games, 24
features) is **strictly worse** than the promoted rung-0 v2 (`9f2606a`). Keep rung-0 as the pilot;
`data/learned/rung1.json` is a documented dead artifact, not a candidate.

## What was tried

Rung 1 adds 13 "dynamics" features on top of the 11 rung-0 terms (see `bots/features.py`
`RUNG1_EXTRA_FEATURES`) — growth, scheduled-payoff split, economy, board geometry — so TD could
price multi-turn plans without a hand-written horizon discount. Trained with the same recipe as
rung-0 v2: TD(λ), λ=0.8, α 0.01→0.001 linear decay over 600 iters, ε=0.05, grad-clip 5, 500-game
batches, 20% anchor fraction, map_b. Checkpoint `results/learn/rung1_v1/` (gitignored). Training
converged cleanly (logloss 1.68→0.55); this is **not** undertraining.

## The result (paired, 200 games/opp, both seats, `bot_comparison`)

rung-1 vs **rung-0 v2** (the currently promoted weights) — the decisive head-to-head:

| deck | Δ win rate | CI95 | note |
|---|---|---|---|
| food_otk | **−0.203** | [−0.226, −0.180] | catastrophic |
| ramp | −0.065 | [−0.085, −0.044] | worse |
| egg_control | −0.045 | [−0.067, −0.024] | worse |
| colony_food_swarm | −0.036 | [−0.060, −0.012] | worse |
| aggro_hq_rush | −0.017 | [−0.042, +0.007] | ~flat |
| canine_buff_tempo | +0.064 | [+0.043, +0.085] | better |
| cats_midrange | +0.051 | [+0.033, +0.069] | better |

rung-1 loses on 5 of 7 decks. The gate-3 run (rung-1 beats the hand-eval greedy on 4/7) is
**misleading**: rung-0 also beats hand-eval, and rung-0 wins the head-to-head above. rung-1 is a
regression, full stop.

## Why it failed — feature collinearity + no regularization, not a bug

The trainer fits a linear model on **raw, unstandardized features with no L2** (only grad-clip and
α-decay — see `learn/td.py`). So a term's real influence ≈ weight × its typical value range, and
adding a feature that is collinear with an existing one lets the fit reallocate weight between the
two freely. Several rung-1 features are near-duplicates of rung-0 terms:

- `sched_near_diff` / `sched_far_diff` iterate the **same** `state.scheduled` list as
  `pending_payoff` — just undiscounted.
- `hq_dist_diff` is a smooth `1/(1+d)` version of the same HQ-front geometry as `enemy_hq_threat`
  / `own_hq_threat`.
- `income_diff` (fully-controlled region food) is the top end of `region_control`.

Shared-feature weights, rung-0 v2 (good) vs rung-1 (regression):

| feature | rung-0 | rung-1 | |
|---|---|---|---|
| pending_payoff | **+0.881** | **+0.143** | signal gutted |
| own_hq_threat | +0.289 | **+1.084** | ~4× |
| enemy_hq_threat | +0.608 | +0.810 | up |
| coverage_exposure | +0.578 | +1.055 | up |
| food_progress | +0.036 | −0.018 | flipped |
| food_proximity | −0.613 | −0.987 | more negative |

The two largest rung-1 weights are both new: `hq_dist_diff` +2.09 (the dominant term) and
`deck_diff` +2.40 (but /30-normalized, so its actual contribution is modest).

Three mechanisms, each mapped to a losing deck:

1. **Scheduled-payoff signal split three ways and diluted.** rung-0's single largest weight (0.88
   on `pending_payoff`) got spread across `pending_payoff` + `sched_near` + `sched_far`
   (0.14 + 0.23 − 0.03). Net "hatches/bears are coming" value collapsed → **egg_control worse**.
2. **HQ-geometry over-amplified.** New `hq_dist_diff` (dominant) stacked on a 4×-inflated
   `own_hq_threat` turned the eval into a board-rush pilot. This is *why* the tempo/midrange decks
   improved (canine +6.4, cats +5.1) — and why decks that don't win by HQ geometry got dragged off
   plan.
3. **Food de-prioritized harder than rung-0** (`food_progress` flipped negative, `food_proximity`
   −0.61→−0.99) → **food_otk −20 pts**, the one deck whose entire plan is food.

**Root cause in one line:** with no regularization on raw features, the unregularized linear fit
reallocated weight to whichever collinear feature best fit self-play's *majority* strategy (board
pressure), at the expense of minority strategies (scheduled combos, food OTK, ramp). That is
exactly the strategy-class blind spot the learned pilot was supposed to remove — reintroduced by a
feature set that lets the dominant dynamic crowd out the rest.

## Salvage levers (if rung-1 is revisited)

Not fixable by training longer — the fit converged. Real options:

- **Cut/merge the redundant features** (`sched_near/far`, `hq_dist_diff`, `income_diff`) so collinear
  terms stop competing for the same weight.
- **Add L2 + feature standardization** so a single collinear variant can't grab an outsized weight.
- **Debias the self-play opponent distribution** so food/ramp/scheduled lines aren't a minority the
  eval learns to ignore.

Until one of those is tried, rung-0 v2 remains the pilot.
