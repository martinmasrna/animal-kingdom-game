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

- `run`: the benchmark. `--decks FILE` plays another deck file, `{"decks": [{"name", "leader", "cards": [25 ids]}]}`; `--random-decks N [--deck-seed S]` plays N random legal decks, the second set a result is checked on so it is not a result about five decks. `--seeds N`, `--seed S` (the run's seed), `--threads T` (default: all cores but two), `--out DIR`. A run's summary also counts, for each bot, how often one enemy action removed three or more of its animals, how often the enemy gained 10 or more food in one turn, and the share of its own turns from its fourth that ended with no region held. `--count-wins` has the referee look, at the start of every turn, for a win that needs no hidden card, and counts the turns that began with one and were not won in: plays wrong beyond argument.
- `show --x SPEC --y SPEC --a Aggro --b Control --seed 3 [--swap]`: one game printed turn by turn, to read how a bot plays; a turn that begins with a certain win says so. `--dump TURN --dump-file FILE` saves the position at the start of that turn.
- `position --file FILE [--bot SPEC]`: a saved position: whether the player to move has a certain win, and the turn the bot plays from it. A position worth keeping goes to `engine_rs/src/bots/positions/` with a test (`bots/tests.rs`, `a_win_in_hand_is_taken`).
- `turns --games 20`: how large a turn is by turn number, with equal positions merged and with nothing merged.
- `winstats --games 300`: what the look for a win costs, by how far the player is from the winning food.
- `evalfit --games 2000`: the evaluation against who won, as a fitted curve (the reply level's `scale` and `tempo`).
- `fit [--games 24000] [--seed S] [--write]`: the race evaluation's weights fitted to who won; `--write` saves them to `engine_rs/src/bots/race_weights.json`, which the next build compiles in. See "Refitting the race evaluation" below.

## The bots

- `greedy`: the bot the game shipped with, one action at a time. The fixed baseline.
- `turn`: plans its whole turn and scores only finished turns. `turn:budget=20000` sets the positions a turn may make; `worlds=4` the imagined decks a first action is averaged over when the turn can draw; `width=16384` the most unfinished positions a layer keeps; `win=N` the positions a look for a win this turn may make before any search (a sixteenth of the budget unless set, 0 never looks); `w.NAME=V` one weight of the evaluation (`engine_rs/src/bots/eval.rs`); `eval=greedy` scores finished turns with the shipped bot's evaluation instead, which measures the search with the evaluation held fixed; `eval=race` with the race evaluation (`engine_rs/src/bots/race.rs`), its weights from `race_weights.json` and `r.NAME=V` setting one; `mull=T` sends back, one at a time, the opening card that costs most while it costs more than T (0: keeps every hand).
- `turn` with `reply=K`: the reply level. The K best finished turns are each played out in `hands=3` hands the opponent may hold; the opponent takes a win if they have one and otherwise plays the turn their own search likes best; a turn's score is the mean of the bot's chance of winning from where the reply leaves it. `per=N` keeps at most N of the K turns that play the same cards on other tiles, so the K differ in what they play (0: the K best whatever they play). `own=25` is the share, in hundredths, of a search's positions that plans the bot's own turn; the replies split the rest evenly, and with fewer than 500 positions each the bot asks about fewer turns, then in fewer hands. `scale=15`, `tempo=10` turn the evaluation into a chance of winning; `decisive=D` scores by the mean of the raw evaluation with a decided game at ±D instead; `spread=1` deals the imagined hands spread over the costs of the opponent's unseen cards. A run prints where the turn the reply level chose stood in the bot's own search's order.

Practice plays `web/match.py` `PRACTICE_BOT`: `turn:budget=200000,reply=12,per=2,eval=race,mull=2`.

## The race evaluation

The position as a race to the winning food: 31 numbers read from the side that has just moved against the side about to move (`race.rs` `features!` names and explains each), all from quantities the rules compute: food and the regions' pay, the pay a side's next card could move on its best tiles (the chance its hand, or a hand dealt from the opponent's unseen cards, holds a card it can pay for that is strong enough or flies), animals that card could cover, raids and the chance a raid empties the den, how near each side's pay brings it to the winning food, animals, strength, cards in hand, tiles cut off from their base. Each number has a sign it must have by its meaning (`SIGNS`); the score is their weighted sum in food, and a decided game stays at the old evaluation's ±1000.

Its weights are fitted to who won (Texel's tuning): 24,000 games of `turn:budget=20000,mull=2` against itself on Martin's five decks and 20 random ones, a tenth of the turns played at random, every finished turn read from both seats and labelled with the winner, a logistic regression held lightly to the hand-set weights, every fifth game held out. The games are played by the hand-set evaluation's bot, which does not read the weights being fitted, so a fit is one step from a fixed source and never a round fed by the last one. A weight that comes out against its number's meaning is held at 0 and the rest fitted again (today: raids either way, the room to place, the chance of the opponent's den emptying, M's own next card, N's animals at risk); those numbers read coincidences of the games, such as a deck that both holds fliers and loses.

### Refitting the race evaluation

After a change to the cards, from the game folder:

```
tools/bot_bench/bench.sh fit --write
tools/bot_bench/bench.sh run --x turn:budget=20000,mull=2,eval=race --y turn:budget=20000,mull=2,OLD --seeds 60 --name refit
```

The first takes about four minutes on six cores, writes `race_weights.json` and prints the weights it replaces as a spec (`the weights this build plays, as a spec:`); that line, for OLD, makes the second the gate: the new weights (compiled in by the run's build) against the old. Keep the new file if it is not worse; a fit's log-loss says nothing about play. Then the confirmation at Practice's budget with the reply level, against `turn:budget=200000,reply=12,per=2` on fresh seeds and on random decks.

What the fit is worth and how far it can be trusted. Fits from different games (other seeds, the race bot's own games instead of the hand-set bot's, 12,000 or 24,000 games, the four numbers added for multi-card turns) all play within a point of each other at 20,000 positions (49.4% to 50.5%, 3,000 games each, intervals about ±0.9), though single weights wander between them: food, `need` and `close_*` all carry the food lead and trade weight among themselves (food 0.28 to 0.97). A second fitting round once scored 49.1% (47.9 to 50.3) against the first; read against this spread, that is most likely the same spread and not a round going wrong. Around the fit, the weights of cards in hand, animals and strength each moved to about half and about one and a half times play the same or a point worse (3,000 games each); strength at twice its weight was the one at +1 (51.0%).

Tests: `cd engine_rs && cargo test --release --no-default-features --lib bots` (a bot's choice does not change when the hidden cards are dealt another way, with the reply level, the race evaluation and the mulligan too; a world holds exactly the cards the seat can count; the look for a win reads nothing hidden; a win in hand is taken in two positions saved from games; a seeded game replays).

## Where the bots stand (2026-11-22, Martin's five decks, 2,000 games a line unless said; with the fatigue rule)

`v1` is `turn` with no reply level, `v2` is `turn:reply=12,per=2`, each at the budget named; `v3` is `v2` with `eval=race,mull=2` (Practice). Seed 1 is the runs' default, 11 a fresh one; the random decks are 8 (deck seed 1), 16 deals a pairing, 2,048 games.

| X | Y | seeds | X wins | 95% interval |
|---|---|---|---|---|
| v3 200,000 | v2 200,000 | 1 | 67.7% | 66.0 to 69.4 |
| v3 200,000 | v2 200,000 | 11 | 66.3% | 64.6 to 68.1 |
| v3 200,000 | v2 200,000 | random decks | 65.4% | 63.7 to 67.1 |
| v3 200,000 | v1 200,000 | 1 | 69.7% | 67.9 to 71.5 |
| v3 200,000 | v1 200,000 | 11 | 70.2% | 68.4 to 71.9 |
| v3 200,000 | v1 200,000 | random decks | 69.8% | 68.1 to 71.4 |
| v3 200,000 | `greedy` | 1 | 86.1% | 84.7 to 87.4 |
| v3 200,000 | `greedy` | 11 | 87.0% | 85.6 to 88.3 |
| v3 200,000 | `greedy` | random decks | 84.9% | 83.5 to 86.3 |
| v2 200,000 with `eval=race` | v2 200,000 | 11 | 53.2% | 51.8 to 54.6 |
| v2 200,000 with `mull=2` | v2 200,000 | 11 | 60.3% | 58.5 to 62.1 |

| X | Y | X wins | 95% interval |
|---|---|---|---|
| v1 20,000 | `greedy` | 71.0% | 69.4 to 72.7 |
| v2 200,000 | `greedy` | 74.2% | 72.7 to 75.8 |
| v2 20,000 | v1 20,000 | 52.1% | 50.9 to 53.4 |
| v2 200,000 | v1 200,000 | 55.0% | 53.8 to 56.3 |
| v2 2,000,000 | v1 2,000,000 (600 games) | 53.8% | 51.5 to 56.1 |
| v2 2,000,000 | v2 200,000 (600 games) | 52.0% | 49.7 to 54.3 |
| v2 200,000 | v1 20,000 | 55.8% | 54.4 to 57.1 |
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

The mulligan. Keeping every opening hand was the largest single loss in the bot's play. `mull=T` against the same race bot keeping every hand, at 20,000 positions (3,000 games each): `mull=2` 62.2% (60.7 to 63.6), `mull=3` 61.5%, `mull=4` 57.6%, `mull=5` 53.8%, `mull=6` 52.4%; `mull=1` against `mull=2` 47.0%. At Practice's budget the mulligan alone is worth 10 points against v2, the race evaluation alone 3, both together 16.

The reply level's candidates. Asked about 48 turns instead of 12 (`reply=48,per=0`, 600,000 positions, 200 games), the reply level picks a turn its own search ranked below twelfth in 9.3% of turns with the hand-set evaluation and 8.7% with the race evaluation, fifth to twelfth in 12 to 14%. So the race evaluation, which prices the opponent's next card on the open and weakly held tiles, did not move the turns the reply favours into the twelve; and asking about more turns has never played better (`reply=24` 50.2%), so the turns it favours from further down are mostly the luck of three imagined hands, not stopping plays missed. Adding as candidates the turns that leave the opponent least food to stand at after their next turn (the race evaluation's own estimate) lost: three of them in the twelve, 48.1% (46.3 to 49.9, 1,000 games).

What did not work. Scoring the reply level's leaves by four games played out to the end by the shipped greedy evaluation, mixed with the evaluation: 45.0% (42.9 to 47.1), the playouts too weak to say anything. Four numbers for turns of several cards (the third to sixth best tiles, how near the pay of the three best tiles brings a side to the winning food): fitted, they play the same (50.4%).

Area removal, bursts and bare boards. Read from losses alone, v3 looked worse than v2 at three things: one card removing three or more of its animals (29 times in 40 losses against 4), the opponent gaining 10 or more food in a turn (7 against 2), ending turns with no region (53% of its later turns against 44%). Counted over every game (500 games, v3 against v2, the run's summary line), none of them is v3's: three or more animals removed at once 0.184 times a game for each, a turn of 10 or more food for the opponent 0.060 times a game against 0.056, no region held at the end of its own turns from its fourth 25.8% against 33.8%. The losses were the games where these happened, not a bot that lets them happen more. What was tried on them, each against v3 itself (1,000 games at 200,000 positions, 3,000 at 20,000):

| X | X wins | 95% interval |
|---|---|---|
| six imagined hands instead of three (`hands=6`) | 50.2% | 48.3 to 52.1 |
| four turns per set of plays (`per=4`) | 51.0% | 49.1 to 52.9 |
| the twelve best whatever they play (`per=0`) | 49.3% | 47.3 to 51.3 |
| an area-removal number in the race evaluation, fitted (-3.6 food an animal exposed), 200,000 | 50.3% | 48.4 to 52.2 |
| the same and a number for the regions a turn of up to three cards completes, fitted (-2.2 a food), 200,000 | 50.5% | 48.6 to 52.4 |
| the same at 20,000 | 50.1% | 49.1 to 51.1 |
| the area number at -10, at 20,000 | 49.7% | 48.6 to 50.7 |
| the area number at -20, at 20,000 | 48.0% | 46.9 to 49.1 |

The area number found each card's reach by playing it through the rules on a copy: an empty board, the enemy's plain animals of one strength on every neighbour of the middle tile, the card landed in the middle; its reach was the highest strength at which two or more were gone (it found the Rhino's 5, the Albatross's 4, the Young Rhino's 3 and the Young Albatross's 2 without reading a card). Priced at the fitted weight, the bot was removed three at a time as often as before (0.223 against 0.236 a game); priced at -20 less often (0.176 against 0.216) and it lost: a region is three animals side by side, and keeping animals apart costs more regions than area removal takes. Neither number is in the bot.

The mulligan's cut-off by what the bot can see, each against `mull=2`, 20,000 positions, 3,000 games: a cut-off of 1 or 3 for the seat going first 48.8% and 49.2%; 3 or 1 for the seat going second 49.4% and 49.1%; one card over the cut-off kept when the hand holds two (or three) at or under it 45.3% (47.9%); a card sent back only while 20, 35 or 50 hundredths of the rest of the decklist costs 2 or less 49.9%, 48.4%, 44.6%. The fixed 2 stands. And weights fitted to 6,000 games of v3 itself instead of the hand-set bot's (labels from stronger play) play the same as today's: 49.8% (47.9 to 51.7) at 200,000.

Speed and time (the Mac, one core, 100 games on one thread): about 1.7 million positions a second. v2 at 200,000 uses 51,000 positions and 25 ms a turn, the slowest choice 86 ms; v3 54,000 and 31 ms, the slowest 122 ms (the race evaluation costs about a fifth more than the hand-set one). A position's copy takes about 100 ns and its key 66 ns; before they were made cheaper (170 and 220 ns) a 30-second sample of v2 at 2,000,000 put copying at 47% of the time and the key at 18%, and the change made the turn bots 1.46 to 1.56 times faster, playing the same seeded games. Not profiled again since.

The games: about 12 turns for both players together, the player who goes first wins about 62%. No game in any run above reached the 400-turn limit. Between two v2 bots 25 to 40 games of 2,000 end by fatigue (an empty deck taking the loser's last food), every one of them Control against Control, and the longest game is 47 turns; against `greedy`, none.
