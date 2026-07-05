# Deck: COLONY FOOD SWARM

Mono-`Colony` insect tribal. Go wide, convert a swarm into food. Heavy Flight.
4-4-6 shape (4 legendary ×1, 4 rare ×2, 6 common ×3 = 30).
Source: user's offline Google Sheet (uploaded 2026-06-28).

## Legendary (×1) — names **PROVISIONAL** (assigned 2026-06-30; final flavor pass pending — alternates in `flavor-review.md` §3)
| Name | Tag | Str | Effect | Description |
|---|---|---:|---|---|
| **Queen Marabunta** | Colony | 4 | Battlecry: gain 4 food for each other friendly Colony unit. | Ant queen. |
| **Vesper, Champion of the Hive** | Colony | 0 | Flight. Has +2 strength for each other friendly Colony unit. | Deadly hornet. *(2026-07-05: body 2→0)* |
| **Queen Honoria** | Colony | 4 | Whenever you play a Colony unit, gain 4 food. | Bee queen. *(2026-07-05: 5/5→4/4)* |
| **Falstaff** | Colony | 3 | Flight. Whenever you gain food, gain 3 additional food. | Hilariously fat bumblebee. |

## Rare (×2)
| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Nurse Bee** | Colony | 2 | Flight. Battlecry: if you control two copies of the same Colony unit, draw 2 cards. |
| **Nurse Bumblebee** | Colony | 3 | Flight. Battlecry: if you control 5 or more Colony units, draw 2 cards. *(2026-07-05: body 2→3)* |
| **Termite King** | Colony | 5 | Battlecry: if you control a Colony Queen, draw 1 card. |
| **Termite Queen** | Colony | 3 | Battlecry: you may play one additional non-Queen Colony unit this turn. *(2026-07-05: body 5→3)* |

## Common (×3)
| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Queen Bee** | Colony | 2 | Battlecry: play a Worker unit. |
| **Guard Hornet** | Colony | 3 | Flight. Has +5 strength while you control 5 or more Colony units. |
| **Soldier Ant** | Colony | 2 | Battlecry: if you control 5 or more Colony units, remove an adjacent enemy. |
| **Worker Ant** | Colony | 1 | Battlecry: gain 12 food. |
| **Worker Wasp** | Colony | 3 | Flight. At the end of your turn, gain 3 food. |
| **Worker Bee** | Colony | 1 | Flight. Battlecry: gain 10 food; if you control another Worker, gain 10 more. *(2026-07-05: 5/5→10/10)* |

---

## New mechanics / systems this deck introduces
- **New tag:** `Colony` (entire deck). Mono-tribal swarm.
- **⚠ Sub-roles beneath the species tag — `Queen` and `Worker`.** Effects reference these as categories, so the data model needs a second classification layer, not just the single species-family tag:
  - **Queen** members: the two legendary queens (ant, bee), Termite Queen, Queen Bee. Referenced by Termite King ("control a Colony Queen") and Termite Queen ("non-Queen").
  - **Worker** members: Worker Ant, Worker Wasp, Worker Bee. Referenced by Queen Bee ("play a Worker unit") and Worker Bee ("another Worker").
  - Termite **King** is a King, not a Queen (doesn't satisfy its own Queen check).
  - Decide: explicit sub-tag field per card (e.g. `subtags: [Queen]`) vs. inferring from name. Recommend explicit.
- **Count-of-tag dynamic strength:** Champion of the Hive = +2 str per other Colony; Guard Hornet = +5 while ≥5 Colony. New `effective_strength` variants (linear-per-tag, and threshold buff).
- **"Whenever you play a Colony unit" trigger** (bee queen) — fires on each tagged placement, not just self-placement.
- **Recurring per-unit end-of-turn food:** Worker Wasp "at the end of your turn, gain 3 food" — food income from a unit on the board, separate from regions.
- **Food rider** (fat bumblebee): "whenever you gain food, gain 3 additional" — additive multiplier on the swarm's food output. Stacks conceptually with the bee queen + worker food.
- **Duplicate-copy condition:** Nurse Bee "if you control two copies of the same Colony unit" — a new board condition (≥2 of an identical card in play).
- **Board-size gates:** "if you control 5 or more Colony units" (Nurse Bumblebee draw, Soldier Ant removal, Guard Hornet buff).
- **Tag/subtype-constrained extra placement:** Queen Bee "play a Worker unit"; Termite Queen "play one additional non-Queen Colony unit this turn."

## Flags (resolve in the all-at-once review)
- **Sub-role data model (Queen/Worker)** — the headline item above; needs a schema decision.
- **Legendary names — provisional set assigned 2026-06-30** (Queen Marabunta / Vesper, Champion of the Hive / Queen Honoria / Falstaff; alternates in `flavor-review.md` §3, flavor-lock pending). The bee-queen legendary **Queen Honoria** is a different card from the common **Queen Bee** (legendary = named individual). *(No collision — README decision A.)*
- **"Play a Worker unit" / "play one additional … unit" — from where?** Hand only, or hand-or-deck (tutor)? Assume hand unless stated. Is it mandatory or "may"? Queen Bee says "play a Worker" (looks mandatory; can it fizzle if no Worker in hand?). Flag.
- **Champion / Guard dynamic strength snapshot timing** — live at comparison time (consistent with existing dynamic-strength rule) vs. on placement. With a swarm that grows/shrinks mid-turn this matters for covering math.
- **Once-per / stacking on food riders:** fat bumblebee "+3 whenever you gain food" — does it apply to its own and the bee queen's gains in the same chain? Watch for runaway loops; sim/tuning dial.
- **Food numbers** (4/each, 5/play, 8, 5+5, 3/turn, +3 rider) are new and want tuning vs region output and `win_food`.
- **Soldier Ant "remove an adjacent enemy"** — no strength cap stated (unlike most removal). Confirm it's unconditional removal once the 5-Colony gate is met. Flag.
- **Legendary names** — provisional (assigned 2026-06-30); see the legendary table + the `docs/STATUS.md` flavor-lock item.
