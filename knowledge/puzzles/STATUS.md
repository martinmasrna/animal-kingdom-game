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

## Calls I made (for Martin to overrule)

- **A draw with an empty deck.** The engine offers no draw from an empty deck. Drawing nothing is the same move as ending
  the turn early, which both players may do at any point, so the search offers that instead of changing the engine.
- **No chance.** A card whose text says "random" is refused, and so is any position where an effect draws on the random
  stream with more than one possible outcome (a City Spider's Dawn choosing between two equally weak animals, a filtered
  draw). A draw with one possible outcome (a choice among identical copies) is allowed.
- **A food win is not a solve.** Only the den counts; a position where the solver could win on food instead is a bad
  puzzle, and `check` would show it as not forced.
- **Timers are not in the format.** A puzzle board holds animals (with an optional `counter` for given strength, and
  `spent` for a used Spikes or Boar charge), not pending "in 2 turns" effects. `from-log` warns when it drops one.

## In progress

- **Phase 5** (twenty composed): 13 of 20, all passing `check` with one winning first turn: five in one turn
  (`river_horse`, `shell_game`, `down_the_hole`, `the_pack`, `buried`) and eight in two (`thorns`, `dam`, `hunger`,
  `first_in_line`, `ink`, `slow_poison`, `stripes`, `shock`). A won turn is grouped by the board it leaves, so the same
  win finished with a different spare card counts once. The two-turn ones are built around one idea in a walled lane;
  the solver shows where a position leaks, and the defender's hand is what makes the solution unique. The notes are
  in `knowledge/puzzles/set-1-2026-11-05.md` (board, hand, obvious move, solution, defence, difficulty).

## Next

The last seven two-turn puzzles, then phase 6 (every puzzle clicked to Solved, both fast suites), then phase 7.

## Blocked

Nothing. (Chrome for Testing could not be downloaded here; the tests run on the preinstalled Chromium.)

## For Martin's own eyes

- `./play`, then http://localhost:8000/#/puzzles: the two puzzles. The game screen with the brief box bottom left,
  the defender's hand face up along the top, the end box (Solved / Not solved).
- `empty_handed` shows the legendary Elephant, which has no painting yet: its piece is a dark disc with "[ELEPHANT]".
  Fine to play, but not to show anyone until the art lands.
- The web suite in this cloud container: 12 tests fail on a clean `main` too (collection filters, news dot, replays, the
  game's panels and hover labels), with the container's Chromium instead of Chrome (Chrome's download was blocked by
  the network). The same 12 fail with my changes, and the 3 new ones pass. Worth one `npm test` on the Mac. `.venv/bin/python tools/puzzles/solve.py solve <file>` prints a verdict.

## Supervisor

supervisor message received (it came from a session named "Evaluation function training methods" that said it is
animal-kingdom-74; the brief names animal-kingdom-74, so check it was yours).
