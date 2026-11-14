# The energy prototype: overnight plan and progress (started 2026-11-14, about 01:30)

Read this first after any context reset. It is the brief, the decisions, the step list and the log for the overnight run Martin set up. Everything lives in this worktree (`provisions-worktree/game`, branch `energy`, branched from `provisions`). Main, live and staging are never touched. The test app on Fly is `animal-kingdom-provisions` (`SKIP_TESTS=1 deploy/deploy.sh provisions`).

## What Martin asked for (his words, 2026-11-14)

His plan: "(1) Implement the rules, the engine, etc., the backend; (2) Go over every single card, adjust strength so that it matched the animals, scale 1-10, along the heuristics we settled (so don't just look at raw weight but use a bit of common sense, that is Orca shouldn't be like elephant and Eagle shouldn't be 'smaller' than dog); (3) Implement the frontend: costs shown and mana/energy crystals or whatever; (4) Bots, probably with the old evaluation function that wasn't tuned to specific cards. Create 5-6 sample, diverse decks and have them play (30 card decks are fine once again, with legendaries at 1 copy and non-legendaries at 2 copies). (5) The costs board yes, with strength adjustments."

His later answers: call the resource "energy" (or mana), never "points". A deck may hold any number of legendaries. "yes, set the initial costs, and also feel free to change and iterate on them, on strength numbers, on any card text. Feel free to temporarily throw away any card that stopped making sense. Use your simulation and data to iterate on whatever you want, I mean you have 10 hours to work with." Time will not run short; the Rust engine is not to be cut.

His real constraints (the only ones): a card game about animals; fun, beautiful, pleasant; good, with as low complexity and as much depth as possible. Old quoted verdicts in docs are not laws.

## The rules of the prototype

- A turn is **5 energy** (his numbers). Unspent energy is lost. No growth, no free card.
- Every animal has a **cost of 1 to 5**, paid on placement. Tokens cost 0. A Titan is simply a cost of 5 (the keyword's two-action rule goes).
- **Drawing a card costs 2 energy** and draws 1 card.
- No limit on placements in a turn beyond energy.
- Roam (moving an animal) costs energy: start at 2, tune.
- The first player's first turn has less energy: simulation picks the number for an even start.
- Opening hand 4, mulligan, hand limit 10, covering, connection, regions, food, the den: unchanged.
- Animals an effect puts into play are free (tokens, Leo fetching Lea). A generic "play another animal" becomes "play another animal that costs N or less" (free), N per card.
- One old action is worth about 2 energy: Beaver "next turn you have 2 more energy", Electric Eel "your opponent has 2 less energy next turn", Krill "your next Titan this turn costs 2 less".
- Decks: 30 cards, 2 copies, 1 of a legendary, any number of legendaries, no rarity caps, no budget.
- Strength is the animal's size on a 1 to 10 scale: weight class with common sense. Sea animals count about two classes lower, birds of prey about two higher, snakes by length. Where Martin set a strength by hand on the boards (`tools/board/boards/prices.json`, `strengths.json`: `strs`), his number wins.
- Card texts with a strength number ("strength 4 or less") get the number shifted so the card hits about the same animals as before.
- The new rules sit behind a switch (config), so the old game's tests still run against the old rules.

## Cost drafting rates (first draft, then iterate on data)

The Lion (7, vanilla) costs 2. A drawn card is worth 2 energy. Body value by strength, effect value on top, rounded to 1..5. His 65-card sort (`boards/prices.json` piles) is a check on the ordering, not on the numbers. Cards whose effect bends a rule get a best guess, marked.

## Steps

- [ ] 1. Python engine: energy rules behind a config switch; card costs; draw price; roam price; action-worded effects translated.
- [ ] 2. Rust engine: the same, built into this worktree's venv, parity with Python checked by the fuzz tool.
- [ ] 3. Data overlay: every collectible card's strength (1 to 10), cost, changed text; benched cards; shifted thresholds.
- [ ] 4. Bots: hand-tuned evaluation (plain referee, or greedy) under the new turn; measure against greedy.
- [ ] 5. Six sample decks, 30 cards, diverse.
- [ ] 6. Simulations: first-turn energy for an even start; pace, deck-out rate, den vs food split, rush share; per-card outliers; iterate costs and texts.
- [ ] 7. Frontend: cost on every card, energy pips, the draw price, deck builder for 30 cards with 2/1 copies sorted by cost.
- [ ] 8. Costs board: cost +/- and strength +/- per card, the rule numbers, writing the overlay; a local game server that restarts on a change; a button to send it to the online test app.
- [ ] 9. Deploy to the test app, verify by playing a bot game through the browser.
- [ ] 10. Morning page for Martin (published artifact, opened): what was built, what changed and why, what the numbers show, the list of touched texts and benched cards, known weak spots.

## Log

- 01:30 Branch `energy` created from `provisions` (62b8cd0a). caffeinate running for 12 h.
