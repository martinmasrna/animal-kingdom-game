"""The energy prototype's card table: every collectible card's strength (the animal's size, 1 to 10) and energy cost
(1 to 5), with any changed text. build.py turns it into animal_kingdom/data/energy.json.

Strength: Martin's own numbers from the boards win (tools/board/boards/prices.json and strengths.json); the rest follow
his calibration: 1 insects and mouse-sized, 2 small animals (bat, toad, raven, squirrel), 3 hare, owl, fox, 4 hawk, lynx,
tortoise, 5 wolf, eagle, dolphin, 6 leopard, boar, 7 lion, bear, orca, 8 grizzly, giraffe, rhino, 9 elephant, 10 whales.

Cost: value of the body by size (1: .25, 2: .5, 3: 1, 4: 1.75, 5: 2.5, 6: 3.25, 7: 4, 8: 5, 9: 6, 10: 7) plus the effect
(a drawn card 2, 10 food 1, a removal 3 to 4, Flight/Reach/Roam/Armor/Stealth .5, Spikes 1, Poison 1.25), less the 2 the
card itself is worth... Since the swarm test (ENERGY_PLAN.md log) the scale is one higher: value less 1, so the Lion
(7, plain) is 3, a wolf-sized body 2, and only small bodies and light effects cost 1. Where Martin's price pile agrees within the new
economy it is kept; where the energy rules changed a card's worth (draws, capped extra plays, energy grants) the cost
follows the new worth, and build.py lists every such difference.

Each entry: id: (strength, cost) or (strength, cost, {options}). Options: text, kw (keywords), hungry, note.
`None` strength keeps the card's own (dynamic or evolving cards)."""

BENCH = {
    "krill": "its whole text is a Titan discount, and Titan is now only a cost",
    "stick_insect": "the plain Stealth body at its true size (1) does nothing",
}

T = {
    # ---- no family
    "butterfly_legend": (None, 3),
    "earthworm": (1, 1),
    "cockroach": (1, 1),
    "cockroach_legend": (1, 3),
    "mole": (2, 2, {"text": "Roar: play another animal that costs 2 or less next to this."}),
    "mole_legend": (2, 5, {"text": "Roar: draw a card, then play another animal."}),
    "dart_frog": (1, 3),
    "caterpillar": (1, 1),
    "bat_legend": (1, 4),
    "blue_whale": (10, 5, {"text": "", "kw": []}),
    "praying_mantis": (1, 2),
    "locust_legend": (1, 5),
    "chameleon": (1, 4),
    "mosquito": (1, 1),
    "butterfly": (1, 2),
    "bat": (2, 2),
    "meerkat": (2, 3),
    "chameleon_legend": (2, 5),
    "tortoise_legend": (5, 4),
    "sloth": (3, 3),
    "honey_badger": (3, 4),
    "electric_eel": (3, 2, {"text": "Roar: your opponent has only 3 energy next turn."}),
    "raccoon": (3, 3),
    "badger": (3, 2),
    "skunk": (2, 2),
    "octopus_legend_2": (3, 3),
    "octopus": (3, 2),
    "opossum": (2, 1),
    "sloth_legend": (3, 4),
    "hyena": (5, 2),
    "wolverine": (4, 3),
    "toad": (2, 1),
    "skunk_legend": (2, 4),
    "honey_badger_legend": (5, 4),
    "armadillo": (4, 2),
    "hedgehog": (3, 1),
    "jellyfish": (3, 3),
    "dolphin": (5, 3),
    "sea_turtle": (4, 3),
    "orca": (7, 4),
    "tortoise": (4, 1),
    "sperm_whale": (9, 5, {"text": "Hungry 4. Roar: remove all adjacent animals.", "kw": ["Hungry"], "hungry": 4}),
    "rhinoceros_legend": (8, 5),
    "sperm_whale_legend": (10, 5, {"text": "Dusk: remove the strongest adjacent enemy.", "kw": []}),
    "rhinoceros": (8, 5),
    "hippopotamus": (8, 5),
    "crocodile": (7, 4, {"text": "Apex Predator. Armor.", "kw": ["Apex Predator", "Armor"]}),
    "elephant": (9, 4, {"text": "Hungry 3.", "kw": ["Hungry"], "hungry": 3}),
    "elephant_legend": (9, 5),
    # ---- Arachnid
    "city_spider": (1, 2),
    "golden_orb_weaver": (1, 1),
    "tarantula": (2, 2),
    # ---- Bear
    "black_bear": (7, 5),
    "grizzly_bear": (8, 4, {"text": ""}),
    # ---- Beetle
    "hercules_beetle": (1, 3),
    "dung_beetle": (1, 1),
    "stag_beetle": (1, 1),
    "dung_beetle_legend": (None, 4),
    # ---- Bird
    "raven": (2, 3),
    "hummingbird": (1, 1, {"text": "Flight. Roar: gain 2 energy."}),
    "peacock": (None, 1),
    "vulture": (4, 2),
    "owl": (3, 3),
    "oxpecker": (1, 2),
    "raven_legend": (3, 4),
    "magpie": (2, 3),
    "eagle_legend": (5, 4),
    "macaw": (2, 3),
    "cuckoo": (2, 1),
    "woodpecker": (2, 2),
    "falcon": (4, 2),
    "hawk": (4, 4),
    "stork": (3, 3),
    "oxpecker_legend": (1, 2),
    "albatross": (4, 3),
    "falcon_legend": (5, 4),
    "pigeon": (3, 1),
    "eagle": (5, 4),
    "cuckoo_legend": (2, 3, {"text": "Roar: remove an adjacent animal of strength {cuckoo_legend_max} or less. If it was yours, play another animal that costs 2 or less."}),
    "pheasant_legend": (7, 4),
    # ---- Canine
    "coyote": (3, 2),
    "street_dog": (3, 3),
    "wolf_legend_3": (4, 4),
    "fox": (3, 3),
    "jackal": (3, 3),
    "bush_dog": (2, 1),
    "african_wild_dog": (4, 2),
    "dhole": (4, 3),
    "fox_legend": (5, 4),
    "wolf_legend_2": (6, 4),
    "wolf": (5, 2),
    # ---- Cat
    "ocelot": (1, 1, {"text": "Roar: if you control another Cat, play another Cat that costs 2 or less."}),
    "serval": (3, 3),
    "alley_cat": (2, 2),
    "lion_legend": (3, 3),
    "lion_legend_2": (3, 3),
    "leopard_legend": (6, 5),
    "lion_legend_4": (5, 4),
    "lynx": (4, 4),
    "bobcat": (5, 3),
    "cheetah": (5, 2),
    "jaguar": (6, 4),
    "leopard": (6, 4),
    "caracal": (4, 1),
    "black_panther": (6, 3),
    "lion": (7, 3),
    "tiger": (7, 3),
    "tiger_legend": (7, 5),
    "lion_legend_3": (8, 5),
    # ---- Colony
    "bee_legend_2": (1, 5),
    "hornet": (2, 3),
    "hornet_legend": (2, 2),
    "bumblebee_legend": (2, 3),
    "termite_king": (3, 3),
    "nurse_bee": (1, 2),
    "nurse_bumblebee": (1, 2),
    "termite_queen": (3, 2, {"text": "Roar: play a non-Queen Colony animal that costs 2 or less."}),
    "bee_legend": (3, 5),
    "army_ant_legend": (3, 4),
    "queen_bee": (3, 2),
    "queen_ant": (3, 4),
    "soldier_ant": (2, 2),
    "guard_wasp": (2, 1),
    "guard_bee": (2, 1),
    "worker_ant": (1, 1),
    "worker_wasp": (1, 2),
    "worker_bee": (1, 1),
    # ---- Egg
    "bird_egg": (None, 2),
    "snake_egg": (None, 3),
    # ---- Fish
    "sardine": (1, 1),
    "remora": (1, 1, {"text": "Roar: if this is next to an allied Fish, play another Fish that costs 2 or less."}),
    "sardine_legend": (1, 2),
    "piranha_legend": (2, 4),
    "piranha": (2, 3),
    "swordfish": (5, 4),
    "mahi_mahi": (3, 1),
    "tuna": (3, 2),
    "manta_ray_legend": (6, 5),
    "barracuda": (3, 2),
    "cod": (2, 2),
    "sunfish": (5, 2),
    "hammerhead": (6, 3),
    "tuna_legend": (5, 5),
    "manta_ray": (6, 3),
    "great_white_shark": (7, 4),
    "whale_shark": (9, 5, {"text": "Hungry 4. Dusk: draw a card.", "kw": ["Hungry"], "hungry": 4}),
    # ---- Hoofed
    "gazelle": (4, 3),
    "impala": (4, 2),
    "deer_legend_2": (2, 4),
    "deer": (5, 2),
    "deer_legend": (5, 5),
    "zebra_legend": (6, 5),
    "okapi": (6, 5),
    "warthog": (5, 3),
    "wildebeest_legend": (6, 5),
    "boar_legend": (6, 4),
    "zebra": (6, 3),
    "boar": (6, 4),
    "giraffe": (8, 4, {"text": "Hungry 2. Reach.", "kw": ["Hungry", "Reach"], "hungry": 2}),
    "wildebeest": (6, 3),
    "giraffe_legend": (8, 4),
    "cape_buffalo": (7, 4),
    "bison": (7, 4),
    "moose": (8, 3),
    # ---- Primate
    "macaque_legend": (2, 3),
    "macaque": (2, 2),
    "tarsier": (1, 2),
    "baboon_legend": (5, 3),
    "orangutan_legend": (6, 4),
    "chimpanzee": (5, 4),
    "orangutan": (6, 4),
    "baboon": (5, 2),
    "gorilla": (7, 4),
    # ---- Rodent
    "chipmunk": (1, 1),
    "capybara": (3, 3),
    "vole": (1, 1),
    "rat_legend_2": (1, 3),
    "rat": (1, 1),
    "flying_squirrel": (2, 3),
    "dormouse": (1, 3),
    "gopher": (1, 2),
    "groundhog": (2, 2),
    "hamster": (1, 1),
    "squirrel_legend": (2, 3),
    "rodent_legend": (2, 3),
    "marmot": (2, 1),
    "hare": (3, 1),
    "mouse": (1, 2, {"text": "Roar: draw 2 cards."}),
    "rat_legend": (2, 3),
    "chipmunk_legend": (1, 2),
    "squirrel": (2, 1),
    "mara": (3, 3),
    "beaver": (4, 2, {"text": "Roar: next turn, you have 2 more energy."}),
    "porcupine": (4, 3),
    "capybara_legend": (4, 4),
    # ---- Snake
    "python": (None, 1),
    "anaconda_legend": (10, 4),
    "viper": (2, 1),
    "black_mamba": (4, 4),
    "anaconda": (6, 3),
    "egg_eater": (None, 1),
}

# Two cost scales, the same ordering. "lion3": the Lion costs 3, a wolf-sized body 2, small bodies 1: for the rules with
# no limit on animals a turn. "lion2": the Lion costs 2, anything below it 1 (Martin's price piles almost as they were):
# for the rules that place at most two animals a turn, where a cheap body cannot swarm. T above holds lion3.
SCALE = "lion3"
COST_LION2 = {
    "butterfly_legend": 3, "earthworm": 1, "cockroach": 1, "cockroach_legend": 3, "mole": 1, "mole_legend": 5, "dart_frog": 2, "caterpillar": 1, "bat_legend": 4, "blue_whale": 5, "praying_mantis": 1, "locust_legend": 5, "chameleon": 3, "mosquito": 1, "butterfly": 1, "bat": 1, "meerkat": 2, "chameleon_legend": 4, "tortoise_legend": 3, "sloth": 2, "honey_badger": 3, "electric_eel": 2, "raccoon": 2, "badger": 1, "skunk": 2, "octopus_legend_2": 2, "octopus": 1, "opossum": 1, "sloth_legend": 3, "hyena": 1, "wolverine": 2, "toad": 1, "skunk_legend": 3, "honey_badger_legend": 4, "armadillo": 2, "hedgehog": 1, "jellyfish": 2, "dolphin": 2, "sea_turtle": 2, "orca": 4, "tortoise": 1, "sperm_whale": 5, "rhinoceros_legend": 5, "sperm_whale_legend": 5, "rhinoceros": 4, "hippopotamus": 4, "crocodile": 3, "elephant": 4, "elephant_legend": 5, "city_spider": 2, "golden_orb_weaver": 1, "tarantula": 2, "black_bear": 4, "grizzly_bear": 3, "hercules_beetle": 3, "dung_beetle": 1, "stag_beetle": 1, "dung_beetle_legend": 3, "raven": 2, "hummingbird": 1, "peacock": 1, "vulture": 1, "owl": 2, "oxpecker": 1, "raven_legend": 3, "magpie": 2, "eagle_legend": 3, "macaw": 2, "cuckoo": 1, "woodpecker": 2, "falcon": 2, "hawk": 3, "stork": 2, "oxpecker_legend": 2, "albatross": 3, "falcon_legend": 3, "pigeon": 1, "eagle": 3, "cuckoo_legend": 3, "pheasant_legend": 3, "coyote": 1, "street_dog": 2, "wolf_legend_3": 4, "fox": 2, "jackal": 2, "bush_dog": 1, "african_wild_dog": 1, "dhole": 2, "fox_legend": 4, "wolf_legend_2": 4, "wolf": 1, "ocelot": 1, "serval": 3, "alley_cat": 2, "lion_legend": 3, "lion_legend_2": 3, "leopard_legend": 5, "lion_legend_4": 4, "lynx": 3, "bobcat": 2, "cheetah": 1, "jaguar": 3, "leopard": 3, "caracal": 1, "black_panther": 2, "lion": 2, "tiger": 2, "tiger_legend": 5, "lion_legend_3": 5, "bee_legend_2": 5, "hornet": 2, "hornet_legend": 2, "bumblebee_legend": 3, "termite_king": 2, "nurse_bee": 1, "nurse_bumblebee": 1, "termite_queen": 1, "bee_legend": 4, "army_ant_legend": 4, "queen_bee": 1, "queen_ant": 3, "soldier_ant": 1, "guard_wasp": 1, "guard_bee": 1, "worker_ant": 1, "worker_wasp": 2, "worker_bee": 1, "bird_egg": 1, "snake_egg": 2, "sardine": 1, "remora": 1, "sardine_legend": 2, "piranha_legend": 3, "piranha": 2, "swordfish": 3, "mahi_mahi": 1, "tuna": 1, "manta_ray_legend": 4, "barracuda": 1, "cod": 1, "sunfish": 1, "hammerhead": 2, "tuna_legend": 4, "manta_ray": 2, "great_white_shark": 3, "whale_shark": 5, "gazelle": 2, "impala": 1, "deer_legend_2": 4, "deer": 2, "deer_legend": 4, "zebra_legend": 4, "okapi": 4, "warthog": 2, "wildebeest_legend": 4, "boar_legend": 3, "zebra": 2, "boar": 3, "giraffe": 4, "wildebeest": 2, "giraffe_legend": 4, "cape_buffalo": 3, "bison": 3, "moose": 3, "macaque_legend": 3, "macaque": 1, "tarsier": 1, "baboon_legend": 3, "orangutan_legend": 3, "chimpanzee": 3, "orangutan": 3, "baboon": 2, "gorilla": 3, "chipmunk": 1, "capybara": 2, "vole": 1, "rat_legend_2": 3, "rat": 1, "flying_squirrel": 2, "dormouse": 3, "gopher": 1, "groundhog": 2, "hamster": 1, "squirrel_legend": 3, "rodent_legend": 2, "marmot": 1, "hare": 1, "mouse": 2, "rat_legend": 2, "chipmunk_legend": 2, "squirrel": 1, "mara": 2, "beaver": 2, "porcupine": 2, "capybara_legend": 3, "python": 1, "anaconda_legend": 4, "viper": 1, "black_mamba": 3, "anaconda": 2, "egg_eater": 1
}

# Tokens played from the hand: what they cost (the rest cost 1; an effect that puts a token on the board is free).
TOKEN_COST = {"eagle_legend_2": 4, "young_stag": 2, "great_stag": 4}

# Martin's hand-set strengths this table must match exactly (checked by build.py against the boards).
# The rule numbers of the prototype (Config overrides).
RULES = {
    "energy_mode": True, "actions_per_turn": 6, "first_turn_actions": 3, "draw_action_count": 1, "draw_cost": 2,
    "roam_cost": 2, "extra_play_max_cost": 2, "max_places_per_turn": 2, "titan_discount": 2, "beaver_bonus_actions": 2, "eel_actions": 3,
    "crocodile_penalty": 0, "giraffe_bonus": 0, "grizzly_opp_draw": 0, "mouse_draw_any": 2, "hummingbird_energy": 2,
    "mole_legend_discard": False, "mole_legend_play_max": 5,
}

# Strength thresholds printed on cards: config field -> (kind, card id). build.py shifts each so the card hits about the
# same share of the pool at the new sizes as it did at the old ones.
THRESHOLDS = {
    "albatross_max": ("max", "albatross"), "elephant_legend_max": ("max", "elephant_legend"), "jaguar_max": ("max", "jaguar"),
    "honey_badger_min": ("min", "honey_badger"), "stoop_max": ("max", "hawk"), "rhinoceros_max": ("max", "rhinoceros"),
    "hippopotamus_max": ("max", "hippopotamus"), "cuckoo_legend_max": ("max", "cuckoo_legend"),
    "tiger_legend_max": ("max", "tiger_legend"), "black_mamba_max": ("max", "black_mamba"),
    "oxpecker_legend_min": ("min", "oxpecker_legend"),
}
# Not shifted: the small-deck line (Capybara, Juliette) stays "no animal of strength 4 or more": hare-sized and below.
