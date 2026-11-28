# 09 Momentum rope

Every number here is a placeholder.

**The question.** With no units at all, can a shared marker that has a velocity (pushes that keep moving it every turn) carry a game of timing: build momentum now, or shove now?

## Setup

- A track from −8 to +8 with a marker on 0, and a velocity from −4 to +4 starting at 0. Player A wins at +8, player B at −8. "Forward" always means toward the opponent's end.
- Each player has the same 26-card deck, shuffled. Random first player; the first player draws 3, the second draws 4 and gets the Coin (0 mana: gain 1 mana this turn).

## Turn

1. Your maximum mana goes up by 1 (cap 8) and refills. Draw 1. Drawing from an empty deck moves the marker 1 toward your own end.
2. Play cards by paying their cost.
3. End of turn: the marker moves by the velocity (velocity +2 moves it 2 toward B's end, and so on). It stops at an end.

The marker moves at the end of every turn, both players' turns. Velocity is clamped to −4..+4.

## End

- The marker reaching the opponent's end wins at once, at any moment.
- After 12 rounds (12 turns each): marker above 0, A wins; below 0, B wins. On exactly 0, the player the velocity points toward loses; with velocity 0 too, it is a draw.

## Cards (26, both players)

| Card | Cost | Text | Copies |
|---|---|---|---|
| Shove | 1 | Marker 1 forward now. | 3 |
| Jolt | 2 | Marker 2 forward now. | 3 |
| Heave | 2 | Velocity 1 forward. | 4 |
| Big Heave | 4 | Velocity 2 forward. | 3 |
| Check | 3 | Velocity becomes 0. | 3 |
| Reverse | 5 | Velocity changes sign. | 2 |
| Anchor | 2 | Until your next turn begins, the marker cannot move toward your end. | 3 |
| Surge | 3 | The marker moves by the velocity now (an extra move). | 2 |
| Draw 2 | 2 | Draw 2 cards. | 3 |

## Builder notes

- Greedy: chooses the plays that maximise (marker position + 2 × velocity), both measured forward, at the end of its turn, spending the most mana among ties.
- Racer: only Shove, Jolt, Heave, Big Heave and Surge.
- Set positions: lethal (marker 6 forward, Jolt in hand and 2 mana: Jolt wins); don't waste (never Check at velocity 0, never Anchor when nothing can move the marker toward you); free swing (velocity is 3 toward you and you have 5 mana and Reverse: Reverse).
