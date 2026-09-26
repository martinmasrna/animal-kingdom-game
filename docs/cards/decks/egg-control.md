# Egg Control

Snake and Bird control. The Birds churn the deck: Raven and Owl draw and shuffle, Secretary Bird fetches a Snake, Aurum draws every turn. The Snakes feed on the churn: Rattlesnake grows with every shuffle (in hand too), Goliath with the Remove Pile, Eon gains food on every draw, shuffle and removal. Each new card is gated on the other tribe: King Cobra removes any adjacent enemy after a shuffle this turn, and Puff Adder removes whatever covers it while you control a Bird.

The plan is to survive the midgame by removing threats one at a time, then win late on size: good against midrange and ramp, which commit one big unit at a time, weak against wide aggro and combo. Played by a human it wins by taking the initiative early (flyers deep on the other side, breaking regions) and building a chain to the enemy HQ anchored by the big Snakes; the bots don't play it that way, so its simulated win rate understates it.

Redesigned 2026-09-26: Bird Egg, Snake Egg and Egg Eater cut to the reserve (Eggs were slower than a Draw action once Draw drew 2), Aurum rethemed from an Egg to a Bird, King Cobra, Puff Adder and Secretary Bird added. Untested beyond unit tests.

## Cards

<!-- cards:begin (generated from cards.json by animal_kingdom.render.deck_docs) -->

### Legendary

| Card | × | Tags | Str | Text |
|---|---:|---|---:|---|
| **Eon** | 1 | Snake | 7 | Whenever a card is drawn, shuffled or removed, gain 1 food. |
| **Ember** | 1 | Bird | 6 | Flight. When this is removed, shuffle it back to your deck. |
| **Aurum** | 1 | Bird | 1 | At the start of your turn, draw a card. |
| **Black Swan** | 1 | Bird | 3 | The first time each turn you draw Black Swan, your opponent removes a random card from their hand. |

### Rare

| Card | × | Tags | Str | Text |
|---|---:|---|---:|---|
| **Goliath** | 2 | Snake | dynamic | This unit's strength is equal to the number of removed units. |
| **Rattlesnake** | 2 | Snake | 0 | Whenever you shuffle a card, gain 1 strength (wherever this is). |
| **Peregrine Falcon** | 2 | Bird | 3 | Flight. Battlecry: remove an adjacent enemy of strength 3 or less. |
| **King Cobra** | 2 | Snake | 4 | Battlecry: if you shuffled a card this turn, remove an adjacent enemy unit. |

### Common

| Card | × | Tags | Str | Text |
|---|---:|---|---:|---|
| **Eagle** | 3 | Bird | 5 | Flight. |
| **Owl** | 3 | Bird | 2 | Flight. Battlecry: look at the top 3 cards; draw 1 and shuffle the rest. |
| **Anaconda** | 3 | Snake | 7 | Apex Predator. |
| **Puff Adder** | 3 | Snake | 3 | When an enemy unit covers this, remove that enemy if you control a Bird. |
| **Secretary Bird** | 3 | Bird | 4 | Flight. Battlecry: draw a Snake. |
| **Raven** | 3 | Bird | 2 | Flight. Battlecry: draw 3 cards, then shuffle 2 cards back. |

<!-- cards:end -->
