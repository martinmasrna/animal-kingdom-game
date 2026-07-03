# Bots — Backlog

Open items only. Top-3 summary in [`../STATUS.md`](../STATUS.md). Ladder: GreedyBot → TurnBot → RefereeBot.

- [x] **DONE (`4e5fd74`) — `bot_comparison` is now config-aware.** It accepted only bot *kind
  strings*, forcing bespoke (and low-power mirror) A/Bs for any config/flag change (the
  `greedy_belief` weight, the `collapse_deck_reveal_choices`/width flag). Now it compares configs
  of the same kind through its paired-vs-fixed-opponent design: `make_bot(extra=...)` threads
  per-kind constructor kwargs, `MatchSpec`/`run_pairs` carry picklable kwargs tuples per seat, and
  `parse_bot_spec("kind:k=v,k=v")` (int/float/bool coercion) powers `--baseline-kind
  "turn:deck_reveal_choice_width=0"`. Kwargs recorded in `summary.json`; table headers show the
  real kinds. Validated: reproduced the egg width-2-vs-0 collapse delta (−0.4% vs the hand-rolled
  −1.4%). **Methodology note now enforceable:** mirror self-play is low-power for small pilot
  changes (identical-play games add coin-flip noise instead of a 0 paired delta) — always use this.
- [ ] **★ Follow-up — retire `referee_comparison`'s `--mirror-deck` strength mode + harden the
  skill.** With `bot_comparison` config-aware, `referee_comparison`'s mirror-strength games (the
  *weaker* head-to-head design) are redundant — its unique, keep-forever role is the fixed-position
  **decision-agreement** screen vs the uncapped legacy oracle. Drop `--mirror-deck`, route referee
  config strength A/Bs through `bot_comparison --candidate-kind "referee:reply_width=8,..."`. Also
  add a one-line caveat to the `balance-eval` skill ("mirror self-play is low-power for small
  changes — prefer the paired-vs-fixed-opponent delta").
- [ ] **TurnBot → default report pilot?** Smoke (20/opp) improves-or-ties all 7 decks but blows the 10× throughput gate (12×–266×; draw-driven turn depth — memoization was a negative result, see status §5). Run acceptance (200/opp) and clear the gate via a turn-depth cap (lowering `TURN_DETERMINIZATIONS`/`TURN_BEAM_WIDTH` was tried and rejected — see the uniform-trim negative result below); A/B speed-vs-winrate via the paired benchmark. Then decide whether `./report` default switches from `greedy,greedy` to `turn,turn`. Don't paper over a failed gate with deck-specific weights.
  - **Measured post-`f598951` (turn-vs-greedy whole-game CPU ÷ greedy-vs-greedy, map_b two-action, 6 games/deck):** ramp **9.6×** (only deck under gate), canine 13.3×, cats 21.8×, aggro/colony 24.0×, egg 184×, **food_otk 590×**. The semantic-preserving perf pass did **not** move the gate — the blowup is structural (complete-turn search explodes on the deep combo decks food_otk/egg, not a constant factor). Confirms a turn-depth cap / determinization cut is required, and that's a strength tradeoff (validate via the paired benchmark, don't just speed-cap). (Measured by timing `play_game` for turn-vs-greedy vs greedy-vs-greedy per deck.)
  - **Diagnosis refined (`a32dc1c`):** the outlier was **egg alone (285×)**, and its cost was *not* placement chains — profiling showed the blowup is Owl/Raven's wide "which cards to keep/shuffle" **selection** sub-tree (585k ChoiceActions vs ~600 on cats), amplified by the Flight-heavy deck's placement fan-out. **Shipped:** collapse those deck-reveal choices to top-N in lookahead (`TURN_DECK_REVEAL_CHOICE_WIDTH=2`, tuned via a paired egg-vs-field width sweep) → egg **285×→~38×** (11.9s→1.45s/game), strength cost insignificant (−1.4% [−5.0, +2.1]); no-op on the six decks without Owl/Raven. **Negative result (reverted, not committed):** a self-cover placement filter (drop covering my own unit with a weaker body unless it hits an enemy) was a **wash** — egg 1.01×, slower on 2 decks — because egg's cost is the selection tree, not placements, and proving the aggressive cases dead costs a sim that cancels the saving.
  - **Still open for the gate:** egg ~38× and the moderate cluster (colony 49×, cats/food_otk/aggro ~20×) all remain >10×. The *uniform* trim (`TURN_DETERMINIZATIONS` 3→2 / `TURN_BEAM_WIDTH` 8→6) was the candidate field-wide cut here.
  - **Uniform trim — NEGATIVE RESULT (2026-07-03, not adopted; keep D3/B8).** Swept D2, B6, D2+B6 vs full-turn across all 7 decks (paired, 60 games/opp × 7 = 420/deck, opp=greedy, `results/` bundle in scratchpad). The two levers are mismatched: **only the determinization cut (3→2) speeds anything up (~25%, `slow`≈0.75×), and it is not free** — it costs ~4% strength (aggro −3.8%, food_otk −4.0% CI [−7.6,−0.5] excludes 0, egg −3.6%); **the beam cut (8→6) is strength-neutral but buys ~0 speed** (`slow`≈0.9×, within timing noise — the ply cost is deck-reveal selection + placement fan-out, not the cross-ply beam). D2+B6 just pays D2's strength cost for no extra speed. **No good elbow exists.** It also can't meet its own purpose: 0.75× of a 20–49× cluster still leaves colony ~37× / cats·food·aggro ~15× / egg ~28×, all >10×. **The gate needs the structural turn-depth cap, not a beam/determinization shave** — that is now the only remaining throughput lever for TurnBot.
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
