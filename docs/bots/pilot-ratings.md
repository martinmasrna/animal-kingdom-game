# Anchored pilot ratings

`animal_kingdom.sim.ratings` measures the bot ladder on a fixed Bradley–Terry log-odds
scale. RandomBot is fixed at `0`; RefereeBot is reported as the observed ceiling reference.
The fit separates pilot strength, mean deck strength, pilot×deck interaction (execution
difficulty), and first-player advantage instead of treating a bot/deck pair as one opaque
competitor.

Run the acceptance cohort with:

```bash
.venv/bin/python -m animal_kingdom.sim.ratings \
  --games 200 \
  --jobs 4 \
  --out results/pilot_ratings
```

`--games` is paired seeds per pilot-pair × ordered deck-pair and cannot be below 200 from
the CLI. Every seed is played twice with the complete pilot/deck competitors swapped
between seats. With the default four pilots and seven decks, the command runs 117,600
games; RefereeBot makes this a calibration run, not a quick smoke test.

The output directory contains:

- `dataset.jsonl`: an incremental checkpoint of model-ready paired outcomes and a
  deterministic provenance header (bot source hashes/search budgets, complete config, map,
  seed schedule, and sample size);
- `ratings.json`: all fitted ratings and 95% confidence intervals plus the same provenance.

The simulator flushes and syncs every 100 paired blocks by default. Re-run the exact same
command after an interruption: it validates the saved provenance, skips complete blocks,
and resumes the missing schedule. Each checkpoint record contains both seat assignments,
so a crash cannot admit half a pair; a truncated final write is discarded safely. Paired
blocks are saved in completion order and slow games do not hold up faster workers or
checkpoints. `Ctrl-C` terminates the active worker pool promptly while retaining every
flushed block. Change the durability/progress interval with `--checkpoint-blocks N`. A
changed pilot version, config, map, seed, deck list, or sample size is rejected instead of
being mixed into the existing dataset—use a different `--out` directory for a different
experiment.

By default intervals use a deterministic paired-block percentile bootstrap. Use
`--dataset results/pilot_ratings/dataset.jsonl` to refit a saved cohort without replaying
games. Deck terms are a Balance byproduct only; this command does not make balance changes.

Human-game logs were inspected but are not imported automatically: the current
`results/games/*.json` collection is sparse, unpaired human-vs-bot play across selected
matchups. Treating it as a direct anchor would mix experimental designs. Human calibration
remains optional until there is a curated, comparable cohort.

## Reporting scale — Elo

The fit is canonical on Bradley–Terry log-odds (what `ratings.json` stores under `ratings`
and what the tests pin), but `format_result` and the `elo` block in `ratings.json` render
**Elo by default** (`ELO_SCALE = 400/ln 10 ≈ 173.72` Elo per log-odds unit; RandomBot = 0).
Elo gap → win% of the higher pilot: `+50→57  +100→64  +200→76  +300→85  +400→91`.

## Results — bot ladder (cohort 2026-07-10)

The shipped ladder was fit from a lean cohort (four pilots × seven decks, independent
seat-balanced games — 50 first / 50 second per matchup, **no paired seeds**, both deck
assignments played). Absolute pilot Elo:

| Pilot | Elo | Note |
| --- | --- | --- |
| referee | +1499 | determinized adversarial search (the calibration "oracle") |
| turn | +1401 | M6 middle tier |
| greedy | +1245 | 1-ply baseline |
| random | 0 | anchor |

First-player term is **negative** (~−16 Elo): a slight *second*-player edge under map_b +
2-action.

## Results — human on the ladder (2026-07-10)

294 recorded human-vs-RefereeBot games (7 sessions × 42, one deck per session, full 7×7
matchup range, seat-balanced, matchup-blocked). Fit by holding the bot terms fixed and MLE-ing
a single anchored human pilot term (`scratchpad human_anchor.py`; anchored single-parameter
fit is robust for scarce human data):

| Pilot | Elo | 95% CI |
| --- | --- | --- |
| **human** | **+1572** | [1530, 1613] |
| referee | +1499 | — |
| turn | +1401 | — |
| greedy | +1245 | — |

**A strong human sits ~73 Elo above the oracle (~60% head-to-head)** — CI floor (1530) clears
Referee's 1499, so RefereeBot is *not* human-level. The per-deck anchored *edge-vs-referee*
(isolating piloting from deck/matchup) is largest where the search underweights foresight
(egg_control +203, cats_midrange +165) and collapses to noise where the oracle executes
mechanically (food_otk +44, ramp +35, colony −3, canine −22 — all inside ±~110 Elo bands).
The egg_control result **re-confirms the egg delayed-payoff blind spot**: it is a piloting
artifact, not a weak deck — do not buff egg off bot win rates.
