# Effects pass

Each launch animal's card, settled habitat by habitat with Martin. Existing cards keep their effect unless noted. Strengths of existing cards wait for the strength-realism pass; numbers marked ~ are first guesses.

Keywords proposed in this pass: **Hungry N** (at the start of your turn, eat N food; if you can't, this gets −N strength), **Flee** (when an enemy covers this, return it to your hand), **Reach**, **Poison**, **Dawn** and **Dusk** (all in [`../rules/keywords.md`](../rules/keywords.md); card text in this doc still spells out "at the start/end of your turn" until the cards are rewritten), and grazing as a condition (an animal grazes while it's a corner of a region you control; card wording still to choose between "if this is grazing" and "if this controls a region").

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
| Meerkat | R | 2 | Roar: draw a card. When an enemy is placed next to this, draw a card. | the sentry; a Rodent by what players believe (it's a mongoose); rare for a unique effect (Martin, 2026-10-08), in Food Aggro as the den guard |

Open: Aardvark, the legendaries; Warthog moves to rare (the herd's den guard), which shifts Savanna's split to rebalance later.

## The herd (Hoofed grazing), draft

Designed as one archetype across the habitats, not card by card (Martin, 2026-10-05). The plan: take a region early and hold it, put grazers on its corners, win on food; the opponent breaks the region. An animal, yours or the opponent's, is grazing while it's a corner of a region its owner controls. Grazing checks stay out of Roars, since region control is checked after a Roar resolves.

- Commons (a deck runs six of these): Gazelle, Giraffe, Wildebeest (as locked above); Zebra, "Flee. While grazing, this has Stealth."; Deer (Forest), "Flee. At the end of your turn, if this is grazing, draw a card."; Cape Buffalo (as locked); Moose (Forest), "Your other grazing animals have +2 strength."; Boar (Forest), "Roar: remove an adjacent enemy that is grazing."
- Rares: Warthog (as locked), Rhinoceros, Hippopotamus (shared with the Giants), Beaver (Forest, R, 4), "Your regions next to this produce 5 more food." (beaver ponds make the land around them richer; a local version of the migration legendary).
- Legendaries: the migration's wildebeest, "Your regions produce 5 more food."; the white stag, "Flee. Roar: draw a card for each region you control."; two open. Rejected: "when an enemy covers one of your grazing animals, remove that enemy" (every corner uncoverable, so the region can't be broken).

Zebra, Deer, Moose, Boar and the two legendaries are proposals.

## The food decks

Food is the win counter itself, so a deck whose cards each gain about 10 food is a clock, not a combo: there is nothing to assemble. The food cards split into two decks:

- **Rodent food aggro:** drafted below as Food Aggro. Scrooge's one-turn burst belongs here.
- **The hoard (true combo), drafted below as Food OTK:** draw, assemble, stall, execute. Its food sources are slow, so the fair route is too slow and the payoff is the plan. It holds the stall pieces (Porcupine, Armadillo, Octopus, Fathom), Black Bear for slow draw, and the defensive cards below. It loses to food aggro by design: food from Roars can't be touched.

The payoff, a legendary squirrel (name to come): "Roar: lose all your food. In 2 turns, gain three times that much." No Armor and a modest body: the deck has to protect it, and covering pauses its timer. Removing it loses the whole stake; that risk is the point. Multiplying only the food put at risk keeps it from being a win button at once; the two turns are the opponent's window. Fathom ("Roar: Scout a legendary animal") is its tutor.

The defensive cards, one answer for each way to reach the squirrel (removal, a ground cover, a cover from behind the lines). A defensive card must be beaten by no existing card and must leave the opponent an ordinary answer (a cover with more strength, or a removal ability); an animal that can never be covered is an unbreakable wall. "When this is removed" text on a small body never fires (opponents cover small animals instead), and 0-strength tokens block nothing (anything covers a 0).

| Animal | Habitat | Rarity | Str | Text | The opponent's answer |
|---|---|---|---:|---|---|
| Poison Dart Frog (locked) | Jungle | C | 1 | Reach. Poison. | a removal ability |
| Jellyfish (locked) | Open Ocean | R | 3 | Poison. | a removal ability |
| Golden Orb-Weaver (locked; Arachnid) | Jungle | R | 3 | When an enemy with Flight is placed next to this, remove it. | cover it (a flyer needs 4+); ground animals ignore the web |
| a Honey Badger (name to come) | | L | 5 | **Armor. Stealth. Spikes. Poison.** (Martin's: every keyword on one animal. Spikes takes the first coverer at once, which cancels that cover's Poison; every later coverer is poisoned. One crossroad the opponent never truly takes, not a wall: the region breaks through any other corner.) |
| Capybara | Jungle | R | 5 | Your animals next to this have Armor. | cover its neighbours, cover it (6+), or remove it |

Open: a Capybara beside a Porcupine is the strongest wall these build (unremovable, kills its first coverer, broken by a second cover of 8+).

## Food OTK, draft

The hoard (Martin, 2026-10-08): a fortress around a bomb. Magic's Approach of the Second Sun, Hearthstone's Freeze Mage and Quest decks. The legendary squirrel ("Roar: lose all your food. In 2 turns, gain three times that much.") stakes everything on one animal for two turns; the rest of the deck reaches a stake worth doubling (about 50 food) and builds the walls that make those two turns survivable. The fun is the siege: a visible timer, the opponent throwing everything at the walls, and the puzzle of building an answer for each way their deck can reach the squirrel. It beats midrange and slow interaction (answers one at a time), loses to speed (Food Aggro, Fish, Den Rush), and gives the meta a reason to carry hard answers.

Open from the first read: food before the payoff (only the Hedgehog's 5 so far; the walls on home regions pay 20 a turn, and the Acorns and a Dusk engine are the candidates), and finding the one-copy payoff (Fathom's Scout always sees it; the Owl digs).

| Card | Habitat | Rarity | Str | Text |
|---|---|---|---:|---|
| Fathom | Open Ocean | L | 7 | Roar: **Scout** a legendary animal. |
| a Squirrel (name to come; Rodent) | | L | 3 | Roar: lose all your food. In 2 turns, gain three times that much. (Three times, Martin: twice is a net gain of only the stake, two turns late, so fair decks just raced it in the imagined games, and neither side touched the other. Three times makes the siege compulsory: fired at 35, it's 105.) |
| a Mimic Octopus (name to come) | Open Ocean | L | ~3 | Roar: this becomes a copy of an adjacent animal. (An amplifier, Martin's pick: a second Capybara, Porcupine or Honey Badger where the fortress needs it; elsewhere it copies any deck's best piece, an enemy's too. The copy takes the animal's strength, keywords and text, but not its Roar, so copying the Squirrel does nothing to the payoff. Fathom and this both need a common or rare Octopus in the pool.) |
| Capybara (Rodent) | Jungle | C | 2 | If your starting deck has no other animal of strength 4 or more, this has strength 9. (2026-10-22: the small-deck common, its one big body; the Armor aura went to the Armadillo, and the Octopus holds its Untouchables rare slot for now.) |
| Porcupine | Forest | R | 5 | **Spikes. Your adjacent animals have Spikes.** |
| Golden Orb-Weaver (Arachnid) | Jungle | R | 4 | When an enemy with **Flight** is placed next to this, remove it. |
| Armadillo | Jungle | R | 5 | **Armor.** Your adjacent animals have **Armor**. |
| Tortoise | Savanna (roster addition) | C | 4 | **Armor.** Roar: gain 5 food for each of your animals with **Armor**. (The early stake: with the Capybara's neighbours, the Armadillo and the Honey Badger, 20–30 food. A common Tortoise also gives Methuselah its species.) |
| Black Bear | Forest | C | 5 | Roar: in 2 turns, draw 2 cards. (From Handlock: slow draw fits the hoard better, Martin.) |
| Owl | Forest | C | 2 | **Flight.** Roar: **Scout** a card. (From Egg Control, Martin: the dig that finds the squirrel or Fathom.) |
| Hedgehog (tagged Rodent) | Meadow | C | 5 | **Spikes.** Roar: gain 5 food. |
| Poison Dart Frog | Jungle | C | 1 | **Reach. Poison.** |
| Jellyfish | Open Ocean | C | 4 | **Poison.** |

Every 10 food on the board by turn 4 is about 30 at the finish, and food arriving on turn 7 counts for nothing: the stake has to be early. Rejected: a common paying food for each Armor, Spikes or Poison animal (clunky; the Tortoise counts Armor alone), and its "each of your animals next to this" rewording (generic food that Food Aggro wants more); the Acorns (late, random food; banked for a deck that draws all game, Egg Control first; Jay as the animal, since Squirrel is taken).

## Food Aggro, draft

Burn (Martin, 2026-10-08): Magic's Red Deck Wins, Hearthstone's Face Hunter. Food from a Roar can't be undone, so every card is a chunk of the opponent's life and nothing on the board blocks it. The fun is counting to lethal: the "10 or more this turn" payoffs make sequencing matter, and the Beaver's extra action with Scrooge makes the burst turn. It preys on control and stall (removal touches nothing here); it loses to den pressure, hand disruption, covering its Rodents (Barley, the Rodent legendary) and, once they exist, the food thieves. It must stay fragile, or it's solitaire.

Imagined games (reasoning, not evidence) showed the clock runs on cards, not food: the hand is empty by turn 4. A card that draws one card is tempo, not value (a Draw action draws two); only cards that draw two or more, or make food over several turns, refill the clock. Face Hunter's hero power, renewable reach at no card cost, has its answer in the empty-hand cards: running out of cards is this deck's best moment, not its end (Magic's Hellbent). A Roar checks the hand after its card has left it, so "if your hand is empty" means "if this was your last card".

| Card | Habitat | Rarity | Str | Text |
|---|---|---|---:|---|
| a Rodent (name to come) | | L | 2 | Roar: draw cards until you have as many as your opponent. (Hearthstone's Divine Favor: a big refill against control, a small one against aggro.) |
| Barley | City | L | 4 | Roar: gain 4 food for each other Rodent you control. Draw a card. |
| Scrooge (rename: the name cites Dickens) | City | L | 4 | Roar: gain 3 food for each 10 food you have. (The finisher, Martin 2026-10-11: 18 at 60 food, 27 at 90. Doubling the turn's food was a common's effect on a legendary, and doubling it every Dusk was too strong.) |
| a Rodent (name to come) | | L | 6 | Roar: repeat the Roar of each of your Rodents next to this. (Martin's wording. The Rodent finisher, played last into your own board; the grid caps it at 4 neighbours, and every Rodent the opponent covers is one fewer Roar. A repeated Scrooge quadruples the turn: Scrooge is the dial.) |
| Flying Squirrel | Forest | R | 3 | **Flight.** Roar: gain 10 food. |
| Beaver | Forest | R | 5 | Roar: next turn, take 1 additional action. (Busy as a beaver. The action comes back next turn, so the Beaver is a free body; 5, Martin 2026-10-12.) |
| Dormouse | Forest (roster addition) | R | 3 | **Dusk:** gain 5 food. (Pays every turn until covered; 5 is a rare's rate, between the common Worker Wasp's 3 and the legendary Methuselah's 5 with its food cap, Martin 2026-10-11. The empty-hand condition never held in a deck that draws constantly. Nocturnal: it comes out at dusk to forage.) |
| Meerkat (tagged Rodent) | Savanna | R | 2 | Roar: draw a card. When an enemy is placed next to this, draw a card. (The sentry at the den front: den pressure turns into cards, often the Muskrat that pushes it back.) |
| Squirrel | Forest | C | 3 | Roar: gain 10 food. |
| Chipmunk | Forest | C | 1 | Roar: gain 10 food. At the start of your next turn, gain 10 more. (Cheek pouches.) |
| Gopher | Meadow | C | 3 | Roar: if you gained 10 or more food this turn, draw 2 cards. |
| Muskrat | Meadow | C | 2 | Roar: if you gained 10 or more food this turn, remove an adjacent enemy. (The den defence.) |
| Groundhog | Meadow | C | 4 | Roar: if you gained 10 or more food this turn, gain 10 food. |
| Hamster | Meadow | C | 2 | Has +1 strength for each 10 food you have. (The board answer, Martin 2026-10-11: the deck had nothing that covers an enemy and stays a big body. A 5 at 30 food, an 8 at 60; it grows in hand too. The hoarder that grows with the hoard. Replaced the Mole, which needed an empty hand and was strictly worse than the Squirrel.) |

Rejected: the Octopus carrying the extra action (its octopus is Fathom, the clever one, and a sea animal in the Rodent deck); Greywhisker and the Naked Mole-Rat (Den Rush's); Mouse and other draw-one cards (tempo, not value); a "protect it and it wins" food engine (a control card); "discard your hand, gain food for each"; "gain food for each card your opponent has more than you"; "the next Roar you play this turn happens twice" (here it's mostly a second Squirrel; banked as the Macaw); a Squirrel that shuffles Acorns into your deck (20 food eventually, in a deck that barely draws; banked for Food OTK, the hoard); the Mouse raid ("gain 10 food for each enemy next to this": Mouse is already a card, and a common animal); a Prairie Dog town rare (Meerkat filled the slot).

## Circle of Life (the Cockroach deck), draft

Symmetric removal that punishes the opponent more than you (Martin, 2026-10-22): the Sperm Whale and its kin remove everything around them, yours included, and you don't mind, because your animals come back (the Cockroach, the Roach King) and every removal pays (the Vulture, the Hyena, the Python). The legendary, The First of Many, is the big reset that amplifies it: the board's top layer cleared, and what survives is yours, the cockroaches crawling back and your buried animals resurfacing. What makes it worth playing: the opponent's interaction feeds it (their covers are your deaths), each turn is a puzzle (how many deaths and payoffs out of two actions), and it wins from behind, on food the opponent can't block, while they seem to hold the board.

How it's built:

- Every piece of fodder pays on its own death; the payoffs multiply that.
- Food scales with the turn's deaths (the Hyena), since food is the win clock; cards don't (the Vulture checks once a turn), since per-death draws would turn the loops into five cards from one action.
- Payoffs count deaths as they happen, not the Remove Pile, since the best fodder leaves the pile (the Cockroach to hand, the Ember to deck).
- Each loop costs a placement, so two actions a turn bound it; any "play another animal" effect needs an audit against these loops.

| Card | Role | Habitat | Rarity | Str | Text |
|---|---|---|---|---:|---|
| Ember (exists) | fodder | Forest | L | 7 | Flight. When this is removed, shuffle it into your deck. |
| the great sloth (legendary, name to come) | payoff | Jungle | L | 4 | Your Dusk effects happen twice. (The sloth sleeps fifteen hours a day. Doubles the Hyena's food and the Vulture's card; bounded, since each Dusk effect fires once a turn. Not tied to this deck: watch it if every Dusk deck runs it.) |
| the cuckoo chick (legendary, name to come; no Flight) | engine | Meadow | L | 6 | Roar: remove an adjacent animal of strength 4 or less. If it was yours, play another animal. (The chick shoves the host's eggs out of the nest and takes their place; a nestling can't fly, and with Flight this would be removal anywhere. The art must show the chick in a host's nest. Vilgefortz's shape, for many decks: on an enemy, small removal; on your own spent small animal, a free placement; here also a death. Not a den burst: removing your own animal from the chain cuts the legendary off.) |
| Tarantula (Arachnid) | engine and body | Jungle | R | 5 | Dawn: remove a random adjacent ally and gain its strength. (A death every turn with no decision at the start of the turn; you steer the randomness by what you place next to it. The deck's one growing body; strength has no ceiling, so past 10 nothing can cover it and only a removal ability answers it, as with the Python.) |
| Praying Mantis | engine | Meadow | R | 3 | Roar: remove one of your animals next to this. If you do, draw 2 cards. |
| Raccoon | recursion | City | R | 2 | Roar: return one of your removed animals to your hand. (Your own only: the Remove Pile is shared.) |
| Sea Turtle | body and fodder | Open Ocean | R | 7 | Dusk: place a Baby Turtle (0, no effect) on an adjacent empty crossroad. (Baby turtles hatch at night and race to the sea; most are eaten. A real body, and free fodder every turn with no card or action spent: next to a Spider the Baby Turtle dies as it lands. A free body each turn is action economy, so it needs the den audit: a turtle one crossroad from the opponent's den front sets up a capture.) |
| City Spider (Arachnid) | engine | City | C | 4 | Dawn: remove a random adjacent ally. (The deck's engine with the Cockroach, Martin 2026-10-11, Hearthstone's Dreadsteed: placed together, a death and a card every turn with no action spent. Dawn, not Dusk, so the turn's Piranha, Hyena and Vulture see the death. A 4 so breaking the engine takes a real animal, not any 3.) |
| Cockroach | fodder | City | C | 1 | When this is removed, return it to your hand and draw a card. |
| Earthworm | fodder | Meadow | C | 1 | When this is removed, place two Worms on its crossroad. (Worm, token, 0: "When this is removed, draw a card.") |
| Piranha (locked; Fish) | removal | Jungle | C | 2 | Roar: if one of your animals was removed this turn, remove an adjacent enemy. (Blood in the water, then the frenzy: the deck's way to fight for the board. A tiny animal that kills anything, so no big animal can carry it.) |
| Vulture (locked; Bird) | payoff: cards | Savanna | C | 3 | Flight. At the end of your turn, if one of your animals was removed this turn, draw a card. |
| Hyena (no tag) | finisher | Savanna | C | 4 | Dusk: gain 5 food for each of your animals removed this turn. (The laughing scavenger: deaths into food. With the Spider's death every turn the deaths are free, so 5 makes it the clock: two Hyenas and two deaths are 20 a turn, Martin 2026-10-11. Copies stack, and the Sloth doubles it; the 5 is the dial.) |

Expected weak points, untested: few cards that kill your own (Spiders die to any cover), and few bodies bigger than a 4. The Tarantula is aimed at both.

## Canines

The pack that roams the board, buffs itself on the board (Primates buff in hand) and hunts by position. High skill: each turn is a puzzle of moves and placements across two actions. Built on Roam ([`../rules/keywords.md`](../rules/keywords.md)), a game-wide keyword that Canines carry most. Count-based effects (stronger the more of them) belong to the Fish. Scarlett stays in the pool, outside this precon.

| Card | Habitat | Rarity | Str | Text |
|---|---|---|---:|---|
| legendary Leopard (name to come; Cat) | Savanna | L | 5 | Apex Predator. Roam. Reach. (Drops onto its prey from a tree, then waits: landing by Reach leaves it unconnected, so it roams again once the chain reaches it.) |
| Clarion | Forest | L | 5 | Once each turn, one of your Canines can roam for free. (The deck is short of actions, not cards.) |
| Lobo | Forest | L | 6 | Whenever one of your animals roams onto an enemy, draw a card. (The wolf king feeds the pack; bounded by one roam per animal per turn.) |
| legendary wolf (name to come) | Forest | L | 4 | Roam. When this roams, your animals next to it gain +2 strength. |
| Orca | Open Ocean | R | 6 | Apex Predator. Roam. (The wolf of the sea; it eats with every roam, so its strength is the dial.) |
| African Wild Dog | Savanna | R | 4 | Roam. Whenever this covers an enemy, draw a card. (The most successful hunter. Rare, not common: three copies would keep one on the board in every game against decks of small animals.) |
| Jackal | Savanna | R | 4 | Roar: remove an adjacent enemy that has another of your Canines next to it. |
| Dhole | Jungle | R | ~6 | Roam. Your animals can roam onto enemies of equal strength. (Dhole packs take prey bigger than themselves.) |
| Wolf | Forest | C | 6 | Roam. (The plain hunter, one below the Lion.) |
| Bush Dog | Jungle | C | 3 | Roar: give an adjacent Canine +3 strength. |
| Raccoon Dog | Forest | C | 3 | Whenever one of your Canines roams, give it +1 strength. |
| Fox | Forest | C | 3 | Dusk: give your adjacent animals +1 strength. |
| Badger | Forest | C | 4 | Roar: draw an animal with Roam. (It digs the prey out for the runners, as badgers do for coyotes.) |
| Street Dog | City | C | 1 | Roar: give one of your animals with Roam +2 strength. It roams. |

Open: the Dhole's strength (~6); a slot for the Raccoon Dog on the Forest roster. "Your animals next to this have Roam" waits for a legendary in a deck without roamers of its own.

## Fish Token Aggro, draft

The swarm (Martin, 2026-10-08). Gwent's Arachas, Hearthstone's Murlocs: one card becomes a school, and every Fish makes the others better. The opponent should feel outnumbered, not outmuscled: each fish is small, but covering them one by one costs a card and an action each. A 2×2 square of Fish is a region, so the packed school wins on food. It preys on slow decks and on decks that answer one threat at a time; area removal (Rhinoceros, Hippopotamus, Brutus) is its predator, which puts Giants on top of it.

How a game goes (agreed with Martin, 2026-10-08): the deck's resource is the empty board, which is full by turn 4 or 5. Turns 1–3 flood it and close regions (two regions, 25 food a turn, reach 100 around turn 6 or 7). Turns 4–6 hold them: the count cards are big by then, and removal clears the coverers off your corners; late Fish land on your own Fish (always legal), firing their Roars and leaving a backup beneath. If the opponent wins the board war by turn 6, Fish loses, on purpose (Hearthstone's Token Paladin): the cards that fill empty crossroads are dead topdecks late, the price of the best opening in the game. Its meta role: it punishes greed in the opening (Handlock, Food OTK, Giants). Food Aggro races off the board, Hoofed holds one region slowly with big animals; Fish takes many regions, fast and fragile. One buff card at most, or it's the old Canines again.

Payoffs count every Fish you control: a plain count keeps the swarm feeling, and a smooth count (each Fish a bit more) plays differently from Colony's thresholds. Adjacency cards stay wherever they make sense; on map_b a crossroad has at most 4 neighbours, so "for each adjacent Fish" pays about 1, at best 2.

Legendaries are drawn at a random point, often after the board is full, so each must work then; the opening is the commons' job (three copies each).

The list (Martin, 2026-10-08; animals and strengths set, wording to the card-text conventions):

| Card | Habitat | Rarity | Str | Text |
|---|---|---|---:|---|
| a Jellyfish (no Fish tag; name to come) | Open Ocean | L | 6 | Your Fish next to this have **Poison**. (Young fish shelter among jellyfish tentacles. "Your other Fish have Poison" would make every corner uncoverable: the herd's rejected card again.) |
| a Bluefin Tuna (name to come) | Open Ocean | L | 5 | Roar: for each region you control, draw a card and gain 5 food. (The closer and the late reload; tuna is the fish people know as food. The herd's white stag, "draw a card for each region you control", needs another effect.) |
| a Manta Ray (name to come) | Open Ocean | L | 4 | **Dusk:** if you control 2 or more regions, draw a card. |
| a Piranha (name to come) | Jungle | L | 7 | Your Fish can be placed on enemies of strength up to the number of Fish you control. (The school strips something far bigger: once the board is full, it lets the small Fish win crossroads back. Snow Leopard's shape.) |
| Swordfish | Open Ocean | R | 3 | Roar: remove a random adjacent enemy for each of your Fish next to this. |
| Barracuda | Open Ocean | R | 4 | Roar: remove an adjacent enemy of strength up to the number of your Fish. |
| Manta Ray | Open Ocean | R | 6 | Whenever your opponent covers one of your Fish, draw a card. |
| Remora | Open Ocean | R | 3 | Roar: play another Fish. (It arrives riding a bigger fish.) |
| Cod | Open Ocean | C | 4 | Roar: draw a card for each of your Fish next to this. |
| Sardine | Open Ocean | C | 1 | Roar: place all Sardines from your hand and deck on random adjacent empty crossroads. (Lemming's effect, fine in play.) |
| Mahi-mahi | Open Ocean | C | 3 | Roar: give your other Fish +1 strength. |
| Mackerel | Open Ocean | C | 2 | Your other Fish have +1 strength. |
| Tuna | Open Ocean | C | 3 | Has +1 strength for each other Fish you control. |
| Sunfish | Open Ocean | C | 4 | Roar: place a Baby Fish (token, Fish, 0) on an empty crossroad next to this. (It lays more eggs than any other animal.) |

Sharks stay out of the count cards: they're lone hunters. Fish's predator is weak on this map (area removal reaches only the edge of a school built at home); Giants need a way to hit the middle of a school. Open Ocean's roster gains Sardine, Tuna, Cod, Remora, Barracuda, Mahi-mahi and Mackerel, to settle in the roster pass after the decks. Rejected: Baby Fish spawners at legendary and rare (empty crossroads exist only in the first turns), a food common (Food Aggro's ground), Goldfish (a pet), Salmon (a river fish, for River and Lake).

## Hoofed Graze, draft

The herd on its pasture (Martin, 2026-10-08): the nearest card-game match is Magic's Pillowfort, a deck that makes attacking it unprofitable while a slow engine wins, here on a piece of land. Hold regions with grazers, win on food; grazing is all or nothing, so one covered corner breaks the region and switches off every grazing bonus, and the opponent always has a weak corner to aim at. It beats decks that win by covering (Cats, Canines, Fish) and Giants' coverers (the Buffalo removes whatever covers your animal); it loses to decks that just race. The plan that's fast enough is both home regions (six crossroads, shared corners at the den front), not one.

The deck is two halves (the fix for Flee fighting the pasture, found in the imagined games): fleers hold their value in their Roar, so running home is a refund and the Roar comes again; standers hold their value on the corners, and the Buffalo frees them when they're covered. Fleers fill the empty pasture early; standers are then placed on top of them (Flee triggers only on an enemy cover); the opponent attacks a stander's corner and the Buffalo frees it.

| Card | Habitat | Rarity | Str | Text |
|---|---|---|---:|---|
| a Wildebeest (the Great Migration; name to come; Hoofed) | Savanna | L | 5 | Your regions produce 5 more food. (5, not the common's 6: an engine has to stay coverable.) |
| a Giraffe (name to come; Hoofed) | Savanna | L | 5 | Your opponent plays with their hand revealed. (The tallest animal sees the lions first. Good in any reactive deck.) |
| a Boar (name to come; Hoofed) | Forest | L | 5 | Your opponent's regions produce 5 less food. (Martin's: a tech card against every deck that farms regions, the mirror of the Migration. Wild boars tearing up fields is what farmers know them for.) |
| a Zebra (name to come; Hoofed) | Savanna | L | 5 | Roar: draw a card for each different Hoofed animal next to this. (The mixed herd: zebras grazing among the wildebeest, the herd every savanna picture shows. Not the Gazelle, which has no link to many kinds of neighbour; not the Oxpecker, whose common works with the Giants. Counts kinds, not numbers, a synergy no other family has; at most 4 neighbours, usually 2 or 3 cards.) |
| Zebra | Savanna | R | 5 | **Flee.** When this flees, return the enemy that covered it to its owner's hand. (Stripes: the striped herd blurs and the attacker lunges at nothing. The corner is left empty, not taken, so you play the Zebra back onto it; taking it costs the opponent two actions.) |
| Moose | Forest | R | 6 | Your other Hoofed animals have +1 strength during your opponent's turn. (+2 put every front corner out of reach, Martin.) |
| Honey Badger | Savanna | R | 2 | Roar: remove an adjacent enemy of strength 6 or more. |
| Okapi | Jungle (roster addition) | R | 4 | At the end of your turn, if this is grazing, draw a card. (The herd's card flow, on a stander. The one-of-a-kind forest giraffe with zebra legs; the Impala was the other option, a Gazelle lookalike.) |
| Cape Buffalo (stander) | Savanna | C | 4 | Roar: remove an adjacent enemy covering one of your Hoofed animals. (Martin's: the buffalo drives the predator off and the animal underneath is safe. Common, since it's the deck's core loop.) |
| Wildebeest (stander) | Savanna | C | 6 | At the end of your turn, if this is grazing, gain 5 food. |
| Giraffe (stander) | Savanna | C | 4 | Has +5 strength during your opponent's turn. |
| Boar (remover) | Forest | C | 4 | Roar: remove an adjacent enemy that isn't covering anything. (Martin, 2026-10-14: the deck had walls enough and no answer to a 6 or 7 on bare ground but two Honey Badgers; Cape Buffalo answers an enemy on your animal, the Boar one on empty ground. The grazing Boar was a third Giraffe. Dial if it's too much: "of strength 7 or less".) |
| Gazelle (fleer) | Savanna | C | 3 | **Flee.** Roar: gain 5 food. |
| Deer (fleer) | Forest | C | 4 | **Flee.** Roar: draw a Hoofed animal. |

Rejected: a regroup rare ("play a Hoofed animal from your hand": spends the hand this deck is short of); the fleeing payoff, the white stag that re-lands on an empty crossroad (there rarely is one) and the herd that bolts back to hand (it wastes your own actions, the opposite of Flee); "enemy regions next to your grazing animals produce no food" (an animal next to a region is one of its corners, so no enemy region is ever next to yours); Flee on animals whose value is where they stand (a fled corner can't be retaken, since the coverer is bigger); Stealth, Armor and Spikes while grazing (Food OTK's identity); a den that can't be captured while grazing; a +1 anthem legendary; a herd bull that stops covers on your other grazing animals (on the back corner nothing reaches it: a lock); a stampede and a 3-of-4-corners region (clunky); the Zebra kicking an enemy back to hand (Zebra is its stripes).

## Giants, draft

Feed the giants (Martin, 2026-10-08): Magic's Eldrazi Ramp, Hearthstone's Ramp and Big Druid. The ramp resource is food, which is also the win counter: every point a giant eats is a point not counting toward 100, so Giants win on the board and the den, rarely on food. Hungry animals eat each turn or shrink; the food cards keep them fed. The fun is landing bodies nothing can cover and running the feeding economy. It beats boards of small and mid-sized animals by covering them with bodies they can't cover back (Fish, Cats, Canines: Giants prey on Fish by covering their region corners, not by area removal, which reaches only a school's edge); it loses to races it can't touch (Food Aggro), unconditional removal (King Cobra, the Octopus's ink) and fortresses (Spikes kills any coverer).

Imagined games (reasoning, not evidence): the board dominance works from turn 4, once the chain delivers the bodies; the feeding economy bites only when the ramp pieces come late (three giants eat about 11 a turn); the Oxpecker is a big ramp piece (about fifteen animals of 8 or more in the starting deck).

| Card | Habitat | Rarity | Str | Text |
|---|---|---|---:|---|
| Brutus (Hoofed) | Savanna | L | 8 | **Hungry 6.** Roar: remove all adjacent animals. |
| Methuselah | Savanna | L | 3 | **Armor.** At the end of your turn, gain 5 food. |
| a Sperm Whale (Moby Dick's whale: the white sperm whale in the art, a name evoking it without citing it, as Eon evokes the Ouroboros; the name must work for players, so no obscure real whale's name) | Open Ocean | L | 10 | **Titan.** Roar: remove all enemies next to your animals. (To try, Martin: on map_b it's close to a full board wipe, everything touching your herd. A 10 can't be covered, so the power has to be in the arrival and nothing may keep working after it: "an enemy placed next to this is removed" locked whole regions for decks without a removal Roar. Dials if too strong: "of strength 7 or less", "next to your Hungry animals", or Brutus's own neighbours. Needs a common or rare Sperm Whale.) |
| an Oxpecker (proposed; name to come; Bird) | Savanna | L | ~2 | **Flight.** Your Hungry animals next to this don't need to eat. (Oxpeckers live on giants, eating their ticks. Placed between giants, it's guarded by them: an enemy has to reach one of its free sides.) |
| Rhinoceros (Hoofed) | Savanna | R | 8 | **Hungry 3.** Roar: remove all adjacent enemies of strength 2 or less. |
| Hippopotamus (Hoofed) | Savanna | R | 8 | **Hungry 3.** When an enemy of strength 3 or less is placed next to this, remove it. |
| Crocodile | Savanna | R | 8 | **Apex Predator.** |
| Whale Shark (Fish) | Open Ocean | R | 8 | **Titan. Hungry 4.** At the end of your turn, draw 2 cards. |
| Sperm Whale | Open Ocean | R | 8 | **Titan.** Roar: remove all adjacent animals. (Brutus's Roar, paid with a whole turn instead of Hungry 6, Martin. Its own neighbours die too, so it lands at the front. Gives Moby's whale its species.) |
| Oxpecker (Bird) | Savanna | C | 1 | **Flight.** Roar: gain 1 food for each animal of strength 8 or more in your starting deck. |
| Anteater | Jungle | C | 4 | Roar: draw a card. Gain food equal to its strength. (It rips open termite mounds: the bigger the mound, the bigger the meal.) |
| Dung Beetle | Savanna | C | 1 | At the end of your turn, gain 2 food for each Hungry animal you control. |
| Blue Whale | Open Ocean | C | 10 | **Titan.** |
| Sloth | Jungle | C | 3 | Roar: in 2 turns, gain 30 food. |
| Elephant | Savanna | C | 9 | **Hungry 5.** |

Titan means playing it costs two actions (Martin): the Blue Whale is a whole turn for a 10 that never eats, the Elephant one action for a 9 that eats 5 a turn. Rejected: the Anteater as an anti-Colony card (Martin: a card that only punishes one deck is bad design), and "Giant" in its name (it's a 4).

## Handlock, draft

Train in secret, then unveil (Martin, 2026-10-08): Hearthstone's Handlock and hand-buff decks (Don Han'Cho, the Grimy Goons); Magic has almost nothing like it. Two hand themes: hand size (Macaque, Grizzly) and training cards in hand (Baboon, Silverback, Orangutan, Tarsier), paid off by thresholds and triggers (Chimpanzee, Gorilla, Capuchin). The fun is hidden power: the opponent sees how many cards you hold, never how strong they are. Strength past about 8 buys almost nothing on the board, so training has to pay off through thresholds, triggers and removal, not raw size. It beats midrange and strength-gated removal; it loses to speed and to hand disruption (Egg Control's Black Swan and Magpie). The first version is [`hand-deck.md`](hand-deck.md); this list replaces it. Commons and rares locked (Martin, 2026-10-08); the legendaries are drafted, the Butterfly's stages and Silverback's +2 to try.

| Card | Habitat | Rarity | Str | Text |
|---|---|---|---:|---|
| a Baboon (name to come; Primate) | Savanna | L | 5 | At the end of your turn, give 2 random animals in your hand +1 strength. |
| Silverback (Gorilla, Primate) | Jungle | L | 7 | Roar: give all animals in your hand +2 strength. (Raised from +1, which was thin for a legendary next to the common Baboon; to try, Martin: may be too strong. The dial is the +2 or the 7.) |
| a Butterfly (name to come) | Meadow | L | 0 | Dawn: evolve. Whenever this gains strength, evolve. (Martin, 2026-10-22: it ripens by itself, in hand or on the board, and buffs only speed it up; evolving on buffs alone made it win-more, its fourth buff arriving when the hand was nearly empty, every buff taken from a real threat. Stages stack, each adding to the last: 1 Egg, no text; 2 Caterpillar, "Roar: draw a card."; 3 Chrysalis, "**Stealth.** Roar: draw a card, then give an animal in your hand +1 strength."; 4 Butterfly, "**Stealth. Flight.** Roar: draw a card, then give all animals in your hand +1 strength."; 5 Monarch, "**Stealth. Flight.** Roar: draw 2 cards, then give all animals in your hand +2 strength." Power climbs evenly: below a common, then common to rare, rare to legendary, above an average legendary. Every buff adds its strength and moves it one stage, so its strength is its buffs; one Dawn or one buff is one stage. The stage shows as a badge on the art, explained on hover; the art changes with each stage. Stealth, not Armor: a chrysalis is famous for hiding, and butterflies hide too.) |
| an Eagle, one of a mated pair (names to come; Bird) | Forest | L | ~2 | **Flight. Apex Predator.** When this enters your hand, add [its mate] to your hand. (The mate, made by this card, not in the deck: "**Flight. Apex Predator.** While this and [its mate] are in your hand, they share their strength." Martin's: every buff to either counts for both, the deck's missing outlet for training; trained, each eats an enemy anywhere. Sharing one number avoids the loop "when one gains, the other gains" would make. An Apex Predator can't land on an empty crossroad or a den, so Flight never captures.) |
| Hummingbird (Bird) | Jungle | R | 1 | **Flight.** Roar: draw 2 cards. |
| Macaque (Primate) | City | R | 2 | Roar: if you have 5 or more cards in your hand, remove an adjacent enemy. |
| Orangutan (Primate) | Jungle | R | 5 | Roar: duplicate a Primate in your hand. |
| Tarsier (Primate) | Jungle | R | 2 | Roar: **Scout** a Primate and give it +1 strength. |
| Butterfly | Meadow | R | 2 | **Flight.** Roar: draw a card, then give an animal in your hand +1 strength. (Also what the Caterpillar becomes.) |
| Chimpanzee (Primate) | Jungle | C | 4 | Roar: remove an adjacent enemy of equal or lower strength. (The chimp with its stone or stick: the tool is as heavy as the arm that swings it. It took the Capuchin's effect, since everyone knows a chimp.) |
| Baboon (Primate) | Savanna | C | 4 | Roar: give 2 animals in your hand +1 strength. |
| Stork (Bird) | Meadow | C | 4 | **Flight.** Roar: add two random younglings to your hand. (Younglings, 1, no text, one per family: Baby Lion (Cat), Baby Wolf (Canine), Baby Squirrel (Rodent), Baby Owl (Bird), Baby Python (Snake), Baby Bear (Bear), Baby Gorilla (Primate), Baby Zebra (Hoofed).) |
| Grizzly Bear (Bear) | Forest | C | 2 | Has +1 strength for each card in your hand. (A bear fattening for winter. Live, so it shrinks as you play your hand out.) |
| Caterpillar | Meadow | C | 1 | When this gains strength in your hand, draw a card and turn this into a Butterfly. (Replaces the Chimpanzee's draw on every training step, the deck's strongest common.) |
| Gorilla (Primate) | Jungle | C | 6 | Roar: if this has 8 or more strength, draw a card. |

## Egg Control

The Owl went to Food OTK; its common slot goes to the Mosquito (Martin, 2026-10-08): with Flight it shrinks any enemy on the board, setting up the flying Hawk (a 5 becomes a 3) or the Black Mamba (a 7 becomes a 5). The Viper does the same job next to your chain only, a midrange card. Rejected for the slot: a Magpie that filters (a weaker Raven, and the Magpie exists), the Monitor Lizard (anti-token removal that replaces itself: good everywhere, nothing special here; banked; eating your own Egg only throws away its hatch).

Its fourth legendary: Omen (a raven; Forest, L, ~3, Bird): "Flight. Roar: put an animal from your opponent's Remove Pile into your hand." The deck removes more than any other, so the opponent's pile holds their best cards; a Bird, so the Bird Egg's Scout can find it. Wording to bring in line on the deck's cards: Eon's end-of-turn shuffle is a Dusk effect, Aurum is "Dawn: draw a card.", the Python counts removed animals (not units), and the Egg Eater counts removed Eggs.

## Colony outside the precon, draft

The precon's fourteen cards all carry a Colony-shaped condition (4 or more, a Queen, a Worker, two of the same), so none of them leaves the deck and only the Hornet enters it (Martin, 2026-10-21: a Colony player is forced into all four legendaries, and the tag has one card outside the precon). Wanted: about two legendaries, a rare and three commons that carry the tag and work in other decks. The shape that travels: the card's own condition is one other decks meet for their own reasons (a food threshold, Flight, its own copies), and the tag is only a tag, a body Colony counts toward its thresholds. "If you control another Colony animal" is the precon in disguise and is not used. New Colony cards are castes of the species already in the deck (Bee, Bumblebee, Wasp, Hornet, Ant, Army Ant, Termite): the deck splits its species by caste, never by subspecies, so a Leafcutter Ant can't stand beside Worker Ant and Soldier Ant.

Queen Melissia says "whenever you place" (Martin, 2026-10-21), not "play": Vesper arriving from the deck and a Vulture landing pay her too; moving (Roam) still doesn't.

Proposed, effects agreed (Martin: "sounds much better effect-wise"), animals and numbers to settle:

| Card | Rarity | Habitat | Str | Text | Closest card |
|---|---|---|---:|---|---|
| Guard Bee | C | Meadow | 2 | Flight. Spikes. | Hedgehog (5, Spikes, gain 5), Porcupine (7, Spikes): a third the body, and it flies |
| Forager Ant (Worker) | C | Forest | 1 | Roar: gain 5 food. If you gained 10 or more food this turn, draw a card. | Worker Ant (12 on the same body), Muskrat (the same condition, removal) |
| Queen Wasp (Queen) | R | Forest | 4 | Flight. Whenever you place an animal with Flight, gain 3 food. | Queen Melissia, keyed to Flight at a rare's rate so the legendary stays ahead |
| The Bee (the dancer) | L | Meadow | ? | Flight. Dusk: if you gained 20 or more food this turn, draw a card. | Tally turns food into food; this turns it into cards |
| The Ant (the farmer) | L | Forest | 1 | Dusk: gain 2 food for each animal you control. | Dung Beetle (Dusk: 2 per Hungry animal); pays any wide deck |

Also: the Naked Mole-Rat (Savanna roster) is the one eusocial mammal and would carry Colony beside Rodent, the first card two families both want.

## Open topics

- The bloodsuckers drain strength: Mosquito's −2, Leech's swap, the Tick's effect still to design, likely a slow drain.
- Taking the opponent's food belongs to thieves (Seagull later, the monkeys) and gets its own session.

## Elsewhere, settled in passing

- Cats: Caracal (Savanna, C, 6), "Reach.", the leap over the front line onto the engines behind it, which every other Cat can only hit when adjacent (at 5 or less the Eagle practically dominates it); Lynx (Forest, C, 6), "Roar: if placed on top of an enemy, draw a card."; Bobcat (Forest, C, 5), "Roar: if you control another Cat, draw a card." The Cougar and its effect wait for Mountains.
- Cuckoo (Meadow, R, ~3, Bird): "Flight. Roar: shuffle two Cuckoo Eggs into your opponent's deck." Cuckoo Egg (token, 0): "When you draw this, your opponent draws a card." The opponent's deck is the host's nest: each Egg clogs their deck, then their hand. It stays in the hand of whoever drew it and is theirs to play (a 0-strength animal); with no way to discard, getting rid of it costs one of their actions. A disruption card, hardest on the decks that draw a lot.
- Mosquito (City, C, ~1): "Flight. Roar: give an adjacent enemy −2 strength."
- Leech (Jungle, 1): "Roar: swap strength with an adjacent animal." It drains its host: the host shrinks, the leech swells. At 1 it can't cover anything, so it lands only on an empty crossroad or one of your own.
- Opossum (City, R, 2, Marsupial): "Roar: return one of your animals next to this to your hand." A mother gathering her young onto her back; it replays an animal's Roar (Skully, Chipmunk, a removal), a value card for other decks, and the City's seed for the Marsupials' "carrying the young" identity when Australia comes.
- Clownfish (Coral Reef, later): its "play another Fish" went to the Remora; Coral Reef gives it its own trait (safe in a stinging anemone). Electric Eel (Jungle) is the stun.
- The decoy (Lapwing, needs a common or rare Lapwing): "Enemy abilities that choose an animal must choose this, if able." It fakes a broken wing to lead predators from the nest. A protector of any deck's engine.
- The lure (a legendary Firefly): "Roar: your opponent's next animal must be placed next to this, if able." The femme-fatale firefly copies another species' flash and eats the males that come. First candidate for the Arachnid traps deck.
- Octopus (Open Ocean, R, ~4; locked, Martin): "Roar: choose an adjacent enemy. Until your next turn, it loses all its effects." The ink cloud: a one-turn blackout of one animal's Spikes, Poison, Armor, trap or aura, the hard answer to Food OTK's fortress and any engine; one target, not all its neighbours (Martin). It gives Fathom and the Mimic Octopus their species.
- Great White Shark (Open Ocean, R, 7; locked, Martin): "**Apex Predator.** If an animal was removed this turn, this has **Reach**." It smells blood and strikes from your own side. Reach, not "ignoring connection": it launches from your connected animals. The blood condition keeps it apart from the legendary Leopard (Apex, Roam, Reach).
- The herd over its young (Martin likes it, for another deck): "Your animals placed on top of your own animals have +2 strength." A mechanic only this game has; Fish landing on their own Fish late is the first fit.
- Groundhog Day (a later Groundhog legendary, in a slower deck; the species has its Food Aggro common): "Roar: gain 5 food. Dawn: this Roars again." The day that keeps repeating, an everyday idiom. Not on the common: Food Aggro wants this turn's burst, not an engine.
- Platypus (Australia, later): its family tag is "All", counting as every family (Martin, 2026-10-08).
- Hermit Crab (Coast, later): Armor plus something about moving into another's shell.
- Macaw (Jungle, Bird; rarity and strength with its deck): "Roar: your next Roar this turn happens twice." (This turn only: cleaner, Martin.) The parrot repeats what it hears. A card for a deck with few, high-impact Roars; Handlock is the first candidate (a doubled Gorilla sweep, an Orangutan training the hand twice). In Food Aggro it was mostly a second Squirrel.
