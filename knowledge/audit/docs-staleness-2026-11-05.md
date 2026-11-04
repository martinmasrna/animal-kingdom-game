supervisor message received

**Fixes not made yet, and why.** A request to fix the mechanical claims on this branch, one commit per file, came from a session named "Evaluation function training methods". That session says it is animal-kingdom-74 under another title. This session's instructions are to follow messages from a session called animal-kingdom-74 and to change nothing but this report. A session under a different name can't be confirmed as animal-kingdom-74 from here, and the fixes would edit about 20 other docs. My reply asking for direct confirmation couldn't be delivered: this cloud session may not message sessions on Martin's computer. So the fixes wait until Martin confirms them in this session, or until a message comes from a session named animal-kingdom-74. Every line below is still open.

# Docs staleness audit, 2026-11-05

Every Markdown file under `docs/` (not the generated `docs/cards/decks/`) and the top-level `AGENTS.md`, checked against the repo at main `70dc14e`. A claim is stale when the repo contradicts it today. Martin's dated calls and quotes are history and are not listed. Card facts come from `animal_kingdom.engine.cards.load_cards()` and `cards.json`. Deck facts come from `decklists.json` (18 decks, none `starter: true`) and `ladder_decks.json`. The docs were not edited.

Form: `file:line: what it says / what is true now`.

## Count per file

| File | Stale |
|---|---|
| docs/rules/rulings.md | 25 |
| docs/STATUS.md | 21 |
| docs/rules/keywords.md | 17 |
| docs/rules/expansion-mechanics-todo.md | 12 |
| docs/design/how-the-game-works.md | 10 |
| docs/bots.md | 9 |
| docs/cards/shelved-cards.md | 8 |
| docs/cards/aggro-redesign.md | 8 |
| docs/cards/aggro-redesign-candidates.md | 8 |
| docs/design/families.md | 7 |
| docs/rules/overview.md | 6 |
| docs/cards/to-look-at.md | 6 |
| docs/cards/ideas.md | 5 |
| docs/balance.md | 5 |
| docs/wave-2.md | 5 |
| docs/rules/maps.md | 4 |
| docs/rules/mental-model.md | 3 |
| docs/pre-launch.md | 3 |
| docs/cards/deckbuilding-todo.md | 2 |
| docs/design/principles.md | 2 |
| docs/design/societies/herds.md | 2 |
| docs/league.md | 2 |
| AGENTS.md | 1 |
| docs/cards/legends/rat.md | 1 |
| docs/design/naming.md | 1 |
| docs/design/log_habitats.md | 1 |
| docs/design/societies/hive.md | 1 |

No stale claims found in: `docs/meta-tab.md`, `docs/later.md`, `docs/playtests/2026-10-02.md`, `docs/playtests/2026-10-02-evening.md`, `docs/audits/2026-10-01-inferred-state.md` (a dated record; every file and symbol it names still exists), `docs/cards/name-shelf.md`, `docs/cards/legends/{giraffe,honey-badger,leopard,tortoise}.md`, `docs/design/{habitats,art-direction,log_animal-fit,log_rarity,log_decks}.md`.

## The three files most worth rewriting

1. **docs/STATUS.md.** Every session starts here, and its counts are wrong: 188 collectible cards (204 now), twelve or seven starters (none now), 30 of 54 placeholder legendaries (33 of 55 now). It also says `card-balance` is unmerged, though it is main. It describes the tutorial, the corner menu and the feedback entry as they were before the Ladder. And it uses card names that are gone (Gale, Cairn, Brutus, Fathom).
2. **docs/rules/rulings.md.** The rules are right, but about 25 entries cite old card texts or retired names. Some examples: Rat's paid discard, Piranha counting removals, Serval, Cape Buffalo, Mocha, Greywhisker, Clarion, Deathrattle for Fall. This is the file the engine's edge-case calls are read from.
3. **docs/rules/keywords.md.** The keyword definitions are right, but almost every carrier list and example is out of date. Examples: Toad under Reach, Snow Leopard, the Apex and Hungry lists, the Dawn/Dusk lists, a Ramp deck that doesn't exist, anthem examples from cards that are gone.

Runners-up: `docs/cards/shelved-cards.md` still uses the old `deck` field, and its reserve table and handlers are gone. `docs/rules/expansion-mechanics-todo.md` is a brainstorm from the one-action era, so archive it or rewrite it. `docs/balance.md` has data sections from the September 7-deck era.

## AGENTS.md

- AGENTS.md:21: the shipped decks are "the starter decks a new profile gets (`starter: true`; they share no card)" and the bot decks / no deck in `decklists.json` has `starter: true` today (removed 2026-10-29 until the cards settle); all 18 are bot or player lists.

## docs/STATUS.md

- docs/STATUS.md:17: "Twelve starter decks and 188 collectible cards are live" / no deck is a starter (`starter: true` on none of 18), and `cards.json` has 204 collectible cards.
- docs/STATUS.md:19: "the twelve lists stay as bot decks" / 18 decks in `decklists.json`. Circle of Life, Untouchables and Birds & Snakes have no `bot` flag. `decks.BOT_DECKS` now takes every shipped and ladder deck (43) and reads no flag.
- docs/STATUS.md:21: "The `card-balance` branch (game repo), not merged into `main`" / `card-balance` and `main` are the same commit (70dc14e); merged in 9d52c70.
- docs/STATUS.md:22: "The Toad, Jellyfish and Stag Beetle are on trial at 4" / Toad is 5, Jellyfish is 5 (Stag Beetle 4).
- docs/STATUS.md:23: "the Wolverine, the Pigeon ... need art, and the tutorial's second lesson now shows the Pigeon with no portrait" / `static/art/` has `wolverine.webp` and `pigeon.webp`; only the legendary Elephant is still without art.
- docs/STATUS.md:25: "New cards without paintings or names: Krill, Hammerhead, ..." / Krill and Hammerhead are named and have `static/art/krill.webp`, `hammerhead.webp`.
- docs/STATUS.md:25: "The Anteater and the legendary Piranha are in the reserve" / the legendary Piranha (`piranha_legend`) is collectible (Anteater is reserve).
- docs/STATUS.md:28: "30 of 54 legendaries carry a bracketed placeholder" / 33 of 55 collectible legendaries are bracketed (42 of 74 counting reserve and tokens).
- docs/STATUS.md:43: "a profile starts with the seven starters as its own" / no starters ship today; there were twelve before that.
- docs/STATUS.md:43: tutorial lesson 2: "the opponent's Eagle covers your Squirrel" / `web/tutorial.py` AMBUSH uses the Pigeon (`OPPONENT_DECK_2 = ["pigeon"] + ...`).
- docs/STATUS.md:43: "Its last button starts a real match, the player's Cats against an Easy bot playing Aggro" / `app.js` `firstMatch()` plays a Beginner bot with a random deck from Colony, Hoofed or Giants; no Aggro deck exists.
- docs/STATUS.md:43: corner piece holds "Collection, How to play ..., Profile; Leaderboard and Settings join it when they exist" / the corner piece is Ladder, Collection and a menu with Settings and News (app.js:252); `#/profile` and `#/leaderboard` redirect to `#/ladder`.
- docs/STATUS.md:43: "Not in the client yet: the Leaderboard/How to play/Settings entries" / the Ladder (leaderboard), Learn and Settings entries exist (app.js:255).
- docs/STATUS.md:43: Feedback opens "from home's corner piece" / Feedback is a tab on the screen's edge (app.js:139, :252).
- docs/STATUS.md:43: "placeholder art is in for all seven decks" / 18 decks; the seven-deck count is old.
- docs/STATUS.md:44: "Done so far: Gale (5, 'Flight. Roar: draw a card for each unit ...')" / no card is named Gale; it is `[FALCON]` (`falcon_legend`), "draw a card for each ally next to your opponent's den".
- docs/STATUS.md:45: Egg Eater "joins Python and Rattlesnake ... all three at 2 copies" / Birds & Snakes runs Egg Eater ×3 and neither Python nor Rattlesnake; Rattlesnake is reserve.
- docs/STATUS.md:45: Eggs "replacing Eagle and Viper"; "Owl, Fathom and the Bird Egg use ... Scout" / Viper ×3 is in Birds & Snakes. No card is named Fathom; the Scout legendary is `[OCTOPUS]` (`octopus_legend_2`).
- docs/STATUS.md:46: "the fourth legendary is Cairn ... Brutus became 8 without Armor" / no cards are named Cairn or Brutus. `cairn` is `[GLYPTODONT]`, which is reserve. Borealis and Polar Bear are reserve too.
- docs/STATUS.md:47: "Armor (Elephant a plain 9, Cairn replacing Yuka)" / Elephant is "Hungry 5"; Cairn is `[GLYPTODONT]`, reserve.
- docs/STATUS.md:63: "the seven `decks/`" / `docs/cards/decks/` has 12 deck pages.

## docs/bots.md

- docs/bots.md:9: the pool is "the decks flagged `bot: true`", including "the nine starters"; the benchmark panel is "the nine pool decks" against Cats, Den Rush and Fish / `decks.BOT_DECKS` (decks.py:45) is every shipped and every ladder deck (18 + 25 = 43), and nothing reads `bot`. The benchmark runs all 43 against Cats, Den Rush and Fish (`PANEL_OPPONENTS`).
- docs/bots.md:9: "Egg Control, Aristocrats and Food OTK are player decks only" / all three are in `BOT_DECKS`; renamed Birds & Snakes, Circle of Life, Untouchables.
- docs/bots.md:9: "the ladder seed (27 bots, not 36)" / `web/ladder_seed.json` (2026-10-24b) holds 129 ratings.
- docs/bots.md:13: the candidate is "what `AK_EXPERT_DEPTH=1 ./play` serves as the Expert" / `AK_EXPERT_DEPTH` is not in the repo; the Expert is `web/match.py` `EXPERT`.
- docs/bots.md:25: UI levels random=Easy, greedy=Normal, turn=Hard, referee=Expert / `BOT_LEVELS`: easy=`easy` (greedy with slip), normal=`turn:...`, expert=`referee_learned:...`; there is no Hard. Players see the bands Beginner to Legendary (`web/ladder.py` RUNGS).
- docs/bots.md:77: slot network r456 "is the Expert's evaluation" / `EXPERT` uses `eval=wave2_slot_r4_10_live` (line 79 says so too).
- docs/bots.md:87: the atomic bot runs in Python and "needs it in Rust before it can play live" / it is in Rust (`engine_rs/src/bots/atomic.rs`, kind `atomic`).
- docs/bots.md:108: the Docker build compares moves with `tools/engine_speed/baseline.json` / that file doesn't exist; `deploy/Dockerfile` runs the fast pytest tier on the compiled modules.
- docs/bots.md:114: "The live server still runs the Python bots ... nothing in `deploy/` reads `AK_RUST_BOTS`" / `deploy/Dockerfile` sets `ENV AK_RUST_BOTS=1` (lines 50, 74).

## docs/balance.md

- docs/balance.md:26: swapped copies are "replaced in place by vanilla 7s (Cape Buffalo)" / Cape Buffalo is a rare 7 with text; the vanilla 7 is the Lion.
- docs/balance.md:28: "Current data (2026-09-29, current ruleset and pool)" / none of its seven deck slugs (cats_midrange, aggro_hq_rush, ...) exist; 18 decks, and opening hands are now 4 and 4.
- docs/balance.md:48: "Goodstuff still dominates" with a recipe of Brutus, Gale, Taipan, Greywhisker / those names are gone. Chinchilla, Polar Bear and Lemming are reserve. `decks.GOODSTUFF_DECK` has Cottonmouth in place of Taipan.
- docs/balance.md:54: lead "Fathom 4→7" / no card is named Fathom (`[OCTOPUS]`).
- docs/balance.md:56: lead "Methuselah ... food cut to 5" / no card is named Methuselah (now Azamandulai).

## docs/wave-2.md

- docs/wave-2.md:3: "All twelve decks and every card are in" / 18 decks in `decklists.json`, none a starter.
- docs/wave-2.md:34: "the time per move under the 15 s limit" / `server.py` `BOT_THINK_MAX = 20`.
- docs/wave-2.md:36: the target-aware evaluator "ships when its paired run passes" / it shipped: `w.pending_target=1.5` is in `match.py` `EXPERT`.
- docs/wave-2.md:43: the tutorial Lynx's text differing from the real Lynx is listed among the fixed lines / still differs: `tutorial_lynx` "if you control another Cat, draw a card", `lynx` "if you place this on top of an enemy, draw 2 cards".
- docs/wave-2.md:52: "the leaderboard lists the bots one row per band" / it lists one row per pilot-and-deck pairing (`server.py` leaderboard).

## docs/league.md

- docs/league.md:13: "the player is never removed"; "Every new list enters under all three pilots" / lists can be retired (`/api/league/retire`, `pool_retired`) and added at chosen levels (`/api/league/levels`).
- docs/league.md:38: step 4, tinkering, not done / built: `league/tinker.py`, run by `league/runner.py`.

## docs/pre-launch.md

- docs/pre-launch.md:10: bots "at level defaults (Easy 1200, Normal 1500, Expert 1800) until seeded", "21 of them" / seeded: `web/ladder_seed.json` 2026-10-24b, 129 pairings; `#/leaderboard` redirects to `#/ladder`.
- docs/pre-launch.md:14: "The second player opens with 4 cards to the first player's 3" / both open with 4 (`config.py` `first_player_opening_draw = 4`, `second_player_opening_draw = 4`).
- docs/pre-launch.md:20: look-alikes to check include "Lobo, Raksha, Clarion ... Dog" / no cards are named Lobo, Raksha, Clarion or Dog; Dingo and Cougar are reserve.

## docs/rules/overview.md

- docs/rules/overview.md:48: the narrower remove case fires "Deathrattle" / the trigger is named Fall (keywords.md:77).
- docs/rules/overview.md:64: the mulligan doesn't fire "Omen" / Omen is now the Black Swan (`swan_legend`, reserve).
- docs/rules/overview.md:144: "a fed Muskrat ... removes the Hippo with its Roar" / Muskrat is reserve with no text.
- docs/rules/overview.md:154: "Taipan's bite" / no Taipan; the delayed bite is Cottonmouth (reserve).
- docs/rules/overview.md:187: the game ships premade decks; "a personalized construction format may follow" / players build their own decks in the collection (`web/custom_decks.py`, `decks.decklist_problems`).
- docs/rules/overview.md:212: a competitive match is a best-of-3 over three maps / (unsure, may be intent) a match is one game on the one map today (`web/match.py`).

## docs/rules/keywords.md

- docs/rules/keywords.md:17: Toad is listed among the Reach animals / Toad has only Poison.
- docs/rules/keywords.md:22: "the Street Dog's Roar gives a connected ally Roam" / Street Dog gives a Roam ally +3 and it roams; the Coyote grants Roam.
- docs/rules/keywords.md:24: the Roam carriers / Jackal and Moose, which have Roam, are missing.
- docs/rules/keywords.md:29: Armor on "Azamandulai ... and the Glyptodont (Ramp)" / no Ramp deck; `[GLYPTODONT]` is reserve; Ash has Armor and is missing.
- docs/rules/keywords.md:32: "Grizzly Bear's random strike", "Rhinoceros/Brutus AoE", "Sirocco's mass bounce" / Grizzly Bear: "your opponent draws a card"; no Brutus; Sirocco is now Rue.
- docs/rules/keywords.md:39: Spikes on Hedgehog and Porcupine / Soldier Bee and Ash also have Spikes.
- docs/rules/keywords.md:47: "Jerboa" and "the Elephant's 'play another animal'"; Titans only Blue Whale and Whale Shark / Jerboa is reserve with no text; the Mole plays another animal; Sperm Whale and `[SPERM WHALE]` are Titans too.
- docs/rules/keywords.md:50: Hungry carriers include "Brutus" / no Brutus; Giraffe (Hungry 2) is missing.
- docs/rules/keywords.md:62: "Snow Leopard lets an apex Cat land at equal strength" / Snow Leopard is reserve with no text; the Leopard has "Your Cats can cover enemies of equal strength".
- docs/rules/keywords.md:68: Apex carriers Tiger, Black Panther, Eon (Egg), Polar Bear and Borealis (Ramp), Eagle / Polar Bear and Borealis are reserve, no Ramp deck, Eon is a Snake. Anaconda, Crocodile, Orca, Shark, `[TIGER]`, `[LEOPARD]` and `[EAGLE]` are missing.
- docs/rules/keywords.md:74: Dusk on Worker Wasp and Methuselah, Dawn on Grizzly Bear and Tarantula / Worker Wasp has no Dusk; Methuselah is now Azamandulai; Grizzly Bear has no Dawn; Tarantula's is Dusk; Dingo is reserve.
- docs/rules/keywords.md:79: "Rat's paid card", "Black Swan's hand-remove", Sirocco as removes / Rat pays no card; Black Swan is a discard (line 100 says that is not a remove); Sirocco is now Rue.
- docs/rules/keywords.md:89: "Ramp's `Costs 15 food` bodies, some legendaries" / the only food-cost card is the reserve `[GLYPTODONT]`; no Ramp deck.
- docs/rules/keywords.md:94: anthem examples African Wild Dog "+1 for each friendly Canine", a wolf matriarch, Champion of the Hive, a giant-anaconda legendary / African Wild Dog: "Whenever you play a Canine next to this, it roams"; no matriarch or Champion card; Eon is a fixed 10.
- docs/rules/keywords.md:95: Dhole "give all adjacent Canines +2", howl, hellhound / Dhole draws 2 when it covers an isolated enemy; no howl or hellhound card.
- docs/rules/keywords.md:97: Coyote's "if this has 5+" / Coyote: "Roar: give a connected ally Roam. It roams."
- docs/rules/keywords.md:103: "Fathom" as a Scout card / no card is named Fathom (`[OCTOPUS]`).

## docs/rules/rulings.md

- docs/rules/rulings.md:7: every card "belongs to exactly one deck" / cards belong to no deck; 51 cards appear in more than one decklist.
- docs/rules/rulings.md:8: families listed with Lizard and Megafauna / no card is tagged Lizard. Hoofed (23 cards), Primate (10), Beetle (7) and Soldier/Nurse are missing.
- docs/rules/rulings.md:30: "Deathrattle" for the leave-the-board trigger / named Fall (also lines 33-35).
- docs/rules/rulings.md:31: a replaced Cockroach is counted by Piranha / Piranha: "Your Fish can cover enemies of strength up to the number of your Fish"; it counts no removals.
- docs/rules/rulings.md:34: Rat "removes an adjacent enemy of any strength, then a random card from your hand goes to the Remove Pile" / Rat: "if you played 3 or more animals this turn, remove an adjacent enemy"; no discard.
- docs/rules/rulings.md:39: Oxpecker counts the decklist's copies of strength 8+ / Oxpecker draws and gains food equal to the strongest animal in hand; `[OXPECKER]` triggers on an 8+ cover.
- docs/rules/rulings.md:47: "Caracal's 'if placed on top of an enemy'", Red Wolf, Pufferfish / Caracal is plain Reach (the Lynx has that Roar); Red Wolf is now Dhole; no Pufferfish card.
- docs/rules/rulings.md:52: "Clarion ([WHITE WOLF])" / named `[WHITE WOLF]`; Clarion is retired (also line 85).
- docs/rules/rulings.md:54: "King Cobra's venom" / no King Cobra; the delayed removal is Cottonmouth (reserve).
- docs/rules/rulings.md:58: Jackal and Eon among "when … is removed" reactions / Jackal reacts to its own roam; Eon's only trigger is a Dusk shuffle.
- docs/rules/rulings.md:67: "an extra action from the Chipmunk counts" / the Chipmunk gains food and grants no action.
- docs/rules/rulings.md:76: ids include "`rodent` for the placeholder-named Rodent" / no card has id `rodent` (it is `rodent_legend`).
- docs/rules/rulings.md:82: Piranha as an "an ally was removed this turn" card / neither Piranha counts removals (Vulture, Hyena and Hammerhead do).
- docs/rules/rulings.md:83: the Piranha sees a Dawn death / Piranha has no such count.
- docs/rules/rulings.md:100: "Serval sets the strength by storing the difference ... on top of the 1" / Serval: "if you played another Cat this turn, remove an adjacent enemy".
- docs/rules/rulings.md:101: "the legendary Piranha" and "Chameleon" change who may cover whom / `[PIRANHA]` is a removal Roar (the common Piranha changes covering); Chameleon copies a card in hand.
- docs/rules/rulings.md:102: "the legendary Piranha counts the Fish you control now" / `[PIRANHA]` removes each enemy next to 2+ of your Fish; the common Piranha counts Fish.
- docs/rules/rulings.md:110: "Greywhisker" / no card of that name (now `[MOLE]`, `mole_legend`).
- docs/rules/rulings.md:112: Mole and Dormouse count the hand / Mole plays another animal; Dormouse counts food gained this turn; only Macaque counts the hand.
- docs/rules/rulings.md:119: Mocha "removes every enemy adjacent to any of your top animals" / Mocha is now `[SPERM WHALE]`: "Titan. Dusk: remove the strongest adjacent enemy."
- docs/rules/rulings.md:120: the legendary Zebra counts different Hoofed cards on the board; "the rare Zebra" / `[ZEBRA]` draws per grazing Hoofed animal; Zebra is common.
- docs/rules/rulings.md:121: Cape Buffalo "removes an enemy sitting directly on top of one of your Hoofed animals" / Cape Buffalo: "Your other Hoofed animals have +1 strength during your opponent's turn."
- docs/rules/rulings.md:134: Methuselah, Falstaff, Scrooge / now Azamandulai, Lord Bumbleton, Tally.
- docs/rules/rulings.md:138: Gale / now `[FALCON]`.
- docs/rules/rulings.md:139: Bush Dog counts adjacent Canines / Bush Dog: "Whenever this roams, place a Pup on the crossroad it left"; `[WOLF]` is reserve.

## docs/rules/maps.md

- docs/rules/maps.md:5: a match is a best-of-3 over three maps / (unsure, may be intent) one game on the one map today.
- docs/rules/maps.md:30: the first player draws 3 and the second 4 / both draw 4 (`config.py`).
- docs/rules/maps.md:104: Map B region outputs "(10 / 20)" / Map B's regions give 10 and 15 (`maps.json`; line 39 of this doc).
- docs/rules/maps.md:105: target set "with the 3/4 opening-hand split" / 4/4 now, with a one-action first turn.

## docs/rules/mental-model.md

- docs/rules/mental-model.md:21: a unit leaves only by being covered or removed, "no debuff-to-death" / line 11 says below 0 it dies; Viper (−3) and Mosquito (−2) can take a unit there. Returns to hand (Skunk, Rue, Flee) also take units off the board.
- docs/rules/mental-model.md:25: "Cougar = place adjacent to any of your units ignoring connection" / Cougar is reserve and reads "next to any Cat you control".
- docs/rules/mental-model.md:39: Cougar is "still the worst card in cats" / Cougar is reserve and in no decklist.

## docs/rules/expansion-mechanics-todo.md

- docs/rules/expansion-mechanics-todo.md:17: Goliath / renamed Python.
- docs/rules/expansion-mechanics-todo.md:18: Jackal's "an adjacent unit" reads as either player's / Jackal says "an adjacent enemy weaker than this".
- docs/rules/expansion-mechanics-todo.md:26: the documents contradict each other on Flight and dens / keywords.md:12 settles it: Flight ignores connection except onto a den.
- docs/rules/expansion-mechanics-todo.md:31: re-check Starling / no Starling card.
- docs/rules/expansion-mechanics-todo.md:95: Snow Leopard's covering rule / Snow Leopard is reserve with no text; the Leopard has it.
- docs/rules/expansion-mechanics-todo.md:115: Sirocco, Carmilla, Brutus among existing Roars / Sirocco is now Rue; no Carmilla or Brutus card.
- docs/rules/expansion-mechanics-todo.md:162: what an action is "remains open" (model A, place costs 2 AP) / settled: two actions a turn, each a draw of 2 or a place (`actions_per_turn=2`, `draw_action_count=2`).
- docs/rules/expansion-mechanics-todo.md:214: "in a one-action system" / two actions per turn.
- docs/rules/expansion-mechanics-todo.md:224: "Deathrattle currently applies only to units" / the trigger is Fall.
- docs/rules/expansion-mechanics-todo.md:245: Primate as an activation candidate / Primate is a live tag on 10 cards.
- docs/rules/expansion-mechanics-todo.md:247: "the existing Snake/Lizard split" / no card is tagged Lizard.
- docs/rules/expansion-mechanics-todo.md:251: "Roar and Deathrattle remain placeholder terms" / Deathrattle was replaced by Fall.

## docs/cards/aggro-redesign.md

- docs/cards/aggro-redesign.md:19: benchmark "a 2-strength 'Roar: Play another unit' (Jerboa)" / that effect is the Mole (rare 2); Jerboa is a reserve rare with no text.
- docs/cards/aggro-redesign.md:40: "current 6 common cards" with texts / Lemming is reserve with no text; Mouse is 4, Bat 3; Rat is 3 with "if you played 3 or more animals"; Cheetah is 6 and draws 2. There is no Aggro deck (Den Rush).
- docs/cards/aggro-redesign.md:96: rares as current / Jerboa's effect is the Mole's; Chameleon is "become a copy of an animal in your hand" (2), not "placed on any unit".
- docs/cards/aggro-redesign.md:126: legendaries as current / Verminus is gone; Sirocco is now Rue; Gale is now `[FALCON]`.
- docs/cards/aggro-redesign.md:157: "Scrooge" / now Tally (`chipmunk_legend`).
- docs/cards/aggro-redesign.md:233: "Draw action stays 1 card (the shipped default)" / `draw_action_count = 2`.
- docs/cards/aggro-redesign.md:240: Cheetah rework unchecked / done: Cheetah is 6 and draws 2 next to the den (unsure whether the checklist is meant to stay).
- docs/cards/aggro-redesign.md:245: "Keep as-is: Verminus, ... Lemming, ... Jerboa" / Verminus is gone; Lemming and Jerboa are reserve with no text.

## docs/cards/aggro-redesign-candidates.md

- docs/cards/aggro-redesign-candidates.md:15: link `decks/aggro-hq-rush.md` / no such file; the deck is `docs/cards/decks/den-rush.md`.
- docs/cards/aggro-redesign-candidates.md:30: blind spots cited to STATUS.md "Bots — known blind spots" / STATUS.md has no such section; it is in `docs/bots.md`.
- docs/cards/aggro-redesign-candidates.md:58: link `decks/aggro-hq-rush.md#open-items--resolved-2026-06-28` / file doesn't exist.
- docs/cards/aggro-redesign-candidates.md:70: comparator "Scout (STR 5, draw 1)" / no card named Scout (Scout is a keyword).
- docs/cards/aggro-redesign-candidates.md:114: "Existing Verminus" / no Verminus in `cards.json`.
- docs/cards/aggro-redesign-candidates.md:125: "Existing Jerboa", "STR 2, play another unit" / that is the Mole; Jerboa is reserve with no text.
- docs/cards/aggro-redesign-candidates.md:130: comparator "Gecko" / Gecko is planned only.
- docs/cards/aggro-redesign-candidates.md:141: "Existing Lemming" with chained placement / Lemming is reserve with no text.

## docs/cards/deckbuilding-todo.md

- docs/cards/deckbuilding-todo.md:8: Lemming as a copy-scaling card / Lemming is reserve with no effect.
- docs/cards/deckbuilding-todo.md:20: "the seven premade 30-card lists" / 18 decks, none a starter.

## docs/cards/shelved-cards.md

- docs/cards/shelved-cards.md:78: "Cards outside the seven starter decks" / 18 decks, none a starter.
- docs/cards/shelved-cards.md:80: the bench via `"deck": "bench"`, "Now: Eagle, Viper, Anaconda" / `cards.json` has no `deck` field (it uses `status`). Eagle is in Heavyweights, Viper in Birds & Snakes, Anaconda in Hunters.
- docs/cards/shelved-cards.md:81: reserve is `"deck": "reserve"`, moved "by changing its deck" / it is `status` in `cards.json`.
- docs/cards/shelved-cards.md:82: Food OTK cuts "exist only as JSON in this file" / Opossum, Gazelle and Impala are collectible with other texts; Black Widow is planned.
- docs/cards/shelved-cards.md:90: reserve table (eon_food_engine, unnamed_giant, shuck, arctic_fox, unnamed_canine) / none of these ids is in `cards.json`.
- docs/cards/shelved-cards.md:118: "one above Armadillo, which trades a point for its Stealth aura" / Armadillo is 5, "Armor. Your adjacent animals have Armor."
- docs/cards/shelved-cards.md:132: handlers `_carmilla_place`, `_black_widow_place`, `_gazelle_remove`, `_impala_remove`, `_pufferfish_covered` "remain in effects.py" / none is in `engine/effects.py`.
- docs/cards/shelved-cards.md:152: re-home by changing `deck` and "add it to DECK_SLUGS" / `DECK_SLUGS` is derived from `decklists.json` (engine/cards.py); cards use `status`.

## docs/cards/ideas.md

- docs/cards/ideas.md:12: Duck, Frog, Pond Skater, Dragonfly, Leech "in the reserve since 2026-10-28" / those five are `planned`, not reserve.
- docs/cards/ideas.md:17: Coyote listed as a waiting Desert animal / a Coyote ships (collectible rare, Forest); a Desert Coyote (`outrider`) is in the reserve.
- docs/cards/ideas.md:19: "Woolly Mammoth (Yuka, in the reserve since 2026-09-29)" / no Yuka or Mammoth in `cards.json`.
- docs/cards/ideas.md:21: Bison under "the prairie, no habitat yet" / Bison ships (collectible rare, Forest).
- docs/cards/ideas.md:27: Wolverine "without a card yet" / Wolverine is a collectible common, Forest.

## docs/cards/to-look-at.md

- docs/cards/to-look-at.md:5: Skunk "(Aggro, ...)" / no Aggro deck (Den Rush). New text: "return an adjacent enemy to its owner's hand. It can't be played next turn."
- docs/cards/to-look-at.md:6: "Sirocco (Aggro, legendary, 5)" / now Rue (`skunk_legend`), in Den Rush.
- docs/cards/to-look-at.md:7: Dhole "Whenever another Canine you control enters play, give it +2 strength" / now "Roam. Whenever this covers an enemy with no other enemy next to it, draw 2 cards."
- docs/cards/to-look-at.md:9: "Barley (Food Aggro, ...)" / now `[RAT]` (`rat_legend`), in the deck named Rodents.
- docs/cards/to-look-at.md:11: Tarantula "Dawn: remove a random adjacent ally and gain its strength" / now "Dusk: remove the weakest animal next to this and gain its strength."
- docs/cards/to-look-at.md:15: "the legendary Octopus copy effect" / that copy card is Iris (`chameleon_legend`); `octopus_legend_2` is `[OCTOPUS]`, a Scout.

## docs/cards/legends/rat.md

- docs/cards/legends/rat.md:5: "Deck: Food Aggro" / the deck is named Rodents (slug `food_aggro`).

## docs/design/how-the-game-works.md

- docs/design/how-the-game-works.md:14: Lemming, "three bodies in one action" / Lemming is reserve, a vanilla 1.
- docs/design/how-the-game-works.md:17: Ocelot as the "if your hand is empty" condition / Ocelot: "if you control another Cat, play another Cat."
- docs/design/how-the-game-works.md:24: "the Boa 'wherever this is'" / no Boa card (Python is the live grower).
- docs/design/how-the-game-works.md:61: "the Eagle (5, Flight)" / Eagle is a rare 6, "Flight. Apex Predator."; the plain 5 flier is the Pigeon.
- docs/design/how-the-game-works.md:81: "Vesper lands on whoever covers a Queen" / Vesper triggers when an enemy covers a Colony ally.
- docs/design/how-the-game-works.md:92: "the Ocelot's empty-hand draw" / the Ocelot has no draw.
- docs/design/how-the-game-works.md:104: Lemming "strong at strength 1" / reserve and vanilla.
- docs/design/how-the-game-works.md:105: "Serval at 3" / Serval is 2.
- docs/design/how-the-game-works.md:111: "The Capybara at 2 with +7 under the small-deck condition" / the Capybara becomes 8 (+6).
- docs/design/how-the-game-works.md:113: Vesper "onto whoever covers a Queen" / any Colony ally.

## docs/design/principles.md

- docs/design/principles.md:19: "The Rat ... its random discard" / the Rat has no discard.
- docs/design/principles.md:31: "the Eagle (5, Flight) for bodies" / Eagle is a rare 6 with Apex; the Pigeon is the common 5 flier.

## docs/design/families.md

- docs/design/families.md:18: Lizards as "a handful of individually unique cards (the Basilisk..., the Gecko...)" / no card has the Lizard tag; Basilisk and Gecko are planned with no values.
- docs/design/families.md:29: "The launch deck is Fish Token Aggro (decklists.json)" / no deck of that name (slug `fish`, named "Fish"), and no deck is a starter.
- docs/design/families.md:40: Canines status "redesign" / done: the Roaming Pack list (2026-10-28).
- docs/design/families.md:46: Circle of Life status "new" / the deck exists (`aristocrats`).
- docs/design/families.md:47: the hand deck status "new" / exists: `handlock`, "Primates".
- docs/design/families.md:48: Giants status "redesign" / (unsure) the Giants list carries its 2026-10-27 cards.
- docs/design/families.md:49: Hoofed status "new" / the deck exists (`hoofed`).

## docs/design/naming.md

- docs/design/naming.md:13: "Greywhisker is an old grey rat" as a card example / no card named Greywhisker (rat legendaries are `[RAT]` and Pestis).

## docs/design/log_habitats.md

- docs/design/log_habitats.md:8: "(the card itself not moved yet)" / the Black Swan has habitat River and Lake, status reserve.

## docs/design/societies/herds.md

- docs/design/societies/herds.md:3: "a hippo carries Hoofed" / the Hippopotamus has no tags.
- docs/design/societies/herds.md:157: Hoofed cards not of the herd: "the moose, the rhino and the hippo" / only the Moose is Hoofed; Rhinoceros and Hippopotamus have no tags.

## docs/design/societies/hive.md

- docs/design/societies/hive.md:32: "every card but the Hornet carries a colony-shaped condition" / Worker Bee ("gain 12 food"), Worker Ant, Lord Bumbleton and Queen Solenia (food per animal) have no Colony condition.

## Total

175 stale claims across 27 files.
