# Deck: RAMP

Ramp food, then spend it on huge `Costs 15 food` bodies (Bears / Megafauna / big Birds).
Delayed effects fuel the ramp. 4-4-6 shape (4 legendary ×1, 4 rare ×2, 6 common ×3 = 30).
Source: user's offline Google Sheet (uploaded 2026-06-28). **Incomplete — has open `?` cells.**

## Legendary (×1) — names **PROVISIONAL** (assigned 2026-06-30; final flavor pass pending — alternates in `flavor-review.md` §3)
| Name | Tag | Str | Effect | Description |
|---|---|---:|---|---|
| **Methuselah** | Megafauna | 3 | Immovable. At the end of your turn, gain 5 food. | Colossal ancient tortoise. *(ramp engine + wall; doc drift fixed 2026-07-15: said Str 5, `a27f0df` set it to 3)* |
| **Borealis** | Bear | 10 | Apex Predator. Costs 15 food. | Giant polar bear. |
| **Aquila** | Bird | 8 | Flight. Apex Predator. Costs 15 food. | Giant harpy eagle. |
| **Bulwark** | Megafauna | 10 | Immovable. Costs 15 food. Battlecry: remove all adjacent units. | Titanic rhino. *(anti-aggro stomp / fortress finisher; 2026-07-05 nerf: now clears friendly neighbours too — place with care)* |

## Rare (×2)
| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Polar Bear** | Bear | 8 | Apex Predator. |
| **Rhinoceros** | Megafauna | 6 | Battlecry: remove all adjacent enemies of strength 3 or less. *(2026-07-05: 5→3, the proactive Battlecry mirror of Hippopotamus; was strictly better than Jaguar)* |
| **Hippopotamus** | Megafauna | 6 | When an enemy unit is placed on an adjacent crossroad, remove it if its strength is 3 or less. *(reactive territorial deterrent; cost dropped)* |
| **Andean Condor** | Bird | 4 | Flight. Reveal top card of both decks. If yours has higher strength, draw it. |

## Common (×3)
| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Elephant** | Megafauna | 8 | Immovable. Costs 15 food. |
| **Grizzly Bear** | Bear | 6 | Battlecry: in 2 turns, remove a random adjacent enemy. *(2026-07-05: 7→6 — a common with a str-7 body AND an effect outclassed the vanilla-Lion-7 baseline)* |
| **Oxpecker** | Bird | 1 | Flight. Gain 1 food for each unit in your starting deck with strength 6 or more. |
| **Black Bear** | Bear | 5 | Battlecry: in 2 turns, draw 2 cards. *(doc drift fixed 2026-07-15: said "draw 1"; `black_bear_draw` has been 2 since the 2026-07-13 baseline-ruler tuning)* |
| **Sloth** | — | 3 | In 2 turns, gain 20 food. *(2026-07-15: replaces Fig Tree's burst-food job when Landmarks were cut. Flavor = slow digestion, not hibernation. Deliberately **not** Fragile — sloths aren't — and **not** Immovable, which would make the payout unanswerable and shadow Methuselah. Its counterplay is the timed-effect rule: cover it with a 4+ and the timer suspends. Kept under STR 6 so it doesn't feed Oxpecker.)* |
| **Cape Buffalo** | Megafauna | 7 | — *(vanilla body; 2026-07-15: replaces Watering Hole, whose "tutor a 6+" job died when the Draw action went to 2 cards. **Not inert:** STR 7 clears Oxpecker's threshold, taking ramp's ≥6 count 15→18 and Oxpecker's output 45→54.)* |

---

## Open items — RESOLVED (2026-06-28)
- **2 legendaries filled:** colossal ancient tortoise (Megafauna 5, ramp engine + wall) and titanic rhino (Megafauna 10, anti-aggro stomp). Names still TBD.
- **Rhinoceros:** proactive AoE charge sweep (remove all adjacent ≤3) — the Battlecry mirror of Hippopotamus.
- **Hippopotamus:** reworked Battlecry-sweep → reactive territorial deterrent (remove adjacent placements ≤3); **Costs 20 dropped** (now a free on-curve body).
- Removal suite reads cleanly: Rhino = proactive AoE, Hippo = reactive AoE, titanic rhino = proactive uncapped stomp. No cheap single-target removal (intentional — not Ramp's identity).

## New mechanics / systems this deck introduces
- ~~**⚠ `Landmark` card type — NON-ANIMAL cards.**~~ **RESOLVED 2026-07-15: cut.** Fig Tree and Watering Hole were the only two Landmarks, and they contradicted the `cards.md` §2 theme rule ("every card is an animal… no spells or other non-creature cards"). The theme rule won: both cards were removed and the game commits to animals only. Nothing is a Landmark now, so `Card.is_unit` is always True and the type machinery is dormant (→ Engine backlog). Their jobs were re-homed onto **Sloth** (burst food) and **Cape Buffalo** (a big body) above.
- **Food as a placement cost at scale:** multiple bodies "Costs 15 food". The ramp loop is: build food → spend on huge units. Same placement-cost gate already scoped for the engine (offer only if food ≥ cost; pay on placement).
- **`Apex Predator` is a KEYWORD, not vanilla** (corrected 2026-06-28): must be placed on top of another occupant and removes it instead of covering. Carried here by Polar Bear and both giant legendaries (alongside Costs 15). See README decision D for the full keyword + open ambiguities (strength gate, friendly targets, HQ capture).
- **New tags:** `Bear`, `Megafauna`. *(`Landmark` retired 2026-07-15 — see above.)*
- **Delayed "in 2 turns" effects** (scheduler): Grizzly Bear (remove random adjacent enemy), Black Bear (draw 2), **Sloth** (gain 20 food). ⚠ **The timer is the unit's, not the board's** — since the 2026-07-15 ruling it advances only while that unit is the **top** of its crossroad (buried = suspended, removal = cancelled, bounce = reset). That rule *is* Sloth's counterplay, and it's why Sloth needs no Fragile. See [`../../rules/overview.md`](../../rules/overview.md) §9.1.
- **RNG removal:** Grizzly "remove a *random* adjacent enemy" — seeded RNG, reproducible.
- **Decklist-reading effect:** Oxpecker "gain 1 food for each unit in your *starting deck* with strength ≥6" — reads the fixed 30-card decklist composition (a per-deck constant), not board/hand. New: effects need access to the deck definition.
- **Reveal/compare across both decks:** Andean Condor "reveal top of both decks; if yours is higher strength, draw it" — peeks the opponent's top card (hidden-info interaction with per-seat view) and a strength comparison.
- ~~**Strength-filtered draw/tutor:** Watering Hole "draw a unit with strength 6 or more."~~ *(Card cut 2026-07-15. The engine's `draw_filtered_random(..., "strength_min:N")` spec survives with no caller — see the Engine backlog's dormant-machinery item.)*

## Flags (resolve in the all-at-once review)
- **Landmark / non-animal theme decision** — the headline item above.
- **Finish the 3 open cards** (2 legendaries + Rhinoceros).
- **Legendary names** — provisional (Methuselah / Borealis / Aquila / Bulwark, assigned 2026-06-30; flavor-lock pending). **Borealis** (giant polar bear) is deliberately distinct from the common **Polar Bear** (named-individual pattern).
- **Food cost vs food win tension:** food is both the ramp fuel (pay the 15-costs) and a win condition (100). **Sharper than "just noting" (revisited 2026-07-15):** the 6 costed copies total **90 food against a 100 win**, so the deck can deploy its payoffs *or* threaten the food win — not both. At the originally-designed 20 it was 120 vs 100, i.e. unaffordable in full; `a27f0df`'s cut to 15 is what relieved that. Feeds Decision H.
- **"In 2 turns" timing:** counted in the actor's turns (resolves at the start of your turn after next)? Align with the existing scheduler convention.
- **Andean Condor info reveal:** revealing opponent's top card is public information for that moment — confirm the per-seat view exposes it correctly and the RNG/deck order stays deterministic.
