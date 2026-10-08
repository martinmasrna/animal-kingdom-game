"""Seed data for the card workbench artifact, transcribed from Martin's deck sheets (2026-10-08).

Writes one JSON file per database document into seed/: decks/<id>.json and habitats/<id>.json.
The artifact's database is the source of truth after seeding; this file is the starting snapshot.
"""
import json
import pathlib

OUT = pathlib.Path(__file__).parent / "seed"

# (rarity, name, species, tag, strength, habitat, text, status)
# species: the animal the card is (for a legendary, the species of the named individual).
DECKS = [
    ("colony", "Colony Food Swarm", [
        ("L", "Queen Marabunta", "Army Ant", "Colony, Queen", 4, "Jungle", "Roar: gain 4 food for each other Colony animal you control.", "locked"),
        ("L", "Vesper", "Hornet", "Colony", 0, "Forest", "Flight. Has +2 strength for each other Colony animal you control.", "locked"),
        ("L", "Queen Honoria", "Bee", "Colony, Queen", 4, "Meadow", "Whenever you play a Colony animal, gain 4 food.", "locked"),
        ("L", "Falstaff", "Bumblebee", "Colony", 3, "Meadow", "Flight. Whenever you gain food, gain 3 additional food.", "locked"),
        ("R", "Nurse Bee", "Bee", "Colony", 3, "Meadow", "Flight. Roar: if you control two of the same Colony animal, draw 2 cards.", "locked"),
        ("R", "Nurse Bumblebee", "Bumblebee", "Colony", 3, "Meadow", "Flight. Roar: if you control 4 or more Colony animals, draw 2 cards.", "locked"),
        ("R", "Termite King", "Termite", "Colony", 6, "Savanna", "Roar: if you control a Colony Queen, draw a card.", "locked"),
        ("R", "Termite Queen", "Termite", "Colony, Queen", 3, "Savanna", "Roar: you may play another non-Queen Colony animal.", "locked"),
        ("C", "Queen Bee", "Bee", "Colony, Queen", 2, "Meadow", "Roar: play a Worker animal.", "locked"),
        ("C", "Guard Wasp", "Wasp", "Colony", 3, "Forest", "Flight. Has +5 strength while you control 4 or more Colony animals.", "locked"),
        ("C", "Soldier Ant", "Army Ant", "Colony", 2, "Jungle", "Roar: if you control 4 or more Colony animals, remove an adjacent enemy.", "locked"),
        ("C", "Worker Ant", "Ant", "Colony, Worker", 1, "Forest", "Roar: gain 12 food.", "locked"),
        ("C", "Worker Wasp", "Wasp", "Colony, Worker", 3, "Forest", "Flight. At the end of your turn, gain 3 food.", "locked"),
        ("C", "Worker Bee", "Bee", "Colony, Worker", 1, "Meadow", "Flight. Roar: gain 10 food; if you control another Worker, gain 10 more.", "locked"),
    ]),
    ("aristocrats", "Aristocrats", [
        ("L", "", "Cuckoo", "", 6, "", "Roar: remove an adjacent animal of strength 4 or less. If it was yours, play another animal.", "locked"),
        ("L", "Ember", "Pheasant", "Bird", 7, "Forest", "Flight. When this is removed, shuffle it into your deck.", "locked"),
        ("L", "", "Opossum", "", 3, "", "When one of your animals is covered, remove it and draw a card.", "locked"),
        ("L", "", "Sloth", "", 4, "Jungle", "Your Dusk effects happen twice.", "locked"),
        ("R", "Praying Mantis", "Praying Mantis", "", 3, "Meadow", "Roar: remove an adjacent friendly animal to draw 2 cards.", "locked"),
        ("R", "Tarantula", "Tarantula", "Arachnid", 5, "Jungle", "Dusk: at random, remove your adjacent friendly animal and gain its strength.", "locked"),
        ("R", "Sea Turtle", "Sea Turtle", "", 5, "Open Ocean", "Dusk: place a Baby Turtle on an adjacent empty crossroad.", "locked"),
        ("R", "Raccoon", "Raccoon", "", 2, "City", "Roar: return an animal from your Remove Pile to your hand.", "locked"),
        ("C", "Piranha", "Piranha", "Fish", 2, "Jungle", "Roar: if one of your animals was removed this turn, remove an adjacent enemy.", "locked"),
        ("C", "Hyena", "Hyena", "", 4, "Savanna", "Dusk: gain 3 food for each of your animals removed this turn.", "locked"),
        ("C", "Vulture", "Vulture", "Bird", 3, "Savanna", "Flight. Dusk: if one of your animals was removed this turn, draw a card.", "locked"),
        ("C", "City Spider", "Spider", "Arachnid", 2, "City", "When an animal of strength 2 or less is placed next to this, remove it.", "locked"),
        ("C", "Earthworm", "Earthworm", "", 1, "Meadow", "When this is removed, place two Worms on its crossroad.", "locked"),
        ("C", "Cockroach", "Cockroach", "", 1, "City", "When this is removed, put it back in your hand and draw a card.", "locked"),
    ]),
    ("canines", "Canine Roam Tempo", [
        ("L", "", "Leopard", "Cat", 7, "Savanna", "Apex Predator. Roam. Reach 2.", "locked"),
        ("L", "Clarion", "Wolf", "Canine", 5, "", "Once each turn, one of your Canines can roam for free.", "locked"),
        ("L", "Lobo", "Wolf", "Canine", 6, "", "Whenever one of your animals roams onto an enemy, draw a card.", "locked"),
        ("L", "", "Wolf", "Canine", 4, "", "Roam. When this roams, your animals next to it gain +2 strength.", "locked"),
        ("R", "Orca", "Orca", "", 7, "Open Ocean", "Apex Predator. Roam.", "locked"),
        ("R", "African Wild Dog", "African Wild Dog", "Canine", 4, "Savanna", "Roam. Whenever this covers an enemy, draw a card.", "locked"),
        ("R", "Jackal", "Jackal", "Canine", 4, "Savanna", "Roar: remove an adjacent enemy that has another of your Canines next to it.", "locked"),
        ("R", "Dhole", "Dhole", "Canine", 6, "Jungle", "Roam. Your animals can roam onto enemies of equal strength.", "locked"),
        ("C", "Wolf", "Wolf", "Canine", 6, "Forest", "Roam.", "locked"),
        ("C", "Bush Dog", "Bush Dog", "Canine", 3, "Jungle", "Roar: give an adjacent Canine +3 strength.", "locked"),
        ("C", "Raccoon Dog", "Raccoon Dog", "Canine", 3, "Forest", "Whenever one of your Canines roams, give it +1 strength.", "locked"),
        ("C", "Fox", "Fox", "Canine", 3, "Forest", "Dusk: give your adjacent animals +1 strength.", "locked"),
        ("C", "Badger", "Badger", "", 4, "Forest", "Roar: draw an animal with Roam.", "locked"),
        ("C", "Stray Dog", "Stray Dog", "Canine", 1, "City", "Roar: give one of your animals with Roam +2 strength. It roams.", "locked"),
    ]),
    ("den-rush", "Aggro Den Rush", [
        ("L", "Greywhisker", "Rat", "Rodent", 1, "City", "Roar: gain 1 food, draw a card, play another animal, then discard a card.", "locked"),
        ("L", "Pestis", "Rat", "Rodent", 3, "City", "Roar: remove an adjacent enemy and every animal buried under it.", "locked"),
        ("L", "Sirocco", "Skunk", "", 5, "Forest", "Roar: return all adjacent enemies to your opponent's hand.", "locked"),
        ("L", "Gale", "Albatross", "Bird", 5, "Open Ocean", "Flight. Roar: draw a card for each animal you control next to the opponent's den.", "locked"),
        ("R", "Naked Mole-Rat", "Naked Mole-Rat", "Rodent", 2, "Savanna", "Roar: play another animal next to this.", "locked"),
        ("R", "Hornet", "Hornet", "Colony", 2, "Forest", "Flight. Roar: discard a Hornet from your hand or deck to remove an adjacent enemy.", "locked"),
        ("R", "Chameleon", "Chameleon", "Lizard", 0, "Jungle", "Can cover animals of any strength.", "locked"),
        ("R", "Skunk", "Skunk", "", 4, "Forest", "Roar: return an adjacent enemy to your opponent's hand. It can't be played next turn.", "locked"),
        ("C", "Hare", "Hare", "Rodent", 3, "Meadow", "Flee. Roar: if you played 3 or more animals this turn, draw a card.", "locked"),
        ("C", "Cheetah", "Cheetah", "Cat", 6, "Savanna", "Roar: if placed next to the opponent's den, draw a card.", "locked"),
        ("C", "Rat", "Rat", "Rodent", 2, "City", "Roar: remove an adjacent enemy, then discard a random card.", "locked"),
        ("C", "Falcon", "Falcon", "Bird", 4, "Forest", "Flight. Roar: if placed next to the opponent's den, draw a card.", "locked"),
        ("C", "Bat", "Bat", "", 3, "City", "Flight. Roar: draw a card.", "locked"),
        ("C", "Mouse", "Mouse", "Rodent", 5, "City", "Roar: draw a Rodent.", "locked"),
    ]),
    ("cats", "Cats Midrange Tempo", [
        ("L", "Prince Leo", "Lion", "Cat", 3, "Savanna", "Battlecry: play Princess Lea from your hand or deck.", "locked"),
        ("L", "Princess Lea", "Lion", "Cat", 3, "Savanna", "Battlecry: play Prince Leo from your hand or deck.", "locked"),
        ("L", "King Theron", "Lion", "Cat", 8, "Savanna", "When one of your Cats covers an enemy unit, remove that enemy.", "locked"),
        ("L", "Queen Adira", "Lion", "Cat", 5, "Savanna", "When one of your Cats removes an enemy unit, draw 1 card.", "locked"),
        ("R", "Jaguar", "Jaguar", "Cat", 5, "Jungle", "Battlecry: remove an adjacent enemy of strength 5 or less.", "locked"),
        ("R", "Serval", "Serval", "Cat", 4, "Savanna", "Battlecry: set an adjacent enemy's strength to 1.", "locked"),
        ("R", "Leopard", "Leopard", "Cat", 6, "Savanna", "Your other Cats may be placed onto enemy units of equal or lower strength.", "locked"),
        ("R", "Black Panther", "Black Panther", "Cat", 6, "Jungle", "Stealth.", "locked"),
        ("C", "Lion", "Lion", "Cat", 7, "Savanna", "", "locked"),
        ("C", "Lynx", "Lynx", "Cat", 6, "Forest", "Roar: if you place this on top of an enemy, draw a card.", "locked"),
        ("C", "Caracal", "Caracal", "Cat", 6, "Savanna", "Reach 2.", "locked"),
        ("C", "Tiger", "Tiger", "Cat", 7, "Jungle", "Apex Predator.", "locked"),
        ("C", "Bobcat", "Bobcat", "Cat", 5, "Forest", "Roar: if you control another Cat, draw 1.", "locked"),
        ("C", "Stray Cat", "Stray Cat", "Cat", 1, "City", "Battlecry: if you control another Cat, play another Cat.", "locked"),
    ]),
    ("fish", "Fish Token Aggro", [
        ("L", "", "Jellyfish", "", 6, "Open Ocean", "Your Fish next to this have Poison.", "locked"),
        ("L", "", "Tuna", "Fish", 5, "Open Ocean", "Roar: for each region you control, draw a card and gain 5 food.", "locked"),
        ("L", "", "Manta Ray", "Fish", 4, "Open Ocean", "Dusk: if you control 2 or more regions, draw a card.", "locked"),
        ("L", "", "Piranha", "Fish", 7, "Jungle", "Your Fish can be placed on enemies with strength up to the number of Fish you control.", "locked"),
        ("R", "Swordfish", "Swordfish", "Fish", 3, "Open Ocean", "Roar: remove a random adjacent enemy for each adjacent friendly Fish.", "locked"),
        ("R", "Barracuda", "Barracuda", "Fish", 4, "Open Ocean", "Roar: remove an adjacent enemy with strength up to the number of your Fish.", "locked"),
        ("R", "Manta Ray", "Manta Ray", "Fish", 6, "Open Ocean", "Whenever your opponent covers one of your Fish, draw a card.", "locked"),
        ("R", "Remora", "Remora", "Fish", 3, "Open Ocean", "Roar: play another Fish.", "locked"),
        ("C", "Cod", "Cod", "Fish", 4, "Open Ocean", "Roar: draw a card for each adjacent friendly Fish.", "locked"),
        ("C", "Sardine", "Sardine", "Fish", 1, "Open Ocean", "Roar: place all Sardines from your hand and deck on random adjacent empty crossroads.", "locked"),
        ("C", "Mahi-mahi", "Mahi-mahi", "Fish", 3, "Open Ocean", "Roar: give your other Fish +1 strength.", "locked"),
        ("C", "Mackerel", "Mackerel", "Fish", 2, "Open Ocean", "Your other Fish have +1 strength.", "locked"),
        ("C", "Tuna", "Tuna", "Fish", 3, "Open Ocean", "Has +1 strength for each other Fish you control.", "locked"),
        ("C", "Sunfish", "Sunfish", "Fish", 4, "Open Ocean", "Roar: place a Baby Fish on an empty crossroad next to this.", "locked"),
    ]),
    ("food-aggro", "Food Aggro", [
        ("L", "", "", "Rodent", 6, "", "Roar: repeat the Roar of each of your adjacent Rodents.", "locked"),
        ("L", "", "", "Rodent", 2, "", "Roar: draw cards until you have as many as your opponent.", "locked"),
        ("L", "Barley", "", "Rodent", 4, "", "Roar: gain 4 food for each other Rodent you control. Draw a card.", "locked"),
        ("L", "Scrooge", "", "Rodent", 4, "", "Roar: gain food equal to the food you gained this turn.", "locked"),
        ("R", "Flying Squirrel", "Flying Squirrel", "Rodent", 3, "Forest", "Flight. Roar: gain 10 food.", "locked"),
        ("R", "Meerkat", "Meerkat", "Rodent", 2, "Savanna", "Roar: draw a card. When an enemy is placed next to this, draw a card.", "locked"),
        ("R", "Chipmunk", "Chipmunk", "Rodent", 4, "Forest", "Roar: next turn, take 1 additional action.", "locked"),
        ("R", "Dormouse", "Dormouse", "Rodent", 3, "Forest", "Dusk: if your hand is empty, gain 10 food.", "locked"),
        ("C", "Squirrel", "Squirrel", "Rodent", 3, "Forest", "Roar: gain 10 food.", "locked"),
        ("C", "Hamster", "Hamster", "Rodent", 1, "Meadow", "Roar: gain 10 food. At the start of your next turn, gain 10 more.", "locked"),
        ("C", "Gopher", "Gopher", "Rodent", 3, "Meadow", "Roar: if you gained 10 or more food this turn, draw 2 cards.", "locked"),
        ("C", "Muskrat", "Muskrat", "Rodent", 2, "Meadow", "Roar: if you gained 10 or more food this turn, remove an adjacent enemy.", "locked"),
        ("C", "Groundhog", "Groundhog", "Rodent", 4, "Meadow", "Roar: if you gained 10 or more food this turn, gain 10 food.", "locked"),
        ("C", "Mole", "Mole", "Rodent", 3, "Meadow", "Roar: gain 5 food. If your hand is empty, draw 2 cards.", "locked"),
    ]),
    ("food-otk", "Food OTK", [
        ("L", "Fathom", "Octopus", "", 7, "Open Ocean", "Roar: Scout a legendary animal.", "locked"),
        ("L", "", "Squirrel", "Rodent", 3, "", "Roar: lose all your food. In 2 turns, gain three times as much.", "locked"),
        ("L", "", "Honey Badger", "", 5, "", "Armor. Stealth. Poison. Spikes.", "locked"),
        ("L", "", "Octopus", "", 3, "Open Ocean", "Roar: this becomes a copy of an adjacent animal.", "locked"),
        ("R", "Capybara", "Capybara", "Rodent", 6, "Jungle", "Your adjacent animals have Armor.", "locked"),
        ("R", "Porcupine", "Porcupine", "Rodent", 7, "Forest", "Spikes.", "locked"),
        ("R", "Golden Orb-Weaver", "Golden Orb-Weaver", "Arachnid", 4, "Jungle", "When an enemy with Flight is placed next to this, remove it.", "locked"),
        ("R", "Armadillo", "Armadillo", "", 7, "Jungle", "Armor. Your adjacent animals have Stealth.", "locked"),
        ("C", "Hedgehog", "Hedgehog", "Rodent", 5, "Meadow", "Spikes. Roar: gain 5 food.", "locked"),
        ("C", "Dart Frog", "Poison Dart Frog", "", 1, "Jungle", "Reach 2. Poison.", "locked"),
        ("C", "Jellyfish", "Jellyfish", "", 4, "Open Ocean", "Poison.", "locked"),
        ("C", "Black Bear", "Black Bear", "Bear", 5, "Forest", "Roar: in 2 turns, draw 2 cards.", "locked"),
        ("C", "Tortoise", "Tortoise", "", 4, "Savanna", "Armor. Roar: gain 5 food for each of your animals with Armor.", "locked"),
        ("C", "Owl", "Owl", "Bird", 2, "Forest", "Flight. Roar: Scout a card.", "locked"),
    ]),
    ("egg-control", "Egg Control", [
        ("L", "Eon", "Snake", "Snake", 10, "Jungle", "Apex Predator. Dusk: shuffle this into your deck with -1 strength.", "locked"),
        ("L", "", "Raven", "Bird", 3, "", "Flight. Roar: put an animal from your opponent's Remove Pile into your hand.", "locked"),
        ("L", "Aurum", "Goose", "Bird", 1, "Meadow", "Dawn: draw a card.", "locked"),
        ("L", "Black Swan", "Swan", "Bird", 3, "Meadow", "Whenever you draw Black Swan, your opponent discards a random card.", "locked"),
        ("R", "Hawk", "Hawk", "Bird", 3, "Forest", "Flight. Roar: remove an adjacent enemy of strength 3 or less.", "locked"),
        ("R", "King Cobra", "King Cobra", "Snake", 4, "Jungle", "Roar: choose an adjacent enemy. At the start of your next turn, remove it.", "locked"),
        ("R", "Magpie", "Magpie", "Bird", 3, "Forest", "Flight. Roar: steal a card from your opponent's hand, then discard a card.", "locked"),
        ("R", "Black Mamba", "Black Mamba", "Snake", 4, "Savanna", "Roar: remove an adjacent enemy of strength 5 or less.", "locked"),
        ("C", "Python", "Python", "Snake", 0, "Jungle", "Has +1 strength for each removed animal.", "locked"),
        ("C", "Egg Eater", "Egg Eater", "Snake", 0, "Savanna", "Has +2 strength for each removed Egg.", "locked"),
        ("C", "Mosquito", "Mosquito", "", 2, "City", "Flight. Roar: give an adjacent enemy -2 strength.", "locked"),
        ("C", "Raven", "Raven", "Bird", 1, "Forest", "Flight. Roar: draw 3 cards, then shuffle 2 cards back.", "locked"),
        ("C", "Bird Egg", "", "Egg", 0, "", "Roar: Scout a Bird. Next turn, remove this and Scout a Bird.", "locked"),
        ("C", "Snake Egg", "", "Egg", 0, "", "Roar: draw a Snake. In 2 turns, remove this and draw 2 Snakes.", "locked"),
    ]),
    ("handlock", "Handlock", [
        ("L", "", "Baboon", "Primate", 5, "Savanna", "Dusk: give 2 random animals in your hand +1 strength.", "locked"),
        ("L", "Silverback", "Gorilla", "Primate", 7, "Jungle", "Roar: give all animals in your hand +2 strength.", "to try"),
        ("L", "", "Butterfly", "", 1, "Jungle", "Whenever this gains strength in your hand, it evolves. (Egg, Caterpillar, Chrysalis, Butterfly, Monarch.)", "to try"),
        ("L", "", "Eagle", "Bird", 2, "", "Flight. Apex Predator. When this enters your hand, add [its mate] to your hand.", "locked"),
        ("R", "Hummingbird", "Hummingbird", "Bird", 1, "Jungle", "Flight. Roar: draw 2 cards.", "locked"),
        ("R", "Macaque", "Macaque", "Primate", 2, "City", "Roar: if you have 5 or more cards in your hand, remove an adjacent enemy.", "locked"),
        ("R", "Orangutan", "Orangutan", "Primate", 5, "Jungle", "Roar: duplicate a Primate in your hand.", "locked"),
        ("R", "Tarsier", "Tarsier", "Primate", 2, "Jungle", "Roar: Scout a Primate and give it +1 strength.", "locked"),
        ("C", "Chimpanzee", "Chimpanzee", "Primate", 4, "Jungle", "Roar: remove an adjacent enemy of equal or lower strength.", "locked"),
        ("C", "Baboon", "Baboon", "Primate", 4, "Savanna", "Roar: give 2 animals in your hand +1 strength.", "locked"),
        ("C", "Stork", "Stork", "Bird", 4, "Meadow", "Flight. Roar: add two random younglings to your hand.", "locked"),
        ("C", "Grizzly Bear", "Grizzly Bear", "Bear", 2, "Forest", "Has +1 strength for each card in your hand.", "locked"),
        ("C", "Caterpillar", "Butterfly", "", 1, "Jungle", "When this gains strength in your hand, draw a card and turn this into a Butterfly.", "locked"),
        ("C", "Gorilla", "Gorilla", "Primate", 6, "Jungle", "Roar: if this has 8 or more strength, draw a card.", "locked"),
    ]),
    ("giants", "Giants", [
        ("L", "Brutus", "Rhinoceros", "Hoofed", 8, "Savanna", "Hungry 6. Roar: remove all adjacent animals.", "locked"),
        ("L", "Methuselah", "Tortoise", "", 3, "Savanna", "Armor. At the end of your turn, gain 5 food.", "locked"),
        ("L", "Mocha", "Sperm Whale", "", 10, "Open Ocean", "Titan. Roar: remove all enemies next to your animals.", "to try"),
        ("L", "", "Oxpecker", "Bird", 4, "Savanna", "Flight. Your Hungry animals next to this don't need to eat.", "locked"),
        ("R", "Rhinoceros", "Rhinoceros", "Hoofed", 8, "Savanna", "Hungry 3. Roar: remove all adjacent enemies of strength 2 or less.", "locked"),
        ("R", "Hippopotamus", "Hippopotamus", "Hoofed", 8, "Savanna", "Hungry 3. When an enemy of strength 3 or less is placed next to this, remove it.", "locked"),
        ("R", "Crocodile", "Crocodile", "", 8, "Savanna", "Apex Predator.", "locked"),
        ("R", "Whale Shark", "Whale Shark", "Fish", 8, "Open Ocean", "Titan. Hungry 4. At the end of your turn, draw 2 cards.", "locked"),
        ("C", "Oxpecker", "Oxpecker", "Bird", 1, "Savanna", "Flight. Roar: gain 1 food for each animal of strength 8 or more in your starting deck.", "locked"),
        ("C", "Anteater", "Giant Anteater", "", 4, "Jungle", "Roar: draw a card. Gain food equal to its strength.", "locked"),
        ("C", "Dung Beetle", "Dung Beetle", "", 1, "Savanna", "At the end of your turn, gain 2 food for each Hungry animal you control.", "locked"),
        ("C", "Blue Whale", "Blue Whale", "", 10, "Open Ocean", "Titan.", "locked"),
        ("C", "Sloth", "Sloth", "", 3, "Jungle", "Roar: in 2 turns, gain 30 food.", "locked"),
        ("C", "Elephant", "Elephant", "", 9, "Savanna", "Hungry 5.", "locked"),
    ]),
    ("hoofed", "Hoofed Graze", [
        ("L", "", "Wildebeest", "Hoofed", 5, "Savanna", "Your regions produce 5 more food.", "locked"),
        ("L", "", "Boar", "Hoofed", 5, "Forest", "Your opponent's regions produce 5 less food.", "locked"),
        ("L", "", "Zebra", "Hoofed", 4, "Savanna", "Roar: draw a card for each different Hoofed animal next to this.", "locked"),
        ("L", "", "Giraffe", "Hoofed", 7, "Savanna", "Your opponent plays with their hand revealed.", "locked"),
        ("R", "Honey Badger", "Honey Badger", "", 2, "Savanna", "Roar: remove an adjacent enemy of strength 6 or more.", "locked"),
        ("R", "Okapi", "Okapi", "Hoofed", 4, "Jungle", "Dusk: if this is grazing, draw a card.", "locked"),
        ("R", "Moose", "Moose", "Hoofed", 6, "Forest", "Your other Hoofed animals have +1 strength during your opponent's turn.", "locked"),
        ("R", "Zebra", "Zebra", "Hoofed", 5, "Savanna", "Flee. When this flees, return the enemy that covered it to its owner's hand.", "locked"),
        ("C", "Giraffe", "Giraffe", "Hoofed", 4, "Savanna", "Has +5 strength during your opponent's turn.", "locked"),
        ("C", "Cape Buffalo", "Cape Buffalo", "Hoofed", 4, "Savanna", "Roar: remove an adjacent enemy covering one of your Hoofed animals.", "locked"),
        ("C", "Gazelle", "Gazelle", "Hoofed", 3, "Savanna", "Flee. Roar: gain 5 food.", "locked"),
        ("C", "Wildebeest", "Wildebeest", "Hoofed", 6, "Savanna", "At the end of your turn, if this is grazing, gain 5 food.", "locked"),
        ("C", "Deer", "Deer", "Hoofed", 4, "Forest", "Flee. Roar: draw a Hoofed animal.", "locked"),
        ("C", "Boar", "Boar", "Hoofed", 5, "Forest", "Has +3 strength while grazing.", "locked"),
    ]),
    ("pool", "Pool, no deck yet", [
        ("R", "Octopus", "Octopus", "", 4, "Open Ocean", "Roar: until your next turn, adjacent enemies lose their keywords and effects.", "locked"),
        ("R", "Great White Shark", "Great White Shark", "Fish", 7, "Open Ocean", "Apex Predator. If an animal was removed this turn, this has Reach 3.", "locked"),
        ("R", "Sperm Whale", "Sperm Whale", "", 8, "Open Ocean", "Titan. Roar: remove all adjacent animals.", "locked"),
        ("R", "Butterfly", "Butterfly", "", 2, "Jungle", "Flight. Roar: draw a card, then give an animal in your hand +1 strength.", "locked"),
        ("R", "Macaw", "Macaw", "Bird", None, "Jungle", "Roar: your next Roar this turn happens twice.", "proposed"),
    ]),
]

# Rosters from docs/design/habitats.md; target = set size (commons, rares, legendaries in 3:2:2).
HABITATS = [
    ("savanna", "Savanna", [18, 12, 12], ["Lion", "Elephant", "Giraffe", "Zebra", "Cheetah", "Wildebeest", "Cape Buffalo", "Warthog", "Ostrich", "African Wild Dog", "Naked Mole-Rat", "Baboon", "Gazelle", "Meerkat", "Oxpecker", "Leopard", "Rhinoceros", "Hippopotamus", "Crocodile", "Hyena", "Honey Badger", "Serval", "Black Mamba", "Termite King", "Termite Queen", "Egg Eater", "Caracal", "Vulture", "Dung Beetle", "Jackal"]),
    ("forest", "Forest", [18, 12, 12], ["Fox", "Wolf", "Grizzly Bear", "Black Bear", "Deer", "Moose", "Boar", "Badger", "Lynx", "Beaver", "Porcupine", "Skunk", "Squirrel", "Chipmunk", "Flying Squirrel", "Woodpecker", "Firefly", "Owl", "Raven", "Hawk", "Eagle", "Falcon", "Magpie", "Salamander", "Viper", "Stag Beetle", "Hornet", "Guard Wasp", "Worker Wasp", "Worker Ant"]),
    ("meadow", "Meadow", [18, 12, 12], ["Hare", "Hedgehog", "Mole", "Weasel", "Hamster", "Groundhog", "Gopher", "Muskrat", "Queen Bee", "Worker Bee", "Nurse Bee", "Nurse Bumblebee", "Butterfly", "Dragonfly", "Ladybird", "Grasshopper", "Praying Mantis", "Pond Skater", "Frog", "Toad", "Snail", "Earthworm", "Tick", "Centipede", "Goose", "Swan", "Duck", "Stork", "Swallow", "Cuckoo"]),
    ("city", "City", [9, 6, 6], ["Rat", "Mouse", "Stray Cat", "Stray Dog", "Raccoon", "Opossum", "Macaque", "Gecko", "Cockroach", "City Spider", "Mosquito", "Bat", "Pigeon", "Sparrow"]),
    ("jungle", "Jungle", [18, 12, 12], ["Jaguar", "Black Panther", "Tiger", "Bush Dog", "Dhole", "Anaconda", "King Cobra", "Python", "Soldier Ant", "Gorilla", "Orangutan", "Chimpanzee", "Sloth", "Capybara", "Giant Anteater", "Tarsier", "Armadillo", "Tapir", "Chameleon", "Poison Dart Frog", "Basilisk", "Iguana", "Golden Orb-Weaver", "Macaw", "Hummingbird", "Peacock", "Piranha", "Electric Eel", "Tarantula", "Leech"]),
    ("open-ocean", "Open Ocean", [15, 10, 10], ["Great White Shark", "Hammerhead", "Whale Shark", "Blue Whale", "Sperm Whale", "Orca", "Dolphin", "Octopus", "Squid", "Jellyfish", "Sea Turtle", "Manta Ray", "Sunfish", "Swordfish", "Albatross"]),
]


def main():
    (OUT / "decks").mkdir(parents=True, exist_ok=True)
    (OUT / "habitats").mkdir(parents=True, exist_ok=True)
    for order, (deck_id, name, rows) in enumerate(DECKS):
        cards = []
        for i, (rarity, card_name, species, tag, strength, habitat, text, status) in enumerate(rows):
            cards.append({
                "id": f"{deck_id}-{i}", "rarity": rarity, "name": card_name, "species": species, "tag": tag,
                "str": strength, "habitat": habitat, "text": text, "status": status, "note": "",
            })
        doc = {"name": name, "order": order, "precon": deck_id != "pool", "cards": cards}
        (OUT / "decks" / f"{deck_id}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1))
    for order, (hab_id, name, target, roster) in enumerate(HABITATS):
        doc = {"name": name, "order": order, "target": {"C": target[0], "R": target[1], "L": target[2]}, "roster": roster, "note": ""}
        (OUT / "habitats" / f"{hab_id}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1))
    print(sum(len(d[2]) for d in DECKS), "cards,", len(HABITATS), "habitats")


if __name__ == "__main__":
    main()
