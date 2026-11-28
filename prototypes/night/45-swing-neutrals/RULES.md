# 45 Swing neutrals

Every number is a placeholder. One rule differs from the spec, the one change the night run allows: a Neutral hits at the **start of its side's next turn**, not at the end of the turn it was pulled (why: `report.json`, key `report`).

- **Neutrals:** a Neutral deck of 12 with attack 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 5, 5, shuffled; 3 are put into three slots. Each slot has a loyalty track from −3 to +3 starting at 0; positive leans to the first seat, negative to the second (on the page: below the middle leans to you, above to him).
- Both players use the same 26-card deck, shuffled. Life 15; bring the other to 0. Random first player; the first draws 3, the second draws 4 and gets the Coin (0 mana: gain 1 mana this turn).
- **Your turn:** (1) each Neutral whose loyalty is on your side (at least 1 toward you) deals its attack to the opponent; (2) your maximum mana goes up by 1 (cap 8) and refills; draw 1 (from an empty deck you lose 1 life, then 2, then 3); (3) play cards by paying their cost. "Toward you" moves a loyalty toward your side; loyalty stays within −3..+3.
- Turn cap 120 turns (a draw); never reached in testing.

| Card | Cost | Text | Copies |
|---|---|---|---|
| Sway 1 | 1 | One Neutral's loyalty 1 toward you. | 5 |
| Sway 2 | 2 | One Neutral's loyalty 2 toward you. | 4 |
| Sway 3 | 4 | One Neutral's loyalty 3 toward you. | 3 |
| Spread | 3 | Every Neutral's loyalty 1 toward you. | 3 |
| Exile | 3 | Remove a Neutral; the next from the Neutral deck takes its slot at loyalty 0. Not playable when the Neutral deck is empty. | 3 |
| Shield | 2 | Prevent the next 4 damage to you. | 3 |
| Rally | 2 | One Neutral loyal to you deals its attack to the opponent now. | 2 |
| Draw 2 | 2 | Draw 2 cards. | 3 |

On the page: tap a Sway, Exile or Rally, then a Neutral's track; other cards play on tap. The gold pile counts the Neutral deck.

## Files

`node build.mjs` writes `index.html` (and `artifact.html`); `node sim.mjs [games] [workers]` runs the gate into `report.json` (`report.asSpecified` holds the run under the spec's end-of-turn hit); `node sanity.mjs` the set positions; `node check.mjs` plays the page headless.
