# 34 Pitch to pay

Every number is a placeholder. Borrowed from Flesh and Blood: a card spent for resources gives its pitch value and goes under the deck, and the hand refills at the end of each turn. The rest is a plain unit board: no heroes, no blocking.

One number differs from the spec, the one change the night run allows: life is **30**, not 20 (why: `report.json`, key `report`).

- Both players use the same 30-card deck, shuffled. Life 30; bring the other player to 0 (both at once is a draw). Up to 6 units a side. Random first player; the first starts with 4 cards, the second with 5.
- **Start of your turn:** your units become ready. From your 15th turn on you first lose 1 life, then 2 on your 16th, and so on.
- **Paying:** there is no mana. Pitch any card from your hand at any time in your turn: it adds its pitch value to your pool for this turn and goes to the bottom of your deck (in the order pitched). A card is played by paying its cost from the pool. The pool empties at the end of the turn.
- **Units** cannot attack the turn they are played. Each ready unit may attack once: an enemy unit (both deal their attack to each other; damage stays) or the enemy player.
- **End of turn:** draw up to 5 cards. An empty deck shuffles the discard pile in (destroyed units and used Hits go there); with both empty, draw nothing.

| Card | Cost | Attack/Health | Pitch | Copies |
|---|---|---|---|---|
| Pip | 1 | 1/1 | 3 | 6 |
| Striker | 1 | 2/1 | 1 | 3 |
| Raider | 2 | 3/2 | 1 | 3 |
| Guard | 2 | 1/4 | 2 | 3 |
| Line | 3 | 3/4 | 2 | 3 |
| Heavy | 4 | 4/5 | 2 | 3 |
| Big | 6 | 6/7 | 1 | 3 |
| Hit 3 | 2 | 3 damage to a unit or player | 2 | 3 |
| Hit 5 | 4 | 5 damage to a unit or player | 1 | 3 |

On the page: tap a card, then the gold pool to pitch it, your half of the board to play a unit, or a target for a Hit. Tap a ready unit, then its target.

## Files

`node build.mjs` writes `index.html` (and `artifact.html`); `node sim.mjs [games] [workers]` runs the gate into `report.json`; `node sanity.mjs` the set positions; `node check.mjs` plays the page headless.
