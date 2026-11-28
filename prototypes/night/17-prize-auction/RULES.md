# 17 Prize auction

Every number is a placeholder.

- Each player starts with the same 8 coin cards (Coin 1 ×6, Coin 2 ×2), shuffled; draw 5. The 16 prizes (below) are shuffled into a prize deck.
- **A round:** both draw 2 (an empty deck reshuffles its discard; Messenger draws one more when drawn). Over 7 cards in hand: discard down to 7, by choice. The top prize is revealed; the one after it is shown face-up.
- **Bid:** both secretly choose any cards from hand, possibly none; reveal. A bid's value is the total coin on its cards. The higher bid takes the prize: its bid cards go to its discard, and the prize goes to its discard (from then on it is drawn like any card). The lower bidder takes its bid back.
- **Equal bids** (0 against 0 too): both take their bids back, nobody takes the prize, it stays, and next round the next prize joins it; the winner then takes both.
- **Debt** goes the other way: when Debt is among the prizes up, the lower bidder takes everything up, and every bid returns to hand.
- **End:** after the 16th prize is resolved (a prize still up then is discarded), the player owning more points wins (Debt counts −3); if equal, more total coin owned; if still equal, a draw.

| Prize | Coin | Points | Copies |
|---|---|---|---|
| Coin 3 | 3 | 0 | 4 |
| Coin 2 | 2 | 0 | 3 |
| Messenger (when drawn, draw 1 more) | 1 | 0 | 2 |
| Point 2 | 0 | 2 | 3 |
| Point 3 | 0 | 3 | 2 |
| Point 5 | 0 | 5 | 1 |
| Debt (the lower bidder takes it) | 0 | −3 | 1 |

Hand, deck and discard sizes are public, and so is everything each player has won; the order of a deck and which of its cards sit in hand are not.

## Files

`node build.mjs` writes `index.html` (and `artifact.html`); `node sim.mjs` runs the gate into `report.json`; `node sanity.mjs` the set positions; `node check.mjs` plays the page headless.
