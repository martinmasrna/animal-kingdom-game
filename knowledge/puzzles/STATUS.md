# Puzzle mode: status

Branch `puzzles/mode` (from `main`), built overnight by a cloud session. Rewritten after every phase.

## Done

- **Phase 1, format and solver.** `animal_kingdom/puzzles.py` holds the format (`data/puzzles/<id>.json`), the position
  builder and the solver; `tools/puzzles/solve.py` is its command line (`solve`, `check`, `write`, `from-log`, `show`).
  The search is an exact AND/OR search over every decision point: every action, every choice, free placements and
  ending the turn early, for both seats, with a transposition table and a node cap that reports "unproven".
  Tests: `animal_kingdom/tests/test_puzzles.py` (forced in 1 with one winning turn, forced in 2, not forced because a
  Grizzly Bear's block escapes, the node cap, random cards refused, chance from the random stream refused, and every
  shipped puzzle file checked).

- **Phase 2, server.** `Match.start_puzzle` (web/match.py) starts a match from the puzzle's position: the defender's
  hand face up (`revealedHand`), decks empty, no mulligan, no clock. The defender is `PuzzleBot`, the solver's own
  search: a reply that escapes if any does, else the one leaving the solver the fewest winning moves. After every
  action the search judges the position; the moment the den can no longer be forced the puzzle fails (result reason
  `puzzle`). `rematch` retries from the start, at any time. A view carries `puzzle` (title, brief, hint, turns left,
  status). Server: `POST /api/match {"puzzle": id}`, `GET /api/puzzles` (with solved flags); a solved puzzle goes into
  a new `puzzles` table on the profile; no game log, no match history, no rating, no Discord line, no rejoin. Puzzle
  moves are applied off the event loop (the verdict searches). Tests: `animal_kingdom/tests/test_puzzle_match.py`.

- **Phase 3, client.** `#/puzzles` lists the puzzles (title, theme, turns, Solved) on the settings screen's layout;
  `#/puzzle/<id>` starts one and opens the ordinary game screen (`#/m/<match>`). There the defender's hand is face up,
  the brief ("Take the den in 2 turns.", the turns left) stands in the box where a card's question stands, with Hint
  and Start over as that box's buttons; the flag becomes the house and goes back to the list; no versus intro. The end
  box says Solved or Not solved, with Puzzles, See the board and Try again. No home entry. Web test:
  `animal_kingdom/web/test/puzzle.test.mjs` (the list, one solved by clicks, one failed and retried), with the click
  driver in `puzzleplay.mjs`; the server reads fixture puzzles from `AK_PUZZLE_DIR`.

- **Phase 4, the first two puzzles**, from `tools/puzzles/forced_captures-2026-11-05.jsonl`, decks emptied, hands
  kept, stacks in full (`solve.py from-log`), each with one winning first turn:
  `empty_handed` ("Empty-handed", the audit's no. 1: roam the Bush Dog forward, its Pup keeps the chain, then the
  Elephant roams in) and `the_whale_road` ("The whale road", no. 2: the Crocodile clears the Oxpecker, the Sloth takes
  the den). `animal_kingdom/web/test/puzzles.test.mjs` clicks every shipped puzzle's main line to Solved (about 2 s
  each, so it sits in the fast suite). The brief stands top left, between your food gem and the defender's face-up hand (at the bottom it
  covered a five-card hand, which is why `dam` timed out in the click-through test on the Mac).

- **Phase 5, twenty composed puzzles**, each built around one idea where the obvious move walks past it, every file
  passing `check` (one winning first turn; `the_herd` two, the same idea either way round). In one turn, for a
  newcomer's first hour: `river_horse` (a Roar comes before the Hippo answers), `shell_game` (Armor survives Spikes),
  `down_the_hole` (the Mole's free placement), `the_pack` (a Wolf roams through its pack), `buried` (a removal brings
  back your own buried Lion). In two turns, rising: `first_in_line` (spend the Boar's one charge), `hunger` (the
  Elephant starves at its owner's Dawn: wait), `slow_poison` (never cover the Toad early), `two_doors` (two threats, one
  Grizzly), `the_herd` (the Cape Buffalo's strength on the opponent's turn), `head_on` (cover the Boar itself; a 5 holds
  against a Pigeon), `thorns` (the Skunk sends the Hedgehog home), `dam` (the Beaver's timer only runs on top: put it
  out of reach), `shock` (a race: the Electric Eel as the link), `bite` (below 0 dies), `stripes` (covering a Zebra
  sends you home; remove it from beside), `ink` (the Octopus dies to the Hippo it switches off), `deep_water` (the
  Krill makes the Sperm Whale cheap and is the top it blasts off your own Lion), `short_circuit` (block the Mouse in
  your den front, then the Eel), `stepping_stone` (a roam uncovers what it stood on). Their boards, obvious moves,
  solutions, defences and difficulty: `knowledge/puzzles/set-1-2026-11-05.md`. The defender's hands are what make the
  solutions unique; most two-turn boards are one walled lane, so the set reads alike (more below).

- **Phase 6, every puzzle through the client.** `animal_kingdom/web/test/puzzles.test.mjs` clicks each shipped
  puzzle's main line (the defender's replies played by the server) to Solved: all 22 pass. Python fast tier: 3717
  passed, only main's own 3 stale deck-doc failures. Web suite here: the 12 container-only failures that a clean
  `main` has too (Chromium instead of Chrome); everything else, the puzzle tests included, passes.

## Calls I made (for Martin to overrule)

- **A draw with an empty deck.** The engine offers no draw from an empty deck. Drawing nothing is the same move as ending
  the turn early, which both players may do at any point, so the search offers that instead of changing the engine.
- **No chance.** A card whose text says "random" is refused, and so is any position where an effect draws on the random
  stream with more than one possible outcome (a City Spider's Dawn choosing between two equally weak animals, a filtered
  draw). A draw with one possible outcome (a choice among identical copies) is allowed.
- **Chance anywhere in the tree refuses the position.** A City Spider or a Tarantula choosing between two equally
  weak animals is chance even off the solution's line, so those cards only fit boards with no ties anywhere.
- **A food win is not a solve.** Only the den counts; a position where the solver could win on food instead is a bad
  puzzle, and `check` would show it as not forced.
- **Timers are not in the format.** A puzzle board holds animals (with an optional `counter` for given strength, and
  `spent` for a used Spikes or Boar charge), not pending "in 2 turns" effects. `from-log` warns when it drops one.

## Next

Phase 7: ten more puzzles at a time, each batch committed, until told to stop. A clean one-turn Ocelot puzzle is already
waiting. Next ideas: boards that are not one walled lane (open fields, both flanks), other decks and habitats
(Fish, Colony, Canines), and the ideas that did not hold yet (the Leo and Lea pair, Flight over a wall, a Dusk timing,
the City Spider, which ties and so brings chance).

## Blocked

Nothing. (Chrome for Testing could not be downloaded here; the tests run on the preinstalled Chromium.)

## For Martin's own eyes

- `./play`, then http://localhost:8000/#/puzzles: the 22 puzzles, one-turn first. Play a few of each kind: are the
  ideas worth a puzzle, is the difficulty order right, do the titles and hints say too much or too little?
- The set document, `knowledge/puzzles/set-1-2026-11-05.md`: every board as text with its obvious move and solution,
  to judge them without playing.
- Variety: most two-turn boards are one lane walled by Grizzly Bears with Lions up the middle, because that shape is
  where uniqueness is easiest to get. Whether that reads as a house style or as sameness is your call; phase 7 is
  trying other shapes.
- The brief box (top left), the hint, Start over, and the end box. No home entry yet: the list is only at `#/puzzles`.
- `empty_handed` shows the legendary Elephant, which has no painting yet ("[ELEPHANT]" on a dark disc).
- The supervisor confirmed both fast suites pass on the Mac apart from `dam`, which is fixed (the brief box was over
  a five-card hand).

## Supervisor

supervisor messages received and acted on (they came from a session named "Evaluation function training methods" that said it is
animal-kingdom-74; the brief names animal-kingdom-74, so check it was yours).
