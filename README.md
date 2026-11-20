# Animal Kingdom

A two-player card game about animals, played on a board of 19 hex tiles. Each turn you have mana (one more each turn, up to 10) and play cards from your hand onto the board; a card covers an enemy it is stronger than, and what it covers is removed. Regions you hold pay food; an animal that reaches the enemy den through their base destroys their food. 30 food wins, and a player whose food drops to 0 loses.

This repo holds the rules engine, a bot, and the web client. The state of the project is in [`docs/STATUS.md`](docs/STATUS.md).

## Setup

```sh
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
./test
```

## Play

```sh
./play                     # the web client at http://localhost:8000
./play --host 0.0.0.0      # let other machines on the network join
```

A friend match is a link or a six-letter code, and two browser windows work as two players. Practice plays the bot, on a mirror of your deck. Every web game with a person in it is saved to `results/human_games/web/`; `.venv/bin/python -m animal_kingdom.replay FILE` replays one.

## Cards

`./cards` is the card table (http://localhost:8002): every card's values, edited in place. Cards change only through `tools/cards/hq.py`.
