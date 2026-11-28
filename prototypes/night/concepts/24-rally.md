# 24 Rally

Every number here is a placeholder.

**The question.** When returning a shot needs reach at least its pace and every shot costs stamina, is choosing the pace of your return, and what to save, a real decision?

## Setup

- Each player has the same 20-card deck of shots, shuffled, and draws 5. A shot card has a Pace and a Reach.
- A random player serves the first game; the server alternates every game.

## A point

1. The server plays any shot, paying its stamina cost.
2. Players then alternate: each must answer the last shot with a card whose Reach is at least that shot's Pace, paying its cost. A player who cannot, or will not, loses the point.
3. After the point, both players discard the cards they played and draw back up to 5 (shuffle the discard when needed).

Stamina: 10 each at the start of every game; it carries from point to point within the game.

## Scoring

A game is won by the first player to 4 points. The match is won by the first player to 3 games.

## Cards (20, both players)

| Card | Cost | Pace | Reach | Copies |
|---|---|---|---|---|
| Push | 0 | 1 | 2 | 4 |
| Drive | 1 | 3 | 3 | 4 |
| Slice | 1 | 2 | 4 | 3 |
| Lob | 1 | 2 | 5 | 2 |
| Dig | 2 | 1 | 6 | 2 |
| Smash | 3 | 5 | 3 | 3 |
| Ace | 4 | 6 | 2 | 2 |

## Builder notes

- Greedy: serves and returns with the highest-Pace card it can legally play and afford.
- The first-player check reads the server of game 1.
- Set positions: free point (the opponent has 0 stamina, so only Push, Reach 2, is payable: serve with Pace 3 or more); lethal (match point with the same opponent state: do the same); don't waste (answering a Pace 1 shot with Push and Dig as the only legal returns: both send back Pace 1, so play Push, which is free).
