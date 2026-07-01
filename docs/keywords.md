# Keyword Registry

Canonical definitions for every printed keyword. **This is the single source of truth** —
card files, deck files, and the engine reference keywords by name and do not re-explain them.
Companion to `overview.md` (rules), `cards.md` (pool), `docs/decks/` (the reworked decklists).

"Occupant" = any card sitting on a crossroad (a `Unit`, an `Egg`, or a `Landmark`); see
`docs/decks/README.md` decision C. "Unit" in card text means animal units (`Unit`/`Egg`),
never `Landmark`.

---

## Official keywords

### Flight
Ignores the connection-to-HQ requirement when placed. (All other placement rules still apply.)

### Immovable
Cannot be removed or moved by special effects. (It can still be covered/eaten under the normal
placement rules unless another keyword says otherwise.)

### Fragile
When another occupant is placed on top of this, this is removed — it does not survive under the
stack. (Pairs with timed payoffs: Eggs and Landmarks are typically Fragile.)

### Apex Predator
**Fully specified (2026-06-28).** A predator that must land on prey and eats it.

- **Must** be placed on top of another **occupant** — it **cannot** be placed on an empty
  crossroad. If there is no legal occupant to land on, it cannot be played.
- **Normal covering strength rules still apply:** to land on an **enemy** occupant it needs
  **strictly greater** effective strength (like normal covering); landing on **your own**
  occupant has **no** strength requirement.
- **May target your own occupants** as well as enemy ones — and removes (eats) them too.
- On placement it **removes** the occupant it lands on **instead of covering/stacking** on it
  (cf. Boa Constrictor). The removed occupant's Deathrattle / on-remove effects fire normally.
  The predator then occupies the crossroad (on top of any remaining stack beneath).
- **If the occupant can't be eaten** (Immovable, or an enemy that's Untargetable — e.g. Black
  Panther), the predator is **not** blocked from landing there: it simply **covers** it under
  the normal placement rules (still needs strictly-greater strength vs an enemy) and buries it
  instead of eating it. Apex Predator is not restricted to prey it can eat — eating is what it
  does *when it can*, not a placement precondition. *(These "can't be eaten" cases are part of
  the broader Immovable/Untargetable rethink — see `todo.md`.)*
- **Cannot be placed onto a headquarters** — deliberate design choice, so Apex Predators can't
  capture an enemy HQ directly.
- **Destroys Eggs and Landmarks** it lands on (they are occupants).
  - ⚠ *Flavor wart:* a predator "eating" a Landmark (a tree, a watering hole) doesn't read
    well. Tracked under the Landmark revisit (`todo.md`); mechanics stand for now.

Carried by: **Tiger** (Cats), **Anaconda** (Egg), **Polar Bear** + the giant-polar-bear &
giant-harpy-eagle legendaries (Ramp).

### Battlecry  *(placeholder name — rename pending, `todo.md`)*
An effect that resolves when the unit is placed. Most "when placed…" effects are Battlecries.

### Deathrattle  *(placeholder name — rename pending, `todo.md`)*
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
