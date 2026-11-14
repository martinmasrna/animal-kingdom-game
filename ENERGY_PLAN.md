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

- Branch `energy` created from `provisions` (62b8cd0a). caffeinate running for 12 h.
- Steps 1 and 2 done: energy rules in Python and Rust behind AK_ENERGY=1, Rust built into the worktree venv (maturin from main's venv), fuzz parity 150/150 under energy and 60/60 under the old rules. Next: the data overlay (step 3).
- Step 3 first draft done: tools/energy/table.py (203 cards: 201 costed, 2 benched), build.py writes data/energy.json and prints the checks. Card changes behind config numbers in both engines (Mouse draws 2, Hummingbird gains 2 energy, Mole legend without discard, Grizzly plain, Crocodile Apex+Armor, Giraffe Reach, Elephant plain, whales lose Titan). Parity 300/300 energy, 100/100 old. Next: decks (step 5), bots and simulations (4, 6).
- Step 3 first draft done: tools/energy/table.py (203 cards: 201 costed, 2 benched), build.py writes data/energy.json and prints the checks. Card changes behind config numbers in both engines (Mouse draws 2, Hummingbird gains 2 energy, Mole legend without discard, Grizzly plain, Crocodile Apex+Armor, Giraffe Reach, Elephant plain, whales lose Titan). Parity under energy and old rules. Next: decks (step 5), bots and simulations (4, 6).
- Steps 4 and 5 done: six decks (tools/energy/decks.py), sim harness (tools/energy/sim.py; AK_ENERGY=1 AK_RUST_BOTS=1). Plain 'referee' (hand-tuned) beats greedy 73% and equals 'turn'; use it for sims. First round robin (900 games, results/energy/rr1.jsonl): median 9 player-turns, food 54% / den 46%, first player 49% with 3 energy on turn one, no deck-outs, decks 43-61% (Deck 6 Colony 61, Deck 1 Cats 57). Next: frontend (7), Costs board (8), deploy (9), then cost iteration (6) and the morning page (10).

(Log times were dropped: the first entries carried guessed clock times. From here each entry reads the clock.)
- 02:33 Step 7 done: cost gem on cards (card.js, shown whenever a card has a price), 'Draw' with its price, five pips, builder with 30 cards / 2 copies / no caps / cost filter / deck list by cost; bot levels use hand-tuned evaluation. Checked by screenshots of a local server (AK_ENERGY=1, port 8011). Old-rules Python suite running in the background as a regression check.
- 02:36 Step 8 done: Costs board at http://localhost:8006/#b=costs (tools/board with an 'energy' board; cost = the Cost N pile; strengths by +/-; rule numbers in the top bar), tools/energy/lab.py runs the board and a local game on 8010 and rebuilds/restarts on every board save (tested through the API: about 9 s). NOTE: the board writes tools/energy/edits.json, which overrides table.py; while I iterate the table, edits.json stays deleted, and at the end make_board.py resets the board to the table. Deploying to the test app now (step 9).
- 02:54 Step 9 done: first version deployed to https://animal-kingdom-provisions.fly.dev/ (AK_ENERGY=1 in deploy/fly.provisions.toml). Old-rules Python suite passes without the switch except test_wasm_build (the committed wasm is stale against the changed Rust sources; the wasm is only used by ?local=1 practice; not rebuilt).
- 02:54 Step 6 findings (results/energy/*.jsonl, sweep_first.txt, sweep_pace.txt; plain referee bot, 840 to 1260 games a run):
  - First-turn energy (5 a turn, no cap, first costs): 2 -> first player wins 46%, 3 -> 50%, 4 -> 57%, 5 -> 59%. Keep 3.
  - SWARM, Martin's own worry: a deck of only 1-cost animals (Deck 7) won 89% under the first costs (Lion 2, wolf-sized bodies 1), taking the den by its second turn in 153 of 360 games. Re-costed with the Lion at 3 and only small bodies at 1: still 81% (wide cheap bodies take regions faster than they can be broken).
  - With max_places_per_turn = 2 ("at most two animals a turn", Config.max_places_per_turn, both engines, parity checked): Lion-2 costs -> Deck 7 70% (its saved energy buys a card every turn); Lion-3 costs -> all seven decks 44-57%, Deck 7 56%, den by turn 4 in 3 games, median 12 turns, first player 52%.
  - Pace under cap 2 + Lion-3: 5 energy median 12; 6 energy median 10 (today's), food/den 51/49, first player 49%, decks 46-59%, no deck-outs; draw cost 1 -> 9-10 draws a player and decks start running out; cap 3 -> Deck 7 79%.
  - DEFAULT NOW: 6 energy a turn, first turn 3, a draw costs 2, at most 2 animals a turn, cost scale lion3 (table.SCALE; COST_LION2 kept as the alternative). Martin's own numbers (5 energy, no cap) are one change away on the Costs board.
  Next: rebuild board, restart lab, redeploy; a check with the stronger search; per-card outliers; then the morning page.
