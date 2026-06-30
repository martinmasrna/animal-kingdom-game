# Deck: RAMP

Ramp food, then spend it on huge `Costs 20 food` bodies (Bears / Megafauna / big Birds).
Landmarks + delayed effects fuel the ramp. 4-4-6 shape (4 legendary ×1, 4 rare ×2, 6 common ×3 = 30).
Source: user's offline Google Sheet (uploaded 2026-06-28). **Incomplete — has open `?` cells.**

## Legendary (×1) — names **PROVISIONAL** (assigned 2026-06-30; final flavor pass pending — alternates in `flavor-review.md` §3)
| Name | Tag | Str | Effect | Description |
|---|---|---:|---|---|
| **Methuselah** | Megafauna | 5 | Immovable. At the end of your turn, gain 10 food. | Colossal ancient tortoise. *(ramp engine + wall)* |
| **Borealis** | Bear | 10 | Apex Predator. Costs 20 food. | Giant polar bear. |
| **Aquila** | Bird | 8 | Flight. Apex Predator. Costs 20 food. | Giant harpy eagle. |
| **Bulwark** | Megafauna | 10 | Immovable. Costs 20 food. Battlecry: remove all adjacent enemy units. | Titanic rhino. *(anti-aggro stomp / fortress finisher)* |

## Rare (×2)
| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Polar Bear** | Bear | 8 | Apex Predator. |
| **Rhinoceros** | Megafauna | 6 | Battlecry: remove all adjacent enemies of strength 5 or less. *(proactive charge sweep)* |
| **Hippopotamus** | Megafauna | 6 | When an enemy unit is placed on an adjacent crossroad, remove it if its strength is 3 or less. *(reactive territorial deterrent; cost dropped)* |
| **Andean Condor** | Bird | 4 | Flight. Reveal top card of both decks. If yours has higher strength, draw it. |

## Common (×3)
| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Elephant** | Megafauna | 8 | Immovable. Costs 20 food. |
| **Grizzly Bear** | Bear | 7 | Battlecry: in 2 turns, remove a random adjacent enemy. |
| **Oxpecker** | Bird | 1 | Flight. Gain 1 food for each unit in your starting deck with strength 6 or more. |
| **Black Bear** | Bear | 5 | Battlecry: in 2 turns, draw 1 card. |
| **Fig Tree** | Landmark | 0 | Fragile. At the start of next turn, gain 20 food. |
| **Watering Hole** | Landmark | 0 | Fragile. At the start of next turn, draw a unit with strength 6 or more. |

---

## Open items — RESOLVED (2026-06-28)
- **2 legendaries filled:** colossal ancient tortoise (Megafauna 5, ramp engine + wall) and titanic rhino (Megafauna 10, anti-aggro stomp). Names still TBD.
- **Rhinoceros:** proactive AoE charge sweep (remove all adjacent ≤5).
- **Hippopotamus:** reworked Battlecry-sweep → reactive territorial deterrent (remove adjacent placements ≤3); **Costs 20 dropped** (now a free on-curve body).
- Removal suite reads cleanly: Rhino = proactive AoE, Hippo = reactive AoE, titanic rhino = proactive uncapped stomp. No cheap single-target removal (intentional — not Ramp's identity).

## New mechanics / systems this deck introduces
- **⚠ `Landmark` card type — NON-ANIMAL cards.** Fig Tree and Watering Hole are not animals (or things that become animals), which contradicts the `cards.md` §2 theme rule ("every card is an animal… no spells or other non-creature cards"). This is a new permitted category (functions like ramp "lands"). **Needs an explicit theme-rule decision** — relax the rule for Landmarks, or re-theme these as animals.
- **Food as a placement cost at scale:** multiple bodies "Costs 20 food". The ramp loop is: build food → spend on huge units. Same placement-cost gate already scoped for the engine (offer only if food ≥ cost; pay on placement).
- **`Apex Predator` is a KEYWORD, not vanilla** (corrected 2026-06-28): must be placed on top of another occupant and removes it instead of covering. Carried here by Polar Bear and both giant legendaries (alongside Costs 20). See README decision D for the full keyword + open ambiguities (strength gate, friendly targets, HQ capture).
- **New tags:** `Bear`, `Megafauna`, plus `Landmark` (type, above).
- **Delayed "in 2 turns" effects** (scheduler): Grizzly Bear (remove random adjacent enemy), Black Bear (draw). Landmarks use "at the start of next turn" (1-turn delay).
- **RNG removal:** Grizzly "remove a *random* adjacent enemy" — seeded RNG, reproducible.
- **Decklist-reading effect:** Oxpecker "gain 1 food for each unit in your *starting deck* with strength ≥6" — reads the fixed 30-card decklist composition (a per-deck constant), not board/hand. New: effects need access to the deck definition.
- **Reveal/compare across both decks:** Andean Condor "reveal top of both decks; if yours is higher strength, draw it" — peeks the opponent's top card (hidden-info interaction with per-seat view) and a strength comparison.
- **Strength-filtered draw/tutor:** Watering Hole "draw a unit with strength 6 or more."

## Flags (resolve in the all-at-once review)
- **Landmark / non-animal theme decision** — the headline item above.
- **Finish the 3 open cards** (2 legendaries + Rhinoceros).
- **Legendary names** — provisional (Methuselah / Borealis / Aquila / Bulwark, assigned 2026-06-30; flavor-lock pending). **Borealis** (giant polar bear) is deliberately distinct from the common **Polar Bear** (named-individual pattern).
- **Food cost vs food win tension:** food is both the ramp fuel (pay 20-costs) and a win condition (100). Worth watching in sim — is the deck ever incentivized to hoard to 100 vs spend? Likely fine, just noting.
- **"In 2 turns" timing:** counted in the actor's turns (resolves at the start of your turn after next)? Align with the existing scheduler convention.
- **Andean Condor info reveal:** revealing opponent's top card is public information for that moment — confirm the per-seat view exposes it correctly and the RNG/deck order stays deterministic.
