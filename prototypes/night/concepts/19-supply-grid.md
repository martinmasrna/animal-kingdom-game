# 19 Supply grid

Every number here is a placeholder.

**The question.** When pieces can only grow from a chain connected to your Base and cut-off pieces die, does the shape of your network (cutting the opponent's lines, protecting your own) become the game?

## Setup

- A 5×5 grid. Player A's Base is on row 1, column 3; player B's Base on row 5, column 3. A Base has power 3, never moves, and can strike.
- Each player has the same 24-card deck, shuffled. Random first player; the first player draws 3, the second draws 4 and gets the Coin (0 mana: gain 1 mana this turn).

## Turn

1. Your maximum mana goes up by 1 (cap 8) and refills. Draw 1 (empty deck: draw nothing).
2. In any order:
   - **Place** a unit by paying its cost, on an empty cell orthogonally next to one of your supplied pieces. A piece is supplied when a chain of your own pieces, cell to orthogonal cell, connects it to your Base.
   - **Strike**: each of your pieces, the Base and units placed this turn included, may strike once per turn at an orthogonally adjacent enemy piece. The lower power is destroyed; equal power destroys both. A Wall cannot strike.
   - Play a spell.
3. After every placement, strike or spell, remove every piece (yours and the opponent's) that is no longer supplied.
4. End the turn.

## End

- A player whose Base is destroyed loses; both Bases destroyed at once is a draw.
- After round 12 (each player has had 12 turns), the player with more pieces on the grid, Base included, wins; equal is a draw.

## Cards

| Card | Cost | Power | Text | Copies |
|---|---|---|---|---|
| Post | 1 | 1 | | 5 |
| Line | 2 | 2 | | 5 |
| Squad | 3 | 3 | | 4 |
| Heavy | 4 | 4 | | 3 |
| Big | 6 | 6 | | 2 |
| Wall | 2 | 3 | Cannot strike. | 3 |
| Cut | 2 | | Spell: destroy an enemy unit with power 2 or less. | 2 |

## Builder notes

- Greedy: place the most expensive affordable unit on a cell next to an enemy piece it beats (else the cell closest to the enemy Base), then make every strike that destroys an enemy piece without losing the striker.
- Racer: grows a straight chain toward the enemy Base and strikes the Base whenever it can win the strike.
- Set positions: lethal (your Heavy stands next to the enemy Base: strike it); cut (one enemy piece is the only link to three others: destroy it); don't waste (never strike a piece of higher power).
