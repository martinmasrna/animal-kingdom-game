# RefereeBot search-cost tuning — methodology & frontier

_Investigation record for the staged Referee v2 speed-vs-strength work (2026-07-03).
Companion to the RefereeBot performance item in [`backlog.md`](backlog.md). Raw data lives
in `results/referee_nodebudget/` (gitignored)._

## Why this is written down

RefereeBot is the **calibration oracle** — the ceiling anchor for the Bradley–Terry pilot
ratings. Two things therefore matter more than raw speed: (1) a speedup must not change how
the oracle plays, and (2) we must know when the oracle itself diverges from truth. This note
records the method used to establish both, so future tuning doesn't re-derive it (or repeat
the mistakes).

## The three references — and why the anchor choice is load-bearing

Any referee search config can be measured against two different opponents, and they answer
different questions:

- **vs the legacy oracle** (`staged=False`, uncapped): "is this config faithful to exhaustive
  search?" This is the *absolute* strength question.
- **vs the shipped v2** (the current production `referee`): "does this *change* preserve the
  bot we actually ship?" This is the *relative* question a speedup must pass.

They come apart whenever the shipped bot already diverges from the oracle on some deck (it
does — see colony below). Validating a speedup against the oracle then conflates the change
with the pre-existing gap. So a speedup is gated **vs the shipped v2**; oracle faithfulness is
tracked **separately**. The mirror harness supports both via `--candidate-config` /
`--reference-config` (`sim/referee_comparison.py`).

## The cheap screen vs the real gate

- **Cheap screen** — first-action agreement with the legacy oracle over an evaluator-independent
  position corpus (RandomBot trajectories, both maps/configs). Fast, but only checks the *first*
  move; it does **not** see deep-line quality. Necessary, not sufficient.
- **Real gate** — paired-seat mirror games, ≥200/deck, both seats, bootstrap CI. A candidate
  ships only if it **ties or beats every deck** (lower CI ≥ 45%, the 5-point margin). High-
  variance decks need more: `egg_control` took 800 games to settle.

## What the profiling said

Whole-game profiling (not cherry-picked positions) showed the average decision's cost is
dominated by **reply rollouts (~320/decision)** — replaying the opponent's turn across sampled
worlds. The node budget fired on only ~2/15 decisions, but those dominated wall-clock. So the
expensive tail, not the typical decision, is where time goes.

## The frontier (139-position corpus agreement + whole-game CPU)

| config | agreement vs oracle | whole-game speedup vs v2 |
|---|---|---|
| v2 (det5 root5 reply4 nodes1000) | 137/139 | 1.00× |
| **nodes=150** | **137/139 (identical)** | **1.73×** |
| nodes=250 | 137/139 | 1.49× |
| nodes=100 | 136/139 | 1.88× |
| root4 | 136/139 | 1.21× |
| det4 / det3 | 129 / 126 | — (agreement loss) |
| reply3 / reply2 | 133 / 134 | ~1.05× (bad trade) |
| adaptive-root 4→8 | 138–139/139 | **0.76–0.85× (slower!)** |

**Node budget is the lever.** Down to 150 it doesn't change *which* move the bot picks
(identical agreement); below that (100) agreement slips. It works because it truncates only
pathological deep expansion — where greedy completion is nearly as good — instead of degrading
normal decisions.

### Negative results (don't retry without new evidence)
- **Adaptive root width** (the intuitive "narrow when confident, escalate when not"): a speed
  *loser*. It maxes agreement only by escalating to width-8, doing more work than fixed root-5.
  Root-narrowing structurally fights the bot's purpose — the delayed-payoff plays it exists to
  value correctly are exactly the ones a cheap 1-ply screen ranks low (on the disagreement
  positions, the oracle's move ranked 4th/7th/7th in the screen).
- **Fewer determinizations** (5→3): agreement 137→126/139. Too much variance.
- **Narrower reply beam**: hurts agreement for almost no speed.

## Result: `nodes=150` ties the shipped v2 on every deck

Paired mirror, nodes=150 vs shipped v2, 200 games/deck (egg pooled to 800), seed 1600:

| deck | candidate win% vs v2 |
|---|---|
| aggro_hq_rush | 50.0 [47.0, 53.0] |
| canine_buff_tempo | 49.5 [47.0, 52.0] |
| cats_midrange | 50.0 [47.5, 52.5] |
| colony_food_swarm | 49.5 [47.0, 51.5] |
| egg_control | 49.1 [46.4, 52.0] (800g) |
| food_otk | 50.5 [47.5, 53.5] |
| ramp | 50.0 [50.0, 50.0] |

Every lower CI ≥ 46 → **meets the ship gate.** ~1.73× whole-game, ~2.8× cumulative vs the
original referee. **Not shipped**: it changes the oracle's decisions on budget-exhausted lines,
so the one-line `REFEREE_MAX_SEARCH_NODES` flip in `sim/runner.py` is left for owner sign-off.

Reproduced at a fresh seed (2500) and pooled to 400 games: egg 49.5% [45.5, 53.8], colony
50.5% [48.8, 52.2], aggro 49.0% [46.8, 51.2] — all lower CI ≥ 45, so the tie is not a seed
artifact.

Reproduce:
```
python -m animal_kingdom.sim.referee_comparison --mirror-deck all --games 200 \
  --candidate-config nodes=150 --reference-config nodes=1000 --jobs 8 --seed 1600 \
  --out results/referee_nodebudget/gate200_n150_vs_v2
```

## Separate finding: staged v2 under-pilots colony vs the oracle

A 100-game v2-vs-legacy profile across all 7 decks is **near-parity everywhere** (44–51%; every
CI ≈ includes 50), so the shipped v2 is roughly oracle-faithful. `colony_food_swarm` is the
softest — **~40%** (seed-noisy: 37% seed1700 / 44% seed1500; magnitude to firm with a larger
saved run) — a mild gap, not the 13-pt divergence the first sample suggested. It is
**budget-independent** (~37% at nodes 1000/350/150 on the low seed).

**Isolation (same seed, staged candidate vs oracle, 100g):** baseline `root5/reply4` 44% →
`root8/reply4` 45% → `root5/reply8` **50%** → `root8/reply8` **55%**. The **reply beam is the
dominant lever** (widening reply 4→8 alone restores parity; root is secondary): the staged
reply/root pruning is what cuts colony's deep combo/swarm lines. **Tension:** widening the reply
beam raises the dominant cost (reply rollouts), so colony faithfulness trades against referee
speed — a faithfulness-vs-throughput call for the oracle tier. Fix is pilot-side (adaptive
wider beams for combo-shaped positions, or `staged=False` on a small calibration cohort),
**never a card nerf**. Tracked as a task and in `backlog.md`.

## Reliability grade of the speedup claim

**B (credible):** stable across seats/seeds, paired ≥200 games (egg 800), reference config
recorded in provenance. Not A only because the corpus agreement screen and the mirror share
the greedy evaluator, and human calibration is absent.
