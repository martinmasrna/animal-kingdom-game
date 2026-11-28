# 17 Prize auction

Every number here is a placeholder.

**The question.** When your deck is your money, and each prize either improves your money or scores points that clog your deck, does every sealed bid carry a real choice?

## Setup

- Each player's starting deck (8 cards): Coin 1 ×6, Coin 2 ×2. Shuffle; draw 5.
- The prize deck (16 prizes, list below) is shuffled.

## A round

1. Each player draws 2 (shuffle the discard when the deck is empty). Hand max 7: discard down to 7 by choice.
2. Reveal the top prize. The prize after it is also shown face-up.
3. **Bid**: both players secretly choose any number of cards from hand, possibly none. Reveal. A bid's value is the total coin on its cards.
4. The higher bid wins: the winner's bid cards go to its discard, and the prize goes to the winner's discard. The lower bidder takes its bid back into hand.
5. Equal bids, 0 against 0 included: both take their bids back, nobody wins, and the prize stays; next round the next prize joins it and the winner takes both.
6. **Debt** goes the other way: when Debt is among the prizes, the lower bidder takes it (along with any other prize in the pot); all bids return to hand.

Prizes in your deck are drawn and bid like any other card; point prizes carry no coin.

## End

After the last prize is resolved (a prize still carried over at the end is discarded), each player totals the points on every prize it owns, wherever the card is. Higher wins; if equal, the higher total coin value owned wins; if still equal, a draw.

## Prizes (16)

| Prize | Coin | Points | Text | Copies |
|---|---|---|---|---|
| Coin 3 | 3 | 0 | | 4 |
| Coin 2 | 2 | 0 | | 3 |
| Messenger | 1 | 0 | When you draw it, draw 1 more. | 2 |
| Point 2 | 0 | 2 | | 3 |
| Point 3 | 0 | 3 | | 2 |
| Point 5 | 0 | 5 | | 1 |
| Debt | 0 | −3 | The lower bidder takes it. | 1 |

## Builder notes

- Greedy: bids all the coin in hand on point prizes, half its coin (rounded down) on coin prizes, nothing on Debt.
- The first-player check: there is no turn order; report seat A's win rate.
- Set positions: don't overpay (the opponent's hand is empty: bid exactly 1); never bid on Debt alone; lethal (the last prize decides the game and your hand's coin exceeds the opponent's largest possible bid, 3 × their hand size: bid enough to be sure).
