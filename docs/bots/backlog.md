# Bots — Backlog

Open items only. Top-3 summary in [`../STATUS.md`](../STATUS.md). Ladder: GreedyBot → TurnBot → RefereeBot.

- [ ] **TurnBot → default report pilot?** Smoke (20/opp) improves-or-ties all 7 decks but blows the 10× throughput gate (12×–266×; draw-driven turn depth — memoization was a negative result, see status §5). Run acceptance (200/opp) and clear the gate: lower `TURN_DETERMINIZATIONS`/`TURN_BEAM_WIDTH` or add a turn-depth cap; A/B speed-vs-winrate via the paired benchmark. Then decide whether `./report` default switches from `greedy,greedy` to `turn,turn`. Don't paper over a failed gate with deck-specific weights.
- [ ] **RefereeBot / TurnSearcher performance (roadmap Phase 2).** `clone()` fast-pathed
  2026-07-02 (`a8bd2fb`): typed plain-copy for the effect-model containers + `Random.__new__`
  RNG copy → **~1.25× referee speedup** (7.53→6.02 CPU-s/game, jobs=1), byte-identical records.
  **Next target = the shared `greedy_bot.evaluate` / connectivity path** (`connected_occupied`
  BFS + `top_unit`/`owner_of`, ~26s cumulative — the biggest remaining sink in the referee
  profile). Higher-risk (shared evaluator gates balance); needs its own semantic-equivalence
  validation. Full 117,600-game calibration is still ~1.5 days on 8 cores (referee portion
  ~46h→~37h) — not yet casual-run practical. **Don't** cut determinizations/beam to go faster
  without a separate paired strength-vs-speed experiment. (4→8 jobs only +9%: 6 perf + 2
  efficiency cores, so per-game speed is the main lever, not more workers.)
- [ ] **Known blind spot: row-2 spine.** `region_control` over-values the row-2 spine on map_a, so neither greedy nor referee ever contests row-1/row-3 as an HQ-rush lane — a shared blind spot a competent human exploits.
- [ ] **cats_midrange vs aggro_hq_rush — bot execution gap (NOT a card nerf).** Bot-sim says cats crushes it (~13%); human playtest says aggro wins 2/3. Root-caused to piloting flaws (hand-dumping instead of holding for disruption; can't sequence removal). Two fixes shipped (wasted-battlecry penalty; opponent-lethal-next-turn) but the specific matchup number barely moved. Trust the human read; keep improving pilot play — don't touch the cards.
