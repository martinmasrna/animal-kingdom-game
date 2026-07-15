# Deck: EGG CONTROL

Snake/Bird/Egg tribal control built around a **draw–shuffle–remove → food** engine.
4-4-6 shape (4 legendary ×1, 4 rare ×2, 6 common ×3 = 30).
Source: user's offline Google Sheet (uploaded 2026-06-28).
**card-balance-todo applied 2026-07-04:** Goliath demoted to rare; Black Swan promoted to
legendary (now capped "first time each turn"); Vulture shelved (see
`../card-candidates.md`); Stoop moved in from Aggro as the rare "Peregrine Falcon" (name
provisional, str 6→4, threshold 6→4). Shape stays 4-4-6. See `../../balance/card-balance-todo.md`.

## Legendary (×1) — names **PROVISIONAL** (assigned 2026-06-30; final flavor pass pending — alternates in `flavor-review.md` §3)
| Name | Tag | Str | Effect | Description |
|---|---|---:|---|---|
| **Eon** | Snake | 7 | Whenever a card is drawn, shuffled or removed, gain 1 food. | Ancient snake, inspired by Ouroboros. |
| **Ember** | Bird | 6 | Flight. When this is removed, shuffle it back to your deck. | Red/orange/yellow, fire-colored bird looking like a Phoenix. |
| **Aurum** | Egg | 0 | Fragile. At the start of your turn, draw a card. | Golden egg. |
| **Black Swan** | Bird | 3 | The first time each turn you draw Black Swan, your opponent removes a random card from their hand. | *(promoted from rare, card-balance-todo 2026-07-04)* |

## Rare (×2)
| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Rattlesnake** | Snake | 0 | Whenever you shuffle a card, gain 1 strength (wherever this is). |
| **Egg Eater** | Snake | 4 | Whenever an Egg is removed, gain 10 food. |
| **Goliath** | Snake | = | This unit's strength is equal to the number of removed units. *(demoted from legendary, card-balance-todo 2026-07-04)* |
| **Peregrine Falcon** *(id `stoop`)* | Bird | 4 | Flight. Battlecry: remove an adjacent enemy of strength 4 or less. *(moved in from Aggro as a rare, card-balance-todo 2026-07-04; name provisional)* |

## Common (×3)
| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Eagle** | Bird | 5 | Flight. |
| **Owl** | Bird | 2 | Flight. Battlecry: look at the top 3 cards; draw 1 and shuffle the rest. |
| **Anaconda** | Snake | 7 | Apex Predator. |
| **Raven** | Bird | 2 | Flight. Battlecry: draw 3 cards, then shuffle 2 cards back. |
| **Bird Egg** | Egg | 0 | Fragile. After 2 turns, remove this and draw 2 Birds. |
| **Snake Egg** | Egg | 0 | Fragile. After 2 turns, remove this and draw 2 Snakes. |

---

## New mechanics / tags this deck introduces
- **New tags:** `Snake`, `Egg` (`Egg` is now a creature-type tag, not just a one-off card).
- **"Shuffle a card" as a discrete, food-generating event.** Multiple cards key off it (Ouroboros legendary, Rattlesnake, Phoenix-on-remove, Owl, Raven). Need a precise definition: is shuffling N cards back N events or 1? (Raven "shuffle 2 back", Owl "shuffle the rest", Phoenix "shuffle it back").
- **Event-driven growth/food** triggers on draw / shuffle / remove (Ouroboros @1 food, Rattlesnake +1 strength/shuffle wherever it is, Vulture @5 food/remove, Egg Eater @10 food/egg-removed). The deck's whole food plan is this engine, not recurring regions.
- **`ON_DRAW` trigger (from hand, not placed):** Black Swan "When you draw this…" — a new event type; fires on draw, not on placement.
- **Tag-filtered draw / tutoring:** "draw 2 Birds" / "draw 2 Snakes" (Bird Egg / Snake Egg hatch into typed draws).
- **Recursion to deck:** Phoenix legendary shuffles itself back to deck on removal.
- **Egg sub-engine:** Fragile eggs get removed easily (covering/hatching) → Egg Eater pays 10 food each time; eggs hatch into typed draws or (golden egg) draw every turn.

## Flags (resolve in the all-at-once review)
- **Legendary names — provisional set assigned 2026-06-30** (Eon / Goliath / Ember / Aurum; alternates in `flavor-review.md` §3, flavor-lock pending). The "giant anaconda" / "Ouroboros snake" / "Phoenix" / "golden egg" notes remain **art/flavor descriptions**. The dynamic-snake legendary **Goliath** is a different card from the common **Anaconda** (legendaries are the named-individual exception). *(Card-identity is globally unique — resolved, see README decision A.)*
- **Golden Egg "at the start of each turn, draw a card":** each of *your* turns, or *both* players' turns? Flag.
- **"Whenever a card is drawn":** whose draws — yours only, or any? Same scope question for "shuffled" / "removed" (your cards vs all).
- **Once-per-turn caps:** none of the event-food triggers state a cap. With Ouroboros and a busy event turn this could spike hard — likely a sim/tuning dial.
- **Food numbers** (Egg Eater 10) are new and want sim tuning against region output and `win_food`.
  Vulture's 5/remove is shelved with the card (see `../card-candidates.md`) but its `config.py`
  dial (`vulture_food`/`cap_vulture`) is left in place, dormant, for if it returns.
- **Black Swan hand-remove:** the opponent removes a random card from their hand into the shared Remove
  Pile using seeded RNG; now hard-capped to the first trigger each turn (card-balance-todo).
- **Eagle / Raven / Owl** are all Flight birds here; just note for the card-identity decision above.
