# 01 Score-or-fight duel

The brief's fixed entry, built as described there. Every number here is a placeholder.

**The question.** Does choosing, unit by unit, between scoring a unit's health and attacking an enemy unit (scoring by subtraction) give a real decision every turn, or does one of the two always win?

## Setup

- Two players, the same 30-card deck each (list below), shuffled. No hero and no life total.
- Random first player. The first player draws 3 cards, the second draws 4 and also gets the Coin.
- Both scores start at 0. Target score: 40.

## Turn

1. Your maximum mana goes up by 1 (cap 10) and refills. Your units become ready. Draw 1 card. Drawing from an empty deck is fatigue: the opponent gains 2 points, then 4, then 6, and so on.
2. In any order, as often as you can:
   - Play a card from hand by paying its cost. A unit enters your board (max 6 units) and cannot act on the turn it is played.
   - Each ready unit that was not played this turn takes one action and is then spent until your next turn:
     - **Attack** an enemy unit: both deal their attack to each other. Damage stays. A unit at 0 health or less is destroyed.
     - **Score**: add the unit's current health to your score.
3. End the turn.

Units are the only targets; there is nothing else to attack. Spent units can be attacked like any other unit.

## End

The moment a score reaches 40 (after a Score action or a fatigue gain), that player wins.

## Cards

The same stats as the template deck in `hs/vanilla`, so its engine can be reused; spells hit units only.

| Card | Cost | Attack/Health | Text | Copies |
|---|---|---|---|---|
| Striker | 1 | 2/1 | | 3 |
| Raider | 2 | 3/2 | | 3 |
| Guard | 2 | 2/3 | | 3 |
| Line | 3 | 3/4 | | 3 |
| Heavy | 4 | 4/5 | | 3 |
| Big | 5 | 5/5 | | 3 |
| Huge | 6 | 6/7 | | 3 |
| Hit 2 | 1 | | 2 damage to any unit | 3 |
| Hit 3 | 2 | | 3 damage to any unit | 3 |
| Hit 6 | 4 | | 6 damage to any unit | 3 |
| Coin | 0 | | Gain 1 mana this turn. Second player only, not in the deck. | |

## Builder notes

- Greedy: play the most expensive affordable cards first; a spell goes to the enemy unit with the most health it destroys, else the enemy unit with the most health; then each ready unit attacks if it destroys an enemy unit and survives, otherwise it scores.
- Racer: plays units only, never attacks, scores with every ready unit.
- Set positions: lethal (score 33, ready units with 4 and 3 health: score both); free trade (your ready Heavy 4/5 against an enemy Raider 3/2: attack); don't waste (never end the turn with a ready unit idle, since scoring costs nothing; never use Hit 6 on a 1-health unit while Hit 2 is in hand).
