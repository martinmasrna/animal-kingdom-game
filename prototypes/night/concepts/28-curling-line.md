# 28 Curling line

Every number here is a placeholder. Borrowed: curling's scoring, where the side with the stone closest to the mark scores one point for each of its stones closer than the opponent's closest, the side that scored throws first in the next end, and an end with no score keeps the last throw where it was. The rest is not that game: one dimension, throws bought with energy from a deck.

**The question.** In one dimension, with throws priced by how precise they are, is the choice between guarding, drawing to the mark and knocking stones out a real decision on every throw?

## The sheet

- Cells 1 to 12. The Mark is cell 9. The House is cells 6 to 12 (distance 3 or less from the Mark).
- A thrown stone starts before cell 1 and slides toward its target cell d.
- If a stone already stands on a cell from 1 to d, the first such stone (lowest cell, p) stops the thrown stone on p − 1, and is itself pushed forward by d − p + 1 cells. A pushed stone that meets another stone on its way stops just before it and passes the rest of its push on, the same way. A stone pushed beyond 12, or a thrown stone that would stop on 0, is out.

## Setup

- Each player has the same 14-card deck, shuffled.
- A random player has the hammer (the last throw) in end 1.

## An end

1. Each player discards its hand, draws 5 (shuffle the discard when needed) and has 5 energy for the end.
2. Eight throws, alternating, the player without the hammer first. A throw plays a card (paying its energy) or the basic Lag (free: d = 4).
3. **Score**: only stones in the House count. The owner of the stone closest to the Mark scores one point for each of its House stones strictly closer than the opponent's closest House stone (all of them if the opponent has none in the House). If the closest stones of both players are equally close, or the House is empty, the end is blank.
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
| Any | 3 | Choose d from 4 to 12 | 2 |

## Builder notes

- Greedy: each throw takes the card and target that leave it the best score if the end stopped now, cheapest among ties.
- The first-player check reads the player with the hammer in end 1.
- Set positions: free takeout (last throw, the opponent's only stone on 9 with an empty path, Hit and Draw 9 in hand: Hit stops your stone on 8 and pushes theirs 4 cells, out, scoring 1, where Draw 9 would only push it to 10 for a blank); don't waste (never use Any for a target a cheaper card in hand reaches); lethal (last throw of the last end, one point needed and a clear path: draw to the Mark).
