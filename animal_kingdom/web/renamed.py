"""Card ids that changed, old -> new, and how anything written before the change reads in the new ids: players' saved decks
and deck covers (web/profiles.py), saved matches (web/server.py), game logs replayed or played from (web/server.py,
web/replay.py), news (web/news.py). static/cardnums.js SUCCESSOR is the same map for the client (a test keeps them equal).
tools/cards/hq.py rename adds to it."""
from __future__ import annotations

from ..engine.cards import load_cards

CARDS = load_cards()

# A live card's successor in the launch collection (2026-10-16), which takes its place in a player's own deck: the same
# animal under a new id, or the same effect on another animal (Martin, 2026-10-17: "if one card kept the exact effect,
# just changed the animal, then it should get replaced in the deck"; the effect wins when the two disagree, the Jackal).
# An id changed by tools/cards/hq.py rename (ids name the animal, AGENTS.md) goes in front: saved matches follow it too.
RENAMED_IDS = {"pilot_fish": "krill", "octopus_legend": "chameleon_legend", "young_wasp": "young_ant", "queen_wasp": "queen_ant", "black_swan": "swan_legend", "locust": "locust_legend", "fathom": "octopus_legend_2",
               "pestis": "rat_legend_2", "barley": "rat_legend", "clarion": "wolf_legend_3", "lobo": "wolf_legend_2",
               "queen_adira": "lion_legend_4", "king_theron": "lion_legend_3", "princess_lea": "lion_legend_2",
               "prince_leo": "lion_legend", "cuco": "cuckoo_legend", "mocha": "sperm_whale_legend",
               "methuselah": "tortoise_legend", "brutus": "rhinoceros_legend", "arna": "eagle_legend_2",
               "arne": "eagle_legend", "silverback": "gorilla_legend", "aurum": "goose_legend",
               "eon": "anaconda_legend", "scrooge": "chipmunk_legend", "big_gus": "capybara_legend",
               "rusty": "baby_fox_2", "poppy": "baby_fox", "scarlett": "fox_legend", "gale": "falcon_legend",
               "sirocco": "skunk_legend", "roach_king": "cockroach_legend", "ember": "pheasant_legend",
               "falstaff": "bumblebee_legend", "queen_honoria": "bee_legend", "vesper": "hornet_legend",
               "queen_marabunta": "army_ant_legend", "gaboon_viper": "cottonmouth", "alpha": "fox_legend",
               "dire_wolf": "wolf", "goliath": "python", "guard_hornet": "guard_wasp", "omen": "swan_legend",
               "red_wolf": "dhole", "stoop": "hawk", "bulwark": "rhinoceros_legend", "rat_king": "rat_legend",
               "jerboa": "mole", "chinchilla": "beaver", "greywhisker": "mole_legend", "house_cat": "alley_cat",
               "taipan": "cottonmouth", "polar_bear": "crocodile", "gray_wolf": "chimpanzee",
               "snow_leopard": "leopard"}


def renamed(x):
    """`x` (a saved match, a game log, any JSON) with every old id that no card holds any more read as the new one; a
    retired card still in the reserve keeps its own."""
    if isinstance(x, str):
        return RENAMED_IDS[x] if x in RENAMED_IDS and x not in CARDS else x
    if isinstance(x, list):
        return [renamed(v) for v in x]
    if isinstance(x, dict):
        return {renamed(k): renamed(v) for k, v in x.items()}
    return x
