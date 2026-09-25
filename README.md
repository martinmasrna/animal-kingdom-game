# Animal Kingdom

A two-player tactical deckbuilding game about animals. Players place units onto a graph of crossroads; you win by capturing the enemy headquarters or by controlling enough regions to reach the food threshold. There is no mana and no combat: a unit is one number, strength, and every turn is two actions.

This repo holds the rules engine, bots from random to search-based, the simulation tools used to design and balance the game, a web client and a terminal interface. The rules are in [`docs/rules/`](docs/rules/), the state of the project in [`docs/STATUS.md`](docs/STATUS.md).

## Setup

```sh
python3 -m venv .venv
.venv/bin/pip install -e '.[dev,cli]'
.venv/bin/python -m pytest -q
```

## Play

```sh
./play                                            # the web client at http://localhost:8000 (needs '.[web]'; installs it if missing)
./play --host 0.0.0.0                             # let other machines on the network join
./run                                             # pick your deck, the opponent's deck and difficulty
./run --bots human,turn --decks cats_midrange,ramp
./run --bots greedy,referee --quiet               # watch two bots
./record                                          # the Textual UI; records every decision (needs '.[tui]')
```

In the web client, Easy is the greedy bot, Normal turn and Expert referee; a friend match is a link or a six-letter code, and two browser tabs work as two players. Every web game with a human seat is saved to `results/human_games/web/`, replayable with `sim.replay`. In the terminal, Easy is random, Normal greedy, Hard turn, Expert referee.

## Simulate

```sh
./report 200                                  # every deck against every deck, 200 games per matchup
./report 200 --deck aggro --opponent cats     # one matchup, both seats
./report 200 --format files --out results/x   # matchup matrix, per-card stats and summary as CSV/JSON
```

Games are seed-deterministic, so `--jobs` changes only speed. How to read the numbers, and how far to trust them, is in [`docs/balance.md`](docs/balance.md) and [`docs/bots.md`](docs/bots.md).

## Layout

```
animal_kingdom/
  engine/     rules: state, actions, effects, strength, maps, config (stdlib only)
  data/       cards.json, maps.json, learned bot weights
  bots/       random, greedy, turn and referee bots; features and the learned evaluator
  learn/      self-play training for the learned evaluator
  sim/        runners, reports, A/B benchmarks, deckbuilding and metagame search
  render/     text rendering and the deck-doc generator
  recording/  human-game recording and cohort schedules
  tui/        the Textual game UI
  web/        the web client: aiohttp server, match model, static JS client
  cli.py      the terminal game
```
