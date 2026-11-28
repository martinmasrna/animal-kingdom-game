# 02 Attack and block

Every number here is a placeholder. Borrowed: Magic's combat, where attacking exhausts (taps) a creature until its controller's next untap, the defending player chooses blockers, and damage on surviving creatures wears off at end of turn. The rest is not that game: mana ramp, no instants, one blocker per attacker.

**The question.** When the defender chooses the blocks and attackers stay exhausted through the opponent's turn, does every turn hold a real attack-or-hold decision with vanilla units?

## Setup

- Each player has the same 30-card deck, shuffled. Life 20. Board max 6 units.
- Random first player; the first player draws 3, the second draws 4 and gets the Coin (0 mana: gain 1 mana this turn).

## Turn

1. Ready all your units. Your maximum mana goes up by 1 (cap 10) and refills. Draw 1. Drawing from an empty deck loses 1 life, then 2, then 3.
2. Play cards by paying their cost. A unit enters ready: it cannot attack this turn, but it can block during the opponent's next turn.
3. **Attack** (at most once per turn, at any point of the turn): choose any of your ready units that were not played this turn. They become exhausted.
4. **Block**: the defender assigns each of its ready units to block at most one attacker; each attacker can be blocked by at most one unit.
5. **Damage**: a blocked attacker and its blocker deal their attack to each other; an unblocked attacker deals its attack to the defender's life. A unit with damage at least its health is destroyed.
6. You may play more cards after the attack.
7. End of turn: every surviving unit on both sides heals completely.

Exhausted units stay exhausted until their controller's next turn begins, so a unit that attacked cannot block on the opponent's turn. Spells are played on your own turn only, never during blocks; damage they deal to a unit that survives heals at end of turn too.

## End

Life 0 or less loses.

## Cards (30, both players)

| Card | Cost | Attack/Health | Text | Copies |
|---|---|---|---|---|
| Striker | 1 | 2/1 | | 3 |
| Raider | 2 | 3/2 | | 3 |
| Wall | 2 | 0/5 | | 3 |
| Line | 3 | 3/3 | | 3 |
| Heavy | 4 | 4/4 | | 3 |
| Big | 5 | 5/5 | | 3 |
| Huge | 6 | 6/6 | | 3 |
| Hit 2 | 1 | | 2 damage to a unit | 3 |
| Hit 4 | 3 | | 4 damage to a unit | 3 |
| Draw 2 | 2 | | Draw 2 cards | 3 |

## Builder notes

- The human blocks during the bot's turn: the page shows the attackers, the human taps a blocker then an attacker, then confirms. The Expert must choose blocks too; enumerating one-blocker-per-attacker assignments is small enough at six units.
- Greedy attacker: attacks with every unit when its total attack is at least the opponent's life; otherwise with each unit no enemy ready unit could destroy without dying. Greedy blocker: blocks each attacker with its smallest unit that destroys it and survives; leaves the rest unblocked unless the unblocked damage would be lethal, then blocks with its smallest units.
- Racer: attacks with everything every turn; blocks only to prevent lethal.
- Set positions: lethal (the opponent on 5 life with no ready units, your ready Line and Striker: attack with both); free block (an enemy Striker attacks and your ready Line can block: block, it destroys the Striker and survives); don't waste (never Hit 4 a unit that Hit 2 destroys).
