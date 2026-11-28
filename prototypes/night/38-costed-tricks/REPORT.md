# 38 Costed tricks: alive

Passes every machine gate (`node sim.mjs 400`, `report.json`); the set positions pass (`node sanity.mjs`); the page plays (`node check.mjs`: whole games clicked through in headless Chrome at 1512×800 and phone width, no script errors).

## Numbers

- Expert vs Random: **100%** of 400 (seats alternated, same deals)
- Expert vs Greedy: **86.8%** of 400
- Expert vs High (its highest card it can pay for, face-up, every time): **83.3%** of 400
- First player's win rate (first leader of hand 1), Expert vs Expert: **48.7%** of 400; Greedy vs Greedy: 50.9% of 2000
- Games hitting a cap: **0%**; no game reached the rules' last hand undecided and none was drawn
- Expert's choice equal to Greedy's: **37.9%** of its decisions with more than one option
- Length: 2.7 hands (a hand pays out 15 points, the target is 20)

There is no racer here (trick-taking has nothing to race), so the third trivial bot is High. Expert is single-observer ISMCTS (2000 iterations a move, play-outs to the end of the hand). The opponent's hand is redealt each iteration from the cards it has not shown face-up, leaving out every card its failures to follow suit ruled out (no card of that suit it could have paid for); in the tree its face-down plays show nothing.

## The loop

Ten energy has to buy eight tricks whose prizes are shown in advance, so each hand is a budget: which 2s and 3s to fight for, and which 1s to throw away. Expert leads its strong cards (high trumps, 6s) into the 3-point tricks, dumps cards it can no longer pay for or does not need face-down into the 1-point tricks (about one play in seven is face-down), wins a face-down lead with a free card, and leads suits that make the opponent pay to follow. Follow-suit is the pressure: a led suit forces the follower to spend on it whenever it can, so leading into the opponent's known suits drains its energy before the big prizes come up.

## Notes

- Set positions (Expert, every seed): answer a face-down lead with a free card, of two winning cards play the cheaper, on 18 points lead the top trump into the 2-point trick to win.
- Rules choices where the spec is silent: face-down cards stay hidden after the trick; with both on 20 or more and equal after hand 5, the game is a draw (the spec's "after 5 hands, equal is a draw" taken over "equal plays another hand").
