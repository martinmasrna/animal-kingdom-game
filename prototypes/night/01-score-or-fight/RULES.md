# Score or Fight

Two players, the same 30-card deck each. No hero, no life total. First to 40 points wins.

- **Start.** Random first player. The first player draws 3 cards; the second draws 4 and also gets the Coin (0 mana: +1 mana this turn).
- **Turn.** Your maximum mana goes up by 1 (cap 10) and refills; your units become ready; draw 1. An empty deck gives the opponent 2 points, then 4, then 6, and so on.
- **Play** cards by paying their cost. A unit enters your board (max 6) and cannot act this turn. A Hit card deals its damage to an enemy unit.
- **Act.** Each ready unit does one thing, then is spent until your next turn:
  - **Attack** an enemy unit (spent or not): both deal their attack to each other. Damage stays; a unit at 0 health is destroyed.
  - **Score**: add its current health to your points.
- **End.** The moment a player reaches 40 points (by scoring or by the opponent's empty deck), that player wins. A game that reaches turn 80 is a draw.

## Cards (3 copies each)

| Card | Cost | Attack/Health or effect |
|---|---|---|
| Striker | 1 | 2/1 |
| Raider | 2 | 3/2 |
| Guard | 2 | 2/3 |
| Line | 3 | 3/4 |
| Heavy | 4 | 4/5 |
| Big | 5 | 5/5 |
| Huge | 6 | 6/7 |
| Hit 2 | 1 | 2 damage to an enemy unit |
| Hit 3 | 2 | 3 damage to an enemy unit |
| Hit 6 | 4 | 6 damage to an enemy unit |

The spec says Hit cards hit "any unit"; the build lets them hit enemy units only, since hitting your own unit never helps here.

## Files

`node build.mjs` writes `index.html` (and `artifact.html`): you against Expert, first player alternating. `node sim.mjs` runs the gate and writes `report.json`; `node sanity.mjs` the set positions; `node check.mjs` plays whole games through the page's calls in node and by clicks in Chrome.
