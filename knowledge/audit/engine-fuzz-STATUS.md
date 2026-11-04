# Engine fuzz: status

Branch `engine/fuzz-crashes`. Report: [`engine-fuzz-2026-11-05.md`](engine-fuzz-2026-11-05.md).

- Done: `tools/engine_fuzz.py`, 5,000-game run (0 crashes, 0 refusals, 1 long game), 115,000-game wider sweeps (same),
  `animal_kingdom/tests/test_engine_fuzz.py` (passes).
- Fixes: none needed. Open: none. Design note for Martin: a lone roamer after both decks run out keeps the game going to
  the 400-turn cap.
