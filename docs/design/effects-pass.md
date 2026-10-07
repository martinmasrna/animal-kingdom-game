# Effects pass

Each launch animal's card, settled habitat by habitat with Martin. Existing cards keep their effect unless noted. Strengths of existing cards wait for the strength-realism pass; numbers marked ~ are first guesses.

Keywords proposed in this pass: **Hungry N** (at the start of your turn, eat N food; if you can't, this gets −N strength), **Flee** (when an enemy covers this, return it to your hand), **Reach N** (lands up to N crossroads from your connected units; [`../rules/keywords.md`](../rules/keywords.md)), and grazing as a condition (an animal grazes while it's a corner of a region you control; card wording still to choose between "if this is grazing" and "if this controls a region").

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

The combo deck from `families.md`: your own animals die on purpose and every death pays. It wins on the board (growing payoffs, predators eating enemies), not on food, which keeps it apart from both food decks. Every piece of fodder pays on its own death; the payoffs multiply that. Each loop costs a placement, so two actions a turn bound it; any future "play another animal" effect needs an audit against these loops.

| Card | Role | Habitat | Rarity | Str | Text |
|---|---|---|---|---:|---|
| City Spider (Arachnid) | engine | City | C | 2 | When an animal of strength 2 or less is placed next to this, remove it. (Both sides: a trap for the opponent's small animals and tokens, a repeatable death for yours.) |
| Anaconda | engine | Jungle | C | | Apex Predator. (exists) |
| Crocodile | engine | Savanna | R | 8 | Apex Predator. (locked) |
| Praying Mantis | engine | Meadow | R | 3 | Roar: remove one of your animals next to this. If you do, draw 2 cards. |
| Cockroach | fodder | City | C | 1 | When this is removed, return it to your hand and draw a card. |
| Earthworm | fodder | Meadow | C | 1 | When this is removed, place two Worms on its crossroad. (Worm, token, 0: "When this is removed, draw a card.") |
| Ostrich | fodder | Savanna | C | 4 | Roar: place an Ostrich Egg (0) on an adjacent empty crossroad. (locked; the Egg feeds the Egg Eater) |
| Python | payoff: strength, board-wide | Jungle | C | | Has +1 strength for each removed animal. (exists) |
| Egg Eater | payoff: strength from Eggs | Savanna | C | | Has +2 strength for each removed Egg. (exists) |
| Piranha | payoff: strength, local | Jungle | C | 2 | Whenever an animal next to this is removed, give this +2 strength. (the feeding frenzy) |
| Great White Shark | payoff: removal | Open Ocean | R | 7 | Apex Predator. If an animal was removed this turn, this can be placed on an animal of any strength. (smells blood; at 7 it is worse than the Crocodile with no death, better after one) |
| Raccoon | payoff: recursion | City | R | 2 | Roar: return one of your removed animals to your hand. (Only your own: the Remove Pile is shared, and taking the opponent's best card would be legendary-level.) |
| the great crocodile (legendary, name to come) | payoff: cards | Savanna | L | 9 | Apex Predator. When this eats one of your animals, draw 2 cards. |

Open: the other three legendaries (Eon fits); the Tarantula (Jungle, Arachnid) as a Goliath birdeater, "Apex Predator. Can land on animals with Flight of any strength.", or its slot stays open (a second anti-flyer card in a small family). Rejected: a Spider Egg (its payoff needs the egg to survive, which this deck works against; a version paying on death is the Earthworm); an unlimited "whenever one of your animals is removed, draw a card" (with the loops, five cards from one action); food for each death (a third food deck); the Opossum as fodder (the Earthworm does more).

Opossum (City, R, 2, Marsupial): "Roar: return one of your animals next to this to your hand." A mother gathering her young onto her back; it replays an animal's Roar (Skully, Chipmunk, a removal), a value card for other decks, and the City's seed for the Marsupials' "carrying the young" identity when Australia comes.

## Elsewhere, settled in passing

- Cats, filling the Cougar's slot (the Cougar and its effect wait for Mountains): Caracal (Savanna, C, 6) becomes "Reach 2.", the leap over the front line onto the engines behind it, which every other Cat can only hit when adjacent (at 5 or less the Eagle practically dominates it); Lynx (Forest, C, 6) takes the Caracal's old "Roar: if placed on top of an enemy, draw a card."; Bobcat (Forest, C, 5) joins with the Lynx's old "Roar: if you control another Cat, draw a card."
- Mosquito (City, C, ~1): "Flight. Roar: give an adjacent enemy −2 strength."
- Leech (Jungle, 1): "Roar: swap strength with an adjacent animal." It drains its host: the host shrinks, the leech swells. At 1 it can't cover anything, so it lands only on an empty crossroad or one of your own.
- Hermit Crab (Coast, later): Armor plus something about moving into another's shell; the strength swap went to the Leech, which fits it far better.
