# Board Toy 3

Each player owns one row of 5 tiles, facing the other's (Martin, 2026-11-26: "each player owning their own row was the idea"). A unit goes on a tile of your own row: an empty one, or one holding your own unit, which it replaces at any strength (as landing on your own unit does in the game; Martin, 2026-11-26: "you should for sure be able to play units on top of your own unit"). You draw 2 cards at the start of each turn (Martin, 2026-11-26, after trying 3: "let's try drawing 2 per turn"); both open with 3 and the first player skips the first draw. Everything else is Board Toy 1's: Hearthstone mana, 25 cards of Units (health = cost) and Strikes (damage = cost) for both.

- A region pays the side whose units in it have more total health; a tie pays nobody. At the end of your turn you gain 1 food for each region that pays you. First to 20 wins.
- Regions are the five columns (your tile and the one facing it). `setRegionShape('block')` in `src/engine.js` makes them the four 2 by 2 blocks instead.

Bot against bot, 100 games each: columns at 20 food, first player 45%, about 11 turns each, no stalls; blocks at 20 food, first player 58%, about 9 turns each. 
`node build.mjs` writes `index.html` and `artifact.html`; `node selftest.mjs` plays the bot against a greedy player, a random player and itself.

## Full Hand

`node build.mjs full` writes the variant where both players start with their whole deck in hand and never draw (Martin, 2026-11-26: "not at the mercy of my draw"), to `index-full.html` and `artifact-full.html`. Identical cards show once, with their count.

Bot against bot, with a little noise in the bot's choices (without noise every game is the same game): the first player wins 93 to 100%. The side to move retakes most columns and is paid for them before the other side can answer, and with every answer always in hand the lead never changes hands. Making up for going second: the coin (1 extra mana once) 93%, a head start of 1 to 3 food 98 to 100%, 5 food 88%, 8 food 43%. Columns paying at the start of their owner's turn instead (what survived the enemy turn) bring it to 71%, with games twice as long (`setScoreAt('start')`; the bot still plans for end-of-turn payment there).

## The 70% test (2026-11-26)

Martin's skill-chain test: from a random player, each bot is the simplest found that beats the one below it in at least 70% of games (`node ladder.mjs`, 400 games a pairing, both seats on the same deals). On this toy, drawing 2:

- Easy, units on random empty tiles and never a strike: beats Random 77%.
- Cluster, each unit next to the most of your own: beats Easy 78%.
- Normal, each play the one that most raises held regions minus his: beats Cluster 85%.
- Hard, Normal that also values half-built triangles (`greedyTurn`): beats Normal 96%.
- Expert, the best of six candidate turns by four play-outs eight turns deep with Hard on both sides (`rolloutBot(6, 4, 8)`): beats Hard 80.5%.
- Nothing found beats Expert: an eight-times larger search 43%, the same search seeing every hidden card 46.5%. Hidden cards are not what stops it; this family of search has hit its own ceiling, which is not proof the game has.

Control, Board Toy 1 (food per unit, the game Martin found shallow): the simplest bot over 70% against Random is the greedy one (kill the biggest you can, else play your biggest unit), 82%; nothing tried beats it 70% (one-turn lookahead 55%, play-outs 41%).
