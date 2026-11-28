# 03 Exert to score

Every number here is a placeholder. Borrowed: Lorcana's rule that a character gains points by exerting (questing), and that only exerted characters can be challenged, first to 20. The rest is not that game: mana ramp instead of an inkwell, no songs, items or locations.

**The question.** When scoring exposes a unit to attack and attacking exposes the attacker, is the choice between scoring, challenging and staying ready a real one?

## Setup

- Each player has the same 30-card deck, shuffled. Random first player; the first player draws 3, the second draws 4 and gets the Coin (0 mana: gain 1 mana this turn).
- Points start at 0. Target: 20.
- Units have Strength, Health and Score (the points they gain when they score).

## Turn

1. Ready all your units. Your maximum mana goes up by 1 (cap 10) and refills. Draw 1. Drawing from an empty deck gives the opponent 2 points, then 4, then 6.
2. In any order:
   - Play a card by paying its cost. A unit enters ready (max 6 units) and cannot act this turn.
   - Each ready unit that was not played this turn may take one action, which exerts it:
     - **Score**: gain its Score in points.
     - **Challenge**: choose an exerted enemy unit; both deal their Strength to each other. Damage stays; a unit at 0 Health or less is destroyed.
3. End the turn.

Ready units cannot be challenged. Exerted units stay exerted until their owner's next turn begins, so any unit that scored or challenged can be challenged during the opponent's turn. Spells can hit any unit, ready or exerted.

## End

The moment a player reaches 20 points, they win.

## Cards (30, both players)

| Card | Cost | Strength/Health | Score | Text | Copies |
|---|---|---|---|---|---|
| Runner | 1 | 1/1 | 1 | | 3 |
| Scout | 2 | 1/3 | 2 | | 3 |
| Raider | 2 | 3/2 | 0 | | 3 |
| Guard | 3 | 2/5 | 1 | | 3 |
| Line | 3 | 3/3 | 2 | | 3 |
| Heavy | 4 | 4/5 | 2 | | 3 |
| Big | 5 | 5/6 | 2 | | 2 |
| Star | 6 | 3/6 | 4 | | 2 |
| Hit 2 | 1 | | | 2 damage to any unit | 3 |
| Hit 4 | 3 | | | 4 damage to any unit | 2 |
| Draw 2 | 2 | | | Draw 2 cards | 3 |

## Builder notes

- Greedy: play the most expensive affordable cards; each ready unit challenges if it destroys an exerted enemy unit and survives, otherwise scores.
- Racer: never challenges; scores with every ready unit; spells unused.
- Set positions: lethal (17 points, ready units with Score 2 and 1: score both); free trade (your ready Line 3/3 and an exerted enemy Runner 1/1: challenge it); don't waste (never Hit 4 a 1-Health unit with Hit 2 in hand).
