# 45 Swing neutrals

Every number here is a placeholder.

**The question.** When three shared Neutral pieces fight for whichever player holds their loyalty, is the choice between spreading influence and concentrating it a real one?

## Setup

- The Neutral deck: 12 Neutrals with attack 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 5, 5, shuffled; 3 are put into the three slots. Each slot has a loyalty track from −3 to +3 starting at 0; positive leans to player A, negative to player B.
- Each player has the same 26-card deck, shuffled. Life 15.
- Random first player; the first player draws 3, the second draws 4 and gets the Coin (0 mana: gain 1 mana this turn).

## Turn

1. Your maximum mana goes up by 1 (cap 8) and refills. Draw 1. Drawing from an empty deck loses 1 life, then 2, then 3.
2. Play cards by paying their cost. "Toward you" moves a loyalty toward your side; loyalty stays within −3..+3.
3. End of turn: each Neutral whose loyalty is on your side (at least 1 toward you) deals its attack to the opponent.

## End

Life 0 or less loses.

## Cards (26, both players)

| Card | Cost | Text | Copies |
|---|---|---|---|
| Sway 1 | 1 | One Neutral's loyalty 1 toward you. | 5 |
| Sway 2 | 2 | One Neutral's loyalty 2 toward you. | 4 |
| Sway 3 | 4 | One Neutral's loyalty 3 toward you. | 3 |
| Spread | 3 | Every Neutral's loyalty 1 toward you. | 3 |
| Exile | 3 | Remove a Neutral; the next from the Neutral deck takes its slot at loyalty 0. Not playable when the Neutral deck is empty. | 3 |
| Shield | 2 | Prevent the next 4 damage to you. | 3 |
| Rally | 2 | One Neutral loyal to you deals its attack to the opponent now. | 2 |
| Draw 2 | 2 | Draw 2 cards. | 3 |

## Builder notes

- Greedy: spends its mana pulling the highest-attack Neutral onto its side, then the next highest.
- Racer: never plays Exile or Shield.
- Set positions: lethal (the opponent on 4 life, a 4-attack Neutral at loyalty 0 and Sway 1 in hand: play it); don't waste (never Sway a Neutral already at 3 toward you); free swing (a 5-attack Neutral at 1 toward the opponent and Sway 2 in hand: pull it to your side).
