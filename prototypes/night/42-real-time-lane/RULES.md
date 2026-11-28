# 42 Real-time lane

Every number is a placeholder. Borrowed from Clash Royale: mana that refills in real time, and an eight-card deck cycling through a hand of four.

- One lane from your base (position 0) to the other base (12). Base health 20 each.
- Both players have the same 8 cards (one of each below), shuffled into a queue: the first 4 are the hand, the 5th is shown as next. A played card goes to the back of the queue and the next one enters the hand.
- Mana starts at 5 and both gain 1 every 2 seconds (cap 10). The match is 3 minutes, in ticks of half a second.
- **Each tick:** mana; each player may play one card from hand by paying its cost; every unit acts: if an enemy unit, an enemy Wall or the enemy base is within its range ahead, it deals its attack to the nearest one, otherwise it moves forward by its speed, never past the nearest enemy unit or Wall; all damage of the tick lands at once and anything at 0 health is removed.
- Units appear at their owner's base and walk toward the enemy base. A Wall is placed anywhere in its owner's half and does not move; enemy units stop at it. Blast hits at once: 8 damage to every enemy unit within 1.5 of the chosen spot.
- **End:** a base at 0 loses (both on the same tick: a draw). At 3:00 the higher base health wins; if level, one more minute in which the first base damage decides; still level, a draw.

| Card | Cost | Health | Attack per tick | Speed per tick | Range |
|---|---|---|---|---|---|
| Runner | 2 | 4 | 1 | 1.0 | 0.5 |
| Grunt | 3 | 10 | 2 | 0.5 | 0.5 |
| Shooter | 3 | 4 | 1 | 0.5 | 3 |
| Brute | 4 | 14 | 3 | 0.4 | 0.5 |
| Tank | 5 | 30 | 1 | 0.3 | 0.5 |
| Swarm | 3 | three units of 2 | 1 each | 0.8 | 0.5 |
| Blast | 3 | 8 damage to enemy units within 1.5 of a chosen spot | | | |
| Wall | 4 | 20 | 0 | 0 | |

Prototype choices the spec left open: units cannot walk into the base cells (they stop at 0.5 / 11.5, which is in range of the base); two fronts that would walk through each other in the same tick meet halfway; Blast hits Walls too; both players' mana is shown (it is countable from the plays anyway); bots decide once a second.

## Files

`node build.mjs` writes `index.html` (and `artifact.html`); `node sim.mjs` runs the gate into `report.json`; `node sanity.mjs` the set positions; `node check.mjs` plays the page headless.
