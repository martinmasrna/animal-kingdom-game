# 18 Edge flip grid

Every number here is a placeholder. Borrowed: Triple Triad's flip, where each card has four edge numbers and a placed card takes every adjacent opponent card whose touching edge is lower. The rest is not that game: a 4×4 grid, mana costs, several cards a turn, rotation.

**The question.** When cards cost mana by their edge strength and the grid fills in a few turns, are placement order, rotation and saving strong cards for the last cells real decisions?

## Setup

- An empty 4×4 grid.
- Each player has the same 20-card deck, shuffled. Random first player; the first player draws 4, the second draws 5 and gets the Coin (0 mana: gain 1 mana this turn).

## Turn

1. Your maximum mana goes up by 1 (cap 6) and refills. Draw 1 (empty deck: draw nothing).
2. Place any number of cards, paying each one's cost, on empty cells. A card may be rotated to any of its four orientations as it is placed.
3. When a card is placed, compare each of its edges with the touching edge of every orthogonally adjacent opponent-owned card: where yours is strictly higher, that card flips to your ownership. Flipped cards do not flip anything further. Edges against the grid border do nothing.
4. End the turn. A turn with no placement is a pass.

## End

When all 16 cells are filled, or after both players pass on consecutive turns, the player owning more cells wins; equal is a draw.

## Cards (20, both players)

Edges listed clockwise from the top; rotate freely.

| Card | Cost | Edges | Copies |
|---|---|---|---|
| Point | 1 | 3, 1, 1, 1 | 3 |
| Pair | 1 | 2, 2, 1, 1 | 3 |
| Even | 2 | 2, 2, 2, 2 | 3 |
| Spear | 2 | 4, 1, 2, 1 | 3 |
| Hook | 3 | 4, 3, 1, 1 | 2 |
| Block | 3 | 3, 3, 3, 2 | 2 |
| Lance | 4 | 5, 2, 3, 2 | 2 |
| Crown | 5 | 4, 4, 4, 4 | 2 |

## Builder notes

- Greedy: each placement takes the card, cell and rotation that flips the most cards now (plus one for the cell itself), most expensive first among ties, until it can place nothing.
- Filler (a second trivial bot): places its cheapest cards in cells with no enemy neighbours.
- Set positions: free flip (a cell touching three weak enemy cards and a Crown in hand: place it there); lethal (the last empty cell decides the majority: place the card that wins it); don't waste (never place a Crown where a Point flips the same cards).
