# Effects pass

Each launch animal's card, settled habitat by habitat with Martin. Existing cards keep their effect unless noted. Strengths of existing cards wait for the strength-realism pass; numbers marked ~ are first guesses.

Keywords proposed in this pass: **Hungry N** (at the start of your turn, eat N food; if you can't, this gets −N strength), **Flee** (when an enemy covers this, return it to your hand), **Reach N** (lands up to N crossroads from your connected units; [`../rules/keywords.md`](../rules/keywords.md)), **Poison**, **Wake** and **Sleep** (start and end of your turn; card text in this doc still spells them out until the cards are rewritten), and grazing as a condition (an animal grazes while it's a corner of a region you control; card wording still to choose between "if this is grazing" and "if this controls a region").

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
| Honey Badger | R | 3 | Roar: remove an adjacent enemy of strength 6 or more. | the Big Game Hunter (Serval's old effect) |
| Serval | R | 4 | Roar: set an adjacent enemy's strength to 1. | 4, not 2, so the Leech's swap doesn't dominate it: the Serval can cover a 3 and pin in one placement | the Cats' answer to big animals: pin the prey, the pride covers it |
| Rhinoceros | R | 8 | Hungry 3. Roar: remove all adjacent enemies of strength 2 or less. | a Giant ~ |
| Hippopotamus | R | 8 | Hungry 3. When an enemy of strength 3 or less is placed next to this, remove it. | a Giant; the reaction stays (the client is to show what removed an animal) ~ |
| Cape Buffalo | R | 6 | While grazing, this has +3 strength. | stands its ground on its own land |
| Crocodile | R | 8 | Apex Predator. | the ambush at the river crossing; art: the huge Nile crocodile, not the Jaguar's caiman |

| Meerkat | C | 2 | Roar: draw a card. When an enemy is placed next to this, draw a card. | the sentry |

Open: Secretarybird, Aardvark, the legendaries; Warthog moves to rare (the herd's den guard), which shifts Savanna's split to rebalance later.

## The herd (Hoofed grazing), draft

Designed as one archetype across the habitats, not card by card (Martin, 2026-10-05). The plan: take a region early and hold it, put grazers on its corners, win on food; the opponent breaks the region. An animal, yours or the opponent's, is grazing while it's a corner of a region its owner controls. Grazing checks stay out of Roars, since region control is checked after a Roar resolves.

- Commons (a deck runs six of these): Gazelle, Giraffe, Wildebeest (as locked above); Zebra, "Flee. While grazing, this has Stealth."; Deer (Forest), "Flee. At the end of your turn, if this is grazing, draw a card."; Cape Buffalo (as locked); Moose (Forest), "Your other grazing animals have +2 strength."; Boar (Forest), "Roar: remove an adjacent enemy that is grazing."
- Rares: Warthog (as locked), Rhinoceros, Hippopotamus (shared with the Giants), Beaver (Forest, R, 4), "Your regions next to this produce 5 more food." (beaver ponds make the land around them richer; a local version of the migration legendary).
- Legendaries: the migration's wildebeest, "Your regions produce 5 more food."; the white stag, "Flee. Roar: draw a card for each region you control."; two open. Rejected: "when an enemy covers one of your grazing animals, remove that enemy" (every corner uncoverable, so the region can't be broken).

Zebra, Deer, Moose, Boar and the two legendaries are proposals.

## The food split (2026-10-07)

Today's Food OTK deck plays as food aggro: nearly every card gains about 10 food, so each action ticks a steady clock and there is nothing to assemble. It becomes two decks:

- **Rodent food aggro:** the Rodents (Barley, Scrooge, Squirrel, Flying Squirrel, Chipmunk, Hamster, Muskrat, Groundhog, Hedgehog) and about four new finishers and speed cards. Scrooge's one-turn burst belongs here.
- **The hoard (true combo):** draw, assemble, stall, execute. Its food sources must be slow, so the fair route is too slow and the payoff is the plan. It takes the stall pieces (Porcupine, Armadillo, Octopus, Fathom) and Black Bear, and gives the game the defensive cards it lacks: spines and poison that punish a cover (Porcupine, Hedgehog, Poison Dart Frog, Jellyfish, Toad), builders that block the way in (Beaver's dam against the den rush, Spider's web against Flight and Reach), survivors as support (Opossum, Cockroach, Earthworm, Gecko). It loses to food aggro by design: food from Roars can't be touched.

The payoff, a legendary squirrel (name to come): "Roar: lose all your food. In 2 turns, gain twice that much." No Armor and a modest body: the deck has to protect it, and covering pauses its timer. Removing it loses the whole stake; that risk is the point (doubling the food at payout instead would be a win button: any opening reaches 50 by then). Fathom ("Roar: Scout a legendary animal") is its tutor.

The defensive cards, one answer for each way to reach the squirrel (removal, a ground cover, a cover from behind the lines). Each must be beaten by no existing card and must leave the opponent an ordinary answer:

| Animal | Habitat | Rarity | Str | Text | The opponent's answer |
|---|---|---|---:|---|---|
| Poison Dart Frog (locked) | Jungle | C | 1 | Reach 2. Poison. | a removal ability |
| Jellyfish (locked) | Open Ocean | R | 3 | Poison. | a removal ability |
| Golden Orb-Weaver (locked; Arachnid) | Jungle | R | 3 | When an enemy with Flight is placed next to this, remove it. | cover it (a flyer needs 4+); ground animals ignore the web |
| Capybara | Jungle | R | 5 | Your animals next to this have Armor. | cover its neighbours, cover it (6+), or remove it |

Open: a Capybara beside a Porcupine is the strongest wall these build (unremovable, kills its first coverer, broken by a second cover of 8+). Rejected: plain Spikes on a small body (Hedgehog dominates it); an animal that removes every coverer at once (an unbreakable wall, the herd draft's rejected rule); "when this is removed" survivors on small bodies (Opossum, Cockroach, Earthworm): nobody removes a 1 or a 2, they cover it, so the text never fires; turned into "when covered", the Cockroach becomes a dominated Flee and the Opossum a weaker Poison, and the Earthworm's two 0-strength Worms block nothing (anything covers a 0): they are free bodies for regions and connection, an action-economy card for another deck; a dam that keeps enemies off the crossroads next to it: permanent, it guards its own approach, so with hand buffs and Armor it can't be answered at all (an exception for Flight still hard-locks every deck without flyers); for one turn it barely matters; Dam tokens block nothing (anything covers a 0), burst free placements and aren't animals.

## The aristocrats, draft (2026-10-07)

The combo deck from `families.md`: your own animals die on purpose and every death pays. What makes it worth playing: the opponent's interaction feeds it (their covers are your deaths), each turn is a puzzle (how many deaths and payoffs out of two actions), and it wins from behind, on food the opponent can't block, while they seem to hold the board. Every piece of fodder pays on its own death; the payoffs multiply that. Each loop costs a placement, so two actions a turn bound it; any future "play another animal" effect needs an audit against these loops.

| Card | Role | Habitat | Rarity | Str | Text |
|---|---|---|---|---:|---|
| Ember (exists) | fodder | Forest | L | 7 | Flight. When this is removed, shuffle it into your deck. |
| the playing-dead opossum (legendary, name to come) | engine | City | L | 2 | When one of your animals is covered, remove it and draw a card. (Covers by either player: your own cover onto your fodder is a death and a card, so every placement runs the engine, and every enemy cover feeds you. The answer: cover or remove it, a 2.) |
| the great sloth (legendary, name to come) | payoff | Jungle | L | ~3 | Your Sleep effects happen twice. (The sloth sleeps fifteen hours a day. Doubles the Hyena's food and the Vulture's card; bounded, since each Sleep effect fires once a turn. Not tied to this deck: watch it if every Sleep deck runs it.) |
| Tarantula (Arachnid) | engine and body | Jungle | R | 5 | Sleep: remove a random one of your animals next to this. This gains its strength. (A death every turn with no decision at the end of the turn; you steer the randomness by what you place next to it. It is the deck's one growing body, up to 10.) |
| Praying Mantis | engine | Meadow | R | 3 | Roar: remove one of your animals next to this. If you do, draw 2 cards. |
| City Spider (Arachnid) | engine | City | C | 2 | When an animal of strength 2 or less is placed next to this, remove it. (Both sides: a trap for the opponent's small animals and tokens, a repeatable death for yours.) |
| Cockroach | fodder | City | C | 1 | When this is removed, return it to your hand and draw a card. |
| Earthworm | fodder | Meadow | C | 1 | When this is removed, place two Worms on its crossroad. (Worm, token, 0: "When this is removed, draw a card.") |
| Piranha (locked) | removal | Jungle | C | 2 | Roar: if one of your animals was removed this turn, remove an adjacent enemy. (Blood in the water, then the frenzy; the Muskrat's shape on this deck's condition: the deck's way to fight for the board.) |
| Vulture (locked; Bird) | payoff: cards | Savanna | C | 3 | Flight. At the end of your turn, if one of your animals was removed this turn, draw a card. (Once a turn, so the loops can't blow it up.) |
| Hyena (no tag) | finisher | Savanna | C | 4 | At the end of your turn, if one of your animals was removed this turn, gain 6 food. (The laughing scavenger: deaths into food, so the deck wins from behind while the opponent holds the board. Common, beside the Vulture, with the same once-a-turn check. The clock is the number of Hyenas on the board, about 6 food a turn each; if games run long, the dial is the 6. Its old Canine pack removal goes to the Dhole, settled with the Canine deck.) |
| Raccoon | payoff: recursion | City | R | 2 | Roar: return one of your removed animals to your hand. (Only your own: the Remove Pile is shared, and taking the opponent's best card would be legendary-level.) |

Played out in the head (2026-10-07), the first version lost with eight cards in hand: an engine with no finisher and no board. Hence the Piranha (removal), the Hyena (deaths into food) and the opossum (the opponent's covers feed you). The Python goes back to Egg Control: it counts the Remove Pile, and this deck's best fodder leaves it (Cockroach to hand, Ember to deck).

Played out again with the opossum, Piranha and Hyena: excellent when the engine runs (the opponent's covers feed it), dead when it doesn't (six cards that kill your own, Spiders that die to any cover), and no body bigger than a 4 apart from the Ember. The Tarantula answers both.

Open: the fourth legendary, a Vilgefortz-style crocodile whose two branches are lopsided (eating your own must pay far more than eating an enemy, or you always eat the enemy); proposal: "Roar: remove an adjacent animal of strength 3 or less. If it was yours, your Sleep effects happen now." One rare slot. Rejected: Eon (its eat-your-own job is the opossum's now, it never holds the board, and doubled Sleep makes its drawback worse; it stays in Egg Control); a plain Crocodile (8, Apex) in the open rare (a tempo removal card, not a way to kill your own); a Tarantula that asks for a decision at Sleep (the end of the turn stays automatic); a great crocodile legendary (eating your own to draw 2 is a Skully with extra steps; eating your own to remove an enemy is worse than eating that enemy directly; landing anywhere on your own animals solved no problem the deck has); the Great White Shark (any-strength eat after a death; dropped with the Apex framing, which was an agent's guess, not the deck); the Ostrich as a body (its Egg pays nothing on its own death); a Tarantula that removes your small animals placed next to it (a worse Spider, no fit). Rejected: a Spider Egg (its payoff needs the egg to survive, which this deck works against; a version paying on death is the Earthworm); an unlimited "whenever one of your animals is removed, draw a card" (with the loops, five cards from one action); food for each death (a third food deck); the Opossum as fodder (the Earthworm does more).

Open topics: the bloodsuckers drain strength (Mosquito's −2, Leech's swap, the Tick's effect still to design, likely a slow drain); taking the opponent's food belongs to thieves (Seagull later, the monkeys) and gets its own session. Rejected: a Worm tag with a Mole that grows per removed Worm (forced, and growing in strength is the Snakes' identity).

Opossum (City, R, 2, Marsupial): "Roar: return one of your animals next to this to your hand." A mother gathering her young onto her back; it replays an animal's Roar (Skully, Chipmunk, a removal), a value card for other decks, and the City's seed for the Marsupials' "carrying the young" identity when Australia comes.

## Elsewhere, settled in passing

- Cats, filling the Cougar's slot (the Cougar and its effect wait for Mountains): Caracal (Savanna, C, 6) becomes "Reach 2.", the leap over the front line onto the engines behind it, which every other Cat can only hit when adjacent (at 5 or less the Eagle practically dominates it); Lynx (Forest, C, 6) takes the Caracal's old "Roar: if placed on top of an enemy, draw a card."; Bobcat (Forest, C, 5) joins with the Lynx's old "Roar: if you control another Cat, draw a card."
- Mosquito (City, C, ~1): "Flight. Roar: give an adjacent enemy −2 strength."
- Leech (Jungle, 1): "Roar: swap strength with an adjacent animal." It drains its host: the host shrinks, the leech swells. At 1 it can't cover anything, so it lands only on an empty crossroad or one of your own.
- Hermit Crab (Coast, later): Armor plus something about moving into another's shell; the strength swap went to the Leech, which fits it far better.
