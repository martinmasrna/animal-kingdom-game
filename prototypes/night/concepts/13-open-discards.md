# 13 Open discards

Every number here is a placeholder.

**The question.** When every card you play or lose becomes the opponent's to play, does exposing a card become a real cost?

## Setup

The template game of `hs/vanilla` exactly (its deck, 30 health, mana 1 to 10, board max 7, opening hands 3 and 4 plus the Coin for the second player, draw 1 a turn, fatigue, minions attack from the turn after they are played, any enemy minion or the enemy hero), with one rule added: open discards.

## Open discards

- Each player has a face-up discard pile. A destroyed minion and a resolved spell go to their owner's discard pile. The Coin is removed from the game when used.
- Once per turn you may play one card from the opponent's discard pile, paying its cost plus 1. It works as if it were yours (a minion enters your board and cannot attack this turn). When it is later destroyed or resolves, it goes to your discard pile.

Everything else is unchanged.

## Cards (30, both players)

The template deck: Striker 1: 2/1, Raider 2: 3/2, Guard 2: 2/3, Line 3: 3/4, Heavy 4: 4/5, Big 5: 5/5, Huge 6: 6/7, Hit 2 (1 mana), Hit 3 (2 mana), Hit 6 (4 mana): 2, 3 or 6 damage to any minion or hero. Three copies of each.

## Builder notes

- Greedy: the template's Greedy, choosing among hand cards and the opponent's discard alike.
- Racer: every attack and spell at the enemy hero.
- Set positions: the template's, plus lethal from the discard (the opponent on 3 health, their Hit 3 in their discard and 3 mana: play it from there at the hero); don't waste (never play a card from the discard for cost plus 1 when the same card in hand costs less and you can only afford one).
