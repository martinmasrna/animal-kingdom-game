# 33 Time track: rules

Two players, the same 24-card deck each, life 20, up to 6 units each. There are no turns and no mana: time is the only cost.

**Setup.** A shared time track from 0 to 60; both markers start on 0 and a random player's marker is on top. Shuffle; each player draws 4.

**Who acts.** The player whose marker is further behind takes one action. On the same space, the marker on top acts. A marker that lands on the space of the other goes on top.

**Actions.** Each moves your marker forward by its time:

- **Play a card** from hand: its time cost. A unit's ready time is your marker's new position + 3.
- **Attack** with a ready unit (your marker has reached its ready time): time 1. It attacks an enemy unit (both deal their attack to each other; damage stays; 0 health is destroyed) or the enemy player. Its ready time becomes your marker's new position + its Recovery.
- **Draw**: time 2, draw a card (not with 8 in hand or an empty deck).
- **Wait**: time 1, only when no other action is possible (an addition: the spec has no pass, and a player can be left with nothing legal).

**End.** Life 0 loses at once. A marker never passes 60 (an action that would take it past stops it there). A player on 60 takes no more actions; the other keeps acting until it reaches 60. When both are on 60, the higher life wins; equal is a draw.

**Cards (24, both players).**

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
