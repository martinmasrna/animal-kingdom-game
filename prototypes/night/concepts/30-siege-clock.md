# 30 Siege clock

Every number here is a placeholder.

**The question.** With two different decks, one side having to break a gate within ten rounds and the other having to hold, do both sides face real choices, and does neither side always win?

## Setup

- Two roles, Attacker and Defender, with their own decks (lists below); roles alternate from game to game.
- The Gate has 20 health. The Attacker's units stand in the Field (max 5); the Defender's on the Wall (max 4).
- Each side shuffles its deck and draws 4.

## A round (10 rounds)

**Attacker's turn**

1. Mana equals the round number (cap 10) and refills. Draw 1 (empty deck: draw nothing).
2. Play cards by paying their cost.
3. Attack, once: choose any Field units that were already in the Field at the start of this turn. The Defender assigns each Wall unit to block at most one attacker; each attacker is blocked by at most one Wall unit. A blocked attacker and its blocker deal their attack to each other; an unblocked attacker deals its attack to the Gate (a Ram deals double). Damage stays.

**Defender's turn**

1. Mana equals the round number (cap 10) and refills. Draw 1.
2. Play cards by paying their cost.
3. End of turn: each Shooter on the Wall deals 1 damage to a Field unit of the Defender's choice.

Wall units block every round; they never become exhausted. Units at 0 health or less are destroyed.

## End

The Attacker wins the moment the Gate reaches 0. The Defender wins at the end of round 10.

## Attacker deck (24)

| Card | Cost | Attack/Health | Text | Copies |
|---|---|---|---|---|
| Grunt | 1 | 2/2 | | 4 |
| Climber | 2 | 2/1 | Cannot be blocked. | 3 |
| Ram | 3 | 3/3 | Deals double damage to the Gate. | 3 |
| Brute | 4 | 4/6 | | 3 |
| Shield | 3 | 1/6 | Shooters and Snipes must target it while it stands. | 2 |
| Volley | 2 | | 2 damage to a Wall unit. | 3 |
| Rush | 1 | | A unit played this turn may attack this turn. | 3 |
| Draw 2 | 2 | | Draw 2 cards. | 3 |

## Defender deck (24)

| Card | Cost | Attack/Health | Text | Copies |
|---|---|---|---|---|
| Guard | 1 | 1/3 | | 4 |
| Shooter | 2 | 1/2 | Shoots 1 at the end of your turn. | 4 |
| Pike | 3 | 3/4 | | 3 |
| Heavy | 4 | 3/7 | | 2 |
| Repair | 2 | | Gate +3 (max 20). | 3 |
| Oil | 4 | | 2 damage to every Field unit. | 3 |
| Snipe | 1 | | 2 damage to a Field unit. | 3 |
| Draw 2 | 2 | | Draw 2 cards. | 2 |

## Builder notes

- Greedy Attacker: plays the most expensive affordable cards and attacks with everything. Greedy Defender: blocks each attacker with a unit that destroys it and survives, otherwise blocks the highest attack; plays the most expensive affordable cards.
- Racer (Attacker only): attacks with everything every round and spends nothing on the Wall.
- The first-player check becomes a role check: the Attacker's win rate over seats must lie within 30–70%.
- Set positions: lethal (Gate on 4, two Climbers that can attack: attack); free block (an attacking Grunt and a ready Pike: block it); don't waste (never Repair a Gate at 20).
