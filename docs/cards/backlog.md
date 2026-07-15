# Cards & Flavor — Backlog

Open items only. Top-3 summary in [`../STATUS.md`](../STATUS.md). Deck source of truth: `decks/`. Card-pool doc: `cards.md` (§5–9 are legacy — ignore).

> **Build #5 (rebuild `data/cards.json` + the effect registry from the deck files) is DONE** — `cards.json` carries the reworked pool and the full test suite runs on it. Remaining card work is flavor + text cleanup below.

## Landmark cut (decided 2026-07-15) — pending execution

- [ ] **★ Cut Fig Tree + Watering Hole; add ramp's 2 replacement commons.** The game commits to
  animals only (Rules decision, see [`../rules/backlog.md`](../rules/backlog.md)). **Blocked on the
  in-flight benchmark run** — `cards.json` must not change mid-run (workers reload it, and the rig's
  `run_key` doesn't fingerprint card data). Agreed replacements, both `ramp` commons ×3:
  - **Cape Buffalo** (Megafauna, STR 7, vanilla) — replaces Watering Hole, whose tutor-a-6+ job died
    when Draw went to 2 cards. ⚠ **Not inert:** STR 7 clears Oxpecker's ≥6 threshold, so ramp's
    count goes 15→18 and Oxpecker's output 45→54 without Oxpecker being touched.
  - **Sloth** (no tag, STR 3) — *"In 2 turns, gain 20 food."* Replaces Fig Tree's burst-food job.
    Flavor = slow digestion (~a month to digest a leaf), not hibernation. **No Fragile** (sloths
    aren't fragile) and **no Immovable** (it would make the payout unanswerable *and* shadow
    Methuselah — legendary, STR 3, Immovable, 5 food/turn). Counterplay comes from the timed-effect
    ruling instead: cover it with a 4+ and the timer suspends. Keep STR < 6 so it doesn't feed
    Oxpecker. **Depends on [`../rules/timed-effect-ruling.md`](../rules/timed-effect-ruling.md)
    landing first** — under today's engine a non-Fragile timed payout cannot be stopped at all.
  - **Number: 20 food — decided 2026-07-15.** Recorded for whoever implements it: with Cape Buffalo
    lifting Oxpecker to 54, 3×20 = 60 puts ramp's food economy at ~114 against ~105 today.
  - **Tribe:** a sloth is none of ramp's Megafauna/Bear/Bird. Costs nothing mechanically — **no card
    in ramp references a tribe** (all 14 checked); the tags are pure identity. Untagged does collide
    with the generic-tag flavor item below.
- [ ] **~20 candidate entries lapse with the cut.** 14 Landmark candidates (Antivenom Grove, Carcass,
  Fallen Log, Fossil Bed, Kelp Forest, Salt Lick, Termite Mound, Tool Cache, Baobab Tree, Cave, Coral
  Reef, Nesting Ground, Royal Jelly, Warren) + 6 cards that only work if Landmarks exist (Capuchin,
  Clownfish, Fishing Cat, Moose, Beaver, Orangutan). Decide: strike them, or park them with the Ice
  Age set. One of them (a bear den — "draw a random Bear; your Bears cost 5 less food") was built for
  ramp and is worth re-casting as an animal.

## Expansion and constructed play

- [ ] **Re-audit every noncanonical candidate for the no-mana economy before promotion.** The
  invariant is explicit in `decks/README.md`: all cards consume the same placement action, so low
  strength is never “cheap.” Apply the body/card/action/delay ledgers in
  `expansion-design-todo.md` to the single consolidated inventory in
  [`card-candidates.md`](card-candidates.md); rarity alone cannot repay a weak rate.
- [ ] **Review the consolidated candidate inventory:** [`card-candidates.md`](card-candidates.md)
  contains the Common, Rare, and Legendary tables. `expansion-design-todo.md` retains the design
  guardrails and module context rather than serving as a second inventory.
- [ ] **Validate actual deckbuilding choice:** [`deckbuilding-todo.md`](deckbuilding-todo.md)
  defines first-pool size targets, module structure, bridge-card goals, and list-diversity tests.
- [ ] **Resolve post-balance names and species:** [`flavor-todo.md`](flavor-todo.md) covers
  Secretarybird, rare Goliath's species collision, legendary Black Swan, the new Aggro legendary,
  and the broader legendary-name policy.

## Flavor
- [ ] **Dedicated legendary-name review (all 28).** The stricter, do-not-skip pass before flavor-lock. Only the 4 Cats are final. Check each against `cards.md` §2.1: (a) evoke, don't cite — extra scrutiny on borderline picks (Lobo, Shuck, Marabunta, Methuselah); (b) real species only; (c) effect↔name fit "like a glove"; (d) no collisions / one-species rule; (e) tone/register consistency. Goliath is now a rare-species rename; legendary Black Swan and the new Aggro cover-retaliation unit enter this review. Alternates and recommendations live in `decks/flavor-review.md` §3 and `flavor-todo.md`.
- [ ] **Reskins & collisions (pure, no mechanics).** Black Panther = melanistic *leopard* (not jaguar — avoids the Cats deck's Jaguar collision). Rename the Aggro placeholder hornet → **Tarantula Hawk** or another flying stinging insect; Velvet Ant no longer fits after the card gained Flight because the stinging females are wingless. Reconcile tag taxonomy: mark `Fish` active (Pufferfish uses it), pick one tortoise tag.
- [ ] **Re-cast animal names onto existing cards (flavor pass).** Keep mechanics fixed; revisit the species per effect so it fits "like a glove." Prioritize the generic `—`-tag cards (Honey Badger, Wild Boar, Armadillo). Filter: pick animals with a *famous specific behavior* (scavenges, plays dead, swarms) over "most iconic."
- [ ] **Colony eusocial-castes §2.1 exception (human ruling).** Bee/ant castes collapse to one species under §2.1, yet real colonies *are* one species across castes. Decide: carve a narrow "eusocial castes may repeat within the Colony tribe" exception (flavor-review's rec), or split the hive across species (advised against).
- [ ] **Balance-gated flavor changes (do NOT do silently).** Canine size-inversion: Fox 5 / Dingo 5 out-body Gray Wolf 4 — reskin which animal carries each engine, or lower the Fox/Dingo bodies (balance-gated → Balance). Apex "trample/raze" vs "eat" a Landmark (balance-gated; folded with the Landmark revisit in `../rules/backlog.md`).

## Card text
- [ ] **`cards.md` §5–9 — give the legacy pool sections a verdict (banner / rewrite / delete).** They're flagged "ignore" in this file's header but still read as plain description, and they're wrong on *substance*, not just wording: Anaconda is documented as "=discard / strength = the number of units in the discard" (shipped: STR 7, "Apex Predator." — **Goliath** is the removed-units scaler), Jackal as "return a unit from the discard to the top of your deck" (shipped: "Whenever an adjacent unit is removed, gain 5 food"), and **Raccoon isn't in the pool at all**. Surfaced 2026-07-15 by the Remove Pile sweep, which deliberately skipped them for this reason (see [`../rules/backlog.md`](../rules/backlog.md)) — renaming "discard" there would only make *wrong* descriptions well-worded. Decide: an in-file staleness banner, a rewrite from `decks/` (the source of truth), or deletion.
- [ ] **Standardize Deathrattle card-text wording across the pool.** Same trigger printed two ways: Opossum "Deathrattle: …" vs Impala/Gazelle/Phoenix "When this is removed, …". Pick one (rec "Deathrattle: …" per `../rules/keywords.md`) and apply uniformly in `cards.json` + deck files.

## Future
- [ ] **Ice Age expansion (parked).** Save Ice Age megafauna (mammoth, sabertooth, dire wolf) for a dedicated later set, not the 0.0.1 pool.
