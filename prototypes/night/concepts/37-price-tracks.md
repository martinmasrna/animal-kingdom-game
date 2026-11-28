# 37 Price tracks

Every number here is a placeholder.

**The question.** When the goods in your deck are worth whatever the shared prices say, and both players can push or crash a price, does guessing what the opponent holds drive the game?

## Setup

- Three goods, X, Y and Z, each with a shared price from 1 to 9, starting at 4.
- Each player has the same 20-card deck, shuffled, and draws 5. Coin 0 each.
- Random first player. Points start at 0. Target: 40.

## Turn

1. Gain 2 coin (cap 6). Draw up to 5 cards (shuffle the discard into the deck when needed).
2. In any order:
   - **Sell**, once per turn: discard any number of goods cards of one type from your hand. Score that good's price times the number sold; then its price drops by the number sold (minimum 1).
   - Play action cards by paying their cost in coin.
3. End the turn. You keep the rest of your hand (hand max 8 at the end of the turn: discard down by choice).

At the end of each round (after both players' turns), every price rises by 1 (maximum 9).

## End

Reaching 40 points wins at once. After 14 rounds, the higher score wins; equal is a draw.

## Cards (20, both players)

| Card | Cost | Text | Copies |
|---|---|---|---|
| Good X | | Sold for X's price. | 5 |
| Good Y | | Sold for Y's price. | 5 |
| Good Z | | Sold for Z's price. | 5 |
| Boost | 1 | One price +2. | 2 |
| Crash | 2 | One price −3. | 2 |
| Spy | 1 | Look at the opponent's hand. | 1 |

## Builder notes

- Hidden information: the Expert determinizes the opponent's hand from the cards not yet seen and never reads it (Spy shows it legally).
- Greedy: every turn sells the type with the highest price times count in hand; Boosts that type first if it can.
- Racer: sells every turn and never plays Crash.
- Set positions: lethal (on 32 points with two Good Z in hand and Z at price 4: sell them); don't waste (never Boost a good you hold none of and do not sell this turn); free crash (Spy has shown the opponent holding four Good Z, you hold none and have 2 coin: Crash Z).
