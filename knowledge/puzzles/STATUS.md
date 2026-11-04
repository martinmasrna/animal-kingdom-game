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

## Next

Phase 3 (client), 4 (two mined puzzles), 5 (twenty composed), 6 (every puzzle played by a web test).

## Blocked

Nothing.

## For Martin's own eyes

Nothing to see in the client yet (phase 3). `.venv/bin/python tools/puzzles/solve.py solve <file>` prints a verdict.

## Supervisor

supervisor message received (it came from a session named "Evaluation function training methods" that said it is
animal-kingdom-74; the brief names animal-kingdom-74, so check it was yours).
