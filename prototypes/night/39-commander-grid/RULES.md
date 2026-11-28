# 39 Commander grid

Every number is a placeholder.

- A grid of 5 columns and 6 rows. Each side has a Commander (attack 2, health 15), starting in the middle of its back row. Bring the enemy Commander to 0 health; both at once is a draw.
- Both play the same 24-card deck. Random first player; the first draws 3, the second draws 4 and gets the Coin (0 mana: +1 mana this turn).
- **Your turn:** your maximum mana goes up by 1 (cap 8) and refills; draw 1 (empty deck: nothing). From round 15 on (a round is one turn each), your Commander first takes 1 damage, 2 in round 16, and so on.
- **Play cards** by paying their cost. A unit goes onto an empty cell orthogonally next to your Commander.
- **Act:** each of your pieces (the Commander included, units played this turn excluded) may **move** 1 cell orthogonally to an empty cell and then **attack** an orthogonally adjacent enemy piece, both optional: both deal their attack to each other. Attacking ends the piece's turn. Damage stays; a unit at 0 health is removed. *(Changed after the gate: the spec lets a piece move or attack, not both. See `report.json`; `MOVE_THEN_ATTACK` in `src/engine.js` switches back.)*
- Turn cap 80 turns (a draw); the round-15 damage ends every game before it.

| Card | Cost | Attack/Health or effect | Copies |
|---|---|---|---|
| Pawn | 1 | 1/2 | 4 |
| Raider | 2 | 3/2 | 4 |
| Guard | 2 | 1/5 | 3 |
| Line | 3 | 3/3, moves up to 2 cells (each step to an empty cell) | 3 |
| Heavy | 4 | 4/5 | 3 |
| Lancer | 4 | 3/3, attacks a piece exactly 2 cells away in a straight line, whatever stands between, and takes nothing back; cannot attack adjacent pieces | 2 |
| Hit 3 | 2 | 3 damage to an enemy piece within 2 cells (counted orthogonally) of your Commander | 3 |
| Rally | 1 | one of your pieces that has already moved or attacked this turn may move and attack again | 2 |

## Files

`node build.mjs` writes `index.html` (and `artifact.html`); `node sim.mjs` runs the gate into `report.json`; `node sanity.mjs` the set positions; `node check.mjs` plays the page headless; `node quick.mjs A B n` a quick head-to-head.
