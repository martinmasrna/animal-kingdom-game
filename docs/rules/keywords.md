# Keyword Registry

Canonical definitions for every printed keyword. **This is the single source of truth** —
card files, deck files, and the engine reference keywords by name and do not re-explain them.
Companion to `overview.md` (rules), `cards.md` (pool), `docs/cards/decks/` (the reworked decklists).

"Occupant" = any card sitting on a crossroad (a `Unit`, an `Egg`, or a `Landmark`); see
`docs/cards/decks/README.md` decision C. "Unit" in card text means animal units (`Unit`/`Egg`),
never `Landmark`.

---

## Official keywords

### Flight
Ignores the connection-to-HQ requirement when placed. (All other placement rules still apply.)

### Immovable
*Physics* (keyword-review ruling A2, 2026-07-02 — see
`docs/rules/keyword-review-immovable-untargetable.md`). Cannot be removed, moved (bounced), or
eaten by **any** ability — the enemy's **or its own controller's** (Carmilla cannot
sacrifice a Giant Tortoise; that cost is deliberate). It can still be **covered** under the
normal placement rules — covering is placement, not an ability. A mass effect (Pestis) skips
an Immovable occupant **in place** and still removes everything else in the stack; Immovable
is not a shield for the cards beneath it. Scope is **board-only**: an Immovable card in hand
can be paid or discarded normally.

Carried by: Giant Tortoise, Scrooge, Methuselah, Bulwark, Elephant.

⚠ *Open item (docs/STATUS.md): the keyword still feels slightly off (name and effect footprint) —
scheduled for another look after balance data accumulates.*

### Stealth  *(renamed from "untargetable", ruling E)*
Cannot be **chosen** by an enemy ability: excluded from any option list an enemy picks a
target from (Jaguar/Serval/Stoop/Gray Wolf/Soldier Ant/Rat/Hornet/Skunk), and an Apex
Predator cannot *eat* it (the eat is a chosen single-out — it covers/buries it instead).
**Mass, random, and automatic effects hit it normally**: Pestis/Rhinoceros/Bulwark AoE,
Sirocco's mass bounce, Grizzly Bear's random strike, Hippopotamus/King Theron/Pufferfish
triggers. Its own controller may still choose it freely. Scope is board-only.

Carried by: Black Panther.

### Fragile
When another occupant is placed on top of this, this is removed — it does not survive under the
stack. (Pairs with timed payoffs: Eggs and Landmarks are typically Fragile.)

### Apex Predator
**Fully specified (2026-06-28).** A predator that must land on prey and eats it.

- **Must** be placed on top of another **occupant** — it **cannot** be placed on an empty
  crossroad. If there is no legal occupant to land on, it cannot be played.
- **Normal covering rules apply in full** (keyword-review ruling C1, 2026-07-02): landing on
  an **enemy** occupant uses the same legality as a normal cover — strictly-greater strength
  by default, **including every covering static**: Snow Leopard lets an apex Cat land at
  equal strength, Chameleon may be landed on regardless of strength, and **Porcupine
  ("cannot be covered by enemy units") blocks the landing entirely** — quills beat teeth.
  Landing on **your own** occupant has **no** strength requirement.
- **May target your own occupants** as well as enemy ones — and removes (eats) them too.
- On placement it **removes** the occupant it lands on **instead of covering/stacking** on it
  (cf. Boa Constrictor). The removed occupant's Deathrattle / on-remove effects fire normally.
  The predator then occupies the crossroad (on top of any remaining stack beneath).
- **If the occupant can't be eaten** (Immovable, or an enemy with Stealth — the eat is a
  chosen single-out, ruling C3), the predator is **not** blocked from landing there: it
  simply **covers** it under the normal placement rules and buries it instead of eating it.
  Apex Predator is not restricted to prey it can eat — eating is what it does *when it can*,
  not a placement precondition.
- **Cannot be placed onto a headquarters** — deliberate design choice, so Apex Predators can't
  capture an enemy HQ directly.
- **Destroys Eggs and Landmarks** it lands on (they are occupants).
  - ⚠ *Flavor wart:* a predator "eating" a Landmark (a tree, a watering hole) doesn't read
    well. Tracked under the Landmark revisit (`docs/STATUS.md`); mechanics stand for now.

Carried by: **Tiger** (Cats), **Anaconda** (Egg), **Polar Bear** + the giant-polar-bear &
giant-harpy-eagle legendaries (Ramp).

### Battlecry  *(placeholder name — rename pending, `docs/STATUS.md`)*
An effect that resolves when the unit is placed. Most "when placed…" effects are Battlecries.

### Deathrattle  *(placeholder name — rename pending, `docs/STATUS.md`)*
An effect that resolves when **a unit leaves the board** — the narrow case. **Print as
"Deathrattle: …"** (not "When this is removed").

**Deathrattle vs. "remove":** a unit leaving the board is one kind of *remove*, but not the
only one — a card sent to the **Remove Pile** from hand or deck (e.g. Rat's paid card, a
discard) is a **remove** but **not** a Deathrattle. So there are two trigger tiers: a
**remove trigger** (any card → Remove Pile, from anywhere) and the narrower **Deathrattle**
(a unit leaving the board). See `overview.md` for the Remove Pile zone. A "return … instead"
effect (e.g. Opossum) is *not* a remove at all — the card never reaches the Remove Pile.

---

## Not a keyword

### Costs X food  *(placement cost)*
A printed cost, handled by the engine, not a keyword. The placement is offered only if the
controller has ≥ X food; X food is paid on placement. (e.g. Ramp's `Costs 20 food` bodies,
some legendaries.)

### Strength modifiers  *(card-text convention, not a keyword)*
Card text grants strength two ways, **distinguished by the verb** — this reading is binding:

- **"has +X strength" → an anthem** (live, conditional aura). Recomputed live; **vanishes**
  when its source leaves play or its condition stops holding. Examples: wolf matriarch ("your
  other Canines *have* +2"), African Wild Dog ("*has* +1 for each friendly Canine"), Champion
  of the Hive, Guard Hornet ("*has* +5 while ≥5 Colony"). The same live layer also computes
  **dynamic strength** (e.g. the giant-anaconda legendary = number of removed units).
- **"give +X strength" → a permanent counter** (one-time grant, **stored on the unit
  instance**, persists after the granter dies). Also applies to **cards in hand** (which carry
  the counter onto the board when played); hand buffs are **one-time** — a unit drawn *after*
  the buff is not retroactively buffed. Examples: Dhole ("*give* all adjacent Canines +2"),
  howl ("*give* +1 to all other Canines in hand and battlefield"), hellhound's returned
  Canine (+2), the end-of-turn buffer.

**`effective_strength`** = `base_or_dynamic + stored_counters + active_anthems`, clamped ≥ 0,
**evaluated live** wherever strength matters (covering, removal thresholds, region-holding,
conditions like Coyote's "if this has 5+"). Counters are signed ints (a future "−X" debuff
works; none exist yet). The event **`ON_GAIN_STRENGTH`** fires only when a counter is granted
(not on live anthem drift).
