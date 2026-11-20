"""What the web tests share: a legal deck, as a player's deck spec and registered under a slug."""

from animal_kingdom.decks import register_deck

LIST = [f"wisp_{n}" for n in range(1, 11) for _ in range(2)] + ["scout_2", "scout_2", "spiky_3", "spiky_3", "warlord_legend"]
DECK = {"name": "Wisps", "list": LIST, "leader": "warlord_legend"}
SLUG = "test_wisps"
register_deck(SLUG, LIST, "warlord_legend")
