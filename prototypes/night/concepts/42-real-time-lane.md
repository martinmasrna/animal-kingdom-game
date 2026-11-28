# 42 Real-time lane

Every number here is a placeholder. Borrowed: Clash Royale's elixir flow and card cycle, where a resource refills in real time and an eight-card deck cycles through a hand of four, a played card returning after the other cards are played. The rest is not that game: one lane, two bases, a different card set.

**The question.** When mana flows by the second and cards cycle through a short hand, is timing (when to spend, when to wait for the opponent's push) a real decision?

## Setup

- One lane from position 0 (player A's base) to 12 (player B's base). Base health 20 each.
- Each player has the same 8-card deck (one of each card below), shuffled into a queue: the first 4 are the hand, the 5th is shown as next.
- Mana starts at 5. Time runs in ticks of 0.5 seconds; the match is 360 ticks (3 minutes).

## Each tick

1. Every 4 ticks (2 seconds) both players gain 1 mana (cap 10).
2. Each player may play one card from hand by paying its cost. The card goes to the back of the queue and the next card enters the hand.
3. Every unit acts: if an enemy unit, an enemy Wall or the enemy base is within its range ahead of it, it deals its attack to the nearest one; otherwise it moves forward by its speed, never past the nearest enemy unit or Wall.
4. All damage of the tick is applied at once; anything at 0 health is removed.

Units appear at their owner's base (A at 0.5, B at 11.5) and move toward the enemy base. A Wall is placed at any position in its owner's half and does not move. Blast hits at once when played.

## End

- A base at 0 health loses; both on the same tick is a draw.
- At tick 360 the higher base health wins. Equal: 120 more ticks, and the first damage to a base decides; still equal, a draw.

## Cards (8, both players)

| Card | Cost | Health | Attack per tick | Speed per tick | Range | Text |
|---|---|---|---|---|---|---|
| Runner | 2 | 4 | 1 | 1.0 | 0.5 | |
| Grunt | 3 | 10 | 2 | 0.5 | 0.5 | |
| Shooter | 3 | 4 | 1 | 0.5 | 3 | |
| Brute | 4 | 14 | 3 | 0.4 | 0.5 | |
| Tank | 5 | 30 | 1 | 0.3 | 0.5 | |
| Swarm | 3 | 2 each | 1 | 0.8 | 0.5 | Three units. |
| Blast | 3 | | | | | 8 damage to every enemy unit within 1.5 of a chosen position. |
| Wall | 4 | 20 | 0 | 0 | | Placed in your half; enemy units stop at it. |

## Builder notes

- The sim runs ticks as fast as it can; the page runs them in real time while the bot decides every 2 ticks. The Expert does short rollouts (a few seconds of game time) per candidate: wait, or each playable card at a few positions.
- Greedy: plays the most expensive affordable card as soon as it can; Blast at the densest enemy group; Wall just in front of the biggest enemy unit.
- Racer: never plays Blast or Wall; plays a unit whenever it can afford one.
- There is no first player; the seat check reports seat A's win rate.
- Set positions: lethal (enemy base on 2 health and a Runner in hand that arrives before any enemy unit can meet it: play it); don't waste (never Blast where no enemy unit is in reach); free value (three enemy Swarm units together in reach: Blast them).
