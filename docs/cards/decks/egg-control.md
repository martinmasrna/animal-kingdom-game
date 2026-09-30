# Egg Control

Snake and Bird control. The Birds churn the deck: Raven and Owl draw and shuffle, Aurum draws every turn. The Snakes feed on the churn: Rattlesnake grows with every shuffle (in hand too), Python with the Remove Pile. The Snakes also carry venom: Viper permanently takes 3 strength off an adjacent enemy, which opens big units to covers; Black Mamba removes an adjacent enemy of strength 5 or less; Taipan's bite removes any adjacent enemy at the start of your next turn, even if the Taipan is covered or removed. Magpie steals a random card from the opponent's hand and discards one of yours, which feeds Python.

Eon is the Ouroboros: a 10 with Apex Predator that eats what it lands on, then shuffles itself back into the deck at the end of your turn, one strength smaller each cycle. Every return is a shuffle, so it also feeds Rattlesnake.

Rarity follows role: the commons are the engine (Owl, Raven, Eagle, Rattlesnake, Python, Viper), the rares are situational answers (Hawk, Taipan, Magpie, Black Mamba).

The plan is to survive the midgame by removing threats one at a time, then win late on size: good against midrange and ramp, which commit one big unit at a time, weak against wide aggro and combo. Played by a human it wins by taking the initiative early (flyers deep on the other side, breaking regions) and building a chain to the enemy den anchored by the big Snakes; the bots don't play it that way, so its simulated win rate understates it.

## Cards

<!-- cards:begin (generated from cards.json by animal_kingdom.render.deck_docs) -->

### Legendary

| Card | × | Tags | Str | Text |
|---|---:|---|---:|---|
| **Eon** | 1 | Snake | 10 | Apex Predator. At the end of your turn, shuffle this into your deck with -1 strength. |
| **Ember** | 1 | Bird | 7 | Flight. When this is removed, shuffle it back to your deck. |
| **Aurum** | 1 | Bird | 1 | At the start of your turn, draw a card. |
| **Omen, the Black Swan** | 1 | Bird | 3 | The first time each turn you draw Omen, your opponent discards a random card. |

### Rare

| Card | × | Tags | Str | Text |
|---|---:|---|---:|---|
| **Hawk** | 2 | Bird | 3 | Flight. Roar: remove an adjacent enemy of strength 3 or less. |
| **Taipan** | 2 | Snake | 4 | Roar: choose an adjacent enemy. At the start of your next turn, remove it. |
| **Magpie** | 2 | Bird | 3 | Flight. Roar: steal a card from your opponent's hand, then discard a card. |
| **Black Mamba** | 2 | Snake | 4 | Roar: remove an adjacent enemy of strength 5 or less. |

### Common

| Card | × | Tags | Str | Text |
|---|---:|---|---:|---|
| **Python** | 3 | Snake | dynamic | Has +1 strength for each removed unit. |
| **Rattlesnake** | 3 | Snake | 0 | Whenever you shuffle a card, gain 1 strength (wherever this is). |
| **Eagle** | 3 | Bird | 5 | Flight. |
| **Owl** | 3 | Bird | 2 | Flight. Roar: look at the top 3 cards; draw 1 and shuffle the rest. |
| **Viper** | 3 | Snake | 3 | Roar: an adjacent enemy gets -3 strength. |
| **Raven** | 3 | Bird | 2 | Flight. Roar: draw 3 cards, then shuffle 2 cards back. |

<!-- cards:end -->

## Proposal: the Eggs return (not in the card pool)

Martin, 2026-09-30. Eggs tie the deck together: both Snakes and Birds lay them. The old Bird Egg and Snake Egg (0, "After 2 turns, remove this and draw 2 Birds/Snakes") were the right design for control (proactive on turn one, a delayed payoff, deck thinning) until Draw went from 1 card to 2: an Egg then paid what a Draw pays, later and breakable. A hatch of 4 would restore the old ratio but reads absurd and makes a broken Egg too big a swing. The fix is to split the payoff (part on the Roar, part at the hatch) and give each family its own egg.

| Card | Tags | Str | Text |
|---|---|---:|---|
| **Snake Egg** | Snake | 0 | Roar: draw a Snake. In 2 turns, remove this and draw 2 Snakes. |
| **Bird Egg** | Bird | 0 | Roar: Discover a Bird. Next turn, remove this and Discover a Bird. |

- The two trade differently: the Snake Egg is quantity and patience (three tutored cards, a two-turn window), the Bird Egg quality and speed (the best of three, twice, a one-turn window). Both remove themselves at the hatch, which feeds Python.
- A covered Egg only pauses (a timer ticks only while its unit is on top); removing the unit that covers it resumes the hatch. Only removal breaks an Egg, which gives a removal deck counterplay.
- Open: the numbers, the Bird Egg's timing wording ("At the start of your next turn" is the convention but runs past the 80-character limit), and what the two Eggs replace in the list.

### Discover (working name)

A card-text term like Discard, not a keyword. **Discover a Bird**: look at three random Birds in your deck, draw one and shuffle the others back (all of them, if fewer than three). It draws from the deck, never creates a card, and its shuffle feeds Rattlesnake. It suits "smart" animals across decks. Candidates for the word: Forage (the pick so far), Scout, Seek, Sniff out.

Cards that would use it:

- **Owl** (Egg Control): "Flight. Roar: Discover a card." (now "look at the top 3 cards; draw 1 and shuffle the rest", the same effect).
- **Fathom** (Food OTK): "Roar: Discover a legendary unit." (now "draw a legendary unit").
- **Bird Egg** above.
