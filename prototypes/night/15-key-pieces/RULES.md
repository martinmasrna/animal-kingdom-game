# 15 Key pieces

Every number is a placeholder.

- Both players use the same 30-card deck, shuffled. There is no life total. Up to 6 pieces a side (Keys count). Random first player; the first draws 3, the second draws 4 and gets the Coin (0 mana: gain 1 mana this turn).
- **Your turn:** (1) if you control Key A, Key B and Key C, you win; (2) your maximum mana goes up by 1 (cap 10) and refills, your units become ready, you draw 1; a player who must draw from an empty deck loses; (3) play cards by paying their cost; a unit cannot attack the turn it is played; Keys are pieces with 0 attack that never attack; (4) each ready unit may attack an enemy unit or Key once: both deal their attack to each other (a Key deals 0); damage stays; a piece at 0 health or less is destroyed. While the defender controls a Guard, attacks must target a Guard. Hits ignore Guard.
- Turn cap 120 turns (a draw); never reached in testing.

| Card | Cost | Attack/Health | Text | Copies |
|---|---|---|---|---|
| Key A | 2 | 0/3 | Key. | 2 |
| Key B | 3 | 0/4 | Key. | 2 |
| Key C | 4 | 0/5 | Key. | 2 |
| Fetch | 2 | | Put a Key of your choice from your deck into your hand. | 2 |
| Striker | 1 | 2/1 | | 3 |
| Raider | 2 | 3/2 | | 3 |
| Guard | 2 | 1/4 | Guard. | 3 |
| Line | 3 | 3/4 | | 3 |
| Heavy | 4 | 4/4 | | 3 |
| Wall | 4 | 2/7 | Guard. | 2 |
| Hit 3 | 2 | | 3 damage to a unit or Key. | 3 |
| Hit 5 | 4 | | 5 damage to a unit or Key. | 2 |

On the page: tap a unit or Key card to play it; a Hit, then its target; a Fetch, then the Key to take. Tap a ready unit, then its target. The row of A, B, C under each board lights the Keys that side holds.

## Files

`node build.mjs` writes `index.html` (and `artifact.html`); `node sim.mjs [games] [workers]` runs the gate into `report.json`; `node sanity.mjs` the set positions; `node check.mjs` plays the page headless.
