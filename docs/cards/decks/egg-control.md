# Egg Control

Snake and Bird control. The Birds churn the deck: Raven and Owl draw and shuffle, Secretary Bird fetches a Snake, Aurum draws every turn. The Snakes feed on the churn: Rattlesnake grows with every shuffle (in hand too), Goliath with the Remove Pile, Eon gains food on every draw, shuffle and removal. The Snakes also carry venom: Viper permanently takes 3 strength off an adjacent enemy, which opens big units to the Birds' covers (a bitten Lion is a 4 an Eagle can land on), and Black Mamba's bite removes any adjacent enemy at the start of your next turn. The venom is on the bitten unit, so it resolves even if the Mamba is covered or removed, or the bitten unit is buried.

The plan is to survive the midgame by removing threats one at a time, then win late on size: good against midrange and ramp, which commit one big unit at a time, weak against wide aggro and combo. Played by a human it wins by taking the initiative early (flyers deep on the other side, breaking regions) and building a chain to the enemy HQ anchored by the big Snakes; the bots don't play it that way, so its simulated win rate understates it.

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
| **Black Mamba** | 2 | Snake | 4 | Battlecry: choose an adjacent enemy unit. At the start of your next turn, remove it. |

### Common

| Card | × | Tags | Str | Text |
|---|---:|---|---:|---|
| **Eagle** | 3 | Bird | 5 | Flight. |
| **Owl** | 3 | Bird | 2 | Flight. Battlecry: look at the top 3 cards; draw 1 and shuffle the rest. |
| **Anaconda** | 3 | Snake | 7 | Apex Predator. |
| **Viper** | 3 | Snake | 3 | Battlecry: an adjacent enemy unit gets -3 strength. |
| **Secretary Bird** | 3 | Bird | 4 | Flight. Battlecry: draw a Snake. |
| **Raven** | 3 | Bird | 2 | Flight. Battlecry: draw 3 cards, then shuffle 2 cards back. |

<!-- cards:end -->
