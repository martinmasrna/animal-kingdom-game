# Design TODO

Open decisions and follow-ups parked during card design. Add freely.

## Card model / types
- [ ] **Revisit the `Landmark` (non-animal) card-type decision.** Provisionally resolved 2026-06-28 (see `docs/decks/README.md` decision C): §2 relaxed to allow non-animal cards used *sparingly*; `Unit`/`Egg` are units mechanically, `Landmark` is the lone non-unit type (invisible to "unit" wording, can't capture an HQ); rules text uses "occupant" as the umbrella noun. **Take another look before building `cards.json` + rules** — confirm Egg-as-unit causes no odd interactions, the "occupant" vocabulary reads cleanly across all card text, and the Landmark minority hasn't crept larger as decks get finished. **Flavor wart to weigh:** an Apex Predator landing on a Landmark "eats" it — a tiger eating a fig tree reads badly. Options when revisiting: accept it, make Landmarks untargetable by Apex Predator, or re-theme the Landmarks.

## Future / expansions
- [ ] **Ice Age expansion (parked).** Save Ice Age megafauna (mammoth, sabertooth, dire wolf, etc.) for a dedicated later set rather than spending them in the 0.0.1 pool. (Came up filling Ramp's stomp legendary — used a "titanic hippo" instead of a mammoth to keep mammoth available for this.)

## Terminology
- [ ] **Rename "Discard" → "Remove Pile" across all docs/data.** Decision 2026-06-28 (README decision F): there is **one** shared pile, the Remove Pile (no separate discard pile); "remove" is the universal verb for any card sent there from hand/deck/board. Sweep `overview.md` §3.7 (and §11/§3.7 references), `cards.md`, and the staging files — replace "discard" wording. Two trigger tiers: **remove** (any card removed) vs **Deathrattle** (a unit leaving the board).

## Naming / keywords
- [ ] **Rename the "Battlecry" keyword** (the "when a unit is placed" trigger). "Battlecry" is a placeholder borrowed from elsewhere; find a more on-theme name (rejected so far: Instinct, Pounce). Until settled, card text keeps saying "Battlecry:"
- [ ] **Rename the "Deathrattle" keyword** (the "when this is removed / leaves play" trigger). **Now in active use** across the reworked pool (Opossum, Impala, Gazelle, Phoenix, …) — kept as a placeholder keyword for now (decision 2026-06-28). Standardize on printing **"Deathrattle: …"** rather than writing out "When this is removed." Find an on-theme name later.
- [x] **`Apex Predator` keyword fully specified** (2026-06-28, see `docs/keywords.md`): must land on an occupant; normal covering strength rules apply (strictly-greater for enemies, no req for own units); may eat your own units; cannot be placed on an HQ (deliberate — no direct HQ capture); destroys Eggs/Landmarks. *Lingering flavor wart — a predator "eating" a Landmark — folded into the Landmark revisit below.*

## Balance constants (tune together on one scale)
- [x] **Food economy — v0 set** (`cards.md` §4.5 *Food Economy Constants*): region 10/20, threshold 100, `F` plain 4 / low 3 / med 5 / high 8, Honeybee +4, Queen Bee +3, Driver Ant 2/unit, Raven cost 12, Bear ×2 over 2 turns. **Now needs sim tuning** — especially the ⚠ dials (Driver Ant scaling, Queen Bee stacking, Bear delay).
- [x] **Forager strength ↔ food budget (Combo):** inverse curve realized in v0 — Wild Boar (Str 5 → 3), Chipmunk (Str 3 → 5), Squirrel (Str 2 → 8), Honeybee (Str 1 → 8+). Confirm in sim.
- [x] **Spotted Hyena threshold `N` — v0 = 4** (control 4 other units to unlock "cover any strength"). Sim should sweep ~3–5.

## Card-specific tuning
- [ ] **Queen Bee (Combo):** keep additive (`+F` per food gain); watch for stacking multiple copies.
- [ ] **Hibernating Bear (Combo):** confirm the 2-turn delay and that "lose all food" + Immovable can't be abused.

## Engine / performance
- [ ] **State-representation speed tradeoff (revisit before NN bots).** The engine currently uses per-unit Python objects (`UnitInstance`) referencing shared immutable `Card` flyweights by id — chosen for correctness, serializability, and readability, and fine for the near-term goal of *thousands* of greedy-bot games. **This will not be fast enough** once we move to **neural-network / AlphaZero-style bots** (MCTS needs millions of cheap state clones + fast batched feature extraction). When we get there, switch the *in-play* representation to **struct-of-arrays / entity-component** (parallel integer arrays indexed by board slot, cloned via array/bytes/NumPy copies, no per-unit objects) and add a tensor-encoding of the per-seat view for the network. The data layer (`cards.json`) and the id-keyed effect registry are deliberately decoupled from the in-play representation, so this is a localized change to `state.py`, not a rewrite. **Measure clone cost in M3 first** (the sim already needs throughput metrics) so the switch is driven by real numbers, not guesswork. Keep `UnitInstance` lean (`__slots__`, primitives only) in the meantime so the gap is as small as possible.
- [ ] **Flavor pass — re-cast animal names onto existing cards.** Keep the mechanical skeleton (effects/roles/archetype ratios) fixed, but revisit the animal assigned to each card so the species fits its effect "like a glove" — pure renaming, no balance impact. Prioritize the cards currently carrying a generic `—` tag (e.g. Honey Badger, Wild Boar, Armadillo, the anchors), which are where effect-first design shows its seams. Selection filter: pick animals with a *famous specific behavior* (scavenges, steals, plays dead, swarms) rather than just "most iconic," so swarm/utility roles don't get starved in favor of big megafauna.