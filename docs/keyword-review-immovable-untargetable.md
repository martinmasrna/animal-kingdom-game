# Immovable / Untargetable — dedicated deep-dive (2026-07-02)

## ✅ RULED & IMPLEMENTED (2026-07-02, same day)

Martin's rulings on §5, all shipped (engine + `tests/test_keywords.py` + `keywords.md`):

- **A → A2 adopted**: Immovable = physics (blocks removal/bounce/eat from everyone,
  own sacrifices included); Untargetable = stealth (blocks enemy *chosen* picks only).
- **B → adopted as recommended, with one amendment**: Pestis does **not** stop mid-stack
  at an Immovable occupant — it skips the Immovable unit in place and removes everything
  else in the stack. Theron/Hippo triggers, Grizzly's random strike, and all mass effects
  now hit Stealth.
- **C → C1 adopted**: apex landings route through `statics.can_cover` (Snow Leopard and
  Chameleon apply; Porcupine blocks apex landings entirely). C3 preserved: Stealth blocks
  the eat (chosen single-out) → cover fallback.
- **D → adopted**: both keywords are board-only. **Plus a new todo**: take another look at
  Immovable later (naming *and* effect) — it still feels a bit off.
- **E → renamed to "Stealth"** (not "Elusive"). `black_panther` now carries a proper
  `Stealth` keyword in cards.json; text prints "Stealth."

Implementation (§6) delivered as sketched: `can_be_targeted` → `statics.can_be_chosen`
consulted only in enemy-chooser option lists + the apex eat; the central removal gate keeps
only `can_be_removed`; mass/random/auto paths pass `chosen=False`. 15 new behavior tests.

The sections below are the pre-ruling analysis, kept for the record.

---

The focused pass `docs/todo.md` calls for. Walks every card that has, grants, or interacts
with the two keywords, tabulates **intended vs actual** behavior per effect class, and ends
in the concrete decision forks (§5) that need a human ruling. Code references are to
`engine/statics.py` (the predicates) and `engine/effects.py` (the call sites).

## 1. The current model, in one paragraph

Two predicates exist: `can_be_removed` (blocked by the **Immovable** keyword — Giant
Tortoise, Scrooge, Methuselah, Bulwark, Elephant) and `can_be_targeted` (blocked by
**Black Panther** against enemies only). **Every unit-touching effect in the engine checks
both predicates together** — the central removal gate (`_remove_specific`,
effects.py:219-222) and every target-list builder (`_adjacent_enemy_targets`,
`_adjacent_friendly_units`, `_adjacent_enemy_unit_crossroads`, `_friendly_unit_crossroads`,
the Hippo trigger). Consequence: the two keywords block the **identical set of effects**;
the only difference is owner scope (Immovable resists everyone including its own
controller; Untargetable resists enemies only). They are one ability with two scopes, not
two abilities.

## 2. Carriers and adjacent statics

| Card | Deck | Keyword / static | Printed text |
|---|---|---|---|
| Giant Tortoise | food_otk | Immovable | "Immovable." (vanilla wall) |
| Scrooge | food_otk | Immovable | store food, ×2 in 2 turns |
| Methuselah | ramp (leg.) | Immovable | +10 food end of turn |
| Bulwark | ramp | Immovable | costs 20, AoE remove on entry |
| Elephant | ramp | Immovable | costs 20 |
| Black Panther | cats_midrange | Untargetable | "Cannot be targeted by enemy special effects." |
| Porcupine | food_otk | cover-block | "Cannot be covered by enemy units." (`can_cover`, statics.py:38) |
| Snow Leopard | cats_midrange | cover-relax | other Cats may cover equal strength (statics.py:45) |
| Chameleon | — | cover-bypass | covers/covered by anything (statics.py:34) |
| Pufferfish | food_otk | cover-punish | removes an enemy coverer + itself |
| Tiger, Anaconda, Polar Bear, Borealis, Aquila | various | Apex Predator | eats what it lands on |

## 3. Interaction table — current engine behavior

Columns: what happens against an **Immovable** unit / an **enemy Black Panther** / your
**own Black Panther**. "Blocked" = the unit is silently excluded from targets or the
removal no-ops.

| Effect (class) | vs Immovable | vs enemy Panther | vs own Panther |
|---|---|---|---|
| **Chosen single-target removal** — Jaguar, Serval, Stoop, Soldier Ant, Gray Wolf, Rat, Hornet | blocked | blocked | n/a (enemy-only lists) |
| **Friendly sacrifice** — Carmilla, Black Widow | **blocked** ⚠ | n/a | **allowed** ✓ |
| **Triggered removal** — King Theron (on your Cat covering it) | blocked (buried, survives under the Cat) | blocked | n/a |
| **Automatic removal** — Hippopotamus (enemy ≤3 placed adjacent) | blocked | blocked (moot: Panther str > 3) | n/a |
| **Random removal** — Grizzly Bear (delayed, random adjacent) | excluded from the pool | excluded from the pool | n/a |
| **Mass AoE removal** — Rhinoceros (≤5), Bulwark (all adjacent) | blocked | blocked | n/a |
| **Mass stack wipe** — Pestis (whole crossroad, top-down) | **stops the wipe**: everything *below* it survives too | same | own Panther in own stack: same stop |
| **Bounce (chosen)** — Skunk | blocked ("moved") | blocked | n/a |
| **Bounce (mass)** — Sirocco (all adjacent enemies) | blocked | blocked | n/a |
| **Normal covering** (placement) | **allowed** (per keywords.md: covering is not an effect) | **allowed** | allowed |
| **Apex eat** (landing) | eat blocked → falls back to a normal **cover** (buried) | eat blocked → cover fallback (buried) | own apex: eat **allowed** (own-sac scope) |
| **Pufferfish retaliation** (you covered it) | **coverer survives** ⚠ (Elephant/Bulwark cover Pufferfish and live; Pufferfish still dies) | **Panther survives** ⚠ (covers Pufferfish with impunity) | n/a |
| **Hand removal** — Rat's cost, Black Swan random discard | **not blocked** (hand Scrooge is payable/removable) | **not blocked** | not blocked |
| **Strength counters/debuffs** | ungated (no enemy-targeted grants exist in the pool; counters are signed for future −X) | ungated | ungated |

⚠ = behaviors that were probably never consciously decided.

**Notable in-deck anti-synergy (probably unintended):** food_otk contains *both* Immovable
bodies (Giant Tortoise, Scrooge) *and* the friendly-sacrifice engine (Carmilla, Black
Widow). Because Immovable blocks its own controller, **Carmilla can never sacrifice a
Tortoise/Scrooge** — the deck's wall cards are dead to its own draw engine. Ruling A below
decides whether that's a cost of the keyword or a bug.

## 4. Apex Predator edge cases (the todo's item c)

Apex landing legality (`_apex_can_land`, effects.py:424) uses a **bare strictly-greater
strength check**, *not* `statics.can_cover`. The eat itself goes through the normal removal
gate. Current results:

| Edge | Current behavior | Consistent? |
|---|---|---|
| Apex vs **Porcupine** ("cannot be covered by enemy units") | Porcupine is removable+targetable → apex **eats it** outright; even the cover *fallback* would ignore `can_cover` | ✖ Porcupine's only ability does nothing against the one placement type it should most plausibly stop; flavor inverted (quills famously deter big cats) |
| Apex Cat vs equal-strength enemy while you control **Snow Leopard** | normal Cats may cover at equal strength, but the apex (Tiger) **cannot land** at equal strength | ✖ the anthem silently excludes the deck's own apex |
| Apex vs stronger enemy **Chameleon** | normal cover would be legal (bypass both ways), apex **cannot land** | ✖ same inconsistency |
| Apex vs enemy **Black Panther** (apex stronger) | eat blocked → covers/buries it | ✓ documented in keywords.md |
| Apex vs **Immovable** (apex stronger) | eat blocked → covers/buries it | ✓ documented in keywords.md |
| Apex eats **Pufferfish** | eat is not a cover → **no retaliation**, clean kill; if the eat were blocked, the cover fallback *would* trigger retaliation | defensible (eaten before it can spike) — decide with C |

## 5. Decision forks — rulings needed

### A. Do the keywords keep identical footprints, or get distinct ones?
Today they are one ability with two scopes. Options:

- **A1 — keep identical scopes**, just fix docs/names. Cheapest; leaves the design debt.
- **A2 — differentiate (recommended):**
  - **Immovable** = *physics*: cannot leave its crossroad or be destroyed by any ability,
    **anyone's** — blocks removal, bounce, apex-eat, from both players (own sacrifices
    stay blocked: that's the cost of the keyword and it's at least a real trade-off).
    Still affectable by non-move effects (future debuffs, marks, etc.).
  - **Untargetable** = *stealth*: cannot be **chosen** by an enemy ability — blocks
    single-target picks only. Mass, random, and automatic effects hit it normally.

### B. If A2: which effect classes count as "chosen"? (recommendations)
- Chosen single-target (Jaguar/Serval/Stoop/Gray Wolf/Soldier Ant/Rat/Hornet/Skunk):
  **blocked** — the core of the keyword.
- Triggered/automatic (King Theron, Hippopotamus): **hits** — nobody aimed; it's a trap.
- Random (Grizzly Bear): **hits** — random is the opposite of targeted (Panther enters the
  pool).
- Mass (Pestis, Rhinoceros, Bulwark, Sirocco): **hits** — and Pestis stops "stopping" at a
  Panther mid-stack (Immovable still stops it, under A2 physics).
- Net effect: a real **nerf to Black Panther** (today it's immune to all of the above).
  If it needs compensation, that's a §G/H balance dial, not a semantics reason to keep the
  blanket immunity.

### C. Apex landing legality (recommendations)
- **C1**: route the enemy-landing check through `statics.can_cover` instead of the bare
  strength comparison — Snow Leopard and Chameleon then apply to apexes exactly as to
  normal covers. (One-line fix + tests.)
- **C2**: rule Porcupine vs Apex explicitly. Recommended: an apex landing is a placement
  onto the occupant, so "cannot be covered by enemy units" **blocks the landing entirely**
  (no eat, no cover). Porcupine becomes honest anti-apex tech and the flavor reads
  perfectly. (Falls out of C1 for free, since `can_cover` already returns False.)
- **C3**: Immovable/Panther eat-block → cover-fallback stays as documented (no change).
  Under A2+C4 an apex *landing* is a chosen single-out, so Panther still blocks the eat and
  gets buried instead — current behavior preserved.

### D. Hand scope
Both keywords are **board-only** (current behavior): Rat may pay an Immovable card from
hand, Black Swan's random discard hits anyone. Recommended: keep, and say so explicitly in
keywords.md — the alternative (hand immunity) makes Scrooge unpayable and is invisible-rules
territory.

### E. Names / printed text (flavor-lock, after A-D)
If A2 adopted, the two abilities finally *are* different and deserve distinct names:
- Immovable: keep **"Immovable"** — text: *"Can't be removed, moved, or eaten by
  abilities."*
- Untargetable: rename — candidate **"Elusive"** (fits a panther; short; reads as
  "can't be picked"): *"Enemies can't choose this with abilities."*
Rename lands in the same sweep as the Battlecry/Deathrattle renames (todo.md).

## 6. Implementation sketch (once ruled)

Small, contained: split the predicate pair into `can_be_removed` (Immovable; consulted by
*every* remove/bounce/eat path regardless of chooser) and `can_be_chosen` (Untargetable;
consulted **only** when building enemy-chooser option lists). Drop `can_be_targeted` from
the mass/random/automatic paths (`_op_pestis_wipe` loop, Rhino/Bulwark/Sirocco pushes,
Hippo, Grizzly pool). Change `_apex_can_land`'s enemy branch to `statics.can_cover`. Update
keywords.md §Immovable + add §Elusive. Tests: extend `test_effects.py` keyword cases +
`test_bot_puzzles.py` stays green; the referee/sim needs nothing (it plays whatever the
engine legalizes). Then a 150-game/matchup referee spot-check on cats_midrange (Panther
nerf) and food_otk (Porcupine buff, Carmilla/Scrooge unchanged under A2) before merging.
