# Card Candidates — Consolidated

Single inventory of proposed new cards and unresolved variants. Nothing here is locked.

**2026-07-04:** the "New cover-retaliation legendary" candidate shipped into `aggro_hq_rush` as
**Gale** (card-balance-todo.md, filling the legendary slot Stoop vacated when it moved to
Egg Control) — removed from this list. Vulture (Rare table, below) is shelved out of
`egg_control` the same session; its `config.py` dial (`vulture_food`/`cap_vulture`) and
`effects.py` handler are left dormant, ready if it's re-added to a deck.

- Multiple strengths or effects in one row are competing versions, not combined card text.
- Where a row has numbered variants, multiple STR values correspond in the same order. If the
  text is shared, only the proposed strength differs.
- Candidates with no proposed rarity are marked **rarity TBD** and parked in the Common table
  solely to keep this document to the requested three tables. That placement does not assign
  Common rarity.
- Tokens created by cards are included in effect text but are not listed as separate collectible
  cards.

## Common

| Name | Type / tags | STR | Candidate text / unresolved variants |
|---|---|---:|---|
| **Action-denial unit (name TBD)** | TBD | TBD | Give the opponent −1 action next turn. **Rarity TBD.** |
| **Action-gain unit (name TBD)** | TBD | TBD | Give you +1 action next turn. **Rarity TBD.** |
| **Antivenom Grove** | Landmark | 0 | Fragile. Battlecry: clear Venom from all friendly units and draw 2 cards. Adjacent friendly units cannot become envenomed. |
| **Aphid** | Insect | 1 / 3 | **Variant 1:** Battlecry: gain 2 food. Whenever you place another Colony or Insect unit, gain 2 food.<br>**Variant 2:** Battlecry: gain 4 food. Whenever you play another Colony or Insect unit adjacent to this, gain 2 food. |
| **Barnacle** | — | X | Has the same strength as the unit directly beneath this; if none, STR 0. |
| **Bat-eared Fox** | Canine | 4 | Battlecry: look at the top 3 cards of your deck; draw a Canine and put the rest on the bottom. |
| **Bighorn Sheep** | — | 6 | Immovable. |
| **Bison** | Megafauna | 8 / 9 | **Variant 1:** Costs 10 food to play.<br>**Variant 2:** Costs 5 food to play. |
| **Bloodhound** | Canine | 3 | Battlecry: look at the top 5 cards of your deck; draw a unit of your choice, put the rest on the bottom. |
| **Bonobo** | Primate | 5 | Battlecry: move an adjacent friendly unit to an adjacent empty crossroad. |
| **Capuchin** | Primate | 5 | Battlecry: if adjacent to a Landmark, draw 1 card. |
| **Carcass** | Landmark | 0 | Fragile. Battlecry: gain 8 food. The first time each turn a unit adjacent to this is removed, gain 4 food. |
| **Cardinal** | Bird | 2 | Battlecry: give a Bird in your hand +2 strength. |
| **Carrion Beetle** | Insect | 2 / 4 | **Variant 1:** Whenever a friendly unit is removed, gain 3 food.<br>**Variant 2:** Battlecry: gain 4 food. The first time each turn another friendly unit is removed, gain 4 food. |
| **Caterpillar** | Insect | 1 | After 2 turns, remove this and play a Butterfly token (Insect, STR 4, Flight). |
| **Clownfish** | Fish | 2 / 6 | **Variant 1:** Cannot be targeted by enemy special effects while you control another Fish.<br>**Variant 2:** Has Stealth while adjacent to a friendly Landmark. |
| **Cow** | — | 4 | At the end of your turn, gain 2 food. |
| **Copy/mimic unit (animal TBD)** | Bird / other TBD | TBD | Become a copy of the last Common unit your opponent played. A narrower “repeat its Battlecry” version is also open. Possible identities include Parrot, mockingbird, lyrebird, Mimic Octopus, cuttlefish, or another animal. **Rarity TBD.** |
| **Decoy Egg** | Egg | 0 | Fragile. Deathrattle: draw 3 cards. |
| **Dinosaur Egg** | Egg | 0 | Fragile. Hatch 2 — play a random non-Legendary Dinosaur from your deck on this crossroad. |
| **Dog/Canine identity TBD** | Canine | 3 | Battlecry: give +3 strength to every other copy, wherever they are. |
| **Dormouse** | Rodent | 2 | Immovable. For 2 turns this does nothing; then gain 12 food. |
| **Dung Beetle** | Insect | 2 / 3 | **Variant 1:** Battlecry: gain 4 food. Deathrattle: gain 4 food.<br>**Variant 2:** Battlecry: gain 4 food. Deathrattle: gain 8 food. |
| **Earthworm** | — | 1 | When this is removed by being covered, return two copies of it to your hand. |
| **Echidna** | — | 3 | Cannot be covered by enemy units. Deathrattle: draw 1 card. |
| **Emperor Penguin** | Bird | 7 | Adjacent friendly Eggs cannot be chosen by enemy abilities. |
| **Fallen Log** | Landmark | 0 | Fragile. When this leaves the battlefield, play two Insect tokens (STR 3) on adjacent empty crossroads. **Rarity TBD.** |
| **Fishing Cat** | Cat | 4 | Battlecry: if this is adjacent to a Landmark, draw 1 card. |
| **Fossil Bed** | Landmark | 0 | Fragile. At the start of your next turn, remove this and play a random non-Legendary Dinosaur from your deck on this crossroad. **Rarity TBD.** |
| **Frogspawn** | Egg / Amphibian | 0 | Fragile. Hatch 1 — play two Tadpole tokens (Amphibian, STR 4) on adjacent empty crossroads. |
| **Gecko** | Lizard | 2 / 7 | **Variant 1:** Battlecry: may be placed on any crossroad adjacent to an enemy unit, ignoring connection.<br>**Variant 2:** May be placed on an empty crossroad adjacent to an enemy unit, ignoring connection. |
| **Giraffe** | — | 5 | May cover enemy units of equal strength. |
| **Goshawk** | Bird | 4 | Flight. Battlecry: remove an adjacent enemy of strength 2 or less. |
| **Groundhog** | Rodent | 3 | At the start of your next turn, gain 4 food and draw 1 card. |
| **Hamster** | Rodent | 1 | Battlecry: draw 2 cards, then remove 1 from your hand. |
| **Hare** | Rabbit | 6 | Burrow. |
| **Honeyguide** | Bird | 1 / 3 | Flight. Battlecry: gain 6 food; if you control a Bear or Colony unit, gain 4 more. |
| **Honeypot Ant** | Colony | 2 | Deathrattle: gain 16 food. |
| **Howler Monkey** | Primate | 3 | Battlecry: give all other Primates in your hand and on the battlefield +1 strength. |
| **Ibex** | — | 5 | Battlecry: may be placed adjacent to any friendly unit, ignoring connection. |
| **Kelp Forest** | Landmark | 0 | Fragile. Battlecry: draw a random Fish from your deck, then you may move a friendly Fish to an empty crossroad adjacent to this. Adjacent Fish have Stealth. |
| **Lamprey** | Fish | 2 | Battlecry: attach to an adjacent enemy unit. At the start of each of your turns, gain 2 food and that unit has −1 strength. |
| **Leafcutter Ant** | Colony | 1 / 3 | Battlecry: gain 3 food for each other friendly Colony unit. |
| **Lemur** | Primate | 2 | Battlecry: if you control another Primate, play another Primate from your hand. |
| **Locust** | Insect | X | Strength equals the number of Colony or Insect units you control. |
| **Maggot** | Insect | 0 | Fragile. After 1 turn, remove this and play a Fly token (Insect, STR 2, Flight). |
| **Magpie** | Bird | 2 | Flight. Battlecry: draw 1 card. |
| **Maned Wolf** | Canine | 6 | May be placed on an empty crossroad adjacent to any Canine you control, ignoring connection. |
| **Mantis Ootheca** | Egg / Insect | 0 | Fragile. Hatch 1 — play up to three Mantis Nymph tokens (Insect, STR 2) on adjacent empty crossroads. |
| **Margay** | Cat | 7 | May be placed on an empty crossroad adjacent to any Cat you control, ignoring connection. |
| **Mayfly** | Insect | 3 | **Variant 1:** Deathrattle: draw 1 card. This is removed at the end of your next turn.<br>**Variant 2:** Battlecry: draw 1 card. Deathrattle: draw 1 card. At the end of your next turn, remove this. |
| **Meerkat** | — | 2 | Battlecry: draw 1 card. |
| **Mole** | Rodent | 5 / 6 | Burrow. |
| **Mongoose** | — | 3 / 5 | **Variant 1:** Battlecry: remove an adjacent enemy Snake of any strength; otherwise remove an adjacent enemy of strength 3 or less.<br>**Variant 2:** Battlecry: clear Venom from an adjacent friendly unit; otherwise remove an adjacent enemy Snake of any strength. |
| **Moose** | Megafauna | 6 | Has +2 strength while adjacent to a Landmark. |
| **Mosquito** | Insect | 1 | Battlecry: steal 4 food from the opponent. |
| **Oviraptor** | Dinosaur | 3 | Battlecry: draw a random Egg from your deck. |
| **Pangolin** | — | 3 | Cannot be covered by enemy units. |
| **Pika** | Rabbit | 5 | Battlecry: if played by Burrow, gain 8 food. |
| **Poison Dart Frog** | Amphibian | 4 | Deathrattle: envenom an adjacent enemy. |
| **Prairie Dog** | Rodent | 1 / 3 | Battlecry: play one more Rodent from your hand. |
| **Protoceratops** | Dinosaur | 7 | No effect. |
| **Rabbit** | Rabbit | 3 | At the start of each of your turns, draw a random Rabbit from your deck. |
| **Raccoon Dog** | Canine | 3 | Battlecry: draw 1 card. Deathrattle: shuffle this into your deck. |
| **Remora** | Fish | 1 / 2 | **Variant 1:** Has +X strength, where X is the highest strength among adjacent friendly units.<br>**Variant 2:** Has +6 strength while adjacent to a friendly unit with strength 6 or more. |
| **Rhinoceros Beetle** | Insect | 2 | Has +1 strength for each other friendly Colony or Insect unit. |
| **Roadrunner** | Bird | 3 | Battlecry: remove an adjacent enemy Snake or Lizard of any strength. |
| **Salmon** | Fish | 4 / 5 | **Variant 1:** Battlecry: move this to any crossroad connected to your HQ.<br>**Variant 2:** Battlecry: move another friendly Fish to an empty crossroad connected to your HQ. |
| **Salt Lick** | Landmark | 0 | **Variant 1:** Fragile. Immovable. At the start of your next turn, give all friendly units +1 strength, then remove this.<br>**Variant 2:** Fragile. At the start of your next turn, give all friendly units +2 strength, then remove this. |
| **Sand Cat** | Cat | 5 | Has +3 strength while no other friendly unit is adjacent to this. |
| **Scorpion** | Arachnid | 3 | The first enemy unit that covers this becomes envenomed. |
| **Spider Egg Sac** | Egg / Arachnid | 0 | Fragile. Deathrattle: play two Spiderling tokens (Arachnid, STR 3) on adjacent empty crossroads. |
| **Starfish** | — | 2 | Deathrattle: play two Arm tokens (STR 1) on adjacent empty crossroads. |
| **Starling** | Bird | 2 | Flight. Battlecry: if you control another unit with Flight, play one more unit with Flight from your hand. |
| **Stingray** | Fish | 3 | Deathrattle: remove the unit that removed this. |
| **Stoat** | — | 3 | Battlecry: remove an adjacent enemy of strength 2 or less. |
| **Tapir** | — | 5 | No effect. |
| **Termite Mound** | Landmark | 0 | Fragile. Immovable. Battlecry: draw a random Colony unit from your deck. Adjacent Colony units have +2 strength. |
| **Tool Cache** | Landmark | 0 | Fragile. When you play a Primate adjacent to this, remove this and draw 3 cards. |
| **Trapdoor Spider** | Arachnid | 2 | When an enemy places a unit on an adjacent crossroad, remove it if its strength is 2 or less. |
| **Truffle Pig** | — | 3 | Battlecry: look at the top 4 cards of your deck; draw 1 card and put the rest on the bottom. |
| **Turtle Egg** | Egg | 0 | Fragile. Hatch 1 — play two Turtle Hatchling tokens (STR 4) on this crossroad and an adjacent empty crossroad. |
| **Velociraptor** | Dinosaur | 5 | Battlecry: if an Egg hatched this turn, draw 1 card. |
| **Warthog** | — | 6 | Battlecry: gain 2 food. |

## Rare

| Name | Type / tags | STR | Candidate text / unresolved variants |
|---|---|---:|---|
| **Albatross** | Bird | 5 | Flight. At the end of your turn, gain 3 food. |
| **Anglerfish** | Fish | 5 | Enemy units that are able to cover this must cover this before covering your other units. Has +2 strength while an enemy is adjacent. |
| **Ankylosaurus** | Dinosaur | 8 | Cannot be returned to a hand. |
| **Antlion** | Insect | 2 | At the start of your next turn, remove an adjacent enemy of strength 3 or less. |
| **Archaeopteryx** | Bird / Dinosaur | 4 | Flight. Battlecry: incubate an adjacent Egg. |
| **Axolotl** | Amphibian | 3 / 5 | The first time this would be removed, return it to this crossroad with base strength 1 instead. |
| **Baobab Tree** | Landmark | 0 | **Variant 1:** Fragile. Immovable. At the start of each of your turns, gain 5 food.<br>**Variant 2:** Fragile. Immovable. At the end of each of your turns, gain 8 food. |
| **Beagle** | Canine | 2 | Battlecry: search your deck for a unit of strength 3 or less and put it into your hand. |
| **Beaver** | — | 5 | At the end of your turn, if this is adjacent to a Landmark, gain 5 food. |
| **Blue Jay** | Bird | 2 | Flight. Battlecry: draw 2 cards, then put 1 card from your hand on top of your deck. |
| **Blue-ringed Octopus** | Cephalopod | 3 | Stealth. Battlecry: envenom an adjacent enemy of strength 5 or less. |
| **Bombardier Beetle** | Insect | 2 / 5 | Battlecry: return an adjacent enemy unit of strength 4 or less to its owner's hand. |
| **Box Jellyfish** | — | 2 | Battlecry: lock an adjacent enemy unit—until your next turn it cannot move, be removed, cover, or use its effects. |
| **Bull** | — | 7 | Whenever this gains strength, give an adjacent friendly unit +1 strength. |
| **Bull Shark** | Fish | 7 | Apex Predator. |
| **Burrow Owl** | Bird | 4 | Flight. Your adjacent units with Burrow have +2 strength. |
| **Camel** | — | 6 | Battlecry: gain 12 food. You cannot gain food again until your next turn. |
| **Capybara** | Rodent | 5 | At the end of your turn, gain 1 food for each unit adjacent to this. |
| **Cave** | Landmark | 0 | Fragile. Immovable. Battlecry: draw a random Bear from your deck. Your Bears cost 5 less food to play. |
| **Chimpanzee** | Primate | 4 | Battlecry: give an adjacent friendly unit +3 strength. |
| **Cicada** | Insect | 1 | After 3 turns, this gains +8 strength. |
| **Clouded Leopard** | Cat | 7 | Camouflage. |
| **Cobra** | Snake | 3 | **Variant 1:** Battlecry: poison an adjacent enemy; remove it at the start of your next turn.<br>**Variant 2:** Battlecry: envenom an adjacent enemy. |
| **Coconut Crab** | — | 5 | Cannot be covered by enemy units. |
| **Coral Reef** | Landmark | 0 | **Variant 1:** Fragile. Immovable. Your Fish have +2 strength.<br>**Variant 2:** Fragile. Immovable. Battlecry: draw a random Fish from your deck. Your Fish have +2 strength. |
| **Crocodile Egg** | Egg | 0 | Fragile. Hatch 2 — play a Crocodile token (Lizard, STR 8) on this crossroad. Its Battlecry removes an adjacent enemy of strength 4 or less. |
| **Cuckoo** | Bird | 2 / 3 | **Variant 1:** Flight. Battlecry: if this covers an enemy unit, gain control of the unit beneath it instead of burying it.<br>**Variant 2:** Flight. Battlecry: you may play an Egg from your hand on an empty crossroad adjacent to an enemy unit. |
| **Culpeo** | Canine | 5 | Battlecry: give one Canine in your hand +2 strength. |
| **Cuttlefish** | — | 3 | Adjacent friendly units cannot be targeted by enemy special effects. |
| **Electric Eel** | Fish | 3 / 5 | Battlecry: an adjacent enemy has 0 strength until the end of your next turn. |
| **Ethiopian Wolf** | Canine | 5 | Battlecry: if this has a strength counter while in your hand, draw 1 card. |
| **Fennec Fox** | Canine | 5 | The first time each turn this gains strength, you may move it to an adjacent empty crossroad. |
| **Frigatebird** | Bird | 3 | Flight. Battlecry: steal a random card from the opponent's hand. |
| **Gaur** | Megafauna | 9 | No effect. |
| **Gorilla** | Primate | 6 / 7 | Adjacent enemy units have −2 strength. |
| **Great White Shark** | Fish | 4 / 5 | Has +2 strength for each adjacent enemy unit. |
| **Honey Buzzard** | Bird | 3 | Flight. Battlecry: remove all adjacent enemy Colony or Insect units of any strength; otherwise remove one adjacent enemy of strength 2 or less. |
| **Kangaroo** | Marsupial | 5 / TBD | **Variant 1:** Battlecry: move this or a friendly unit up to 2 crossroads.<br>**Variant 2:** Battlecry: Move 1. Proposed scope: move itself or an ally; exact targeting and destination rules are TBD. |
| **King Cobra** | Snake | 4 | Battlecry: envenom an adjacent enemy unit. |
| **Komodo Dragon** | Lizard | 5 | **Variant 1:** Battlecry: poison an adjacent enemy of any strength; gaining strength cannot save it.<br>**Variant 2:** Battlecry: envenom an adjacent enemy of strength 5 or less. |
| **Malleefowl** | Bird | 5 | At the end of your turn, incubate one adjacent Egg. |
| **Mandrill** | Primate | 5 | Your other Primates have +2 strength. |
| **Musk Ox** | Megafauna | 6 | Has +1 strength for each other unit adjacent to this. |
| **Naked Mole Rat** | Rodent | 2 | Immovable. Cannot be targeted by enemy special effects. |
| **Nesting Ground** | Landmark | 0 | Fragile. Immovable. At the end of your turn, incubate every adjacent Egg. |
| **Ocelot** | Cat | 6 | Battlecry: if this covers an enemy, return one friendly Cat buried beneath it to your hand. |
| **Orangutan** | Primate | 6 | Battlecry: return a Landmark from the Remove Pile to your hand. |
| **Osprey** | Bird | 5 | Flight. Apex Predator. |
| **Ox** | — | 8 | No effect. |
| **Parrot** | Bird | 4 | Flight. Battlecry: reveal the top card of your deck; if it is a Bird, draw it. |
| **Pelican** | Bird | 4 | Flight. Battlecry: remove another friendly unit; draw 2 cards. |
| **Praying Mantis** | Insect | 3 | Battlecry: remove an adjacent enemy of strength equal to or less than this unit's strength. |
| **Python** | Snake | 4 | When this covers a unit, give this +X strength, where X is that unit's strength. |
| **Removal-draw Bird (Vulture / Crow / other identity TBD)** | Bird | 3 | Flight. Battlecry: draw 1 card; if an enemy unit was removed this turn, draw 2 cards instead. |
| **Royal Jelly** | Landmark | 0 | Fragile. At the start of your next turn, remove this and play a random Queen from your deck on this crossroad. |
| **Saltwater Crocodile** | Lizard | 4 | Has +1 strength for each unit buried beneath this. |
| **Secretarybird** | Bird | 4 | Flight. Battlecry: remove an adjacent enemy of strength 4 or less. |
| **Shrike** | Bird | 2 | Flight. Battlecry: remove an adjacent enemy of strength 3 or less; it cannot be returned to a hand or deck. |
| **Springhare** | Rodent | 5 | Burrow. Battlecry: if played adjacent to the opponent's HQ, draw 1 card. |
| **Stick Insect** | Insect | 2 | Cannot be targeted by enemy special effects until it covers an enemy unit. |
| **Tarantula** | Arachnid | 4 | **Variant 1:** Deathrattle: play a Spiderling token (Arachnid, STR 1) on each adjacent empty crossroad.<br>**Variant 2:** Deathrattle: play up to two Spiderling tokens (Arachnid, STR 2) on adjacent empty crossroads. |
| **Tardigrade** | — | 1 | Immovable. Cannot be removed. After 4 turns, gain 30 food. |
| **Tasmanian Devil** | Marsupial | 3 | Adjacent enemy units have −1 strength. |
| **Triceratops** | Dinosaur | 7 | When an enemy covers an adjacent Egg, remove that enemy if its strength is 4 or less. |
| **Vulture** | Bird | 4 | Flight. Whenever a card is removed, gain 5 food. Currently shelved. |
| **Walrus** | — | 8 | Has −1 strength for each empty crossroad adjacent to this. |
| **Warren** | Landmark | 0 | Fragile. At the end of your turn, play a Rabbit token (Rabbit, STR 3) on an adjacent empty crossroad. |
| **Weaver Ant** | Colony | 5 | Battlecry: move an adjacent Colony unit to an adjacent empty crossroad. |
| **Wildebeest** | — | 4 | Battlecry: move a friendly unit to an adjacent crossroad. |
| **Wolverine** | — | 5 | Apex Predator. Cannot be covered by enemy units. |
| **Wombat** | Marsupial | 8 | Burrow. Cannot cover enemy units. |

## Legendary

| Name | Type / tags | STR | Candidate text / unresolved variants |
|---|---|---:|---|
| **Blue Whale — “Sounder”** | Cetacean | 10 | Immovable. Cannot be covered. This cannot cover units or capture an HQ. Costs 15 food to play. |
| **Hachiko, the Faithful** | Canine | 5 | The first time each turn another friendly Canine would be removed, return it to your hand instead. |
| **Kanzi** | Primate | 4 | Battlecry: repeat the Battlecry of another adjacent Primate. |
| **Legendary Parrot (name TBD)** | Bird | TBD | **Variant 1:** Become a copy of the last unit your opponent played.<br>**Variant 2:** Flight. Battlecry: repeat the Battlecry of the last unit your opponent played. |
| **Orca — “Granny”** | Cetacean | 8 | Battlecry: remove an adjacent enemy of any strength. |
| **Sable, the Solitary** | Cat | 5 | At the end of your turn, if no other friendly unit is adjacent to this, draw 1 card. |
| **Scarface** | Cat | TBD | TBD — a Lion legendary; not yet designed. |
| **Sue (Tyrannosaurus rex)** | Dinosaur | 10 / 12 | **Variant 1:** Apex Predator. You may play this only if one of your Eggs has hatched this game.<br>**Variant 2:** Apex Predator. Adjacent enemy units have −2 strength. Costs 20 food to play. |
