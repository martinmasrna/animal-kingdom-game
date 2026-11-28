# 14 Response duel: alive

Passes every machine gate (`node sim.mjs 400`, `report.json`); the set positions pass (`node sanity.mjs`); the page plays (`node check.mjs`: whole games clicked through in headless Chrome at 1512×800 and phone width, no script errors).

## Numbers

- Expert vs Random: **99.8%** of 400 (seats alternated, same deals)
- Expert vs Greedy: **96.0%** of 400
- Expert vs Racer: **98.5%** of 400
- First player's win rate, Expert vs Expert: **55.0%** of 400; Greedy vs Greedy: 50.7% of 2000
- Games hitting the turn cap: **0%**
- Expert's choice equal to Greedy's: **46.2%** of its decisions with more than one option
- Length: 28.8 turns in all between Experts (about 14 each), 18.7 against Greedy
- Among the trivial bots, answering is what matters: Greedy (answers when it happens to have mana left) beats Racer (never answers) 86%, and Racer loses even to Random, 34%, because Random often ends its turn with mana and answers by chance.

Expert is single-observer ISMCTS (1500 iterations a move; the opponent's hand redealt each iteration from the cards it has not seen, 4-turn play-outs with a heuristic policy, scored by life, cards and Sieges still to tick). Every response window is its own decision in the search.

## The loop

The whole game is one question asked twice a turn: spend the mana now, or end the turn with it stored so that every spell the opponent casts meets a Cancel, Ward or Mirror. Expert ends most turns with mana held back, feeds cheap Bolts first to draw out the opponent's answers, and casts Blast or Barrage only into an empty or spent store; answering, it takes about three of every four windows it gets. A spell's worth depends on what the other side has stored and how many answers it has shown, so the duel is read off the stored-mana gems and the cards already spent, not off the hand alone. With no board, the pace is set entirely by that bluff-and-bait exchange; races end only when one side's store runs dry.

## Notes

- Set positions (Expert, every seed): lethal (Blast into 5 life against nothing stored), Cancel the Barrage with 3 stored, never Ward a Study, with no Response in hand spend all the mana on damage.
- Rules choices where the spec is silent: Mirror answers only damage spells of 5 or less (not Study, Barrage or Siege); Ward may be cast on any spell, Study included (it does nothing there); the Coin is not a Spell and cannot be answered; the other player gets a response window whenever it has stored mana and a card in hand. On the page, a window where you hold nothing that can answer passes by itself.
