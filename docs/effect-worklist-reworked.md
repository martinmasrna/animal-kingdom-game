# Effect worklist — reworked 98-design pool (Phase 2 of #5)

Resume artifact for **Phase 2**: wiring card *logic* on top of the Phase-1 static data
(`data/cards.json` + the migrated loader/validation/decks now in place). Grouped like
[`m2b-worklist.md`](m2b-worklist.md) by how much new engine code each card needs.

**Engine entry points** (all in `engine/`): triggered behavior → `EFFECTS[card_id]` in
`effects.py` (hooks push op-steps); reusable ops → `OPS`; static modifiers → `statics.py`;
strength (base/dynamic + counters + anthems) → `strength.py`. Golden test per card in
`tests/test_effects.py` (currently `@pytest.mark.skip` module-wide — drop the skip as each
card lands). Binding rulings: README decisions **A–J** + `keywords.md`.

> Scope note: the M2a `EFFECTS`/`OPS` entries left dormant in `effects.py` key a few ids
> that **also exist in the reworked pool** (`squirrel`, `chipmunk`, `gray_wolf`,
> `pufferfish`). Their behavior **changed** (e.g. Squirrel 8→6 food; Gray Wolf now removes
> ≤ own buffed strength). Re-derive these from the new text — do not assume the old handler
> is correct.

---

## New subsystems to build first (each unlocks many cards)

1. **Strength modifiers** (dec. E / `keywords.md`) — `effective_strength = base_or_dynamic
   + Σ counters + Σ anthems`, clamped ≥0, evaluated live.
   - *Anthems* ("**has** +X"): Raksha, Vesper, Guard Hornet, Lobo, African Wild Dog, Verminus.
   - *Counters* ("**give** +X", stored on instance, incl. hand instances): Dhole, Clarion,
     Red Wolf, Dingo, Bush Dog, Shuck's returned Canine. Rattlesnake uses persistent
     per-player/card growth so its shuffle gains apply in every zone.
   - `ON_GAIN_STRENGTH` fires only on counter grants (Fox, Bush Dog); once-per-turn + loop guard.
2. **Food-event engine** — discrete `ON_DRAW` / `ON_SHUFFLE` / `ON_REMOVE` events (dec. F2/F9).
   Triggers: Eon (any of the three → +1 food), Vulture (+5 food/remove),
   Rattlesnake (+1 strength/own shuffle, wherever it is), Egg Eater (+10/Egg removed),
   Jackal (+3/adjacent removal). Shuffle = one event per card
   shuffled *into* the deck.
3. **Apex Predator placement** (dec. D) — must land on an occupant; strictly-greater vs enemy,
   free on own; removes-instead-of-covers; can't target HQ; destroys Eggs/Landmarks.
   Carriers: Tiger, Anaconda, Polar Bear, Borealis, Aquila.
4. **`food_cost` placement gate** (dec. F / `keywords.md`) — offer only if food ≥ cost, pay on
   placement; in `legal_placements` + `do_placement`. Cards: Borealis, Aquila, Bulwark, Elephant.
5. **Landmark type** (dec. C) — `type=="landmark"` invisible to unit-queries, can't capture HQ,
   uses the delayed scheduler. Cards: Fig Tree, Watering Hole. (Also harden HQ capture so a
   landmark can never be placed onto an HQ.)
6. **Filtered RANDOM draws** (dec. F10) — uniform random among matching deck cards, seeded, no
   choice/inspection, fizzle if none. By tag: Mouse (Rodent), Bird Egg (2 Birds), Snake Egg
   (2 Snakes). By rarity: Fathom (legendary). By strength: Watering Hole (≥6). The Prince
   Leo / Princess Lea twins are the *named* exception (fetch the specific sibling hand-or-deck).

---

## Group A — static modifiers (`statics.py` / `strength.py`)
- **snow_leopard** — anthem: other Cats may cover ≤ (can_cover; M2a logic exists, retune).
- **cougar** — placement adjacent to any Cat, ignoring connection (extra_placement_crossroads; exists).
- **black_panther** — untargetable by enemy effects (can_be_targeted; exists).
- **porcupine** — cannot be covered by enemy units (can_cover; cf. old giant_tortoise).
- **giant_tortoise**, **scrooge**, **methuselah**, **bulwark**, **elephant** — Immovable (can_be_removed; exists). Scrooge must stay put so its store/double resolves.
- **chameleon** — ±∞ both ways (can_cover; exists). Needs real non-covering strength semantics (dynamic placeholder).
- **goliath** — dynamic strength = size of the Remove Pile (`strength.py`, rule `removed_units_count`).
- Anthem/dynamic strength cards (**raksha/vesper/guard_hornet/lobo/african_wild_dog/verminus**) → subsystem 1.

## Group B — triggered effects reusing existing ops (handler-only)
Push `gain_food` / `draw` / `remove_choice` / `play_extra` / `schedule`. `[ ]` = small op tweak.

**Gain food (on_place):** worker_ant (8), worker_bee (5; +5 if another Worker), flying_squirrel (4),
squirrel (6), queen_marabunta (4×other Colony), greywhisker (1 + draw 1 + play 1 more).
**Conditional draw (on_place):** lynx (another Cat), coyote (if self ≥5 — reads buffed strength),
nurse_bee (≥2 same Colony copy), nurse_bumblebee (≥5 Colony), termite_king (control a Colony Queen),
bat (draw 1), caracal (on_place_onto_enemy: draw 1).
**Capped single-target removal (on_place):** jaguar (≤5), serval (**≥6** — needs a min-strength
`remove_choice` variant), stoop (≤6), gray_wolf (≤ own buffed strength), soldier_ant (uncapped if ≥5 Colony).
**AoE removal (on_place):** rhinoceros (all adjacent enemy ≤5), bulwark (all adjacent enemy — uncapped)
`[remove_all op, no choice]`.
**Reactive removal:** hippopotamus (on_enemy_placed_adjacent, ≤3 — hook already dispatched).
**Recurring/delayed food (schedule + on_end_of_turn):** worker_wasp (+3 end of turn), methuselah (+10 end
of turn), chipmunk (5 now + 5 next turn), black_bear (draw in 2 turns), grizzly_bear (random adjacent
removal in 2 turns `[seeded RNG]`).
**Extra placement (`play_extra`):** jerboa (any), greywhisker (1 more), house_cat (Cat, ≠self),
dog (Canine, ≠self), queen_bee (a Worker), termite_queen (non-Queen Colony), prince_leo/princess_lea
(the named twin, hand-or-deck — subsystem 6).
**Start-of-turn draw:** aurum (Egg, your turn).

## Group C — needs a NEW op / mechanic
- **eon / vulture / rattlesnake / egg_eater / jackal** — food-event engine (subsystem 2).
- **queen_honoria** — "whenever you play a Colony unit" → +5 (new `ON_PLAY` tribal trigger).
- **falstaff** — "whenever you gain food, +3" → food rider (cf. old queen_bee rider; watch loops w/ Honoria).
- **owl** — look at top 3, draw 1, shuffle the rest (top-N peek + per-card shuffle events).
- **raven** — draw 3, then shuffle 2 back (shuffle events).
- **ember** — on-remove: shuffle self back to deck (remove fires, then shuffle → dec. F9).
- **black_swan** — `ON_DRAW` (from hand): both players discard a random hand card (seeded; cf. `discard_random`).
- **fathom / mouse / bird_egg / snake_egg / watering_hole** — filtered random draws (subsystem 6).
- **andean_condor** — reveal both decks' tops, compare printed base strength, draw if strictly greater (dec. F13).
- **oxpecker** — +1 food per starting-deck unit with printed base ≥6 (dec. F12; reads the fixed decklist).
- **pestis** — remove everything from an adjacent crossroad (whole stack, both players; dec. F3) `[remove_all_at_crossroad]`.
- **sirocco** — bounce all adjacent enemies to owner's hand (mass-bounce; not a remove).
- **skunk** — bounce one adjacent enemy + lock "can't play next turn" (per-card locked-until-turn status; dec. F4).
- **rat** — discard a hand card → destroy an adjacent enemy, any strength (hand-cost; dec. F5).
- **hornet** — optional self-remove → destroy any adjacent enemy (optional yes/no, cf. old wasp).
- **lemming** — place all hand Lemmings on random empty adjacent crossroads (dec. F8; multi-place, seeded).
- **cheetah / falcon** — draw if placed next to enemy HQ (HQ-adjacency helper; dec. F6).
- **carmilla / black_widow** — sacrifice friendly units → draw (friendly-target removal firing Deathrattles).
- **gazelle / impala / opossum** — Deathrattle payoffs (gazelle +20, impala draw 2, opossum return-to-hand; dec. F9).
- **scrooge** — store all food → set 0, recover 2× in 2 turns; keep earning in the window (dec. F7).
- **king_theron / queen_adira** — team-wide triggers (Cat covers→remove enemy; Cat removes→draw); once-per-turn TBD (dec. G).
- **shuck** — pull a removed Canine from the Remove Pile to hand with a +2 counter (subsystem 1 + Remove-Pile query).

---

## Open tuning / ruling dials (defer to sim — dec. G/H)
Once-per-turn caps on uncapped value triggers (Queen Adira, Eon, Rattlesnake, Vulture, Jackal,
Honoria, Falstaff); the whole food scale (Worker Ant 8, Egg Eater 10, Gazelle 20, Fig Tree 20,
the `Costs 20` bodies) vs `win_food` 100; "whose turn / whose cards" scoping on the event triggers.
None of these block the Phase-2 wiring; they live in `config.py`.
