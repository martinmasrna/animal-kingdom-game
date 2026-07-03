# CLAUDE.md

Headless rules engine + bots + simulation harness for *Animal Kingdom* (a 2-player tactical
board game). Goal: **trustworthy balance data** from bot-vs-bot sims. Pure, stdlib,
transport-agnostic library; no UI.

**Start every session at [`docs/STATUS.md`](docs/STATUS.md)** — the project map (8 areas, current
state, next moves). Open items per area live in `docs/<area>/backlog.md`. Rules are
source-of-truth in `docs/rules/` (`overview.md`, `keywords.md`).

## Commands

Python ≥3.11; venv at `.venv` (`python3 -m venv .venv && .venv/bin/pip install -e '.[dev,cli]'`).

- **Tests:** `.venv/bin/python -m pytest animal_kingdom/tests/ -q`
- **Play a game:** `./run` (launcher, finds the venv). `./run --help` for flags.
- **Balance report:** `./report 500` (500 games/matchup; `--deck aggro` to scope one deck).
- **Matchup matrix / sim:** `.venv/bin/python -m animal_kingdom.sim --decks all --games 200 --seed 0 --jobs 4 --out results/`
- **Paired bot-quality benchmark:** `.venv/bin/python -m animal_kingdom.sim.bot_comparison --games 200 --out results/bot_quality/turnbot`

The ruleset is **map_b + 2 actions/turn** (draw 1 per Draw action) — the shipped default everywhere,
no flags needed.

## Invariants — do not violate

- **Balance constants live in `engine/config.py` as placeholders** — tune there, never hard-code
  numbers in effect logic.
- **Production bot policies must be generalist** — no deck slugs / archetype names / card IDs in bot
  code; deck knowledge emerges from generic state features.
- **Bots never read hidden info** (opponent hand / deck order). Honesty is regression-tested — don't
  add a peek.
- **Never nerf a card to fix a bot.** Triage every sim finding: real card signal → Balance;
  bot blind-spot / execution bug → Bots (see the boundary rules in `STATUS.md`).
- **Validate balance/bot claims at ≥200 games/matchup**, paired seeds, both seats. 40-game runs mislead.
- **Keep `engine/` pure** — stdlib-only, transport-agnostic, no I/O.

## Gotchas

- GreedyBot is 1-ply and **underplays combo / delayed-effect decks** (`GREEDY_CAVEAT`) — its win
  rates are a signal to investigate, not truth. TurnBot / RefereeBot are the stronger pilots.

## Workflow

- Run the test suite before committing non-trivial changes.
- Git is the agent's to manage — commit proactively at natural stopping points, straight to `main`
  (solo project); push at sensible checkpoints. No need to ask.
