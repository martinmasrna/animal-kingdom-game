# 07 Blind fronts

Every number here is a placeholder.

**The question.** When players commit cards face-down to three fronts in turn and energy can be banked between rounds, does reading the opponent's commitments beat any fixed spread?

## Setup

- Each player has the same 25-card deck, shuffled, and draws 5. Energy 4 each (bank cap 10).
- A random player is the first player of round 1; the first player alternates every round.
- Points start at 0. Target: 12.

## A round

1. Both gain 4 energy (cap 10) and draw 2 (hand max 8: discard down by choice). Shuffle the discard into the deck when needed.
2. The three fronts get the values 1, 2 and 3 in a random order, shown.
3. **Placement.** Starting with the round's first player, players alternate: place one card face-down at a front, paying its cost, or pass. A player who has passed places nothing more this round. Both players see how many face-down cards sit at each front and how much energy each has left.
4. When both have passed, reveal everything. At each front, the higher total strength (after card texts) wins the front's value in points; equal: nobody.
5. All placed cards go to their owners' discard piles.

## End

After a round in which a player reaches 12 points, the higher score wins; equal scores play another round. After round 12, the higher score wins; equal is a draw.

## Cards (25, both players)

| Card | Cost | Strength | Text | Copies |
|---|---|---|---|---|
| Feint | 0 | 0 | | 3 |
| Scout | 0 | 1 | | 3 |
| Troop | 1 | 2 | | 4 |
| Squad | 2 | 4 | | 4 |
| Elite | 3 | 5 | | 3 |
| Heavy | 4 | 7 | | 2 |
| Lone | 2 | 3 | +3 if it is your only card at its front. | 3 |
| Mass | 1 | 1 | +1 for each other card of yours at its front. | 3 |

## Builder notes

- Hidden information: the Expert determinizes the opponent's face-down cards from the unseen part of the known deck list and never reads them.
- Greedy: places its highest-strength affordable card at the 3-front, then the 2-front, then the 1-front, passing when it can place nothing.
- The first-player check reads the first player of round 1.
- Set positions: free front (the opponent has passed with nothing at the 1-front and you hold a Scout: place it there); don't waste (the opponent has passed with nothing at a front: win it with your cheapest card, never a Heavy); lethal (at 10 points, the opponent has passed with no energy left and nothing at the 2-front: place there).
