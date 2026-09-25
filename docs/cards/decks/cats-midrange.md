# Deck: CATS MIDRANGE TEMPO

Mono-Cat tribal. 4-4-6 shape (4 legendary ×1, 4 rare ×2, 6 common ×3 = 30).
Source: user's offline Google Sheet (uploaded 2026-06-28).
**card-balance-todo applied 2026-07-04:** Prince Leo/Princess Lea 4→3, Queen Adira 6→5 (cats was
the clear balance outlier at ~69-72% corrected winrate; trims only, no effect changes). See
`../../balance/card-balance-todo.md`.

## Legendary (×1)
| Name | Tag | Str | Effect | Description |
|---|---|---:|---|---|
| **Prince Leo** | Cat | 3 | Battlecry: you may immediately play Princess Lea from your hand or deck. | Lion prince. Young, strong, quick, and always by his twin sister's side. |
| **Princess Lea** | Cat | 3 | Battlecry: you may immediately play Prince Leo from your hand or deck. | Lion princess. Young, strong, quick, and always by her twin brother's side. |
| **King Theron** | Cat | 8 | When one of your Cats covers an enemy unit, remove that enemy. | Lion king. |
| **Queen Adira** | Cat | 5 | When one of your Cats removes an enemy unit, draw 1 card. | Lion queen. |

## Rare (×2)
| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Jaguar** | Cat | 5 | Battlecry: remove an adjacent enemy of strength 5 or less. |
| **Serval** | Cat | 2 | Battlecry: remove an adjacent enemy of strength 6 or more. |
| **Snow Leopard** | Cat | 6 | Your other Cats may be placed onto enemy units of equal or lower strength. |
| **Black Panther** | Cat | 6 | Cannot be targeted by enemy special effects. |

## Common (×3)
| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Lion** | Cat | 7 | *(vanilla — pride anchor)* |
| **Lynx** | Cat | 3 | Battlecry: if you control another Cat, draw 1. |
| **Caracal** | Cat | 4 | Battlecry: if placed on top of an enemy unit, draw 1 card. |
| **Tiger** | Cat | 7 | Apex Predator. |
| **Cougar** | Cat | 6 | You may place this adjacent to any Cat you control, ignoring connection. |
| **House Cat** | Cat | 1 | Battlecry: if you control another Cat, play one more Cat from your hand (other than House Cat). |

---

## Flags / engine notes (for M2 reconciliation)
- **King Theron** — new *team-wide* trigger: any of your Cats covering an enemy → remove the covered unit. Combos hard with **Snow Leopard** (cover equal/lower) → cover-then-remove. Need: does "one of your Cats" include Theron itself? (assume yes). Once-per-turn? (not stated → assume unlimited). `TODO(rules)`.
- **Queen Adira** — new team-wide trigger: any of your Cats removing an enemy → draw 1. Not stated once-per-turn → assume unlimited; flag. Interacts with Theron (cover→remove→draw chain).
- **Snow Leopard** — static anthem while in play: your other Cats may cover equal-or-lower-strength enemies.
- **Tiger** has the **Apex Predator** keyword (not vanilla) — must land on an occupant and removes it. See README decision D for the keyword + open ambiguities.
