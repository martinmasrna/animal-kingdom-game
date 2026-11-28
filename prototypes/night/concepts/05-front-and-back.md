# 05 Front and back rows

Every number here is a placeholder.

**The question.** When position protects (the front row shields the back row and your life) and ranged units chip the front without being hit back, does arranging the board create decisions a single row does not?

## Setup

- Each side has a front row (max 3 units) and a back row (max 3 units). Melee units always go to the front row, Ranged units to the back row.
- Each player has the same 30-card deck, shuffled. Life 20.
- Random first player; the first player draws 3, the second draws 4 and gets the Coin (0 mana: gain 1 mana this turn).

## Turn

1. Your maximum mana goes up by 1 (cap 10) and refills. Your units become ready. Draw 1. Drawing from an empty deck loses 1 life, then 2, then 3.
2. Play cards by paying their cost. A unit cannot attack on the turn it is played.
3. Each ready unit may attack once. Its targets are the enemy front-row units; only when the enemy front row is empty can it target enemy back-row units or the enemy player.
   - A Melee attacker and its target deal their attack to each other.
   - A Ranged attacker deals its attack and takes nothing back.
4. End the turn.

Damage stays; a unit at 0 health or less is destroyed. Spells ignore rows: they can hit any unit.

## End

Life 0 or less loses.

## Cards (30, both players)

| Card | Kind | Cost | Attack/Health | Text | Copies |
|---|---|---|---|---|---|
| Striker | Melee | 1 | 2/1 | | 3 |
| Wall | Melee | 2 | 1/5 | | 3 |
| Raider | Melee | 2 | 3/2 | | 3 |
| Line | Melee | 3 | 3/4 | | 3 |
| Heavy | Melee | 5 | 5/6 | | 3 |
| Shooter | Ranged | 2 | 1/2 | | 3 |
| Gunner | Ranged | 3 | 2/2 | | 3 |
| Cannon | Ranged | 5 | 4/3 | | 3 |
| Hit 2 | Spell | 1 | | 2 damage to any unit | 3 |
| Hit 4 | Spell | 3 | | 4 damage to any unit | 3 |

## Builder notes

- Greedy: plays the most expensive affordable cards; attacks that destroy a unit without losing the attacker first, then the enemy player when the front is open, then the weakest front unit.
- Racer: attacks the enemy player whenever the front is open; otherwise attacks the front unit it can destroy, Ranged first.
- Set positions: lethal (the enemy front row is empty, enemy on 5 life, your ready Raider and Shooter: attack the player with both); free shot (your ready Gunner and an enemy front Raider on 2 health: shoot it); don't waste (never Hit 4 a 1-health unit while Hit 2 is in hand).
