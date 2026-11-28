# 41 Wave defense

One player against the game's threat deck. Every number is a placeholder.

## Setup

- Three lanes, each with rows 4 (far) to 1 (next to your Wall), and one Defender slot per lane at the Wall. Wall 20.
- The threat deck (24) is built in three tiers of 8, each shuffled on its own: tier 1 on top, tier 3 at the bottom.
- Your deck: the 12-card start deck, shuffled. Your hand starts empty.

## A round

1. **Advance.** Each threat moves 1 row toward the Wall (Swift moves 2), nearest first. Only one threat can stand in row 1 of a lane; another that would enter waits in row 2. Threats in row 1 stay.
2. **Attack.** Each threat in row 1 attacks: if its lane has a Defender, the two deal their attack to each other; otherwise it deals its attack to the Wall. Damage stays.
3. **Spawn.** Reveal 1 threat (2 from round 7 on); each goes to row 4 of the lane with the fewest threats (leftmost on ties).
4. **Your turn.** You have **4 mana** (the spec's rule was mana = the round number, cap 8; see REPORT.md). Draw 2 (hand max 7; shuffle your discard when the deck is empty). Play cards: a Defender goes into a slot (destroying the one there), spells resolve at once.
5. **Shoot.** Each Defender with Shoot deals that much damage to the nearest threat in its lane.
6. **Reward.** After rounds 4, 8 and 12, three random cards from the reward pool are shown; add one to your discard pile, or none.

A threat or Defender at 0 health or less is removed at once.

## End

Win when the threat deck is empty and no threat is left. Lose when the Wall reaches 0.

## Threat deck (attack/health)

| Tier | Threats |
|---|---|
| 1 | Runner 1/2 ×4, Grunt 2/3 ×4 |
| 2 | Grunt 2/3 ×2, Swift 2/2 (moves 2) ×3, Brute 3/6 ×3 |
| 3 | Brute 3/6 ×2, Tank 1/10 ×2, Swift 2/2 ×1, Boss 5/8 ×3 |

## Start deck (12)

| Card | Cost | Text | Copies |
|---|---|---|---|
| Guard | 1 | Defender 1/5 | 3 |
| Shooter | 2 | Defender 0/2, Shoot 1 | 3 |
| Hit 3 | 1 | 3 damage to a threat | 3 |
| Repair | 2 | Wall +4 (max 20) | 1 |
| Draw 2 | 1 | Draw 2 cards | 2 |

## Reward pool (any card can come up any number of times)

| Card | Cost | Text |
|---|---|---|
| Heavy | 4 | Defender 3/8 |
| Cannon | 4 | Defender 0/3, Shoot 3 |
| Twin | 3 | Defender 1/3, Shoot 2 |
| Bomb | 3 | 2 damage to every threat in one lane |
| Freeze | 2 | Threats in one lane do not advance next round |
| Rebuild | 3 | Wall +8 (max 20) |
| Hit 6 | 3 | 6 damage to a threat |

## The page

You play; the Expert plays the same seeded game in the background. At the end both results show side by side, and the two numbers by Rules count who ended better (a win beats a loss; two wins: more Wall; two losses: more rounds).
