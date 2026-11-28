# 39 Commander grid

Every number here is a placeholder.

**The question.** When the only target is a Commander that fights too, and units must deploy next to it on a small grid, does positioning (shield it or strike with it) carry the game?

## Setup

- A grid of 5 columns and 6 rows. Player A's Commander on row 1, column 3; player B's on row 6, column 3. A Commander has attack 2 and health 15.
- Each player has the same 24-card deck, shuffled. Random first player; the first player draws 3, the second draws 4 and gets the Coin (0 mana: gain 1 mana this turn).

## Turn

1. Your maximum mana goes up by 1 (cap 8) and refills. Draw 1 (empty deck: draw nothing). From round 15 on, your Commander first takes 1 damage, 2 in round 16, and so on.
2. Play cards by paying their cost. A unit goes onto an empty cell orthogonally next to your Commander.
3. Each of your pieces (the Commander included, units played this turn excluded) may take one action:
   - **Move** 1 cell orthogonally to an empty cell (Line: up to 2).
   - **Attack** an orthogonally adjacent enemy piece: both deal their attack to each other.
4. End the turn.

Damage stays; a unit at 0 health or less is removed.

## End

A Commander at 0 health loses the game for its owner; both at once is a draw.

## Cards (24, both players)

| Card | Cost | Attack/Health | Text | Copies |
|---|---|---|---|---|
| Pawn | 1 | 1/2 | | 4 |
| Raider | 2 | 3/2 | | 4 |
| Guard | 2 | 1/5 | | 3 |
| Line | 3 | 3/3 | Moves up to 2. | 3 |
| Heavy | 4 | 4/5 | | 3 |
| Lancer | 4 | 3/3 | Attacks a piece exactly 2 cells away in a straight line, whatever stands between; takes nothing back. It cannot attack adjacent pieces. | 2 |
| Hit 3 | 2 | | 3 damage to an enemy piece within 2 cells (counted orthogonally) of your Commander. | 3 |
| Rally | 1 | | One of your pieces that has already acted this turn may act again. | 2 |

## Builder notes

- Greedy: plays the most expensive affordable cards; each piece attacks if it hits the enemy Commander or destroys a piece and survives, otherwise moves toward the enemy Commander.
- Racer: every piece moves toward and attacks the enemy Commander; nothing defends.
- Set positions: lethal (the enemy Commander on 3 health next to your ready Raider: attack it); free trade (your ready Heavy next to an enemy Pawn: attack it); don't waste (never Hit 3 a unit with 1 health while a Pawn next to it can attack it for free).
