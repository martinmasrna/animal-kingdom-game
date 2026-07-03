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

A 100-game v2-vs-legacy profile across all 7 decks is near-parity (44–51%; CIs include 50) —
except `colony_food_swarm`, which at **500 games is 43.4% [39.8%, 46.8%]**, a *real* ~7-pt
regression (CI excludes 50). So the shipped v2 is oracle-faithful on the field but genuinely
under-pilots colony — milder than the alarming 37% first sample, but not noise. The other 6
decks weren't measured at 500g power, so small gaps aren't excluded for them; colony is the
confirmed outlier. It is **budget-independent** (~37–44% at nodes 1000/350/150).

**Isolation (same seed, staged candidate vs oracle, 100g):** baseline `root5/reply4` 44% →
`root8/reply4` 45% → `root5/reply8` **50%** → `root8/reply8` **55%**. The **reply beam is the
dominant lever** (widening reply 4→8 alone restores parity; root is secondary): the staged
reply/root pruning is what cuts colony's deep combo/swarm lines. **Tension:** widening the reply
beam raises the dominant cost (reply rollouts), so colony faithfulness trades against referee
speed — a faithfulness-vs-throughput call for the oracle tier. Fix is pilot-side (adaptive
wider beams for combo-shaped positions, or `staged=False` on a small calibration cohort),
**never a card nerf**. Tracked as a task and in `backlog.md`.

## The reply beam recovers strength cheaply — `reply=8` dominates `reply=4`

Widening the reply beam turns out to help the whole field, not just colony. `reply=8`-vs-v2
(200 games/deck): **beats v2 on every deck** — colony 57.5% [53, 62.5], aggro 57.0%, cats 59.0%
(all significant), plus ramp 54%, food_otk 52.5%, egg 51.5%, canine 51.5% (non-inferior). So the
shipped `reply_width=4` was globally under-powered; colony was just where it hurt most.

Crucially the node budget *pays for* the reply widening. Whole-game CPU (ref-vs-random, map_b):

| config | CPU-s/game | vs v2 |
|---|---|---|
| v2 (nodes1000, reply4) | 5.30 | 1.00× |
| nodes=150 | 3.19 | 1.66× faster |
| reply=8 | 5.82 | 0.91× (slower) |
| **nodes=150 + reply=8** | **4.05** | **1.31× faster** |

So `nodes=150+reply=8` is **1.31× faster than v2** while being **stronger on the field** — a
near-strict improvement (faster *and* more oracle-faithful), far better than `nodes=150` alone
merely preserving v2's flawed strength. Direct validation (`nodes=150,reply=8` vs v2, 200g/deck; egg pooled to 600g) **beats or ties v2
on all 7 decks**: cats 58.0% [53, 63], colony 57.5% [53, 62.5] (both significant), aggro 53.0%,
food_otk 53.5%, ramp 54.0%, canine 51.0%, egg 51.2% [47.8, 54.7]. Every lower CI ≥ 45.5.

**Recommendation (owner sign-off):** upgrade from "flip `REFEREE_MAX_SEARCH_NODES` 1000→150" to
flipping that **and** `REFEREE_REPLY_WIDTH` 4→8 in `sim/runner.py` — one config that is **~1.31×
faster than v2 and a strictly better (more oracle-faithful) pilot on every deck**, fixing
colony's ~7-pt gap as part of a general strength gain. (Trade-off vs `nodes=150` alone: that is
faster still — ~2.8× cumulative vs original — but merely *ties* v2's flawed strength;
`nodes=150+reply=8` is ~2.1× cumulative and *improves* the oracle. For the calibration tier,
faithfulness wins.) A flat `reply=8` is viable since the combo already nets faster; *adaptive*
reply-widening (reply=8 only for combo-shaped positions via generic features) stays a fallback if
cost ever dictates.

## Reliability grade of the speedup claim

**B (credible):** stable across seats/seeds, paired ≥200 games (egg 800), reference config
recorded in provenance. Not A only because the corpus agreement screen and the mirror share
the greedy evaluator, and human calibration is absent.
