# Card wording audit (2026-11-05)

Every collectible card's text (204, from `load_cards()`), checked against the card-text conventions at the end of `docs/rules/keywords.md`, the keyword lines, `docs/rules/rulings.md`, `animal_kingdom/tests/test_card_text_wording.py`, the engine (where the audits in this folder found the text and the engine apart, and a handful of handlers read directly), and each other. No card, keyword or rule was edited.

28 cards need a change. Each appears once below, under its main problem; the reason names any other problem it has. Format: `id: current / proposed / why`.

Proposals that make a text longer have not been measured: run `web/test/cardtext.test.mjs` (the three-line limit) before applying them. A proposal that turns a word into a digit may need a line in `test_card_text_consistency.py`, which checks printed numbers against `engine/config.py`.

## The text doesn't say what the engine does

- worker_wasp: "Flight. Whenever you place a Colony animal, gain 3 food." / "Flight. Whenever you place another Colony animal, gain 3 food." / The engine pays only for Colony animals placed after the Wasp (forest audit, reading B). The Worker Ant and the Falcon legend count themselves, so without "another" a player reads it the other way.
- wolf_legend_2: "Roam. Whenever a Canine roams, give it +1 strength and draw a card." / "Roam. Whenever an allied Canine roams, give it +1 strength and draw a card." / The engine counts only your own Canines (forest audit, reading B; rulings.md). "A Canine" includes the opponent's.
- wolf_legend_3: "Once each turn, an ally can roam for free." / "Once each turn, an ally with Roam can roam for free." / The engine gives the free roam only to an ally that has Roam (forest audit, reading B; rulings.md, Clarion). The Street Dog already says "a connected ally with Roam".
- vole: "Roar: repeat the Roar of an adjacent Rodent." / "Roar: repeat the Roar of an adjacent allied Rodent." / The engine repeats only your own Rodent (meadow audit, reading B; rulings.md, Vole). The meadow audit suggests the same words.
- oxpecker_legend: "Flight. Whenever your animal of strength 8 or more covers an enemy, play an Oxpecker." / "Flight. Whenever an ally of strength 8 or more covers an enemy, play a new Oxpecker." / The engine makes an Oxpecker out of nothing (savanna audit, reading B). "Play" means from your hand (keywords.md), and the Oxpecker is a collectible card that can be in hand, unlike the Bunny or the Baby Impala. "Your animal" for one animal is "an ally" by the convention. If Martin rules for reading A, the text keeps "play an Oxpecker" and the engine changes.
- cockroach: "Fall: replace this with a Cockroach and place a Roach on an adjacent empty crossroad." / "Fall: replace this with a Cockroach and place a Roach on a random adjacent empty crossroad." / The engine picks the crossroad at random; the Deer, the Sunfish and Scarlett print "random". Still open (city and rulings audits): the engine puts the same card back and nothing reaches the Remove Pile, while "replace this with a Cockroach" reads as a removal and a fresh card. If that engine reading stands, Roach King's words fit it better: "put this back where it was".
- queen_ant: "Dusk: place a Young Ant on an adjacent empty crossroad." / "Dusk: place a Young Ant on a random adjacent empty crossroad." / The engine and rulings.md pick at random (Dusk asks no decision). The Deer and the Sunfish print "random".
- vulture: "Flight. Dusk: if 3 or more animals were removed this turn, fly in from your hand or deck." / "Flight. Dusk: if 3 or more animals were removed this turn, place this on a random empty crossroad from your hand or deck." / The engine places each Vulture in your hand and deck on a random empty crossroad anywhere, with no Roar. "Fly in" says neither where it lands nor that it is placed, not played. It is the longest proposal here; measure it first.
- eagle_legend: "Flight. Apex Predator. When this enters your hand, add [NAME] to your hand." / "Flight. Apex Predator. When this enters your hand, add [EAGLE'S MATE] to your hand." / "[NAME]" matches no card. The mate token (`eagle_legend_2`) is shown as "[EAGLE'S MATE]", and the other unnamed legendaries print their own bracket name ("[SARDINE] and your adjacent Fish…").
- hornet_legend: "Flight. When an enemy covers a Colony ally, place Vesper on top of it from your hand or deck." / "Flight. When an enemy covers an allied Colony animal, place Vesper on top of it from your hand or deck." / The convention's form for one of your animals of a kind is "an allied Cat"; "a Colony ally" appears on no other card. Not fixable in the text: the engine resolves Vesper before a Soldier Bee's Spikes, so Vesper can end up on its own Bee (rulings audit, two readings).
- dung_beetle_legend: "Evolves at 10 food eaten by your Hungry animals." / "Evolves once your Hungry animals have eaten 10 food this game." / The engine counts the food eaten over the whole game (`dung_beetle_legend_draw_at`), whether this card is in hand or on the board; "at 10 food eaten" doesn't say since when. Its forms say it two ways ("eaten by your Hungry animals", "your Hungry animals ate"); they are tokens, outside these 204, and should match whatever this one says.

## "An ally" versus "your"

- deer_legend: "Flee. Roar: draw 2 animals with Flee. Whenever one of your animals flees, give it +2 strength." / "Flee. Roar: draw 2 animals with Flee. Whenever an ally flees, give it +2 strength." / One of your animals is "an ally" by the convention, and it is shorter. The Deer itself is included either way (rulings.md).

## Numbers

The convention says only "draw a card" and "draw 2 cards"; every other count on the cards is a digit except these.

- earthworm: "Fall: draw a card and place two Worms on its crossroad." / "Fall: draw a card and place 2 Worms on its crossroad." / Digits elsewhere ("add 2 Kittens", "draw 2 Snakes").
- cuckoo: "Flight. Roar: shuffle two Cuckoo Eggs into your opponent's deck." / "Flight. Roar: shuffle 2 Cuckoo Eggs into your opponent's deck." / As above; the Raven prints "shuffle 2 cards back".
- stork: "Flight. Roar: add two random younglings to your hand." / "Flight. Roar: add 2 different random younglings to your hand." / Digit as above. The engine never gives the same youngling twice (`rng.sample`; rulings.md: "two different younglings"); the text doesn't say so.
- krill: "Roar: draw a card. The next Titan you play this turn costs one action." / "Roar: draw a card. The next Titan you play this turn costs 1 action." / The Electric Eel prints "1 action", the Beaver "1 additional action".
- squirrel_legend: "Roar: lose all your food. In 2 turns, gain three times as much." / "Roar: lose all your food. In 2 turns, gain 3 times as much." / The only number in words that is a multiplier; digits on every other card. Depends on the convention line asked for below.

## Two cards say the same thing in different words

- dart_frog: "Reach. Poison. Fall: remove all animals next to this." / "Reach. Poison. Fall: remove all adjacent animals." / The Sperm Whale says the same thing as "remove all adjacent animals". Bare "adjacent" means adjacent to this (convention), and it is shorter.
- city_spider: "Dawn: remove the weakest animal next to this." / "Dawn: remove the weakest adjacent animal." / The Sperm Whale legend says "the strongest adjacent enemy". Shorter.
- tarantula: "Dusk: remove the weakest animal next to this and gain its strength." / "Dusk: remove the weakest adjacent animal and gain its strength." / As the City Spider.
- skunk_legend: "Roar: return all adjacent enemies to your opponent's hand." / "Roar: return each adjacent enemy to its owner's hand." / The Skunk and the Zebra say "to its owner's hand". An enemy can be a Wild Locust, which is not the opponent's.
- raven_legend: "Flight. Roar: put 2 animals from your opponent's Remove Pile into your hand." / "Flight. Roar: add 2 animals from your opponent's Remove Pile to your hand." / "Add … to your hand" is the phrase on the Alley Cat, Queen Bee, Stork, Sea Turtle, [FAWN] and Iris; "put … into your hand" appears only here.
- barracuda: "Roar: remove an adjacent enemy with strength up to the number of your Fish." / "Roar: remove an adjacent enemy of strength up to the number of your Fish." / The Piranha says "of strength up to the number of your Fish", and the convention reads "of strength 4 or less".
- bee_legend_2: "Roar: if your starting deck has no animals of strength 4 or more, give your animals +2 strength (wherever they are)." / "Roar: if your starting deck has no animal of strength 4 or more, give your animals +2 strength (wherever they are)." / The Capybara's condition is the same in the singular.
- lynx: "Roar: if you place this on top of an enemy, draw 2 cards." / "Roar: if this covers an enemy, draw 2 cards." / "Covers an enemy" is the phrase on the Dhole, King Theron, the Oxpecker legend and the Zebra; "place this on top of" appears only here, and "place" is the word for an effect's placement, which never fires a Roar (rulings.md). Shorter.
- bumblebee_legend: "Flight. Whenever you gain food, gain 3 additional food." / "Flight. Whenever you gain food, gain 3 more food." / The Chipmunk says "gain 10 more". Shorter.
- beaver: "Roar: next turn, take 1 additional action." / "Roar: next turn, take 1 more action." / As the Bumblebee legend.

## A shorter sentence says the same

- chameleon_legend: "Roar: choose an adjacent animal. Become a copy of it, and add another copy to your hand." / "Roar: become a copy of an adjacent animal and add another copy to your hand." / No other card prints "choose": a target is chosen by default ("remove an adjacent enemy"). One sentence; Stealth still keeps an enemy out, as for any chosen target.

## Checked, no text change

- bush_dog: the text ("place a Pup on the crossroad it left") matches the engine, which places the Pup even on an animal that resurfaced there. The ruling that says "only if the crossroad is empty" is what disagrees (rulings audit).
- woodpecker: the engine was fixed to match the text (forest audit).
- cockroach_legend: "with +1 strength" fits both readings of what a fall keeps (rulings audit); the text can't settle it. It uses its own name; see "Self-reference" below.
- locust_legend: which Locusts a Hippopotamus takes depends on the order the engine lands them (keywords audit); no wording fixes that.
- sloth, snake_egg, black_bear, squirrel_legend ("In 2 turns") and sperm_whale_legend ("the strongest adjacent enemy"): the engine is consistent with the text once the conventions say how a timer counts and what "the strongest" picks from (below).

## The conventions

Where the conventions are silent or contradict the cards, each with what the cards do now and a proposed line.

**Contradicted**

- Timed triggers. The bullet still says recurring triggers read "At the end of your turn, …" and "At the start of your next turn, …", while the Dawn and Dusk entry says those two words replace them, and every recurring trigger on the cards is Dawn or Dusk. The long form survives only for a one-time delay (the Chipmunk's "At the start of your next turn, gain 10 more."). Proposed: "Recurring timed effects are **Dawn** and **Dusk**. A one-time delay reads "At the start of your next turn, …", "In 2 turns, …", or "Next turn, …" where the long form doesn't fit."
- "Play means from your hand." The Rabbit ("play a Bunny"), the Impala ("play a Baby Impala") and the Oxpecker legend make a new card and play it; none of them is in your hand. Proposed: "Play means from your hand; "play a" with a token's name makes that token and plays it." The Oxpecker legend still needs its own change (above), because the Oxpecker is not a token.
- What "remove" means. The Discard entry says "removed" on a card means an animal leaving the board; the Fall entry says a card sent to the Remove Pile from hand or deck is a remove too, and rulings.md still calls leaving the board "Deathrattle". On today's cards every "remove" is an animal leaving the board, so the Discard wording fits the cards. Proposed, in the conventions: "**Remove** on a card means an animal leaves the board for the Remove Pile; a card leaving a hand is a **discard**." Rulings.md's "Deathrattle" would then read "Fall" or "leaving the board".

**Silent**

- Keyword order. Nothing says it. The 11 cards with two or more keywords already agree with one order: Flight, Titan, Hungry, Apex Predator, Armor, Stealth, Roam, Reach, Poison, Spikes, Flee. Proposed: write that order down; no card changes.
- Numbers other than drawn cards. Proposed: "Every count is a digit ("2 Worms", "1 action", "3 times as much"); one card is "a card", one animal "an animal"." This is the convention the Numbers section above applies.
- Whose turns a timer counts. The engine counts the owner's turns for "In 2 turns" (Sloth, Snake Egg, Black Bear, Yuki: two of your turns), and every turn for a Wild animal (the Locust: the opponent's, then yours), which keywords.md states only for Wild. The jungle audit found two readings for the Sloth and the Snake Egg because of this. Proposed: "A timer counts its owner's turns; a Wild animal's counts every turn." "Next turn" means the next turn of the player the sentence names: yours on the Beaver and the Bird Egg, your opponent's on the Electric Eel and the Skunk. Proposed: say so in the same bullet.
- What "the strongest" and "the weakest" pick from. The engine and rulings.md pick among the animals the effect can remove (Armor excluded) for the City Spider, the Tarantula and the Sperm Whale legend; the ocean audit found two readings for the last. Proposed: "An effect that picks "the strongest" or "the weakest" picks among the animals it can act on."
- Whether "an ally" includes this animal. The cards use "other" to leave it out ("your other Fish", "another Cat"), and rulings.md counts it in where "other" is absent (the Deer legend, the Black Wolf). Proposed: "An ally includes this animal unless the text says "other"."
- "Your X" versus "X you control". Both are allowed and the cards mix them for the same job: "each other Fish you control" (Tuna) and "your other Fish" (Mahi-mahi); "each animal you control" (Worker Ant) and "each of your animals with Armor" (Stag Beetle). Likewise "each adjacent allied Fish" (Cod, Swordfish) and "each of your adjacent Rodents" (Big Gus). No card is wrong today. Proposed: "For counts, "for each X you control"; for a group an effect acts on or gives to, "your X"; one adjacent animal of yours, "an adjacent allied X"." This would change about a dozen cards; it is not applied above.
- "When" versus "Whenever". Repeating triggers use both: "Whenever this roams" (Jackal), "Whenever you draw a card" (Hamster), but "When an allied Cat covers an enemy" (King Theron), "When an enemy … is placed next to this" (Hippopotamus, Golden Orb-Weaver, Meerkat), "When this flees" (Zebra). Proposed: "Whenever" for a trigger that can happen again, "When" for one that happens once; that changes those five cards, and none is listed above until Martin picks.
- Self-reference by name. Eon, Ember, Vesper, Roach King and [SARDINE] name themselves; every other card says "this". The convention judges "this" against "it" card by card but says nothing of the name. "This" is shorter on all five; on Vesper ("place Vesper on top of it") the name is clearer.
- "Gain N strength". The convention gives "has +X" (an anthem) and "give +X" (a counter). The Anaconda, Python, Tarantula and the Leopard legend "gain" strength, which the engine treats as a counter on itself. Proposed: "This "gains N strength": a counter on itself, as "give" is."
- "Evolve". The Butterfly legend and the Dung Beetle legend evolve; neither keywords.md nor the conventions say what it is (the card turns into its next form, keeping its counter). Proposed: one line under "Not a keyword".
- "Place". The card-text conventions define "play" but not "place"; rulings.md does ("puts it there outright… It isn't a play"). The Worker Wasp's "whenever you place" deliberately covers both. Proposed: move the one-sentence definition into the conventions.
- The minus sign. The cards print an ASCII hyphen ("-2 strength"); keywords.md writes "−1". Proposed: say which one cards use.
