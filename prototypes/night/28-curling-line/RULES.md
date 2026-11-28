# 28 Curling line

Stones on a one-dimensional sheet push the first stone in their path; closest to the Mark scores curling-style; throws are cards bought with energy. Every number is a placeholder.

## The sheet

- Cells 1 to 12. The Mark is cell 9. The House is cells 6 to 12 (distance 3 or less from the Mark).
- A thrown stone starts before cell 1 and slides toward its target cell d.
- If a stone stands on a cell from 1 to d, the first such stone (lowest cell, p) stops the thrown stone on p − 1 and is itself pushed forward by d − p + 1 cells. A pushed stone that meets another stone on its way stops just before it and passes the rest of its push on, the same way. A stone pushed beyond 12, or a thrown stone that would stop on 0, is out.

## Setup

- Each player has the same 14-card deck, shuffled.
- A random player has the hammer (the last throw) in end 1.

## An end

1. Each player discards its hand, draws 5 (shuffle the discard when needed) and has 5 energy for the end.
2. Eight throws, alternating, the player without the hammer first. A throw plays a card (paying its energy) or the basic Lag (free: d = 4).
3. **Score**: only stones in the House count. The owner of the stone closest to the Mark scores one point for each of its House stones strictly closer than the opponent's closest House stone (all of them if the opponent has none in the House). Equally close closest stones, or an empty House: a blank end.
4. After a scoring end, the player who did not score has the hammer. After a blank end, the hammer stays.

## End of the match

After 6 ends, more points wins. Equal: one extra end; still equal, a draw.

## Cards (14, both players)

| Card | Cost | Target | Copies |
|---|---|---|---|
| Guard | 0 | d = 5 | 2 |
| Short | 0 | d = 7 | 2 |
| Draw 8 | 1 | d = 8 | 2 |
| Draw 9 | 2 | d = 9 | 2 |
| Draw 10 | 1 | d = 10 | 2 |
| Hit | 1 | d = 12 | 2 |
| Any | 3 | choose d from 4 to 12 | 2 |

Played cards and discarded hands go face-up to the discard pile.
