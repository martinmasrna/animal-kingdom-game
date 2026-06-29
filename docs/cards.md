# 1. Document Scope

This document describes the proposed cards for the **0.0.1** version of the game, plus the general guidelines used to design them. It is the companion to `overview.md` (rules) — this file covers the card pool and design conventions.

---

# 2. Card Theme and Semantics

Staying true to the core theme — **Animal Kingdom** — is critical. Every card is an **animal, or something that becomes one** (an egg, a larva) — there are **no spells** or other non-creature cards. Strength and effects should make sense in real-world terms:

- birds fly over enemy lines;
- elephants are strong, immovable defenders;
- vultures scavenge dead/discarded units;
- raccoons steal;
- lemmings and locusts swarm; and so on.

When in doubt, let the animal's real behaviour suggest the mechanic.

## 2.1 Rarity and naming

Rarity maps onto how exotic the animal is, and onto the name:

- **Common** — everyday, widely-known real animals (lion, lynx, house cat).
- **Rare** — rarer / more exotic real animals (jaguar, snow leopard, serval).
- **Legendary** — a **specific, named individual** real animal given a proper name (e.g. the twin cheetahs of the Cats deck). The animal stays real — *no invented creatures* — but the **name** may carry a light mythic/folklore flavor, evoking legend without directly referencing it (no "Bastet", no "Phoenix"). Hardest tier to design: a unique effect *and* a fitting marquee name.

**One species per pool — among commons and rares.** Each real animal appears at most once across the common and rare tiers; subspecies, sex, and age variants count as the *same* species there (e.g. no Tiger *and* Siberian Tiger). **Legendaries are exempt:** a legendary is a *named individual*, set apart by a unique design and its own lore, so it may reuse a species that appears elsewhere — a named legendary lion can sit alongside the common Lion (the plan for bears, birds, and cats alike). Deliberately designed pairs like the Cheetah twins are also fine.

---

# 3. Deck Archetypes

There are no classes or factions. Any unit may be combined with any other; the only roster restrictions are the copy limits (see `overview.md`). Archetypes are expected to **emerge naturally** from card synergies rather than be enforced. For 0.0.1 we are designing around four core archetypes:

| # | Archetype |
|---|---|
| 3.1 | Aggro |
| 3.2 | Control |
| 3.3 | Combo |
| 3.4 | Midrange |

## 3.5 Balanced Metagame (Rock-Paper-Scissors)

| Archetype | Main win condition | Beats | Loses to |
|---|---|---|---|
| Aggro | rush the enemy base, OR quickly control multiple regions | Combo | Control |
| Control | remove enemy threats and grind out value | Aggro | Combo |
| Combo | absorb pressure, assemble synergy pieces, win in 1–3 big turns | Control | Aggro |
| Midrange | flexible, adapts to the opponent | 50/50 vs. all | 50/50 vs. all |

---

# 4. Card Conventions

These conventions keep cards consistent and machine-/human-readable.

## 4.1 Stat-line format

Cards are listed as a table per rarity:

| Name | Tag | Str | Effect |

- **Str** is the unit's strength, `0`–`10` (some special units use other values; see Chameleon).
- **Effect** is written as plain reminder text, except where a **keyword** (§4.4) applies.

## 4.2 Species tags

Every unit carries one **species-family tag**. Tags are the hook for future synergies ("for each other *Primate* you control…"). Starter taxonomy (extensible):

`Rodent · Insect · Fish · Primate · Canine · Cat · Bird · Reptile · Rabbit`

Tags on non-Aggro cards below are provisional until those archetypes are designed.

## 4.3 Behavioral roles (design guide — not printed on cards)

Roles describe *how* a unit plays and guide which effects it should get. They are **not** printed tags. When a role's pattern recurs often enough, it gets promoted to a **keyword** (§4.4).

Current roles: `Swarm · Feeder (rewards covering enemies) · Striker/Reach · Anchor/Defender · Scavenger · Disruptor · Engine/Value`.

## 4.4 Keywords (registry)

A keyword is a *reusable, defined* mechanic with a printed name. Only the following are official keywords:

- **Flight** — ignores the connection-to-HQ requirement when placed.
- **Immovable** — cannot be removed or moved by special effects.
- **Fragile** — when another unit is placed on top of this unit, remove this unit (it does not survive under the stack).
- **Battlecry** *(provisional name — see `todo.md`)* — an effect that resolves when the unit is placed. Most "When placed…" effects are Battlecries; we keep writing them out as "When placed" until the keyword name is finalized.

One-off, single-card effects do **not** get a keyword name — they are written as plain text. (e.g. Honey Badger's cover ability is unique and stays plain text.)

## 4.5 Food as a card resource

Food is normally **recurring** income from controlled regions (`overview.md` §10). Card effects may also touch food directly:

- **One-off gain** — e.g. Army Ant grants food on a wide turn.
- **Cost** — e.g. Raven costs food to play.

These are fine because they are one-shot, not recurring. All food numbers (region output, win threshold, card gains/costs) live on **one shared scale**.

### Food Economy Constants (v0)

Starting values for the simulator to tune (see `todo.md`). This table is the **single source of truth**; the card rows below quote the resulting numbers, and the engine mirrors these in `config.py`. Design hierarchy: **regions are the backbone**, one-off `F` is an **accelerant** (a ~6-card food package reaches only ~half the threshold), and Hibernating Bear is the **combo finish**.

| Constant | v0 value | Used by |
|---|---:|---|
| Win threshold (`win_food`) | 100 | Map A (`maps.md`) |
| Region output — flank / center | 10 / 20 per turn | Map A (`maps.md`) |
| `F` — plain / conditional rider | 4 | Army Ant, Vervet Monkey, Caracal |
| low `F` | 3 | Wild Boar |
| medium `F` | 5 | Chipmunk |
| high `F` | 8 | Squirrel, Honeybee (base) |
| Honeybee Insect bonus | +4 | Honeybee |
| Queen Bee (additive, per food gain) | +3 | Queen Bee ⚠ stacking — watch |
| Driver Ant Queen (per unit you control) | 2 | Driver Ant Queen ⚠ scales with board |
| Raven cost | 12 | Raven |
| Hibernating Bear | ×2 payout, 2-turn delay | Hibernating Bear |

⚠ = values most likely to need sim attention (see `todo.md`).

---

# 5. Aggro Units

## 5.1 Identity (locked for 0.0.1)

- **Engine:** chained placements + cheap swarm bodies. Aggro develops *faster than 1 unit/turn* by going wide.
- **Strength:** mostly low. Fragile bodies are the price of tempo — and the reason Aggro loses to Control (who covers/removes them).
- **Removal:** minimal. Aggro races, it doesn't fight. The only removal is the **Wasp** (a rare, and self-sacrificing).
- **Win conditions:** both — rush the enemy HQ *and* flood/surround regions for the food win.
- **Food:** embraced as a one-off lever (Army Ant, Vervet Monkey) to push the region/food win.
- **Tag clusters:** a small **Primate** sub-tribe (Vervet Monkey + Baboon) demonstrates species-tag synergy and is extensible.

## 5.2 Legendary Aggro Units *(2 slots — locked)*

| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Nile Crocodile** | Reptile | =units | This unit's strength is equal to the number of units you control. |
| **Queen Ant** | Insect | 3 | When placed, gain **2** food for each unit you control. |

Both are **payoffs**, not engines — they reward a board you've already built wide and do little when you're behind:

- **Nile Crocodile** is the HQ-rush answer: Aggro normally can't *cover* the fat unit defending an enemy HQ (all low-strength bodies), so this grows with your swarm until it can out-muscle that defender and capture. Still needs a connected path and dies to removal.
- **Queen Ant** converts a wide board straight into food-win progress. *(Tuning fork: "each unit" vs. "each Insect" — keeping it "each unit" for now so it isn't deck-warping.)*

## 5.3 Rare Aggro Units *(3 slots — locked)*

| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Wild Dogs** | Canine | 1 | When placed, immediately play one more unit from your hand. |
| **Wasp** | Insect | 2 | When placed, you may remove this unit to destroy an adjacent enemy unit. |
| **Spotted Hyena** | Canine | 3 | May be placed onto an enemy unit of any strength (ignoring the covering rule) if you control at least **4** other units. |

**Spotted Hyena** is the lower-rarity, conditional cousin of the Crocodile / Honey Badger theme — *with the numbers, the clan pulls down anything*. v0 threshold **4** other units (the balance dial — sim should sweep ~3–5).

## 5.4 Common Aggro Units *(7–8 slots; 7 locked, ~1 flex open)*

| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Lemming** | Rodent | 1 | When placed, you may also play every other Lemming from your hand. |
| **Rat** | Rodent | 1 | When placed, if you control 3 or more other units, draw 1. |
| **Army Ant** | Insect | 1 | When placed, if you have already placed another unit this turn, gain **4** food. |
| **Piranha** | Fish | 2 | When placed onto an enemy unit, draw 1. |
| **Honey Badger** | — | 3 | May be placed onto an enemy unit of *equal or lower* strength (instead of strictly lower). |
| **Vervet Monkey** | Primate | 1 | When placed, if you control another Primate, gain **4** food. |
| **Baboon** | Primate | 4 | When placed, if you control another Primate, draw 1. |

*Flex slot:* likely a third Primate or a cheap reach body — pending the legendary HQ-rush design.

---

# 6. Control Units

## 6.1 Identity (locked for 0.0.1)

- **Plan:** grind / attrition — out-value and exhaust the opponent, then convert with the **food** win (holding regions) or a **late HQ capture**.
- **Engine:** efficient removal + durable high-strength bodies; moderate card advantage from clean trades and outlasting.
- **Food:** used **sparingly** as a *cost* on premium cards (hold regions → bank food → buy power), not an archetype-wide tax.
- **Matchups:** beats Aggro (shreds the fragile swarm), loses to Combo (too slow to stop the over-the-top turn).
- **New levers in use:** reactive removal (triggers on the opponent's placement), removal-by-covering, hand disruption (exhaust), death-triggered draw.

## 6.2 Legendary Control Units *(2 slots — locked)*

| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Raven** | Bird | 6 | Costs **12** food to play. When placed, draw 3 cards. |
| **Anaconda** | Reptile | =discard | This unit's strength is equal to the number of units in the discard. |

- **Raven** is the food → knowledge value bomb: a deliberate, food-gated refuel that powers the grind. Pairs thematically with the Vulture rare (the clever-bird value/scavenger pair).
- **Anaconda** is the **attrition payoff**: the grindier the game, the bigger it gets, until it can wall a lane or capture. It scales with *total carnage* (the discard) — the mirror of Aggro's Nile Crocodile, which scales with *your own board*.

## 6.3 Rare Control Units *(5 slots — over the 3-rare target; anti-swarm removal moved up from common)*

| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Vulture** | Bird | 2 | Whenever an enemy unit is removed, draw 1 *(once per turn)*. |
| **Matriarch Elephant** | — | 8 | **Immovable.** |
| **Giant Tortoise** | — | 6 | Cannot be covered by enemy units. |
| **Hippopotamus** | — | 6 | When an enemy unit is placed on an adjacent crossroad, remove it if its strength is 3 or less. |
| **Rhinoceros** | — | 6 | When placed, remove all enemy units of strength 3 or less adjacent to this unit. |

## 6.4 Common Control Units *(7 slots — locked)*

| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Gray Wolf** | Canine | 4 | When placed, remove an adjacent enemy of strength 3 or less. |
| **Boa Constrictor** | Reptile | 4 | When placed onto an enemy unit, remove that unit instead of stacking on it. |
| **Raccoon** | — | 2 | When placed, the opponent discards a random card. |
| **Cape Buffalo** | — | 6 | When this unit is removed, draw 1. |
| **Owl** | Bird | 3 | **Flight.** When placed, look at the top 3 cards of your deck; draw 1 and put the rest on the bottom. |
| **Jackal** | Canine | 3 | When placed, return a unit from the discard to the top of your deck. |
| **Coyote** | Canine | 3 | When placed, if you control another Canine, draw 1. |

---

# 7. Combo Units

## 7.1 Identity (locked for 0.0.1)

- **Plan:** stall and **hoard food**, then drop the **Hibernating Bear** (eat your hoard → double it two turns later) to vault past the food threshold in one swing.
- **Engine:** heavy draw + a tutor (Octopus) to assemble the pieces.
- **vs Aggro:** cheap stall bodies plus a strength-agnostic defensive trap (Pufferfish) to protect the HQ during the 2-turn payoff window; still loses to raw speed.
- **Resilience:** deliberately mixed — fragile/telegraphed pieces (Egg, Queen Bee, the Bear's 2-turn window) balanced with some recursion (Opossum) and tutoring.
- **Identity cost:** a linear, high-risk/high-reward "draw the Bear or fizzle" deck — accepted, and softened by the Octopus tutor + deep draw shell.
- **Strength ↔ food budget:** foragers split power between *body* (strength) and *fuel* (`F`), inversely — strong bodies generate little food, fragile ones generate a lot, so the deck can still contest the board.

## 7.2 Legendary Combo Units *(2 slots — locked)*

| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Hibernating Bear** | — | 6 | **Immovable.** When placed, lose all your stored food; two turns later, gain twice that amount. |
| **Octopus** | — | 4 | When placed, search your deck for a unit and put it into your hand. |

The Bear is the payoff (Immovable guarantees it resolves, so the only answer is to race it); the Octopus is the consistency engine that finds the Bear.

## 7.3 Rare Combo Units *(3 slots — locked)*

| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Egg** | — | 0 | After 2 turns, remove this unit and draw 2 cards. **Fragile.** |
| **Queen Bee** | Insect | 2 | Whenever you gain food, gain **3** additional food. *(additive)* |
| **Opossum** | — | 2 | When placed, draw 1. When this would be removed, return it to your hand instead. |

## 7.4 Common Combo Units *(7–8 slots — locked at 8)*

| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Cottontail** | Rabbit | 2 | When placed, draw 1. |
| **Squirrel** | Rodent | 2 | When placed, gain **8** food. |
| **Honeybee** | Insect | 1 | When placed, gain **8** food; if you control another Insect, gain **4** more. |
| **Chipmunk** | Rodent | 3 | When placed, gain **5** food. |
| **Wild Boar** | — | 5 | When placed, gain **3** food. |
| **Hedgehog** | — | 3 | When this unit is removed, draw 1. |
| **Armadillo** | — | 4 | Cannot be removed until your next turn. |
| **Pufferfish** | Fish | 2 | When an enemy unit is placed on top of this, remove that enemy unit and this unit. |

**Pufferfish** is the strength-agnostic defensive trap (see §7.1): park it on the HQ and any unit that covers it to advance/capture dies, regardless of strength — a one-time 1-for-1, not a permanent wall.

---

# 8. Midrange Units

## 8.1 Identity (locked for 0.0.1)

- **Theme:** mono-**Cat** tribal. Every Midrange unit is a felid.
- **Role:** flexible goodstuff — moderate strength and a bit of everything (tempo, card selection, removal, reach); adapts to the opponent, 50/50 vs. the field.
- **Synergy:** "if you control another Cat" / "for each other Cat" riders turn a fair pile of cats into a coordinated pride. *(First real use of the species-tag system as a deck engine.)*

## 8.2 Legendary Midrange Units *(2 slots — locked)*

| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Cheetah Brother** | Cat | 5 | When placed, you may immediately play Cheetah Sister from your hand or deck. |
| **Cheetah Sister** | Cat | 5 | When placed, you may immediately play Cheetah Brother from your hand or deck. |

The twins are a two-body tempo swing — play one, fetch and deploy the other. *(Tutoring the pair out of the deck is powerful; flag for tuning — may restrict to "from your hand" if too consistent.)*

## 8.3 Rare Midrange Units *(4 — locked; intentionally over the 3-rare target)*

| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Leopard** | Cat | 5 | When placed, remove an adjacent enemy of strength 4 or less. |
| **Lioness** | Cat | 4 | When placed, draw 1 for each Cat you control adjacent to this unit. |
| **Tiger** | Cat | 7 | When placed, remove an adjacent enemy of strength 5 or less. |
| **Snow Leopard** | Cat | 6 | While you control this, your other Cats may be placed onto enemy units of equal or lower strength. |

## 8.4 Common Midrange Units *(7 — locked)*

| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Lion** | Cat | 7 | *(vanilla body — the pride anchor; raw strength is the point)* |
| **Lynx** | Cat | 3 | When placed, if you control another Cat, draw 1. |
| **Cougar** | Cat | 5 | When placed, you may place this adjacent to any Cat you control, ignoring connection. |
| **Serval** | Cat | 2 | When placed, remove an adjacent enemy of strength 6 or more. |
| **Black Panther** | Cat | 5 | Cannot be targeted by enemy special effects. |
| **Caracal** | Cat | 4 | When placed, if you control another Cat, gain **4** food. |
| **Domestic Cat** | Cat | 1 | When placed, if you control another Cat, you may play one more Cat from your hand. |

---

# 9. General Units

Archetype-neutral cards that fit into **any** deck — flexible includes rather than members of a single archetype. *(These sit outside the per-archetype 12–13 budget; we'll reconcile the 50-card total once the General list is sized.)*

## 9.1 Rare General Units

| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Golden Eagle** | Bird | 5 | **Flight.** |
| **Chameleon** | Reptile | ±∞ | May be placed on any unit, and any unit may be placed on top of it. |

---

# 10. Design Parking Lot

Cool card designs without a home archetype yet — parked for future use.

| Name | Tag | Str | Effect | Note |
|---|---|---:|---|---|
| **Rabbit** | Rabbit | 1 | At the start of your next turn, draw a Rabbit. | Self-perpetuating breeding draw-engine; seeds a future **Rabbit-tribal / "breeding"** theme. |
