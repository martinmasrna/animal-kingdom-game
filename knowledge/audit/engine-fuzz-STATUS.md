# Engine fuzz: status

Branch `engine/fuzz-crashes`. Report: [`engine-fuzz-2026-11-05.md`](engine-fuzz-2026-11-05.md).

supervisor message received (phase 2, relayed by the session "Evaluation function training methods" as from animal-kingdom-74)

- Phase 1 done: `tools/engine_fuzz.py`, 5,000 uniform games (0 crashes, 0 refusals, 1 long game), 115,000-game sweeps (same).
- Phase 2 done: 20,000 biased games (0 crashes, 0 refusals, 3 long games); human-game probe over every replayable log
  found one crash group (`state.py ensure_mates` KeyError on an unknown card id), fixed in `new_game` (commit 717a207).
- Open, for Martin: a lone roamer after both decks run out keeps a game going to the 400-turn cap; 575 human logs hold
  old design ids that `web/renamed.py` doesn't map (six of them replayed before the fix only by luck).
