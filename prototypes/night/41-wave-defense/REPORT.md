# 41 Wave defense: alive after one rule change (dead at the spec's rules)

`node sim.mjs 400 600` runs both versions on the same 400 seeds; numbers in `report.json`, set positions in `node sanity.mjs`. One player, so the gate compares paired games: Expert, Greedy and Random each play the same seeded game (same threat order, same first deck order, same reward offers), and a pair goes to whoever ends better (a win beats a loss; two wins, more Wall; two losses, more rounds; for two wins the spec's "more rounds survived" would only reward a slower win, so it is not used).

## The spec's rules (mana = round number, cap 8): dead

Greedy wins 99.5% of games with 19.75 of 20 Wall left; Expert wins all with 20. Expert ends better than Greedy in only 30 of 400 pairs; the other 370 are even. Counting only decided pairs (the concept's note) gives 100%, but that hides the point: a fixed rule plays this game perfectly. Why, about the loop: income (mana rising with the round, 2 cards a round, a hand that persists) outgrows the threat, so spending is never scarce and "where to spend" is never a choice.

## The one change: mana is 4 every round: alive

Stated before measuring: a flat income makes each round's spend compete, while keeping every card (cost up to 4) playable.

| Check | Result | Line |
|---|---|---|
| Expert vs Greedy, paired | better in 370 of 400, worse in 0 (Greedy wins 39%, 13.3 Wall on wins) | ≥ 70% of decided pairs |
| Expert vs Random, paired | better in 400 of 400 (Random wins 0%) | ≥ 70% |
| Expert's own result | wins 100%, always at full Wall | reported |
| Games at the round cap | 0% | ≤ 2% |
| Expert's choice equals Greedy's | 24.5% of 25,621 decisions | ≤ 90% |
| Set positions (finish the last threat, no Repair on a full Wall, Bomb three 2-health threats) | Expert all pass; Greedy Repairs a full Wall | |

Expert: determinized flat Monte Carlo over each action (600 play-outs, successive halving, play-outs to the end of the game), reshuffling the unrevealed threats within their tiers, its own deck and the future reward offers; its play-out rule's own move stands unless another beats it by a standard error. The gate's first run caught that Expert Repairing a full Wall (every option scored the same, noise picked it); the default move fixed it and the flat-4 numbers above are from the fixed bot. Caveat for the morning: the Expert never loses a point of Wall, and the hand-written play-out rule alone wins 97%, so at these numbers it is an easy puzzle even though Greedy fails it.

## The loop

- Each round: where 4 mana goes among Hit 3s, Draw 2s and Defenders, which lane gets a Defender, and which reward (if any) joins the deck.
- Watching the Expert (30 games): Hit 3 and Draw 2 are most of its plays, chained to kill each threat before it reaches the Wall; it declines the reward in 51 of 90 offers, keeping the cheap start deck thin; it leaves about half a mana unspent a round.
- The best play boils down to killing everything early with the cheapest damage and not diluting the deck; the 4-mana rewards are mostly worse than another pass through the start deck.
