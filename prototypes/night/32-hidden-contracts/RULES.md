# 32 Hidden contracts

Every number is a placeholder.

- No life. First to 10 points wins at once. Points come only from contracts.
- Each player has the same 30-card main deck and a contract deck of the same 8 contracts, both shuffled. Each draws 2 contracts and keeps them face-down. Board max 6 units; units attack enemy units only.
- Random first player; the first draws 3 main cards, the second draws 4 and gets the Coin (0 mana: +1 mana this turn).
- **Your turn:** your maximum mana goes up by 1 (cap 10) and refills; your units become ready; draw 1 (from an empty main deck the opponent gets 1 point). Then every contract you hold whose condition is true now is revealed and scores; you draw a replacement for each (if your contract deck has any). You never hold more than 2.
- Play cards by paying their cost; a unit cannot attack the turn it is played. Once per turn you may pay 1 mana to bury a held contract face-down and draw a replacement.
- Each ready unit may attack an enemy unit once: both deal their attack to each other. Damage stays; a unit at 0 health is destroyed.
- If both players hold no contracts and both contract decks are empty, the higher score wins; equal is a draw. Turn cap 120 (a draw); never reached.

| Contract | Condition at the start of your turn | Points |
|---|---|---|
| Crowd | You control 4 or more units | 3 |
| Tower | You control a unit with 6 or more health | 2 |
| Clean | The opponent controls no units | 3 |
| More | You control more units than the opponent | 2 |
| Hunter | You destroyed 2 or more enemy units during your last turn | 2 |
| Force | Your units' total attack is 10 or more | 3 |
| Spread | You control units of 3 different costs | 2 |
| Patience | You hold 6 or more cards in hand | 2 |

Main deck, three of each: Striker 1: 2/1, Raider 2: 3/2, Guard 2: 2/3, Line 3: 3/4, Heavy 4: 4/5, Big 5: 5/5, Huge 6: 6/7, Hit 2 (1 mana), Hit 3 (2 mana), Hit 6 (4 mana): that much damage to an enemy unit.

## Files

`node build.mjs` writes `index.html` (and `artifact.html`); `node sim.mjs` runs the gate into `report.json`; `node sanity.mjs` the set positions; `node check.mjs` plays the page headless; `node quick.mjs A B n` a quick head-to-head; `node trace.mjs seed` prints one Expert mirror game.
