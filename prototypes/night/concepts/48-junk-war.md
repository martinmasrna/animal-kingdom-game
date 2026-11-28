# 48 Junk war

Every number here is a placeholder.

**The question.** In a deckbuilder where points are scored by playing cards and the main attack is pushing junk into the opponent's deck, does polluting pay as well as building?

## Setup

- Each player's starting deck: Coin ×7 (+1 coin), Score ×3 (+1 point). Shuffle.
- The market deck (40 cards, list below) is shuffled; 5 cards lie face-up as the row, refilled at once when one is bought.
- A shared Junk pile of 30 Junk cards (Junk does nothing).
- Random first player. The first player's first hand is 3 cards; every other hand is 5. Points start at 0. Target: 25.

## Turn

1. **Play** every card in your hand, in an order you choose. Coin adds to this turn's pool; points are added to your total at once; effects resolve.
2. **Buy** any number of row cards with coin; each goes to your discard pile.
3. Discard everything played and left over; draw 5 (shuffle your discard into a new deck when needed).

Junk sent to the opponent comes from the shared pile; when the pile is empty, Junk effects do nothing. Removed cards leave the game.

## End

- Reaching 25 points wins at once.
- When the market deck runs out, finish the round (both players have had the same number of turns); the higher score wins; equal is a draw.

## Market (40 cards)

| Card | Cost | Text | Copies |
|---|---|---|---|
| Coin 2 | 3 | +2 coin | 6 |
| Coin 3 | 6 | +3 coin | 4 |
| Score 2 | 4 | +2 points | 5 |
| Score 4 | 8 | +4 points | 3 |
| Draw | 3 | Draw 2 cards and play them | 4 |
| Foul | 3 | +1 coin; put a Junk on top of the opponent's deck | 5 |
| Foul 2 | 5 | +1 point; put 2 Junk into the opponent's discard pile | 3 |
| Purge | 3 | Remove up to 2 other cards in your hand from the game | 4 |
| Clean | 2 | +1 coin; remove a Junk from your hand or discard pile from the game | 4 |
| Thief | 5 | +2 coin; take 1 point from the opponent | 2 |

## Builder notes

- Greedy: buys the most expensive affordable card, repeating until it can buy nothing; Purge removes Junk first, then Coin.
- Racer: never buys Foul, Foul 2 or Thief.
- Set positions: don't waste (8 coin and a Score 4 in the row: don't end the buy with nothing); free clean (Purge in hand with two Junk: remove both Junk, not a Coin); lethal buy (on 22 points with 8 coin, a Score 4 in the row and the Junk pile empty, so the opponent cannot slow you: buy it, not Coin 3).
