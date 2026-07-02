# Animal Kingdom — Engine

Headless rules engine, bots, and a simulation harness for the *Animal Kingdom*
two-player tactical board game. The end goal is **balance data**: run thousands of
bot-vs-bot games and measure whether the card pool and archetypes are balanced. A
human/web UI is out of scope for now, but the engine is built as a pure,
transport-agnostic library so a UI layer can drop on top later.

Design source of truth lives in [`docs/`](docs/): `overview.md` (rules),
`cards.md` (card pool), `maps.md` (Map A), `todo.md` (open design items). The build
spec is `docs/handoff-engine.md`.

## Status

Built in milestones (each is a review checkpoint):

- **M0 — Data & loading** ✅ — full card pool + Map A as validated JSON, loaders, central config.
- **M1 — Vanilla engine** ✅ — state (mutate + clone, per-seat views, serialization), `legal_actions`/`apply_action`/`is_terminal`, connection/covering/stacks, food, all three win conditions, RandomBot, text renderer, CLI. Decision-point seam in place (effect stack / pending / carried RNG) for M2. No card effects yet.
- **M2 — Effects** ✅ — effect-stack interpreter + static modifiers + dynamic strength; every card implemented and unit-tested.
- **M3 — Greedy bot + metrics** ✅ — `GreedyBot` (board-eval heuristic + 1-ply lookahead) and a sim harness emitting the balance metrics (matchup matrix, win-condition split, first-player win rate, game length, per-card win-rate delta) to CSV/JSON.
- **M4 — Bot-quality gauntlet** ✅ — `sim/gauntlet.py` pits a candidate bot/weights against a pinned opponent pool so heuristic changes are validated on win-rate deltas, not vibes.
- **M5 — Referee bot** ✅ — `RefereeBot` (`--bots referee,...`), determinized adversarial search: samples K possible opponent hands from public info (`bots/determinize.py`), plays the opponent's reply turn with a real `GreedyBot` in each sampled world, and averages the outcome. ~50–100× slower than greedy; used at low volume to calibrate which greedy balance verdicts hold (gauntlet-validated: +5 to +13 points over greedy piloting the same deck).

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
Hard = referee bot — thinks a moment per move);
you play seat A. Passing either flag (or `--quiet`) skips the prompt for scripted runs.

Equivalent without the launcher: `python -m animal_kingdom.cli ...` (venv activated).

`greedy` is also a controller, so you can watch the heuristic bot play:

```sh
./run --bots greedy,random --decks ramp,aggro_hq_rush --quiet
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

## Run a simulation

The sim harness plays N headless games per matchup and writes the balance metrics to a
results directory (CSV + JSON, standard-library only — `pandas` is only needed for your own
downstream analysis):

```sh
python -m animal_kingdom.sim --decks all --games 200 --seed 0 --jobs 4 --out results/
python -m animal_kingdom.sim --decks ramp,egg_control --games 100 --bots greedy,random
```

`--decks all` runs the full deck round-robin; two slugs run a single matchup. Output:
`matchup_matrix.csv` (win rate from seat A's view), `per_card_winrate.csv`, and
`summary.json` (win-condition split, first-player win rate, average game length, and a
caveat that greedy self-play underplays Combo decks). Runs are seed-deterministic, so
`--jobs` only changes speed, not results.

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
