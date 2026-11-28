# Supply Grid

Two players on a 5×5 grid, the same 24-card deck each. Destroy the enemy Base, or have more pieces on the grid after round 12.

- **Start.** Each Base (power 3) sits in the middle of its own edge row. Random first player; the first player draws 3, the second draws 4 and gets the Coin (0 mana: +1 mana this turn).
- **Turn.** Your maximum mana goes up by 1 (cap 8) and refills; draw 1 (an empty deck draws nothing). Then in any order:
  - **Place** a unit by paying its cost on an empty cell orthogonally next to one of your pieces.
  - **Strike**: each of your pieces, the Base and units placed this turn included, may strike once per turn at an orthogonally adjacent enemy piece. The lower power is destroyed; equal power destroys both. A Wall cannot strike.
  - Play **Cut**.
- **Supply.** After every placement, strike or spell, every piece no longer connected to its own Base through a chain of its own pieces (orthogonal steps) is removed.
- **End.** A player whose Base is destroyed loses; both at once is a draw. After round 12 (12 turns each) the player with more pieces on the grid, Base included, wins; equal is a draw.

## Cards

| Card | Cost | Power | Copies |
|---|---|---|---|
| Post | 1 | 1 | 5 |
| Line | 2 | 2 | 5 |
| Squad | 3 | 3 | 4 |
| Heavy | 4 | 4 | 3 |
| Big | 6 | 6 | 2 |
| Wall | 2 | 3, cannot strike | 3 |
| Cut | 2 | spell: destroy an enemy unit with power 2 or less | 2 |

## Files

`node build.mjs` writes `index.html` (and `artifact.html`): you against Expert, your Base at the bottom, first player alternating. `node sim.mjs` runs the gate and writes `report.json`; `node sanity.mjs` the set positions; `node check.mjs` plays whole games through the page's calls in node and by clicks in Chrome.
