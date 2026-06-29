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
- **M2 — Effects** — _planned_ (effect-stack interpreter + static modifiers + dynamic strength; every card implemented).
- **M3 — Greedy bot + metrics** — _planned_ (heuristic bot + sim harness emitting balance metrics).

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
