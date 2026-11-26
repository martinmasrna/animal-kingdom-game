# Board Toy 2

Board Toy 1 with food from regions instead of bodies. A region is any 2 by 2 block of tiles: nine of them, overlapping, so a centre tile is in four, an edge tile in two, a corner in one. At the end of your turn you gain 1 food for each region that pays you. Everything else is Toy 1's.

`REGION_RULE` in `src/engine.js` picks which side a region pays:

- `full`: the side holding all four tiles (today's game). Bot against bot, 55 to 77% of games stall to the turn limit whatever the bot's weights: building a region takes four cards, one enemy unit inside blocks it for good until a strike removes it, so neither side completes one. Covering is what makes this rule work in the game, where one stronger card retakes a blocked tile.
- `count`: the side with more units in it. No stalls; first player about 55%.
- `power`: the side with more total health in it. No stalls; size and chip damage matter; first player 61 to 71%.

`node build.mjs` writes `index.html` and `artifact.html`; `node selftest.mjs` plays the bot against a greedy player, a random player and itself.
