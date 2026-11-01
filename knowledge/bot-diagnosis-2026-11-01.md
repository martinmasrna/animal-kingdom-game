# Bot play: the diagnosis of 2026-11-01

A reading by the second last-hope run, from the full record (every bot session 2026-10-17 to 2026-11-01, docs/bots.md, the bot commit history), awaiting Martin's verdict. Nothing here is settled until he says so.

## The sentence every treatment shared

"The right move is the one with the highest average score, so the job is to compute that average more exactly and faster." Ten network rounds, about fifteen search dials, the whole-turn rebuild and eight speed passes all served that sentence. None of them gave the bot any notion of what a move is for.

## What is broken

The bot has no model of threats. It never asks "what does he threaten, what do I threaten, what must I stop"; it lists everything and averages a number over sampled hands. Two consequences, and every recorded misplay falls under one of them:

1. The number it averages is a statistical correlate of winning in bot-vs-bot games, not a judgment of the position. It cannot know that burying your own 7 is bad (bots never did it, so it never learned it), that a Roar already fired is spent, that a small body on your own den front is a defence and not a sign of losing. A search over such a number seeks out exactly the leaves where the number is wrong in the bot's favour (Oxpecker 2026-10-30, Alley Cat and Tiger-Lion 2026-10-27).
2. The averaging over sampled hands with decided games at ±500 turns every tactical question (can he kill me, can I kill him, which hands do I survive) into an expectation that drowns the board difference: greedy-you takes bait (Tiger 2026-10-31, Eagle 2026-10-28), oracle-you knows its deck order (Gorilla 2026-10-31), five hands miss the 11% (turn 28, 2026-10-31), every line lost means every move ties (Lions 2026-10-30).

Because nothing in the system knows what matters, nothing can prune: the human sees three to five legal spots and two or three candidate turns (docs/design/how-the-game-works.md §4), the search sees 200 to 3,000 whole turns and 10,000 replies per hand, and depth 2 costs minutes. Pruning by the same blind number drops exactly the lines that matter (the Tiger's Roar target for 3.5 points, the Lion onto the Butterfly). A fast exhaustive search is not an engineering problem; it is impossible without a relevance model, and the relevance model is the thing that was never built.

Every dial in the record (den_sense, den_open, den_far, outs, reply_min, quiesce, decisive, the lethal checks) is one threat bolted onto the averager after Martin pointed at it. That is why each fix held on its position and the next blunder arrived within a day.

## Why the loop could not learn

- Verifier: the only in-system judge of a play is the number under test; the benchmark pits two bots sharing the same blind number, so the blunder class is invisible to it. Martin is the only verifier, one position a day.
- Channel: Martin's own reasoning arrived each time as threats ("block the Cat to Cat lethal, then best chances next turn", "2 or 3 choices, not 400") and was translated each time into more enumeration (skip decided hands, sample draws, whole turns).
- Base rate: no documented bot plays a Hearthstone-like game at strong human level by search alone; the competition winners (Coac for Legends of Code and Magic, the Hearthstone AI competition) are shallow searches with explicit lethal detection, move ordering and pruning over a legible evaluation. Those bots do not make "no universe" plays, because the blunder classes are priced explicitly.

## The test that could prove this wrong

Build the smallest threat-first bot: exact win-now and lose-next-turn checks over the unseen pool, a handful of candidate turns from those threats, an explicit evaluation Martin can read, a shallow look at the opponent's few dangerous replies. Run it on the six worked positions and the recorded misplays inside 5 s. If it plays the sound move on most of them, the diagnosis holds. If it makes the same "no universe" plays, the horizon is the link and this reading is wrong.

## Evidence counted

Misplays Martin reported 2026-10-20 to 2026-10-31: 15 positions. Treatments: 10 network rounds (one shipped on his call with a clear deck down), about 15 dials (7 shipped, the rest benchmark washes), one search rebuild, eight speed passes. Static score right and search wrong: Tiger, Eagle, Rhinoceros. Static score wrong and search rescued: Oxpecker. Net blind spots named in the record: own-den-front body, spent Roar, grazing, timers, the price of a buried 7. Depth 2 on the best network: +4.7 against depth 1's +4.9 (2026-10-23). Twenty worlds against five: a wash. Whole-turn depth 1 on a mid-game position: over 60 s; Martin's bound: 30 s.
