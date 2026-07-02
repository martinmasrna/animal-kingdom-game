# Cards & Flavor — Backlog

Open items only. Top-3 summary in [`../STATUS.md`](../STATUS.md). Deck source of truth: `decks/`. Card-pool doc: `cards.md` (§5–9 are legacy — ignore).

> **Build #5 (rebuild `data/cards.json` + the effect registry from the deck files) is DONE** — `cards.json` carries the reworked pool and the 252-test suite runs on it. Remaining card work is flavor + text cleanup below.

## Flavor
- [ ] **Dedicated legendary-name review (all 28).** The stricter, do-not-skip pass before flavor-lock. 24/28 are provisional machine-suggested names (2026-06-30); only the 4 Cats are final. Check each against `cards.md` §2.1: (a) evoke, don't cite — extra scrutiny on borderline picks (Lobo, Shuck, Marabunta, Methuselah, Goliath); (b) real species only; (c) effect↔name fit "like a glove"; (d) no collisions / one-species rule (Borealis vs Polar Bear, Goliath vs Anaconda, Carmilla vs Black Widow); (e) tone/register consistency. Alternates in `decks/flavor-review.md` §3.
- [ ] **Reskins & collisions (pure, no mechanics).** Black Panther = melanistic *leopard* (not jaguar — avoids the Cats deck's Jaguar collision). Rename the Aggro placeholder hornet (→ Tarantula Hawk / Velvet Ant; collides with Colony's Guard Hornet). Reconcile tag taxonomy: mark `Fish` active (Pufferfish uses it), pick one tortoise tag.
- [ ] **Re-cast animal names onto existing cards (flavor pass).** Keep mechanics fixed; revisit the species per effect so it fits "like a glove." Prioritize the generic `—`-tag cards (Honey Badger, Wild Boar, Armadillo). Filter: pick animals with a *famous specific behavior* (scavenges, plays dead, swarms) over "most iconic."
- [ ] **Colony eusocial-castes §2.1 exception (human ruling).** Bee/ant castes collapse to one species under §2.1, yet real colonies *are* one species across castes. Decide: carve a narrow "eusocial castes may repeat within the Colony tribe" exception (flavor-review's rec), or split the hive across species (advised against).
- [ ] **Balance-gated flavor changes (do NOT do silently).** Canine size-inversion: Fox 5 / Dingo 5 out-body Gray Wolf 4 — reskin which animal carries each engine, or lower the Fox/Dingo bodies (balance-gated → Balance). Apex "trample/raze" vs "eat" a Landmark (balance-gated; folded with the Landmark revisit in `../rules/backlog.md`).

## Card text
- [ ] **Standardize Deathrattle card-text wording across the pool.** Same trigger printed two ways: Opossum "Deathrattle: …" vs Impala/Gazelle/Phoenix "When this is removed, …". Pick one (rec "Deathrattle: …" per `../rules/keywords.md`) and apply uniformly in `cards.json` + deck files.

## Future
- [ ] **Ice Age expansion (parked).** Save Ice Age megafauna (mammoth, sabertooth, dire wolf) for a dedicated later set, not the 0.0.1 pool.
