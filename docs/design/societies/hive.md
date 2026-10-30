# The hive

The second society page, 2026-10-24, to the form in `knowledge/world-first-study-2026-10-24.md` (section 6): observed nature written down, so the playstyle the society's cards serve, their effects, the art and the names read from one source. The hive is the first invented society: bees, bumblebees, wasps, hornets, ants and termites never live together, but they all live the same way, one mother and her thousands of daughters divided by job, and their cards all play the same way, numbers into food. That is the unit (study, section 5), and this page is its test. Lines 1 to 3 and 5 are written from nature and would read the same with no cards; section 4 is the bridge, one role per section with the cards that play it generated under it from `cards.json`, and a role with no card is an open slot. Line 5 is the one invented thing and is a proposal for Martin. Nothing here is settled.

## 1. What they are

The insects that live as one family under a queen: honeybees, bumblebees, wasps, hornets, ants, termites. One nest, one mother, thousands of sisters, each born to a job. None of them matters alone; together they are the most numerous animals on earth and they outlive their enemies by making more of themselves than can be killed.

## 2. How they live

- One mother, everyone else her daughters. The queen lays; the workers are her children and lay nothing. The nest is one family, and the family is the animal.
- Everyone has a job, and the job is the body. Workers forage, nurses feed the brood, guards stand at the door and smell who comes in, soldiers fight; an ant's job changes with age, from nursing inside to foraging outside. A soldier is built bigger, a queen is built to lay, a worker to carry.
- The queen is the colony. Kill her and it dies slowly, unless the nurses raise a new one: any young larva fed royal jelly becomes a queen. The nurses, not the queen, decide who rules next.
- Food is the whole point. Bees turn a summer of flowers into honey to live through winter; ants farm aphids and grow fungus; termites eat wood that nothing else can digest. A nest stores far more than it can eat.
- They tell each other where the food is. A bee dances the distance and direction to the flowers on the comb; an ant lays a scent trail and a hundred follow it; one alarm smell brings every guard to the door.
- Numbers are the weapon. One sting kills the bee that gave it and does nothing; a thousand kill a bear. Honeybees kill a hornet by balling it and cooking it with their own heat. Army ants march in a column and eat everything in their path.
- Nobody gives orders. No bee commands another; the nest decides by how many are doing a thing, and a few scouts dancing hard enough move the whole swarm.
- When the nest is full, it splits. The old queen leaves with half the workers to found a new one and a daughter takes the comb; a termite king and queen fly out together once and never fly again, and their mound lives for decades. The termite king is the only king among insects: he stays with his queen for life.
- They defend the door, not the field. A forager far from the nest is lost without a fight; the fight is at the entrance, where the guards are.
- Hornets raid hives and carry the brood home to feed their own; bumblebees live in small nests that die in autumn, one mated queen sleeping alone through winter to begin again.

## 3. The playstyle the hive's cards serve

The colony is one animal (Martin, 2026-10-24). Three things follow, and a hive card does at least one of them:

- **The queen lays.** The colony makes its own bodies: a queen on the board puts workers down without the player spending actions to go and find them. This is the hive's numbers, and the thing no other society can do; the rodents are many because the player played many.
- **The workers feed the whole.** A worker's food is worth what the colony around her is worth, not a flat number per card: more of them together, more food. A flat sack of grain is a rat.
- **Nothing alone, and the queen is the single point of failure.** The payoffs (the guards' strength, the soldiers' removal, the nurses' cards) need the colony standing, four or more, a queen on the board; kill the queen and the colony dies. This is the character, and it is also the weakness that makes the hive lose to a swept board, which is right.

It wins on food through numbers, not through the den, and it loses when the board is cleared before the colony stands.

Not every hive card needs the colony (Martin, 2026-10-24). A society's cards are a mix: some work only with the colony around them (the guards, the soldiers, the nurses), and some are hive animals whose effect travels into any deck that wants it, the way the Hornet's removal and Lord Bumbleton's food multiplier do; those are the cards a player slots into another deck, and a society with none of them is a walled garden, all its cards or none, which is bad deckbuilding. Today the precon has almost no travellers: every card but the Hornet carries a colony-shaped condition, so none leaves the deck and only the Hornet enters it. The test for a traveller is that its condition is one another deck meets for its own reasons (food gained, Flight, its own copies), never "if you control another Colony animal", which is the precon in disguise. What makes a hive card a hive card is the animal and that its effect reads as something the hive does; a flat sack of food on a worker reads as a rodent, and that, not travelling, is the problem with the flat workers.

## 4. Who does what

One section per job the nest gives. Under each, the cards that play it; a heading with no cards is a job the game doesn't have yet. New cards are castes of the species already here: the hive splits its species by caste, never by subspecies.

### The queen

The one the colony is for. She lays, and everyone else exists to feed her brood.

<!-- cards:begin ids=queen_bee,termite_queen,bee_legend,army_ant_legend,queen_ant (generated from cards.json by animal_kingdom.render.deck_docs) -->

| Card | Rarity | Str | Text | Habitat |
|---|---|---:|---|---|
| **Queen Melissia** | legendary | 2 | Roar: draw a Worker, a Soldier and a Nurse Colony animal. | Meadow |
| **Queen Solenia** | legendary | 3 | Dusk: gain 2 food for each animal you control. | Jungle |
| **Queen Ant** | rare | 5 | Dusk: place a Young Ant on an adjacent empty crossroad. | Forest |
| **Queen Bee** | rare | 5 | Roar: add a Worker Bee, Soldier Bee or Nurse Bee to your hand. | Meadow |
| **Termite Queen** | rare | 2 | Roar: play a non-Queen Colony animal. | Savanna |

<!-- cards:end -->

### The workers

The daughters who carry: nectar, seeds, wood, whatever the nest eats. More of them, more food.

<!-- cards:begin ids=worker_bee,worker_ant,worker_wasp,forager_ant (generated from cards.json by animal_kingdom.render.deck_docs) -->

| Card | Rarity | Str | Text | Habitat |
|---|---|---:|---|---|
| **Worker Ant** | common | 2 | Roar: gain 3 food for each animal you control. | Forest |
| **Worker Bee** | common | 2 | Flight. Roar: gain 12 food. | Meadow |
| **Worker Wasp** | common | 2 | Flight. Whenever you place a Colony animal, gain 3 food. | Forest |
| **Forager Ant (reserve)** | common | 1 | Roar: gain 5 food. If you gained 10 or more food this turn, draw a card. | Forest |

<!-- cards:end -->

### The nurses

The ones inside who feed the brood and decide, with royal jelly, which larva becomes a queen.

<!-- cards:begin ids=nurse_bee,nurse_bumblebee (generated from cards.json by animal_kingdom.render.deck_docs) -->

| Card | Rarity | Str | Text | Habitat |
|---|---|---:|---|---|
| **Nurse Bee** | common | 2 | Flight. Roar: if you control 4 or more Colony animals, draw 2 cards. | Meadow |
| **Nurse Bumblebee** | common | 3 | Flight. Roar: draw a Colony animal. | Meadow |

<!-- cards:end -->

### The guards and soldiers

The ones at the door and the ones built to fight. Nothing alone; everything in numbers.

<!-- cards:begin ids=guard_wasp,guard_bee,soldier_ant,hornet,hornet_legend (generated from cards.json by animal_kingdom.render.deck_docs) -->

| Card | Rarity | Str | Text | Habitat |
|---|---|---:|---|---|
| **Vesper** | legendary | 3 | Flight. When an enemy covers a Colony ally, place Vesper on top of it from your hand or deck. | Forest |
| **Hornet** | rare | 2 | Flight. Roar: discard a Hornet from your hand or deck to remove an adjacent enemy. | Forest |
| **Soldier Ant** | common | 2 | Roar: if you control 4 or more Colony animals, remove an adjacent enemy. | Jungle |
| **Soldier Bee** | common | 3 | Flight. Spikes. | Meadow |
| **Soldier Wasp** | common | 3 | Flight. Has +3 strength while you control 4 or more Colony animals. | Forest |

<!-- cards:end -->

### The king

The termite king, the one insect king: he stays beside his queen for life and is nothing without her.

<!-- cards:begin ids=termite_king (generated from cards.json by animal_kingdom.render.deck_docs) -->

| Card | Rarity | Str | Text | Habitat |
|---|---|---:|---|---|
| **Termite King** | rare | 5 | Roar: draw a card for each Colony Queen you control. | Savanna |

<!-- cards:end -->

### The store

The honey, the granary, the fungus garden: a summer's work kept against the winter, more than the nest can eat.

<!-- cards:begin ids=bumblebee_legend (generated from cards.json by animal_kingdom.render.deck_docs) -->

| Card | Rarity | Str | Text | Habitat |
|---|---|---:|---|---|
| **Lord Bumbleton** | legendary | 3 | Flight. Whenever you gain food, gain 3 additional food. | Meadow |

<!-- cards:end -->

### The scouts

The ones who fly out alone, find the flowers, and come back to dance the way.

<!-- cards:begin ids=scout_bee (generated from cards.json by animal_kingdom.render.deck_docs) -->

| Card | Rarity | Str | Text | Habitat |
|---|---|---:|---|---|
| **[SCOUT BEE] (reserve)** | legendary | 3 | Flight. Dusk: if you gained 20 or more food this turn, draw a card. | Meadow |

<!-- cards:end -->

### The trail

The scent one ant lays that a hundred follow; the alarm smell that brings every guard to the door.

<!-- cards:begin ids= (generated from cards.json by animal_kingdom.render.deck_docs) -->
<!-- cards:end -->

### The swarm

The nest splitting when it is full: the old queen leaving with half the workers to begin again.

<!-- cards:begin ids= (generated from cards.json by animal_kingdom.render.deck_docs) -->
<!-- cards:end -->

### The ball

A hornet at the door, and a hundred bees on it, cooking it with their own heat.

<!-- cards:begin ids= (generated from cards.json by animal_kingdom.render.deck_docs) -->
<!-- cards:end -->

### Unplaced

Cards of the hive whose job the page can't yet name.

<!-- cards:begin ids=bee_legend_2 (generated from cards.json by animal_kingdom.render.deck_docs) -->

| Card | Rarity | Str | Text | Habitat |
|---|---|---:|---|---|
| **[BEE]** | legendary | 1 | Roar: if your starting deck has no animals of strength 4 or more, give your animals +2 strength (wherever they are). | Meadow |

<!-- cards:end -->

## 5. Who names whom (proposal)

A worker has no name. There are forty thousand of her, she lives six weeks, and the nest does not tell her from her sister; a named worker would be a lie about what she is. The hive names its court and nothing else: the queen, and the few who stand beside her.

The names already on the cards read as one court, and the proposal is to keep that court as the hive's register. A queen carries a given name in the old register, a word the ear hears as a name and not a word (Melissia, from the Greek for bee; Solenia, from the army ant's Latin). A lord is named by his place (Bumbleton). The sworn sword by one word (Vesper, the evening, when hornets hunt). Places local and given names classical, as in every real court, so the mix is no seam; the comedy was Bumbleton's alone and belongs to the bumblebee, a fat nest that dies in autumn, not to the register.

The hive's words: the comb, the wax, the honey, the flowers by name, the sun (bees steer by it), the dance, the swarm, the door, the brood, the winter. Words the hive cannot know: the ground's animals' things (no claws, no dens, no herds), meat for the bees (the hornets and the wasps know it), the sea, snow.

Who speaks a hive name: the nest itself, about its own queen, the way a people names its ruler. The hive's enemies, the bear and the hornet, have no word for any of them, since to a bear a hive is a thing, not a someone. So a hive name never comes from outside.

## 6. Ledger

Names on the cards: Queen Melissia (honeybee), Queen Solenia (army ant), Lord Bumbleton (bumblebee), Vesper (hornet). Open: the unplaced bee legendary and the scout bee (reserve); both are court or caste names by this page's rule.

Legends that read from this page: none written yet.

Not of the hive, for the next pages: the praying mantis and the stick insect (loners), the butterfly and its stages, the locust swarm (The First of Many: a swarm has no queen and no jobs; it belongs with the scavengers' plague or with nobody), the earthworm, the spiders. The naked mole-rat (reserve, Savanna) is the one mammal that lives as a hive and would belong here the day its card plays that way.
