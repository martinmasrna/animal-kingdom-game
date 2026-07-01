# Design TODO

Open decisions and follow-ups parked during card design. Add freely.

## Card model / types
- [ ] **Revisit the `Landmark` (non-animal) card-type decision.** Provisionally resolved 2026-06-28 (see `docs/decks/README.md` decision C): §2 relaxed to allow non-animal cards used *sparingly*; `Unit`/`Egg` are units mechanically, `Landmark` is the lone non-unit type (invisible to "unit" wording, can't capture an HQ); rules text uses "occupant" as the umbrella noun. **Take another look before building `cards.json` + rules** — confirm Egg-as-unit causes no odd interactions, the "occupant" vocabulary reads cleanly across all card text, and the Landmark minority hasn't crept larger as decks get finished. **Flavor wart to weigh:** an Apex Predator landing on a Landmark "eats" it — a tiger eating a fig tree reads badly. Options when revisiting: accept it, make Landmarks untargetable by Apex Predator, or re-theme the Landmarks. **Status:** the Phase-1 `cards.json` build encodes `type: landmark` per decision C (provisional), so this is now a *confirm-or-revert* — not a blocker for the build.

## Future / expansions
- [ ] **Ice Age expansion (parked).** Save Ice Age megafauna (mammoth, sabertooth, dire wolf, etc.) for a dedicated later set rather than spending them in the 0.0.1 pool. (Came up filling Ramp's stomp legendary — used a "titanic hippo" instead of a mammoth to keep mammoth available for this.)

## Terminology
- [ ] **Rename "Discard" → "Remove Pile" across all docs/data.** Decision 2026-06-28 (README decision F): there is **one** shared pile, the Remove Pile (no separate discard pile); "remove" is the universal verb for any card sent there from hand/deck/board. Sweep `overview.md` §3.7 (and §11/§3.7 references), `cards.md`, and the staging files — replace "discard" wording. Two trigger tiers: **remove** (any card removed) vs **Deathrattle** (a unit leaving the board).

## Naming / keywords

### ⚠️ SPECIAL FLAVOR CHECK — LEGENDARY card names (dedicated human review, do not skip)
- [ ] **Deliberately re-review all 28 legendary names before flavor-lock — this is a *separate, stricter* pass than the general flavor pass below.** Legendaries are the marquee tier (§2.1: hardest to design — a unique effect *and* a fitting named-individual), so their names carry the most flavor weight and deserve their own focused look. **24 of the 28 are machine-suggested *provisional* names assigned 2026-06-30** (only the 4 Cats — Prince Leo / Princess Lea / King Theron / Queen Adira — are human-final). Names live in each deck's legendary table; 2–3 explained alternates per card are in `flavor-review.md` §3. Walk every legendary by hand and check each against the rules in `cards.md` §2.1:
  - **(a) Evoke, don't cite.** The name may carry light mythic/folklore/literary resonance but must **not** directly reference the myth-creature the card depicts (no "Phoenix", "Ouroboros", "Kraken", "Cerberus", "Roc", "Fenrir"). **Extra scrutiny on the borderline / strong-resonance picks** that lean on a real legend's own name: **Lobo** (Seton's real "Lobo, King of Currumpaw"), **Shuck** (England's "Black Shuck" black-dog), **Marabunta** (folkloric army-ant-swarm word), **Methuselah** / **Goliath** (biblical persons used for age/size). Each is *defensible* (person/word, not the depicted creature) but is exactly where the rule bends — confirm or swap to an alternate.
  - **(b) Real animal, no invented creatures.** Confirm every legendary is a *real* species. In particular the two reskinned cards: the former *howl* / *hellhound* are now real named wolves (**Clarion** / **Shuck**) — verify nothing else reads as invented/mythic.
  - **(c) Effect↔name "like a glove."** Re-judge that each name fits the *effect/role*, not just the species (the whole point of the provisional picks). `flavor-review.md` itself flags the soft spots (e.g. the octopus "draw a legendary" tie).
  - **(d) No collisions / one-species rule.** Confirm each legendary name is globally unique and that a legendary sharing a species with a common stays distinct (e.g. **Borealis** vs common **Polar Bear**, **Goliath** vs common **Anaconda**, **Carmilla** vs common **Black Widow**).
  - **(e) Tone/register consistency.** The Cats use royal titles; other decks use bare proper names + designer epithets (the Devourer, Keeper of the Stash, Champion of the Hive, the two Queens, the Rat King). Confirm the register reads as one pool.
  - **Does NOT block the `cards.json` build** — provisional names already give every legendary a stable name/id. This is pure flavor-lock; run it before art/printing.

### Other naming / keyword items
- [ ] **Rename the "Battlecry" keyword** (the "when a unit is placed" trigger). "Battlecry" is a placeholder borrowed from elsewhere; find a more on-theme name (rejected so far: Instinct, Pounce). Until settled, card text keeps saying "Battlecry:"
- [ ] **Rename the "Deathrattle" keyword** (the "when this is removed / leaves play" trigger). **Now in active use** across the reworked pool (Opossum, Impala, Gazelle, Phoenix, …) — kept as a placeholder keyword for now (decision 2026-06-28). Standardize on printing **"Deathrattle: …"** rather than writing out "When this is removed." Find an on-theme name later.
- [ ] **Standardize the Deathrattle card-text wording across the pool (concrete sweep, do at `cards.json` build).** The same trigger is printed two ways today: Opossum prints "Deathrattle: …" while **Impala / Gazelle / Phoenix** write out "When this is removed, …". Pick one form (recommend **"Deathrattle: …"** per `keywords.md`) and apply it uniformly to every Deathrattle card. This is separate from the keyword *rename* above — purely unifying the printed phrasing. Per `keywords.md`, keep the two tiers distinct: a *unit leaving the board* = Deathrattle; a card removed from hand/deck = a plain *remove*, **not** a Deathrattle.
- [x] **`Apex Predator` keyword fully specified** (2026-06-28, see `docs/keywords.md`): must land on an occupant; normal covering strength rules apply (strictly-greater for enemies, no req for own units); may eat your own units; cannot be placed on an HQ (deliberate — no direct HQ capture); destroys Eggs/Landmarks. *Lingering flavor wart — a predator "eating" a Landmark — folded into the Landmark revisit below.* **Amended 2026-07-01:** Apex is *not* restricted to prey it can eat — if the occupant can't be eaten (Immovable / enemy Untargetable), it now **covers/buries** it under normal placement rules instead of being unplayable there (see the Immovable/Untargetable rethink below).
- [ ] **⚠ DEDICATED DEEP-DIVE — re-examine `Immovable` and `Untargetable` from scratch (do a focused pass, don't just fold into other work).** This is flagged for its own sit-down review: walk every card that has, cares about, or interacts with these two keywords, tabulate the intended vs actual behavior across all effect types, and only then decide the model. Treat the notes below as the starting agenda, not a settled design. **Rethink the effects of `Immovable` and `Untargetable` (Black Panther) as a pair.** Right now they overlap almost entirely: in the code every unit-touching effect (single/mass removal, bounce/move, Hippo auto-remove) requires *both* `can_be_removed` **and** `can_be_targeted`, so the two keywords block the exact same *set* of effects — the only real difference is **owner scope** (Immovable resists *everyone's* effects incl. its own controller's; Untargetable resists *enemies only*, so you can still sacrifice/move your own Black Panther). Open questions to settle deliberately: (a) Should they block the same effect *types*, or should each have a distinct footprint (e.g. Immovable = can't be *moved/removed* but *can* be debuffed/targeted; Untargetable = can't be *singled out* at all but *can* be caught by non-targeted mass effects)? (b) Is "targeted" meant to include *mass* effects (Pestis/Bulwark wipes) or only single-target picks? (c) Confirm the new Apex ruling (cover-don't-eat) reads consistently for both, and decide the **Porcupine × Apex** and **Snow Leopard × Apex** edges (Apex legality currently uses a bare strictly-greater check, *not* `can_cover`, so Porcupine's "can't be covered by enemy" and Snow Leopard's equal-strength cover don't apply to an Apex landing). (d) Nail down flavor names/text so the two keywords read as clearly different abilities.

## Balance constants (tune together on one scale)

### ⚠ Reworked-pool tuning — the real G/H work (gates final balance; does NOT block the `cards.json` build)
- [ ] **(Decision G) Once-per-turn caps on value/food triggers — undecided; pick defaults + flag as sim dials.** Many reworked triggers state no cap and could spike on a busy turn. Decide a default (uncapped vs once-per-owner-turn) per card; treat the rest as sweepable dials. Prime suspects: **Queen Adira** (draw per Cat-kill) and **King Theron** (remove per Cat-cover) [Cats]; the Egg event-food engine — **Eon** (+1 per draw/shuffle/remove), **Rattlesnake** (+5/shuffle), **Vulture** (+2/remove), **Egg Eater** (+10/egg-removed); **Queen Honoria** (+5 per Colony played), **Worker Wasp** (+3 end of turn), **Soldier Ant** (gated removal) [Colony]; **Jackal** (+3 per adjacent removal) [Canine]. (Fox and Bush Dog already self-cap "once a turn".) Loop-risk pair to watch: **Falstaff** food-rider × **Queen Honoria** / Worker food in one chain.
- [ ] **(Decision H) Re-derive the whole food economy for the reworked pool (sim job).** Balance all the new numbers on one shared scale against `win_food` (100) and region output (`maps.json`), **replacing the legacy v0 set below** (which references retired cards). New magnitudes to tune: the 20-cost bodies + **Fig Tree** (+20) / **Watering Hole** Landmarks; **Gazelle** (+20 on death) and the sac-OTK burst; **Egg Eater** 10 / **Rattlesnake** 5 / **Vulture** 2 / **Eon** 1-per-event; **Queen Marabunta** (+4/Colony) / **Queen Honoria** (+5/play) / **Worker Ant** (+8) / **Worker Bee** (5+5) / **Falstaff** (+3 rider); **Chipmunk** (5+5) / **Squirrel** (+6); **Scrooge** store→2× window. Keep every number a placeholder in `engine/config.py` — tune there, never hard-code in effect logic. Depends on the M3 sim throughput.

### Legacy v0 constants (superseded by the G/H work above — most reference retired cards; kept for reference)
- [x] **Food economy — v0 set** (`cards.md` §4.5 *Food Economy Constants*): region 10/20, threshold 100, `F` plain 4 / low 3 / med 5 / high 8, Honeybee +4, Queen Bee +3, Driver Ant 2/unit, Raven cost 12, Bear ×2 over 2 turns. **Now needs sim tuning** — especially the ⚠ dials (Driver Ant scaling, Queen Bee stacking, Bear delay).
- [x] **Forager strength ↔ food budget (Combo):** inverse curve realized in v0 — Wild Boar (Str 5 → 3), Chipmunk (Str 3 → 5), Squirrel (Str 2 → 8), Honeybee (Str 1 → 8+). Confirm in sim.
- [x] **Spotted Hyena threshold `N` — v0 = 4** (control 4 other units to unlock "cover any strength"). Sim should sweep ~3–5.

## Bot-sim balance findings (M3 gauntlet / report)
Findings from bot-vs-bot simulation (`sim/report.py`, `sim/gauntlet.py`) worth a human look.
Caveat carried from `metrics.GREEDY_CAVEAT`: the bot is 1-ply greedy and underplays
combo/delayed-effect decks, so treat anything here as a *signal to investigate*, not final
balance truth, until sim quality is closer to competent human play.

- [ ] **Colony Food Swarm loses to board-presence decks before its engine can turn on
  (2026-07-01, real card-balance signal, not a bot-piloting artifact).** 150-game round-robin:
  overall win rate 23.1% (worst of the 7 decks), driven almost entirely by two matchups that
  **no amount of `GreedyWeights` re-tuning moves at all** (identical win rate across three
  tried presets): vs `cats_midrange` 2%, vs `canine_buff_tempo` 14%. Traced actual game logs
  (`python -m animal_kingdom.cli --bots greedy,greedy --decks colony_food_swarm,cats_midrange
  --seed 0`): the deck's only early plays are 1-3 strength Colony/Worker bodies (Worker Bee,
  Worker Wasp, Queen Bee), which can't hold a crossroad against `cats_midrange`'s efficient
  4-7 strength bodies (Lion, Black Panther, Caracal) or `canine_buff_tempo`'s snowballing
  persistent buffs. 6/8 sampled seeds vs `cats_midrange` end in `hq_capture` by turn 7-13
  (3-6 of the deck's own turns); 4/4 vs `canine_buff_tempo` end in `hq_capture` by turn 10-23.
  That's not enough time for the deck's actual payoff (Queen Honoria/Falstaff/worker-chain
  food swings) to ever come online, regardless of piloting quality - weight tuning got a real
  but small +2-3% overall improvement (helps the winnable matchups, e.g. `food_otk`/`ramp`)
  and made zero difference in these two specific matchups. **Worth a card-design look:** the
  deck may need a cheap efficient early blocker, or its engine needs to pay off faster.

- [ ] **`cats_midrange` vs `aggro_hq_rush`: bot-sim says `cats_midrange` crushes it (~10-12%
  win rate), but human playtesting (2026-07-01) directly contradicts this - martin played the
  matchup 3 times as `aggro_hq_rush` and won 2. Root-caused to a bot piloting flaw, not a card
  power-level problem; downgraded from the original "cats_midrange may be overpowered" framing.**
  Traced `colony_food_swarm`/`food_otk`/`aggro_hq_rush` all losing to the same `cats_midrange`
  row-2 connected-chain rush (HQ capture turn 7-13), and retuning the losing decks'
  `GreedyWeights` didn't help (`food_otk` -0.7% overall; `card_economy` alone moved **zero**
  of 300 sampled games). That looked like a `cats_midrange` power-level issue - until stepping
  through the `aggro_hq_rush` vs `cats_midrange` seed=1 loss action-by-action: at every one of
  turns 0/2/4 the bot had a `DrawAction` available and instead dumped its hand (Jerboa -> Rat
  -> Mouse -> Lemming) into marginal placements, never holding to draw into its actual
  disruption tools (Hornet/Skunk/Pestis/Rat's own removal - Rat was played on an empty board
  before any target existed). It ran out of cards and lost turn 7 having never deployed a
  single piece of interaction. That's the same "1-ply plays too eagerly, can't hold for a
  better line" pattern as the Grizzly Bear/own-line-lookahead findings above - a bot quality
  gap, not evidence `cats_midrange` needs nerfing. **Take-away:** trust human playtests over
  bot-sim win rates for "is this deck too strong" questions until the bot can hold cards /
  sequence removal like a competent player; keep the row-2-rush *mechanic* itself in mind
  (worth watching whether real humans can also be run over by it), but don't act on the 76%
  round-robin number alone.

  **Update (2026-07-01) - shipped a fix, partially closes the gap:** added a generic
  `wasted_battlecry` penalty to `GreedyBot` (see `bots/greedy_bot.py::_battlecry_fizzled`,
  tests in `test_greedy_bot.py`) - detects, from before/after state alone (no per-card
  special-casing), whether a played card's ability text fired for literally nothing (no
  food/removal/draw/buff beyond the unit landing) and discourages it, so the bot now prefers
  Draw or a different card over e.g. playing Rat into an empty board. Caught and fixed a
  related bug along the way: a battlecry that opens a pending sub-choice (e.g. Rat *with* a
  target - "which adjacent enemy") was being scored before that choice resolves, so it was
  wrongly flagged as fizzled too; `_battlecry_fizzled` now treats an open `state.pending` as
  "a live effect mid-resolution", not a fizzle. Validated via a clean 150-game round-robin
  (matched sample size against the original baseline, not the noisier 40-game runs used
  mid-investigation): **`aggro_hq_rush` +6.0% overall** (`cats_midrange` +3.5%, `food_otk`
  -2.8%, others within ~2%) - real and now the default, though not uniformly positive across
  the field (the decks that lean hardest on targeted-removal battlecries, `cats_midrange`
  included, benefit more from more-correct play than decks that don't - the same "a smarter
  bot can widen the gap" pattern as the earlier lookahead work). *But* the specific
  `aggro_hq_rush` vs `cats_midrange` matchup that started this investigation is **still
  exactly 13.3%** (was 12.0%/13.3% before either fix, unchanged) - the hand-dumping fix
  didn't touch whatever else is actually losing that specific matchup for the bot. Still
  open; still trust the human read (2/3 for aggro_hq_rush) over this number until further
  diagnosed.

## Card-specific tuning
- [ ] **Queen Bee (Combo):** keep additive (`+F` per food gain); watch for stacking multiple copies.
- [ ] **Hibernating Bear (Combo):** confirm the 2-turn delay and that "lose all food" + Immovable can't be abused.

## Flavor (reworked-pool review follow-ups)
Action items from `flavor-review.md` (the 7-deck flavor audit). The legendary-name pass is tracked separately under *Naming / keywords* above; the per-card "re-cast the animal" pass is the last item under *Engine / performance* below.

- [ ] **Pure reskins — no mechanics (do at/before the `cards.json` build).**
  - **Pin Black Panther = melanistic *leopard*** (Panthera pardus), not jaguar, so it doesn't duplicate the Cats deck's own **Jaguar** (one-species violation). Add a one-line art note.
  - **Rename the Aggro rare `[a hornet]`** — still an unnamed placeholder *and* a pool-wide species collision with Colony's **Guard Hornet**. Reskin to a distinct stinging insect: **Tarantula Hawk** or **Velvet Ant**. *(This is the one remaining non-legendary naming gap.)*
  - **Reconcile the README tag taxonomy:** mark **`Fish`** *active* (Pufferfish uses it; README still lists it "dormant"); pick **one tortoise tag** (Ramp's colossal tortoise = `Megafauna` vs Food OTK's Giant Tortoise = tagless — flavor-review leans tagless for both).
- [ ] **Human ruling — Colony "eusocial castes" exception (§2.1).** Honey-bee castes (Queen/Worker/Nurse Bee) and ant castes (Worker/Soldier Ant) each collapse to one species under §2.1, yet README A/B bless caste-distinctness and real colonies *are* one species across many castes. Decide: formally carve a narrow "eusocial castes may repeat within the Colony tribe" exception into §2.1 (flavor-review's recommendation), or split the hive across species (advised against). No silent change.
- [ ] **⚠ Balance-gated flavor changes — need a separate balance review (do NOT do silently).**
  - **Canine size-inversion:** Fox 5 / Dingo 5 out-body Gray Wolf 4 / Coyote 3 (a fox out-muscling a wolf). Either reskin which animal carries each engine (pure, no mechanics) **or** lower the Fox/Dingo bodies toward real canid sizes (balance-gated).
  - **Apex Predator "eats" a Landmark** (a tiger devouring a fig tree) reads badly; option is to let Apex Predators *trample/raze* rather than eat a Landmark — balance-gated. Folded with the Landmark revisit (*Card model / types*).

## Engine / performance
- [ ] **State-representation speed tradeoff (revisit before NN bots).** The engine currently uses per-unit Python objects (`UnitInstance`) referencing shared immutable `Card` flyweights by id — chosen for correctness, serializability, and readability, and fine for the near-term goal of *thousands* of greedy-bot games. **This will not be fast enough** once we move to **neural-network / AlphaZero-style bots** (MCTS needs millions of cheap state clones + fast batched feature extraction). When we get there, switch the *in-play* representation to **struct-of-arrays / entity-component** (parallel integer arrays indexed by board slot, cloned via array/bytes/NumPy copies, no per-unit objects) and add a tensor-encoding of the per-seat view for the network. The data layer (`cards.json`) and the id-keyed effect registry are deliberately decoupled from the in-play representation, so this is a localized change to `state.py`, not a rewrite. **Measure clone cost in M3 first** (the sim already needs throughput metrics) so the switch is driven by real numbers, not guesswork. Keep `UnitInstance` lean (`__slots__`, primitives only) in the meantime so the gap is as small as possible.
- [ ] **Flavor pass — re-cast animal names onto existing cards.** Keep the mechanical skeleton (effects/roles/archetype ratios) fixed, but revisit the animal assigned to each card so the species fits its effect "like a glove" — pure renaming, no balance impact. Prioritize the cards currently carrying a generic `—` tag (e.g. Honey Badger, Wild Boar, Armadillo, the anchors), which are where effect-first design shows its seams. Selection filter: pick animals with a *famous specific behavior* (scavenges, steals, plays dead, swarms) rather than just "most iconic," so swarm/utility roles don't get starved in favor of big megafauna.