# M2b worklist — remaining card implementations

Resume artifact for finishing M2 (the effect pool). M2a built the engine core + a 10-card
slice; this lists the rest, grouped by how much new code they need. Delete when M2 is done.

**Engine entry points** (all in `engine/`): triggered behavior → `EFFECTS[card_id]` in
`effects.py` (hooks push op-steps); reusable ops → `OPS` in `effects.py`; static modifiers
→ `statics.py`; dynamic strength → `strength.py`. Golden test per card in
`tests/test_effects.py`. See plan file + `[[choice-model-effect-stack]]` memory.

When done: re-enable dynamic cards in `decks.make_vanilla_deck` (currently excludes them);
add a reveal-on-removal-by-effect test; full-pool fuzz must stay legal/terminating.

---

## Group A — statics already coded in M2a, only need golden tests
The `statics.py` predicates already handle these generally; just confirm + test.
- **matriarch_elephant** (Immovable — can_be_removed)
- **giant_tortoise** (can't be covered — can_cover)
- **armadillo** (can_be_removed until owner's next turn; uses `UnitInstance.placed_on_turn`)
- **black_panther** (untargetable — can_be_targeted)
- **snow_leopard** (anthem: other Cats cover ≤ — can_cover)
- **spotted_hyena** (cover any if ≥4 others — can_cover; sweep threshold)
- **cougar** (placement adjacent to any Cat — extra_placement_crossroads)
- **chameleon** (±∞ bypass — can_cover; also dynamic strength placeholder in strength.py — revisit ≤N target semantics)
- **anaconda** (dynamic = discard count — strength.py; test + re-enable in decks)
- **boa_constrictor** (remove-instead-of-stack — handled in `_land_unit`; test, incl. buried-enemy edge)
- **queen_bee** (food rider — already in `gain_food`; test stacking)
- **opossum** (return-to-hand on remove — `_dispose`; + on_place draw 1, see Group B)

## Group B — triggered effects that REUSE existing ops (mostly handler-only)
Handler computes a condition/amount, then pushes `gain_food` / `draw` / `remove_choice`.
May need tiny op tweaks noted in []. 
- **driver_ant_queen** — on_place gain `driver_ant_per_unit * units_controlled` food
- **rat** — on_place: if ≥3 other units, draw 1
- **army_ant** — on_place: if `units_placed_this_turn > 1`, gain `f_plain`
- **piranha** — on_place_onto_enemy: draw 1
- **vervet_monkey** — on_place: if another Primate, gain `f_plain`
- **baboon** — on_place: if another Primate, draw 1
- **coyote** — on_place: if another Canine, draw 1
- **lynx** — on_place: if another Cat, draw 1
- **caracal** — on_place: if another Cat, gain `f_plain`
- **cottontail** — on_place draw 1
- **wild_boar** — on_place gain `f_low`
- **honeybee** — on_place gain `f_high`; if another Insect, +`honeybee_insect_bonus`
- **cape_buffalo** — on_remove draw 1
- **hedgehog** — on_remove draw 1
- **lioness** — on_place: draw 1 per adjacent Cat you control [count adjacent]
- **leopard** — on_place remove adjacent enemy ≤4 [remove_choice, param max=4]
- **tiger** — on_place remove adjacent enemy ≤5 [remove_choice max=5]
- **serval** — on_place remove adjacent enemy **≥6** [remove_choice needs a min_strength variant]
- **rhinoceros** — on_place remove ALL adjacent enemy ≤3 [new `remove_all` op, no choice]
- **hippopotamus** — on_enemy_placed_adjacent: remove it if ≤3 [hook dispatch already wired in `_push_reactions`]
- **domestic_cat** — on_place: if another Cat, play one more Cat [reuse `play_extra` constraint="cat", optional]

## Group C — need a NEW op / mechanic
- **raven** — costs 12 food to play (placement gate) + on_place draw 3. NEW: placement cost in `legal_placements` (can't offer if food < cost) and pay in `do_placement`.
- **raccoon** — opponent discards a random card. NEW op `discard_random` (chance — uses `state.rng`; reproducible). The carried RNG seam exists for this.
- **octopus** — search deck for a unit → hand. NEW `tutor` op (choose a card from deck; deck is hidden but controller picks → reveals to engine; keep deterministic).
- **owl** — look at top 3 of deck, draw 1, rest to bottom. NEW: choice among top N of own deck.
- **jackal** — return a unit from discard to top of deck. NEW: choose_card from discard.
- **wasp** — on_place "you may remove this to destroy an adjacent enemy ≤2". NEW: optional yes/no (`choose_option` + SKIP) then remove-adjacent + self-remove.
- **lemming** — on_place "you may also play every other Lemming from hand". Variant of `play_extra` (auto multi, optional).
- **cheetah_brother / cheetah_sister** — on_place may play the sibling from hand OR deck. Combines tutor (from deck) + extra placement. (Flag: may restrict to hand if too consistent.)
- **rabbit** (parked) — on_place schedule "at start of your next turn, draw a Rabbit" → scheduled `tutor` of a specific card id into hand. (Uses scheduler; on_start_of_turn already dispatched.)

---

## Order suggestion
1. Group A tests (fast, confidence the statics work).
2. Group B in archetype batches (handler + test each).
3. Group C one mechanic at a time (each unlocks several cards: tutor → Octopus/Cheetah/Rabbit; cost → Raven; discard_random → Raccoon; top-N → Owl; discard-return → Jackal; optional → Wasp/Lemming).
4. Re-enable dynamic cards in decks; full-pool fuzz; reveal-on-removal test; consolidate `TODO(rules)` flags.
