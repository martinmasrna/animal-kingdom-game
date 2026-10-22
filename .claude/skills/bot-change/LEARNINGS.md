# Learnings — bot-change

Staged, Martin-ratified lessons about measuring and shipping bot changes. Read at the start of every run; append only after Martin confirms, one line each; prune freely. Stable lessons graduate into `SKILL.md` and leave here.

<!-- Format: - [YYYY-MM-DD] <the heuristic>. -->
- [2026-10-21] The mechanism check is a reading aid, not a gate: when the pooled interval clears zero and several decks clear on their own, the result stands even if the predicted pattern was wrong (quiescence: predicted sub-choice density, got headroom; shipped).
- [2026-10-22] Two candidates run back to back on one frozen checkout are each measured against the Expert of that checkout, so the second never sees the first: when the first ships mid-run, the second ships on the assumption that the gains add (mulligan after quiescence), and the next run on a fresh checkout measures against both. Say the assumption in the ship entry; rerun the second only when the two touch the same decisions.
