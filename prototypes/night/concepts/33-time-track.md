# 33 Time track

Every number here is a placeholder. Borrowed: Patchwork's time track, where the player furthest behind takes the next turn and, on a shared space, the token on top (the one that arrived last) goes first. The rest is not that game: a unit duel with life.

**The question.** With no turns, where whoever is behind on the time track acts next and every action costs time, do cheap fast actions and slow strong ones trade off in a real way?

## Setup

- A shared time track from 0 to 60. Both markers start on 0; a random player's marker is on top.
- Each player has the same 24-card deck, shuffled, and draws 4. Life 20. Board max 6 units.

## Who acts

The player whose marker is further behind takes one action. On the same space, the marker on top acts. Whenever a marker lands on the space the other marker occupies, it goes on top.

## Actions

Each action moves your marker forward by its time cost:

- **Play a card** from hand: forward by the card's time cost. A unit's ready time is your marker's new position + 3.
- **Attack** with a ready unit (your marker has reached its ready time): forward 1. It attacks an enemy unit (both deal their attack to each other, damage stays) or the enemy player. Its ready time becomes your marker's new position + its Recovery.
- **Draw**: forward 2, draw a card (hand max 8; not possible with an empty deck).

There are no automatic draws and no mana: time is the only cost.

## End

- Life 0 loses.
- A marker never passes 60: an action that would take it past stops it on 60. A player on 60 takes no more actions; the other keeps acting until it reaches 60. When both are on 60, the higher life wins; equal is a draw.

## Cards (24, both players)

| Card | Time | Attack/Health | Recovery | Text | Copies |
|---|---|---|---|---|---|
| Quick | 2 | 2/1 | 2 | | 3 |
| Raider | 3 | 3/2 | 3 | | 3 |
| Guard | 3 | 1/5 | 4 | | 3 |
| Line | 5 | 3/4 | 3 | | 3 |
| Heavy | 7 | 5/6 | 4 | | 3 |
| Slow | 9 | 7/8 | 5 | | 2 |
| Hit 3 | 3 | | | 3 damage to a unit or the enemy | 3 |
| Hit 6 | 6 | | | 6 damage to a unit or the enemy | 2 |
| Haste | 1 | | | One of your units is ready now | 2 |

## Builder notes

- The page needs the track drawn with both markers and each unit's ready time shown as a mark on it.
- Greedy: in order of preference, attack with a ready unit that destroys an enemy unit and survives; play the most expensive card in hand; attack the enemy with a ready unit; Draw.
- Racer: every attack goes at the enemy player; plays units, never spells on units.
- The first-player check reads the player whose marker starts on top.
- Set positions: lethal (enemy at 3 life, your ready Raider: attack the enemy); free trade (your ready Heavy against an enemy Quick: attack it); don't waste (never Draw with 8 cards in hand; never Haste a unit that is already ready).
