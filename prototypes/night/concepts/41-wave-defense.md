# 41 Wave defense

Every number here is a placeholder. One player against the game.

**The question.** Alone against a deck of threats walking down three lanes, do choosing where to spend and what to add to your deck make a game, or does a fixed rule beat it?

## Setup

- Three lanes, each with rows 4 (far) to 1 (next to your Wall), and one Defender slot per lane at the Wall. Wall health 20.
- The threat deck (24, list below) is built in three tiers of 8: each tier shuffled on its own, tier 1 on top, tier 3 at the bottom.
- Your deck: the 12-card start deck below, shuffled.

## A round

1. **Advance.** Each threat moves 1 row toward the Wall (Swift moves 2), nearest threats first. A threat cannot enter row 1 of a lane while another threat stands there; it waits in row 2. Threats in row 1 stay.
2. **Attack.** Each threat in row 1 attacks: if its lane's Defender slot is filled, the threat and the Defender deal their attack to each other; otherwise the threat deals its attack to the Wall. Damage stays.
3. **Spawn.** Reveal 1 threat (2 from round 7 on) and put each in row 4 of the lane with the fewest threats (leftmost on ties).
4. **Your turn.** Mana equals the round number (cap 8). Draw 2 (hand max 7; shuffle your discard when the deck is empty). Play cards by paying their cost: Defenders go into slots (a Defender played onto a filled slot destroys the one there), spells resolve at once.
5. **Shoot.** Each Defender with Shoot deals that much damage to the nearest threat in its lane.
6. **Reward.** After rounds 4, 8 and 12, three random cards from the reward pool are shown; add one to your discard pile, or none.

A threat or Defender at 0 health or less is removed at once.

## End

You win when the threat deck is empty and no threat is left. You lose when the Wall reaches 0.

## Threat deck (24; attack/health)

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

## Reward pool (each card can come up any number of times)

| Card | Cost | Text |
|---|---|---|
| Heavy | 4 | Defender 3/8 |
| Cannon | 4 | Defender 0/3, Shoot 3 |
| Twin | 3 | Defender 1/3, Shoot 2 |
| Bomb | 3 | 2 damage to every threat in one lane |
| Freeze | 2 | Threats in one lane do not advance next round |
| Rebuild | 3 | Wall +8 (max 20) |
| Hit 6 | 3 | 6 damage to a threat |

## Builder notes

- The gate for one player: Expert and each trivial bot play the same seeded games (same threat order, same draws, same reward offers). Expert wins a pair when it ends better: a win beats a loss; between two wins or two losses, more Wall left, then more rounds survived, decides. Expert must win at least 70% of the decided pairs against each trivial bot over 400 seeds. There is no first player; report Expert's own win rate. The game always ends (the threat deck runs out), so the turn cap never applies.
- Greedy: plays the most expensive affordable cards; Hit goes to the threat nearest the Wall; Defenders into empty slots, the lane with the most threat attack first; takes the most expensive reward.
- Set positions: lethal (the last threat is in row 1 with 3 health and Hit 3 is in hand: play it); don't waste (never Repair a full Wall); free value (Bomb a lane holding three threats with 2 health).
