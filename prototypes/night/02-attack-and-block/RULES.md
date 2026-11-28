# 02 Attack and block

Every number is a placeholder. Borrowed from Magic: attacking exhausts a unit until its controller's next turn, the defender chooses the blocks, damage on surviving units wears off at end of turn.

- Life 20 each; reduce the other to 0. Both play the same 30-card deck. Random first player; the first draws 3, the second draws 4 and gets the Coin (0 mana: +1 mana this turn). Max 6 units a side.
- **Your turn:** ready your units; your maximum mana goes up by 1 (cap 10) and refills; draw 1 (from an empty deck you lose 1 life, then 2, then 3). Play cards by paying their cost, before and after your attack. A unit can't attack the turn it is played, but it can block on the opponent's next turn.
- **Attack, once a turn:** choose any of your ready units not played this turn. They become exhausted and stay so until your next turn begins, so they cannot block on the opponent's turn.
- **Block:** the defender gives each attacker at most one of its ready (not exhausted) units, each blocking one attacker. A blocked attacker and its blocker deal their attack to each other; an unblocked attacker deals its attack to the defender's life. Damage at least a unit's health destroys it.
- **End of turn:** every surviving unit on both sides heals fully (spell damage too).
- Turn cap 120 turns (a draw); never reached in testing.

| Card | Cost | Attack/Health or effect | Copies |
|---|---|---|---|
| Striker | 1 | 2/1 | 3 |
| Raider | 2 | 3/2 | 3 |
| Wall | 2 | 0/5 | 3 |
| Line | 3 | 3/3 | 3 |
| Heavy | 4 | 4/4 | 3 |
| Big | 5 | 5/5 | 3 |
| Huge | 6 | 6/6 | 3 |
| Hit 2 | 1 | 2 damage to an enemy unit | 3 |
| Hit 4 | 3 | 4 damage to an enemy unit | 3 |
| Draw 2 | 2 | draw 2 cards | 3 |

## Files

`node build.mjs` writes `index.html` (and `artifact.html`); `node sim.mjs` runs the gate into `report.json`; `node sanity.mjs` the set positions; `node check.mjs` plays the page headless.
