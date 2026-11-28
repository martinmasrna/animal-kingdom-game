# 40 Simultaneous turns

Every number here is a placeholder.

**The question.** When both players plan their whole turn at once and everything resolves together, does predicting the other's attacks replace tempo as the skill?

## Setup

- Each player has the same 30-card deck, shuffled, and draws 4. Life 20. Board max 6 units. There is no first player and no Coin.

## A round

1. Both players' maximum mana is the round number (cap 10) and refills. Both draw 1. Drawing from an empty deck loses 1 life, then 2, then 3.
2. **Plan**, secretly and at the same time:
   - which cards to play (total cost within your mana, units within your free board slots), with targets for spells chosen among what is on the board now;
   - for each of your ready units, its attack target (an enemy unit on the board now, or the enemy player) or no attack.
3. **Reveal**, then resolve in three steps:
   1. All spells, at the same time: damage is dealt, then destroyed units are removed.
   2. All new units enter. They are not ready until next round.
   3. All attacks, at the same time: each attacker deals its attack to its target, and each attacked unit deals its attack to every unit attacking it. Then destroyed units are removed. An attack whose attacker or target was destroyed in step 1 does not happen.
4. All surviving units become ready.

Damage stays.

## End

Life 0 or less loses; both at once is a draw.

## Cards (30, both players)

The template deck of `hs/vanilla`: Striker 1: 2/1, Raider 2: 3/2, Guard 2: 2/3, Line 3: 3/4, Heavy 4: 4/5, Big 5: 5/5, Huge 6: 6/7, Hit 2 (1 mana), Hit 3 (2 mana), Hit 6 (4 mana): 2, 3 or 6 damage to any unit or player. Three copies of each.

## Builder notes

- Simultaneous: the Expert scores candidate plans by rollouts against plans sampled from a model of the opponent (for example its Greedy plan plus noise), and never sees the opponent's plan. The candidate set can be pruned to a few dozen plans per round.
- Greedy: plays the most expensive affordable cards; each ready unit attacks the enemy unit it destroys and survives against, otherwise the enemy player.
- Racer: every attack and every spell at the enemy player.
- There is no first player; the seat check reports seat A's win rate.
- Set positions: lethal (the enemy on 4 life with an empty hand, so no spell can stop you, and your two ready Raiders: both attack the player); free trade (your ready Heavy against an enemy Raider with an empty enemy hand: attack it); don't waste (never Hit 6 a 2-health unit while Hit 2 is in hand).
