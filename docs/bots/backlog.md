# Bots — Backlog

Open items only. Top-3 summary in [`../STATUS.md`](../STATUS.md). Ladder: GreedyBot → TurnBot → RefereeBot.

- [ ] **★ HIGH — Unify the A/B harnesses: give `bot_comparison` config-awareness, retire
  `referee_comparison`'s mirror-strength mode.** The two benchmarks answer different questions
  and are *not* broadly redundant: `bot_comparison` = strength verdict (candidate(D) vs Greedy(O)
  vs baseline(D) vs Greedy(O), **paired per (opponent, seed)** → cancels shared variance, tight CI);
  `referee_comparison` = decision-agreement + speed screen over a fixed position corpus vs the
  uncapped legacy oracle (higher-power for "same move?" than any win-rate test; keep it). **The
  real defect is a missing abstraction:** `bot_comparison` accepts only bot *kind strings*, not
  parametrized configs/flags. That single gap forced (a) `referee_comparison` to grow its own
  config-parametrized **mirror-strength** mode (`--mirror-deck`), which duplicates `bot_comparison`
  in the *weaker* head-to-head design, and (b) bespoke hand-rolled A/Bs for any config/flag change
  (e.g. the `greedy_belief` weight and the `collapse_deck_reveal_choices` flag). **Fix:** generalize
  `bot_comparison` to take a parametrized bot spec (kind + kwargs/config), keeping the
  paired-vs-fixed-opponent design; then future flag/config A/Bs run through the one good harness in
  the superior design, and `referee_comparison` sheds `--mirror-deck` and keeps only its unique
  agreement/oracle screen. **Why HIGH:** it kills a *class* of methodology error — a mirror
  self-play A/B is valid but **low-power for small pilot changes** (games where the two versions
  play identically add coin-flip noise instead of contributing 0 to a paired delta), so hand-rolled
  mirror checks understate/obscure real effects. Also: add a one-line caveat to the `balance-eval`
  skill ("mirror self-play is low-power for small changes — prefer the paired-vs-fixed-opponent
  delta"); the skill already prescribes `bot_comparison` for bot changes, this hardens the trap.
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
  - **Search-budget lever — SHIPPED as Referee v3 (`3794071`, 2026-07-03).** `nodes 1000→150`
    **and** `reply_width 4→8` in `sim/runner.py`: **~1.31×** faster than v2 whole-game while
    *stronger* on every deck (fixes the prior colony under-pilot gap). Full method/data in
    [`referee-search-tuning.md`](referee-search-tuning.md), raw in `results/referee_nodebudget/`.
    Persistent connectivity cache remains a further semantic-preserving lever but is higher-risk
    (per-mutation invalidation).
- [ ] **Known blind spot: row-2 spine.** `region_control` over-values the row-2 spine on map_a, so neither greedy nor referee ever contests row-1/row-3 as an HQ-rush lane — a shared blind spot a competent human exploits.
- [ ] **cats_midrange vs aggro_hq_rush — bot execution gap (NOT a card nerf).** Bot-sim says cats crushes it (~13%); human playtest says aggro wins 2/3. Root-caused to piloting flaws (hand-dumping instead of holding for disruption; can't sequence removal). Two fixes shipped (wasted-battlecry penalty; opponent-lethal-next-turn) but the specific matchup number barely moved. Trust the human read; keep improving pilot play — don't touch the cards.
