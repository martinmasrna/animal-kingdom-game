# 14 Response duel

Every number here is a placeholder.

**The question.** With no board at all, does holding mana for a response against spending it on your own turn carry a duel?

## Setup

- Each player has the same 30-card deck, shuffled. Life 20 (it can never rise above 20). Hand max 10.
- Random first player; the first player draws 3, the second draws 4 and gets the Coin (0 mana: gain 1 mana this turn).

## Turn

1. Your maximum mana goes up by 1 (cap 10) and refills. Draw 1. Drawing from an empty deck loses 1 life, then 2, then 3.
2. Cast Spells by paying their cost.
3. End the turn. Mana you did not spend stays available through the opponent's next turn, for Responses only, and is gone when your mana refills.

## Responses

Whenever a player casts a Spell, the other player may cast one Response to it, paying from their stored mana. The Response resolves first, then the Spell (unless cancelled). Nobody can respond to a Response, and Responses can only be cast this way.

Siege leaves an effect that ticks at the start of its caster's next three turns; it can only be answered when it is cast.

## End

Life 0 or less loses.

## Cards (30, both players)

| Card | Type | Cost | Text | Copies |
|---|---|---|---|---|
| Bolt | Spell | 1 | 2 damage to the opponent | 5 |
| Blast | Spell | 3 | 5 damage to the opponent | 3 |
| Barrage | Spell | 5 | 8 damage to the opponent | 2 |
| Drain | Spell | 2 | 2 damage to the opponent; you gain 2 life | 3 |
| Study | Spell | 2 | Draw 2 cards | 3 |
| Siege | Spell | 4 | At the start of each of your next 3 turns, 2 damage to the opponent | 2 |
| Cancel | Response | 3 | Cancel the spell | 4 |
| Ward | Response | 1 | The spell deals 3 less damage (a Siege deals 1 less each tick) | 5 |
| Mirror | Response | 2 | The spell's damage hits its caster instead (only a spell of 5 damage or less; not Siege) | 3 |

## Builder notes

- Greedy: casts the most damage per mana, spending all its mana every turn; responds when it has stored mana: Cancel against 5 damage or more, Ward against the rest.
- Racer: as Greedy, but never responds.
- Set positions: lethal (the opponent on 5 life with no stored mana, Blast in hand and 3 mana: cast it); free response (the opponent casts Barrage while you hold Cancel and 3 stored mana: Cancel); don't waste (never Ward a Study; with no Response in hand, spend your mana rather than store it).
