# Deck: EGG CONTROL

Snake/Bird/Egg tribal control built around a **draw–shuffle–remove → food** engine.
4-4-6 shape (4 legendary ×1, 4 rare ×2, 6 common ×3 = 30).
Source: user's offline Google Sheet (uploaded 2026-06-28).

## Legendary (×1) — names still placeholders
| Name | Tag | Str | Effect | Description |
|---|---|---:|---|---|
| **[NAME]** | Snake | 6 | Whenever a card is drawn, shuffled or removed, gain 1 food. | Ancient snake, inspired by Ouroboros. |
| **[NAME]** | Snake | = | This unit's strength is equal to the number of removed units. | A giant anaconda, trying to swallow everything. |
| **[NAME]** | Bird | 5 | Flight. When this is removed, shuffle it back to your deck. | Red/orange/yellow, fire-colored bird looking like a Phoenix. |
| **[NAME]** | Egg | 0 | Fragile. At the start of your turn, draw a card. | Golden egg. |

## Rare (×2)
| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Rattlesnake** | Snake | 6 | Whenever you shuffle a card, gain 5 food. |
| **Egg Eater** | Snake | 4 | Whenever an Egg is removed, gain 10 food. |
| **Black Swan** | Bird | 5 | When you draw this, both players remove a random card from their hand. |
| **Vulture** | Bird | 4 | Flight. Whenever a card is removed, gain 2 food. |

## Common (×3)
| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Eagle** | Bird | 5 | Flight. |
| **Owl** | Bird | 2 | Flight. Battlecry: look at the top 3 cards; draw 1 and shuffle the rest. |
| **Anaconda** | Snake | 7 | Apex Predator. |
| **Raven** | Bird | 2 | Flight. Battlecry: draw 2, then shuffle 2 cards back. |
| **Bird Egg** | Egg | 0 | Fragile. After 2 turns, remove this and draw 2 Birds. |
| **Snake Egg** | Egg | 0 | Fragile. After 2 turns, remove this and draw 2 Snakes. |

---

## New mechanics / tags this deck introduces
- **New tags:** `Snake`, `Egg` (`Egg` is now a creature-type tag, not just a one-off card).
- **"Shuffle a card" as a discrete, food-generating event.** Multiple cards key off it (Ouroboros legendary, Rattlesnake, Phoenix-on-remove, Owl, Raven). Need a precise definition: is shuffling N cards back N events or 1? (Raven "shuffle 2 back", Owl "shuffle the rest", Phoenix "shuffle it back").
- **Event-driven food** triggers on draw / shuffle / remove (Ouroboros @1, Rattlesnake @5/shuffle, Vulture @2/remove, Egg Eater @10/egg-removed). The deck's whole food plan is this engine, not recurring regions.
- **`ON_DRAW` trigger (from hand, not placed):** Black Swan "When you draw this…" — a new event type; fires on draw, not on placement.
- **Tag-filtered draw / tutoring:** "draw 2 Birds" / "draw 2 Snakes" (Bird Egg / Snake Egg hatch into typed draws).
- **Recursion to deck:** Phoenix legendary shuffles itself back to deck on removal.
- **Egg sub-engine:** Fragile eggs get removed easily (covering/hatching) → Egg Eater pays 10 food each time; eggs hatch into typed draws or (golden egg) draw every turn.

## Flags (resolve in the all-at-once review)
- **Legendary names:** three of four legendaries are still `[NAME]` placeholders. The "giant anaconda" / "Ouroboros snake" / "Phoenix" / "golden egg" notes are **art/flavor descriptions, not names** — real names TBD. The dynamic-snake legendary is a different card from the common **Anaconda** (legendaries are the named-individual exception). *(Card-identity is globally unique — resolved, see README decision A.)*
- **Golden Egg "at the start of each turn, draw a card":** each of *your* turns, or *both* players' turns? Flag.
- **"Whenever a card is drawn":** whose draws — yours only, or any? Same scope question for "shuffled" / "removed" (your cards vs all).
- **Once-per-turn caps:** none of the event-food triggers state a cap. With Ouroboros + Rattlesnake + a shuffle-heavy turn this could spike hard — likely a sim/tuning dial.
- **Food numbers** (Egg Eater 10, Rattlesnake 5, Vulture 2/remove) are new and want sim tuning against region output and `win_food`.
- **Black Swan symmetric discard:** "both players remove a random card from their hand" — confirm discard-to-shared-discard, seeded RNG (the `discard_random` op already exists).
- **Eagle / Raven / Owl / Vulture** are all Flight birds here; just note for the card-identity decision above.
