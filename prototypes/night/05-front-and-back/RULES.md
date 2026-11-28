# 05 Front and back rows

Every number is a placeholder.

- Life 20 each; bring the other to 0. Both play the same 30-card deck. Random first player; the first draws 3, the second draws 4 and gets the Coin (0 mana: +1 mana this turn).
- **Rows.** Each side has a front row and a back row, 3 units each at most. Melee units always go to the front row, Ranged units to the back row.
- **Your turn:** your maximum mana goes up by 1 (cap 10) and refills; your units become ready; draw 1 (from an empty deck you lose 1 life, then 2, then 3). Play cards by paying their cost. A unit cannot attack on the turn it is played.
- **Attack:** each ready unit may attack once. It must target an enemy front-row unit; only when the enemy front row is empty can it target an enemy back-row unit or the enemy player. A Melee attacker and its target deal their attack to each other; a Ranged attacker deals its attack and takes nothing back.
- Damage stays; a unit at 0 health is destroyed. Hit cards ignore rows: they hit any enemy unit.
- Turn cap 120 turns (a draw).

| Card | Kind | Cost | Attack/Health or effect | Copies |
|---|---|---|---|---|
| Striker | Melee | 1 | 2/1 | 3 |
| Wall | Melee | 2 | 1/5 | 3 |
| Raider | Melee | 2 | 3/2 | 3 |
| Line | Melee | 3 | 3/4 | 3 |
| Heavy | Melee | 5 | 5/6 | 3 |
| Shooter | Ranged | 2 | 1/2 | 3 |
| Gunner | Ranged | 3 | 2/2 | 3 |
| Cannon | Ranged | 5 | 4/3 | 3 |
| Hit 2 | Spell | 1 | 2 damage to any enemy unit | 3 |
| Hit 4 | Spell | 3 | 4 damage to any enemy unit | 3 |

## Files

`node build.mjs` writes `index.html` (and `artifact.html`); `node sim.mjs` runs the gate into `report.json`; `node sanity.mjs` the set positions; `node check.mjs` plays the page headless; `node quick.mjs A B n` a quick head-to-head.
