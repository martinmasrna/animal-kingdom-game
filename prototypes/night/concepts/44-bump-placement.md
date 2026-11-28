# 44 Bump placement

Every number here is a placeholder.

**The question.** When a stronger card can bump a weaker one off a shared action space, does choosing which card to commit where, and when to bump, make the game?

## Setup

- Five shared spaces, which activate in this order at the end of each round: **Score 3** (gain 3 points), **Score 1** (gain 1 point and draw 1), **Study** (draw 2), **Fund** (next round you have 3 more mana), **Sabotage** (the opponent discards a random card from hand).
- Each player has the same 24-card deck, shuffled, and draws 5.
- A random player is the first player of round 1; the first player alternates every round.
- Points start at 0. Target: 20.

## A round

1. Each player draws 3 (hand max 8: discard down by choice; shuffle the discard into the deck when needed). Mana 4 each, plus 3 for the player whose card was on Fund last round. Unspent mana is lost at the end of the round.
2. Starting with the first player, players alternate: place one card or pass. A player who has passed places nothing more this round.
3. **Place**: pay the card's cost and put it on a space. A space holds one card. If an enemy card of lower strength is there, it returns to its owner's hand (bumped). You cannot place on a space held by your own card or by an enemy card of equal or higher strength.
4. When both have passed, each space activates for the owner of the card on it, in the order above. Then every placed card goes to its owner's discard pile.

## End

At the end of a round, a player on 20 or more wins; both: the higher wins, equal plays another round. After round 12, the higher score wins; equal is a draw.

## Cards (24, both players)

| Card | Cost | Strength | Text | Copies |
|---|---|---|---|---|
| Worker | 0 | 1 | | 6 |
| Hand | 1 | 2 | | 5 |
| Foreman | 2 | 3 | | 4 |
| Boss | 3 | 4 | | 3 |
| Chief | 5 | 6 | | 2 |
| Lock | 2 | 2 | Cannot be bumped. | 2 |
| Shove | 1 | 1 | When placed, bump an enemy card of strength 3 or less from another space. | 2 |

## Builder notes

- Greedy: places its strongest affordable card on the best space it can take, in the order Score 3, Study, Score 1, Fund, Sabotage; passes when it can place nothing.
- The first-player check reads the first player of round 1.
- Set positions: lethal (on 17 points, Score 3 held by an enemy Worker and a Hand in hand with 1 mana: bump it); free bump (an enemy Worker on Score 3 and a Hand in hand: take it); don't waste (the opponent has passed: take an open space with your cheapest card, never a Chief).
