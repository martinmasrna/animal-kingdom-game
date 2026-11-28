# Breaking Sites

Two players, the same 30-card deck each, three shared sites. First to 15 points wins.

- **Start.** The 10 sites are shuffled into a site deck; 3 lie face-up. Random first player; the first player draws 3, the second draws 4 and gets the Coin (0 mana: +1 mana this turn).
- **Turn.** Your maximum mana goes up by 1 (cap 10) and refills; draw 1 (an empty deck gives the opponent 1 point). Play cards by paying their cost. A unit goes onto your side of any site (max 4 of your units per site).
- **Break.** After every card, a site whose total power, both sides together, is at least its threshold breaks. The side with more power there takes the Winner points; the other side takes the Runner-up points if it has at least one unit there; a tie gives both sides the Runner-up points. Its units go to their owners' discard piles and the next site from the site deck replaces it.
- **End.** The first player to reach 15 points wins at once. If the site deck is empty and every site has broken, the higher score wins; equal is a draw. A game that reaches turn 100 is a draw.

Only one site can reach its threshold from a single card here, so the spec's "the mover orders simultaneous breaks" never comes up; the engine still resolves several breaks the mover's best first.

## Sites

| Threshold | Winner | Runner-up |
|---|---|---|
| 8 | 3 | 1 |
| 9 | 3 | 1 |
| 10 | 4 | 1 |
| 10 | 4 | 2 |
| 11 | 4 | 2 |
| 12 | 5 | 2 (×2) |
| 13 | 5 | 3 |
| 14 | 6 | 3 |
| 15 | 6 | 3 |

## Cards (30)

| Card | Cost | Power or effect | Copies |
|---|---|---|---|
| Pawn | 1 | 1 | 5 |
| Squad | 2 | 3 | 5 |
| Force | 3 | 4 | 3 |
| Heavy | 4 | 6 | 3 |
| Big | 5 | 7 | 3 |
| Move | 1 | Move one of your units to another site | 3 |
| Strike | 2 | Destroy an enemy unit with power 3 or less | 3 |
| Boost | 2 | One of your units gets +3 power for the rest of the game | 3 |
| Draw 2 | 2 | Draw 2 cards | 2 |

## Files

`node build.mjs` writes `index.html` (and `artifact.html`): you against Expert, first player alternating. `node sim.mjs` runs the gate and writes `report.json`; `node sanity.mjs` the set positions; `node check.mjs` plays whole games through the page's calls in node and by clicks in Chrome.
