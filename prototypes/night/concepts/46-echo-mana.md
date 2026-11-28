# 46 Echo mana

Every number here is a placeholder.

**The question.** When your mana each turn is what the opponent spent on their last turn plus one, is spending less to starve them a real decision?

## Setup

The template game of `hs/vanilla` exactly (its deck, 30 health, board max 7, opening hands 3 and 4 plus the Coin for the second player, draw 1 a turn, fatigue 1, 2, 3 on an empty deck, minions attack from the turn after they are played, any enemy minion or the enemy hero), with one rule changed: mana.

## Mana

- At the start of your turn, your mana is the mana the opponent spent on their previous turn, plus 1; at least 2, at most 10. The first player's first turn has 2.
- Spent means mana actually paid for cards. Mana from the Coin counts as yours to spend, and what you pay with it counts as spent.
- Unspent mana is lost at the end of your turn.

Everything else is unchanged.

## Cards (30, both players)

The template deck: Striker 1: 2/1, Raider 2: 3/2, Guard 2: 2/3, Line 3: 3/4, Heavy 4: 4/5, Big 5: 5/5, Huge 6: 6/7, Hit 2 (1 mana), Hit 3 (2 mana), Hit 6 (4 mana): 2, 3 or 6 damage to any minion or hero. Three copies of each.

## Builder notes

- The page shows both players' mana for the coming turn, since it follows from what was spent.
- Greedy: the template's Greedy, spending the most mana.
- Starver (a third trivial bot): spends the least it can while still playing one card each turn.
- Racer: every attack and spell at the enemy hero.
- Set positions: the template's (lethal, lethal through the Coin, a free trade, no face damage on turn 1), plus don't waste (never pass with mana and a card that would destroy an enemy minion for free).
