# The starter decks

Every deck is 30 cards in the 4-4-6 shape: 4 legendary designs ×1, 4 rare ×2, 6 common ×3. `tools/card-workbench/decks.json` (converted into `animal_kingdom/data/cards.json` by `tools/card-workbench/convert.py`) is the source of truth for every card; each deck doc's card table is generated from cards.json (`.venv/bin/python -m animal_kingdom.render.deck_docs`) and a test fails when one goes stale. Edit the prose by hand, never the tables.

| Deck |
|---|
| [Colony](colony.md) |
| [Aristocrats](aristocrats.md) |
| [Canine Roam Tempo](canines.md) |
| [Aggro Den Rush](den-rush.md) |
| [Cats](cats.md) |
| [Fish](fish.md) |
| [Rodents](food-aggro.md) |
| [Food OTK](food-otk.md) |
| [Birds & Snakes](egg-control.md) |
| [Primates](handlock.md) |
| [Giants](giants.md) |
| [Hoofed](hoofed.md) |
