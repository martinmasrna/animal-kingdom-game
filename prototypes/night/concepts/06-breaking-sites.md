# 06 Breaking sites

Every number here is a placeholder. Borrowed: Smash Up's breakpoint, where a base scores as soon as the total power on it reaches its threshold and the winner and runner-up take printed points. The rest is not that game: two players, one shared deck list, mana costs.

**The question.** When a site scores the moment total power reaches its threshold, is choosing where to commit power, and when to push a site over, a real decision?

## Setup

- The site deck: 10 sites (list below), shuffled; 3 are laid face-up.
- Each player has the same 30-card deck, shuffled. Random first player; the first player draws 3, the second draws 4 and gets the Coin (0 mana: gain 1 mana this turn).
- Points start at 0. Target: 15.

## Turn

1. Your maximum mana goes up by 1 (cap 10) and refills. Draw 1. Drawing from an empty deck gives the opponent 1 point.
2. Play cards by paying their cost. A unit goes onto your side of any site (max 4 of your units per site).
3. After every card, check each site: if the total power on it, both sides together, is at least its threshold, it **breaks**. The side with more power there takes the Winner points; the other side takes the Runner-up points if it has at least one unit there. A tie gives both sides the Runner-up points. Every unit on that site goes to its owner's discard pile, and the next site from the site deck replaces it. If several sites break at once, the player whose turn it is chooses the order.
4. End the turn.

## End

- The first player to reach 15 points wins at once.
- If the site deck is empty and every site in play has broken, the higher score wins; equal is a draw.

## Sites

| Threshold | Winner | Runner-up | Copies |
|---|---|---|---|
| 8 | 3 | 1 | 1 |
| 9 | 3 | 1 | 1 |
| 10 | 4 | 1 | 1 |
| 10 | 4 | 2 | 1 |
| 11 | 4 | 2 | 1 |
| 12 | 5 | 2 | 2 |
| 13 | 5 | 3 | 1 |
| 14 | 6 | 3 | 1 |
| 15 | 6 | 3 | 1 |

## Cards (30, both players)

| Card | Cost | Power | Text | Copies |
|---|---|---|---|---|
| Pawn | 1 | 1 | | 5 |
| Squad | 2 | 3 | | 5 |
| Force | 3 | 4 | | 3 |
| Heavy | 4 | 6 | | 3 |
| Big | 5 | 7 | | 3 |
| Move | 1 | | Move one of your units to another site. | 3 |
| Strike | 2 | | Destroy an enemy unit with power 3 or less. | 3 |
| Boost | 2 | | One of your units gets +3 power for the rest of the game. | 3 |
| Draw 2 | 2 | | Draw 2 cards. | 2 |

## Builder notes

- Greedy: play the most expensive affordable unit at the site where it creates or widens your lead most, never breaking a site it would lose; use Strike on the biggest enemy unit it can destroy.
- Racer: always plays at the site with the highest Winner points, ignoring the opponent's power there.
- Set positions: lethal (at 12 points you lead a Winner-3 site 6 to 3 with threshold 10: a Pawn breaks it and wins); don't break a site you are losing; free Strike (the opponent's only unit at a site you contest has power 3: destroy it).
