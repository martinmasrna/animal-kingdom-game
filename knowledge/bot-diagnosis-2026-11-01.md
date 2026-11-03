# Bot play: the diagnosis of 2026-11-01

A reading by the second last-hope run, from the full record (every bot session 2026-10-17 to 2026-11-01, docs/bots.md, the bot commit history), awaiting Martin's verdict. Nothing here is settled until he says so.

## The sentence every treatment shared

"The right move is the one with the highest average score, so the job is to compute that average more exactly and faster." Ten network rounds, about fifteen search dials, the whole-turn rebuild and eight speed passes all served that sentence. None of them gave the bot any notion of what a move is for.

## What is broken

The bot has no model of threats. It never asks "what does he threaten, what do I threaten, what must I stop"; it lists everything and averages a number over sampled hands. Two consequences, and every recorded misplay falls under one of them:

1. The number it averages is a statistical correlate of winning in bot-vs-bot games, not a judgment of the position. It cannot know that burying your own 7 is bad (bots never did it, so it never learned it), that a Roar already fired is spent, that a small body on your own den front is a defence and not a sign of losing. A search over such a number seeks out exactly the leaves where the number is wrong in the bot's favour (Oxpecker 2026-10-30, Alley Cat and Tiger-Lion 2026-10-27).
2. The averaging over sampled hands with decided games at ±500 turns every tactical question (can he kill me, can I kill him, which hands do I survive) into an expectation that drowns the board difference: greedy-you takes bait (Tiger 2026-10-31, Eagle 2026-10-28), oracle-you knows its deck order (Gorilla 2026-10-31), five hands miss the 11% (turn 28, 2026-10-31), every line lost means every move ties (Lions 2026-10-30).

Because nothing in the system knows what matters, nothing can prune: the human sees three to five legal spots and two or three candidate turns (docs/design/how-the-game-works.md §4), the search sees 200 to 3,000 whole turns and 10,000 replies per hand, and depth 2 costs minutes. Pruning by the same blind number drops exactly the lines that matter (the Tiger's Roar target for 3.5 points, the Lion onto the Butterfly). A fast exhaustive search is not an engineering problem; it is impossible without a relevance model, and the relevance model is the thing that had never been built.

Every dial in the record (den_sense, den_open, den_far, outs, reply_min, quiesce, decisive, the lethal checks) is one threat bolted onto the averager after Martin pointed at it. That is why each fix held on its position and the next blunder arrived within a day.

## Why the loop could not learn

- Verifier: the only in-system judge of a play is the number under test; the benchmark pits two bots sharing the same blind number, so the blunder class is invisible to it. Martin is the only verifier, one position a day.
- Channel: Martin's own reasoning arrived each time as threats ("block the Cat to Cat lethal, then best chances next turn", "2 or 3 choices, not 400") and was translated each time into more enumeration (skip decided hands, sample draws, whole turns).
- Base rate: no documented bot plays a Hearthstone-like game at strong human level by search alone; the competition winners (Coac for Legends of Code and Magic, the Hearthstone AI competition) are shallow searches with explicit lethal detection, move ordering and pruning over a legible evaluation. Those bots do not make "no universe" plays, because the blunder classes are priced explicitly.

## The test, and what it showed

The relevance model is a candidate network (`engine_rs/src/bots/cand.rs`, `tools/policy/`): from the position and an action's own features it scores every legal action, trained on which action the Expert's search took. Day 1 (2026-11-01): the search's move is in its top 8 on 91% of held-out Expert decisions and 88% of Martin's 4,485 logged moves; ranking by the evaluation function, which is how the search cuts today, gets 87% and 80%; chance about 50%. The 90% is the ceiling of a picker that imitates the Expert: it cannot pick better moves than its teacher, it makes the search affordable. Day 2: the whole-turn search on the net's six candidates, two turns deep, one draw outcome and one reply per line over five imagined hands, against the live Expert's exhaustive one-turn search, both untimed, Martin's ten decks, 380 paired games (`results/bot_quality/cand-v4-m1`): +3.2 points, interval -2.2 to +8.5. Not worse, not clearly better. The reading: cutting by the net throws away nothing the exhaustive search found, and looking deeper on the right moves bought nothing, because both searches end in the same evaluation function. The strength has to come from that function.

A per-move deadline (`time_budget` on the atomic bot) makes the deeper search answer in bounded time from the deepest level it finished; Martin, 2026-11-01: 15 s for the live bot, "maybe 15 to try first", the 8 s and 30 s in the record were agents' numbers.

## The loop, and what one round showed

The evaluation function was fitted on positions labelled only by who won the game. Each decision's search imagines thousands of positions two turns out and throws its answer away. Martin, 2026-11-01, on why simulation is wasteful: the same positions recur and the continuations from a mid-game position are the valuable part. So self-play keeps what the search found: `tools/policy/selfplay_rs.py` plays games whole in Rust (`ak_engine.play_game`, every seat the search with the candidate net, 3 s a move, 5% random moves) and writes the games for the candidate net, the positions labelled by outcome, and the turn-start positions labelled by the search's own score of the position as a win chance (sigmoid of its points over 47, the evaluation's scale). Checkpoints every 200 games are written whole and renamed, so a run killed mid-save keeps its last one.

Round 1 (`results/policy/r1*`, the night of 2026-11-01 to 02): 3,000 games, 132,393 positions labelled by outcome; its search labels were lost to a checkpoint killed mid-save, so 1,200 more games with search labels followed (`r1s*`, 12,031 search-labelled turn starts). On those turn starts the search's label agrees with the eventual winner on 63%, the evaluation alone on 60%: the search knows more than its network. Two refits of the evaluation, both on rounds 4 to 10 plus the new positions: `results/netlearn/slot_r1_out.json` on the outcome labels alone, `slot_r1_search.json` with the search-labelled rows added at ten times their weight. On Martin's 974 logged positions they predict the winner's side on 70% and 68%, the hand formula on 65%.

The pass/fail, each refit's search against the round-0 bot (the same search with `wave2_slot_r4_10_live`), 380 paired games on Martin's ten decks, 3 s a move, two threads a bot, run with `AK_RUST_BOTS=1` (without it `sim.bot_comparison` silently runs the Python whole-turn search, hours a deck):

| the search's evaluation | its wins | round-0 bot's wins | difference | 95% interval | where |
|---|---|---|---|---|---|
| refit on outcome labels | 51.6% | 47.4% | +4.2 | −1.3 to +9.7 | `results/bot_quality/r1-out` |
| refit on outcome and search labels | 50.0% | 48.7% | +1.3 | −4.5 to +7.1 | `results/bot_quality/r1-search` |

Neither interval clears zero. The outcome refit is up on eight decks of ten; the search-label refit is a wash whose whole gain sits in one deck (p2, +26). The reading: one round moves the evaluation by a few points at most; 12,000 search-labelled rows add nothing to 1.6 million outcome rows; and the benchmark's resolution at 380 games is about ±5.5 points, so a step of this size is invisible to it. Seeing a +4 step with the interval above zero takes about 800 paired games; a round costs ten hours of games and four of benchmark. One round at a time, this benchmark cannot steer the loop.

What runs instead: rounds continue unattended with the outcome refit as the search's evaluation (round 2 is `results/policy/r2*`, 3,000 games, the night of 2026-11-02 to 03, spec in `r2_spec.txt`); the number read between rounds is the refit's prediction of the winner's side on Martin's logged positions (`outside_test` in the fit log, `sign_t5_9`, 71.2% for the round-1 refit); the benchmark runs once on the sum of three rounds against the round-0 bot at 800 paired games. The disproof: if that sum stays inside its interval, labels from this bot's own games do not move its evaluation, and the next question is what the network cannot see in its features (the blind spots named below), not more games.

## Evidence counted

Misplays Martin reported 2026-10-20 to 2026-10-31: 15 positions. Treatments: 10 network rounds (one shipped on his call with a clear deck down), about 15 dials (7 shipped, the rest benchmark washes), one search rebuild, eight speed passes. Static score right and search wrong: Tiger, Eagle, Rhinoceros. Static score wrong and search rescued: Oxpecker. Net blind spots named in the record: own-den-front body, spent Roar, grazing, timers, the price of a buried 7. Depth 2 on the best network: +4.7 against depth 1's +4.9 (2026-10-23). Twenty worlds against five: a wash. Whole-turn depth 1 on a mid-game position: over 60 s; Martin's bound: 30 s.

## What 2026-11-03 measured

Martin's questions drove the day: "how is it different from search depth", "isn't this overindexing into one situation", "what does 'values problem' mean in practice", "is there a cheap way to test", "maybe the mistake is forcing the bot to be general instead of letting it identify cards by id". Every claim below was measured; the claims that failed their test are listed last so the record stops repeating them.

The exploit under study: the combo deck (Martin's p5; Laras's first-week deck, 275 wins to 20 against the Expert, 68% of her wins by turn 5). Its test: the old Expert pilots p5 and attacks; a defender plays the other nine decks; 144 paired games; the numbers are the defender's wins and the share of games where the den falls by turn 5 (`results/bot_quality/exploit-p5*`).

| defender | wins | den captured by turn 5 |
|---|---|---|
| the live Expert (greedy reply model, 8 s) | 40% | 31% |
| the whole-turn search, 5 hands, 3 s (Saturday's benchmark setting) | 41% (+0.7, −8 to +10) | 27% |
| the whole-turn search, 20 hands, 30 s (Martin's budget, 2026-11-03) | 51% (+11.1, +1.4 to +20.1) | 26% |

So: the search's gain is real and comes from time and hands, not from the whole-turn reply alone (Saturday's flat tournament measured the cheap setting and was right about it); and no search budget moves the early kills. On Martin's own replayable captures, the whole-turn search two bot-turns before the capture already scores five of six positions as losing (−20 to −125 two rounds out, with 5 hands as with 20); one turn before, no defence exists. The decision that loses is on turns 1 and 2, where every bot reads the position as fine (+55, −19) and draws. The bot attacker is half a Laras (60% wins against the Expert to her 93%), so a pass on this test is necessary, not sufficient.

The judge, measured on 36,025 turn-start positions (turns 1 to 8) from the chaining bot's own 4,914 self-play games, held out by game, label "the side to move loses its den within 3 turns" (base rate 8.8%), scored as AUC (0.5 is useless):

| ranks the positions by | AUC |
|---|---|
| the live judge's own score (`wave2_slot_r4_10_live`) | 0.65 |
| the round-1 refit, old games plus new | 0.65 |
| the round-1 refit with the search's scores as labels | 0.65 |
| a refit on the chaining games only, no old games (`results/netlearn/slot_new_only.json`) | 0.65 |
| the same refit with the outcome discounted by distance, 0.9 a turn (`slot_disc9.json`) | 0.68 |
| the same, 0.75 a turn (`slot_disc.json`) | 0.72 |
| a linear predictor fitted to this label on the same 908 inputs | 0.77 |
| the same linear predictor on card identities instead (hand, board by side, opponent's unseen pool, 264 ids) | 0.80 |

The discount is a dial: the steep one predicts the final winner on Martin's 974 positions at 61% against the live judge's 67%, the gentle one at 65%. A judge with two outputs (final winner; danger in the next turns) would not have to trade. On the final-winner label the identity picture also beats the description picture: AUC 0.753 against 0.726, accuracy 69% against 66%.

What this says: the judge is taught one question, who won the whole game, in which a den lost in three turns and a grind lost in twenty are the same 0; and it is shown descriptions (strength, cost, tags, keywords, one bit "has a Roar") under which Mole and Mouse are the same card. The generalist rule (CLAUDE.md, 2026-07-02, "no deck slugs, archetype names or card ids in bot policies") was written against hand-coded card logic and is enforced by a source scan; a learned meaning per card id is the chess bot's "this is a rook" and is not what the rule forbade. Martin, 2026-11-03: "maybe the fundamental mistake we're making is trying to force the bot to be general, instead of letting it identify cards by id?" Martin dropped the rule on 2026-11-03 ("Just drop the sentence altogether, I don't care"); AGENTS.md keeps only the honesty invariant.

Pending as of writing: the discounted judge and the new-only judge in the cheap search, paired against the old judge, on the exploit test (`exploit-p5-newjudge`, `exploit-p5-disc`).

Claims made on 2026-11-03 that failed their test, so no session repeats them: that bot games contain no chains to the den (a third of self-play den captures are three placements or more); that the imagined hands are the likeliest hands (they are random deals); that five hands is the hole (five and twenty see the same losses two turns out); that the judge's inputs lack the warning signs (adding opponent-deck and chain-distance numbers to the 908 changed nothing: 0.765 to 0.766); that the lesson was drowned by old games (the new-only refit is 0.645). The one earlier reading that held: the live Expert plays the opponent's reply turn greedily (`advance`/`play_turn` in `engine_rs/src/bots/search.rs`), and the whole-turn search does not.

## The raw position: the evaluation function's inputs, agreed 2026-11-03

Martin and the session settled this line by line ("instinctively it sounds like the right shape, as simple and as raw as possible"); a cold Opus audit against the engine then found the holes marked *audit*. The principle: the network sees everything the rules read and nothing an agent summarised. What a card's printed text says comes through the card id; what differs between two copies of the same card is given as state.

Every card id maps to one learned vector (32 numbers to start; 16 and 64 tried offline), shared wherever the card appears. Evaluation is from the seat of one player, the board mirrored so my den is at the bottom (map_b is symmetric under the row flip); only on a quiet position (no effect resolving, no choice pending), which is how both searches already call it.

- Board, top piece of each of the 15 crossroads: card vector; owner mine/theirs/wild (*audit*: the Locusts); strength on my turn and strength on the opponent's turn (*audit*: Giraffe, Crocodile and Cape Buffalo change with whose turn it is); stored counter; inked; Spikes or Wild Boar charge spent (`retaliation_used`); granted Roam; roamed this turn; rank in its owner's play order (*audit*: Dawn/Dusk order, Queen guards); its scheduled effects, each as (ticks on my turns / theirs / every turn, ticks while buried, turns remaining, what it does, its amount) (*audit*: the Eel ticks on the opponent's turns, Poison stacks, the OTK Squirrel's stake is not on the card).
- Board, the card directly beneath the top: the same minus the within-turn bits, plus how many more sit beneath; and a pooled sum of everything deeper with its timed removals (*audit*: Venom and Poison tick under a cover and remove buried pieces).
- My hand: plain sum of card vectors; sum weighted by each card's strength as the rules compute it in hand; hand size; sum of cards whose Skunk lock is still live (`locked_until_turn > turn_counter`).
- My deck: plain and strength-weighted sums (a card priced as it would leave the deck: the Dung Beetle's reached form, the Bee's jelly on the counted copies only); deck size.
- Opponent's unseen pool, their hand and deck as one multiset: plain and strength-weighted sums, every copy priced from its card id plus public growth only, never from the instance (*audit*: instance counters would leak how their cards split between hand and deck); their hand size; their deck size; their locked hand cards (public, the bounce was seen); when my legendary Giraffe reveals their hand, hand and deck given separately with a revealed bit.
- Remove pile: plain and strength-weighted sums, mine and theirs.
- Food, each side. Side to move. Actions left this turn (covers the Beaver, the Eel and the one-action first turn). Idle turns in a row.
- Within the turn, zero once the turn ends: animals placed this turn; food gained this turn each side; animals lost this turn mine/theirs/wild and whether any was removed; roams this turn each side, free roams granted and used; the common Krill's discount used; per side the sum of card vectors played this turn (*audit*: the engine's `played_<p>` list, read by "if you played another <tag>", counts animals that have since died and excludes ones placed by effects).
- Game-long: the Woodpecker's double Roar live this turn; the Dung Beetle's eaten food each side; the Macaw's last Roar card each side.

Excluded, with the reason: the turn counter (read only for the first turn, the 400-turn cap and relative comparisons, all covered above); "placed this turn" (`placed_on_turn` is written and read by no rule); Falstaff's and the other `cap_*` flags (dead unless a config switch nobody sets is on); `free_roam_iid` (never written); instance ids, play_seq as a raw number, the random generator, the effect stack, the pending choice, first player (mulligan only), starting decks (Capybara and the Python fold into strength).

Upkeep: a test compares this encoding against the engine's own inventory (the state's `to_dict`, `UnitInstance`'s slots, the Rust `TurnFlags` struct and every `turn_flags[` key written in `effects.py`/`rules.py`): every field is encoded or on the exclusion list with its reason, so a new mechanic that adds state fails the test until someone decides what the network sees.

### The raw network's first test in play (2026-11-03, evening)

Trained on rounds 1 and 2 of the chaining bot's self-play (4,914 games, 105,284 positions from both seats), card vectors of 16 numbers, dropout 0.3. Offline, how often it ranks the winning position above the losing one: 77% on held-out self-play (live function 75%), 69% on Martin's games (67%); the doomed position below the safe one: 80% on self-play (67%), 78% on Martin's games (71%). With Martin's games in training, on his held-out games: 69% and 77% against the description network's 62% and 73%.

In play, the Den Rush test (the cheap whole-turn search, 5 hands, 3 s, defending with the raw network against the same search with the live function; the live Expert attacking on Den Rush; 144 paired games): raw network 35% wins and 25.0% dens lost by turn 5, live function 42% and 25.7%. Pooled −6 points, inside the noise but not positive; the early deaths unmoved. The raw network's scores have the same spread as the live function's (std 69 against 85 points, correlation 0.79, nothing clamped at ±500), so the thresholds are not the cause; its search is 1.5× slower per move on the same tree (2.8 s against 1.8 s), so at 3 s a turn it searched less.

What this says: an evaluation that ranks doomed positions better on paper did not stop the early deaths on the board at this data size. Next question, before anything else: at the saved positions two bot turns before Martin's captures, does the raw network see the loss where the live one did not (`two_turns_out_raw.log`)? If not, the inputs were not the hole either, and the remaining suspects are the games (3,000, played by the old bot) and the label (the game's end, not the search's verdict).

At the six saved positions two bot turns before Martin's captures (`two_turns_out_raw.log` against `two_turns_out5.log`), the raw network does not see the loss earlier than the live function. Where the live function already read the position as lost (game 5 at −228, game 7 at −30) so does the raw network (−215, −30); where the live function read it as fine at turn 1 (games 19 and 21: +108, +45) the raw network reads it as fine too (+36 to +44, +6), and in game 1 it is rosier (+59 against −37). So at this data size the inputs were not the hole: the danger at turns 1 and 2 is in Den Rush's hand and deck, and no function trained on 3,000 games in which Den Rush was one deck in ten, each labelled by who won twenty turns later, learned it. The remaining suspects are the games and the label. The next step follows the agreed loop: the 1,440 Den Rush benchmark games played today (five runs, both defenders, the live Expert attacking) and Martin's games added to the rounds, retrain, the Den Rush test again.
