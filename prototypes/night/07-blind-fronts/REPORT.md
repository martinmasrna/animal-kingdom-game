# 07 Blind fronts: alive

Passes every machine gate (`node sim.mjs 400`, `report.json`); the set positions pass (`node sanity.mjs`); the page plays (`node check.mjs`: whole games clicked through in headless Chrome at 1512×800 and phone width, no script errors).

## Numbers

- Expert vs Random: **100%** of 400 (seats alternated, same deals)
- Expert vs Greedy: **99.5%** of 400
- Expert vs Spread (a fixed split: its three strongest cards, one to each front, then pass): **99.5%** of 400
- First player's win rate (first player of round 1), Expert vs Expert: **52.5%** of 400; Greedy vs Greedy: 53.9% of 2000
- Games hitting a cap: **0%**; no game reached the rules' own last round (12) and none was drawn
- Expert's choice equal to Greedy's: **17.3%** of its decisions with more than one option
- Length: 5.1 rounds between Experts, 3.5 against Greedy

Expert is single-observer ISMCTS (2000 iterations a move, play-outs to the end of the round, scored by points, banked energy and hand). The opponent's face-down cards are redealt each iteration from the cards it has not seen, each with the cost its energy drop showed; in the tree the opponent's placement is known only by front and cost. Once the opponent has passed, the rest of the round is solved exactly instead: every set of placements the energy pays for is scored over 48 dealt worlds of the face-down cards, and the best is played (worst case 76 ms).

## The loop

Each placement is a read of the other side: how many face-down cards sit at each front and what each one cost (the energy drop shows it), against what is left in your own hand and energy. Expert spends where the front is cheap to take, gives up fronts the opponent has paid heavily for, puts a Feint or Scout down as a decoy (about one Feint per player per game), and often passes early with energy unspent to bank toward a 10-energy round. Once the opponent passes, it takes what is left as cheaply as possible. The concept's question has a clear answer in the numbers: reading the commitments beats a fixed spread 99.5% and Greedy's fixed rotation 99.5%.

## Notes

- Set positions (Expert, every seed): a free front taken with the Scout after the opponent passed, an empty 3-front taken with a cheap card and never the Heavy, lethal (on 10 points, take the empty 2-front).
- A search weakness found by the free-front position and fixed before the gate: after the opponent passed, the tree could not tell good placement sets from bad through the noise of averaging over continuations, so that phase now uses the exact enumeration above.
- Rules read literally: each player starts with 4 energy and round 1 adds 4 more (8 in round 1); round 1 also draws 2 on top of the opening 5. Discards are face-up. The page shows each of the bot's face-down cards with the energy it paid, which the rules make public anyway.
