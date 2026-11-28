# 44 Bump placement

Every number is a placeholder.

- Five shared spaces, which pay out in this order at the end of each round: **Score 3** (gain 3 points), **Score 1** (gain 1 point and draw 1), **Study** (draw 2), **Fund** (next round you have 3 more mana), **Sabotage** (the opponent discards a random card from hand).
- Each player has the same 24-card deck, shuffled, and draws 5. A random player starts round 1; the starting player alternates every round. Points start at 0; target 20.
- **A round:** each player draws 3 (more than 8 cards in hand: discard down by choice; the discard pile is shuffled into the deck when needed). Mana 4 each, plus 3 for the player whose card was on Fund last round; unspent mana is lost at the end of the round.
- Starting with the round's first player, players alternate: place one card or pass. A player who has passed places nothing more this round.
- **Place:** pay the card's cost and put it on a space. A space holds one card. If an enemy card of lower strength is there, it returns to its owner's hand (bumped). You cannot place on a space held by your own card or by an enemy card of equal or higher strength.
- When both have passed, each space pays the owner of the card on it, in the order above. Then every placed card goes to its owner's discard pile.
- **End:** at the end of a round, a player on 20 or more wins; both: the higher wins, equal plays another round. After round 12, the higher score wins; equal is a draw.

| Card | Cost | Strength | Text | Copies |
|---|---|---|---|---|
| Worker | 0 | 1 | | 6 |
| Hand | 1 | 2 | | 5 |
| Foreman | 2 | 3 | | 4 |
| Boss | 3 | 4 | | 3 |
| Chief | 5 | 6 | | 2 |
| Lock | 2 | 2 | Cannot be bumped. | 2 |
| Shove | 1 | 1 | When placed, bump an enemy card of strength 3 or less from another space. | 2 |

## Files

`node build.mjs` writes `index.html` (and `artifact.html`); `node sim.mjs` runs the gate into `report.json`; `node sanity.mjs` the set positions; `node check.mjs` plays the page headless; `node quick.mjs A B n` a quick head-to-head; `node trace.mjs seed` prints one Expert mirror game.
