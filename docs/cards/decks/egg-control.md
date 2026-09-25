# Egg Control

Snake, Bird and Egg control built on a draw, shuffle and remove engine that pays food. Its food plan is events, not regions: Eon gains food on every draw, shuffle and removal; Egg Eater pays for every Egg removed; Rattlesnake grows with every shuffle; Goliath grows with the Remove Pile. Fragile Eggs hatch into typed draws.

It wins by out-scaling midrange late (Rattlesnake to 8, Goliath past 10). Bots can't plan that multi-turn growth, so its simulated win rate understates it: a human piloting egg into cats won about half the games the bots lose (see [`../../bots.md`](../../bots.md)).

## Cards

<!-- cards:begin (generated from cards.json by animal_kingdom.render.deck_docs) -->

### Legendary

| Card | × | Tags | Str | Text |
|---|---:|---|---:|---|
| **Eon** | 1 | Snake | 7 | Whenever a card is drawn, shuffled or removed, gain 1 food. |
| **Ember** | 1 | Bird | 6 | Flight. When this is removed, shuffle it back to your deck. |
| **Aurum** | 1 | Egg | 0 | Fragile. At the start of your turn, draw a card. |
| **Black Swan** | 1 | Bird | 3 | The first time each turn you draw Black Swan, your opponent removes a random card from their hand. |

### Rare

| Card | × | Tags | Str | Text |
|---|---:|---|---:|---|
| **Goliath** | 2 | Snake | dynamic | This unit's strength is equal to the number of removed units. |
| **Rattlesnake** | 2 | Snake | 0 | Whenever you shuffle a card, gain 1 strength (wherever this is). |
| **Egg Eater** | 2 | Snake | 4 | Whenever an Egg is removed, gain 10 food. |
| **Peregrine Falcon** | 2 | Bird | 3 | Flight. Battlecry: remove an adjacent enemy of strength 3 or less. |

### Common

| Card | × | Tags | Str | Text |
|---|---:|---|---:|---|
| **Eagle** | 3 | Bird | 5 | Flight. |
| **Owl** | 3 | Bird | 2 | Flight. Battlecry: look at the top 3 cards; draw 1 and shuffle the rest. |
| **Anaconda** | 3 | Snake | 7 | Apex Predator. |
| **Raven** | 3 | Bird | 2 | Flight. Battlecry: draw 3 cards, then shuffle 2 cards back. |
| **Bird Egg** | 3 | Egg | 0 | Fragile. After 2 turns, remove this and draw 2 Birds. |
| **Snake Egg** | 3 | Egg | 0 | Fragile. After 2 turns, remove this and draw 2 Snakes. |

<!-- cards:end -->
