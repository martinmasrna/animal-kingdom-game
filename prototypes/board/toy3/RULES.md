# Board Toy 3

Each player owns one row of 5 tiles, facing the other's (Martin, 2026-11-26: "each player owning their own row was the idea"). A unit goes on a tile of your own row: an empty one, or one holding your own unit, which it replaces at any strength (as landing on your own unit does in the game; Martin, 2026-11-26: "you should for sure be able to play units on top of your own unit"). Everything else is Board Toy 1's: Hearthstone mana, 25 cards of Units (health = cost) and Strikes (damage = cost) for both, both open with 3 and the first player skips the first draw.

- A region pays the side whose units in it have more total health; a tie pays nobody. At the end of your turn you gain 1 food for each region that pays you. First to 20 wins.
- Regions are the five columns (your tile and the one facing it). `setRegionShape('block')` in `src/engine.js` makes them the four 2 by 2 blocks instead.

Bot against bot, 100 games each: columns at 20 food, first player 45%, about 11 turns each, no stalls; blocks at 20 food, first player 58%, about 9 turns each. 
`node build.mjs` writes `index.html` and `artifact.html`; `node selftest.mjs` plays the bot against a greedy player, a random player and itself.

## Full Hand

`node build.mjs full` writes the variant where both players start with their whole deck in hand and never draw (Martin, 2026-11-26: "not at the mercy of my draw"), to `index-full.html` and `artifact-full.html`. Identical cards show once, with their count.

Bot against bot, with a little noise in the bot's choices (without noise every game is the same game): the first player wins 93 to 100%. The side to move retakes most columns and is paid for them before the other side can answer, and with every answer always in hand the lead never changes hands. Making up for going second: the coin (1 extra mana once) 93%, a head start of 1 to 3 food 98 to 100%, 5 food 88%, 8 food 43%. Columns paying at the start of their owner's turn instead (what survived the enemy turn) bring it to 71%, with games twice as long (`setScoreAt('start')`; the bot still plans for end-of-turn payment there).
