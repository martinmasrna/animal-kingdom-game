# Egg Control

Snake and Bird control. The Birds churn the deck: Raven and Owl draw and shuffle, Aurum draws every turn. The Snakes feed on the churn: Rattlesnake grows with every shuffle (in hand too), Python with the Remove Pile. The Snakes also carry venom: Viper permanently takes 3 strength off an adjacent enemy, which opens big units to covers; Black Mamba removes an adjacent enemy of strength 5 or less; Taipan's bite removes any adjacent enemy at the start of your next turn, even if the Taipan is covered or removed. Magpie steals a random card from the opponent's hand and caches one of yours in the deck.

Eon is the Ouroboros: a 10 with Apex Predator that eats what it lands on, then shuffles itself back into the deck at the end of your turn, one strength smaller each cycle. Every return is a shuffle, so it also feeds Rattlesnake.

Rarity follows role: the commons are the engine (Owl, Raven, Eagle, Rattlesnake, Python, Viper), the rares are situational answers (Peregrine Falcon, Taipan, Magpie, Black Mamba).

The plan is to survive the midgame by removing threats one at a time, then win late on size: good against midrange and ramp, which commit one big unit at a time, weak against wide aggro and combo. Played by a human it wins by taking the initiative early (flyers deep on the other side, breaking regions) and building a chain to the enemy HQ anchored by the big Snakes; the bots don't play it that way, so its simulated win rate understates it.

## Cards

<!-- cards:begin (generated from cards.json by animal_kingdom.render.deck_docs) -->

### Legendary

| Card | × | Tags | Str | Text |
|---|---:|---|---:|---|
| **Eon** | 1 | Snake | 10 | Apex Predator. At the end of your turn, shuffle this into your deck with -1 strength. |
| **Ember** | 1 | Bird | 7 | Flight. When this is removed, shuffle it back to your deck. |
| **Aurum** | 1 | Bird | 1 | At the start of your turn, draw a card. |
| **Nassim** | 1 | Bird | 3 | The first time each turn you draw Nassim, your opponent removes a random card from their hand. |

### Rare

| Card | × | Tags | Str | Text |
|---|---:|---|---:|---|
| **Peregrine Falcon** | 2 | Bird | 3 | Flight. Battlecry: remove an adjacent enemy of strength 3 or less. |
| **Taipan** | 2 | Snake | 4 | Battlecry: choose an adjacent enemy unit. At the start of your next turn, remove it. |
| **Magpie** | 2 | Bird | 3 | Flight. Battlecry: take a random card from your opponent's hand, then shuffle a card from your hand into your deck. |
| **Black Mamba** | 2 | Snake | 4 | Battlecry: remove an adjacent enemy of strength 5 or less. |

### Common

| Card | × | Tags | Str | Text |
|---|---:|---|---:|---|
| **Python** | 3 | Snake | dynamic | This unit's strength is equal to the number of removed units. |
| **Rattlesnake** | 3 | Snake | 0 | Whenever you shuffle a card, gain 1 strength (wherever this is). |
| **Eagle** | 3 | Bird | 5 | Flight. |
| **Owl** | 3 | Bird | 2 | Flight. Battlecry: look at the top 3 cards; draw 1 and shuffle the rest. |
| **Viper** | 3 | Snake | 3 | Battlecry: an adjacent enemy unit gets -3 strength. |
| **Raven** | 3 | Bird | 2 | Flight. Battlecry: draw 3 cards, then shuffle 2 cards back. |

<!-- cards:end -->
