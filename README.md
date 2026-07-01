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

## Setup

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"        # add ,analysis once the sim harness lands: ".[dev,analysis]"
```

## Run the tests

```sh
python -m pytest
```

## Play a game in the terminal

The `./run` launcher finds the venv for you and forwards all flags to the CLI:

```sh
./run                              # bot vs bot, seed 0
./run --bots random,random --seed 1   # watch a game step by step
./run --bots human,random --seed 7    # hotseat vs a bot
./run --quiet                      # final board + result only
./run --help                       # all flags
```

Equivalent without the launcher: `python -m animal_kingdom.cli ...` (venv activated).

`greedy` is also a controller, so you can watch the heuristic bot play:

```sh
./run --bots greedy,random --decks ramp,aggro_hq_rush --quiet
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
