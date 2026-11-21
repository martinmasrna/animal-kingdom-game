# The bot benchmark

Is one bot stronger than another? `bench.sh` plays them against each other and says by how much. The bots, the search and the benchmark are Rust only (`engine_rs/src/bots/`, `engine_rs/src/bin/bot_bench.rs`); nothing here needs Python.

```
tools/bot_bench/bench.sh run --x turn:budget=20000 --y greedy --seeds 20 --name v1-20k
```

X is the bot under test, Y the one it is measured against. The decks are Martin's five (`martin_decks.json`: Aggro, Control, Midrange, Food Token, Combo Token); every ordered pairing is played, mirrors included, `--seeds` deals each (20 gives 500 deals, 1,000 games). Every deal is played twice with the pilots swapped: same decks, same seats, same shuffle. So neither a strong deck nor a lucky draw can favour a bot, and 50% means the two are equal. The number to read is X's share of the games with its 95% interval, a deal's two games counting as one observation.

A bot's budget is a count of positions it may make in a turn, never a clock, and every bot is seeded from the deal. A run with the same arguments on the same commit plays the same games, on any machine, under any load. Milliseconds are reported and never used.

## What a run leaves

`results/bot_bench/<name>/` (untracked): `run.json` (the commit, a hash of the card table and the map, both bots' specs, the decks, the seeds), `games.jsonl` (one line a game: decks, seed, who piloted which seat, who went first, the winner, how it ended, turns, each bot's positions and time; `--log-actions` adds every action), `summary.txt` and `summary.json` (what the run printed).

## Options

- `--decks FILE`: another deck file, `{"decks": [{"name", "leader", "cards": [25 ids]}]}`. `--random-decks N [--deck-seed S]`: N random legal decks instead, the second set a result is checked on so it is not a result about five decks.
- `--seeds N`, `--seed S` (the run's seed), `--threads T` (default: all cores but two), `--out DIR`.
- `bench.sh show --x SPEC --y SPEC --a Aggro --b Control --seed 3 [--swap 1]`: one game printed turn by turn, to read how a bot plays.
- `bench.sh turns --games 20`: how large a turn is by turn number, with equal positions merged and with nothing merged.

## The bots

- `greedy`: the bot the game shipped with, one action at a time. The fixed baseline.
- `turn`: plans its whole turn and scores only finished turns. `turn:budget=20000` sets the positions a turn may make; `worlds=4` the imagined decks a first action is averaged over when the turn can draw; `width=16384` the most unfinished positions a layer keeps; `w.NAME=V` one weight of the evaluation (`engine_rs/src/bots/eval.rs`).

Tests: `cd engine_rs && cargo test --release --no-default-features --lib bots` (a bot's choice does not change when the hidden cards are dealt another way; a world holds exactly the cards the seat can count; a seeded game replays).
