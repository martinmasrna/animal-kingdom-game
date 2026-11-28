# 18 Edge flip grid

Every number is a placeholder. Borrowed from Triple Triad: four edge numbers per card, and a placed card takes every adjacent enemy card whose touching edge is lower.

- An empty 4×4 grid. Both play the same 20-card deck, shuffled. Random first player; the first draws 4, the second draws 5 and gets the Coin (0 mana: +1 mana this turn).
- **Your turn:** your maximum mana goes up by 1 (cap 6) and refills; draw 1 (an empty deck draws nothing). Place any number of cards on empty cells, paying each one's cost; each may be turned to any of its four orientations as it is placed.
- **Taking:** when a card is placed, each of its edges is compared with the touching edge of every orthogonally adjacent card the opponent owns; where yours is strictly higher, that card becomes yours. Taken cards take nothing further. Edges against the border do nothing.
- A turn with no placement is a pass.
- **End:** when all 16 cells are filled, or after both players pass on consecutive turns, the player owning more cells wins; equal is a draw.

| Card | Cost | Edges (clockwise from the top) | Copies |
|---|---|---|---|
| Point | 1 | 3, 1, 1, 1 | 3 |
| Pair | 1 | 2, 2, 1, 1 | 3 |
| Even | 2 | 2, 2, 2, 2 | 3 |
| Spear | 2 | 4, 1, 2, 1 | 3 |
| Hook | 3 | 4, 3, 1, 1 | 2 |
| Block | 3 | 3, 3, 3, 2 | 2 |
| Lance | 4 | 5, 2, 3, 2 | 2 |
| Crown | 5 | 4, 4, 4, 4 | 2 |

Turn cap 60 turns (a draw); never reached.

## Files

`node build.mjs` writes `index.html` (and `artifact.html`); `node sim.mjs` runs the gate into `report.json`; `node sanity.mjs` the set positions; `node check.mjs` plays the page headless.
