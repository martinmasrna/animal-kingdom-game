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
  --config animal_kingdom/data/two_action_config.json \
  --map map_b \
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
so a crash cannot admit half a pair; a truncated final write is discarded safely. Change
the durability/progress interval with `--checkpoint-blocks N`. A changed pilot version,
config, map, seed, deck list, or sample size is rejected instead of being mixed into the
existing dataset—use a different `--out` directory for a different experiment.

By default intervals use a deterministic paired-block percentile bootstrap. Use
`--dataset results/pilot_ratings/dataset.jsonl` to refit a saved cohort without replaying
games. Deck terms are a Balance byproduct only; this command does not make balance changes.

Human-game logs were inspected but are not imported automatically: the current
`results/games/*.json` collection is sparse, unpaired human-vs-bot play across selected
matchups. Treating it as a direct anchor would mix experimental designs. Human calibration
remains optional until there is a curated, comparable cohort.
