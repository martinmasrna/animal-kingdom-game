# Board Toy 3

Each player owns one row of 5 tiles, facing the other's (Martin, 2026-11-26: "each player owning their own row was the idea"). A unit goes only on an empty tile of your own row. Everything else is Board Toy 1's: Hearthstone mana, 25 cards of Units (health = cost) and Strikes (damage = cost) for both, both open with 3 and the first player skips the first draw.

- A region pays the side whose units in it have more total health; a tie pays nobody. At the end of your turn you gain 1 food for each region that pays you. First to 20 wins.
- Regions are the five columns (your tile and the one facing it). `setRegionShape('block')` in `src/engine.js` makes them the four 2 by 2 blocks instead.

Bot against bot, 100 games each: columns at 20 food, first player 45%, about 11 turns each, no stalls; blocks at 20 food, first player 58%, about 9 turns each. In both, a player's own row is full on about a fifth of turns, and a unit then has nowhere to go.

`node build.mjs` writes `index.html` and `artifact.html`; `node selftest.mjs` plays the bot against a greedy player, a random player and itself.
