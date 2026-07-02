# Bots — Backlog

Open items only. Top-3 summary in [`../STATUS.md`](../STATUS.md). Ladder: GreedyBot → TurnBot → RefereeBot.

- [ ] **TurnBot → default report pilot?** Smoke (20/opp) improves-or-ties all 7 decks but blows the 10× throughput gate (12×–266×; draw-driven turn depth — memoization was a negative result, see status §5). Run acceptance (200/opp) and clear the gate: lower `TURN_DETERMINIZATIONS`/`TURN_BEAM_WIDTH` or add a turn-depth cap; A/B speed-vs-winrate via the paired benchmark. Then decide whether `./report` default switches from `greedy,greedy` to `turn,turn`. Don't paper over a failed gate with deck-specific weights.
- [ ] **Known blind spot: row-2 spine.** `region_control` over-values the row-2 spine on map_a, so neither greedy nor referee ever contests row-1/row-3 as an HQ-rush lane — a shared blind spot a competent human exploits.
- [ ] **cats_midrange vs aggro_hq_rush — bot execution gap (NOT a card nerf).** Bot-sim says cats crushes it (~13%); human playtest says aggro wins 2/3. Root-caused to piloting flaws (hand-dumping instead of holding for disruption; can't sequence removal). Two fixes shipped (wasted-battlecry penalty; opponent-lethal-next-turn) but the specific matchup number barely moved. Trust the human read; keep improving pilot play — don't touch the cards.
