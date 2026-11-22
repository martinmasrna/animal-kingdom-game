# The bot benchmark

Is one bot stronger than another? `bench.sh` plays them against each other and says by how much. The bots, the search and the benchmark are Rust only (`engine_rs/src/bots/`, `engine_rs/src/bin/bot_bench.rs`); nothing here needs Python.

```
tools/bot_bench/bench.sh run --x turn:budget=200000,reply=12,per=2 --y turn:budget=200000 --seeds 40 --name my-run
```

X is the bot under test, Y the one it is measured against. The decks are Martin's five (`martin_decks.json`: Aggro, Control, Midrange, Food Token, Combo Token); every ordered pairing is played, mirrors included, `--seeds` deals each (40 gives 1,000 deals, 2,000 games). Every deal is played twice with the pilots swapped: same decks, same seats, same shuffle. So neither a strong deck nor a lucky draw can favour a bot, and 50% means the two are equal. The number to read is X's share of the games with its 95% interval, a deal's two games counting as one observation.

A bot's budget is a count of positions it may make in a turn, never a clock, and every bot is seeded from the deal. A run with the same arguments on the same commit plays the same games, on any machine, under any load. Milliseconds are reported and never used; read them from a run on a quiet machine.

## What a run leaves

`results/bot_bench/<name>/` (untracked): `run.json` (the commit, a hash of the card table and the map, both bots' specs, the decks, the seeds), `games.jsonl` (one line a game: decks, seed, who piloted which seat, who went first, the winner, how it ended and whether by fatigue, turns, each bot's positions and time, and how it played: cards and unspent mana a turn, turns ended with a play still legal, raids, leader powers; `--log-actions` adds every action), `summary.txt` and `summary.json` (what the run printed).

## Commands

- `run`: the benchmark. `--decks FILE` plays another deck file, `{"decks": [{"name", "leader", "cards": [25 ids]}]}`; `--random-decks N [--deck-seed S]` plays N random legal decks, the second set a result is checked on so it is not a result about five decks. `--seeds N`, `--seed S` (the run's seed), `--threads T` (default: all cores but two), `--out DIR`. `--count-wins` has the referee look, at the start of every turn, for a win that needs no hidden card, and counts the turns that began with one and were not won in: plays wrong beyond argument.
- `show --x SPEC --y SPEC --a Aggro --b Control --seed 3 [--swap]`: one game printed turn by turn, to read how a bot plays; a turn that begins with a certain win says so. `--dump TURN --dump-file FILE` saves the position at the start of that turn.
- `position --file FILE [--bot SPEC]`: a saved position: whether the player to move has a certain win, and the turn the bot plays from it. A position worth keeping goes to `engine_rs/src/bots/positions/` with a test (`bots/tests.rs`, `a_win_in_hand_is_taken`).
- `turns --games 20`: how large a turn is by turn number, with equal positions merged and with nothing merged.
- `winstats --games 300`: what the look for a win costs, by how far the player is from the winning food.
- `evalfit --games 2000`: the evaluation against who won, as a fitted curve (the reply level's `scale` and `tempo`).

## The bots

- `greedy`: the bot the game shipped with, one action at a time. The fixed baseline.
- `turn`: plans its whole turn and scores only finished turns. `turn:budget=20000` sets the positions a turn may make; `worlds=4` the imagined decks a first action is averaged over when the turn can draw; `width=16384` the most unfinished positions a layer keeps; `win=N` the positions a look for a win this turn may make before any search (a sixteenth of the budget unless set, 0 never looks); `w.NAME=V` one weight of the evaluation (`engine_rs/src/bots/eval.rs`); `eval=greedy` scores finished turns with the shipped bot's evaluation instead, which measures the search with the evaluation held fixed.
- `turn` with `reply=K`: the reply level. The K best finished turns are each played out in `hands=3` hands the opponent may hold; the opponent takes a win if they have one and otherwise plays the turn their own search likes best; a turn's score is the mean of the bot's chance of winning from where the reply leaves it. `per=N` keeps at most N of the K turns that play the same cards on other tiles, so the K differ in what they play (0: the K best whatever they play). `own=25` is the share, in hundredths, of a search's positions that plans the bot's own turn; the replies split the rest evenly, and with fewer than 500 positions each the bot asks about fewer turns, then in fewer hands. `scale=15`, `tempo=10` turn the evaluation into a chance of winning; `decisive=D` scores by the mean of the raw evaluation with a decided game at ±D instead; `spread=1` deals the imagined hands spread over the costs of the opponent's unseen cards.

Practice plays `web/match.py` `PRACTICE_BOT`.

Tests: `cd engine_rs && cargo test --release --no-default-features --lib bots` (a bot's choice does not change when the hidden cards are dealt another way, with the reply level too; a world holds exactly the cards the seat can count; the look for a win reads nothing hidden; a win in hand is taken in two positions saved from games; a seeded game replays).

## Where the bots stand (2026-11-22, Martin's five decks, 2,000 games a line unless said; with the fatigue rule)

`v1` is `turn` with no reply level, `v2` is `turn:reply=12,per=2`, each at the budget named.

| X | Y | X wins | 95% interval |
|---|---|---|---|
| v1 20,000 | `greedy` | 71.0% | 69.4 to 72.7 |
| v2 200,000 | `greedy` | 74.2% | 72.7 to 75.8 |
| v2 20,000 | v1 20,000 | 52.1% | 50.9 to 53.4 |
| v2 200,000 | v1 200,000 | 55.0% | 53.8 to 56.3 |
| v2 2,000,000 | v1 2,000,000 (600 games) | 53.8% | 51.5 to 56.1 |
| v2 2,000,000 | v2 200,000 (600 games) | 52.0% | 49.7 to 54.3 |
| v2 200,000 (Practice) | v1 20,000 | 55.8% | 54.4 to 57.1 |
| v1 20,000 | v1 20,000 with `win=0` | 49.6% | 48.7 to 50.5 |

The reply level's settings, each against `turn:budget=200000,reply=6` (six turns whatever they play, three hands):

| X | X wins | 95% interval |
|---|---|---|
| `reply=3` | 49.1% | 47.8 to 50.4 |
| `reply=12` | 50.3% | 49.1 to 51.6 |
| `reply=6,per=1` | 51.0% | 49.7 to 52.4 |
| `reply=12,per=1` | 51.5% | 50.2 to 52.9 |
| `reply=12,per=2` | 51.7% | 50.4 to 53.0 |
| `hands=1` | 48.9% | 47.5 to 50.2 |
| `hands=6` | 49.7% | 48.4 to 51.0 |

And against `turn:budget=200000,reply=12,per=2`: `reply=24` 50.2% (49.0 to 51.4), `spread=1` 49.9% (48.7 to 51.1), `decisive=1000` 49.6% (48.4 to 50.8).

What they say. Planning the whole turn is worth about 20 points over one action at a time. Asking the opponent's reply is worth about 5 more at 200,000 positions a turn and about 2 at 20,000, where a reply gets some 400 positions. More turns asked about buy nothing by themselves; turns that differ in what they play do, a little. One imagined hand is slightly worse than three, six no better. Ten times the positions (2,000,000) may be worth 2 points more and the interval does not exclude none. Scoring the reply by the chance of winning or by the raw evaluation with a decided game at ±1000 plays the same, and so does dealing the imagined hands spread over costs.

The look for a win costs no strength and takes the blunder out: in 2,000 games the bot without it began 8 turns with a certain win it did not take, the bot with it none; over the runs above a bot with it misses 0 to 2 in 2,000 games.

Raids. `w.raid=R` adds R to the value of a food the opponent's den lacks. Against the same bot without it:

| X | X wins | X's raids a game | Aggro in X's hands, in Y's |
|---|---|---|---|
| v1 20,000, `w.raid=0.5` | 49.6% | 0.02 | 34.8%, 35.2% |
| v1 20,000, `w.raid=1` | 49.9% | 0.03 | 35.0%, 34.5% |
| v1 20,000, `w.raid=2` | 48.9% | 0.15 | 33.0%, 36.0% |
| v1 20,000, `w.raid=4` | 47.0% | 0.49 | 23.0%, 37.2% |
| v2 200,000, `w.raid=0.5` | 50.1% | 0.11 | |
| v2 200,000, `w.raid=1` | 49.8% | 0.12 | |
| v2 200,000, `w.raid=2` | 49.0% | 0.28 | |

Only Aggro raids at all (0.72 a game at `w.raid=2`, 2.11 at 4; the other four decks under 0.15), and the more it is made to raid the more it loses. As these bots play, an animal's body on the board is worth more than its strength off the enemy's food.

Speed and time (the Mac, one core): about 900,000 positions a second. v1 at 20,000 uses 2,900 positions and 3.4 ms a turn; v2 at 20,000 uses 7,000 and 8 ms, at 200,000 52,000 and 60 ms (the largest turn 198,707 positions, about a quarter of a second), at 2,000,000 347,000 and 0.4 s (the largest 1,962,989, a little over 2 s). Where v2's time goes at 2,000,000 (a 30-second sample): copying positions 47%, the position key 18%, applying actions 11%, the search's own tables and ranking 10%, the evaluation 7.5%, listing legal actions 3%, dealing hands 2%, the look for a win under 1%.

The games: about 12 turns for both players together, the player who goes first wins about 62%. No game in any run above reached the 400-turn limit. Between two v2 bots 25 to 40 games of 2,000 end by fatigue (an empty deck taking the loser's last food), every one of them Control against Control, and the longest game is 47 turns; against `greedy`, none.
