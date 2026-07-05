# Animal Kingdom — Engine

Headless rules engine, bots, and a simulation harness for the *Animal Kingdom*
two-player tactical board game. The end goal is **balance data**: run thousands of
bot-vs-bot games and measure whether the card pool and archetypes are balanced. A
human/web UI is out of scope for now, but the engine is built as a pure,
transport-agnostic library so a UI layer can drop on top later.

Design source of truth lives in [`docs/`](docs/) — start at [`docs/STATUS.md`](docs/STATUS.md),
the project dashboard. Rules are in `docs/rules/` (`overview.md`, `keywords.md`, `maps.md`), the
card pool in `docs/cards/` (incl. `decks/`). Each area has a `backlog.md` of open items.

## Status

Built in milestones (each is a review checkpoint):

- **M0 — Data & loading** ✅ — full card pool + Map A as validated JSON, loaders, central config.
- **M1 — Vanilla engine** ✅ — state (mutate + clone, per-seat views, serialization), `legal_actions`/`apply_action`/`is_terminal`, connection/covering/stacks, food, all three win conditions, RandomBot, text renderer, CLI. Decision-point seam in place (effect stack / pending / carried RNG) for M2. No card effects yet.
- **M2 — Effects** ✅ — effect-stack interpreter + static modifiers + dynamic strength; every card implemented and unit-tested.
- **M3 — Greedy bot + metrics** ✅ — `GreedyBot` (board-eval heuristic + 1-ply lookahead) and a sim harness emitting the balance metrics (matchup matrix, win-condition split, first-player win rate, game length, per-card win-rate delta) to CSV/JSON.
- **M4 — Bot-quality gauntlet** ✅ — `sim/gauntlet.py` pits a candidate bot/weights against a pinned opponent pool so heuristic changes are validated on win-rate deltas, not vibes.
- **M5 — Referee bot** ✅ — `RefereeBot` (`--bots referee,...`), determinized adversarial search: samples K possible opponent hands from public info (`bots/determinize.py`), plays the opponent's reply turn with a real `GreedyBot` in each sampled world, and averages the outcome. ~50–100× slower than greedy; used at low volume to calibrate which greedy balance verdicts hold (gauntlet-validated: +5 to +13 points over greedy piloting the same deck).
- **M6 — Turn bot** — `TurnBot` (`--bots turn,...`), the scalable middle tier: shares the referee's determinized information-set search (`bots/turn_search.py`) but plans only the *complete current turn* and stops at the turn boundary (no opponent-reply rollout), so it sequences draw→play / ordered Battlecries / effect-granted placements the two-action rules need at a small multiple of greedy's cost. Paired seven-deck benchmark: `python -m animal_kingdom.sim.bot_comparison`.

## Setup

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,cli]"    # add ,analysis once the sim harness lands: ".[dev,cli,analysis]"
```

## Run the tests

```sh
python -m pytest
```

## Play a game in the terminal

The `./run` launcher finds the venv for you and forwards all flags to the CLI:

```sh
./run                              # interactive setup: pick your deck, opponent's deck, opponent level
./run --bots random,random --seed 1   # watch a bot game step by step
./run --bots human,random --decks aggro_hq_rush,ramp --seed 7   # skip setup, configure via flags
./run --quiet                      # final board + result only (bot vs bot, defaults)
./run --help                       # all flags
```

With no `--bots`/`--decks` flags, `./run` walks you through setup at launch — your deck,
the opponent's deck, then the opponent's level (Easy = random bot, Normal = greedy bot,
Hard = turn bot, Expert = referee bot — the last two think a moment per move);
you play seat A. Passing either flag (or `--quiet`) skips the prompt for scripted runs.

Equivalent without the launcher: `python -m animal_kingdom.cli ...` (venv activated).

## Record human benchmark games

Install the TUI extra, then launch the persistent recorder:

```sh
pip install -e ".[dev,tui]"
./record
```

The board, hand, status, and recent actions stay on screen. Click a card and then a
highlighted target; `D` draws, number keys select cards, arrows move between targets, and
Enter confirms. Every human and bot decision is saved immediately under
`results/human_games/`, including the player-visible state, legal alternatives, chosen
action, exact engine state, timing, provenance, and final result. `M` excludes the latest
human decision and `G` excludes the whole game without deleting raw data.

For a reproducible cohort, generate an explicit schedule and record its next incomplete
game:

```sh
python -m animal_kingdom.recording.schedule \
  --id human-v1 --out human-v1.json \
  --human-decks all --opponent-decks all \
  --bots greedy,turn --repetitions 1 --seats both

./record --schedule human-v1.json --player-id human-1
```

Completed valid games are skipped automatically. Interrupted or excluded scheduled games
remain in the queue.

`greedy` and `turn` are also controllers, so you can watch the heuristic bots play:

```sh
./run --bots greedy,random --decks ramp,aggro_hq_rush --quiet
./run --bots turn,greedy --decks colony_food_swarm,cats_midrange --quiet  # complete-own-turn planner
```

### Sharing a game with an agent

At game end (unless `--quiet`), `./run` offers to save an agent-friendly JSON log —
one entry per turn with the actions taken, a compact board snapshot, food/hand/deck
counts, and the remove pile — far cheaper to hand to an LLM than pasting the terminal
transcript. Point an agent at the saved file, or use `--log <path>` (`-` for stdout)
to save non-interactively:

```sh
./run --bots greedy,greedy --seed 7 --quiet --log results/games/greedy_vs_greedy.json
```

## Run a balance simulation or report

`./report` is the unified balance CLI. It plays N headless games per matchup and prints a
human-readable matchup/per-card report by default:

```sh
./report 200 --seed 0 --jobs 4
./report 100 --deck ramp --opponent egg --bots greedy,random
./report 200 --format files --out results/baseline
./report 200 --format both --out results/baseline
```

Use `--deck` to focus one deck and `--opponent` to narrow it to one opponent. `--format
files` writes `matchup_matrix.csv`, `per_card_stats.csv`, and `summary.json`; `--format
both` writes those artifacts and prints the report from the same run. Runs are
seed-deterministic, so `--jobs` only changes speed, not results.

The older `python -m animal_kingdom.sim --decks all --games ...` form remains a
compatibility alias for `./report ... --format files`; it no longer has a separate
implementation.

## Layout

```
animal_kingdom/
  engine/   # pure, stdlib-only rules engine (config, cards, maps, ...)
  data/     # cards.json, maps.json (static data)
  bots/     # bot implementations (random, greedy)
  sim/      # simulation runner + metrics (may use pandas)
  render/   # ASCII renderer
  tests/    # pytest suite
```
