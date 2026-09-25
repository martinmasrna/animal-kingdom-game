# The seven premade decks

Every deck is 30 cards in the 4-4-6 shape: 4 legendary designs ×1, 4 rare ×2, 6 common ×3 (a few cards override their copy count). `animal_kingdom/data/cards.json` is the source of truth for every card; each deck doc's card table is generated from it (`.venv/bin/python -m animal_kingdom.render.deck_docs`) and a test fails when one goes stale. Edit the prose by hand, never the tables.

| Deck | Identity |
|---|---|
| [Cats Midrange](cats-midrange.md) | mono-Cat tempo and removal |
| [Aggro HQ Rush](aggro-hq-rush.md) | cheap chains and reach to capture the HQ (being redesigned) |
| [Canine Buff Tempo](canine-buff-tempo.md) | mono-Canine persistent buffs and pack reach |
| [Colony Food Swarm](colony-food-swarm.md) | mono-Colony swarm converted into food |
| [Egg Control](egg-control.md) | Snake/Bird/Egg draw-shuffle-remove engine that pays food |
| [Food OTK](food-otk.md) | Rodent food burst in one turn |
| [Ramp](ramp.md) | build food, then deploy huge food-costed bodies |

Legendary names outside Cats are provisional; the flavor audit and alternates are in [`flavor-review.md`](flavor-review.md) and [`../flavor-todo.md`](../flavor-todo.md).
