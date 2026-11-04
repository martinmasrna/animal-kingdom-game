# Engine crash fuzz, 2026-11-05

**Tool:** `tools/engine_fuzz.py`. Random 30-card decks over every collectible card (204 cards, copy limits kept), a
random legal action each step from whichever seat is to act, one seeded stream per game (`random.Random(seed)` picks
the decks and the actions; `new_game(seed)` the engine's own chance). A 3% chance to end the turn early once an action
is taken, and a 30% chance that the seat whose mulligan waits underneath makes its choice first
(`rules.apply_early_mulligan`). Python engine only. It records every exception from `legal_actions`, `apply_action` or
`is_terminal`, every offered action that `apply_action` refused, and every game past 300 actions; groups them by the
traceback's last engine frame; keeps the shortest reproduction per group in `results/engine_fuzz.json`.

    .venv/bin/python tools/engine_fuzz.py --games 5000 --seed 0          # the run below, 16 s on 4 cores
    .venv/bin/python tools/engine_fuzz.py --replay 2800 --show          # one game, where it fails

## The run

5,000 games (seeds 0–4999), 317,650 actions. Every collectible card was placed at least 110 times; 5,230 early
mulligans; 18,460 pending choices, 3,861 pending placements, 24,515 roams, 3,826 early turn ends.

| Group | Games | Traceback line | Fixed or left | Reproduction |
|---|---|---|---|---|
| Exceptions from `legal_actions` / `apply_action` / `is_terminal` | 0 | — | — | — |
| Offered actions refused by `apply_action` | 0 | — | — | — |
| Past 300 actions | 1 | none (no exception) | left: not an engine fault | seed 2800, index 300 |

**The long game (seed 2800).** At action 300 it is turn 263: both decks and hands are empty, A's units on the board can
Roam, B has nothing to do and passes. A Roam counts as acting (`rules._end_turn`: `roams_<player>`), so the "two idle
turns in a row end the game" rule never fires, and the game runs until the 400-turn cap (`config.max_turns`) ends it at
action 369 by food (B 73, A 64). The engine does what its rules say; nothing raises and the game ends.
`test_engine_fuzz.py::test_long_game_ends_at_the_turn_cap` holds it.

A design note for Martin, not a bug: in a real game a player out of cards with a roamer can keep the game going to the
turn cap by walking a unit back and forth. With humans the cap is far off (400 turns), so it only matters if someone
stalls on purpose.

## Wider sweeps (same tool, to check the clean result)

- 95,000 more games (seeds 100000–194999): 5,981,870 actions, 0 exceptions, 0 refusals, 25 long games.
- 20,000 games with no early turn ends (`--pass-rate 0`, seeds 300000–319999): 0 exceptions, 0 refusals, 3 long games.

All 29 long games re-played to the end: each one ends by the turn cap (21) or by food (5) with both decks and hands
empty, or by the turn cap (3) with one seat holding a single card it can't place (an Orca, the legendary Anaconda) while
the other roams. Same pattern as seed 2800.

## Tests

`animal_kingdom/tests/test_engine_fuzz.py`: 40 seeded games raise nothing and end; seed 2800 ends at the turn cap; the
tool reports a planted crash and a planted refusal with seed, decks and action; `play(seed, stop_at=i)` rebuilds the
position before action i. No failing or xfail test: there was no failure to hold. No engine change, so no Rust mirror
to name.

## Counts

- Games: 5,000 (plus 115,000 in the wider sweeps)
- Failure groups: 1 (long games), 0 crash groups, 0 refusal groups
- Fixed: 0
- Left as xfail: 0
- Left, not an engine fault: 1 (lone roamer runs to the turn cap)
