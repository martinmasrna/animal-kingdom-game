# 15 Key pieces

Every number here is a placeholder.

**The question.** When the only way to win is to hold three different Keys at once and Keys can be attacked, does protecting against completing make the game?

## Setup

- Each player has the same 30-card deck, shuffled. There is no life total. Board max 6 pieces (Keys count).
- Random first player; the first player draws 3, the second draws 4 and gets the Coin (0 mana: gain 1 mana this turn).

## Turn

1. **Win check**: if you control Key A, Key B and Key C, you win.
2. Your maximum mana goes up by 1 (cap 10) and refills. Your units become ready. Draw 1. A player who must draw from an empty deck loses.
3. Play cards by paying their cost. A unit cannot attack on the turn it is played. Keys are pieces with 0 attack that never attack.
4. Each ready unit may attack an enemy unit or Key once: both deal their attack to each other (a Key deals 0). Damage stays; a piece at 0 health or less is destroyed. While the defender controls a Guard, attacks must target a Guard. Spells ignore Guard.
5. End the turn.

## End

Holding all three Keys at the start of your turn wins; drawing from an empty deck loses.

## Cards (30, both players)

| Card | Cost | Attack/Health | Text | Copies |
|---|---|---|---|---|
| Key A | 2 | 0/3 | Key. | 2 |
| Key B | 3 | 0/4 | Key. | 2 |
| Key C | 4 | 0/5 | Key. | 2 |
| Fetch | 2 | | Put a Key of your choice from your deck into your hand. | 2 |
| Striker | 1 | 2/1 | | 3 |
| Raider | 2 | 3/2 | | 3 |
| Guard | 2 | 1/4 | Guard. | 3 |
| Line | 3 | 3/4 | | 3 |
| Heavy | 4 | 4/4 | | 3 |
| Wall | 4 | 2/7 | Guard. | 2 |
| Hit 3 | 2 | | 3 damage to a unit or Key. | 3 |
| Hit 5 | 4 | | 5 damage to a unit or Key. | 2 |

## Builder notes

- Greedy: plays a missing Key whenever it can, otherwise the most expensive affordable card; attacks or Hits an enemy Key it can destroy, otherwise trades that destroy a unit and survive.
- Racer: plays Keys and Guards first; attacks only to destroy Keys.
- Set positions: deny (the opponent controls all three Keys, one of them Key A on 3 health, and you hold Hit 3 with 2 mana: destroy it); free trade (your ready Line against an enemy Raider, no enemy Guard: attack it); don't waste (never Fetch a Key you already control while another is missing).
