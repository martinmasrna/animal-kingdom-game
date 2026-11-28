# Engine War

A deckbuilder for two. No life total: points come only from Posts on your table, which the opponent shoots. 20 points at the start of your turn wins.

- **Start.** Each deck: Coin ×7 (+1 coin), Shot ×3 (+1 damage). The 36-card market deck is shuffled and 5 cards lie face-up as the row. Random first player; the first player's first hand is 3 cards, every other hand 5.
- **Turn.**
  1. **Yield.** Each of your Posts on the table gives its yield in points. 20 or more: you win.
  2. **Play** your whole hand. Coin and damage add to this turn's pools; a Post goes onto your table and stays until destroyed; Draw adds 1 coin and draws 2 cards that are played too; Trash removes another card in your hand or discard pile from the game.
  3. **Buy** any number of row cards with coin; each goes to your discard pile and the row refills at once.
  4. **Shoot** enemy Posts: a Post is destroyed when you assign damage at least equal to its health this turn. While the opponent has a Wall Post on the table, only it can be shot. Destroyed Posts go to their owner's discard pile.
  5. Discard what you played, then draw 5, shuffling your discard pile into a new deck when needed. Unspent coin and damage are lost.
- **End.** 20 points at the start of your turn wins. When the market deck runs out, the round is finished (both players have had the same number of turns) and the higher score wins; equal is a draw. A game that reaches turn 120 is a draw.

Buying and shooting may be done in any order in the build (neither affects the other).

## Market (36 cards)

| Card | Cost | Effect | Copies |
|---|---|---|---|
| Coin 2 | 3 | +2 coin | 6 |
| Shot 2 | 3 | +2 damage | 5 |
| Shot 4 | 6 | +4 damage | 3 |
| Draw | 4 | +1 coin, draw 2 cards and play them | 4 |
| Small Post | 3 | Post: health 3, yield 1 | 5 |
| Post | 5 | Post: health 5, yield 2 | 5 |
| Big Post | 8 | Post: health 7, yield 3 | 3 |
| Wall Post | 4 | Post: health 6, yield 0; your other Posts cannot be shot while it stands | 3 |
| Trash | 2 | Remove another card in your hand or discard pile from the game | 2 |

## Files

`node build.mjs` writes `index.html` (and `artifact.html`): you against Expert, first player alternating. `node sim.mjs` runs the gate and writes `report.json`; `node sanity.mjs` the set positions; `node check.mjs` plays whole games through the page's calls in node and by clicks in Chrome.
