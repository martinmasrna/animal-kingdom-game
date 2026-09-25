# Colony Food Swarm

Mono-Colony insect swarm that converts a wide board into food. Heavy Flight. Queen and Worker are role tags inside the Colony tribe, so effects can ask for "a Worker" or "a non-Queen Colony unit". Several payoffs are gated on controlling 4 or more Colony units: the tribe-count threshold is the deck's defence against goodstuff piles, which can't reach it (see [`../../design/goodstuff.md`](../../design/goodstuff.md)).

Watch Falstaff's "whenever you gain food, gain 3 more" stacking with the food-on-play queens: it is the likeliest runaway loop in the deck.

## Cards

<!-- cards:begin (generated from cards.json by animal_kingdom.render.deck_docs) -->

### Legendary

| Card | × | Tags | Str | Text |
|---|---:|---|---:|---|
| **Queen Marabunta** | 1 | Colony, Queen | 4 | Battlecry: gain 4 food for each other friendly Colony unit. |
| **Vesper, Champion of the Hive** | 1 | Colony | 0 | Flight. Has +2 strength for each other friendly Colony unit. |
| **Queen Honoria** | 1 | Colony, Queen | 4 | Whenever you play a Colony unit, gain 4 food. |
| **Falstaff** | 1 | Colony | 3 | Flight. Whenever you gain food, gain 3 additional food. |

### Rare

| Card | × | Tags | Str | Text |
|---|---:|---|---:|---|
| **Nurse Bee** | 2 | Colony | 3 | Flight. Battlecry: if you control two copies of the same Colony unit, draw 2 cards. |
| **Nurse Bumblebee** | 2 | Colony | 3 | Flight. Battlecry: if you control 4 or more Colony units, draw 2 cards. |
| **Termite King** | 2 | Colony | 5 | Battlecry: if you control a Colony Queen, draw 1 card. |
| **Termite Queen** | 2 | Colony, Queen | 3 | Battlecry: you may play one additional non-Queen Colony unit this turn. |

### Common

| Card | × | Tags | Str | Text |
|---|---:|---|---:|---|
| **Queen Bee** | 3 | Colony, Queen | 3 | Battlecry: play a Worker unit. |
| **Guard Hornet** | 3 | Colony | 3 | Flight. Has +5 strength while you control 4 or more Colony units. |
| **Soldier Ant** | 3 | Colony | 2 | Battlecry: if you control 4 or more Colony units, remove an adjacent enemy. |
| **Worker Ant** | 3 | Colony, Worker | 1 | Battlecry: gain 12 food. |
| **Worker Wasp** | 3 | Colony, Worker | 3 | Flight. At the end of your turn, gain 3 food. |
| **Worker Bee** | 3 | Colony, Worker | 1 | Flight. Battlecry: gain 10 food; if you control another Worker, gain 10 more. |

<!-- cards:end -->
