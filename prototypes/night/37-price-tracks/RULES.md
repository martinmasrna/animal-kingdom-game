# 37 Price tracks

Every number is a placeholder. One rule differs from the spec, the one change the night run allows: reaching 40 ends the match **at the end of that round**, not at once (why: `report.json`, key `report`). The concept is dead either way.

- Three goods, X, Y and Z, each with a shared price from 1 to 9, starting at 4.
- Both players use the same 20-card deck, shuffled, and draw 5. Coin 0 each. Points 0. Random first player.
- **Your turn:** (1) gain 2 coin (cap 6); draw up to 5 cards (shuffle your discard into your deck when needed); (2) in any order: **sell**, once a turn: discard any number of goods cards of one type from your hand, score that good's price times the number sold, then its price drops by the number sold (minimum 1); and play action cards by paying their cost in coin; (3) end the turn and keep the rest of your hand (hand max 8, which never binds: the hand only refills up to 5).
- At the end of each round (after both players' turns) every price rises by 1 (maximum 9).
- **End:** when a player reaches 40 points, the match ends at the end of that round and the higher score wins; equal is a draw. Otherwise after 14 rounds, the higher score wins.

| Card | Cost | Text | Copies |
|---|---|---|---|
| Good X | | Sold for X's price. | 5 |
| Good Y | | Sold for Y's price. | 5 |
| Good Z | | Sold for Z's price. | 5 |
| Boost | 1 | One price +2. | 2 |
| Crash | 2 | One price −3. | 2 |
| Spy | 1 | Look at the opponent's hand. | 1 |

On the page: tap a goods card to take every card of its type (tap again to put one back), then that good's track to sell; tap Boost or Crash, then a track; Spy plays on tap and turns the cards it saw face up while they stay in his hand.

## Files

`node build.mjs` writes `index.html` (and `artifact.html`); `node sim.mjs [games] [workers]` runs the gate into `report.json` (`report.asSpecified` holds the run with the spec's instant win); `node sanity.mjs` the set positions; `node check.mjs` plays the page headless.
