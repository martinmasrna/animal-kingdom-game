# 12 Deck is life: alive (first-player edge close to the line)

Passes every machine gate (`node sim.mjs 400`, `report.json`); the set positions pass (`node sanity.mjs`); the page plays (`node check.mjs`: whole games clicked through in headless Chrome at 1512×800 and phone width, no script errors).

## Numbers

- Expert vs Random: **100%** of 400 (seats alternated, same deals)
- Expert vs Greedy: **82.8%** of 400
- Expert vs Racer: **86.8%** of 400
- First player's win rate, Expert vs Expert: **66.2%** of 400; Greedy vs Greedy: 62.1% of 2000. Inside 30–70%, but its 95% interval reaches past 70.
- Games hitting the turn cap: **0%**
- Expert's choice equal to Greedy's: **43.3%** of its decisions with more than one option
- Length: 13.5 turns in all (about 7 each)

Expert is single-observer ISMCTS (1500 iterations a move; its own deck order and the opponent's hand and deck redealt each iteration, 4-turn play-outs with a heuristic policy). Its strength does not move with budget: against Greedy, 1500, 4000 and 10000 iterations all won 82–89% over 100–120 games.

## The loop

Nothing blocks, so it is a race of decks: every unit that can hit the opponent's deck usually does (about 70% of Expert's attacks go at the deck), and a turn's real decisions are which enemy units are worth killing (Hit 2, or a trade that kills and survives), when to cash Burn 3, and when to spend life on cards. Draw 2 trades two cards of life for two cards of hand, Recover buys three cards of life for 2 mana; Expert uses each about once a game per player, mostly late, when the deck is short and a card in hand or a turn of life decides the race. The first player hits first, which is why the first-player edge sits near the line.

## Notes

- Set positions (Expert, every seed): lethal (a Raider at a 3-card deck), lethal through Burn 3, with a deck of 1 never Draw 2 (Recover instead), and kill the Raider that would burn your last 3 cards (going face cannot win that turn).
- The spec's free-trade position (your ready Line against an enemy Raider: attack it) is not free in this game: played out by Expert from both sides, going face won 19% and trading 7% from that position. Damage here is card loss, so a trade costs tempo in the race. The set position was replaced by this game's own unarguable trade, above.
- Two Expert bugs found by the set positions and fixed before the gate: the play-out cut-off scored material, so a side already holding an empty deck (dead at its next draw) could still look ahead; and it did not prefer a win now to a sure win later.
- Rules choices where the spec is silent: the Coin leaves the game when played (it never reaches the discard, so Recover cannot shuffle it in); Recover may take 0 to 3 cards (the page asks you to pick them; the bots take the three best).
