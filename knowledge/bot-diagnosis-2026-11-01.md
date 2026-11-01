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

## The loop, as it runs now

The evaluation function was fitted on positions labelled only by who won the game. Each decision's search imagines thousands of positions two turns out and throws its answer away. Martin, 2026-11-01, on why simulation is wasteful: the same positions recur and the continuations from a mid-game position are the valuable part. So self-play now keeps what the search found: `tools/policy/selfplay_rs.py` plays games whole in Rust (`ak_engine.play_game`, every seat the search with the candidate net, 3 s a move, 5% random moves) and writes the games for the candidate net, the positions labelled by outcome, and the turn-start positions labelled by the search's own score of the position as a win chance (sigmoid of its points over 47, the evaluation's scale).

Round 1 runs the night of 2026-11-01 to 02: `results/policy/r1.jsonl`, `r1_out.npz`, `r1_search.npz` (4,000 games asked, three at a time with three threads each; a checkpoint every 200 games in `r1_*.partial.npz`; the spec in `r1_spec.txt`, log `r1.log`). The morning:

1. Refit the evaluation on rounds 4 to 10 plus the new positions, once with the outcome labels and once with the search labels: `.venv/bin/python -m animal_kingdom.learn.slotnet results/netlearn/slot_r1_out.json results/netlearn/board_r{4,5,6,7b,8,9,10}.npz results/policy/r1_out.npz --live --test results/netlearn/human_set_board.npz`, and the same with `r1_search.npz` into `slot_r1_search.json` (the search-labelled rows alone are too few to fit on their own).
2. Retrain the candidate net on the Expert's games plus the new ones (`tools/policy/extract.py OUT.npz expert results/policy/r1.jsonl` with `AK_EXTRA_DECKS` from `results/policy/decks.json`, then `train.py`, `export.py`) only if the search's picks drift from the net's top 8 on the new games; at 90% it is not the bottleneck.
3. The pass/fail: the search with each refitted evaluation against tonight's bot (the search with `wave2_slot_r4_10_live`), 200 paired games on the ten decks, both untimed. The plan holds if a refitted one wins clearly (interval above zero). If neither does, the loop has no engine of improvement at this scale, and the next question is whether the labels or the games are at fault, not more rounds.

## Evidence counted

Misplays Martin reported 2026-10-20 to 2026-10-31: 15 positions. Treatments: 10 network rounds (one shipped on his call with a clear deck down), about 15 dials (7 shipped, the rest benchmark washes), one search rebuild, eight speed passes. Static score right and search wrong: Tiger, Eagle, Rhinoceros. Static score wrong and search rescued: Oxpecker. Net blind spots named in the record: own-den-front body, spent Roar, grazing, timers, the price of a buried 7. Depth 2 on the best network: +4.7 against depth 1's +4.9 (2026-10-23). Twenty worlds against five: a wash. Whole-turn depth 1 on a mid-game position: over 60 s; Martin's bound: 30 s.
