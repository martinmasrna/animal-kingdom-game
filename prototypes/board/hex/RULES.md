# Hex

A shared hex board of 14 tiles in rows of 2, 3, 4, 3, 2 (Martin, 2026-11-26). A region is any three mutually adjacent tiles (16 of them); at the end of your turn you gain 1 food for each region whose three tiles all hold your units. First to 20 wins.

- Placement, connection (Martin, 2026-11-26: "the most natural would be the rule where you must place units so that they are connected to your base"): a unit goes on one of your two base tiles (your nearest row) or next to one of your units that links back to a base tile through your own units, onto an empty tile or one of your own units, which it replaces. Strikes hit any enemy unit. `setConnect(false)` restores free placement, which the 70% runs below were made with unless they say otherwise.
- Cards: 25 for both, Units costing 1 to 5 with health equal to cost (three each) and Strikes dealing their cost (1 and 2: three each, 3 and 4: two each). Hearthstone mana. Both open with 3; you draw 1 at the start of each turn (Martin, 2026-11-26, after trying 3 and 2: "make it draw 1 card per turn"), except the first player's first turn.

Drawing 2, bot against bot, 150 games: first player 54 to 61%, about 14 turns each, both decks empty by about turn 11 each. Drawing 3: first player 57%, decks empty by about turn 8. Drawing 1: first player 34 to 39%.

The page plays you against Expert, alternates who goes first, keeps a win count in your browser, and saves each finished game (seed, first player, every move) to the artifact's store; `node replay.mjs <dir>` replays saved games turn by turn.

## The 70% test (2026-11-26)

Martin's skill-chain test: from a random player, each bot is the simplest found that beats the one below it in at least 70% of games (`node ladder.mjs`, 400 games a pairing, both seats on the same deals). Every bot first passes `node sanity.mjs` (close the winning triangle, no chip damage for nothing, break his winning triangle). On this toy, drawing 2, after the fix of 2026-11-26 (a played card counts as spent; Expert keeps Hard's turn unless its play-outs clearly prefer another):

- Easy, units on random empty tiles and never a strike: beats Random 77%.
- Cluster, each unit next to the most of your own: beats Easy 78%.
- Normal, each play the one that most raises held regions minus his: beats Cluster 85%.
- Hard, Normal that also values half-built triangles (`greedyTurn`): beats Normal 96%.
- Expert, Hard's turn unless twelve play-outs per candidate, eight turns deep with Hard on both sides, clearly prefer another (`rolloutBot(6, 12, 8)`): beats Hard 83%.
- Centre+, Martin's centre rule (`centreBot`: every triangle holds one of the four centre tiles 3, 6, 7, 10, so hold them all, save strikes for them, refill with the strongest unit) with play-outs on top (`centrePlus()`): beats Expert 70.9% (400 games). The rule alone beats Expert 62.6%. Martin found it by hand and beat Expert 5-1 with it (2026-11-26), and called the game boring once he had it: the board's whole blocking set is four adjacent tiles that also pay 2 food a turn, so the top of the chain is one recipe.
- The lock scales: on 3-4-5-4-3 the centre 2-3-2 (a tile and its six neighbours, 7 tiles) touches all 24 triangles and holds 6 of them, 6 food a turn against nothing (Martin, 2026-11-26).
- Before the fix, nothing found beat Expert: an eight-times larger search 43%, the same search seeing every hidden card 46.5%; that search has not been rerun on the fixed bots.

Control, Slots (food per unit, the game Martin found shallow): the simplest bot over 70% against Random is the greedy one (kill the biggest you can, else play your biggest unit), 82%; nothing tried beats it 70% (one-turn lookahead 55%, play-outs 41%).

## The 70% chain with connection, drawing 1 (2026-11-26, `node chain.mjs`, 400 games a step)

- Cluster, units next to the most of your own: beats Random 79.6% (Easy, units on random tiles, only 60.1%).
- Normal, each play the one that most raises held regions minus his: beats Cluster 96.0%.
- Hard, Normal that also values half-built triangles: beats Normal 84.3%.
- Nothing found beats Hard 70%: Expert 58.0%; above Expert, the centre rule with search 22.5% and an eight-times-larger search 50.0%.

