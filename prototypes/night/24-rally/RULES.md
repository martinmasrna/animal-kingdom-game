# 24 Rally

Every number is a placeholder.

- Each player has the same 20-card deck of shots, shuffled, and draws 5. A shot card has a Pace, a Reach and a stamina cost.
- A random player serves first.
- **A point:** the server plays any shot, paying its stamina cost. Then the players alternate: each must answer the last shot with a card whose Reach is at least that shot's Pace, paying its cost. A player who cannot, or will not, loses the point. After the point, both discard the cards they played and draw back up to 5 (the discard pile is shuffled in when needed).
- **Stamina:** 10 each at the start of every game; it carries from point to point within the game.
- **Serve:** the serve passes to the other player after every point. *(Changed after the gate; the spec has one player serve a whole game, the serve passing every game. See `report.json`.)*
- **Scoring:** a game is won by the first player to 4 points; the match by the first player to 3 games.

| Card | Cost | Pace | Reach | Copies |
|---|---|---|---|---|
| Push | 0 | 1 | 2 | 4 |
| Drive | 1 | 3 | 3 | 4 |
| Slice | 1 | 2 | 4 | 3 |
| Lob | 1 | 2 | 5 | 2 |
| Dig | 2 | 1 | 6 | 2 |
| Smash | 3 | 5 | 3 | 3 |
| Ace | 4 | 6 | 2 | 2 |

## Files

`node build.mjs` writes `index.html` (and `artifact.html`); `node sim.mjs` runs the gate into `report.json` (`SERVE_EVERY_POINT` in `src/engine.js` switches between the changed rule and the spec's); `node sanity.mjs` the set positions; `node check.mjs` plays the page headless; `node quick.mjs A B n` a quick head-to-head.
