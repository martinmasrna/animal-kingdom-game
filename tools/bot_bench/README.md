# The bot benchmark

Is one bot stronger than another? `bench.sh` plays them against each other and says by how much. The bots, the search and the benchmark are Rust only (`engine_rs/src/bots/`, `engine_rs/src/bin/bot_bench.rs`); nothing here needs Python.

```
tools/bot_bench/bench.sh run --x turn:budget=20000 --y greedy --seeds 20 --name v1-20k
```

X is the bot under test, Y the one it is measured against. The decks are Martin's five (`martin_decks.json`: Aggro, Control, Midrange, Food Token, Combo Token); every ordered pairing is played, mirrors included, `--seeds` deals each (20 gives 500 deals, 1,000 games). Every deal is played twice with the pilots swapped: same decks, same seats, same shuffle. So neither a strong deck nor a lucky draw can favour a bot, and 50% means the two are equal. The number to read is X's share of the games with its 95% interval, a deal's two games counting as one observation.

A bot's budget is a count of positions it may make in a turn, never a clock, and every bot is seeded from the deal. A run with the same arguments on the same commit plays the same games, on any machine, under any load. Milliseconds are reported and never used.

## What a run leaves

`results/bot_bench/<name>/` (untracked): `run.json` (the commit, a hash of the card table and the map, both bots' specs, the decks, the seeds), `games.jsonl` (one line a game: decks, seed, who piloted which seat, who went first, the winner, how it ended, turns, each bot's positions and time, and how it played: cards and unspent mana a turn, turns ended with a play still legal, raids, leader powers; `--log-actions` adds every action), `summary.txt` and `summary.json` (what the run printed).

## Options

- `--decks FILE`: another deck file, `{"decks": [{"name", "leader", "cards": [25 ids]}]}`. `--random-decks N [--deck-seed S]`: N random legal decks instead, the second set a result is checked on so it is not a result about five decks.
- `--seeds N`, `--seed S` (the run's seed), `--threads T` (default: all cores but two), `--out DIR`.
- `bench.sh show --x SPEC --y SPEC --a Aggro --b Control --seed 3 [--swap 1]`: one game printed turn by turn, to read how a bot plays.
- `bench.sh turns --games 20`: how large a turn is by turn number, with equal positions merged and with nothing merged.

## The bots

- `greedy`: the bot the game shipped with, one action at a time. The fixed baseline.
- `turn`: plans its whole turn and scores only finished turns. `turn:budget=20000` sets the positions a turn may make; `worlds=4` the imagined decks a first action is averaged over when the turn can draw; `width=16384` the most unfinished positions a layer keeps; `w.NAME=V` one weight of the evaluation (`engine_rs/src/bots/eval.rs`); `eval=greedy` scores finished turns with the shipped bot's evaluation instead, which measures the search with the evaluation held fixed.

Tests: `cd engine_rs && cargo test --release --no-default-features --lib bots` (a bot's choice does not change when the hidden cards are dealt another way; a world holds exactly the cards the seat can count; a seeded game replays).

## Where the bots stand (2026-11-22, commit of this file's last change, Martin's five decks, 2,000 games a line)

| X | Y | X wins | 95% interval |
|---|---|---|---|
| `turn:budget=2000` | `greedy` | 67.1% | 65.5 to 68.7 |
| `turn:budget=20000` | `greedy` | 70.9% | 69.2 to 72.5 |
| `turn:budget=200000` | `greedy` | 70.2% | 68.6 to 71.8 |
| `turn:budget=20000` | `turn:budget=2000` | 54.7% | 53.6 to 55.8 |
| `turn:budget=200000` | `turn:budget=20000` | 50.3% | 49.4 to 51.3 |
| `turn:budget=20000` | `turn:budget=20000,eval=greedy` | 53.6% | 52.2 to 55.1 |
| `turn:budget=20000,eval=greedy` | `greedy` | 69.1% | 67.5 to 70.7 |
| `turn:budget=20000` | `turn:budget=20000,worlds=1` | 50.6% | 49.6 to 51.6 |
| `turn:budget=20000` on 8 random decks (2,048 games) | `greedy` | 70.1% | 68.5 to 71.7 |

What they say: planning the whole turn is worth about 20 points over one action at a time, and almost all of it comes from the search, not from the evaluation (the search on the greedy bot's own evaluation is at 69.1%). Past 20,000 positions a turn more search buys nothing. Averaging a first action over four imagined decks instead of one buys nothing measurable.

The turn bot makes about 900,000 positions a second on one core: 3,250 positions and 3.6 ms a turn at a budget of 20,000. A turn's first search stops short of every whole turn in 51% of turns at 2,000, 28% at 20,000 and 13% at 200,000. The games are short, 12 turns for both players together; 99.7% end at 30 food, and the player who goes first wins 61% of them.
