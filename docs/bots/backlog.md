# Bots — Backlog

Open items only. Top-3 summary in [`../STATUS.md`](../STATUS.md). Ladder: GreedyBot → TurnBot → RefereeBot.

- [ ] **TurnBot → default report pilot?** Smoke (20/opp) improves-or-ties all 7 decks but blows the 10× throughput gate (12×–266×; draw-driven turn depth — memoization was a negative result, see status §5). Run acceptance (200/opp) and clear the gate: lower `TURN_DETERMINIZATIONS`/`TURN_BEAM_WIDTH` or add a turn-depth cap; A/B speed-vs-winrate via the paired benchmark. Then decide whether `./report` default switches from `greedy,greedy` to `turn,turn`. Don't paper over a failed gate with deck-specific weights.
- [ ] **RefereeBot / TurnSearcher performance (roadmap Phase 2).** Two proven
  semantic-preserving passes so far (same-machine, jobs=1, referee cohort):
  - `clone()` fast-path (`a8bd2fb`): typed plain-copy + `Random.__new__` → **1.26×** (5.80→4.58 CPU-s/game).
  - evaluate/connectivity (this pass): precomputed `GameMap.neighbors` sort, deduped the
    double `connected_occupied(me)` in `evaluate`, threaded a single `occ` through
    `_enabled_battlecry_count` + `TurnSearcher._beam`, inlined `owner_of` in the BFS →
    **1.14×** (4.58→4.02). Proven: evaluator/connectivity byte-identical over 5421 states
    (both maps/configs), byte-identical GameRecords on the referee/turn/greedy cohort.
  - **Cumulative 1.44×** (5.80→4.02). Full 117,600-game calibration referee portion ~46h→~32h
    (8 jobs), total still ~1.5 days — faster but not yet casual-run practical.
  - **Next lever = persistent per-state connectivity cache** (`connected_occupied` + `is_connected`
    are still the top cluster). Higher-risk: board mutates in ~4 scattered `effects.py` sites and
    `legal_placements` queries connectivity mid-`apply_action`, so it needs per-mutation
    invalidation + its own broad-cohort equivalence proof. **Don't** cut determinizations/beam
    without a separate paired strength-vs-speed experiment. (4→8 jobs only +9%: 6 perf + 2
    efficiency cores, so per-game speed is the main lever, not more workers.)
- [ ] **Known blind spot: row-2 spine.** `region_control` over-values the row-2 spine on map_a, so neither greedy nor referee ever contests row-1/row-3 as an HQ-rush lane — a shared blind spot a competent human exploits.
- [ ] **cats_midrange vs aggro_hq_rush — bot execution gap (NOT a card nerf).** Bot-sim says cats crushes it (~13%); human playtest says aggro wins 2/3. Root-caused to piloting flaws (hand-dumping instead of holding for disruption; can't sequence removal). Two fixes shipped (wasted-battlecry penalty; opponent-lethal-next-turn) but the specific matchup number barely moved. Trust the human read; keep improving pilot play — don't touch the cards.
