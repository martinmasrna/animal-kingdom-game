# Effects pass

Each launch animal's card, settled habitat by habitat with Martin. Existing cards keep their effect unless noted. Strengths of existing cards wait for the strength-realism pass; numbers marked ~ are first guesses.

Keywords proposed in this pass: **Hungry N** (at the start of your turn, eat N food; if you can't, this gets −N strength), **Flee** (when an enemy covers this, return it to your hand), **Reach N**, **Poison**, **Dawn** and **Dusk** (all in [`../rules/keywords.md`](../rules/keywords.md); card text in this doc still spells out "at the start/end of your turn" until the cards are rewritten), and grazing as a condition (an animal grazes while it's a corner of a region you control; card wording still to choose between "if this is grazing" and "if this controls a region").

## Savanna

Locked:

| Animal | Rarity | Str | Effect | Note |
|---|---|---:|---|---|
| Elephant | C | 9 | Hungry 5. | the vanilla giant; the bigger, the hungrier ~ |
| Ostrich | C | 4 | Roar: place an Ostrich Egg (0, no effect) on an adjacent empty crossroad. | the biggest egg |
| Giraffe | C | 5 | During your opponent's turn, this has +4 strength. | its kick |
| Wildebeest | C | 5 | At the end of your turn, if this is grazing, gain 5 food. | wording to follow the grazing decision |
| Gazelle | C | 3 | Flee. Roar: gain 5 food. | numbers to tune |
| Warthog | C | 4 | While this is next to your den, it has +4 strength. | the den guard |
| Baboon | C | 4 | Roar: give an animal in your hand +2 strength. | Primates train |
| Dung Beetle | C | 1 | At the end of your turn, gain 2 food for each of your animals of strength 8 or more. | lives off the giants |
| Honey Badger | R | 3 | Roar: remove an adjacent enemy of strength 6 or more. | the Big Game Hunter |
| Serval | R | 4 | Roar: set an adjacent enemy's strength to 1. | the Cats' answer to big animals: pin the prey, the pride covers it; at 4 it covers a 3 and pins in one placement, which keeps the Leech's swap from dominating it |
| Rhinoceros | R | 8 | Hungry 3. Roar: remove all adjacent enemies of strength 2 or less. | a Giant ~ |
| Hippopotamus | R | 8 | Hungry 3. When an enemy of strength 3 or less is placed next to this, remove it. | a Giant; the reaction stays (the client is to show what removed an animal) ~ |
| Cape Buffalo | R | 6 | While grazing, this has +3 strength. | stands its ground on its own land |
| Crocodile | R | 8 | Apex Predator. | the ambush at the river crossing; art: the huge Nile crocodile, not the Jaguar's caiman |
| Meerkat | C | 2 | Roar: draw a card. When an enemy is placed next to this, draw a card. | the sentry |

Open: Aardvark, the legendaries; Warthog moves to rare (the herd's den guard), which shifts Savanna's split to rebalance later.

## The herd (Hoofed grazing), draft

Designed as one archetype across the habitats, not card by card (Martin, 2026-10-05). The plan: take a region early and hold it, put grazers on its corners, win on food; the opponent breaks the region. An animal, yours or the opponent's, is grazing while it's a corner of a region its owner controls. Grazing checks stay out of Roars, since region control is checked after a Roar resolves.

- Commons (a deck runs six of these): Gazelle, Giraffe, Wildebeest (as locked above); Zebra, "Flee. While grazing, this has Stealth."; Deer (Forest), "Flee. At the end of your turn, if this is grazing, draw a card."; Cape Buffalo (as locked); Moose (Forest), "Your other grazing animals have +2 strength."; Boar (Forest), "Roar: remove an adjacent enemy that is grazing."
- Rares: Warthog (as locked), Rhinoceros, Hippopotamus (shared with the Giants), Beaver (Forest, R, 4), "Your regions next to this produce 5 more food." (beaver ponds make the land around them richer; a local version of the migration legendary).
- Legendaries: the migration's wildebeest, "Your regions produce 5 more food."; the white stag, "Flee. Roar: draw a card for each region you control."; two open. Rejected: "when an enemy covers one of your grazing animals, remove that enemy" (every corner uncoverable, so the region can't be broken).

Zebra, Deer, Moose, Boar and the two legendaries are proposals.

## The food decks

Food is the win counter itself, so a deck whose cards each gain about 10 food is a clock, not a combo: there is nothing to assemble. The food cards split into two decks:

- **Rodent food aggro:** the Rodents (Barley, Scrooge, Squirrel, Flying Squirrel, Chipmunk, Hamster, Muskrat, Groundhog, Hedgehog) and about four finishers and speed cards still to design. Scrooge's one-turn burst belongs here.
- **The hoard (true combo):** draw, assemble, stall, execute. Its food sources are slow, so the fair route is too slow and the payoff is the plan. It holds the stall pieces (Porcupine, Armadillo, Octopus, Fathom), Black Bear for slow draw, and the defensive cards below. It loses to food aggro by design: food from Roars can't be touched.

The payoff, a legendary squirrel (name to come): "Roar: lose all your food. In 2 turns, gain twice that much." No Armor and a modest body: the deck has to protect it, and covering pauses its timer. Removing it loses the whole stake; that risk is the point. Doubling only the food put at risk keeps it from being a win button. Fathom ("Roar: Scout a legendary animal") is its tutor.

The defensive cards, one answer for each way to reach the squirrel (removal, a ground cover, a cover from behind the lines). A defensive card must be beaten by no existing card and must leave the opponent an ordinary answer (a cover with more strength, or a removal ability); an animal that can never be covered is an unbreakable wall. "When this is removed" text on a small body never fires (opponents cover small animals instead), and 0-strength tokens block nothing (anything covers a 0).

| Animal | Habitat | Rarity | Str | Text | The opponent's answer |
|---|---|---|---:|---|---|
| Poison Dart Frog (locked) | Jungle | C | 1 | Reach 2. Poison. | a removal ability |
| Jellyfish (locked) | Open Ocean | R | 3 | Poison. | a removal ability |
| Golden Orb-Weaver (locked; Arachnid) | Jungle | R | 3 | When an enemy with Flight is placed next to this, remove it. | cover it (a flyer needs 4+); ground animals ignore the web |
| Capybara | Jungle | R | 5 | Your animals next to this have Armor. | cover its neighbours, cover it (6+), or remove it |

Open: a Capybara beside a Porcupine is the strongest wall these build (unremovable, kills its first coverer, broken by a second cover of 8+).

## The aristocrats, draft

Your own animals die on purpose and every death pays. What makes it worth playing: the opponent's interaction feeds it (their covers are your deaths), each turn is a puzzle (how many deaths and payoffs out of two actions), and it wins from behind, on food the opponent can't block, while they seem to hold the board.

How it's built:

- Every piece of fodder pays on its own death; the payoffs multiply that.
- Food scales with the turn's deaths (the Hyena), since food is the win clock; cards don't (the Vulture checks once a turn), since per-death draws would turn the loops into five cards from one action.
- Payoffs count deaths as they happen, not the Remove Pile, since the best fodder leaves the pile (the Cockroach to hand, the Ember to deck).
- Each loop costs a placement, so two actions a turn bound it; any "play another animal" effect needs an audit against these loops.

| Card | Role | Habitat | Rarity | Str | Text |
|---|---|---|---|---:|---|
| Ember (exists) | fodder | Forest | L | 7 | Flight. When this is removed, shuffle it into your deck. |
| the playing-dead opossum (legendary, name to come) | engine | City | L | 3 | When one of your animals is covered, remove it and draw a card. (Covers by either player: your own cover onto your fodder is a death and a card, so every placement runs the engine, and every enemy cover feeds you. The answer: cover or remove it, a 3.) |
| the great sloth (legendary, name to come) | payoff | Jungle | L | 4 | Your Dusk effects happen twice. (The sloth sleeps fifteen hours a day. Doubles the Hyena's food and the Vulture's card; bounded, since each Dusk effect fires once a turn. Not tied to this deck: watch it if every Dusk deck runs it.) |
| the cuckoo chick (legendary, name to come; no Flight) | engine | Meadow | L | 6 | Roar: remove an adjacent animal of strength 4 or less. If it was yours, play another animal. (The chick shoves the host's eggs out of the nest and takes their place; a nestling can't fly, and with Flight this would be removal anywhere. The art must show the chick in a host's nest. Vilgefortz's shape, for many decks: on an enemy, small removal; on your own spent small animal, a free placement; here also a death. Not a den burst: removing your own animal from the chain cuts the legendary off.) |
| Tarantula (Arachnid) | engine and body | Jungle | R | 5 | Dusk: remove a random one of your animals next to this. This gains its strength. (A death every turn with no decision at the end of the turn; you steer the randomness by what you place next to it. The deck's one growing body; strength has no ceiling, so past 10 nothing can cover it and only a removal ability answers it, as with the Python.) |
| Praying Mantis | engine | Meadow | R | 3 | Roar: remove one of your animals next to this. If you do, draw 2 cards. |
| Raccoon | recursion | City | R | 2 | Roar: return one of your removed animals to your hand. (Your own only: the Remove Pile is shared.) |
| Sea Turtle | body and fodder | Open Ocean | R | 7 | Dusk: place a Baby Turtle (0, no effect) on an adjacent empty crossroad. (Baby turtles hatch at night and race to the sea; most are eaten. A real body, and free fodder every turn with no card or action spent: next to a Spider the Baby Turtle dies as it lands. A free body each turn is action economy, so it needs the den audit: a turtle one crossroad from the opponent's den front sets up a capture.) |
| City Spider (Arachnid) | engine | City | C | 2 | When an animal of strength 2 or less is placed next to this, remove it. (Both sides: a trap for the opponent's small animals and tokens, a repeatable death for yours.) |
| Cockroach | fodder | City | C | 1 | When this is removed, return it to your hand and draw a card. |
| Earthworm | fodder | Meadow | C | 1 | When this is removed, place two Worms on its crossroad. (Worm, token, 0: "When this is removed, draw a card.") |
| the blood-scenting removal (animal open; Great White Shark proposed, as a rare ~6) | removal | | | | Roar: if one of your animals was removed this turn, remove an adjacent enemy. (Smells blood: the deck's way to fight for the board. The Piranha that carried it moved to the Fish.) |
| Vulture (locked; Bird) | payoff: cards | Savanna | C | 3 | Flight. At the end of your turn, if one of your animals was removed this turn, draw a card. |
| Hyena (no tag) | finisher | Savanna | C | 4 | Dusk: gain 3 food for each of your animals removed this turn. (The laughing scavenger: deaths into food. It scales with the turn's deaths, so a big turn pays big: that's the deck's puzzle, how many deaths out of two actions. Copies stack, and the Sloth doubles it; if games end too fast or too slow, the dial is the 3.) |

Expected weak points, untested: few cards that kill your own (Spiders die to any cover), and few bodies bigger than a 4. The Tarantula is aimed at both.

## Canines

The pack that roams the board, buffs itself on the board (Primates buff in hand) and hunts by position. High skill: each turn is a puzzle of moves and placements across two actions. Built on Roam ([`../rules/keywords.md`](../rules/keywords.md)), a game-wide keyword that Canines carry most. Count-based effects (stronger the more of them) belong to the Fish. Scarlett stays in the pool, outside this precon.

| Card | Habitat | Rarity | Str | Text |
|---|---|---|---:|---|
| legendary Leopard (name to come; Cat) | Savanna | L | 7 | Apex Predator. Roam. Reach 2. (Drops onto its prey from a tree, then waits: landing by Reach leaves it unconnected, so it roams again once the chain reaches it.) |
| Clarion | Forest | L | 5 | Once each turn, one of your Canines can roam for free. (The deck is short of actions, not cards.) |
| Lobo | Forest | L | 6 | Whenever one of your animals roams onto an enemy, draw a card. (The wolf king feeds the pack; bounded by one roam per animal per turn.) |
| legendary wolf (name to come) | Forest | L | 4 | Roam. When this roams, your animals next to it gain +2 strength. |
| Orca | Open Ocean | R | 7 | Apex Predator. Roam. (The wolf of the sea; it eats with every roam, so its strength is the dial.) |
| African Wild Dog | Savanna | R | 4 | Roam. Whenever this covers an enemy, draw a card. (The most successful hunter. Rare, not common: three copies would keep one on the board in every game against decks of small animals.) |
| Jackal | Savanna | R | 4 | Roar: remove an adjacent enemy that has another of your Canines next to it. |
| Dhole | Jungle | R | ~6 | Roam. Your animals can roam onto enemies of equal strength. (Dhole packs take prey bigger than themselves.) |
| Wolf | Forest | C | 6 | Roam. (The plain hunter, one below the Lion.) |
| Bush Dog | Jungle | C | 3 | Roar: give an adjacent Canine +3 strength. |
| Raccoon Dog | Forest | C | 3 | Whenever one of your Canines roams, give it +1 strength. |
| Fox | Forest | C | 3 | Dusk: give your adjacent animals +1 strength. |
| Badger | Forest | C | 4 | Roar: draw an animal with Roam. (It digs the prey out for the runners, as badgers do for coyotes.) |
| Stray Dog | City | C | 1 | Roar: give one of your animals with Roam +2 strength. It roams. |

Open: the Dhole's strength (~6); a slot for the Raccoon Dog on the Forest roster. "Your animals next to this have Roam" waits for a legendary in a deck without roamers of its own.

## Fish Token Aggro, draft

The swarm (Martin, 2026-10-08). Gwent's Arachas, Hearthstone's Murlocs: one card becomes a school, and every Fish makes the others better. The opponent should feel outnumbered, not outmuscled: each fish is small, but covering them one by one costs a card and an action each. A 2×2 square of Fish is a region, so the packed school wins on food. It preys on slow decks and on decks that answer one threat at a time; area removal (Rhinoceros, Hippopotamus, City Spider, Brutus) is its predator, which puts Giants on top of it.

How a game goes (agreed with Martin, 2026-10-08): the deck's resource is the empty board, which is full by turn 4 or 5. Turns 1–3 flood it and close regions (two regions, 25 food a turn, reach 100 around turn 6 or 7). Turns 4–6 hold them: the count cards are big by then, and removal clears the coverers off your corners; late Fish land on your own Fish (always legal), firing their Roars and leaving a backup beneath. If the opponent wins the board war by turn 6, Fish loses, on purpose (Hearthstone's Token Paladin): the cards that fill empty crossroads are dead topdecks late, the price of the best opening in the game. Its meta role: it punishes greed in the opening (Handlock, Food OTK, Giants). Food Aggro races off the board, Hoofed holds one region slowly with big animals; Fish takes many regions, fast and fragile. One buff card at most, or it's the old Canines again.

Payoffs count every Fish you control: a plain count keeps the swarm feeling, and a smooth count (each Fish a bit more) plays differently from Colony's thresholds. Adjacency cards stay wherever they make sense; on map_b a crossroad has at most 4 neighbours, so "for each adjacent Fish" pays about 1, at best 2.

Legendaries are drawn at a random point, often after the board is full, so each must work then; the opening is the commons' job (three copies each).

The list (Martin, 2026-10-08; animals and strengths set, wording to the card-text conventions):

| Card | Habitat | Rarity | Str | Text |
|---|---|---|---:|---|
| a Jellyfish (no Fish tag; name to come) | Open Ocean | L | 6 | Your Fish next to this have **Poison**. (Young fish shelter among jellyfish tentacles. "Your other Fish have Poison" would make every corner uncoverable: the herd's rejected card again.) |
| a Bluefin Tuna (name to come) | Open Ocean | L | 5 | Roar: for each region you control, draw a card and gain 5 food. (The closer and the late reload; the most expensive fish ever sold. The herd's white stag, "draw a card for each region you control", needs another effect.) |
| a Manta Ray (name to come) | Open Ocean | L | 4 | **Dusk:** if you control 2 or more regions, draw a card. |
| a Piranha (name to come) | Jungle | L | 7 | Your Fish can be placed on enemies of strength up to the number of Fish you control. (The school strips something far bigger: once the board is full, it lets the small Fish win crossroads back. Snow Leopard's shape.) |
| Swordfish | Open Ocean | R | 3 | Roar: remove a random adjacent enemy for each of your Fish next to this. |
| Piranha | Jungle | R | 4 | Roar: remove an adjacent enemy of strength up to the number of your Fish. |
| Manta Ray | Open Ocean | R | 6 | Whenever your opponent covers one of your Fish, draw a card. |
| Remora | Open Ocean | R | 3 | Roar: play another Fish. (It arrives riding a bigger fish.) |
| Tuna | Open Ocean | C | 4 | Roar: draw a card for each of your Fish next to this. |
| Sardine | Open Ocean | C | 1 | Roar: place all Sardines from your hand and deck on random adjacent empty crossroads. (Lemming's effect, fine in play.) |
| Mahi-mahi | Open Ocean | C | 3 | Roar: give your other Fish +1 strength. |
| Mackerel | Open Ocean | C | 2 | Your other Fish have +1 strength. |
| Barracuda | Open Ocean | C | 3 | Has +1 strength for each other Fish you control. |
| Sunfish | Open Ocean | C | 4 | Roar: place a Baby Fish (token, Fish, 0) on an empty crossroad next to this. (It lays more eggs than any other animal.) |

Sharks stay out of the count cards: they're lone hunters. Fish's predator is weak on this map (area removal reaches only the edge of a school built at home); Giants need a way to hit the middle of a school. Open Ocean's roster gains Sardine, Tuna, Remora, Mahi-mahi and Mackerel, to settle in the roster pass after the decks. Rejected: Baby Fish spawners at legendary and rare (empty crossroads exist only in the first turns), a food common (Food Aggro's ground), Goldfish (a pet), Salmon (a river fish, for River and Lake).

## Egg Control

Its fourth legendary: Omen (a raven; Forest, L, ~3, Bird): "Flight. Roar: put an animal from your opponent's Remove Pile into your hand." The deck removes more than any other, so the opponent's pile holds their best cards; a Bird, so the Bird Egg's Scout can find it. Wording to bring in line on the deck's cards: Eon's end-of-turn shuffle is a Dusk effect, Aurum is "Dawn: draw a card.", the Python counts removed animals (not units), and the Egg Eater counts removed Eggs.

## Open topics

- The bloodsuckers drain strength: Mosquito's −2, Leech's swap, the Tick's effect still to design, likely a slow drain.
- Taking the opponent's food belongs to thieves (Seagull later, the monkeys) and gets its own session.

## Elsewhere, settled in passing

- Cats: Caracal (Savanna, C, 6), "Reach 2.", the leap over the front line onto the engines behind it, which every other Cat can only hit when adjacent (at 5 or less the Eagle practically dominates it); Lynx (Forest, C, 6), "Roar: if placed on top of an enemy, draw a card."; Bobcat (Forest, C, 5), "Roar: if you control another Cat, draw a card." The Cougar and its effect wait for Mountains.
- Cuckoo (Meadow, R, ~3, Bird): "Flight. Roar: shuffle two Cuckoo Eggs into your opponent's deck." Cuckoo Egg (token, 0): "When you draw this, your opponent draws a card." The opponent's deck is the host's nest: each Egg clogs their deck, then their hand. It stays in the hand of whoever drew it and is theirs to play (a 0-strength animal); with no way to discard, getting rid of it costs one of their actions. A disruption card, hardest on the decks that draw a lot.
- Mosquito (City, C, ~1): "Flight. Roar: give an adjacent enemy −2 strength."
- Leech (Jungle, 1): "Roar: swap strength with an adjacent animal." It drains its host: the host shrinks, the leech swells. At 1 it can't cover anything, so it lands only on an empty crossroad or one of your own.
- Opossum (City, R, 2, Marsupial): "Roar: return one of your animals next to this to your hand." A mother gathering her young onto her back; it replays an animal's Roar (Skully, Chipmunk, a removal), a value card for other decks, and the City's seed for the Marsupials' "carrying the young" identity when Australia comes.
- Clownfish (Coral Reef, later): its "play another Fish" went to the Remora; Coral Reef gives it its own trait (safe in a stinging anemone). Electric Eel (Jungle) is the stun.
- Hermit Crab (Coast, later): Armor plus something about moving into another's shell.
