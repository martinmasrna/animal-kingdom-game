# 04 Lanes and scale

Every number here is a placeholder. Borrowed: Inscryption's scale, where a card attacks the card opposite it and, facing an empty space, puts its damage on a shared scale, a five-point lead winning. The rest is not that game: mana ramp, a different card set, no sacrifices.

**The question.** When combat resolves itself and the only decision is which card goes into which lane, is placement enough of a decision?

## Setup

- Four lanes. Each player has one slot per lane on their side, so each lane has two facing slots.
- A shared scale at 0. Player A wins when it reaches +5, player B at −5. Damage "to the scale" moves it toward the attacker's winning end.
- Each player has the same 30-card deck, shuffled. Random first player; the first player draws 3, the second draws 4 and gets the Coin (0 mana: gain 1 mana this turn).

## Turn

1. Your maximum mana goes up by 1 (cap 10) and refills. Draw 1. Drawing from an empty deck moves the scale 1 toward the opponent's winning end.
2. Play cards by paying their cost. A unit goes into an empty slot on your side. Spells resolve at once.
3. End of turn, **combat**: each of your units, lane 1 to lane 4, attacks. If an enemy unit stands opposite, it deals its attack to that unit; otherwise it moves the scale by its attack. The unit attacked does not strike back. Damage stays; a unit at 0 health or less is removed at once. Units attack on the turn they are played.

Only the active player's units attack in its combat; the opponent's units attack in theirs.

## End

The scale reaching 5 toward a player's end wins for that player at once.

## Cards (30, both players)

| Card | Cost | Attack/Health | Text | Copies |
|---|---|---|---|---|
| Wall | 1 | 0/4 | | 3 |
| Striker | 1 | 1/2 | | 3 |
| Raider | 2 | 2/2 | | 3 |
| Lancer | 3 | 3/2 | | 3 |
| Line | 3 | 2/4 | | 3 |
| Heavy | 4 | 3/5 | | 3 |
| Big | 5 | 4/6 | | 3 |
| Hit 2 | 1 | | 2 damage to a unit | 3 |
| Shift | 1 | | Move one of your units to an empty slot on your side | 3 |
| Shove | 2 | | Move the scale 1 toward your winning end | 3 |

## Builder notes

- Greedy: places each unit opposite an enemy unit it destroys in this combat; else facing an empty enemy slot; else opposite the enemy unit with the highest attack; most expensive first.
- Racer: places units only in lanes with no enemy unit opposite; never Shift onto a blocked lane.
- Set positions: lethal (scale 3 toward you, an open lane and a Raider in hand with 2 mana: place it in the open lane); free kill (an enemy Lancer 3/2 in lane 2 and a Heavy in hand: place it opposite, it deals 3 in this combat); don't waste (never Shift a unit that is hitting the scale into a lane where it hits a Wall).
