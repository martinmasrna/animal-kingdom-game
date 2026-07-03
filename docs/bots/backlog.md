# Bots — Backlog

Open items only. Top-3 summary in [`../STATUS.md`](../STATUS.md). Ladder: GreedyBot → TurnBot → RefereeBot.

- [ ] **TurnBot → default report pilot?** Smoke (20/opp) improves-or-ties all 7 decks but blows the 10× throughput gate (12×–266×; draw-driven turn depth — memoization was a negative result, see status §5). Run acceptance (200/opp) and clear the gate: lower `TURN_DETERMINIZATIONS`/`TURN_BEAM_WIDTH` or add a turn-depth cap; A/B speed-vs-winrate via the paired benchmark. Then decide whether `./report` default switches from `greedy,greedy` to `turn,turn`. Don't paper over a failed gate with deck-specific weights.
  - **Measured post-`f598951` (turn-vs-greedy whole-game CPU ÷ greedy-vs-greedy, map_b two-action, 6 games/deck):** ramp **9.6×** (only deck under gate), canine 13.3×, cats 21.8×, aggro/colony 24.0×, egg 184×, **food_otk 590×**. The semantic-preserving perf pass did **not** move the gate — the blowup is structural (complete-turn search explodes on the deep combo decks food_otk/egg, not a constant factor). Confirms a turn-depth cap / determinization cut is required, and that's a strength tradeoff (validate via the paired benchmark, don't just speed-cap). (Measured by timing `play_game` for turn-vs-greedy vs greedy-vs-greedy per deck.)
- [ ] **RefereeBot / TurnSearcher performance (roadmap Phase 2).** Three proven
  semantic-preserving passes so far (same-machine, jobs=1, referee cohort):
  - `clone()` fast-path (`a8bd2fb`): typed plain-copy + `Random.__new__` → **1.26×** (5.80→4.58 CPU-s/game).
  - evaluate/connectivity (this pass): precomputed `GameMap.neighbors` sort, deduped the
    double `connected_occupied(me)` in `evaluate`, threaded a single `occ` through
    `_enabled_battlecry_count` + `TurnSearcher._beam`, inlined `owner_of` in the BFS →
    **1.14×** (4.58→4.02). Proven: evaluator/connectivity byte-identical over 5421 states
    (both maps/configs), byte-identical GameRecords on the referee/turn/greedy cohort.
  - semantic-preserving pass 3 (`f598951`): `legal_placements` precomputes the connection-legal
    crossroad set once per call (not per card×crossroad); `_enabled_battlecry_count` enumerates
    only battlecry-card placements via `allowed_cards`; `_planning_eval`'s readiness projection
    uses field save/restore instead of a full `clone`. Byte-identical over a 114-game
    greedy/referee/turn cohort (both maps+configs) + suite 279 passed. **~1.14×** referee-vs-greedy.
  - **Cumulative ~1.6×** vs original (1.44× × 1.14×). Profiling (this session) shows the average
    cost is now dominated by reply rollouts (~320/decision), so further *semantic-preserving*
    wins are small — the next lever is algorithmic (search-budget), which needs paired strength.
  - **Node-budget candidate — NOT shipped, awaiting owner sign-off.** `REFEREE_MAX_SEARCH_NODES`
    1000→150 gives **~1.73×** whole-game (cumulative **~2.8×** vs original) with 137/139
    first-action agreement (identical to v2). Paired mirror vs the *shipped* v2 (200 games/deck,
    seed 1600; egg pooled to 800): **ties every deck** — aggro 50.0 [47,53], canine 49.5,
    cats 50.0, colony 49.5, egg 49.1 [46.4,52], food_otk 50.5, ramp 50.0 (all lower CI ≥46).
    The budget is strength-neutral (colony identical at nodes 1000/350/150; egg 150==350).
    Validate/reproduce: `python -m animal_kingdom.sim.referee_comparison --mirror-deck all
    --games 200 --candidate-config nodes=150 --reference-config nodes=1000 --jobs 8 --seed 1600`.
    **Owner decision:** flip the one constant in `sim/runner.py` (raw data in
    `results/referee_nodebudget/`). Persistent connectivity cache remains a further
    semantic-preserving lever but is higher-risk (per-mutation invalidation).
- [ ] **Staged Referee v2 diverges from the legacy oracle on combo/deep decks (calibration risk;
  NOT a card nerf).** The shipped `referee` (staged v2, `526ccd0`) pilots **colony_food_swarm
  43.4% [39.8%, 46.8%]** vs the full legacy referee (500 games: seed3000 400g + seed1500 100g) —
  a real ~7-pt regression (CI excludes 50), budget-independent (~37–44% at nodes 1000/350/150).
  The other 6 decks are near-parity at 100g but weren't measured at 500g power. The staged
  root-screen + reply-beam prune
  exactly colony's deep multi-placement combo/swarm lines. Isolation (100g, same seed, staged
  candidate vs oracle): baseline root5/reply4 44% → root8/reply4 45% → **root5/reply8 50%** →
  **root8/reply8 55%** — the **reply beam is the dominant lever** (widening reply 4→8 restores
  parity; root secondary). Caveat: a full 100g v2-vs-legacy profile is near-parity on all decks
  (44–51%), so colony is the softest, not a stark outlier. Tension: widening reply raises the
  dominant cost (reply rollouts), so this is a faithfulness-vs-throughput call for the oracle.
  The v2 acceptance only ever validated food_otk (50.5%), so this went unmeasured. Since
  RefereeBot is the **calibration oracle**, a ~10-pt pilot gap means staged-v2
  is a weaker colony pilot than the exhaustive search it approximates — it can mis-rank colony
  in the anchored ratings. Fix is pilot-side (e.g. widen root/reply for combo-shaped positions,
  generalist; or run the oracle at `staged=False` on a small calibration cohort), **never a card
  change**. Owner triage. (egg shows a much smaller ~2% budget sensitivity — see above.)
- [ ] **Known blind spot: row-2 spine.** `region_control` over-values the row-2 spine on map_a, so neither greedy nor referee ever contests row-1/row-3 as an HQ-rush lane — a shared blind spot a competent human exploits.
- [ ] **cats_midrange vs aggro_hq_rush — bot execution gap (NOT a card nerf).** Bot-sim says cats crushes it (~13%); human playtest says aggro wins 2/3. Root-caused to piloting flaws (hand-dumping instead of holding for disruption; can't sequence removal). Two fixes shipped (wasted-battlecry penalty; opponent-lethal-next-turn) but the specific matchup number barely moved. Trust the human read; keep improving pilot play — don't touch the cards.
