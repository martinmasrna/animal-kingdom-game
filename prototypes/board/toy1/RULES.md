# Board Toy 1

The smallest version of Martin's no-covering idea (2026-11-26): units that only sit, removed only by damage from a spell. Everything else in today's game (regions, connection, raids, landing on your own unit) is left out until a toy shows it is needed.

- Board: a shared 4 by 4. Tiles have no geometry yet: any empty tile is as good as any other.
- Mana as in Hearthstone: 1 on your first turn, one more each turn up to 10, refilled at the start of your turn.
- Deck: 25 cards, the same list for both players. Both open with 3. Draw 1 at the start of each of your turns, except the first player's first turn (as in Magic). An empty deck draws nothing.
- Unit (cost 1 to 5, three copies each): placed on an empty tile. Its health equals its cost. Damage stays; at 0 it is removed.
- Strike (cost 1 and 2: three copies, cost 3 and 4: two copies): deal damage equal to its cost to an enemy unit.
- Food: at the end of your turn you gain 1 food for each of your units on the board, as in the game. First to 20 wins.

Who goes first, in bot-against-bot games: with Hearthstone's hands (3 and 4, both drawing) the first player won 58%; skipping only the first draw, 26%; equal hands of 3 with both drawing, 79%; this rule, 50%. A card is worth a lot in a game this short.

`node build.mjs` writes `index.html` (and `artifact.html` for publishing); `node selftest.mjs` plays the bot against a greedy player, a random player and itself.
