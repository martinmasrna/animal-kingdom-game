---
name: balance-eval
description: >-
  Evaluate whether a balance or bot change actually helped, and whether a deck/card is balanced,
  using this repo's bot-vs-bot simulation methodology. Use when running or interpreting the
  balance report, matchup matrix, or paired bot benchmark; when asked "did this change help?",
  "is this deck/card balanced?", or "is this bot better?"; or before recording any balance/bot
  conclusion. Enforces paired-seed, both-seat, >=200-games sampling and the card-vs-bot triage.
---

# Balance-change evaluation

The core purpose of this repo is **trustworthy balance data**. A conclusion is only as good as the
methodology and the pilot behind it. This skill is the procedure that keeps a result from being a
noisy or mis-attributed mislead. Deeper framework: `docs/balance/simulation-platform-roadmap.md`
(release gates, reliability grades). Boundary rules: `docs/STATUS.md`.

## When this applies
- "I changed a number / heuristic / weights — did it help?" → run the procedure below.
- "Is this deck/card balanced?" → measure against the targets (deck winrate **40–60%**, card impact **±10%**).
- Open-ended balance digs are a mix: start with the procedure to get a trustworthy baseline number, then branch into investigation from there.
- **Not** for command lookups (those are in `CLAUDE.md`).

## Procedure (don't skip steps)
1. **Frame it.** State the exact question and the metric that answers it (a deck's winrate, a card's `impact`, or a single matchup delta).
2. **Snapshot the baseline** — the current numbers / pre-change state you're comparing against.
3. **Run paired.** Same seed schedule before vs after, **both seat assignments**, **≥200 games/matchup**. Deterministic, so `--jobs` only changes speed. Commands under *Quick reference*.
4. **Read deltas with confidence intervals.** A delta inside its CI is noise — don't report it. 40-game runs have burned this project; ≥200 is the house rule.
5. **Interpret against targets + caveats.** Deck 40–60%, card ±10%. Apply the caveats below before believing a number.
6. **Triage the finding — the load-bearing step:**
   - Is it a **real card-balance signal**, or a **bot artifact** (a pilot too weak/blind to execute)?
   - Decision aids: does a *stronger* pilot (`turn`/`referee`) change it? Does it replicate across pilots? Does human playtest agree?
   - Real card signal → **Balance** backlog + tune the number (in `engine/config.py`). Bot blind-spot / execution gap → **Bots** backlog. **Never nerf a card to fix a bot.**
7. **Record with provenance.** Conclusion + bot versions, config, map, seed schedule, sample size, and CI. Update the relevant `docs/<area>/backlog.md` (and `docs/STATUS.md` if a priority moves).

## Bot-change branch
If the change is to a **bot** (heuristic / weights / search), additionally:
- Freeze the specific misplayed line as a reproducible puzzle in `animal_kingdom/tests/test_bot_puzzles.py` *before* fixing it.
- Confirm invariants: **no hidden-info reads**, **no deck slugs / card IDs** in the policy (both regression-tested — see `CLAUDE.md`).
- Validate old-vs-new via the **paired benchmark** (`sim/bot_comparison.py`): the change must **improve or tie every deck**, not just lift the aggregate.

## Caveats / release gates (believe a number only after these)
- **GreedyBot is 1-ply and underplays combo/delayed decks** (`GREEDY_CAVEAT`) — its winrates are a signal to investigate, not truth. Confirm suspect verdicts with `turn`/`referee`.
- **`per_card_stats` `impact` is confounded by game length** (open bug — `docs/engine/backlog.md`). Don't act on a single card's `impact` yet.
- **Pilot sensitivity is itself a result.** If a matchup swings a lot across pilots, that *lowers* reliability — report the spread, don't average it away.
- **Sample size:** ≥200 games/matchup, paired seeds, both seats.

## Quick reference (commands)
Ruleset is the shipped default everywhere (map_b + 2 actions/turn) — no ruleset flags needed.
- Matchup matrix + per-card table: `./report 200 [--deck aggro --opponent cat]`
- Paired bot/deck benchmark: `.venv/bin/python -m animal_kingdom.sim.bot_comparison --games 200 --out results/bot_quality/<name>`
- Single matchup, both seats: `.venv/bin/python -m animal_kingdom.sim --decks A,B --games 200 --seed 0 --jobs 4 --out results/`
